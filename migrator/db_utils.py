"""
Database introspection and migration utilities.
Supports Oracle -> PostgreSQL data migration.
Uses mock data when real DBs are unavailable (for UI development/demo).
"""

import json
import os
import logging
import math
import uuid
from decimal import Decimal
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ── Mock data for demo / when DBs are not connected ─────────────────────────

MOCK_ORACLE_TABLES = [
    {"name": "EMPLOYEES", "rows": 1250, "schema": "HR"},
    {"name": "DEPARTMENTS", "rows": 27, "schema": "HR"},
    {"name": "JOBS", "rows": 19, "schema": "HR"},
    {"name": "LOCATIONS", "rows": 23, "schema": "HR"},
    {"name": "CUSTOMERS", "rows": 8400, "schema": "SALES"},
    {"name": "ORDERS", "rows": 34200, "schema": "SALES"},
    {"name": "ORDER_ITEMS", "rows": 98500, "schema": "SALES"},
    {"name": "PRODUCTS", "rows": 320, "schema": "SALES"},
]

MOCK_PG_TABLES = [
    {"name": "employees", "rows": 0, "schema": "public"},
]

MOCK_ORACLE_COLUMNS = {
    "EMPLOYEES": [
        {"name": "EMPLOYEE_ID", "type": "NUMBER", "nullable": False, "pk": True},
        {"name": "FIRST_NAME", "type": "VARCHAR2(20)", "nullable": True, "pk": False},
        {"name": "LAST_NAME", "type": "VARCHAR2(25)", "nullable": False, "pk": False},
        {"name": "EMAIL", "type": "VARCHAR2(25)", "nullable": False, "pk": False},
        {"name": "PHONE_NUMBER", "type": "VARCHAR2(20)", "nullable": True, "pk": False},
        {"name": "HIRE_DATE", "type": "DATE", "nullable": False, "pk": False},
        {"name": "JOB_ID", "type": "VARCHAR2(10)", "nullable": False, "pk": False},
        {"name": "SALARY", "type": "NUMBER(8,2)", "nullable": True, "pk": False},
        {
            "name": "COMMISSION_PCT",
            "type": "NUMBER(2,2)",
            "nullable": True,
            "pk": False,
        },
        {"name": "MANAGER_ID", "type": "NUMBER(6)", "nullable": True, "pk": False},
        {"name": "DEPARTMENT_ID", "type": "NUMBER(4)", "nullable": True, "pk": False},
    ],
}

MOCK_PG_COLUMNS = {
    "employees": [
        {"name": "id", "type": "SERIAL", "nullable": False, "pk": True},
        {"name": "first_name", "type": "VARCHAR(50)", "nullable": True, "pk": False},
        {"name": "last_name", "type": "VARCHAR(100)", "nullable": False, "pk": False},
        {"name": "email", "type": "VARCHAR(150)", "nullable": False, "pk": False},
        {"name": "phone", "type": "VARCHAR(30)", "nullable": True, "pk": False},
        {"name": "hire_date", "type": "DATE", "nullable": False, "pk": False},
        {"name": "job_code", "type": "VARCHAR(20)", "nullable": True, "pk": False},
        {"name": "salary", "type": "NUMERIC(10,2)", "nullable": True, "pk": False},
        {"name": "dept_id", "type": "INTEGER", "nullable": True, "pk": False},
        {"name": "created_at", "type": "TIMESTAMPTZ", "nullable": False, "pk": False},
    ],
}


def get_oracle_connection():
    """Try to get real Oracle connection, return None if unavailable."""
    try:
        import oracledb
        from django.conf import settings

        # Thick mode required for older Oracle DB versions (pre-12.1)
        # Set ORACLE_CLIENT_DIR to your Instant Client path, or leave blank to
        # let oracledb find it via PATH / LD_LIBRARY_PATH
        client_dir = os.environ.get("ORACLE_CLIENT_DIR", "C:\oracle\instantclient_23_0")
        try:
            if client_dir:
                oracledb.init_oracle_client(lib_dir=client_dir)
            else:
                oracledb.init_oracle_client()  # finds via PATH
        except Exception:
            pass  # already initialized in this process — safe to ignore

        db = settings.DATABASES["oracle_source"]
        conn = oracledb.connect(
            user=db["USER"],
            password=db["PASSWORD"],
            dsn=db["NAME"],
        )
        return conn
    except Exception as e:
        logger.warning(f"Oracle connection failed: {e}")
        return None


def get_postgres_connection():
    """Try to get real PostgreSQL connection, return None if unavailable."""
    try:
        import psycopg2
        from django.conf import settings

        db = settings.DATABASES["postgres_target"]
        options = db.get("options", "")
        conn = psycopg2.connect(
            dbname=db["NAME"],
            user=db["USER"],
            password=db["PASSWORD"],
            host=db["HOST"],
            port=db["PORT"],
            options=options,
        )
        return conn
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")
        return None


def test_connection(db_type):
    """Test DB connection. Returns (success, message)."""
    if db_type == "oracle":
        conn = get_oracle_connection()
        if conn:
            conn.close()
            return True, "Oracle connection successful"
        return False, "Cannot connect to Oracle (using mock data)"
    elif db_type == "postgres":
        conn = get_postgres_connection()
        if conn:
            conn.close()
            return True, "PostgreSQL connection successful"
        return False, "Cannot connect to PostgreSQL (using mock data)"
    return False, "Unknown database type"


def list_oracle_tables():
    """List tables from Oracle or return mock data."""
    conn = get_oracle_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.table_name, t.num_rows, t.owner
                FROM all_tables t
                WHERE t.owner NOT IN ('SYS','SYSTEM','DBSNMP','SYSMAN','OUTLN','MDSYS',
                    'ORDSYS','EXFSYS','DMSYS','WMSYS','CTXSYS','ANONYMOUS','XDB','ORDPLUGINS',
                    'SI_INFORMTN_SCHEMA','OLAPSYS','MDDATA','IX','ORACLE_OCM','DIP','TSMSYS')
                ORDER BY t.owner, t.table_name
            """)
            rows = cursor.fetchall()
            return [{"name": r[0], "rows": r[1] or 0, "schema": r[2]} for r in rows]
        except Exception as e:
            logger.error(f"Oracle table listing error: {e}")
        finally:
            conn.close()
    return MOCK_ORACLE_TABLES


def list_postgres_tables():
    """List tables from a specific PostgreSQL schema."""

    conn = get_postgres_connection()

    PG_SCHEMA = os.getenv("PG_SCHEMA", "agrobiotic")

    if conn:
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    t.table_name,
                    COALESCE(s.n_live_tup, 0) AS rows,
                    t.table_schema
                FROM information_schema.tables t
                LEFT JOIN pg_stat_user_tables s 
                    ON s.relname = t.table_name
                WHERE t.table_schema = %s
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name
            """,
                (PG_SCHEMA,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "name": r[0],
                    "rows": r[1],
                    "schema": r[2],
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"PostgreSQL table listing error: {e}")

        finally:
            conn.close()

    return MOCK_PG_TABLES


def get_oracle_columns(table_name):
    """Get columns for Oracle table."""
    conn = get_oracle_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.column_name, c.data_type || 
                    CASE WHEN c.data_precision IS NOT NULL 
                         THEN '(' || c.data_precision || CASE WHEN c.data_scale > 0 THEN ',' || c.data_scale ELSE '' END || ')'
                         WHEN c.char_length > 0 THEN '(' || c.char_length || ')'
                         ELSE '' END as full_type,
                    c.nullable,
                    CASE WHEN pk.column_name IS NOT NULL THEN 'Y' ELSE 'N' END as is_pk
                FROM all_tab_columns c
                LEFT JOIN (
                    SELECT cc.column_name FROM all_cons_columns cc
                    JOIN all_constraints con ON con.constraint_name = cc.constraint_name
                    WHERE con.constraint_type = 'P' AND con.table_name = :tbl
                ) pk ON pk.column_name = c.column_name
                WHERE c.table_name = :tbl
                ORDER BY c.column_id
            """,
                tbl=table_name.upper(),
            )
            rows = cursor.fetchall()
            return [
                {"name": r[0], "type": r[1], "nullable": r[2] == "Y", "pk": r[3] == "Y"}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Oracle column error: {e}")
        finally:
            conn.close()
    return MOCK_ORACLE_COLUMNS.get(table_name.upper(), [])


def get_postgres_columns(table_name, schema=None):
    """Get columns for PostgreSQL table (schema-aware)."""

    conn = get_postgres_connection()

    PG_SCHEMA = schema or os.getenv("PG_SCHEMA", "agrobiotic")

    if conn:
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    c.column_name,

                    c.udt_name || 
                    CASE 
                        WHEN c.character_maximum_length IS NOT NULL 
                            THEN '(' || c.character_maximum_length || ')'
                        WHEN c.numeric_precision IS NOT NULL 
                             AND c.numeric_scale IS NOT NULL
                            THEN '(' || c.numeric_precision || ',' || c.numeric_scale || ')'
                        ELSE ''
                    END AS data_type,

                    c.is_nullable,

                    CASE 
                        WHEN pk.column_name IS NOT NULL THEN true 
                        ELSE false 
                    END AS is_pk

                FROM information_schema.columns c

                LEFT JOIN (
                    SELECT ku.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage ku
                        ON ku.constraint_name = tc.constraint_name
                        AND ku.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                      AND tc.table_name = %s
                      AND tc.table_schema = %s
                ) pk 
                ON pk.column_name = c.column_name

                WHERE c.table_name = %s
                  AND c.table_schema = %s

                ORDER BY c.ordinal_position
            """,
                (table_name.lower(), PG_SCHEMA, table_name.lower(), PG_SCHEMA),
            )

            rows = cursor.fetchall()

            return [
                {
                    "name": r[0],
                    "type": r[1],
                    "nullable": r[2] == "YES",
                    "pk": r[3],
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"PostgreSQL column error: {e}")

        finally:
            conn.close()

    return MOCK_PG_COLUMNS.get(table_name.lower(), [])


def execute_migration(config):
    """
    Execute migration based on config:
    {
      source_table, target_table,
      mappings: [{source_col, target_col, default_value}],
      batch_size, truncate_target
    }
    Returns migration result dict.
    """
    PG_SCHEMA = os.getenv("PG_SCHEMA", "agrobiotic")
    source_table = config["source_table"]
    target_table = config["target_table"]
    mappings = config["mappings"]
    batch_size = config.get("batch_size", 1000)
    truncate_target = config.get("truncate_target", False)

    table_ref = f'"{PG_SCHEMA}"."{target_table}"'

    src_conn = get_oracle_connection()
    tgt_conn = get_postgres_connection()

    using_mock = src_conn is None or tgt_conn is None

    if using_mock:
        # Simulate migration result
        import time, random

        time.sleep(0.5)
        oracle_table = MOCK_ORACLE_TABLES
        row_count = next(
            (t["rows"] for t in oracle_table if t["name"] == source_table.upper()), 100
        )
        return {
            "success": True,
            "mode": "simulation",
            "rows_read": row_count,
            "rows_written": row_count,
            "rows_failed": 0,
            "duration_seconds": round(random.uniform(1.2, 8.5), 2),
            "batches": max(1, row_count // batch_size),
            "message": f"Simulation complete. {row_count} rows would be migrated from Oracle:{source_table} to PostgreSQL:{target_table}",
        }

    # Real migration
    start = datetime.now()
    rows_read = rows_written = rows_failed = 0
    errors = []

    try:
        src_cursor = src_conn.cursor()
        tgt_cursor = tgt_conn.cursor()

        pg_columns = get_postgres_columns(target_table)
        pg_type_map = {c["name"]: c["type"] for c in pg_columns}

        if truncate_target:
            tgt_cursor.execute(f"TRUNCATE TABLE {table_ref}")
            tgt_conn.commit()

        # Build SELECT
        src_cols = [m["source_col"] for m in mappings if m.get("source_col")]
        select_sql = f"SELECT {', '.join(src_cols)} FROM {source_table}"
        src_cursor.execute(select_sql)

        # Build INSERT
        tgt_cols = [m["target_col"] for m in mappings]
        placeholders = ", ".join(["%s"] * len(tgt_cols))
        insert_sql = f"""INSERT INTO {table_ref} ({', '.join(f'"{c}"' for c in tgt_cols)})
                        VALUES ({placeholders})"""

        batch = []
        while True:
            rows = src_cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                rows_read += 1
                try:
                    values = []
                    src_idx = 0
                    for m in mappings:
                        col = m["target_col"]
                        pg_type = pg_type_map.get(col)
                        if m.get("source_col"):

                            raw = row[src_idx]
                            src_idx += 1
                            converted = convert_value(raw, pg_type)
                            if converted == "":
                                converted = None
                            values.append(converted)
                        else:
                            converted = convert_value(m.get("default_value"), pg_type)
                            if converted == "":
                                converted = None
                            values.append(converted)

                    batch.append(sanitize_values(values))

                except Exception as e:
                    rows_failed += 1
                    errors.append(str(e))

            if batch:
                tgt_cursor.executemany(insert_sql, batch)
                tgt_conn.commit()
                rows_written += len(batch)
                batch = []

        duration = (datetime.now() - start).total_seconds()
        return {
            "success": True,
            "mode": "live",
            "rows_read": rows_read,
            "rows_written": rows_written,
            "rows_failed": rows_failed,
            "duration_seconds": round(duration, 2),
            "batches": max(1, rows_read // batch_size),
            "errors": errors[:10],
            "message": f"Migration complete: {rows_written} rows written to {target_table}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rows_read": rows_read,
            "rows_written": rows_written,
        }
    finally:
        if src_conn:
            src_conn.close()
        if tgt_conn:
            tgt_conn.close()


def sanitize_values(values):
    cleaned = []

    for v in values:
        # convert empty strings to NULL
        if v == "" or v == " ":
            v = None

        # extra safety cleanup
        if isinstance(v, str):
            v = v.strip()
            if v.lower() in ["null", "none", "nan", ""]:
                v = None

        cleaned.append(v)

    return tuple(cleaned)


def convert_value(value, pg_type):
    """
    Safe and robust Oracle → PostgreSQL value converter.
    Handles dirty data, type mismatch, and edge cases.
    """

    # ─────────────────────────────
    # NULL / EMPTY CLEANUP
    # ─────────────────────────────
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if value == "" or value.lower() in ["null", "none", "nan"]:
            return None

    pg_type = (pg_type or "").upper().strip()

    try:
        # ─────────────────────────────
        # TEXT / STRING TYPES
        # ─────────────────────────────
        if any(
            t in pg_type
            for t in ["CHAR", "TEXT", "CLOB", "UUID", "JSON", "JSONB", "XML"]
        ):
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value)

        # ─────────────────────────────
        # UUID
        # ─────────────────────────────
        if "UUID" in pg_type:
            try:
                return str(uuid.UUID(str(value)))
            except:
                return None

        # ─────────────────────────────
        # INTEGER TYPES
        # ─────────────────────────────
        if any(t in pg_type for t in ["BIGINT", "INT8"]):
            try:
                return int(float(value))
            except:
                return None

        if any(t in pg_type for t in ["INTEGER", "INT", "INT4", "SMALLINT"]):
            try:
                return int(float(value))
            except:
                return None

        # ─────────────────────────────
        # NUMERIC / FLOAT TYPES
        # ─────────────────────────────
        if any(
            t in pg_type
            for t in ["NUMERIC", "DECIMAL", "FLOAT", "REAL", "DOUBLE", "MONEY"]
        ):
            try:
                val = float(value)
                if math.isnan(val) or math.isinf(val):
                    return None
                return val
            except:
                return None

        # ─────────────────────────────
        # BOOLEAN
        # ─────────────────────────────
        if "BOOL" in pg_type:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value == 1
            if isinstance(value, str):
                return value.lower() in ["1", "true", "t", "yes", "y"]
            return False

        # ─────────────────────────────
        # DATE
        # ─────────────────────────────
        if pg_type == "DATE":
            if isinstance(value, date) and not isinstance(value, datetime):
                return value
            if isinstance(value, datetime):
                return value.date()
            try:
                return datetime.fromisoformat(str(value)).date()
            except:
                return None

        # ─────────────────────────────
        # TIMESTAMP / DATETIME
        # ─────────────────────────────
        if any(t in pg_type for t in ["TIMESTAMP", "DATETIME"]):
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            try:
                return datetime.fromisoformat(str(value))
            except:
                return None

        # ─────────────────────────────
        # JSON SAFE (fallback detection)
        # ─────────────────────────────
        if isinstance(value, (dict, list)):
            return json.dumps(value)

        # ─────────────────────────────
        # DEFAULT SAFE STRING
        # ─────────────────────────────
        return value

    except Exception:
        return None
