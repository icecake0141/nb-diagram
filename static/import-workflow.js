export function initImportWorkflow() {
  const fileInput = document.getElementById('apiCsvFile');
  const createBtn = document.getElementById('apiCreateBtn');
  const statusEl = document.getElementById('apiImportStatus');
  const panel = document.getElementById('apiMappingPanel');
  const importIdEl = document.getElementById('apiImportId');
  const mappingEl = document.getElementById('apiMappingJson');
  const saveBtn = document.getElementById('apiSaveMappingBtn');
  const executeBtn = document.getElementById('apiExecuteBtn');
  const refreshBtn = document.getElementById('apiRefreshBtn');
  const openResult = document.getElementById('apiOpenResult');

  if (!fileInput || !createBtn || !statusEl || !panel || !importIdEl || !mappingEl) {
    return;
  }

  let currentImportId = null;

  const setStatus = (text, isError = false) => {
    statusEl.textContent = text;
    statusEl.style.color = isError ? '#b91c1c' : '#475569';
  };

  const updateResultLink = (resultId) => {
    if (!resultId) {
      openResult.hidden = true;
      openResult.href = '#';
      return;
    }
    openResult.hidden = false;
    openResult.href = `/result/${resultId}`;
    openResult.textContent = `Open Result ${resultId}`;
  };

  const applyImportData = (data) => {
    currentImportId = data.import_id;
    importIdEl.textContent = String(data.import_id);
    mappingEl.value = JSON.stringify(data.mapping || data.mapping_candidates || {}, null, 2);
    panel.hidden = false;
    updateResultLink(data.result_id);
    setStatus(`Status: ${data.status}`);
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
}
