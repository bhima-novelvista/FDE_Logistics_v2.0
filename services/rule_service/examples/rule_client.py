"""
rule_client.py - a small machine client of the rule service.

It shows how ANOTHER PROGRAM should call the API (service-to-service), for
example a scheduler, a phone app back end, or the v3.0 AI service:

- logs in with the API key (header X-API-Key). The key is read from the
  project's .env and is never printed;
- sets time limits: 3 s to connect, 30 s to answer;
- retries up to 3 times, but only when the call surely did not get
  through or the service says "try again" (connection refused, 502, 503,
  504), waiting 0.5, 1 and 2 seconds (or the Retry-After the service gives);
- sends its own request ID (X-Request-ID: client-...), so the call can be
  found in the service log and in the audit table;
- turns an error answer (problem details) into one clear line.

Usage, from the project folder (the venv's Python; see Step 4, Part G):
  python services/rule_service/examples/rule_client.py health
  python services/rule_service/examples/rule_client.py ready
  python services/rule_service/examples/rule_client.py rules
  python services/rule_service/examples/rule_client.py latest 3
  python services/rule_service/examples/rule_client.py decision 32065
  python services/rule_service/examples/rule_client.py evaluate 6.5 2.0 3.0 0.4 "Moderate Risk"
  python services/rule_service/examples/rule_client.py scan --from 2024-08-01 --to 2024-08-29 --examples 2
Add --json after the command name to print the full JSON answer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx2 as httpx

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RETRY_STATUSES = {502, 503, 504}
WAITS = [0.5, 1.0, 2.0]


def read_env(path: Path) -> dict[str, str]:
    """Read KEY=value lines from .env (no values are printed)."""
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


class RuleServiceClient:
    def __init__(self, base_url: str, api_key: str):
        self.client = httpx.Client(
            base_url=base_url,
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout=httpx.Timeout(30.0, connect=3.0),
        )

    def call(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        request_id = f"client-{uuid.uuid4().hex[:20]}"
        headers = {"X-Request-ID": request_id}
        for attempt in range(len(WAITS) + 1):
            start = time.perf_counter()
            try:
                response = self.client.request(method, path, headers=headers, **kwargs)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                if attempt == len(WAITS):
                    raise SystemExit(
                        f"ERROR: cannot reach the rule service at {self.client.base_url} ({exc.__class__.__name__}). "
                        "Is it running? (Step 4, Part E)"
                    ) from None
                wait = WAITS[attempt]
                print(f"   ... no connection, retry {attempt + 1}/{len(WAITS)} in {wait} s", file=sys.stderr)
                time.sleep(wait)
                continue
            ms = (time.perf_counter() - start) * 1000
            if response.status_code in RETRY_STATUSES and attempt < len(WAITS):
                wait = min(float(response.headers.get("Retry-After", WAITS[attempt])), 3.0)
                print(f"   ... {response.status_code}, retry {attempt + 1}/{len(WAITS)} in {wait} s", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"-> {method} {path}  {response.status_code} {response.reason_phrase}  in {ms:.0f} ms  "
                  f"request_id={response.headers.get('X-Request-ID', '?')}")
            return response
        raise AssertionError("unreachable")


def fail_if_error(response: httpx.Response) -> dict[str, Any]:
    body = response.json() if response.content else {}
    if response.status_code >= 400:
        print(f"ERROR {body.get('status', response.status_code)} {body.get('title', '')}: {body.get('detail', response.text)}")
        for err in body.get("errors") or []:
            print(f"   - {err.get('where')}: {err.get('problem')}")
        raise SystemExit(1)
    return body


def show_decision(decision: dict[str, Any]) -> None:
    print(f"Outcome: {decision['outcome']} (highest severity: {decision['highest_severity']}) - {decision['summary']}")
    for f in decision["fired"]:
        print(f"  {f['rule_id']:<3} {f['severity']:<8} {f['action']}")
        print(f"      because {'; '.join(f['evidence'])}   [SOP {f['sop_section']}]")
        if f.get("note"):
            print(f"      note: {f['note']}")
    print(f"Rules version: {decision['rules_version']}")


def show_reading(r: dict[str, Any]) -> None:
    print(f"Reading {r['reading_id']} at {r['timestamp']}: {r['temperature_c']:.2f} C, "
          f"{r['eta_variation_hours']:+.2f} h ETA, port {r['port_congestion_level']:.2f}, "
          f"{r['risk_classification']} (delay {r['delay_probability']:.3f}), "
          f"lat {r['latitude']:.4f} lon {r['longitude']:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the rule service with the API key from .env")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("health", "ready", "rules"):
        sub.add_parser(name).add_argument("--json", action="store_true")
    p = sub.add_parser("latest"); p.add_argument("limit", type=int, nargs="?", default=5); p.add_argument("--json", action="store_true")
    p = sub.add_parser("reading"); p.add_argument("reading_id", type=int); p.add_argument("--json", action="store_true")
    p = sub.add_parser("decision"); p.add_argument("reading_id", type=int); p.add_argument("--json", action="store_true")
    p = sub.add_parser("evaluate")
    for arg in ("temperature_c", "eta_variation_hours", "port_congestion_level", "delay_probability"):
        p.add_argument(arg, type=float)
    p.add_argument("risk_classification")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("scan")
    p.add_argument("--from", dest="from_time"); p.add_argument("--to", dest="to_time")
    p.add_argument("--examples", type=int, default=3); p.add_argument("--json", action="store_true")
    args = parser.parse_args()

    env = {**read_env(PROJECT_ROOT / ".env"), **os.environ}
    api_key = env.get("RULE_API_KEY", "")
    if not api_key:
        raise SystemExit("ERROR: RULE_API_KEY is not set in .env (Step 4, Part B).")
    base_url = env.get("RULE_API_URL") or f"http://127.0.0.1:{env.get('RULE_API_PORT', '8101')}"
    svc = RuleServiceClient(base_url, api_key)

    if args.command in ("health", "ready", "rules"):
        path = {"health": "/health", "ready": "/ready", "rules": "/v1/rules"}[args.command]
        body = fail_if_error(svc.call("GET", path))
        if args.command == "rules" and not args.json:
            print(f"{body['sop_name']} version {body['rules_version']} (loaded {body['loaded_at_utc']})")
            for r in body["rules"]:
                conds = (" AND " if r["match"] == "all" else " OR ").join(f"{c['field']} {c['op']} {c['value']}" for c in r["conditions"])
                print(f"  {r['rule_id']:<3} {r['kind']:<4} {r['severity']:<8} IF {conds}")
                print(f"      THEN {r['action']}")
            return
    elif args.command == "latest":
        body = fail_if_error(svc.call("GET", "/v1/readings/latest", params={"limit": args.limit}))
        if not args.json:
            for r in body["readings"]:
                show_reading(r)
            return
    elif args.command == "reading":
        body = fail_if_error(svc.call("GET", f"/v1/readings/{args.reading_id}"))
        if not args.json:
            show_reading(body)
            return
    elif args.command == "decision":
        body = fail_if_error(svc.call("GET", f"/v1/readings/{args.reading_id}/decision"))
        if not args.json:
            show_reading(body["reading"])
            show_decision(body["decision"])
            print(f"Audit row written: {'yes' if body['audit_logged'] else 'NO'}")
            return
    elif args.command == "evaluate":
        reading = {k: getattr(args, k) for k in (
            "temperature_c", "eta_variation_hours", "port_congestion_level", "delay_probability", "risk_classification")}
        body = fail_if_error(svc.call("POST", "/v1/evaluate", json=reading))
        if not args.json:
            show_decision(body["decision"])
            print(f"Audit row written: {'yes' if body['audit_logged'] else 'NO'}")
            return
    elif args.command == "scan":
        request: dict[str, Any] = {"examples": args.examples}
        if args.from_time:
            request["from_time"] = args.from_time if "T" in args.from_time else args.from_time + "T00:00:00"
        if args.to_time:
            request["to_time"] = args.to_time if "T" in args.to_time else args.to_time + "T23:59:59"
        body = fail_if_error(svc.call("POST", "/v1/scan", json=request))
        if not args.json:
            print(f"Readings checked: {body['readings_checked']}  (rules version {body['rules_version']})")
            print("Per rule:  " + "  ".join(f"{k}={v}" for k, v in body["rule_counts"].items()))
            print("Outcomes:  " + "  ".join(f"{k}={v}" for k, v in body["outcome_counts"].items()))
            for ex in body["examples"]:
                r, d = ex["reading"], ex["decision"]
                print(f"  {r['reading_id']} {r['timestamp']}  {d['outcome']:<15} {','.join(f['rule_id'] for f in d['fired'])}")
            return
    print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
