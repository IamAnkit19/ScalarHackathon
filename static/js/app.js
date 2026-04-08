// static/js/app.js  — step-by-step AJAX (no SSE, fully reliable)

let level       = 'easy';
let resultCount = 0;
let rewardHist  = [];
let running     = false;

/* ── INIT ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadRewardTable(level);
  renderRewardHistory();
  checkServer();

  document.getElementById('run-btn').addEventListener('click', runAgent);
  document.getElementById('reset-btn').addEventListener('click', resetEnv);
  document.getElementById('clear-log-btn').addEventListener('click', () => {
    document.getElementById('log-body').innerHTML = '';
  });

  document.querySelectorAll('.level-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (running) return;
      document.querySelectorAll('.level-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      level = btn.dataset.level;
      loadRewardTable(level);
      resetEnv();
    });
  });
});

/* ── SERVER CHECK ──────────────────────────── */
async function checkServer() {
  try {
    const res  = await fetch('/api/check');
    const data = await res.json();
    if (!data.api_key_set) {
      showBanner('⚠ API key .env mein set nahi hai! Server band karo, key daalo, phir restart karo.', 'error');
      addLog('API key missing!', 'error');
    } else {
      addLog(`Server ready ✓  |  Key: ${data.preview}`, 'success');
    }
  } catch (e) {
    addLog('Server se connect nahi ho pa raha — Flask chalu hai?', 'error');
  }
}

/* ── BANNER ────────────────────────────────── */
function showBanner(msg, type) {
  let b = document.getElementById('top-banner');
  if (!b) {
    b = document.createElement('div');
    b.id = 'top-banner';
    b.style.cssText = `
      position:fixed;top:14px;left:50%;transform:translateX(-50%);
      padding:11px 22px;border-radius:8px;font-size:13px;z-index:9999;
      font-family:'JetBrains Mono',monospace;cursor:pointer;max-width:640px;text-align:center;
      border:1px solid;`;
    b.onclick = () => b.remove();
    document.body.appendChild(b);
  }
  b.style.background = type === 'error' ? '#450a0a' : '#052e16';
  b.style.color      = type === 'error' ? '#fca5a5' : '#86efac';
  b.style.borderColor= type === 'error' ? '#ef4444' : '#22c55e';
  b.textContent = msg + '   ✕';
  setTimeout(() => b && b.remove(), 7000);
}

/* ── RESET ─────────────────────────────────── */
async function resetEnv() {
  if (running) return;
  resultCount = 0; rewardHist = [];

  await fetch('/api/reset', { method: 'POST' }).catch(() => {});

  document.querySelectorAll('.email-card').forEach(card => {
    card.className = 'email-card';
    const ef = document.getElementById('ef-' + card.dataset.id);
    if (ef) ef.innerHTML = '<span class="tag tag-pending">pending</span>';
    card.querySelector('.scan-overlay')?.remove();
  });

  document.getElementById('results-panel').innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🤖</div>
      <div>Run agent to begin classification</div>
      <div style="font-size:11px;color:var(--text3)">Agent will process all 5 emails</div>
    </div>`;

  document.getElementById('result-count').textContent = '0 classified';
  document.getElementById('prog').style.width = '0%';
  setMetrics({ step:0, total_reward:0, correct:0, accuracy:0, done:false });
  updateCharts({ spam:0, work:0, personal:0 }, 0, 0);
  setStatus('idle', '');
  renderRewardHistory();

  const btn = document.getElementById('run-btn');
  btn.disabled = false;
  btn.innerHTML = runIcon() + ' Run Agent';
  btn.onclick = runAgent;

  addLog('Environment reset. Ready.', 'info');
}

/* ── RUN AGENT — step-by-step AJAX ────────── */
async function runAgent() {
  if (running) return;
  running = true;

  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  setStatus('running', 'running');
  addLog(`Agent loop shuru. Level = ${level}`, 'step');

  // reset environment on server
  await fetch('/api/reset', { method: 'POST' }).catch(() => {});

  for (let i = 0; i < 5; i++) {
    // highlight current email
    highlightCard(i + 1);
    addLog(`step(${i+1}): email read kar raha hoon...`, 'step');
    addLog(`  → Claude API call (${level} prompt)...`, 'info');

    let data;
    try {
      const res = await fetch('/api/step', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ level, email_index: i }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        addLog(`  ✗ Server error: ${err.error}`, 'error');
        showBanner(err.error, 'error');
        break;
      }

      data = await res.json();

    } catch (e) {
      addLog(`  ✗ Network error: ${e.message}`, 'error');
      showBanner('Network error! Flask server chalu hai?', 'error');
      break;
    }

    // ── update UI ──────────────────────────────
    const { email, action, reward, correct, state } = data;
    const cat = action.category || action.label || 'work';
    addLog(`  ← category="${cat}"${action.reason ? `, reason="${action.reason.substring(0,40)}..."` : ''}`, 'info');
    addLog(`  reward: ${reward >= 0 ? '+' : ''}${reward.toFixed(1)} | total: ${state.total_reward.toFixed(1)} | ${correct ? '✓ correct' : '✗ wrong'}`,
           correct ? 'success' : 'warn');

    // update inbox card
    const card = document.getElementById('ec-' + email.id);
    if (card) {
      card.querySelector('.scan-overlay')?.remove();
      card.className = `email-card done-${cat}`;
      const ef = document.getElementById('ef-' + email.id);
      if (ef) ef.innerHTML = buildTags(action);
    }

    // result card
    resultCount++;
    renderResultCard(email, action, reward, correct);

    // metrics
    rewardHist.push(reward);
    renderRewardHistory();

    const lastEl = document.getElementById('m-last');
    lastEl.textContent = (reward >= 0 ? '+' : '') + reward.toFixed(1);
    lastEl.className   = 'metric-value ' + (reward > 0 ? 'pos' : reward < 0 ? 'neg' : 'amber');
    document.getElementById('m-last-sub').textContent = correct ? '✓ correct' : '✗ wrong';

    setMetrics(state);
    updateCharts(state.cat_counts, state.correct, state.step);
    document.getElementById('prog').style.width = (state.step / 5 * 100) + '%';
    document.getElementById('result-count').textContent = resultCount + ' classified';

    await sleep(400);   // pacing
  }

  // ── done ───────────────────────────────────
  running = false;
  const finalRes  = await fetch('/api/state').catch(() => null);
  const finalData = finalRes ? await finalRes.json() : null;

  if (finalData) {
    setMetrics({ ...finalData, done: true });
    addLog(`Episode complete! Score: ${finalData.total_reward.toFixed(1)} | Accuracy: ${Math.round(finalData.accuracy*100)}% | ${finalData.correct}/5 correct`, 'success');
  }

  setStatus('done', 'done');
  btn.disabled = false;
  btn.innerHTML = runIcon() + ' Run Again';
  btn.onclick   = () => { resetEnv(); setTimeout(runAgent, 300); };
}

/* ── HELPERS ───────────────────────────────── */
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function runIcon() {
  return `<svg class="btn-icon" viewBox="0 0 13 13" fill="none">
    <path d="M2.5 2L10.5 6.5L2.5 11V2Z" fill="currentColor"/></svg>`;
}

function highlightCard(id) {
  document.querySelectorAll('.email-card').forEach(c => {
    c.classList.remove('active');
    c.querySelector('.scan-overlay')?.remove();
  });
  const card = document.getElementById('ec-' + id);
  if (card) {
    card.classList.add('active');
    const o = document.createElement('div');
    o.className = 'scan-overlay';
    card.prepend(o);
  }
}

function buildTags(action) {
  if (level === 'hard') {
    return `<span class="tag tag-${action.category||'work'}">${action.category||'?'}</span>
            <span class="tag tag-${action.priority||'low'}">${action.priority||'?'}</span>
            <span class="tag tag-${action.action||'ignore'}">${action.action||'?'}</span>`;
  }
  return `<span class="tag tag-${action.label||'work'}">${action.label||'?'}</span>`;
}

function renderResultCard(email, action, reward, correct) {
  const panel = document.getElementById('results-panel');
  if (panel.querySelector('.empty-state')) panel.innerHTML = '';

  const rClass = reward > 0 ? 'reward-pos' : reward < 0 ? 'reward-neg' : 'reward-mid';
  const gtOk   = (action.category || action.label || '').toLowerCase() === email.label;

  let jsonHtml = '';
  try {
    jsonHtml = JSON.stringify(action, null, 2)
      .replace(/"([^"]+)":/g,  '<span class="json-key">"$1"</span>:')
      .replace(/: "([^"]+)"/g, ': <span class="json-str">"$1"</span>');
  } catch(_) { jsonHtml = '{}'; }

  panel.innerHTML += `
  <div class="result-item">
    <div class="result-header">
      <div class="result-email-info">
        <div class="result-email-id">Email #${email.id} · ${email.sender}</div>
        <div class="result-subject">${email.subject}</div>
      </div>
      <div class="reward-badge ${rClass}">${reward >= 0 ? '+' : ''}${reward.toFixed(1)}</div>
    </div>
    <div class="tags-row">${buildTags(action)}</div>
    ${action.reason ? `<div class="result-reason">${action.reason}</div>` : ''}
    <div class="result-ground">
      <span class="${gtOk?'correct-icon':'wrong-icon'}">${gtOk?'✓':'✗'}</span>
      <span class="ground-label">Ground truth:</span>
      <span class="tag tag-${email.label}" style="font-size:10px;padding:2px 7px">${email.label}</span>
      ${level==='hard'?`
        <span class="tag tag-${email.priority}" style="font-size:10px;padding:2px 7px">${email.priority}</span>
        <span class="tag tag-${email.action}"   style="font-size:10px;padding:2px 7px">${email.action}</span>`:''}
    </div>
    <details>
      <summary>JSON response dekhein</summary>
      <div class="json-box">${jsonHtml}</div>
    </details>
  </div>`;
  panel.scrollTop = panel.scrollHeight;
}

function setMetrics(s) {
  document.getElementById('m-processed').textContent = `${s.step||0} / 5`;
  const sc = document.getElementById('m-score');
  sc.textContent = (s.total_reward||0).toFixed(1);
  sc.className   = 'metric-value' + (s.total_reward>0?' pos':s.total_reward<0?' neg':'');
  document.getElementById('m-acc').textContent =
    s.step > 0 ? Math.round((s.correct/s.step)*100)+'%' : '—';
  const el  = document.getElementById('m-state');
  const sub = document.getElementById('m-state-sub');
  if (s.done)        { el.textContent='DONE';    el.style.color='var(--green)'; sub.textContent='episode complete'; }
  else if (s.step>0) { el.textContent='RUNNING'; el.style.color='var(--amber)'; sub.textContent=`step ${s.step+1} of 5`; }
  else               { el.textContent='RESET';   el.style.color='var(--amber)'; sub.textContent='awaiting episode'; }
}

function updateCharts(cats, correct, total) {
  const t = total||1;
  ['spam','work','personal'].forEach(cat => {
    document.getElementById('bar-'+cat).style.width = Math.round(((cats[cat]||0)/t)*100)+'%';
    document.getElementById('bv-'+cat).textContent  = cats[cat]||0;
  });
  const acc = total>0 ? correct/total : 0;
  const C   = 2*Math.PI*35;
  document.getElementById('donut-arc').style.strokeDashoffset = C*(1-acc);
  document.getElementById('donut-arc').setAttribute('stroke-dasharray', C);
  document.getElementById('donut-pct').textContent = total>0 ? Math.round(acc*100)+'%' : '0%';
}

function renderRewardHistory() {
  const el  = document.getElementById('reward-history');
  const bars = rewardHist.map(r => {
    const pct = Math.min(100,Math.max(10,((r+0.2)/1.2)*100));
    const col = r>0?'#22c55e':r<0?'#ef4444':'#f59e0b';
    return `<div class="rh-bar" style="height:${pct}%;background:${col};opacity:.7"></div>`;
  });
  const empty = Array(5-rewardHist.length).fill('<div class="rh-bar" style="background:var(--bg3)"></div>');
  el.innerHTML = [...bars,...empty].join('');
}

async function loadRewardTable(lvl) {
  try {
    const rows = await (await fetch(`/api/rewards/${lvl}`)).json();
    document.getElementById('rb-rows').innerHTML = rows.map(r=>
      `<div class="rb-row">
        <span class="rb-action">${r.action}</span>
        <span class="rb-val" style="color:${r.positive?'var(--green)':'var(--red)'}">${r.value}</span>
      </div>`).join('');
  } catch(_){}
}

function setStatus(text, type) {
  document.getElementById('status-text').textContent = text;
  const dot = document.getElementById('status-dot');
  dot.className = 'status-dot'+(type==='running'?' running':type==='done'?' done':'');
}

function addLog(msg, type='info') {
  const panel = document.getElementById('log-body');
  const ts    = new Date().toLocaleTimeString('en-IN',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const d     = document.createElement('div');
  d.className = 'log-line';
  d.innerHTML = `<span class="log-ts">${ts}</span><span class="log-msg ${type}">${msg}</span>`;
  panel.appendChild(d);
  panel.scrollTop = panel.scrollHeight;
}