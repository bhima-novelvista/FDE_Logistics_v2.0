-- =====================================================================
-- 05_create_integration_layer.sql
-- v2.0, Step 3 (data integration layer): the safe way in for the new
-- rule service. The legacy table is NOT changed.
--
-- Creates:
--   fde_views.vw_fleet_readings   readable, read-only window on the
--                                 legacy table (11 of its columns)
--   fde_audit.RuleDecisionLog     append-only audit table: one row per
--                                 decision the rule service makes
--
-- The view runs with the rights of the admin who created it
-- (SQL SECURITY DEFINER), so the service login never needs any right on
-- the legacy table itself.
--
-- Safe to re-run: the view is replaced with the same definition; the
-- audit table and its rows are kept.
-- Run (from the project folder, Windows or macOS):
--   docker exec fde-mysql sh /scripts/run_sql.sh /scripts/05_create_integration_layer.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS fde_views
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

CREATE DATABASE IF NOT EXISTS fde_audit
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- The readable view. The 9 names marked HLD are the names used in the
-- HLD v1.2 (Table 8-2), so the later AI step (v3.0) can use them as is.
-- ---------------------------------------------------------------------
CREATE OR REPLACE
  ALGORITHM = MERGE
  SQL SECURITY DEFINER
VIEW fde_views.vw_fleet_readings AS
SELECT
  REC_ID          AS Reading_ID,             -- row number (not a truck or shipment ID)
  TS_UTC          AS `Timestamp`,            -- HLD
  V_LAT           AS Latitude,               -- HLD
  V_LON           AS Longitude,              -- HLD
  IOT_TEMP_VAL_C  AS Current_Temperature_C,  -- HLD
  ETA_VAR_HRS     AS ETA_Variation_Hours,    -- hours late (+) or early (-); SOP rule R2
  PRT_CNG_LVL     AS Port_Congestion_Level,  -- HLD
  DELAY_PROB_DEC  AS Delay_Probability,      -- HLD
  RISK_CLS_TXT    AS Risk_Classification,    -- HLD
  CGO_COND_CD     AS Cargo_Condition_Code,   -- HLD
  RT_RSK_IDX      AS Route_Risk_Index        -- HLD
FROM legacy_fleet.TBL_SC_FLEET_HIST_RAW;

-- ---------------------------------------------------------------------
-- The audit table. The service may only ADD rows (see 06_...sh); it can
-- never read, change or delete them.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fde_audit.RuleDecisionLog (
  Log_ID          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  Logged_At_UTC   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),  -- when (UTC, milliseconds)
  Request_ID      VARCHAR(64)     NOT NULL,       -- the request ID returned to the caller
  Caller          VARCHAR(64)     NOT NULL,       -- user name or client name
  Caller_Role     VARCHAR(32)     NOT NULL,       -- dispatcher, supervisor, admin, service, ...
  Auth_Method     VARCHAR(16)     NOT NULL,       -- jwt, api_key or self_test
  Endpoint        VARCHAR(128)    NOT NULL,       -- for example GET /v1/readings/{id}/decision
  Reading_ID      BIGINT UNSIGNED NULL,           -- the reading the decision is about (if any)
  Rules_Version   VARCHAR(16)     NULL,           -- for example 2.4
  Outcome         VARCHAR(32)     NOT NULL,       -- ACTION_REQUIRED, REVIEW, NO_ACTION, SCAN, RULES_RELOADED, RULES_REJECTED, SELF_TEST
  Fired_Rules     VARCHAR(255)    NULL,           -- for example R3,G1
  Detail_JSON     JSON            NULL,           -- the full decision as returned to the caller
  PRIMARY KEY (Log_ID),
  KEY IX_RDL_LOGGED_AT (Logged_At_UTC),
  KEY IX_RDL_READING (Reading_ID)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci;

SELECT 'fde_views.vw_fleet_readings and fde_audit.RuleDecisionLog are ready' AS status;

SELECT COUNT(*) AS rows_in_view FROM fde_views.vw_fleet_readings;

SELECT COUNT(*) AS columns_in_view
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'fde_views'
  AND TABLE_NAME   = 'vw_fleet_readings';
