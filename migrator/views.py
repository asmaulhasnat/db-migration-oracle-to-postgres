import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from . import db_utils


def index(request):
    return render(request, "migrator/index.html")


@require_http_methods(["GET"])
def test_connections(request):
    oracle_ok, oracle_msg = db_utils.test_connection("oracle")
    pg_ok, pg_msg = db_utils.test_connection("postgres")
    return JsonResponse(
        {
            "oracle": {"connected": oracle_ok, "message": oracle_msg},
            "postgres": {"connected": pg_ok, "message": pg_msg},
        }
    )


@require_http_methods(["GET"])
def list_tables(request):
    db = request.GET.get("db", "oracle")
    if db == "oracle":
        tables = db_utils.list_oracle_tables()
    else:
        tables = db_utils.list_postgres_tables()
    return JsonResponse({"tables": tables})


@require_http_methods(["GET"])
def get_columns(request):
    db = request.GET.get("db", "oracle")
    table = request.GET.get("table", "")
    if not table:
        return JsonResponse({"error": "table parameter required"}, status=400)
    if db == "oracle":
        columns = db_utils.get_oracle_columns(table)
    else:
        columns = db_utils.get_postgres_columns(table)
    return JsonResponse({"columns": columns, "table": table, "db": db})


@csrf_exempt
@require_http_methods(["POST"])
def run_migration(request):
    try:
        config = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    required = ["source_table", "target_table", "mappings"]
    for field in required:
        if field not in config:
            return JsonResponse({"error": f"Missing field: {field}"}, status=400)

    if not config["mappings"]:
        return JsonResponse(
            {"error": "At least one column mapping is required"}, status=400
        )

    result = db_utils.execute_migration(config)
    status_code = 200 if result.get("success") else 500
    return JsonResponse(result, status=status_code)


@csrf_exempt
@require_http_methods(["POST"])
def preview_migration(request):
    """Preview first N rows of migration without writing."""
    try:
        config = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    source_table = config.get("source_table", "")
    mappings = config.get("mappings", [])
    limit = min(config.get("limit", 10), 50)

    # Build mock preview
    oracle_cols = db_utils.get_oracle_columns(source_table)
    preview_rows = []
    for i in range(min(limit, 5)):
        row = {}
        for m in mappings:
            if m.get("source_col"):
                src = next(
                    (c for c in oracle_cols if c["name"] == m["source_col"]), None
                )
                if src:
                    t = src["type"].upper()
                    if "NUMBER" in t or "INT" in t:
                        row[m["target_col"]] = (i + 1) * 100
                    elif "DATE" in t or "TIME" in t:
                        row[m["target_col"]] = "2024-01-15"
                    else:
                        row[m["target_col"]] = f'sample_{m["source_col"].lower()}_{i+1}'
            else:
                row[m["target_col"]] = m.get("default_value", None)
        preview_rows.append(row)

    return JsonResponse(
        {
            "preview": preview_rows,
            "columns": [m["target_col"] for m in mappings],
            "note": "Preview shows sample data. Actual values depend on your Oracle source.",
        }
    )
