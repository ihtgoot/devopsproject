const API = '/api';
let pollingInterval = null;
let selectedJobId = null;

// ── Health check ─────────────────────────────────────────────────────────────
async function checkHealth() {
  const el = document.getElementById('api-status');
  try {
    const r = await fetch(`${API}/health`);
    if (r.ok) {
      el.innerHTML = '<span class="dot" style="background:var(--success)"></span> API Online';
    } else throw new Error();
  } catch {
    el.innerHTML = '<span class="dot" style="background:var(--danger)"></span> API Offline';
    el.style.borderColor = 'rgba(248,113,113,0.3)';
    el.style.color = 'var(--danger)';
  }
}

// ── Submit training job ───────────────────────────────────────────────────────
async function submitJob() {
  const dataset = document.getElementById('dataset').value.trim();
  const epochs = parseInt(document.getElementById('epochs').value) || 1;
  const lr = parseFloat(document.getElementById('lr').value) || 0.0001;

  if (!dataset) { toast('⚠️ Please enter some dataset text', 'warn'); return; }

  const btn = document.getElementById('train-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Submitting…';

  try {
    // Save dataset text to a temp file via the API
    const res = await fetch(`${API}/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_text: dataset, epochs, learning_rate: lr })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const job = await res.json();

    toast(`✅ Job queued: ${job.id.slice(0, 8)}…`);
    await loadJobs();
    selectJob(job.id);
  } catch (e) {
    toast(`❌ Failed to submit: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>⚡</span> Start Training';
  }
}

// ── Load all jobs ─────────────────────────────────────────────────────────────
async function loadJobs() {
  try {
    const res = await fetch(`${API}/jobs`);
    const jobs = await res.json();
    renderJobs(Array.isArray(jobs) ? jobs : []);
  } catch {
    // silent fail
  }
}

function renderJobs(jobs) {
  const el = document.getElementById('jobs-list');
  if (!jobs.length) {
    el.innerHTML = '<div class="empty"><span>📭</span>No jobs yet. Submit one above.</div>';
    return;
  }

  // Sort newest first
  jobs.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  el.innerHTML = jobs.map(j => `
    <div class="job-item" onclick="selectJob('${j.id}')" id="job-row-${j.id}">
      <div>
        <div class="job-id">${j.id.slice(0, 16)}…</div>
        <div class="job-meta">Epochs: ${j.epochs} · LR: ${j.learning_rate}</div>
      </div>
      <span class="badge badge-${j.status}">${j.status}</span>
    </div>
  `).join('');
}

// ── Select & poll job ─────────────────────────────────────────────────────────
function selectJob(id) {
  selectedJobId = id;
  document.getElementById('detail-panel').style.display = '';
  document.getElementById('detail-id').textContent = id.slice(0, 24) + '…';
  document.getElementById('inference-response').style.display = 'none';

  if (pollingInterval) clearInterval(pollingInterval);
  pollJob(id);
  pollingInterval = setInterval(() => {
    if (['completed', 'failed'].includes(document.getElementById('d-status').textContent.toLowerCase())) {
      clearInterval(pollingInterval);
    } else {
      pollJob(id);
    }
  }, 2000);
}

async function pollJob(id) {
  try {
    const res = await fetch(`${API}/status/${id}`);
    if (!res.ok) return;
    const job = await res.json();
    updateDetail(job);
  } catch { /* silent */ }
}

function updateDetail(job) {
  document.getElementById('d-status').textContent = job.status;
  const progress = job.progress || 0;
  document.getElementById('d-progress').textContent = `${Math.round(progress)}%`;
  document.getElementById('d-epoch').textContent = job.current_epoch ?? '—';
  document.getElementById('d-bar').style.width = `${progress}%`;

  const errEl = document.getElementById('d-error');
  if (job.error) { errEl.textContent = `Error: ${job.error}`; errEl.style.display = ''; }
  else { errEl.style.display = 'none'; }

  // Also refresh list badge
  const row = document.getElementById(`job-row-${job.id}`);
  if (row) {
    const badge = row.querySelector('.badge');
    badge.className = `badge badge-${job.status}`;
    badge.textContent = job.status;
  }
}

// ── Inference ─────────────────────────────────────────────────────────────────
async function runInference() {
  if (!selectedJobId) return;
  const instruction = document.getElementById('inf-instruction').value.trim();
  if (!instruction) { toast('⚠️ Enter an instruction first'); return; }

  const el = document.getElementById('inference-response');
  el.style.display = '';
  el.textContent = '⏳ Thinking…';

  try {
    const res = await fetch(`/api/inference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: selectedJobId, instruction })
    });
    const data = await res.json();
    el.textContent = data.response || data.error || 'No response';
  } catch (e) {
    el.textContent = `Error: ${e.message}`;
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show';
  if (type === 'error') el.style.borderColor = 'var(--danger)';
  else if (type === 'warn') el.style.borderColor = 'var(--warn)';
  else el.style.borderColor = 'var(--success)';
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = ''; }, 3500);
}

// ── Init ──────────────────────────────────────────────────────────────────────
checkHealth();
loadJobs();
setInterval(loadJobs, 5000);
