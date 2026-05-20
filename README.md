# DB Migrator — Oracle → PostgreSQL

A Django-based visual data migration system that lets you transfer data from an Oracle database to PostgreSQL through a browser UI — no scripting required.

Map source columns to target columns, set default values for unmatched fields, preview sample output, and run batched migrations with live progress and result stats.

---

## Features

- **Visual column mapping** — auto-maps Oracle → PostgreSQL columns by name; reassign via dropdowns
- **Default value support** — set fallback values for target columns with no Oracle source
- **Live connection status** — shows whether Oracle and PostgreSQL are reachable
- **Preview mode** — inspect sample output rows before committing
- **Batch processing** — configurable batch sizes for large tables
- **Truncate option** — optionally clear the target table before inserting
- **Simulation fallback** — works with mock data when databases are unreachable (dev/demo)
- **CLI command** — automate migrations via `manage.py migrate_table`
- **Detailed error reporting** — per-row error messages with column and raw value context

---

## Requirements

- Python 3.10+
- Oracle Instant Client (required for thick mode — older Oracle DB versions)
- Oracle DB (tested with Oracle 11g+)
- PostgreSQL 12+

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/asmaulhasnat/db-migration-oracle-to-postgres.git
cd db-migration-oracle-to-postgres
```

### 2. Check your Python version

```bash
python3 --version
# or on Windows
python --version
```

Requires Python 3.10 or higher.

### 3. Create a virtual environment

```bash
python3 -m venv venv
# or
python -m venv venv
```

### 4. Activate the virtual environment

```bash
# Linux / macOS
source venv/bin/activate

# Windows (Git Bash)
source venv/Scripts/activate

# Windows (CMD)
venv\Scripts\activate.bat
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Install Oracle Instant Client (required for older Oracle versions)

Download the **Basic Package** for your OS from:
https://www.oracle.com/database/technologies/instant-client/downloads.html

Extract it to a stable path, for example:

```
C:\oracle\instantclient_23_0        # Windows
/opt/oracle/instantclient_23_0      # Linux
```

Then set the environment variable:

```bash
# Linux / macOS
export ORACLE_CLIENT_DIR="/opt/oracle/instantclient_23_0"

# Windows (Git Bash)
export ORACLE_CLIENT_DIR="C:/oracle/instantclient_23_0"

# Windows (CMD)
set ORACLE_CLIENT_DIR=C:\oracle\instantclient_23_0
```

### 7. Configure your databases

Set these environment variables before running the server (or add them to a `.env` file):

```bash
# Oracle source
export ORACLE_DSN="192.168.0.144:1521/ORCL"
export ORACLE_USER="myuser"
export ORACLE_PASS="mypassword"
export ORACLE_CLIENT_DIR="/opt/oracle/instantclient_23_0"

# PostgreSQL target
export PG_HOST="localhost"
export PG_PORT="5432"
export PG_DB="target_db"
export PG_USER="postgres"
export PG_PASS="postgres"
export PG_SCHEMA="public"        # schema where your target tables live
```

Or edit the defaults directly in `config/settings.py` under `DATABASES`.

### 8. Run migrations

```bash
python manage.py migrate
```

### 9. Start the server

```bash
python manage.py runserver
```

Open your browser at: **http://127.0.0.1:8000**

---

## Using the Web UI

1. **Left panel** — browse Oracle or PostgreSQL tables; use the toggle to switch between them; use the search box to filter
2. **Select an Oracle table** — sets the migration source
3. **Select a PostgreSQL table** — sets the migration target; auto-mapping runs immediately
4. **Center panel** — review and adjust column mappings:
   - Matched columns are pre-selected by name similarity
   - Unmatched target columns show an enabled **default value** input
   - PK and NOT NULL badges warn you of constraint-critical columns
5. **Right panel** — configure options:
   - **Truncate target** — clears the table before inserting
   - **Batch size** — rows per transaction (default 1000)
   - **Stop on error** — abort migration on first row failure
6. **Preview** — see sample output for the first 5 rows before running
7. **Run Migration** — executes the migration with live progress and a result summary

---

## CLI Usage

Migrate a table directly from the terminal:

```bash
python manage.py migrate_table \
  --source EMPLOYEES \
  --target employees \
  --map EMPLOYEE_ID:id FIRST_NAME:first_name LAST_NAME:last_name \
        EMAIL:email HIRE_DATE:hire_date SALARY:salary \
  --default created_at:NOW() \
  --batch 500 \
  --truncate
```

| Argument | Description |
|---|---|
| `--source` | Oracle source table name (required) |
| `--target` | PostgreSQL target table name (required) |
| `--map` | Column mappings as `SOURCE:TARGET` pairs |
| `--default` | Default values as `TARGET_COL:VALUE` pairs |
| `--batch` | Batch size (default: 1000) |
| `--truncate` | Truncate the target table before migrating |

---

## API Reference

The web UI communicates with these endpoints — you can also call them directly:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/connections/` | Test Oracle and PostgreSQL connectivity |
| GET | `/api/tables/?db=oracle` | List Oracle tables |
| GET | `/api/tables/?db=pg` | List PostgreSQL tables |
| GET | `/api/columns/?db=oracle&table=NAME` | Get columns for an Oracle table |
| GET | `/api/columns/?db=pg&table=NAME` | Get columns for a PostgreSQL table |
| POST | `/api/preview/` | Preview sample migration output |
| POST | `/api/migrate/` | Execute a migration |

### Migration request body

```json
{
  "source_table": "EMPLOYEES",
  "target_table": "employees",
  "mappings": [
    { "source_col": "EMPLOYEE_ID", "target_col": "id",         "default_value": "" },
    { "source_col": "FIRST_NAME",  "target_col": "first_name", "default_value": "" },
    { "source_col": "",            "target_col": "created_at", "default_value": "NOW()" }
  ],
  "batch_size": 1000,
  "truncate_target": false
}
```

---

## Project Structure

```
db-migration-oracle-to-postgres/
├── config/
│   ├── settings.py                   # Dual DB config + Django settings
│   ├── urls.py                       # Root URL routing
│   └── wsgi.py
├── migrator/
│   ├── db_utils.py                   # Oracle/PG connections, introspection, migration engine
│   ├── views.py                      # REST API views
│   ├── urls.py                       # App URL routing
│   ├── management/
│   │   └── commands/
│   │       └── migrate_table.py      # CLI migration command
│   └── templates/
│       └── migrator/
│           └── index.html            # Web UI (single-page, no frontend build step)
├── requirements.txt
├── manage.py
└── README.md
```

---

## Dependency Notes

| Package | Purpose |
|---|---|
| `django` | Web framework and ORM |
| `oracledb` | Oracle DB driver (replaces deprecated `cx_Oracle`) |
| `psycopg2-binary` | PostgreSQL driver |
| `djangorestframework` | API response utilities |

> **Why `oracledb` and not `cx_Oracle`?**
> Oracle officially deprecated `cx_Oracle` in 2022. `oracledb` is the supported replacement. It runs in thin mode (no client needed) for Oracle 12.1+ and thick mode (Instant Client required) for older versions. This project uses thick mode to support Oracle 11g and earlier.

---

## Troubleshooting

**`DPY-3010` — connections not supported in thin mode**
Your Oracle server is older than 12.1. Install Oracle Instant Client and set `ORACLE_CLIENT_DIR`.

**`DPY-6005` — cannot connect to database**
Check that `ORACLE_DSN` is correct (`host:port/service_name`) and the Oracle listener is running.

**Zero rows inserted**
Run the debug script in the project root:
```bash
python debug_migration.py
```
This prints raw Oracle values, converted values, and flags any NOT NULL or PK columns resolving to NULL.

**`LookupError: No installed app with label 'admin'`**
Your `config/urls.py` still has `path('admin/', admin.site.urls)` but admin is not in `INSTALLED_APPS`. Remove that line from `urls.py`.

**`pkg_resources` / `cx_Oracle` build error**
Upgrade pip and setuptools, then use `oracledb` instead:
```bash
pip install --upgrade pip setuptools wheel
pip install oracledb
```

---

## Save requirements

After installing all packages:

```bash
pip freeze > requirements.txt
```

---

## License

MIT
