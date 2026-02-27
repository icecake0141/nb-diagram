CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    upload_path TEXT NOT NULL,
    graph_path TEXT NOT NULL,
    rows_path TEXT NOT NULL,
    node_count INTEGER NOT NULL,
    edge_count INTEGER NOT NULL,
    columns_json TEXT NOT NULL,
    type_legend_json TEXT NOT NULL
);
