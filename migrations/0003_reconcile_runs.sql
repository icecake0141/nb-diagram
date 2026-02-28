CREATE TABLE IF NOT EXISTS reconcile_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    import_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    method TEXT NOT NULL,
    seed_device TEXT NOT NULL,
    params_json TEXT NOT NULL,
    report_json TEXT,
    error_message TEXT,
    FOREIGN KEY(import_id) REFERENCES import_runs(id)
);
