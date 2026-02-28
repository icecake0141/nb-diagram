export function initImportWorkflow() {
  const fileInput = document.getElementById('apiCsvFile') as HTMLInputElement | null;
  const createBtn = document.getElementById('apiCreateBtn');
  const statusEl = document.getElementById('apiImportStatus');
  const panel = document.getElementById('apiMappingPanel') as HTMLElement | null;
  const importIdEl = document.getElementById('apiImportId');
  const mappingEl = document.getElementById('apiMappingJson') as HTMLTextAreaElement | null;
  const saveBtn = document.getElementById('apiSaveMappingBtn');
  const executeBtn = document.getElementById('apiExecuteBtn');
  const refreshBtn = document.getElementById('apiRefreshBtn');
  const openResult = document.getElementById('apiOpenResult') as HTMLAnchorElement | null;
  const reconcileSeed = document.getElementById('reconcileSeedDevice') as HTMLInputElement | null;
  const reconcileHost = document.getElementById('reconcileSshHost') as HTMLInputElement | null;
  const reconcileUser = document.getElementById('reconcileSshUsername') as HTMLInputElement | null;
  const reconcileVendor = document.getElementById('reconcileSshVendor') as HTMLSelectElement | null;
  const reconcileCommand = document.getElementById(
    'reconcileSshCommand'
  ) as HTMLInputElement | null;
  const reconcileTimeout = document.getElementById(
    'reconcileSshTimeout'
  ) as HTMLInputElement | null;
  const reconcileBtn = document.getElementById('reconcileCompareBtn');
  const reconcileStatus = document.getElementById('reconcileStatus');
  const reconcileSummary = document.getElementById('reconcileSummary') as HTMLElement | null;

  if (!fileInput || !createBtn || !statusEl || !panel || !importIdEl || !mappingEl) {
    return;
  }

  let currentImportId: number | null = null;

  const setStatus = (text: string, isError = false) => {
    statusEl.textContent = text;
    (statusEl as HTMLElement).style.color = isError ? '#b91c1c' : '#475569';
  };

  const setReconcileStatus = (text: string, isError = false) => {
    if (!reconcileStatus) return;
    reconcileStatus.textContent = text;
    (reconcileStatus as HTMLElement).style.color = isError ? '#b91c1c' : '#475569';
  };

  const setReconcileSummary = (value: string) => {
    if (!reconcileSummary) return;
    if (!value) {
      reconcileSummary.hidden = true;
      reconcileSummary.textContent = '';
      return;
    }
    reconcileSummary.hidden = false;
    reconcileSummary.textContent = value;
  };

  const updateResultLink = (resultId: number | null | undefined) => {
    if (!openResult) return;
    if (!resultId) {
      openResult.hidden = true;
      openResult.href = '#';
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
      const resp = await fetch('/api/reconcile/ssh-vendors');
      const data = await resp.json();
      if (!resp.ok || !Array.isArray(data.vendors)) return;
      for (const item of data.vendors as Array<{ name: string; default_command: string }>) {
        const opt = document.createElement('option');
        opt.value = item.name;
        opt.textContent = `${item.name} (${item.default_command})`;
        reconcileVendor.appendChild(opt);
      }
    } catch (_) {
      // Ignore vendor list loading failures and allow manual command entry.
    }
  };

  createBtn.addEventListener('click', async () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      setStatus('Please select a CSV file for API workflow.', true);
      return;
    }

    const formData = new FormData();
    formData.append('csv_file', file, file.name);
    setStatus('Creating import...');

    try {
      const resp = await fetch('/api/imports', { method: 'POST', body: formData });
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || 'Failed to create import.', true);
        return;
      }
      applyImportData(data);
    } catch (_) {
      setStatus('Network error while creating import.', true);
    }
  });

  saveBtn?.addEventListener('click', async () => {
    if (!currentImportId) return;

    let mapping = null;
    try {
      mapping = JSON.parse(mappingEl.value);
    } catch (_) {
      setStatus('Mapping JSON is invalid.', true);
      return;
    }

    setStatus('Saving mapping...');
    try {
      const resp = await fetch(`/api/imports/${currentImportId}/mapping`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mapping }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || 'Failed to save mapping.', true);
        return;
      }
      applyImportData({ ...data, import_id: currentImportId, result_id: null });
      setStatus(`Mapping saved. Status: ${data.status}`);
    } catch (_) {
      setStatus('Network error while saving mapping.', true);
    }
  });

  executeBtn?.addEventListener('click', async () => {
    if (!currentImportId) return;

    setStatus('Executing import...');
    try {
      const resp = await fetch(`/api/imports/${currentImportId}/execute`, { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || 'Failed to execute import.', true);
        return;
      }
      updateResultLink(data.result_id);
      setStatus(`Completed. Result ID: ${data.result_id}`);
    } catch (_) {
      setStatus('Network error while executing import.', true);
    }
  });

  refreshBtn?.addEventListener('click', async () => {
    if (!currentImportId) return;

    setStatus('Refreshing status...');
    try {
      const resp = await fetch(`/api/imports/${currentImportId}`);
      const data = await resp.json();
      if (!resp.ok) {
        setStatus(data.error || 'Failed to fetch status.', true);
        return;
      }
      applyImportData(data);
    } catch (_) {
      setStatus('Network error while refreshing status.', true);
    }
  });

  reconcileBtn?.addEventListener('click', async () => {
    if (!currentImportId) {
      setReconcileStatus('Create/execute import first.', true);
      return;
    }
    const seedDevice = (reconcileSeed?.value || '').trim();
    const host = (reconcileHost?.value || '').trim();
    const username = (reconcileUser?.value || '').trim();
    const vendor = (reconcileVendor?.value || '').trim();
    const command = (reconcileCommand?.value || '').trim();
    const timeoutRaw = (reconcileTimeout?.value || '').trim();
    const timeout = Number(timeoutRaw || '10');

    if (!seedDevice || !host || !username) {
      setReconcileStatus('Seed device, SSH host, and SSH username are required.', true);
      return;
    }
    if (!vendor && !command) {
      setReconcileStatus('Select vendor profile or enter SSH command.', true);
      return;
    }

    const params: Record<string, string | number> = { host, username, timeout };
    if (vendor) params.vendor = vendor;
    if (command) params.command = command;

    setReconcileStatus('Running SSH reconcile...');
    setReconcileSummary('');
    try {
      const resp = await fetch('/api/reconcile/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          import_id: currentImportId,
          method: 'ssh',
          seed_device: seedDevice,
          params,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setReconcileStatus(data.error || 'SSH reconcile failed.', true);
        return;
      }
      const summary = data.report?.summary || {};
      setReconcileStatus('SSH reconcile completed.');
      setReconcileSummary(
        JSON.stringify(
          {
            summary,
            missing: data.report?.missing?.slice(0, 5) || [],
            unexpected: data.report?.unexpected?.slice(0, 5) || [],
            mismatched: data.report?.mismatched?.slice(0, 5) || [],
          },
          null,
          2
        )
      );
    } catch (_) {
      setReconcileStatus('Network error while running SSH reconcile.', true);
    }
  });

  reconcileVendor?.addEventListener('change', () => {
    if (!reconcileCommand || !reconcileVendor) return;
    if (reconcileCommand.value.trim()) return;
    const selected = reconcileVendor.selectedIndex;
    const optText = reconcileVendor.options[selected]?.textContent || '';
    const m = optText.match(/\((.+)\)$/);
    if (m && m[1]) {
      reconcileCommand.placeholder = m[1];
    }
  });

  loadSshVendors();
}
