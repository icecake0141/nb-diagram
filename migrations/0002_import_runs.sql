CREATE TABLE IF NOT EXISTS import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    status TEXT NOT NULL,
    upload_path TEXT NOT NULL,
    suggested_mapping_json TEXT NOT NULL,
    mapping_json TEXT NOT NULL,
    result_id INTEGER,
    error_message TEXT,
    FOREIGN KEY(result_id) REFERENCES results(id)
);

CREATE TABLE IF NOT EXISTS column_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    header_signature TEXT NOT NULL,
    mapping_json TEXT NOT NULL
);
