const API = "http://localhost:8000";

const STAGES = ['applied','screen','interview','offer'];
const STAGE_LABEL = {applied:'Applied',screen:'Screening',assessment_scheduled:'Assessment scheduled',interview:'Interview',offer:'Offer',rejected:'Rejected'};

let masterResume = { experience: [] };
let applications = [];

function escapeHtml(str){
  return (str||'').toString().replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

async function api(path, options={}){
  const res = await fetch(API + path, {
    headers: {"Content-Type":"application/json"},
    ...options,
  });
  if(!res.ok){
    let detail = res.statusText;
    try{ const j = await res.json(); detail = j.detail || detail; }catch(e){}
    throw new Error(detail);
  }
  if(res.status === 204) return null;
  return res.json();
}

/* ---------- Boot ---------- */
async function loadAll(){
  try{
    await api('/api/health');
    document.getElementById('api-status').textContent = 'connected';
  }catch(e){
    document.getElementById('api-status').textContent = 'offline';
    document.getElementById('main').insertAdjacentHTML('afterbegin',
      `<div class="card" style="border-color:var(--clay);"><span class="muted">Can't reach the backend at ${API}. Start it with <code>uvicorn app.main:app --reload</code> from the backend folder, then reload this page.</span></div>`);
  }
  try{ masterResume = await api('/api/resume'); }catch(e){ masterResume = { experience: [] }; }
  try{ applications = await api('/api/applications'); }catch(e){ applications = []; }
  renderMasterResumeForm();
  await renderDashboard();
  renderTracker();
  loadMatches();
  loadSkillGaps();
  loadBlacklist();
  loadReferrals();
  loadSources();
  loadPortals();
  loadGitHubRepos();
  loadGitHubStatus();
  loadActiveConnectors();
  document.getElementById('export-csv-link').href = API + '/api/applications/export.csv';
}

/* ---------- Master resume ---------- */
function renderMasterResumeForm(){
  document.getElementById('mr-name').value = masterResume.name || '';
  document.getElementById('mr-email').value = masterResume.email || '';
  document.getElementById('mr-phone').value = masterResume.phone || '';
  document.getElementById('mr-linkedin').value = masterResume.linkedin_url || '';
  document.getElementById('mr-github').value = masterResume.github_url || '';
  document.getElementById('mr-portfolio').value = masterResume.portfolio_url || '';
  document.getElementById('mr-summary').value = masterResume.summary || '';
  document.getElementById('mr-skills').value = masterResume.skills || '';
  document.getElementById('mr-education').value = masterResume.education || '';
  document.getElementById('mr-certs').value = masterResume.certs || '';
  document.getElementById('mr-cgpa').value = masterResume.cgpa || '';
  document.getElementById('mr-batch-year').value = masterResume.batch_year || '';
  document.getElementById('mr-backlogs').value = masterResume.has_backlogs ? 'true' : 'false';
  const wrap = document.getElementById('mr-experience');
  wrap.innerHTML = '';
  (masterResume.experience || []).forEach((e, i) => {
    const div = document.createElement('div');
    div.style.cssText = 'border:1px solid var(--hair);border-radius:8px;padding:12px 14px;margin-bottom:12px;';
    div.innerHTML = `
      <div class="flex-between"><input type="text" class="exp-heading" style="font-weight:500;background:transparent;border:none;padding:4px 0;" value="${escapeHtml(e.heading)}">
      <button class="small danger-ghost" onclick="removeExpBlock(${i})">Remove</button></div>
      <textarea class="exp-bullets" style="min-height:90px;">${escapeHtml((e.bullets||[]).join('\n'))}</textarea>
      <label style="margin-top:8px;">GitHub repo / project link (optional)</label>
      <input type="text" class="exp-project-url" placeholder="https://github.com/you/project" value="${escapeHtml(e.project_url||'')}">
    `;
    wrap.appendChild(div);
  });
}
function addExpBlock(){
  masterResume.experience = masterResume.experience || [];
  let project_url = '';
  const isProject = confirm('Is this a new coding project? Click OK to link a GitHub repo (Cancel to skip).');
  if(isProject){
    const url = prompt('Paste the GitHub repo URL for this project (leave blank to skip):', 'https://github.com/');
    if(url && url.trim() && url.trim() !== 'https://github.com/') project_url = url.trim();
  }
  masterResume.experience.push({heading:'New role or project', bullets:['Describe the impact and how you achieved it.'], project_url});
  renderMasterResumeForm();
}
function removeExpBlock(i){
  masterResume.experience.splice(i,1);
  renderMasterResumeForm();
}
function collectMasterResumeFromForm(){
  masterResume.name = document.getElementById('mr-name').value;
  masterResume.email = document.getElementById('mr-email').value;
  masterResume.phone = document.getElementById('mr-phone').value;
  masterResume.linkedin_url = document.getElementById('mr-linkedin').value;
  masterResume.github_url = document.getElementById('mr-github').value;
  masterResume.portfolio_url = document.getElementById('mr-portfolio').value;
  masterResume.summary = document.getElementById('mr-summary').value;
  masterResume.skills = document.getElementById('mr-skills').value;
  masterResume.education = document.getElementById('mr-education').value;
  masterResume.certs = document.getElementById('mr-certs').value;
  masterResume.cgpa = document.getElementById('mr-cgpa').value;
  masterResume.batch_year = document.getElementById('mr-batch-year').value;
  masterResume.has_backlogs = document.getElementById('mr-backlogs').value === 'true';
  const headings = document.querySelectorAll('.exp-heading');
  const bullets = document.querySelectorAll('.exp-bullets');
  const projectUrls = document.querySelectorAll('.exp-project-url');
  const exp = [];
  headings.forEach((h,i)=>{
    exp.push({heading:h.value, bullets: bullets[i].value.split('\n').map(s=>s.trim()).filter(Boolean), project_url: projectUrls[i].value.trim()});
  });
  masterResume.experience = exp;
}
async function saveMasterResume(){
  collectMasterResumeFromForm();
  const msg = document.getElementById('mr-saved-msg');
  try{
    masterResume = await api('/api/resume', { method:'PUT', body: JSON.stringify(masterResume) });
    msg.textContent = 'Saved.';
  }catch(e){
    msg.textContent = 'Save failed: ' + e.message;
  }
  setTimeout(()=>msg.textContent='', 2500);
}
function downloadResume(){
  window.open(API + '/api/resume/download', '_blank');
}

/* ---------- Discover ---------- */
async function runDiscovery(){
  const btn = document.getElementById('discover-btn');
  const msg = document.getElementById('discover-msg');
  btn.disabled = true; btn.textContent = 'Searching...';
  msg.textContent = '';
  try{
    const result = await api('/api/discover/run', { method:'POST' });
    if(result.message){
      msg.textContent = result.message;
    }else{
      const skipBits = [];
      if(result.skippedDuplicate) skipBits.push(`${result.skippedDuplicate} duplicate`);
      if(result.skippedBlacklist) skipBits.push(`${result.skippedBlacklist} blacklisted`);
      if(result.skippedIneligible) skipBits.push(`${result.skippedIneligible} ineligible`);
      msg.textContent = `Found ${result.found}, added ${result.added} new matches` + (skipBits.length ? ` (skipped ${skipBits.join(', ')}).` : '.');
    }
    await loadMatches();
    await loadSkillGaps();
  }catch(e){
    msg.textContent = 'Discovery failed: ' + e.message;
  }finally{
    btn.disabled = false; btn.textContent = 'Find matching jobs ↗';
  }
}

async function loadSources(){
  let sources = [];
  try{ sources = await api('/api/discover/sources'); }catch(e){}
  const wrap = document.getElementById('sources-list');
  if(!wrap) return;
  wrap.innerHTML = sources.length ? sources.map(s => `
    <span class="pill ${s.enabled?'sage':'slate'}" style="margin:0 6px 6px 0;">${escapeHtml(s.name)} — ${s.enabled?'active':'not configured'}</span>
  `).join('') : '<span class="empty">Could not load source status.</span>';
}

async function loadMatches(){
  let matches = [];
  try{ matches = await api('/api/discover/matches'); }catch(e){ matches = []; }
  const wrap = document.getElementById('matches-list');
  if(!matches.length){
    wrap.innerHTML = '<div class="card"><span class="empty">No matches yet. Save your master resume, then click "Find matching jobs".</span></div>';
    return;
  }
  wrap.innerHTML = matches.map(m=>{
    const scoreClass = m.matchScore>=70?'sage':m.matchScore>=45?'amber':'clay';
    return `
    <div class="card match-card">
      <div class="match-score-badge pill ${scoreClass}">${m.matchScore}</div>
      <div style="flex:1;">
        <div class="flex-between">
          <div><strong>${escapeHtml(m.title)}</strong><div class="muted">${escapeHtml(m.company)} · ${escapeHtml(m.location||'')} · ${escapeHtml(m.source)}</div></div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button class="small" onclick="dismissMatch(${m.id})">Dismiss</button>
            <a href="${m.url}" target="_blank"><button class="small">View posting</button></a>
            <button class="small" onclick="downloadMatchResume(${m.id})">Resume ↓</button>
            <button class="small primary" onclick="promoteMatch(${m.id})">Mark as applied ↗</button>
            <button class="small connector-btn" onclick="showApplyConnector(${m.id})" title="Apply via connector">⚡ Auto-apply</button>
          </div>
        </div>
        <div class="muted" style="margin-top:10px;">${escapeHtml(m.tailoredSummary)}</div>
        <div style="margin-top:8px;">
          ${(m.matchedKeywords||[]).map(k=>`<span class="pill slate" style="margin:0 4px 4px 0;">${escapeHtml(k)}</span>`).join('')}
          ${(m.missingSkills||[]).map(k=>`<span class="pill clay" style="margin:0 4px 4px 0;">${escapeHtml(k)}</span>`).join('')}
        </div>
        <div id="connector-panel-${m.id}" class="connector-panel" style="display:none;"></div>
      </div>
    </div>`;
  }).join('');
}

async function showApplyConnector(matchId){
  const panel = document.getElementById(`connector-panel-${matchId}`);
  if(panel.style.display !== 'none'){
    panel.style.display = 'none';
    return;
  }
  panel.style.display = 'block';
  panel.innerHTML = '<span class="muted">Loading connectors...</span>';
  try{
    const connectors = await api('/api/portals/connectors/active');
    if(!connectors.length){
      panel.innerHTML = '<div class="muted" style="margin-top:8px;">No connectors configured. Go to <strong>Job portals</strong> to set up your profiles.</div>';
      return;
    }
    panel.innerHTML = `
      <div style="margin-top:10px;padding:10px;background:var(--bg);border-radius:8px;">
        <div class="muted" style="margin-bottom:8px;">Choose a portal to apply through:</div>
        ${connectors.map(c => `
          <button class="small ${c.can_auto_apply ? 'primary' : ''}" style="margin:0 6px 6px 0;"
            onclick="applyViaConnector(${matchId}, '${c.portal_name}')">
            ${c.can_auto_apply ? '⚡' : '🔗'} ${escapeHtml(c.display)}
            ${c.can_auto_apply ? '(auto)' : '(manual)'}
          </button>
        `).join('')}
      </div>`;
  }catch(e){
    panel.innerHTML = `<div class="muted" style="margin-top:8px;">Could not load connectors: ${escapeHtml(e.message)}</div>`;
  }
}

async function applyViaConnector(matchId, portalName){
  const panel = document.getElementById(`connector-panel-${matchId}`);
  panel.innerHTML = '<span class="muted">Applying...</span>';
  try{
    const result = await api('/api/portals/connectors/apply', {
      method: 'POST',
      body: JSON.stringify({ match_id: matchId, portal_name: portalName }),
    });
    if(result.applied){
      panel.innerHTML = `<div class="pill sage" style="margin-top:8px;">✅ Applied automatically via ${escapeHtml(portalName)}!</div>`;
    }else{
      panel.innerHTML = `
        <div style="margin-top:8px;">
          <span class="muted">${escapeHtml(result.message)}</span>
          ${result.apply_url ? `<br><a href="${result.apply_url}" target="_blank"><button class="small primary" style="margin-top:6px;">Open apply page ↗</button></a>` : ''}
        </div>`;
    }
  }catch(e){
    panel.innerHTML = `<div class="muted" style="margin-top:8px;">Error: ${escapeHtml(e.message)}</div>`;
  }
}

async function dismissMatch(id){
  try{ await api(`/api/discover/matches/${id}/dismiss`, { method:'POST' }); }catch(e){}
  loadMatches();
}

async function promoteMatch(id){
  try{
    const result = await api(`/api/discover/matches/${id}/promote`, { method:'POST' });
    applications = await api('/api/applications');
    renderTracker();
    await renderDashboard();
    loadMatches();
    if(confirm(`Saved as ${result.code}. Email yourself the details now?`)){
      emailApplication(result.applicationId);
    }
  }catch(e){
    alert('Could not save this application: ' + e.message);
  }
}

function downloadMatchResume(id){
  window.open(API + `/api/discover/matches/${id}/resume.docx`, '_blank');
}

/* ---------- Skill gaps ---------- */
async function loadSkillGaps(){
  let data = {gaps:[], totalMatches:0};
  try{ data = await api('/api/discover/skill-gaps'); }catch(e){}
  const wrap = document.getElementById('skill-gaps-list');
  if(!wrap) return;
  if(!data.gaps.length){
    wrap.innerHTML = '<span class="empty">No gaps yet — run discovery to see what shows up most in JDs you\'re missing.</span>';
    return;
  }
  const max = Math.max(...data.gaps.map(g=>g.count));
  wrap.innerHTML = data.gaps.map(g => `
    <div class="flex-between" style="padding:6px 0;border-bottom:1px solid var(--hair);">
      <span style="font-size:13px;">${escapeHtml(g.skill)}</span>
      <span class="pill ${g.count/max>0.6?'clay':'amber'}">${g.count} of ${data.totalMatches}</span>
    </div>`).join('');
}

/* ---------- Blacklist ---------- */
async function loadBlacklist(){
  let items = [];
  try{ items = await api('/api/blacklist'); }catch(e){}
  const wrap = document.getElementById('blacklist-list');
  if(!wrap) return;
  wrap.innerHTML = items.length ? items.map(b => `
    <div class="flex-between" style="padding:6px 0;border-bottom:1px solid var(--hair);">
      <span style="font-size:13px;">${escapeHtml(b.company)}${b.reason?` <span class="muted">— ${escapeHtml(b.reason)}</span>`:''}</span>
      <button class="small danger-ghost" onclick="removeBlacklist(${b.id})">Remove</button>
    </div>`).join('') : '<span class="empty">No blacklisted companies yet.</span>';
}
async function addBlacklist(){
  const company = document.getElementById('bl-company').value.trim();
  const reason = document.getElementById('bl-reason').value.trim();
  if(!company) return;
  try{
    await api('/api/blacklist', { method:'POST', body: JSON.stringify({company, reason}) });
    document.getElementById('bl-company').value = '';
    document.getElementById('bl-reason').value = '';
    loadBlacklist();
  }catch(e){
    alert('Could not add: ' + e.message);
  }
}
async function removeBlacklist(id){
  try{ await api(`/api/blacklist/${id}`, { method:'DELETE' }); }catch(e){}
  loadBlacklist();
}

/* ---------- Manual tailor ---------- */
async function runTailor(){
  const company = document.getElementById('tl-company').value.trim();
  const title = document.getElementById('tl-title').value.trim();
  const source = document.getElementById('tl-source').value;
  const deadline = document.getElementById('tl-deadline').value;
  const url = document.getElementById('tl-url').value.trim();
  const jd = document.getElementById('tl-jd').value.trim();
  const resultWrap = document.getElementById('tl-result');
  if(!company || !title || !jd){
    resultWrap.innerHTML = '<div class="card"><span class="muted">Fill in company, role title, and the job description first.</span></div>';
    return;
  }
  const btn = document.getElementById('tl-run-btn');
  btn.disabled = true; btn.textContent = 'Scoring...';
  resultWrap.innerHTML = '';
  try{
    const result = await api('/api/tailor', { method:'POST', body: JSON.stringify({ company, title, jd }) });
    renderTailorResult(result, {company, title, source, deadline, url, jd});
  }catch(e){
    resultWrap.innerHTML = `<div class="card"><span class="muted">Tailoring failed: ${escapeHtml(e.message)}</span></div>`;
  }finally{
    btn.disabled = false; btn.textContent = 'Score & tailor ↗';
  }
}

let pendingTailor = null;
function renderTailorResult(result, meta){
  pendingTailor = {result, meta};
  const scoreColor = result.matchScore >= 70 ? 'sage' : (result.matchScore >= 45 ? 'amber' : 'clay');
  document.getElementById('tl-result').innerHTML = `
    <div class="card">
      <div class="flex-between">
        <div class="card-title" style="margin:0;">Match score</div>
        <div class="pill ${scoreColor}" style="font-size:14px;padding:5px 14px;">${result.matchScore}/100</div>
      </div>
      <div style="margin-top:10px;" class="muted">${escapeHtml(result.companySnapshot || '')}</div>
      <div style="margin-top:14px;">
        <div class="muted" style="margin-bottom:6px;">Matched keywords</div>
        ${(result.matchedKeywords||[]).map(k=>`<span class="pill slate" style="margin:0 6px 6px 0;">${escapeHtml(k)}</span>`).join('')}
      </div>
      <div style="margin-top:14px;">
        <div class="muted" style="margin-bottom:6px;">Gaps to address</div>
        ${(result.missingSkills||[]).length ? (result.missingSkills||[]).map(k=>`<span class="pill clay" style="margin:0 6px 6px 0;">${escapeHtml(k)}</span>`).join('') : '<span class="muted">No major gaps detected.</span>'}
      </div>
    </div>
    <div class="card">
      <div class="card-title">Tailored summary</div>
      <p style="font-size:13px;line-height:1.6;">${escapeHtml(result.tailoredSummary||'')}</p>
      <div class="card-title" style="margin-top:16px;">Tailored bullets to use</div>
      <ul class="bullet-list">${(result.tailoredBullets||[]).map(b=>`<li>${escapeHtml(b)}</li>`).join('')}</ul>
    </div>
    <button class="primary" onclick="saveApplication()">Save to tracker ↗</button>
    <span class="muted" style="margin-left:10px;">You'll still submit this yourself on ${escapeHtml(meta.source)}.</span>
  `;
}

async function saveApplication(){
  if(!pendingTailor) return;
  const {result, meta} = pendingTailor;
  try{
    const created = await api('/api/applications', { method:'POST', body: JSON.stringify({
      company: meta.company, title: meta.title, source: meta.source, url: meta.url || null,
      deadline: meta.deadline || null, jd: meta.jd, matchScore: result.matchScore,
      companySnapshot: result.companySnapshot, tailoredSummary: result.tailoredSummary,
      tailoredBullets: result.tailoredBullets, missingSkills: result.missingSkills,
    })});
    ['tl-jd','tl-company','tl-title','tl-deadline','tl-url'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('tl-result').innerHTML = `
      <div class="card"><span class="muted">Saved as ${created.code}.</span>
      <button class="primary" style="margin-left:10px;" onclick="emailApplication(${created.id})">Email me this application ↗</button></div>`;
    applications = await api('/api/applications');
    renderTracker();
    await renderDashboard();
  }catch(e){
    document.getElementById('tl-result').innerHTML = `<div class="card"><span class="muted">Save failed: ${escapeHtml(e.message)}</span></div>`;
  }
}

async function emailApplication(id){
  try{
    await api(`/api/notify/email/${id}`, { method:'POST' });
    alert('Sent — check your inbox.');
  }catch(e){
    alert('Could not send email: ' + e.message + '\n\nCheck EMAIL_ADDRESS / EMAIL_APP_PASSWORD in backend/.env');
  }
}

/* ---------- Tracker ---------- */
function stageIndex(status){
  if(status === 'rejected') return -1;
  if(status === 'assessment_scheduled') return STAGES.indexOf('screen');
  return STAGES.indexOf(status);
}
function runwayHtml(status){
  const idx = stageIndex(status);
  const colorClass = status === 'rejected' ? 'clay' : (status === 'offer' ? 'sage' : '');
  let segs = '';
  STAGES.forEach((s,i)=>{
    const dotFilled = status === 'rejected' ? (i===0) : (i <= idx);
    segs += `<div class="runway-dot ${dotFilled ? 'filled '+colorClass : ''}"></div>`;
    if(i < STAGES.length-1){
      const segFilled = status === 'rejected' ? false : (i < idx);
      segs += `<div class="runway-seg ${segFilled ? 'filled '+colorClass : ''}"></div>`;
    }
  });
  return `<div class="runway">${segs}</div>`;
}
function statusPillClass(status){
  if(status==='offer') return 'sage';
  if(status==='rejected') return 'clay';
  if(status==='interview'||status==='assessment_scheduled') return 'amber';
  return 'slate';
}
function renderTracker(){
  const body = document.getElementById('tracker-body');
  const empty = document.getElementById('tracker-empty');
  body.innerHTML = '';
  if(!applications.length){ empty.style.display='block'; return; }
  empty.style.display='none';
  applications.forEach(a=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="mono track-code">${a.code}</td>
      <td><div style="font-weight:500;">${escapeHtml(a.title)}</div><div class="muted">${escapeHtml(a.company)}</div></td>
      <td>${escapeHtml(a.source)}</td>
      <td>
        <select onchange="updateStatus(${a.id}, this.value)" style="width:auto;padding:4px 8px;font-size:12px;">
          ${['applied','screen','assessment_scheduled','interview','offer','rejected'].map(s=>`<option value="${s}" ${a.status===s?'selected':''}>${STAGE_LABEL[s]}</option>`).join('')}
        </select>
        ${runwayHtml(a.status)}
      </td>
      <td><input type="date" value="${a.assessment_date||''}" onchange="updateAssessmentDate(${a.id}, this.value)" style="width:auto;padding:4px 6px;font-size:12px;"></td>
      <td><span class="pill ${a.match_score>=70?'sage':a.match_score>=45?'amber':'clay'}">${a.match_score}</span></td>
      <td class="mono muted">${a.applied_date || '—'}</td>
      <td>
        <button class="small" onclick="downloadApplicationResume(${a.id})">Resume ↓</button>
        <button class="small danger-ghost" onclick="deleteApp(${a.id})">Remove</button>
      </td>
    `;
    body.appendChild(tr);
  });
}
async function updateStatus(id, status){
  try{
    await api(`/api/applications/${id}/status`, { method:'PATCH', body: JSON.stringify({status}) });
    applications = await api('/api/applications');
  }catch(e){}
  renderTracker();
  await renderDashboard();
}
async function updateAssessmentDate(id, assessment_date){
  try{
    await api(`/api/applications/${id}/assessment`, { method:'PATCH', body: JSON.stringify({assessment_date: assessment_date || null}) });
    applications = await api('/api/applications');
  }catch(e){}
  renderTracker();
}
function downloadApplicationResume(id){
  window.open(API + `/api/applications/${id}/resume.docx`, '_blank');
}
async function deleteApp(id){
  try{
    await api(`/api/applications/${id}`, { method:'DELETE' });
    applications = await api('/api/applications');
  }catch(e){}
  renderTracker();
  await renderDashboard();
}

/* ---------- Dashboard ---------- */
async function renderDashboard(){
  let stats = {total:0, screen:0, interview:0, offer:0, rejected:0};
  try{ stats = await api('/api/dashboard/stats'); }catch(e){}
  document.getElementById('stat-strip').innerHTML = `
    <div class="stat-cell"><div class="stat-num">${stats.total}</div><div class="stat-label">Applied</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.screen}</div><div class="stat-label">Screening</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.interview}</div><div class="stat-label">Interview</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.offer}</div><div class="stat-label">Offers</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.rejected}</div><div class="stat-label">Rejected</div></div>
  `;

  let deadlines = [];
  try{ deadlines = await api('/api/dashboard/deadlines'); }catch(e){}
  document.getElementById('deadline-list').innerHTML = deadlines.length ? deadlines.map(a=>`
    <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
      <div><span class="mono track-code">${a.code}</span> &nbsp; ${escapeHtml(a.title)} · ${escapeHtml(a.company)}</div>
      <div class="pill amber">${a.deadline}</div>
    </div>`).join('') : '<div class="empty">No deadlines tracked yet.</div>';

  const recent = applications.slice(0,5);
  document.getElementById('recent-list').innerHTML = recent.length ? recent.map(a=>`
    <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
      <div><span class="mono track-code">${a.code}</span> &nbsp; ${escapeHtml(a.title)} · ${escapeHtml(a.company)}</div>
      <span class="pill ${statusPillClass(a.status)}">${STAGE_LABEL[a.status]}</span>
    </div>`).join('') : '<div class="empty">Nothing applied yet.</div>';

  await renderTimeline();
}

async function renderTimeline(){
  const rangeSel = document.getElementById('dash-range');
  const range = rangeSel.value;
  let timelineData = [];
  try{ timelineData = await api('/api/dashboard/timeline'); }catch(e){}
  const counts = {};
  timelineData.forEach(d => counts[d.date] = d.count);

  let days = [];
  if(range === 'all'){
    days = Object.keys(counts).sort();
    if(!days.length) days = [new Date().toISOString().slice(0,10)];
  }else{
    const n = parseInt(range,10);
    const today = new Date();
    for(let i=n-1;i>=0;i--){
      const d = new Date(today);
      d.setDate(d.getDate()-i);
      days.push(d.toISOString().slice(0,10));
    }
  }

  const max = Math.max(1, ...days.map(d=>counts[d]||0));
  document.getElementById('timeline-chart').innerHTML = `<div style="display:flex;align-items:flex-end;gap:3px;height:90px;">
    ${days.map(d=>{
      const v = counts[d]||0;
      const h = Math.round((v/max)*80) + (v>0 ? 6 : 2);
      return `<div title="${d}: ${v} applied" style="flex:1;min-width:2px;height:${h}px;background:${v>0?'var(--amber)':'var(--hair)'};border-radius:2px 2px 0 0;"></div>`;
    }).join('')}
  </div>
  <div class="flex-between muted" style="margin-top:6px;font-size:11px;">
    <span>${days[0]}</span><span>${days[days.length-1]}</span>
  </div>`;

  const totalInRange = days.reduce((s,d)=>s+(counts[d]||0),0);
  const activeDays = days.filter(d=>counts[d]).sort((a,b)=>b.localeCompare(a));
  document.getElementById('timeline-table').innerHTML = `
    <div class="muted" style="margin-bottom:8px;">${totalInRange} applied in this window across ${activeDays.length} active day${activeDays.length===1?'':'s'}.</div>
    ${activeDays.map(d=>`
      <div class="flex-between" style="padding:6px 0;border-bottom:1px solid var(--hair);font-size:13px;">
        <span class="mono">${d}</span><span class="pill slate">${counts[d]} applied</span>
      </div>`).join('')}
  `;
}

document.getElementById('dash-range').addEventListener('change', renderTimeline);

/* ---------- Referrals / cold reach-out ---------- */
let referrals = [];
let pendingDraft = null;

async function draftReferralMessage(){
  const name = document.getElementById('rf-name').value.trim();
  const company = document.getElementById('rf-company').value.trim();
  const role_title = document.getElementById('rf-role').value.trim();
  const target_job_title = document.getElementById('rf-target-title').value.trim();
  const linkedin_url = document.getElementById('rf-linkedin').value.trim();
  const jd = document.getElementById('rf-jd').value.trim();
  const resultWrap = document.getElementById('rf-draft-result');
  if(!name || !company){
    resultWrap.innerHTML = '<div class="muted">Fill in at least their name and company first.</div>';
    return;
  }
  const btn = document.getElementById('rf-draft-btn');
  btn.disabled = true; btn.textContent = 'Drafting...';
  resultWrap.innerHTML = '';
  try{
    const {message} = await api('/api/referrals/draft-message', { method:'POST', body: JSON.stringify({name, company, role_title, target_job_title, jd}) });
    pendingDraft = {name, company, role_title, target_job_title, linkedin_url, message};
    resultWrap.innerHTML = `
      <div class="card">
        <div class="card-title">Draft — edit freely before sending</div>
        <textarea id="rf-message-edit" style="min-height:120px;">${escapeHtml(message)}</textarea>
        <div style="margin-top:12px;">
          <button class="primary" onclick="saveReferral()">Save to tracker ↗</button>
        </div>
      </div>`;
  }catch(e){
    resultWrap.innerHTML = `<div class="muted">Drafting failed: ${escapeHtml(e.message)}</div>`;
  }finally{
    btn.disabled = false; btn.textContent = 'Generate message ↗';
  }
}

async function saveReferral(){
  if(!pendingDraft) return;
  const message = document.getElementById('rf-message-edit').value;
  try{
    const created = await api('/api/referrals', { method:'POST', body: JSON.stringify({
      name: pendingDraft.name, company: pendingDraft.company, role_title: pendingDraft.role_title,
      linkedin_url: pendingDraft.linkedin_url, target_job_title: pendingDraft.target_job_title,
    })});
    await api(`/api/referrals/${created.id}`, { method:'PATCH', body: JSON.stringify({message_draft: message}) });
    document.getElementById('rf-draft-result').innerHTML = '<div class="muted">Saved. Copy the message from the tracker below when you\'re ready to send it.</div>';
    ['rf-name','rf-role','rf-company','rf-target-title','rf-linkedin','rf-jd'].forEach(id=>document.getElementById(id).value='');
    pendingDraft = null;
    loadReferrals();
  }catch(e){
    alert('Could not save: ' + e.message);
  }
}

async function loadReferrals(){
  try{ referrals = await api('/api/referrals'); }catch(e){ referrals = []; }
  const body = document.getElementById('referrals-body');
  const empty = document.getElementById('referrals-empty');
  if(!body) return;
  body.innerHTML = '';
  if(!referrals.length){ empty.style.display='block'; return; }
  empty.style.display='none';
  referrals.forEach(r=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><div style="font-weight:500;">${escapeHtml(r.name)}</div><div class="muted">${escapeHtml(r.role_title||'')}</div></td>
      <td>${escapeHtml(r.company)}</td>
      <td>${escapeHtml(r.target_job_title||'—')}</td>
      <td>
        <select onchange="updateReferralStatus(${r.id}, this.value)" style="width:auto;padding:4px 8px;font-size:12px;">
          ${['not_sent','sent','replied','no_response'].map(s=>`<option value="${s}" ${r.status===s?'selected':''}>${s.replace('_',' ')}</option>`).join('')}
        </select>
      </td>
      <td class="mono muted">${r.message_sent_date || '—'}</td>
      <td>
        ${r.linkedin_url ? `<a href="${r.linkedin_url}" target="_blank"><button class="small">Open LinkedIn</button></a>` : ''}
        <button class="small" onclick="copyReferralMessage(${r.id})">Copy message</button>
        <button class="small danger-ghost" onclick="deleteReferral(${r.id})">Remove</button>
      </td>
    `;
    body.appendChild(tr);
  });
  loadFollowUps();
}
async function updateReferralStatus(id, status){
  try{ await api(`/api/referrals/${id}`, { method:'PATCH', body: JSON.stringify({status}) }); }catch(e){}
  loadReferrals();
}
function copyReferralMessage(id){
  const r = referrals.find(x=>x.id===id);
  if(!r) return;
  navigator.clipboard.writeText(r.message_draft || '').then(()=>alert('Message copied — paste it into LinkedIn.'));
}
async function deleteReferral(id){
  try{ await api(`/api/referrals/${id}`, { method:'DELETE' }); }catch(e){}
  loadReferrals();
}

/* ---------- Bulk drafting ---------- */
function parseBulkLine(line){
  const parts = line.split(',').map(s=>s.trim());
  const [name, company, role_title='', linkedin_url='', target_job_title=''] = parts;
  return {name, company, role_title, linkedin_url, target_job_title};
}
async function draftBulkReferrals(){
  const raw = document.getElementById('rf-bulk-input').value;
  const jd = document.getElementById('rf-bulk-jd').value.trim();
  const lines = raw.split('\n').map(l=>l.trim()).filter(Boolean);
  const contacts = lines.map(parseBulkLine).filter(c=>c.name && c.company);
  const resultWrap = document.getElementById('rf-bulk-result');
  if(!contacts.length){
    resultWrap.innerHTML = '<div class="muted">Add at least one line with a name and company.</div>';
    return;
  }
  const btn = document.getElementById('rf-bulk-btn');
  btn.disabled = true; btn.textContent = `Drafting ${contacts.length}...`;
  resultWrap.innerHTML = '';
  try{
    const {results} = await api('/api/referrals/draft-message-bulk', { method:'POST', body: JSON.stringify({contacts, jd}) });
    const okCount = results.filter(r=>r.ok).length;
    resultWrap.innerHTML = `<div class="muted">${okCount} of ${results.length} drafted and saved to the tracker below.</div>` +
      results.filter(r=>!r.ok).map(r=>`<div class="muted">Failed for ${escapeHtml(r.name)} (${escapeHtml(r.company)}): ${escapeHtml(r.error)}</div>`).join('');
    document.getElementById('rf-bulk-input').value = '';
    loadReferrals();
  }catch(e){
    resultWrap.innerHTML = `<div class="muted">Bulk drafting failed: ${escapeHtml(e.message)}</div>`;
  }finally{
    btn.disabled = false; btn.textContent = 'Generate all & save to tracker ↗';
  }
}

/* ---------- Follow-up reminders ---------- */
async function loadFollowUps(){
  let data = {followUps:[], count:0};
  try{ data = await api('/api/referrals/follow-ups'); }catch(e){}
  const wrap = document.getElementById('rf-followups-list');
  if(wrap){
    wrap.innerHTML = data.followUps.length ? data.followUps.map(f=>`
      <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
        <div>${escapeHtml(f.name)} · ${escapeHtml(f.company)} <span class="muted">— sent ${f.daysSinceSent}d ago</span></div>
        ${f.linkedin_url ? `<a href="${f.linkedin_url}" target="_blank"><button class="small">Open LinkedIn</button></a>` : '<span class="pill amber">No reply yet</span>'}
      </div>`).join('') : '<span class="empty">Nothing overdue — you\'re on top of it.</span>';
  }
  const dashWrap = document.getElementById('dash-followups');
  if(dashWrap){
    dashWrap.innerHTML = data.followUps.length ? data.followUps.slice(0,5).map(f=>`
      <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
        <div>${escapeHtml(f.name)} · ${escapeHtml(f.company)}</div>
        <span class="pill amber">${f.daysSinceSent}d, no reply</span>
      </div>`).join('') : '<div class="empty">Nothing overdue.</div>';
  }
}

/* ---------- Job portals ---------- */
let portals = [];

async function loadPortals(){
  try{ portals = await api('/api/portals'); }catch(e){ portals = []; }
  const wrap = document.getElementById('portals-list');
  if(!wrap) return;
  if(!portals.length){
    wrap.innerHTML = '<div class="card"><span class="empty">No portals configured yet.</span></div>';
    return;
  }
  wrap.innerHTML = portals.map(p => {
    const extraStr = Object.keys(p.extra_fields||{}).length
      ? Object.entries(p.extra_fields).map(([k,v])=>`<span class="muted" style="font-size:12px;">${escapeHtml(k)}: ${escapeHtml(v)}</span>`).join(' · ')
      : '';
    return `
    <div class="card portal-card" id="portal-card-${p.portal_name}">
      <div class="flex-between">
        <div>
          <strong class="portal-display-name">${escapeHtml(p.display_name)}</strong>
          <span class="pill slate" style="margin-left:8px;font-size:11px;">${escapeHtml(p.portal_name)}</span>
          ${p.is_connector_enabled ? '<span class="pill sage" style="margin-left:6px;font-size:11px;">⚡ Connector ON</span>' : ''}
        </div>
        <div style="display:flex;gap:6px;">
          <button class="small" onclick="togglePortalEdit('${p.portal_name}')">Edit</button>
          <button class="small" onclick="checkConnectorStatus('${p.portal_name}')">Test connector</button>
          <button class="small danger-ghost" onclick="deletePortal('${p.portal_name}')">Remove</button>
        </div>
      </div>
      ${p.profile_url ? `<div class="muted" style="margin-top:6px;font-size:13px;">Profile: <a href="${p.profile_url}" target="_blank">${escapeHtml(p.profile_url)}</a></div>` : ''}
      ${p.username ? `<div class="muted" style="font-size:13px;">Username: ${escapeHtml(p.username)}</div>` : ''}
      ${extraStr ? `<div style="margin-top:4px;">${extraStr}</div>` : ''}
      <div id="portal-edit-${p.portal_name}" style="display:none;margin-top:12px;padding:12px;background:var(--bg);border-radius:8px;">
        <div class="row2">
          <div><label>Profile URL</label><input type="text" id="pe-url-${p.portal_name}" value="${escapeHtml(p.profile_url)}"></div>
          <div><label>Username / email</label><input type="text" id="pe-user-${p.portal_name}" value="${escapeHtml(p.username)}"></div>
        </div>
        <label style="margin-top:8px;">
          <input type="checkbox" id="pe-connector-${p.portal_name}" ${p.is_connector_enabled ? 'checked' : ''}>
          Enable connector (auto-apply where possible)
        </label>
        <div style="margin-top:10px;">
          <button class="small primary" onclick="savePortalEdit('${p.portal_name}', '${escapeHtml(p.display_name)}')">Save</button>
        </div>
      </div>
      <div id="portal-connector-status-${p.portal_name}" style="margin-top:8px;"></div>
    </div>`;
  }).join('');
}

function togglePortalEdit(name){
  const el = document.getElementById(`portal-edit-${name}`);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function savePortalEdit(portalName, displayName){
  const profile_url = document.getElementById(`pe-url-${portalName}`).value.trim();
  const username = document.getElementById(`pe-user-${portalName}`).value.trim();
  const is_connector_enabled = document.getElementById(`pe-connector-${portalName}`).checked;
  try{
    await api(`/api/portals/${portalName}`, {
      method: 'PUT',
      body: JSON.stringify({
        portal_name: portalName,
        display_name: displayName,
        profile_url,
        username,
        is_connector_enabled,
        extra_fields: {},
      }),
    });
    loadPortals();
    loadActiveConnectors();
  }catch(e){
    alert('Save failed: ' + e.message);
  }
}

async function addNewPortal(){
  const name = document.getElementById('pp-new-name').value.trim().toLowerCase().replace(/\s+/g, '_');
  const display = document.getElementById('pp-new-display').value.trim();
  if(!name || !display) { alert('Fill in both fields.'); return; }
  try{
    await api(`/api/portals/${name}`, {
      method: 'PUT',
      body: JSON.stringify({ portal_name: name, display_name: display }),
    });
    document.getElementById('pp-new-name').value = '';
    document.getElementById('pp-new-display').value = '';
    loadPortals();
  }catch(e){
    alert('Could not add: ' + e.message);
  }
}

async function deletePortal(name){
  if(!confirm(`Remove ${name} portal profile?`)) return;
  try{ await api(`/api/portals/${name}`, { method:'DELETE' }); }catch(e){}
  loadPortals();
  loadActiveConnectors();
}

async function checkConnectorStatus(portalName){
  const wrap = document.getElementById(`portal-connector-status-${portalName}`);
  wrap.innerHTML = '<span class="muted">Checking...</span>';
  try{
    const s = await api(`/api/portals/${portalName}/connector-status`);
    const pillClass = s.configured ? 'sage' : 'amber';
    wrap.innerHTML = `
      <span class="pill ${pillClass}">${s.has_connector ? (s.configured ? '✅ Ready' : '⚠ Not configured') : '❌ No connector'}</span>
      <span class="muted" style="margin-left:8px;">${escapeHtml(s.message)}</span>
      ${s.can_auto_apply ? '<span class="pill sage" style="margin-left:6px;">Can auto-apply</span>' : ''}
    `;
  }catch(e){
    wrap.innerHTML = `<span class="muted">Error: ${escapeHtml(e.message)}</span>`;
  }
}

async function loadActiveConnectors(){
  const wrap = document.getElementById('active-connectors-list');
  if(!wrap) return;
  try{
    const connectors = await api('/api/portals/connectors/active');
    if(!connectors.length){
      wrap.innerHTML = '<span class="empty">No connectors active. Fill in your portal profiles below to enable them.</span>';
      return;
    }
    wrap.innerHTML = connectors.map(c => `
      <span class="pill ${c.can_auto_apply ? 'sage' : 'amber'}" style="margin:0 6px 6px 0;">
        ${c.can_auto_apply ? '⚡' : '🔗'} ${escapeHtml(c.display)}
      </span>
    `).join('');
  }catch(e){
    wrap.innerHTML = '<span class="empty">Could not load connectors.</span>';
  }
}

/* ---------- GitHub sync ---------- */
let ghRepos = [];

async function loadGitHubStatus(){
  const badge = document.getElementById('gh-status-badge');
  if(!badge) return;
  try{
    const s = await api('/api/github/status');
    badge.innerHTML = s.enabled
      ? '<span class="pill sage">Monitoring active</span>'
      : '<span class="pill amber">Not configured — set GITHUB_USERNAME in .env</span>';
  }catch(e){
    badge.innerHTML = '<span class="pill slate">Unknown</span>';
  }
}

async function runGitHubSync(){
  const btn = document.getElementById('gh-sync-btn');
  const msg = document.getElementById('gh-sync-msg');
  btn.disabled = true; btn.textContent = 'Syncing...';
  msg.textContent = '';
  try{
    const result = await api('/api/github/sync', { method:'POST' });
    msg.textContent = `Found ${result.found} repos, added ${result.added} new. ${result.emailed ? `Emailed ${result.emailed} notification(s).` : ''}`;
    loadGitHubRepos();
  }catch(e){
    msg.textContent = 'Sync failed: ' + e.message;
  }finally{
    btn.disabled = false; btn.textContent = 'Sync repos now ↗';
  }
}

async function loadGitHubRepos(){
  try{ ghRepos = await api('/api/github/repos'); }catch(e){ ghRepos = []; }

  const pendingWrap = document.getElementById('gh-pending-list');
  const acceptedWrap = document.getElementById('gh-accepted-list');
  const ignoredWrap = document.getElementById('gh-ignored-list');
  if(!pendingWrap) return;

  const pending = ghRepos.filter(r => r.status === 'pending');
  const accepted = ghRepos.filter(r => r.status === 'accepted');
  const ignored = ghRepos.filter(r => r.status === 'ignored');

  pendingWrap.innerHTML = pending.length ? pending.map(r => `
    <div class="gh-repo-card" style="padding:12px 0;border-bottom:1px solid var(--hair);">
      <div class="flex-between">
        <div>
          <strong><a href="${r.repo_url}" target="_blank" style="color:var(--fg);">${escapeHtml(r.repo_name)}</a></strong>
          ${r.stars ? `<span class="muted" style="margin-left:8px;">⭐ ${r.stars}</span>` : ''}
        </div>
        <div style="display:flex;gap:6px;">
          <button class="small primary" onclick="acceptGitHubRepo(${r.id})">✅ Accept</button>
          <button class="small" onclick="ignoreGitHubRepo(${r.id})">Ignore</button>
        </div>
      </div>
      <div class="muted" style="margin-top:4px;font-size:13px;">${escapeHtml(r.description||'No description')}</div>
      <div style="margin-top:6px;">
        ${(r.languages||[]).map(l=>`<span class="pill slate" style="margin:0 4px 4px 0;font-size:11px;">${escapeHtml(l)}</span>`).join('')}
      </div>
      ${r.auto_bullets.length ? `
        <div style="margin-top:8px;">
          <div class="muted" style="font-size:12px;margin-bottom:4px;">Auto-generated resume bullets:</div>
          <ul class="bullet-list" style="font-size:13px;">${r.auto_bullets.map(b=>`<li>${escapeHtml(b)}</li>`).join('')}</ul>
        </div>` : ''}
    </div>
  `).join('') : '<span class="empty">No pending repos. Click "Sync repos now" to check.</span>';

  acceptedWrap.innerHTML = accepted.length ? accepted.map(r => `
    <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
      <div>
        <a href="${r.repo_url}" target="_blank" style="color:var(--fg);font-weight:500;">${escapeHtml(r.repo_name)}</a>
        <span class="pill sage" style="margin-left:8px;font-size:11px;">On resume</span>
      </div>
      <span class="muted" style="font-size:12px;">${escapeHtml(r.last_pushed)}</span>
    </div>
  `).join('') : '<span class="empty">No accepted projects yet.</span>';

  ignoredWrap.innerHTML = ignored.length ? ignored.map(r => `
    <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
      <div>
        <a href="${r.repo_url}" target="_blank" style="color:var(--fg);">${escapeHtml(r.repo_name)}</a>
      </div>
      <button class="small" onclick="resetGitHubRepo(${r.id})">Reconsider</button>
    </div>
  `).join('') : '<span class="empty">No ignored repos.</span>';
}

async function acceptGitHubRepo(id){
  try{
    await api(`/api/github/repos/${id}/accept`, { method:'POST' });
    loadGitHubRepos();
    // Refresh resume since a new experience block was added
    try{ masterResume = await api('/api/resume'); }catch(e){}
    renderMasterResumeForm();
    alert('Project added to your resume! Check the Master Resume page to review.');
  }catch(e){
    alert('Could not accept: ' + e.message);
  }
}

async function ignoreGitHubRepo(id){
  try{
    await api(`/api/github/repos/${id}/ignore`, { method:'POST' });
    loadGitHubRepos();
  }catch(e){
    alert('Could not ignore: ' + e.message);
  }
}

async function resetGitHubRepo(id){
  try{
    await api(`/api/github/repos/${id}/reset`, { method:'POST' });
    loadGitHubRepos();
  }catch(e){
    alert('Could not reset: ' + e.message);
  }
}

/* ---------- Nav ---------- */
document.querySelectorAll('.nav-item').forEach(item=>{
  item.addEventListener('click', ()=>{
    document.querySelectorAll('.nav-item').forEach(i=>i.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
    item.classList.add('active');
    document.getElementById('view-'+item.dataset.view).classList.add('active');
  });
});

loadAll();

/* ---------- Master resume ---------- */
function renderMasterResumeForm(){
  document.getElementById('mr-name').value = masterResume.name || '';
  document.getElementById('mr-email').value = masterResume.email || '';
  document.getElementById('mr-phone').value = masterResume.phone || '';
  document.getElementById('mr-linkedin').value = masterResume.linkedin_url || '';
  document.getElementById('mr-github').value = masterResume.github_url || '';
  document.getElementById('mr-portfolio').value = masterResume.portfolio_url || '';
  document.getElementById('mr-summary').value = masterResume.summary || '';
  document.getElementById('mr-skills').value = masterResume.skills || '';
  document.getElementById('mr-education').value = masterResume.education || '';
  document.getElementById('mr-certs').value = masterResume.certs || '';
  document.getElementById('mr-cgpa').value = masterResume.cgpa || '';
  document.getElementById('mr-batch-year').value = masterResume.batch_year || '';
  document.getElementById('mr-backlogs').value = masterResume.has_backlogs ? 'true' : 'false';
  const wrap = document.getElementById('mr-experience');
  wrap.innerHTML = '';
  (masterResume.experience || []).forEach((e, i) => {
    const div = document.createElement('div');
    div.style.cssText = 'border:1px solid var(--hair);border-radius:8px;padding:12px 14px;margin-bottom:12px;';
    div.innerHTML = `
      <div class="flex-between"><input type="text" class="exp-heading" style="font-weight:500;background:transparent;border:none;padding:4px 0;" value="${escapeHtml(e.heading)}">
      <button class="small danger-ghost" onclick="removeExpBlock(${i})">Remove</button></div>
      <textarea class="exp-bullets" style="min-height:90px;">${escapeHtml((e.bullets||[]).join('\n'))}</textarea>
      <label style="margin-top:8px;">GitHub repo / project link (optional)</label>
      <input type="text" class="exp-project-url" placeholder="https://github.com/you/project" value="${escapeHtml(e.project_url||'')}">
    `;
    wrap.appendChild(div);
  });
}
function addExpBlock(){
  masterResume.experience = masterResume.experience || [];
  let project_url = '';
  const isProject = confirm('Is this a new coding project? Click OK to link a GitHub repo (Cancel to skip).');
  if(isProject){
    const url = prompt('Paste the GitHub repo URL for this project (leave blank to skip):', 'https://github.com/');
    if(url && url.trim() && url.trim() !== 'https://github.com/') project_url = url.trim();
  }
  masterResume.experience.push({heading:'New role or project', bullets:['Describe the impact and how you achieved it.'], project_url});
  renderMasterResumeForm();
}
function removeExpBlock(i){
  masterResume.experience.splice(i,1);
  renderMasterResumeForm();
}
function collectMasterResumeFromForm(){
  masterResume.name = document.getElementById('mr-name').value;
  masterResume.email = document.getElementById('mr-email').value;
  masterResume.phone = document.getElementById('mr-phone').value;
  masterResume.linkedin_url = document.getElementById('mr-linkedin').value;
  masterResume.github_url = document.getElementById('mr-github').value;
  masterResume.portfolio_url = document.getElementById('mr-portfolio').value;
  masterResume.summary = document.getElementById('mr-summary').value;
  masterResume.skills = document.getElementById('mr-skills').value;
  masterResume.education = document.getElementById('mr-education').value;
  masterResume.certs = document.getElementById('mr-certs').value;
  masterResume.cgpa = document.getElementById('mr-cgpa').value;
  masterResume.batch_year = document.getElementById('mr-batch-year').value;
  masterResume.has_backlogs = document.getElementById('mr-backlogs').value === 'true';
  const headings = document.querySelectorAll('.exp-heading');
  const bullets = document.querySelectorAll('.exp-bullets');
  const projectUrls = document.querySelectorAll('.exp-project-url');
  const exp = [];
  headings.forEach((h,i)=>{
    exp.push({heading:h.value, bullets: bullets[i].value.split('\n').map(s=>s.trim()).filter(Boolean), project_url: projectUrls[i].value.trim()});
  });
  masterResume.experience = exp;
}
async function saveMasterResume(){
  collectMasterResumeFromForm();
  const msg = document.getElementById('mr-saved-msg');
  try{
    masterResume = await api('/api/resume', { method:'PUT', body: JSON.stringify(masterResume) });
    msg.textContent = 'Saved.';
  }catch(e){
    msg.textContent = 'Save failed: ' + e.message;
  }
  setTimeout(()=>msg.textContent='', 2500);
}
function downloadResume(){
  window.open(API + '/api/resume/download', '_blank');
}

/* ---------- Discover ---------- */
async function runDiscovery(){
  const btn = document.getElementById('discover-btn');
  const msg = document.getElementById('discover-msg');
  btn.disabled = true; btn.textContent = 'Searching...';
  msg.textContent = '';
  try{
    const result = await api('/api/discover/run', { method:'POST' });
    if(result.message){
      msg.textContent = result.message;
    }else{
      const skipBits = [];
      if(result.skippedDuplicate) skipBits.push(`${result.skippedDuplicate} duplicate`);
      if(result.skippedBlacklist) skipBits.push(`${result.skippedBlacklist} blacklisted`);
      if(result.skippedIneligible) skipBits.push(`${result.skippedIneligible} ineligible`);
      msg.textContent = `Found ${result.found}, added ${result.added} new matches` + (skipBits.length ? ` (skipped ${skipBits.join(', ')}).` : '.');
    }
    await loadMatches();
    await loadSkillGaps();
  }catch(e){
    msg.textContent = 'Discovery failed: ' + e.message;
  }finally{
    btn.disabled = false; btn.textContent = 'Find matching jobs ↗';
  }
}

async function loadSources(){
  let sources = [];
  try{ sources = await api('/api/discover/sources'); }catch(e){}
  const wrap = document.getElementById('sources-list');
  if(!wrap) return;
  wrap.innerHTML = sources.length ? sources.map(s => `
    <span class="pill ${s.enabled?'sage':'slate'}" style="margin:0 6px 6px 0;">${escapeHtml(s.name)} — ${s.enabled?'active':'not configured'}</span>
  `).join('') : '<span class="empty">Could not load source status.</span>';
}

async function loadMatches(){
  let matches = [];
  try{ matches = await api('/api/discover/matches'); }catch(e){ matches = []; }
  const wrap = document.getElementById('matches-list');
  if(!matches.length){
    wrap.innerHTML = '<div class="card"><span class="empty">No matches yet. Save your master resume, then click "Find matching jobs".</span></div>';
    return;
  }
  wrap.innerHTML = matches.map(m=>{
    const scoreClass = m.matchScore>=70?'sage':m.matchScore>=45?'amber':'clay';
    return `
    <div class="card match-card">
      <div class="match-score-badge pill ${scoreClass}">${m.matchScore}</div>
      <div style="flex:1;">
        <div class="flex-between">
          <div><strong>${escapeHtml(m.title)}</strong><div class="muted">${escapeHtml(m.company)} · ${escapeHtml(m.location||'')} · ${escapeHtml(m.source)}</div></div>
          <div style="display:flex;gap:8px;">
            <button class="small" onclick="dismissMatch(${m.id})">Dismiss</button>
            <a href="${m.url}" target="_blank"><button class="small">View posting</button></a>
            <button class="small" onclick="downloadMatchResume(${m.id})">Resume ↓</button>
            <button class="small primary" onclick="promoteMatch(${m.id})">Mark as applied ↗</button>
          </div>
        </div>
        <div class="muted" style="margin-top:10px;">${escapeHtml(m.tailoredSummary)}</div>
        <div style="margin-top:8px;">
          ${(m.matchedKeywords||[]).map(k=>`<span class="pill slate" style="margin:0 4px 4px 0;">${escapeHtml(k)}</span>`).join('')}
          ${(m.missingSkills||[]).map(k=>`<span class="pill clay" style="margin:0 4px 4px 0;">${escapeHtml(k)}</span>`).join('')}
        </div>
      </div>
    </div>`;
  }).join('');
}

async function dismissMatch(id){
  try{ await api(`/api/discover/matches/${id}/dismiss`, { method:'POST' }); }catch(e){}
  loadMatches();
}

async function promoteMatch(id){
  try{
    const result = await api(`/api/discover/matches/${id}/promote`, { method:'POST' });
    applications = await api('/api/applications');
    renderTracker();
    await renderDashboard();
    loadMatches();
    if(confirm(`Saved as ${result.code}. Email yourself the details now?`)){
      emailApplication(result.applicationId);
    }
  }catch(e){
    alert('Could not save this application: ' + e.message);
  }
}

function downloadMatchResume(id){
  window.open(API + `/api/discover/matches/${id}/resume.docx`, '_blank');
}

/* ---------- Skill gaps ---------- */
async function loadSkillGaps(){
  let data = {gaps:[], totalMatches:0};
  try{ data = await api('/api/discover/skill-gaps'); }catch(e){}
  const wrap = document.getElementById('skill-gaps-list');
  if(!wrap) return;
  if(!data.gaps.length){
    wrap.innerHTML = '<span class="empty">No gaps yet — run discovery to see what shows up most in JDs you\'re missing.</span>';
    return;
  }
  const max = Math.max(...data.gaps.map(g=>g.count));
  wrap.innerHTML = data.gaps.map(g => `
    <div class="flex-between" style="padding:6px 0;border-bottom:1px solid var(--hair);">
      <span style="font-size:13px;">${escapeHtml(g.skill)}</span>
      <span class="pill ${g.count/max>0.6?'clay':'amber'}">${g.count} of ${data.totalMatches}</span>
    </div>`).join('');
}

/* ---------- Blacklist ---------- */
async function loadBlacklist(){
  let items = [];
  try{ items = await api('/api/blacklist'); }catch(e){}
  const wrap = document.getElementById('blacklist-list');
  if(!wrap) return;
  wrap.innerHTML = items.length ? items.map(b => `
    <div class="flex-between" style="padding:6px 0;border-bottom:1px solid var(--hair);">
      <span style="font-size:13px;">${escapeHtml(b.company)}${b.reason?` <span class="muted">— ${escapeHtml(b.reason)}</span>`:''}</span>
      <button class="small danger-ghost" onclick="removeBlacklist(${b.id})">Remove</button>
    </div>`).join('') : '<span class="empty">No blacklisted companies yet.</span>';
}
async function addBlacklist(){
  const company = document.getElementById('bl-company').value.trim();
  const reason = document.getElementById('bl-reason').value.trim();
  if(!company) return;
  try{
    await api('/api/blacklist', { method:'POST', body: JSON.stringify({company, reason}) });
    document.getElementById('bl-company').value = '';
    document.getElementById('bl-reason').value = '';
    loadBlacklist();
  }catch(e){
    alert('Could not add: ' + e.message);
  }
}
async function removeBlacklist(id){
  try{ await api(`/api/blacklist/${id}`, { method:'DELETE' }); }catch(e){}
  loadBlacklist();
}

/* ---------- Manual tailor ---------- */
async function runTailor(){
  const company = document.getElementById('tl-company').value.trim();
  const title = document.getElementById('tl-title').value.trim();
  const source = document.getElementById('tl-source').value;
  const deadline = document.getElementById('tl-deadline').value;
  const url = document.getElementById('tl-url').value.trim();
  const jd = document.getElementById('tl-jd').value.trim();
  const resultWrap = document.getElementById('tl-result');
  if(!company || !title || !jd){
    resultWrap.innerHTML = '<div class="card"><span class="muted">Fill in company, role title, and the job description first.</span></div>';
    return;
  }
  const btn = document.getElementById('tl-run-btn');
  btn.disabled = true; btn.textContent = 'Scoring...';
  resultWrap.innerHTML = '';
  try{
    const result = await api('/api/tailor', { method:'POST', body: JSON.stringify({ company, title, jd }) });
    renderTailorResult(result, {company, title, source, deadline, url, jd});
  }catch(e){
    resultWrap.innerHTML = `<div class="card"><span class="muted">Tailoring failed: ${escapeHtml(e.message)}</span></div>`;
  }finally{
    btn.disabled = false; btn.textContent = 'Score & tailor ↗';
  }
}

let pendingTailor = null;
function renderTailorResult(result, meta){
  pendingTailor = {result, meta};
  const scoreColor = result.matchScore >= 70 ? 'sage' : (result.matchScore >= 45 ? 'amber' : 'clay');
  document.getElementById('tl-result').innerHTML = `
    <div class="card">
      <div class="flex-between">
        <div class="card-title" style="margin:0;">Match score</div>
        <div class="pill ${scoreColor}" style="font-size:14px;padding:5px 14px;">${result.matchScore}/100</div>
      </div>
      <div style="margin-top:10px;" class="muted">${escapeHtml(result.companySnapshot || '')}</div>
      <div style="margin-top:14px;">
        <div class="muted" style="margin-bottom:6px;">Matched keywords</div>
        ${(result.matchedKeywords||[]).map(k=>`<span class="pill slate" style="margin:0 6px 6px 0;">${escapeHtml(k)}</span>`).join('')}
      </div>
      <div style="margin-top:14px;">
        <div class="muted" style="margin-bottom:6px;">Gaps to address</div>
        ${(result.missingSkills||[]).length ? (result.missingSkills||[]).map(k=>`<span class="pill clay" style="margin:0 6px 6px 0;">${escapeHtml(k)}</span>`).join('') : '<span class="muted">No major gaps detected.</span>'}
      </div>
    </div>
    <div class="card">
      <div class="card-title">Tailored summary</div>
      <p style="font-size:13px;line-height:1.6;">${escapeHtml(result.tailoredSummary||'')}</p>
      <div class="card-title" style="margin-top:16px;">Tailored bullets to use</div>
      <ul class="bullet-list">${(result.tailoredBullets||[]).map(b=>`<li>${escapeHtml(b)}</li>`).join('')}</ul>
    </div>
    <button class="primary" onclick="saveApplication()">Save to tracker ↗</button>
    <span class="muted" style="margin-left:10px;">You'll still submit this yourself on ${escapeHtml(meta.source)}.</span>
  `;
}

async function saveApplication(){
  if(!pendingTailor) return;
  const {result, meta} = pendingTailor;
  try{
    const created = await api('/api/applications', { method:'POST', body: JSON.stringify({
      company: meta.company, title: meta.title, source: meta.source, url: meta.url || null,
      deadline: meta.deadline || null, jd: meta.jd, matchScore: result.matchScore,
      companySnapshot: result.companySnapshot, tailoredSummary: result.tailoredSummary,
      tailoredBullets: result.tailoredBullets, missingSkills: result.missingSkills,
    })});
    ['tl-jd','tl-company','tl-title','tl-deadline','tl-url'].forEach(id=>document.getElementById(id).value='');
    document.getElementById('tl-result').innerHTML = `
      <div class="card"><span class="muted">Saved as ${created.code}.</span>
      <button class="primary" style="margin-left:10px;" onclick="emailApplication(${created.id})">Email me this application ↗</button></div>`;
    applications = await api('/api/applications');
    renderTracker();
    await renderDashboard();
  }catch(e){
    document.getElementById('tl-result').innerHTML = `<div class="card"><span class="muted">Save failed: ${escapeHtml(e.message)}</span></div>`;
  }
}

async function emailApplication(id){
  try{
    await api(`/api/notify/email/${id}`, { method:'POST' });
    alert('Sent — check your inbox.');
  }catch(e){
    alert('Could not send email: ' + e.message + '\n\nCheck EMAIL_ADDRESS / EMAIL_APP_PASSWORD in backend/.env');
  }
}

/* ---------- Tracker ---------- */
function stageIndex(status){
  if(status === 'rejected') return -1;
  if(status === 'assessment_scheduled') return STAGES.indexOf('screen');
  return STAGES.indexOf(status);
}
function runwayHtml(status){
  const idx = stageIndex(status);
  const colorClass = status === 'rejected' ? 'clay' : (status === 'offer' ? 'sage' : '');
  let segs = '';
  STAGES.forEach((s,i)=>{
    const dotFilled = status === 'rejected' ? (i===0) : (i <= idx);
    segs += `<div class="runway-dot ${dotFilled ? 'filled '+colorClass : ''}"></div>`;
    if(i < STAGES.length-1){
      const segFilled = status === 'rejected' ? false : (i < idx);
      segs += `<div class="runway-seg ${segFilled ? 'filled '+colorClass : ''}"></div>`;
    }
  });
  return `<div class="runway">${segs}</div>`;
}
function statusPillClass(status){
  if(status==='offer') return 'sage';
  if(status==='rejected') return 'clay';
  if(status==='interview'||status==='assessment_scheduled') return 'amber';
  return 'slate';
}
function renderTracker(){
  const body = document.getElementById('tracker-body');
  const empty = document.getElementById('tracker-empty');
  body.innerHTML = '';
  if(!applications.length){ empty.style.display='block'; return; }
  empty.style.display='none';
  applications.forEach(a=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="mono track-code">${a.code}</td>
      <td><div style="font-weight:500;">${escapeHtml(a.title)}</div><div class="muted">${escapeHtml(a.company)}</div></td>
      <td>${escapeHtml(a.source)}</td>
      <td>
        <select onchange="updateStatus(${a.id}, this.value)" style="width:auto;padding:4px 8px;font-size:12px;">
          ${['applied','screen','assessment_scheduled','interview','offer','rejected'].map(s=>`<option value="${s}" ${a.status===s?'selected':''}>${STAGE_LABEL[s]}</option>`).join('')}
        </select>
        ${runwayHtml(a.status)}
      </td>
      <td><input type="date" value="${a.assessment_date||''}" onchange="updateAssessmentDate(${a.id}, this.value)" style="width:auto;padding:4px 6px;font-size:12px;"></td>
      <td><span class="pill ${a.match_score>=70?'sage':a.match_score>=45?'amber':'clay'}">${a.match_score}</span></td>
      <td class="mono muted">${a.applied_date || '—'}</td>
      <td>
        <button class="small" onclick="downloadApplicationResume(${a.id})">Resume ↓</button>
        <button class="small danger-ghost" onclick="deleteApp(${a.id})">Remove</button>
      </td>
    `;
    body.appendChild(tr);
  });
}
async function updateStatus(id, status){
  try{
    await api(`/api/applications/${id}/status`, { method:'PATCH', body: JSON.stringify({status}) });
    applications = await api('/api/applications');
  }catch(e){}
  renderTracker();
  await renderDashboard();
}
async function updateAssessmentDate(id, assessment_date){
  try{
    await api(`/api/applications/${id}/assessment`, { method:'PATCH', body: JSON.stringify({assessment_date: assessment_date || null}) });
    applications = await api('/api/applications');
  }catch(e){}
  renderTracker();
}
function downloadApplicationResume(id){
  window.open(API + `/api/applications/${id}/resume.docx`, '_blank');
}
async function deleteApp(id){
  try{
    await api(`/api/applications/${id}`, { method:'DELETE' });
    applications = await api('/api/applications');
  }catch(e){}
  renderTracker();
  await renderDashboard();
}

/* ---------- Dashboard ---------- */
async function renderDashboard(){
  let stats = {total:0, screen:0, interview:0, offer:0, rejected:0};
  try{ stats = await api('/api/dashboard/stats'); }catch(e){}
  document.getElementById('stat-strip').innerHTML = `
    <div class="stat-cell"><div class="stat-num">${stats.total}</div><div class="stat-label">Applied</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.screen}</div><div class="stat-label">Screening</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.interview}</div><div class="stat-label">Interview</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.offer}</div><div class="stat-label">Offers</div></div>
    <div class="stat-cell"><div class="stat-num">${stats.rejected}</div><div class="stat-label">Rejected</div></div>
  `;

  let deadlines = [];
  try{ deadlines = await api('/api/dashboard/deadlines'); }catch(e){}
  document.getElementById('deadline-list').innerHTML = deadlines.length ? deadlines.map(a=>`
    <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
      <div><span class="mono track-code">${a.code}</span> &nbsp; ${escapeHtml(a.title)} · ${escapeHtml(a.company)}</div>
      <div class="pill amber">${a.deadline}</div>
    </div>`).join('') : '<div class="empty">No deadlines tracked yet.</div>';

  const recent = applications.slice(0,5);
  document.getElementById('recent-list').innerHTML = recent.length ? recent.map(a=>`
    <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
      <div><span class="mono track-code">${a.code}</span> &nbsp; ${escapeHtml(a.title)} · ${escapeHtml(a.company)}</div>
      <span class="pill ${statusPillClass(a.status)}">${STAGE_LABEL[a.status]}</span>
    </div>`).join('') : '<div class="empty">Nothing applied yet.</div>';

  await renderTimeline();
}

async function renderTimeline(){
  const rangeSel = document.getElementById('dash-range');
  const range = rangeSel.value;
  let timelineData = [];
  try{ timelineData = await api('/api/dashboard/timeline'); }catch(e){}
  const counts = {};
  timelineData.forEach(d => counts[d.date] = d.count);

  let days = [];
  if(range === 'all'){
    days = Object.keys(counts).sort();
    if(!days.length) days = [new Date().toISOString().slice(0,10)];
  }else{
    const n = parseInt(range,10);
    const today = new Date();
    for(let i=n-1;i>=0;i--){
      const d = new Date(today);
      d.setDate(d.getDate()-i);
      days.push(d.toISOString().slice(0,10));
    }
  }

  const max = Math.max(1, ...days.map(d=>counts[d]||0));
  document.getElementById('timeline-chart').innerHTML = `<div style="display:flex;align-items:flex-end;gap:3px;height:90px;">
    ${days.map(d=>{
      const v = counts[d]||0;
      const h = Math.round((v/max)*80) + (v>0 ? 6 : 2);
      return `<div title="${d}: ${v} applied" style="flex:1;min-width:2px;height:${h}px;background:${v>0?'var(--amber)':'var(--hair)'};border-radius:2px 2px 0 0;"></div>`;
    }).join('')}
  </div>
  <div class="flex-between muted" style="margin-top:6px;font-size:11px;">
    <span>${days[0]}</span><span>${days[days.length-1]}</span>
  </div>`;

  const totalInRange = days.reduce((s,d)=>s+(counts[d]||0),0);
  const activeDays = days.filter(d=>counts[d]).sort((a,b)=>b.localeCompare(a));
  document.getElementById('timeline-table').innerHTML = `
    <div class="muted" style="margin-bottom:8px;">${totalInRange} applied in this window across ${activeDays.length} active day${activeDays.length===1?'':'s'}.</div>
    ${activeDays.map(d=>`
      <div class="flex-between" style="padding:6px 0;border-bottom:1px solid var(--hair);font-size:13px;">
        <span class="mono">${d}</span><span class="pill slate">${counts[d]} applied</span>
      </div>`).join('')}
  `;
}

document.getElementById('dash-range').addEventListener('change', renderTimeline);

/* ---------- Referrals / cold reach-out ---------- */
let referrals = [];
let pendingDraft = null;

async function draftReferralMessage(){
  const name = document.getElementById('rf-name').value.trim();
  const company = document.getElementById('rf-company').value.trim();
  const role_title = document.getElementById('rf-role').value.trim();
  const target_job_title = document.getElementById('rf-target-title').value.trim();
  const linkedin_url = document.getElementById('rf-linkedin').value.trim();
  const jd = document.getElementById('rf-jd').value.trim();
  const resultWrap = document.getElementById('rf-draft-result');
  if(!name || !company){
    resultWrap.innerHTML = '<div class="muted">Fill in at least their name and company first.</div>';
    return;
  }
  const btn = document.getElementById('rf-draft-btn');
  btn.disabled = true; btn.textContent = 'Drafting...';
  resultWrap.innerHTML = '';
  try{
    const {message} = await api('/api/referrals/draft-message', { method:'POST', body: JSON.stringify({name, company, role_title, target_job_title, jd}) });
    pendingDraft = {name, company, role_title, target_job_title, linkedin_url, message};
    resultWrap.innerHTML = `
      <div class="card">
        <div class="card-title">Draft — edit freely before sending</div>
        <textarea id="rf-message-edit" style="min-height:120px;">${escapeHtml(message)}</textarea>
        <div style="margin-top:12px;">
          <button class="primary" onclick="saveReferral()">Save to tracker ↗</button>
        </div>
      </div>`;
  }catch(e){
    resultWrap.innerHTML = `<div class="muted">Drafting failed: ${escapeHtml(e.message)}</div>`;
  }finally{
    btn.disabled = false; btn.textContent = 'Generate message ↗';
  }
}

async function saveReferral(){
  if(!pendingDraft) return;
  const message = document.getElementById('rf-message-edit').value;
  try{
    const created = await api('/api/referrals', { method:'POST', body: JSON.stringify({
      name: pendingDraft.name, company: pendingDraft.company, role_title: pendingDraft.role_title,
      linkedin_url: pendingDraft.linkedin_url, target_job_title: pendingDraft.target_job_title,
    })});
    await api(`/api/referrals/${created.id}`, { method:'PATCH', body: JSON.stringify({message_draft: message}) });
    document.getElementById('rf-draft-result').innerHTML = '<div class="muted">Saved. Copy the message from the tracker below when you\'re ready to send it.</div>';
    ['rf-name','rf-role','rf-company','rf-target-title','rf-linkedin','rf-jd'].forEach(id=>document.getElementById(id).value='');
    pendingDraft = null;
    loadReferrals();
  }catch(e){
    alert('Could not save: ' + e.message);
  }
}

async function loadReferrals(){
  try{ referrals = await api('/api/referrals'); }catch(e){ referrals = []; }
  const body = document.getElementById('referrals-body');
  const empty = document.getElementById('referrals-empty');
  if(!body) return;
  body.innerHTML = '';
  if(!referrals.length){ empty.style.display='block'; return; }
  empty.style.display='none';
  referrals.forEach(r=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><div style="font-weight:500;">${escapeHtml(r.name)}</div><div class="muted">${escapeHtml(r.role_title||'')}</div></td>
      <td>${escapeHtml(r.company)}</td>
      <td>${escapeHtml(r.target_job_title||'—')}</td>
      <td>
        <select onchange="updateReferralStatus(${r.id}, this.value)" style="width:auto;padding:4px 8px;font-size:12px;">
          ${['not_sent','sent','replied','no_response'].map(s=>`<option value="${s}" ${r.status===s?'selected':''}>${s.replace('_',' ')}</option>`).join('')}
        </select>
      </td>
      <td class="mono muted">${r.message_sent_date || '—'}</td>
      <td>
        ${r.linkedin_url ? `<a href="${r.linkedin_url}" target="_blank"><button class="small">Open LinkedIn</button></a>` : ''}
        <button class="small" onclick="copyReferralMessage(${r.id})">Copy message</button>
        <button class="small danger-ghost" onclick="deleteReferral(${r.id})">Remove</button>
      </td>
    `;
    body.appendChild(tr);
  });
  loadFollowUps();
}
async function updateReferralStatus(id, status){
  try{ await api(`/api/referrals/${id}`, { method:'PATCH', body: JSON.stringify({status}) }); }catch(e){}
  loadReferrals();
}
function copyReferralMessage(id){
  const r = referrals.find(x=>x.id===id);
  if(!r) return;
  navigator.clipboard.writeText(r.message_draft || '').then(()=>alert('Message copied — paste it into LinkedIn.'));
}
async function deleteReferral(id){
  try{ await api(`/api/referrals/${id}`, { method:'DELETE' }); }catch(e){}
  loadReferrals();
}

/* ---------- Bulk drafting ---------- */
function parseBulkLine(line){
  const parts = line.split(',').map(s=>s.trim());
  const [name, company, role_title='', linkedin_url='', target_job_title=''] = parts;
  return {name, company, role_title, linkedin_url, target_job_title};
}
async function draftBulkReferrals(){
  const raw = document.getElementById('rf-bulk-input').value;
  const jd = document.getElementById('rf-bulk-jd').value.trim();
  const lines = raw.split('\n').map(l=>l.trim()).filter(Boolean);
  const contacts = lines.map(parseBulkLine).filter(c=>c.name && c.company);
  const resultWrap = document.getElementById('rf-bulk-result');
  if(!contacts.length){
    resultWrap.innerHTML = '<div class="muted">Add at least one line with a name and company.</div>';
    return;
  }
  const btn = document.getElementById('rf-bulk-btn');
  btn.disabled = true; btn.textContent = `Drafting ${contacts.length}...`;
  resultWrap.innerHTML = '';
  try{
    const {results} = await api('/api/referrals/draft-message-bulk', { method:'POST', body: JSON.stringify({contacts, jd}) });
    const okCount = results.filter(r=>r.ok).length;
    resultWrap.innerHTML = `<div class="muted">${okCount} of ${results.length} drafted and saved to the tracker below.</div>` +
      results.filter(r=>!r.ok).map(r=>`<div class="muted">Failed for ${escapeHtml(r.name)} (${escapeHtml(r.company)}): ${escapeHtml(r.error)}</div>`).join('');
    document.getElementById('rf-bulk-input').value = '';
    loadReferrals();
  }catch(e){
    resultWrap.innerHTML = `<div class="muted">Bulk drafting failed: ${escapeHtml(e.message)}</div>`;
  }finally{
    btn.disabled = false; btn.textContent = 'Generate all & save to tracker ↗';
  }
}

/* ---------- Follow-up reminders ---------- */
async function loadFollowUps(){
  let data = {followUps:[], count:0};
  try{ data = await api('/api/referrals/follow-ups'); }catch(e){}
  const wrap = document.getElementById('rf-followups-list');
  if(wrap){
    wrap.innerHTML = data.followUps.length ? data.followUps.map(f=>`
      <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
        <div>${escapeHtml(f.name)} · ${escapeHtml(f.company)} <span class="muted">— sent ${f.daysSinceSent}d ago</span></div>
        ${f.linkedin_url ? `<a href="${f.linkedin_url}" target="_blank"><button class="small">Open LinkedIn</button></a>` : '<span class="pill amber">No reply yet</span>'}
      </div>`).join('') : '<span class="empty">Nothing overdue — you\'re on top of it.</span>';
  }
  const dashWrap = document.getElementById('dash-followups');
  if(dashWrap){
    dashWrap.innerHTML = data.followUps.length ? data.followUps.slice(0,5).map(f=>`
      <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--hair);">
        <div>${escapeHtml(f.name)} · ${escapeHtml(f.company)}</div>
        <span class="pill amber">${f.daysSinceSent}d, no reply</span>
      </div>`).join('') : '<div class="empty">Nothing overdue.</div>';
  }
}

/* ---------- Nav ---------- */
document.querySelectorAll('.nav-item').forEach(item=>{
  item.addEventListener('click', ()=>{
    document.querySelectorAll('.nav-item').forEach(i=>i.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
    item.classList.add('active');
    document.getElementById('view-'+item.dataset.view).classList.add('active');
  });
});

loadAll();
