from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sqlite3
import uuid
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from nbcart.exporters.drawio import build_drawio_xml
from nbcart.graph import build_device_graph, build_graph, list_racks
from nbcart.ingest import normalize_color, parse_cables_csv
from nbcart.models import CableRow

__all__ = [
    "app",
    "create_app",
    "CableRow",
    "build_device_graph",
    "build_drawio_xml",
    "init_storage",
    "normalize_color",
    "parse_cables_csv",
    "resolve_data_path",
]

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
DB_PATH = DATA_DIR / "results.db"
MIGRATIONS_DIR = BASE_DIR / "migrations"
OPENAPI_PATH = BASE_DIR / "docs" / "openapi.yaml"


def list_migrations() -> list[Path]:
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied = {r[0] for r in con.execute("SELECT version FROM schema_migrations").fetchall()}
    for migration in list_migrations():
        version = migration.name
        if version in applied:
            continue
        con.executescript(migration.read_text(encoding="utf-8"))
        con.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, dt.datetime.now().isoformat(timespec="seconds")),
        )


def init_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    RESULT_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        apply_migrations(con)
        con.commit()


def resolve_data_path(rel_path: str) -> Path:
    path = (DATA_DIR / rel_path).resolve()
    if DATA_DIR.resolve() not in path.parents and path != DATA_DIR.resolve():
        raise ValueError("Invalid path.")
    return path


def read_headers(file_bytes: bytes) -> list[str]:
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = file_bytes.decode("utf-8", errors="ignore")

    reader = csv.DictReader(io.StringIO(text))
    return list(reader.fieldnames or [])


def mapping_signature(headers: list[str]) -> str:
    normalized = [h.strip().lower() for h in headers if h.strip()]
    return "|".join(normalized)


def store_result(
    *,
    original_filename: str,
    file_bytes: bytes,
    rows: list[CableRow],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    columns: dict[str, str | None],
    type_legend: list[dict[str, Any]],
) -> int:
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    safe_name = secure_filename(original_filename) or "upload.csv"
    upload_rel = Path("uploads") / f"{stamp}_{suffix}_{safe_name}"
    graph_rel = Path("results") / f"{stamp}_{suffix}_graph.json"
    rows_rel = Path("results") / f"{stamp}_{suffix}_rows.json"

    (DATA_DIR / upload_rel).write_bytes(file_bytes)
    (DATA_DIR / graph_rel).write_text(
        json.dumps(nodes + edges, ensure_ascii=False), encoding="utf-8"
    )
    (DATA_DIR / rows_rel).write_text(
        json.dumps([asdict(r) for r in rows], ensure_ascii=False), encoding="utf-8"
    )

    created_at = dt.datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """
            INSERT INTO results (
                created_at, original_filename, upload_path, graph_path, rows_path,
                node_count, edge_count, columns_json, type_legend_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                original_filename,
                str(upload_rel),
                str(graph_rel),
                str(rows_rel),
                len(nodes),
                len(edges),
                json.dumps(columns, ensure_ascii=False),
                json.dumps(type_legend, ensure_ascii=False),
            ),
        )
        con.commit()
        row_id = cur.lastrowid
        if row_id is None:
            raise RuntimeError("Failed to persist result row.")
        return int(row_id)


def list_recent_results(limit: int = 20) -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT id, created_at, original_filename, node_count, edge_count
            FROM results
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_result(result_id: int) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM results WHERE id = ?", (result_id,)).fetchone()
    return dict(row) if row else None


def get_import_run(import_id: int) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM import_runs WHERE id = ?", (import_id,)).fetchone()
    return dict(row) if row else None


def update_import_run(import_id: int, **fields: Any) -> None:
    if not fields:
        return
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = [fields[k] for k in fields]
    values.append(import_id)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE import_runs SET {columns} WHERE id = ?", values)
        con.commit()


def create_import_run(
    original_filename: str,
    file_bytes: bytes,
) -> tuple[int, dict[str, str | None], list[str], list[str]]:
    created_at = dt.datetime.now().isoformat(timespec="seconds")
    safe_name = secure_filename(original_filename) or "upload.csv"

    rows, suggested = parse_cables_csv(file_bytes)
    headers = read_headers(file_bytes)

    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """
            INSERT INTO import_runs (
                created_at, original_filename, status, upload_path,
                suggested_mapping_json, mapping_json, result_id, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                created_at,
                original_filename,
                "uploaded",
                "",
                json.dumps(suggested, ensure_ascii=False),
                json.dumps(suggested, ensure_ascii=False),
            ),
        )
        import_id_raw = cur.lastrowid
        if import_id_raw is None:
            raise RuntimeError("Failed to persist import_runs row.")
        import_id = int(import_id_raw)
        upload_rel = Path("uploads") / f"import_{import_id}_{uuid.uuid4().hex[:8]}_{safe_name}"
        (DATA_DIR / upload_rel).write_bytes(file_bytes)
        con.execute(
            "UPDATE import_runs SET upload_path = ? WHERE id = ?",
            (str(upload_rel), import_id),
        )

        con.execute(
            (
                "INSERT INTO column_mappings "
                "(created_at, header_signature, mapping_json) VALUES (?, ?, ?)"
            ),
            (created_at, mapping_signature(headers), json.dumps(suggested, ensure_ascii=False)),
        )
        con.commit()

    missing = [
        name
        for name, col in suggested.items()
        if col is None and name in {"a_device", "a_port", "b_device", "b_port"}
    ]
    if not rows:
        update_import_run(import_id, status="needs_mapping")
    return import_id, suggested, missing, headers


def get_run_headers(run: dict[str, Any]) -> list[str]:
    upload_path = resolve_data_path(run["upload_path"])
    if not upload_path.exists():
        return []
    return read_headers(upload_path.read_bytes())


def build_summary(rows: list[CableRow], columns: dict[str, str | None]) -> dict[str, Any]:
    nodes, edges = build_graph(rows)
    device_nodes, device_edges = build_device_graph(rows)
    missing = [
        name
        for name, col in columns.items()
        if col is None and name in {"a_device", "a_port", "b_device", "b_port"}
    ]

    type_counter = Counter(r.cable_type for r in rows)
    legend_map: dict[str, str] = {}
    for r in rows:
        legend_map.setdefault(r.cable_type, r.cable_color)
    type_legend = [
        {"type": cable_type, "count": count, "color": legend_map.get(cable_type, "#64748b")}
        for cable_type, count in type_counter.most_common()
    ]

    endpoint_kind_counter = Counter([r.a_kind for r in rows] + [r.b_kind for r in rows])
    kind_labels = {
        "interface": "Interface",
        "front_port": "FrontPort",
        "rear_port": "RearPort",
        "circuit_termination": "CircuitTermination",
        "power_port": "PowerPort",
        "power_outlet": "PowerOutlet",
        "power_feed": "PowerFeed",
    }
    node_legend = [
        {"kind": kind, "label": kind_labels.get(kind, kind), "count": count}
        for kind, count in endpoint_kind_counter.most_common()
    ]

    return {
        "rows": rows,
        "columns": columns,
        "nodes": nodes,
        "edges": edges,
        "device_nodes": device_nodes,
        "device_edges": device_edges,
        "missing": missing,
        "type_legend": type_legend,
        "node_legend": node_legend,
    }


def execute_import(import_id: int) -> tuple[int, dict[str, Any]]:
    run = get_import_run(import_id)
    if not run:
        raise ValueError("Import not found")
    upload_path = resolve_data_path(run["upload_path"])
    if not upload_path.exists():
        update_import_run(import_id, status="failed", error_message="Upload file not found")
        raise FileNotFoundError("Upload file not found")

    mapping = json.loads(run.get("mapping_json") or "{}")
    file_bytes = upload_path.read_bytes()
    rows, columns = parse_cables_csv(file_bytes, mapping)
    if not rows:
        update_import_run(
            import_id,
            status="failed",
            error_message="No connection data could be extracted with current mapping.",
        )
        raise ValueError("No connection data could be extracted with current mapping.")

    summary = build_summary(rows, columns)
    result_id = store_result(
        original_filename=run["original_filename"],
        file_bytes=file_bytes,
        rows=rows,
        nodes=summary["nodes"],
        edges=summary["edges"],
        columns=columns,
        type_legend=summary["type_legend"],
    )
    update_import_run(import_id, status="completed", result_id=result_id, error_message=None)
    return result_id, summary


def build_upload_context(file_bytes: bytes) -> dict[str, Any]:
    rows, columns = parse_cables_csv(file_bytes)
    return build_summary(rows, columns)


def create_app() -> Flask:
    flask_app = Flask(__name__)
    flask_app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    @flask_app.get("/")
    def index() -> str:
        return render_template("index.html", recent_results=list_recent_results())

    @flask_app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_: RequestEntityTooLarge):
        return (
            render_template(
                "index.html",
                error="Uploaded file is too large. Maximum size is 5 MiB.",
                recent_results=list_recent_results(),
            ),
            413,
        )

    @flask_app.post("/upload")
    def upload() -> Any:
        return (
            render_template(
                "index.html",
                error="Legacy /upload is deprecated. Please use the API workflow on this page.",
                recent_results=list_recent_results(),
            ),
            410,
        )

    @flask_app.get("/result/<int:result_id>")
    def result_detail(result_id: int) -> str:
        record = get_result(result_id)
        if not record:
            abort(404)

        graph_path = resolve_data_path(record["graph_path"])
        rows_path = resolve_data_path(record["rows_path"])
        if not graph_path.exists() or not rows_path.exists():
            abort(404)

        graph_json = json.loads(graph_path.read_text(encoding="utf-8"))
        row_items = json.loads(rows_path.read_text(encoding="utf-8"))
        rows = [CableRow(**item) for item in row_items]
        device_nodes, device_edges = build_device_graph(rows)
        columns = json.loads(record["columns_json"])
        type_legend = json.loads(record["type_legend_json"])
        missing = [
            name
            for name, col in columns.items()
            if col is None and name in {"a_device", "a_port", "b_device", "b_port"}
        ]
        endpoint_kind_counter = Counter([r.a_kind for r in rows] + [r.b_kind for r in rows])
        kind_labels = {
            "interface": "Interface",
            "front_port": "FrontPort",
            "rear_port": "RearPort",
            "circuit_termination": "CircuitTermination",
            "power_port": "PowerPort",
            "power_outlet": "PowerOutlet",
            "power_feed": "PowerFeed",
        }
        node_legend = [
            {"kind": kind, "label": kind_labels.get(kind, kind), "count": count}
            for kind, count in endpoint_kind_counter.most_common()
        ]

        return render_template(
            "index.html",
            graph_json=graph_json,
            device_graph_json=device_nodes + device_edges,
            rack_options=list_racks(rows),
            rows=rows,
            node_count=record["node_count"],
            edge_count=record["edge_count"],
            device_node_count=len(device_nodes),
            device_edge_count=len(device_edges),
            columns=columns,
            missing=missing,
            type_legend=type_legend,
            node_legend=node_legend,
            result_id=result_id,
            recent_results=list_recent_results(),
        )

    @flask_app.get("/files/<int:result_id>/<kind>")
    def download_file(result_id: int, kind: str):
        record = get_result(result_id)
        if not record:
            abort(404)

        if kind == "csv":
            path = resolve_data_path(record["upload_path"])
            download_name = record["original_filename"] or f"result-{result_id}.csv"
        elif kind == "graph":
            path = resolve_data_path(record["graph_path"])
            download_name = f"result-{result_id}-graph.json"
        elif kind == "drawio":
            rows_path = resolve_data_path(record["rows_path"])
            if not rows_path.exists():
                abort(404)
            row_items = json.loads(rows_path.read_text(encoding="utf-8"))
            rows = [CableRow(**item) for item in row_items]
            device_nodes, device_edges = build_device_graph(rows)
            drawio_xml = build_drawio_xml(
                device_nodes + device_edges, diagram_name=f"Result-{result_id}"
            )
            return send_file(
                io.BytesIO(drawio_xml.encode("utf-8")),
                as_attachment=True,
                download_name=f"result-{result_id}-diagram.drawio",
                mimetype="application/xml",
            )
        else:
            abort(404)

        if not path.exists():
            abort(404)
        return send_file(path, as_attachment=True, download_name=download_name)

    @flask_app.post("/api/imports")
    def api_create_import():
        file = request.files.get("csv_file")
        if not file or not file.filename:
            return jsonify({"error": "csv_file is required."}), 400

        file_bytes = file.read()
        try:
            import_id, suggested, missing, headers = create_import_run(file.filename, file_bytes)
            return (
                jsonify(
                    {
                        "import_id": import_id,
                        "filename": file.filename,
                        "status": "uploaded",
                        "headers": headers,
                        "mapping_candidates": suggested,
                        "missing": missing,
                    }
                ),
                201,
            )
        except Exception as exc:
            return jsonify({"error": f"Failed to create import: {exc}"}), 400

    @flask_app.put("/api/imports/<int:import_id>/mapping")
    def api_set_mapping(import_id: int):
        run = get_import_run(import_id)
        if not run:
            return jsonify({"error": "Import not found."}), 404

        payload = request.get_json(silent=True) or {}
        mapping = payload.get("mapping")
        if not isinstance(mapping, dict):
            return jsonify({"error": "mapping object is required."}), 400

        upload_path = resolve_data_path(run["upload_path"])
        if not upload_path.exists():
            return jsonify({"error": "Upload file not found."}), 404

        try:
            _, sanitized = parse_cables_csv(upload_path.read_bytes(), mapping)
        except Exception as exc:
            return jsonify({"error": f"Invalid mapping: {exc}"}), 400

        missing = [
            name
            for name, col in sanitized.items()
            if col is None and name in {"a_device", "a_port", "b_device", "b_port"}
        ]
        status = "mapped" if not missing else "needs_mapping"
        update_import_run(
            import_id,
            mapping_json=json.dumps(sanitized, ensure_ascii=False),
            status=status,
        )
        return jsonify(
            {
                "import_id": import_id,
                "status": status,
                "mapping": sanitized,
                "missing": missing,
            }
        )

    @flask_app.post("/api/imports/<int:import_id>/execute")
    def api_execute_import(import_id: int):
        run = get_import_run(import_id)
        if not run:
            return jsonify({"error": "Import not found."}), 404

        if run["status"] == "completed" and run.get("result_id"):
            return jsonify(
                {
                    "import_id": import_id,
                    "status": "completed",
                    "result_id": run["result_id"],
                }
            )

        try:
            result_id, summary = execute_import(import_id)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 422

        return jsonify(
            {
                "import_id": import_id,
                "status": "completed",
                "result_id": result_id,
                "row_count": len(summary["rows"]),
                "node_count": len(summary["nodes"]),
                "edge_count": len(summary["edges"]),
            }
        )

    @flask_app.get("/api/imports/<int:import_id>")
    def api_get_import(import_id: int):
        run = get_import_run(import_id)
        if not run:
            return jsonify({"error": "Import not found."}), 404

        out: dict[str, Any] = {
            "import_id": import_id,
            "created_at": run["created_at"],
            "filename": run["original_filename"],
            "status": run["status"],
            "headers": get_run_headers(run),
            "mapping_candidates": json.loads(run.get("suggested_mapping_json") or "{}"),
            "mapping": json.loads(run.get("mapping_json") or "{}"),
            "error": run.get("error_message"),
            "result_id": run.get("result_id"),
        }
        if run.get("result_id"):
            result = get_result(int(run["result_id"]))
            if result:
                out.update(
                    {
                        "node_count": result["node_count"],
                        "edge_count": result["edge_count"],
                        "columns": json.loads(result["columns_json"]),
                        "type_legend": json.loads(result["type_legend_json"]),
                    }
                )
                rows_path = resolve_data_path(result["rows_path"])
                if rows_path.exists():
                    out["row_count"] = len(json.loads(rows_path.read_text(encoding="utf-8")))
        return jsonify(out)

    @flask_app.get("/api/graphs/<int:import_id>")
    def api_get_graph(import_id: int):
        view = request.args.get("view", "device")
        run = get_import_run(import_id)
        if not run:
            return jsonify({"error": "Import not found."}), 404
        if run["status"] != "completed" or not run.get("result_id"):
            return jsonify({"error": "Import is not completed."}), 409

        result = get_result(int(run["result_id"]))
        if not result:
            return jsonify({"error": "Result not found."}), 404

        if view == "interface":
            graph_path = resolve_data_path(result["graph_path"])
            if not graph_path.exists():
                return jsonify({"error": "Graph file missing."}), 404
            return jsonify(
                {
                    "import_id": import_id,
                    "view": "interface",
                    "elements": json.loads(graph_path.read_text(encoding="utf-8")),
                }
            )

        rows_path = resolve_data_path(result["rows_path"])
        if not rows_path.exists():
            return jsonify({"error": "Rows file missing."}), 404
        rows = [CableRow(**item) for item in json.loads(rows_path.read_text(encoding="utf-8"))]
        device_nodes, device_edges = build_device_graph(rows)
        return jsonify(
            {
                "import_id": import_id,
                "view": "device",
                "elements": device_nodes + device_edges,
            }
        )

    @flask_app.get("/api/exports/<int:import_id>")
    def api_export(import_id: int):
        fmt = request.args.get("format", "json")
        run = get_import_run(import_id)
        if not run:
            return jsonify({"error": "Import not found."}), 404
        if run["status"] != "completed" or not run.get("result_id"):
            return jsonify({"error": "Import is not completed."}), 409

        result_id = int(run["result_id"])
        if fmt == "csv":
            return download_file(result_id, "csv")
        if fmt == "drawio":
            return download_file(result_id, "drawio")
        if fmt == "json":
            return download_file(result_id, "graph")
        return jsonify({"error": "Unsupported format."}), 400

    @flask_app.get("/api/openapi.yaml")
    def api_openapi():
        if not OPENAPI_PATH.exists():
            return jsonify({"error": "OpenAPI spec not found."}), 404
        return send_file(
            OPENAPI_PATH,
            mimetype="application/yaml",
            download_name="openapi.yaml",
        )

    return flask_app


init_storage()
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
