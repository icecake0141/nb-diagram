type DiffTab = "missing" | "unexpected" | "mismatched";

type ReconcileReport = {
  summary?: Record<string, unknown>;
  collection?: Record<string, unknown>;
  missing?: Array<Record<string, unknown>>;
  unexpected?: Array<Record<string, unknown>>;
  mismatched?: Array<Record<string, unknown>>;
};

function toJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

function csvEscape(value: unknown): string {
  const text = String(value ?? "");
  return `"${text.replace(/"/g, '""')}"`;
}

function downloadText(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}

export function initImportWorkflow() {
  const fileInput = document.getElementById("apiCsvFile") as HTMLInputElement | null;
  const createBtn = document.getElementById("apiCreateBtn");
  const statusEl = document.getElementById("apiImportStatus");
  const panel = document.getElementById("apiMappingPanel") as HTMLElement | null;
  const importIdEl = document.getElementById("apiImportId");
  const mappingEl = document.getElementById("apiMappingJson") as HTMLTextAreaElement | null;
  const saveBtn = document.getElementById("apiSaveMappingBtn");
  const executeBtn = document.getElementById("apiExecuteBtn");
  const refreshBtn = document.getElementById("apiRefreshBtn");
  const openResult = document.getElementById("apiOpenResult") as HTMLAnchorElement | null;
  const reconcileSeed = document.getElementById("reconcileSeedDevice") as HTMLInputElement | null;
  const reconcileHost = document.getElementById("reconcileSshHost") as HTMLInputElement | null;
  const reconcileUser = document.getElementById("reconcileSshUsername") as HTMLInputElement | null;
  const reconcileVendor = document.getElementById("reconcileSshVendor") as HTMLSelectElement | null;
  const reconcileCommand = document.getElementById(
    "reconcileSshCommand"
  ) as HTMLInputElement | null;
  const reconcileTimeout = document.getElementById(
    "reconcileSshTimeout"
  ) as HTMLInputElement | null;
  const reconcileBtn = document.getElementById("reconcileCompareBtn");
  const reconcileExportJsonBtn = document.getElementById("reconcileExportJsonBtn");
  const reconcileExportCsvBtn = document.getElementById("reconcileExportCsvBtn");
  const reconcileStatus = document.getElementById("reconcileStatus");
  const reconcileSummary = document.getElementById("reconcileSummary") as HTMLElement | null;
  const reconcileDiagnostics = document.getElementById("reconcileDiagnostics") as HTMLElement | null;
  const reconcileFilterInput = document.getElementById(
    "reconcileFilterInput"
  ) as HTMLInputElement | null;
  const reconcileTabCaption = document.getElementById("reconcileTabCaption") as HTMLElement | null;
  const tabMissing = document.getElementById("reconcileTabMissing") as HTMLButtonElement | null;
  const tabUnexpected = document.getElementById("reconcileTabUnexpected") as HTMLButtonElement | null;
  const tabMismatched = document.getElementById("reconcileTabMismatched") as HTMLButtonElement | null;
  const diffTable = document.getElementById("reconcileDiffTable") as HTMLTableElement | null;
  const diffTableBody = document.getElementById("reconcileDiffTableBody") as HTMLElement | null;

  if (!fileInput || !createBtn || !statusEl || !panel || !importIdEl || !mappingEl) {
    return;
  }

  let currentImportId: number | null = null;
  let currentReport: ReconcileReport | null = null;
  let activeTab: DiffTab = "missing";

  const setStatus = (text: string, isError = false) => {
    statusEl.textContent = text;
    (statusEl as HTMLElement).style.color = isError ? "#b91c1c" : "#475569";
  };

  const setReconcileStatus = (text: string, isError = false) => {
    if (!reconcileStatus) return;
    reconcileStatus.textContent = text;
    (reconcileStatus as HTMLElement).style.color = isError ? "#b91c1c" : "#475569";
  };

  const updateResultLink = (resultId: number | null | undefined) => {
    if (!openResult) return;
    if (!resultId) {
      openResult.hidden = true;
      openResult.href = "#";
      return;
    }
    openResult.hidden = false;
    openResult.href = `/result/${resultId}`;
    openResult.textContent = `Open Result ${resultId}`;
  };

  const applyImportData = (data: any) => {
    currentImportId = data.import_id;
    importIdEl.textContent = String(data.import_id);
    mappingEl.value = JSON.stringify(data.mapping || data.mapping_candidates || {}, null, 2);
    panel.hidden = false;
    updateResultLink(data.result_id);
    setStatus(`Status: ${data.status}`);
  };

  const loadSshVendors = async () => {
    if (!reconcileVendor) return;
    try {
      const resp = await fetch("/api/reconcile/ssh-vendors");
      const data = await resp.json();
      if (!resp.ok || !Array.isArray(data.vendors)) return;
      for (const item of data.vendors as Array<{ name: string; default_command: string }>) {
        const opt = document.createElement("option");
        opt.value = item.name;
        opt.textContent = `${item.name} (${item.default_command})`;
        reconcileVendor.appendChild(opt);
      }
    } catch (_) {
      // Ignore vendor list loading failures and allow manual command entry.
    }
  };

  const tabItems = (report: ReconcileReport, tab: DiffTab): Array<Record<string, unknown>> => {
    const list = report[tab];
    return Array.isArray(list) ? list : [];
  };

  const filteredTabItems = (
    report: ReconcileReport,
    tab: DiffTab,
    filterText: string
  ): Array<Record<string, unknown>> => {
    const source = tabItems(report, tab);
    const q = filterText.trim().toLowerCase();
    if (!q) return source;
    return source.filter((item) => JSON.stringify(item).toLowerCase().includes(q));
  };

  const setTabButtons = (report: ReconcileReport) => {
    const counts = {
      missing: tabItems(report, "missing").length,
      unexpected: tabItems(report, "unexpected").length,
      mismatched: tabItems(report, "mismatched").length,
    };
    if (tabMissing) tabMissing.textContent = `Missing (${counts.missing})`;
    if (tabUnexpected) tabUnexpected.textContent = `Unexpected (${counts.unexpected})`;
    if (tabMismatched) tabMismatched.textContent = `Mismatched (${counts.mismatched})`;

    const activeClass = "active";
    if (tabMissing) tabMissing.classList.toggle(activeClass, activeTab === "missing");
    if (tabUnexpected) tabUnexpected.classList.toggle(activeClass, activeTab === "unexpected");
    if (tabMismatched) tabMismatched.classList.toggle(activeClass, activeTab === "mismatched");
  };

  const renderDiagnostics = (report: ReconcileReport) => {
    if (!reconcileDiagnostics) return;
    const collection = report.collection || {};
    const lines = [
      `Method: ${String(collection.method ?? "-")}`,
      `Collector: ${String(collection.collector ?? "-")}`,
      `Parser: ${String(collection.parser ?? "-")}`,
      `Vendor: ${String(collection.vendor ?? "-")}`,
      `Fallback used: ${String(collection.parser_fallback_used ?? false)}`,
      `Observed links: ${String(collection.observed_links ?? "-")}`,
    ];
    reconcileDiagnostics.innerHTML = "";
    for (const line of lines) {
      const p = document.createElement("p");
      p.textContent = line;
      reconcileDiagnostics.appendChild(p);
    }
    reconcileDiagnostics.hidden = false;
  };

  const renderTable = (report: ReconcileReport) => {
    if (!diffTable || !diffTableBody) return;
    const q = reconcileFilterInput?.value || "";
    const rows = filteredTabItems(report, activeTab, q);
    const total = tabItems(report, activeTab).length;
    if (reconcileTabCaption) {
      reconcileTabCaption.textContent = `${activeTab}: ${rows.length} / ${total}`;
    }
    diffTableBody.innerHTML = "";
    for (const item of rows) {
      const tr = document.createElement("tr");
      const tdKey = document.createElement("td");
      tdKey.textContent = String(item.key ?? "");
      const tdReason = document.createElement("td");
      tdReason.textContent = String(item.reason ?? "");
      const tdExpected = document.createElement("td");
      tdExpected.textContent = toJson(item.expected);
      const tdObserved = document.createElement("td");
      tdObserved.textContent = toJson(item.observed);
      tr.append(tdKey, tdReason, tdExpected, tdObserved);
      diffTableBody.appendChild(tr);
    }
    diffTable.hidden = false;
  };

  const renderReconcileReport = (report: ReconcileReport | null) => {
    if (!reconcileSummary) return;
    if (!report) {
      reconcileSummary.hidden = true;
      reconcileSummary.textContent = "";
      if (reconcileDiagnostics) reconcileDiagnostics.hidden = true;
      if (diffTable) diffTable.hidden = true;
      if (reconcileTabCaption) reconcileTabCaption.textContent = "";
      return;
    }
    reconcileSummary.hidden = false;
    reconcileSummary.textContent = toJson(report.summary);
    setTabButtons(report);
    renderDiagnostics(report);
    renderTable(report);
  };

  const exportCurrentJson = () => {
    if (!currentReport) {
      setReconcileStatus("No reconcile report to export.", true);
      return;
    }
    const q = reconcileFilterInput?.value || "";
    const items = filteredTabItems(currentReport, activeTab, q);
    const payload = {
      tab: activeTab,
      summary: currentReport.summary || {},
      collection: currentReport.collection || {},
      items,
    };
    downloadText(
      `reconcile-${activeTab}.json`,
      JSON.stringify(payload, null, 2),
      "application/json"
    );
  };

  const exportCurrentCsv = () => {
    if (!currentReport) {
      setReconcileStatus("No reconcile report to export.", true);
      return;
    }
    const q = reconcileFilterInput?.value || "";
    const items = filteredTabItems(currentReport, activeTab, q);
    const lines = ["category,key,reason,expected,observed"];
    for (const item of items) {
      lines.push(
        [
          csvEscape(activeTab),
          csvEscape(item.key ?? ""),
          csvEscape(item.reason ?? ""),
          csvEscape(toJson(item.expected)),
          csvEscape(toJson(item.observed)),
        ].join(",")
      );
    }
    downloadText(`reconcile-${activeTab}.csv`, lines.join("\n"), "text/csv");
  };

  createBtn.addEventListener("click", async () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      setStatus("Please select a CSV file for API workflow.", true);
      return;
    }

    const formData = new FormData();
    formData.append("csv_file", file, file.name);
    setStatus("Creating import...");

    try {
      const resp = await fetch("/api/imports", { method: "POST", body: formData });
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || "Failed to create import.", true);
        return;
      }
      applyImportData(data);
    } catch (_) {
      setStatus("Network error while creating import.", true);
    }
  });

  saveBtn?.addEventListener("click", async () => {
    if (!currentImportId) return;

    let mapping = null;
    try {
      mapping = JSON.parse(mappingEl.value);
    } catch (_) {
      setStatus("Mapping JSON is invalid.", true);
      return;
    }

    setStatus("Saving mapping...");
    try {
      const resp = await fetch(`/api/imports/${currentImportId}/mapping`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mapping }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || "Failed to save mapping.", true);
        return;
      }
      applyImportData({ ...data, import_id: currentImportId, result_id: null });
      setStatus(`Mapping saved. Status: ${data.status}`);
    } catch (_) {
      setStatus("Network error while saving mapping.", true);
    }
  });

  executeBtn?.addEventListener("click", async () => {
    if (!currentImportId) return;

    setStatus("Executing import...");
    try {
      const resp = await fetch(`/api/imports/${currentImportId}/execute`, { method: "POST" });
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || "Failed to execute import.", true);
        return;
      }
      updateResultLink(data.result_id);
      setStatus(`Completed. Result ID: ${data.result_id}`);
    } catch (_) {
      setStatus("Network error while executing import.", true);
    }
  });

  refreshBtn?.addEventListener("click", async () => {
    if (!currentImportId) return;

    setStatus("Refreshing status...");
    try {
      const resp = await fetch(`/api/imports/${currentImportId}`);
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || "Failed to fetch status.", true);
        return;
      }
      applyImportData(data);
    } catch (_) {
      setStatus("Network error while refreshing status.", true);
    }
  });

  reconcileBtn?.addEventListener("click", async () => {
    if (!currentImportId) {
      setReconcileStatus("Create/execute import first.", true);
      return;
    }
    const seedDevice = (reconcileSeed?.value || "").trim();
    const host = (reconcileHost?.value || "").trim();
    const username = (reconcileUser?.value || "").trim();
    const vendor = (reconcileVendor?.value || "").trim();
    const command = (reconcileCommand?.value || "").trim();
    const timeoutRaw = (reconcileTimeout?.value || "").trim();
    const timeout = Number(timeoutRaw || "10");

    if (!seedDevice || !host || !username) {
      setReconcileStatus("Seed device, SSH host, and SSH username are required.", true);
      return;
    }
    if (!vendor && !command) {
      setReconcileStatus("Select vendor profile or enter SSH command.", true);
      return;
    }

    const params: Record<string, string | number> = { host, username, timeout };
    if (vendor) params.vendor = vendor;
    if (command) params.command = command;

    setReconcileStatus("Running SSH reconcile...");
    currentReport = null;
    renderReconcileReport(null);
    try {
      const resp = await fetch("/api/reconcile/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          import_id: currentImportId,
          method: "ssh",
          seed_device: seedDevice,
          params,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setReconcileStatus(data.error || "SSH reconcile failed.", true);
        return;
      }
      activeTab = "missing";
      currentReport = (data.report || {}) as ReconcileReport;
      renderReconcileReport(currentReport);
      setReconcileStatus("SSH reconcile completed.");
    } catch (_) {
      setReconcileStatus("Network error while running SSH reconcile.", true);
    }
  });

  reconcileVendor?.addEventListener("change", () => {
    if (!reconcileCommand || !reconcileVendor) return;
    if (reconcileCommand.value.trim()) return;
    const selected = reconcileVendor.selectedIndex;
    const optText = reconcileVendor.options[selected]?.textContent || "";
    const m = optText.match(/\((.+)\)$/);
    if (m && m[1]) {
      reconcileCommand.placeholder = m[1];
    }
  });

  reconcileFilterInput?.addEventListener("input", () => {
    renderReconcileReport(currentReport);
  });

  tabMissing?.addEventListener("click", () => {
    activeTab = "missing";
    renderReconcileReport(currentReport);
  });
  tabUnexpected?.addEventListener("click", () => {
    activeTab = "unexpected";
    renderReconcileReport(currentReport);
  });
  tabMismatched?.addEventListener("click", () => {
    activeTab = "mismatched";
    renderReconcileReport(currentReport);
  });
  reconcileExportJsonBtn?.addEventListener("click", exportCurrentJson);
  reconcileExportCsvBtn?.addEventListener("click", exportCurrentCsv);

  loadSshVendors();
}
