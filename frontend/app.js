import {createApi, mergeEvents} from './api.js';
import {mountSops} from './sop.js';

const $ = id => document.getElementById(id);
const labels = {endpoint_sec:'Endpoint', etch_rate_nm_min:'Etch rate', rf_reflected_w:'RF reflected', pressure_mtorr:'Pressure'};
const units = {endpoint_sec:'sec', etch_rate_nm_min:'nm/min', rf_reflected_w:'W', pressure_mtorr:'mTorr'};
const statuses = {
  QUEUED:'접수됨', RUNNING:'조사 중', SEARCH_STARTED:'근거 검색 중',
  ANALYSIS_STARTED:'수치 분석 중', REPORT_STARTED:'보고서 작성 중',
  WAITING_INPUT:'추가 정보 대기', WAITING_APPROVAL:'엔지니어 검토 대기',
  DONE:'완료', INCOMPLETE:'근거 부족', FAILED:'실패', REVIEWED:'검토됨', LOADING:'조사 불러오는 중'
};
const terminal = new Set(['DONE', 'INCOMPLETE', 'FAILED']);
const intro = $('conversation').innerHTML;
const state = {
  identity: {name:'이엔지니어', role:'engineer'}, api:null,
  task:null, selected:null, records:[], events:[], after:0,
  controller:new AbortController(), listController:null, detailController:null,
  closeStream:null, busy:false, reviewBusy:false, reviewTask:null, epoch:0, syncVersion:0
};
state.api = createApi(state.identity);

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  })[char]);
}
function text(value) {
  return typeof value === 'string' ? value : value == null ? '' : JSON.stringify(value, null, 2);
}
function date(value) {
  if (!value) return '미제공';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) :
    new Intl.DateTimeFormat('ko-KR', {dateStyle:'medium', timeStyle:'short'}).format(parsed);
}
const number = value => Number.isFinite(value) ? value.toFixed(2) : '미제공';
function notify(error) {
  if (error.name === 'AbortError') return;
  $('networkMessage').textContent = error.message;
  $('networkNotice').hidden = false;
}
function clearError() { $('networkNotice').hidden = true; }
function isOwner(task) {
  return task?.user_name === state.identity.name;
}
function canReview(task) {
  return state.identity.role === 'engineer' && task?.status === 'WAITING_APPROVAL' && !task.legacy;
}
function stopTask() {
  state.epoch++;
  state.detailController?.abort();
  state.controller.abort();
  state.controller = new AbortController();
  state.closeStream?.();
  state.closeStream = null;
  state.busy = false;
  state.reviewBusy = false;
  state.reviewTask = null;
  $('reportDialog').close();
}
function setPage(page) {
  const records = page === true;
  const sop = page === 'sop';
  $('recordsPage').hidden = !records;
  $('sopPage').hidden = !sop;
  $('conversation').hidden = records || sop;
  $('questionForm').hidden = records || sop;
  $('recordsNav').classList.toggle('active', records);
  $('sopNav').classList.toggle('active', sop);
  $('investigationNav').classList.toggle('active', !records && !sop);
  document.querySelector('.app-shell').classList.toggle('sop-open', sop);
  document.querySelector('.topbar-actions').hidden = sop;
  document.querySelector('.topbar h1').textContent = sop ? 'SOP 목록' : records ? '조사 기록' : '식각 장비 이상 조사';
}
function resetInvestigation() {
  stopTask();
  state.task = null;
  state.selected = null;
  state.events = [];
  state.after = 0;
  $('conversation').innerHTML = intro;
  $('questionInput').value = '';
  clearError();
  renderEvidence(null);
  setPage(false);
  updateControls();
  $('questionInput').focus();
}
function updateControls() {
  const task = state.task;
  const blocked = task && !(task.status === 'WAITING_INPUT' && isOwner(task));
  $('questionInput').disabled = state.busy || Boolean(blocked);
  document.querySelector('.send-button').disabled = state.busy || Boolean(blocked);
  $('taskStatus').textContent = state.busy ? '요청 전송 중' :
    task ? `${statuses[task.status] || task.status} · ${task.id}` : '질문을 입력해 주세요';
  $('questionInput').placeholder = task?.status === 'WAITING_INPUT' ?
    (isOwner(task) ? '추가 정보를 입력해 주세요…' : '조사 소유자만 추가 정보를 보낼 수 있습니다') :
    task ? '새 질문은 새 조사를 시작해 주세요' : '특정 이상에 대해 질문해 주세요…';
  let step = 1;
  for (const event of state.events) {
    if (event.type === 'SEARCH_STARTED') step = 2;
    if (event.type === 'ANALYSIS_STARTED') step = 3;
    if (['REPORT_STARTED', 'APPROVAL_REQUIRED', 'DONE'].includes(event.type)) step = 4;
  }
  if (task?.report) step = 4;
  document.querySelectorAll('#steps li').forEach((li, index) => {
    li.classList.toggle('active', index === step - 1);
    li.classList.toggle('done', index < step - 1);
  });
}
function citation(id) {
  return `<button type="button" class="citation" data-evidence="${escapeHtml(id)}">[${escapeHtml(id)}]</button>`;
}
function renderReport(report, review = false) {
  if (!report) return '';
  const context = report.context || {};
  const metrics = (report.metrics || []).map(metric => `<div class="metric-card">
    <header><strong>${escapeHtml(labels[metric.key] || metric.key)}</strong><span class="severity">${escapeHtml(metric.severity)}</span></header>
    <div class="metric-values"><b>${escapeHtml(metric.value)}</b><span>${escapeHtml(units[metric.key] || '')} · 비교군 평균 ${number(metric.mean)}</span></div>
    <div class="delta">평균 대비 ${number(metric.deltaPct)}% · z-score ${number(metric.z)}</div></div>`).join('');
  const causes = (report.causeCases || []).map((item, index) => `<div class="cause-item">
    <span>${index + 1}</span><div><strong>${escapeHtml(item.cause)}</strong><small>${escapeHtml(item.action)}</small></div><span class="citation">[${escapeHtml(item.id)}]</span>
    <div class="cause-docs">${(item.docs || []).map(citation).join(' ')}</div></div>`).join('');
  return `<p class="message-label">근거 기반 조사 결과${report.demo === true ? ' · 데모 데이터' : ''}</p>
    <h2>${escapeHtml([context.equipment, context.chamber, context.recipe].filter(Boolean).join(' / ') || '조사')} 분석 결과</h2>
    <p class="answer-summary report-text">${escapeHtml(text(report.summary))}</p>
    <div class="analysis-grid">${metrics || '<p>계측값 미제공</p>'}</div>
    <section class="answer-section"><h3>우선 확인할 항목</h3><div class="cause-list">${causes || '<p>원인 후보를 좁힐 근거가 부족합니다.</p>'}</div></section>
    <section class="answer-section"><h3>문서 근거</h3>${(report.docIds || []).map(citation).join(' ')}</section>
    ${review ? '' : '<div class="record-cta"><p><strong>조사 결과를 기록으로 남길까요?</strong><br>서버 검토 상태와 권한을 확인해 승인 또는 수정을 요청합니다.</p><button class="record-button" type="button" data-review>조사 기록 만들기</button></div>'}`;
}
function message(role, content) {
  return `<div class="message ${role === 'user' ? 'user-message' : 'assistant-message'}"><div class="avatar">${role === 'user' ? '나' : 'AI'}</div><div class="message-body">${content}</div></div>`;
}
function renderConversation() {
  const task = state.task;
  if (!task) return;
  const messages = task.messages || [];
  let html = messages.length ? messages.map(item =>
    message(item.role === 'user' ? 'user' : 'assistant', `<p class="report-text">${escapeHtml(text(item.text ?? item.content))}</p>`)).join('') :
    message('user', `<p>${escapeHtml(task.question)}</p>`);
  // QUESTION is the authoritative follow-up prompt, including missing fields.
  html += state.events.filter(event => event.type === 'QUESTION' &&
    !messages.some(item => item.role === 'assistant' &&
      (item.text ?? item.content) === event.payload.text)).map(event =>
    message('assistant', `<p class="message-label">추가 정보 필요</p><p>${escapeHtml(text(event.payload.text))}</p>
      <p>${escapeHtml(text(event.payload.missing))}</p>`)).join('');
  if (task.report) html += message('assistant', renderReport(task.report));
  const last = state.events.at(-1);
  if (last && ['FAILED', 'INCOMPLETE'].includes(last.type)) {
    html += message('assistant', `<p>${escapeHtml(text(last.payload.error ?? last.payload.reason))}</p>`);
  }
  $('conversation').innerHTML = html;
  renderEvidence(task.report);
  updateControls();
}
function renderEvidence(report) {
  const docs = report?.documents || [];
  $('emptyEvidence').hidden = docs.length > 0;
  $('evidenceContent').hidden = !docs.length;
  $('evidenceCount').textContent = docs.length;
  $('evidenceContent').innerHTML = `<section class="evidence-group"><h3>관련 문서 <span>${docs.length}건</span></h3>${docs.map(item =>
      `<article class="evidence-item" data-evidence-id="${escapeHtml(item.id)}"><header><strong>${escapeHtml(item.id)}</strong></header><p class="report-text"><b>${escapeHtml(item.title)}</b><br>${escapeHtml(item.text)}</p></article>`).join('')}</section>`;
}
function openEvidence(id) {
  if ($('reportDialog').open) $('reportDialog').close();
  document.querySelector('.app-shell').classList.remove('evidence-closed');
  $('evidencePanel').classList.add('open');
  $('evidencePanel').setAttribute('aria-hidden', 'false');
  const item = [...$('evidenceContent').querySelectorAll('[data-evidence-id]')]
    .find(element => element.dataset.evidenceId === id);
  $('evidenceContent').querySelectorAll('.highlight').forEach(element => element.classList.remove('highlight'));
  if (item) {
    item.classList.add('highlight');
    item.scrollIntoView({block:'nearest', behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }
}
function applyEvents(events) {
  state.events = mergeEvents(state.events, events);
  state.after = state.events.at(-1)?.seq || 0;
  for (const event of events) {
    const payload = event.payload || {};
    const status = {QUESTION:'WAITING_INPUT', APPROVAL_REQUIRED:'WAITING_APPROVAL'}[event.type];
    if (status) state.task.status = status;
    else if (['QUEUED', 'RUNNING', 'DONE', 'FAILED', 'INCOMPLETE'].includes(event.type)) state.task.status = event.type;
    else if (['SEARCH_STARTED', 'ANALYSIS_STARTED', 'REPORT_STARTED'].includes(event.type)) state.task.status = 'RUNNING';
    if (payload.report) state.task.report = payload.report;
  }
  state.task.events = state.events;
}
function connectStream() {
  const task = state.task;
  if (!task || terminal.has(task.status)) return;
  state.closeStream?.();
  const epoch = state.epoch;
  state.closeStream = state.api.stream(task.id, state.after, {
    signal:state.controller.signal,
    onEvent(event) {
      if (epoch !== state.epoch || event.seq <= state.after) return;
      applyEvents([event]);
      renderConversation();
      if (state.selected?.id === task.id) renderDetail(state.task);
      if (terminal.has(state.task.status)) state.closeStream?.();
      if (['QUESTION', 'APPROVAL_REQUIRED', 'DONE', 'FAILED', 'INCOMPLETE', 'REVIEWED'].includes(event.type)) {
        refreshRecords();
        syncTask(epoch);
      }
    },
    onError(error) { if (epoch === state.epoch) notify(error); }
  });
}
async function syncTask(epoch = state.epoch) {
  const version = ++state.syncVersion;
  const startingSeq = state.after;
  try {
    const detail = await state.api.detail(state.task.id, state.controller.signal);
    if (epoch !== state.epoch || version !== state.syncVersion) return;
    const liveTask = state.task;
    const liveAdvanced = state.after > startingSeq;
    state.events = mergeEvents(detail.events || [], state.events);
    state.after = state.events.at(-1)?.seq || 0;
    // Never derive current status from historical approvals after a revision.
    // Events arriving during this request are newer than its snapshot.
    state.task = {...detail,
      status:liveAdvanced ? liveTask.status : detail.status,
      report:liveAdvanced ? liveTask.report : detail.report || liveTask.report,
      events:state.events};
    renderConversation();
    if (state.selected?.id === detail.id) renderDetail(state.task);
    // Completion may already be in the snapshot before SSE reconnects.
    if (state.task.status === 'DONE' && liveTask.status !== 'DONE') await refreshRecords();
  } catch (error) { if (epoch === state.epoch && version === state.syncVersion) notify(error); }
}
async function activateTask(id) {
  stopTask();
  clearError();
  const epoch = state.epoch;
  state.task = (state.task?.id === id ? state.task : state.records.find(item => item.id === id)) ||
    {id, status:'LOADING'};
  state.events = [];
  state.after = 0;
  state.busy = true;
  renderConversation();
  try {
    const detail = await state.api.detail(id, state.controller.signal);
    if (epoch !== state.epoch) return;
    state.task = detail;
    state.events = mergeEvents([], detail.events || []);
    state.after = state.events.at(-1)?.seq || 0;
    if (detail.status === 'DONE') await refreshRecords();
    if (epoch !== state.epoch) return;
    // Detail status is authoritative; replay only builds chronology/progress.
    renderConversation();
    connectStream();
    setPage(false);
  } catch (error) { if (epoch === state.epoch) notify(error); }
  finally { if (epoch === state.epoch) { state.busy = false; updateControls(); } }
}

async function submitQuestion(event) {
  event.preventDefault();
  const question = $('questionInput').value.trim();
  if (!question || state.busy || $('questionInput').disabled) return;
  const epoch = state.epoch;
  const task = state.task;
  state.busy = true;
  clearError();
  updateControls();
  try {
    if (task) {
      if (task.status !== 'WAITING_INPUT' || !isOwner(task)) return;
      await state.api.message(task.id, question, state.controller.signal);
      if (epoch !== state.epoch) return;
      $('questionInput').value = '';
      await syncTask(epoch);
      connectStream();
    } else {
      const created = await state.api.create(question, state.controller.signal);
      if (epoch !== state.epoch) return;
      // Keep the accepted id even if the first detail request fails.
      state.task = {id:created.taskId, question, status:'QUEUED', user_name:state.identity.name, user_role:state.identity.role};
      $('questionInput').value = '';
      await activateTask(created.taskId);
    }
    refreshRecords();
  } catch (error) { if (epoch === state.epoch) notify(error); }
  finally { if (epoch === state.epoch) { state.busy = false; updateControls(); } }
}
function legacyRecords() {
  try {
    const records = JSON.parse(localStorage.getItem('etch-investigation-records-v1') || '[]');
    return Array.isArray(records) ? records.filter(item => item && typeof item === 'object').map((item, index) => ({
      ...item, id:`legacy-${index}`, legacy:true, legacyId:item.id,
      status:'로컬 미검증', question:item.context?.symptom || '기존 로컬 기록',
      created_at:item.approvedAt,
      report:{context:item.context, metrics:item.metrics, causeCases:item.causes,
        documents:item.documents, docIds:(item.documents || []).map(doc => doc.id),
        summary:'이전 브라우저에서 저장한 읽기 전용 기록입니다. 서버에서 검증된 승인이 아닙니다.'}
    })) : [];
  } catch { return []; }
}
async function refreshRecords() {
  state.listController?.abort();
  const controller = state.listController = new AbortController();
  const api = state.api;
  $('refreshRecords').disabled = true;
  try {
    const records = await api.history(controller.signal);
    if (controller !== state.listController) return;
    state.records = [...records, ...legacyRecords()];
    renderRecords();
    if (!$('recordsPage').hidden && state.selected) selectRecord(state.selected.id);
  } catch (error) {
    if (controller === state.listController) {
      if (!state.records.length) { state.records = legacyRecords(); renderRecords(); }
      notify(error);
    }
  } finally { if (controller === state.listController) $('refreshRecords').disabled = false; }
}
function recordTitle(record) {
  const context = record.report?.context || record.context || {};
  const equipment = typeof context.equipment === 'string' ? context.equipment.trim() : '';
  const symptom = typeof context.symptom === 'string' ? context.symptom.trim() : '';
  const fallback = record.report?.summary || record.question || '조사 결과';
  const title = [equipment, symptom].filter(Boolean).join(' · ') || String(fallback).replace(/\s+/g, ' ').trim() || '조사 결과';
  return title.length > 80 ? `${title.slice(0, 80)}…` : title;
}
function renderRecords() {
  $('recordNavCount').textContent = state.records.filter(item => !item.legacy).length;
  $('recordCount').textContent = `${state.records.length}건 (로컬 포함)`;
  $('recordList').innerHTML = state.records.map(item => `<button type="button" class="record-list-item ${state.selected?.id === item.id ? 'active' : ''}" data-record-id="${escapeHtml(item.id)}" aria-pressed="${state.selected?.id === item.id}">
    <header><strong>${escapeHtml(recordTitle(item))}</strong><span>${escapeHtml(statuses[item.status] || item.status)}</span></header>
    <p>${escapeHtml(item.question)}</p><small>${escapeHtml(date(item.created_at))} · ${escapeHtml(item.user_name || '읽기 전용 로컬 기록')}</small></button>`).join('');
  if (!state.selected) $('recordDetail').innerHTML = `<div class="records-empty"><strong>${state.records.length ? '조사 기록을 선택해 주세요' : '조사 기록이 없습니다'}</strong><p>승인 후 저장된 조사 이력과 기존 로컬 기록을 표시합니다.</p><button type="button" data-start>이상 조사 시작</button></div>`;
}
function highlightRecord(id) {
  $('recordList').querySelectorAll('[data-record-id]').forEach(button => {
    const selected = button.dataset.recordId === id;
    button.classList.toggle('active', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
}
async function selectRecord(id) {
  const item = state.records.find(record => record.id === id);
  if (!item) return;
  state.detailController?.abort();
  const controller = state.detailController = new AbortController();
  const changed = state.selected?.id !== id;
  highlightRecord(id);
  // The list already includes the saved report: show it without a blank loading frame.
  renderDetail(item);
  const panel = $('recordDetail');
  if (changed && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    panel.getAnimations?.().forEach(animation => animation.cancel());
    panel.animate?.([
      {opacity:0.5, transform:'translateY(6px)'},
      {opacity:1, transform:'translateY(0)'}
    ], {duration:180, easing:'ease-out'});
  }
  if (item.legacy) { panel.setAttribute('aria-busy', 'false'); return; }
  panel.setAttribute('aria-busy', 'true');
  panel.classList.add('is-refreshing');
  try {
    const detail = await state.api.historyDetail(id, controller.signal);
    if (controller === state.detailController) renderDetail(detail);
  } catch (error) {
    // Preserve the saved report while allowing another selection or retry.
    if (controller === state.detailController) notify(error);
  } finally {
    if (controller === state.detailController) {
      panel.setAttribute('aria-busy', 'false');
      panel.classList.remove('is-refreshing');
    }
  }
}
function renderDetail(task) {
  state.selected = task;
  $('recordDetail').innerHTML = `<div class="detail-status"><div><p class="eyebrow">조사 결과</p><h3>${escapeHtml(recordTitle(task))}</h3></div><span class="approved-badge">${escapeHtml(statuses[task.status] || task.status)}</span></div>
    <div class="detail-meta"><div><span>요청자</span><strong>${escapeHtml(task.user_name || '기존 로컬 기록')} / ${escapeHtml(task.user_role || '미검증')}</strong></div><div><span>생성</span><strong>${escapeHtml(date(task.created_at))}</strong></div><div><span>최근 갱신</span><strong>${escapeHtml(date(task.updated_at))}</strong></div></div>
    ${task.legacy ? '<p class="data-notice">읽기 전용 로컬 기록 · 서버 검증 승인 아님</p>' : `<div class="detail-meta"><div><span>승인자</span><strong>${escapeHtml(task.approved_by || '')}</strong></div><div><span>승인 시각</span><strong>${escapeHtml(date(task.approved_at))}</strong></div><div><span>LOT</span><strong>${escapeHtml(task.lot_id || '')}</strong></div></div>`}
    ${renderReport(task.report, true)}`;
  renderEvidence(task.report);
}
function openReview(task) {
  if (!task?.report || task.legacy) return;
  state.reviewTask = task;
  $('recordReviewer').value = state.identity.name;
  $('recordTime').value = '';
  $('recordLot').value = '';
  $('reviewComment').value = '';
  $('reportPreview').innerHTML = renderReport(task.report, true);
  $('reviewNotice').textContent = canReview(task) ? '엔지니어 권한으로 서버에 검토를 제출합니다.' : '검토 대기 상태의 조사만 엔지니어가 승인하거나 수정 요청할 수 있습니다. 현재는 읽기 전용입니다.';
  $('approveReport').disabled = $('reviseReport').disabled = !canReview(task);
  $('reportDialog').showModal();
}
async function submitReview(event) {
  event.preventDefault();
  const task = state.reviewTask;
  if (!canReview(task) || state.reviewBusy) return;
  const action = event.submitter?.value;
  if (!['approve', 'revise'].includes(action)) return;
  const comment = $('reviewComment').value.trim();
  if (action === 'revise' && !comment) {
    $('reviewNotice').textContent = '수정 요청 의견을 입력해 주세요.';
    $('reviewComment').focus();
    return;
  }
  const epoch = state.epoch;
  state.reviewBusy = true;
  $('approveReport').disabled = $('reviseReport').disabled = true;
  try {
    const eventTime = $('recordTime').value;
    await state.api.approval(task.id, {
      action, comment,
      ...(eventTime ? {event_time:new Date(eventTime).toISOString()} : {}),
      ...($('recordLot').value.trim() ? {lot_id:$('recordLot').value.trim()} : {})
    }, state.controller.signal);
    if (epoch !== state.epoch) return;
    $('reportDialog').close();
    await refreshRecords();
    if (state.task?.id === task.id) {
      await syncTask(epoch);
      connectStream();
    }
    if (state.selected?.id === task.id) await selectRecord(task.id);
  } catch (error) { if (epoch === state.epoch) { notify(error); $('reviewNotice').textContent = error.message; } }
  finally {
    if (epoch === state.epoch) {
      state.reviewBusy = false;
      $('approveReport').disabled = $('reviseReport').disabled = !canReview(state.reviewTask);
    }
  }
}
function changeIdentity() {
  const name = $('userName').value.trim() || state.identity.name;
  $('userName').value = name;
  state.listController?.abort();
  state.detailController?.abort();
  resetInvestigation();
  state.identity = {name, role:$('userRole').value};
  state.api = createApi(state.identity);
  state.records = [];
  state.selected = null;
  renderRecords();
  refreshRecords();
}
$('questionForm').addEventListener('submit', submitQuestion);
$('questionInput').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $('questionForm').requestSubmit();
  }
});
$('questionInput').addEventListener('input', () => {
  $('questionInput').style.height = 'auto';
  $('questionInput').style.height = `${Math.min($('questionInput').scrollHeight, 140)}px`;
});
document.addEventListener('click', event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.prompt) { $('questionInput').value = button.dataset.prompt; $('questionInput').focus(); }
  if (button.hasAttribute('data-evidence')) openEvidence(button.dataset.evidence);
  if (button.hasAttribute('data-review')) openReview(state.task);
  if (button.hasAttribute('data-detail-review')) openReview(state.selected);
  if (button.dataset.recordId) selectRecord(button.dataset.recordId);
  if (button.dataset.resume) activateTask(button.dataset.resume);
  if (button.hasAttribute('data-start')) { resetInvestigation(); }
});
for (const id of ['newInvestigation', 'mobileNew']) $(id).addEventListener('click', resetInvestigation);
for (const id of ['investigationNav', 'mobileInvestigation', 'emptyStartInvestigation']) $(id).addEventListener('click', () => { setPage(false); renderEvidence(state.task?.report); });
for (const id of ['recordsNav', 'mobileRecords']) $(id).addEventListener('click', () => { setPage(true); refreshRecords(); });
for (const id of ['sopNav', 'mobileSop']) $(id).addEventListener('click', () => setPage('sop'));
$('refreshRecords').addEventListener('click', () => { clearError(); refreshRecords(); });
$('openEvidence').addEventListener('click', () => openEvidence());
$('closeEvidence').addEventListener('click', () => {
  document.querySelector('.app-shell').classList.add('evidence-closed');
  $('evidencePanel').classList.remove('open');
  $('evidencePanel').setAttribute('aria-hidden', 'true');
});
$('reviewForm').addEventListener('submit', submitReview);
for (const id of ['closeReport', 'cancelReport']) $(id).addEventListener('click', () => $('reportDialog').close());
$('userName').addEventListener('change', changeIdentity);
$('userRole').addEventListener('change', changeIdentity);
$('retryConnection').addEventListener('click', async () => {
  clearError();
  if (state.task) {
    const epoch = state.epoch;
    try {
      const events = await state.api.events(state.task.id, state.after, state.controller.signal);
      if (epoch !== state.epoch) return;
      applyEvents(events.filter(event => Number(event.seq) > state.after));
      await syncTask(epoch);
      if (epoch === state.epoch) connectStream();
    } catch (error) { if (epoch === state.epoch) notify(error); }
  }
  refreshRecords();
});
window.addEventListener('pagehide', () => {
  stopTask();
  state.listController?.abort();
  state.detailController?.abort();
});
updateControls();
refreshRecords();
mountSops();
