"""
Write the API's OpenAPI description (the contract Swagger shows) to a file.

    python services/rule_service/scripts/export_openapi.py docs/api/openapi.json

Needs no database and no real secrets: placeholder settings are used only
to build the app; nothing is started.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    placeholder = "placeholder-only-for-export-0000000000"
    settings = Settings(
        _env_file=None,
        RULE_SVC_PASSWORD=placeholder,
        JWT_SECRET=placeholder,
        RULE_API_KEY=placeholder,
        API_USER_DISPATCHER_PASSWORD=placeholder,
        API_USER_SUPERVISOR_PASSWORD=placeholder,
        API_USER_ADMIN_PASSWORD=placeholder,
        LOG_LEVEL="WARNING",
    )
    spec = create_app(settings, repository=object()).openapi()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OpenAPI {spec['openapi']} description of '{spec['info']['title']}' {spec['info']['version']} "
          f"written to {out} ({len(spec['paths'])} paths)")


if __name__ == "__main__":
    main()
