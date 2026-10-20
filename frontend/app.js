const cases = [
  {id:'ETCH-2025-014', equipment:'ETCH-07', chamber:'CH-B', recipe:'OX-120', symptom:'etch rate 저하 endpoint 지연', metrics:{etch_rate_nm_min:512,endpoint_sec:94,rf_reflected_w:18,pressure_mtorr:42}, cause:'상부 전극 폴리머 누적', action:'챔버 wet clean 및 seasoning', docs:['SOP-ETCH-12#4.2','WI-PM-07#3.1']},
  {id:'ETCH-2025-031', equipment:'ETCH-07', chamber:'CH-B', recipe:'OX-120', symptom:'endpoint 지연 RF reflected power 상승', metrics:{etch_rate_nm_min:525,endpoint_sec:91,rf_reflected_w:21,pressure_mtorr:41}, cause:'RF match network 접점 열화', action:'match unit 접점 교체 및 RF calibration', docs:['SOP-ETCH-12#4.2','SPEC-RF-03#2.4']},
  {id:'ETCH-2025-044', equipment:'ETCH-09', chamber:'CH-B', recipe:'OX-120', symptom:'etch rate 저하 chamber pressure 불안정', metrics:{etch_rate_nm_min:505,endpoint_sec:96,rf_reflected_w:16,pressure_mtorr:44}, cause:'MFC zero drift', action:'CF4 MFC 교정 및 leak check', docs:['SOP-ETCH-12#4.2','WI-MFC-02#5.3']},
  {id:'ETCH-2025-052', equipment:'ETCH-07', chamber:'CH-A', recipe:'OX-120', symptom:'endpoint 지연', metrics:{etch_rate_nm_min:518,endpoint_sec:92,rf_reflected_w:17,pressure_mtorr:42}, cause:'endpoint window 오염', action:'window 세정 후 endpoint gain 확인', docs:['WI-PM-07#3.1','SPEC-EPD-01#6.2']},
  {id:'ETCH-2026-006', equipment:'ETCH-07', chamber:'CH-B', recipe:'OX-120', symptom:'정상 baseline', metrics:{etch_rate_nm_min:530,endpoint_sec:89,rf_reflected_w:15,pressure_mtorr:41}, cause:'이상 없음', action:'모니터링 유지', docs:['SOP-ETCH-12#4.2']}
];
const documents = {
  'SOP-ETCH-12#4.2': {title:'식각 이상 대응 §4.2', text:'Endpoint가 기준 대비 10% 이상 지연되면 RF, 압력, 가스 유량 이력을 함께 비교한다.'},
  'WI-PM-07#3.1': {title:'챔버 예방정비 §3.1', text:'폴리머 누적 또는 endpoint window 오염이 의심되면 세정 전후 값을 보존하고 seasoning 결과를 기록한다.'},
  'SPEC-RF-03#2.4': {title:'RF 계통 판정 기준 §2.4', text:'Reflected power 상승이 반복될 경우 match network 접점과 calibration 상태를 확인한다.'},
  'WI-MFC-02#5.3': {title:'MFC 점검 §5.3', text:'압력 변동과 etch rate 저하가 동반되면 MFC zero와 leak rate를 확인한다.'},
  'SPEC-EPD-01#6.2': {title:'Endpoint 검출 §6.2', text:'Endpoint 신호 지연 시 window 오염, gain 설정, 광원 상태를 순차 점검한다.'}
};
const metricLabels = {endpoint_sec:'Endpoint',etch_rate_nm_min:'Etch rate',rf_reflected_w:'RF reflected',pressure_mtorr:'Pressure'};
const metricUnits = {endpoint_sec:'sec',etch_rate_nm_min:'nm/min',rf_reflected_w:'W',pressure_mtorr:'mTorr'};
const state = {context:{}, lastAnalysis:null};

const conversation = document.getElementById('conversation');
const input = document.getElementById('questionInput');
const form = document.getElementById('questionForm');
const evidencePanel = document.getElementById('evidencePanel');
const evidenceContent = document.getElementById('evidenceContent');
const emptyEvidence = document.getElementById('emptyEvidence');
const reportDialog = document.getElementById('reportDialog');
const recordsPage = document.getElementById('recordsPage');
const recordList = document.getElementById('recordList');
const recordDetail = document.getElementById('recordDetail');
const RECORDS_KEY = 'etch-investigation-records-v1';

document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => {
  input.value = button.dataset.prompt;
  input.focus();
}));
document.getElementById('openEvidence').addEventListener('click', () => evidencePanel.classList.add('open'));
document.getElementById('closeEvidence').addEventListener('click', () => evidencePanel.classList.remove('open'));
document.getElementById('newInvestigation').addEventListener('click', resetInvestigation);
document.getElementById('investigationNav').addEventListener('click', showInvestigationPage);
document.getElementById('recordsNav').addEventListener('click', showRecordsPage);
document.getElementById('emptyStartInvestigation').addEventListener('click', showInvestigationPage);
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
});
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 140) + 'px'; });

form.addEventListener('submit', async event => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  addUserMessage(question);
  input.value = ''; input.style.height = 'auto';
  const thinking = addThinking();
  setStep(1);
  await wait(550);
  Object.assign(state.context, parseQuestion(question));
  const missing = [];
  if (!state.context.symptom) missing.push('어떤 이상 현상이 관찰됐나요?');
  if (!state.context.equipment && !state.context.chamber && !state.context.recipe) missing.push('장비·챔버·레시피 중 아는 항목을 알려주세요.');
  thinking.remove();
  if (missing.length) {
    addAssistant(`<p class="message-label">추가 정보 필요</p><p>${missing.join(' ')}</p>`);
    return;
  }
  await runInvestigation();
});

function parseQuestion(text) {
  const upper = text.toUpperCase();
  const result = {metrics:{}};
  const equipment = upper.match(/ETCH[\s_-]?(\d+)/);
  const chamber = upper.match(/CH[\s_-]?([A-Z])/);
  const recipes = [...upper.matchAll(/([A-Z]{2,5}-\d{2,4})/g)].map(m => m[1]).filter(v => !v.startsWith('ETCH-'));
  if (equipment) result.equipment = `ETCH-${equipment[1]}`;
  if (chamber) result.chamber = `CH-${chamber[1]}`;
  if (recipes.length) result.recipe = recipes[0];
  extractMetric(text, result.metrics, 'endpoint_sec', /(?:endpoint|엔드포인트)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:초|sec|s\b)/i);
  extractMetric(text, result.metrics, 'etch_rate_nm_min', /(?:etch\s*rate|식각률|식각\s*속도)[^\d]{0,15}(\d+(?:\.\d+)?)/i);
  extractMetric(text, result.metrics, 'rf_reflected_w', /(?:reflected(?:\s*power)?|반사\s*전력)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:w|와트)?/i);
  extractMetric(text, result.metrics, 'pressure_mtorr', /(?:pressure|압력)[^\d]{0,15}(\d+(?:\.\d+)?)\s*(?:mtorr)?/i);
  const symptoms = [];
  const lower = text.toLowerCase();
  if ((lower.includes('endpoint') || lower.includes('엔드포인트')) && /지연|증가|늦/.test(lower)) symptoms.push('endpoint 지연');
  if (/etch\s*rate|식각률|식각 속도/.test(lower) && /저하|감소|낮/.test(lower)) symptoms.push('etch rate 저하');
  if (/reflected|반사 전력|반사전력/.test(lower) && /상승|증가|높/.test(lower)) symptoms.push('RF reflected power 상승');
  if (/pressure|압력/.test(lower) && /불안정|변동|상승|저하/.test(lower)) symptoms.push('chamber pressure 이상');
  if (symptoms.length) result.symptom = symptoms.join(' · ');
  return result;
}
function extractMetric(text, target, key, pattern) { const match = text.match(pattern); if (match) target[key] = Number(match[1]); }

async function runInvestigation() {
  setStep(2); const thinking = addThinking('과거 사례와 문서를 검색하고 있습니다'); await wait(520);
  const scored = cases.map(item => ({...item, score:similarity(item, state.context)})).filter(item => item.score >= .25).sort((a,b) => b.score-a.score).slice(0,5);
  setStep(3); await wait(430);
  const metrics = analyzeMetrics(scored, state.context.metrics || {});
  const causeCases = scored.filter(item => item.cause !== '이상 없음').slice(0,3);
  const docIds = [...new Set(causeCases.flatMap(item => item.docs))];
  state.lastAnalysis = {scored, metrics, causeCases, docIds, context:{...state.context}};
  thinking.remove(); setStep(4);
  addAssistant(renderAnswer(state.lastAnalysis));
  renderEvidence(state.lastAnalysis);
  document.getElementById('evidenceCount').textContent = scored.length + docIds.length;
  document.querySelectorAll('.record-button').forEach(button => button.addEventListener('click', openReport));
  document.querySelectorAll('.citation').forEach(button => button.addEventListener('click', () => highlightEvidence(button.dataset.evidence)));
}

function similarity(item, context) {
  let score = 0;
  if (item.equipment === context.equipment) score += .30;
  if (item.chamber === context.chamber) score += .20;
  if (item.recipe === context.recipe) score += .25;
  const symptoms = (context.symptom || '').toLowerCase().split(/\s+|·/).filter(v => v.length > 1);
  const target = item.symptom.toLowerCase();
  const hits = symptoms.filter(token => target.includes(token)).length;
  score += Math.min(.20, hits * .05);
  const shared = Object.keys(context.metrics || {}).filter(key => key in item.metrics).length;
  if (shared) score += .05;
  return Math.min(1, score);
}

function analyzeMetrics(scored, current) {
  return Object.entries(current).map(([key,value]) => {
    const values = scored.map(item => item.metrics[key]).filter(Number.isFinite);
    if (!values.length) return null;
    const mean = values.reduce((a,b) => a+b,0)/values.length;
    const variance = values.reduce((sum,v) => sum + (v-mean)**2,0)/values.length;
    const std = Math.sqrt(variance);
    const deltaPct = mean ? (value-mean)/mean*100 : 0;
    const z = std ? (value-mean)/std : null;
    const severity = Math.abs(z || 0)>=2 || Math.abs(deltaPct)>=20 ? '비정상' : Math.abs(z || 0)>=1 || Math.abs(deltaPct)>=10 ? '주의' : '정상';
    return {key,value,mean,std,deltaPct,z,severity};
  }).filter(Boolean);
}

function renderAnswer(data) {
  const context = [data.context.equipment,data.context.chamber,data.context.recipe].filter(Boolean).join(' / ');
  const metricCards = data.metrics.length ? data.metrics.map(metric => `
    <div class="metric-card"><header><strong>${metricLabels[metric.key]}</strong><span class="severity">${metric.severity}</span></header>
    <div class="metric-values"><b>${metric.value}</b><span>${metricUnits[metric.key]} · 비교군 평균 ${metric.mean.toFixed(1)}</span></div>
    <div class="delta">평균 대비 ${signed(metric.deltaPct)}%${metric.z===null?'':` · z-score ${signed(metric.z)}`}</div></div>`).join('') : '<p>현재 계측값이 없어 사례 유사도 중심으로 분석했습니다.</p>';
  const causes = data.causeCases.map((item,index) => `
    <div class="cause-item"><span>${index+1}</span><div><strong>${escapeHtml(item.cause)}</strong><small>${escapeHtml(item.action)}</small></div>
    <button class="citation" data-evidence="${item.id}">[${item.id}]</button></div>`).join('');
  return `<p class="message-label">근거 기반 조사 결과</p><h2>${escapeHtml(context || '지정 범위')} 분석 결과</h2>
    <p class="answer-summary">관련성이 높은 과거 사례 <strong>${data.scored.length}건</strong>을 찾았습니다. 아래 항목은 과거 사례의 연관성을 바탕으로 한 우선 확인 가설이며, 현장 점검으로 최종 확인해야 합니다.</p>
    <div class="analysis-grid">${metricCards}</div>
    <section class="answer-section"><h3>우선 확인할 항목</h3><div class="cause-list">${causes || '<p>원인 후보를 좁힐 사례가 부족합니다.</p>'}</div></section>
    <div class="record-cta"><p><strong>조사 결과를 기록으로 남길까요?</strong><br>발생 시각과 검토자를 추가해 승인용 기록을 만들 수 있습니다.</p><button class="record-button" type="button">조사 기록 만들기</button></div>`;
}

function renderEvidence(data) {
  emptyEvidence.hidden = true; evidenceContent.hidden = false;
  evidenceContent.innerHTML = `<section class="evidence-group"><h3>비교 사례 <span>${data.scored.length}건</span></h3>${data.scored.map(item => `
    <article class="evidence-item" data-evidence-id="${item.id}"><header><strong>${item.id}</strong><b>${Math.round(item.score*100)}% 일치</b></header><p>${item.equipment} · ${item.chamber} · ${item.recipe}<br>${item.symptom}<br><strong>원인:</strong> ${item.cause}</p></article>`).join('')}</section>
    <section class="evidence-group"><h3>관련 문서 <span>${data.docIds.length}건</span></h3>${data.docIds.map(id => `<article class="evidence-item" data-evidence-id="${id}"><header><strong>${id}</strong></header><p><b>${documents[id].title}</b><br>${documents[id].text}</p></article>`).join('')}</section>`;
}

function openReport() {
  if (!state.lastAnalysis) return;
  const data = state.lastAnalysis;
  const rows = data.metrics.map(m => `<tr><td>${metricLabels[m.key]}</td><td>${m.value} ${metricUnits[m.key]}</td><td>${m.mean.toFixed(1)}</td><td>${signed(m.deltaPct)}%</td><td>${m.severity}</td></tr>`).join('');
  document.getElementById('reportPreview').innerHTML = `<h3>식각 장비 이상 조사 기록</h3><p><strong>대상:</strong> ${[data.context.equipment,data.context.chamber,data.context.recipe].filter(Boolean).join(' / ')}<br><strong>현상:</strong> ${data.context.symptom}</p>
    <h4>수치 분석</h4><table><thead><tr><th>지표</th><th>현재값</th><th>비교군 평균</th><th>편차</th><th>판정</th></tr></thead><tbody>${rows || '<tr><td colspan="5">계측값 미제공</td></tr>'}</tbody></table>
    <h4>우선 확인 가설</h4><ol>${data.causeCases.map(c => `<li>${c.cause} — ${c.action} [${c.id}]</li>`).join('')}</ol>
    <h4>문서 근거</h4><ul>${data.docIds.map(id => `<li>${id} ${documents[id].title}</li>`).join('')}</ul>`;
  const now = new Date(); now.setMinutes(now.getMinutes()-now.getTimezoneOffset());
  document.getElementById('recordTime').value = now.toISOString().slice(0,16);
  reportDialog.showModal();
}

document.getElementById('approveReport').addEventListener('click', event => {
  const reviewer = document.getElementById('recordReviewer');
  if (!reviewer.value.trim()) { event.preventDefault(); reviewer.focus(); return; }
  saveApprovedRecord(reviewer.value.trim());
  setTimeout(() => {
    showToast(`${reviewer.value.trim()} 검토자로 조사 기록이 승인되었습니다.`);
    showRecordsPage();
  }, 50);
});

function getRecords() {
  try { return JSON.parse(localStorage.getItem(RECORDS_KEY) || '[]'); }
  catch { return []; }
}

function saveApprovedRecord(reviewer) {
  const data = state.lastAnalysis;
  if (!data) return;
  const records = getRecords();
  const now = new Date();
  const id = `IR-${now.toISOString().slice(0,10).replaceAll('-','')}-${String(records.length+1).padStart(3,'0')}`;
  records.unshift({
    id,
    eventTime: document.getElementById('recordTime').value,
    lotId: document.getElementById('recordLot').value.trim() || '미제공',
    reviewer,
    approvedAt: now.toISOString(),
    context: data.context,
    metrics: data.metrics,
    causes: data.causeCases.map(item => ({id:item.id,cause:item.cause,action:item.action})),
    documents: data.docIds.map(id => ({id,title:documents[id].title,text:documents[id].text}))
  });
  localStorage.setItem(RECORDS_KEY, JSON.stringify(records));
  updateRecordCount();
}

function showInvestigationPage() {
  recordsPage.hidden = true;
  conversation.hidden = false;
  form.hidden = false;
  document.getElementById('investigationNav').classList.add('active');
  document.getElementById('recordsNav').classList.remove('active');
  document.querySelector('.topbar h1').textContent = '식각 장비 이상 조사';
}

function showRecordsPage() {
  conversation.hidden = true;
  form.hidden = true;
  recordsPage.hidden = false;
  document.getElementById('investigationNav').classList.remove('active');
  document.getElementById('recordsNav').classList.add('active');
  document.querySelector('.topbar h1').textContent = '승인된 조사 기록';
  renderRecords();
}

function renderRecords(selectedId) {
  const records = getRecords();
  updateRecordCount(records.length);
  if (!records.length) {
    recordList.innerHTML = '';
    recordDetail.innerHTML = `<div class="records-empty"><span aria-hidden="true">▤</span><strong>저장된 조사 기록이 없습니다</strong><p>이상 조사에서 답변을 생성한 후 \`조사 기록 만들기\`를 눌러 승인해 주세요.</p><button type="button" id="emptyStartInvestigationDynamic">이상 조사 시작</button></div>`;
    document.getElementById('emptyStartInvestigationDynamic').addEventListener('click', showInvestigationPage);
    return;
  }
  const selected = records.find(item => item.id === selectedId) || records[0];
  recordList.innerHTML = records.map(item => `<button type="button" class="record-list-item ${item.id===selected.id?'active':''}" data-record-id="${item.id}"><header><strong>${item.id}</strong><span>승인</span></header><p>${[item.context.equipment,item.context.chamber,item.context.recipe].filter(Boolean).join(' · ')}<br>${item.context.symptom}</p><small>${formatDate(item.approvedAt)} · ${escapeHtml(item.reviewer)}</small></button>`).join('');
  recordList.querySelectorAll('[data-record-id]').forEach(button => button.addEventListener('click', () => renderRecords(button.dataset.recordId)));
  renderRecordDetail(selected);
}

function renderRecordDetail(record) {
  const metricRows = record.metrics.map(metric => `<tr><td>${metricLabels[metric.key]}</td><td>${metric.value} ${metricUnits[metric.key]}</td><td>${metric.mean.toFixed(1)}</td><td>${signed(metric.deltaPct)}%</td><td>${metric.severity}</td></tr>`).join('');
  recordDetail.innerHTML = `<div class="detail-status"><div><p class="eyebrow">${record.id}</p><h3>식각 장비 이상 조사 기록</h3></div><span class="approved-badge">승인 완료</span></div>
    <div class="detail-meta"><div><span>대상 설비</span><strong>${[record.context.equipment,record.context.chamber,record.context.recipe].filter(Boolean).join(' / ')}</strong></div><div><span>발생 시각</span><strong>${formatDate(record.eventTime)}</strong></div><div><span>Lot ID</span><strong>${escapeHtml(record.lotId)}</strong></div></div>
    <h4>이상 현상</h4><p class="answer-summary">${escapeHtml(record.context.symptom)}</p>
    <h4>수치 분석</h4><table><thead><tr><th>지표</th><th>현재값</th><th>비교군 평균</th><th>편차</th><th>판정</th></tr></thead><tbody>${metricRows || '<tr><td colspan="5">계측값 미제공</td></tr>'}</tbody></table>
    <h4>우선 확인 가설</h4><ul class="detail-evidence">${record.causes.map(item => `<li><strong>${escapeHtml(item.cause)}</strong> — ${escapeHtml(item.action)} [${item.id}]</li>`).join('')}</ul>
    <h4>문서 근거</h4><ul class="detail-evidence">${record.documents.map(item => `<li><strong>${item.id}</strong> ${escapeHtml(item.title)}</li>`).join('')}</ul>
    <div class="review-signoff"><strong>검토자 ${escapeHtml(record.reviewer)}</strong> · ${formatDate(record.approvedAt)} 승인</div>`;
}

function updateRecordCount(count=getRecords().length) {
  document.getElementById('recordNavCount').textContent = count;
  document.getElementById('recordCount').textContent = `${count}건`;
}

function formatDate(value) {
  if (!value) return '미제공';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('ko-KR',{dateStyle:'medium',timeStyle:'short'}).format(date);
}

function addUserMessage(text) { conversation.insertAdjacentHTML('beforeend', `<div class="message user-message"><div class="avatar">나</div><div class="message-body"><p>${escapeHtml(text)}</p></div></div>`); scrollEnd(); }
function addAssistant(html) { conversation.insertAdjacentHTML('beforeend', `<div class="message assistant-message"><div class="avatar">AI</div><div class="message-body">${html}</div></div>`); scrollEnd(); }
function addThinking(label='질문을 이해하고 있습니다') { const el=document.createElement('div'); el.className='message assistant-message'; el.innerHTML=`<div class="avatar">AI</div><div class="message-body"><p class="message-label">${label}</p><div class="thinking"><i></i><i></i><i></i></div></div>`; conversation.appendChild(el); scrollEnd(); return el; }
function setStep(index) { document.querySelectorAll('#steps li').forEach((li,i) => {li.classList.toggle('active',i===index-1); li.classList.toggle('done',i<index-1);}); }
function highlightEvidence(id) { evidencePanel.classList.add('open'); const item=document.querySelector(`[data-evidence-id="${CSS.escape(id)}"]`); if (!item) return; document.querySelectorAll('.evidence-item').forEach(el=>el.classList.remove('highlight')); item.classList.add('highlight'); item.scrollIntoView({behavior:'smooth',block:'center'}); setTimeout(()=>item.classList.remove('highlight'),1800); }
function resetInvestigation() { state.context={}; state.lastAnalysis=null; conversation.querySelectorAll('.message:not(.intro-message)').forEach(el=>el.remove()); emptyEvidence.hidden=false; evidenceContent.hidden=true; evidenceContent.innerHTML=''; document.getElementById('evidenceCount').textContent='0'; setStep(1); input.focus(); }
function showToast(text) { const toast=document.getElementById('toast'); toast.textContent=text; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),3000); }
function signed(value) { return `${value>=0?'+':''}${value.toFixed(2)}`; }
function wait(ms) { return new Promise(resolve=>setTimeout(resolve,ms)); }
function scrollEnd() { requestAnimationFrame(()=>conversation.scrollTo({top:conversation.scrollHeight,behavior:'smooth'})); }
function escapeHtml(value) { const div=document.createElement('div'); div.textContent=value; return div.innerHTML; }

updateRecordCount();
