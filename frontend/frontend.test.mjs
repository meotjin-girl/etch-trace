import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const apiSource = await readFile(new URL('./api.js', import.meta.url), 'utf8');
const {createApi, mergeEvents, streamUrl, ApiError} = await import(
  `data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`
);
const identity = {name:'이엔지니어', role:'engineer'};

test('HTTP contract: encoded actor, routes, JSON bodies and abort signals', async () => {
  const calls = [];
  const controller = new AbortController();
  const api = createApi(identity, {fetch:async (url, options) => {
    calls.push({url, ...options});
    return new Response('{"taskId":"t/1"}', {status:202});
  }});
  await api.create('질문', controller.signal);
  await api.message('t/1', '추가 정보', controller.signal);
  await api.approval('t/1', {action:'revise', comment:'확인'}, controller.signal);
  await api.list(controller.signal);
  await api.detail('t/1', controller.signal);
  await api.events('t/1', 7, controller.signal);
  assert.equal(calls[0].headers['X-User-Name'], encodeURIComponent(identity.name));
  assert.equal(calls[0].headers['X-User-Role'], 'engineer');
  assert.deepEqual(JSON.parse(calls[0].body), {question:'질문'});
  assert.deepEqual(JSON.parse(calls[1].body), {text:'추가 정보'});
  assert.equal(calls[2].url, '/api/ai/tasks/t%2F1/approval');
  assert.equal(calls[3].method, 'GET');
  assert.equal(calls[4].url, '/api/ai/tasks/t%2F1');
  assert.equal(calls[5].url, '/api/ai/tasks/t%2F1/events?after=7');
  assert.ok(calls.every(call => call.signal === controller.signal));
});

test('errors retain server denial and distinguish cancellation/network/bad JSON', async () => {
  await assert.rejects(createApi(identity, {fetch:async () =>
    new Response('{"detail":"engineer only"}', {status:403})}).list(),
  error => error instanceof ApiError && error.status === 403 && error.message === 'engineer only');
  await assert.rejects(createApi(identity, {fetch:async () => {throw new TypeError('offline');}}).list(), ApiError);
  await assert.rejects(createApi(identity, {fetch:async () => new Response('<html>')}).list(), ApiError);
  const abort = new DOMException('cancelled', 'AbortError');
  await assert.rejects(createApi(identity, {fetch:async () => {throw abort;}}).list(), error => error === abort);
});

class FakeSource {
  static instances = [];
  constructor(url) { this.url = url; this.listeners = {}; FakeSource.instances.push(this); }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  close() { this.closed = true; }
  emit(type, data, id = '') { this.listeners[type]({type, data:JSON.stringify(data), lastEventId:id}); }
}
test('SSE identity, payload variants, close on abort and explicit reconnect cursor', () => {
  const api = createApi(identity, {EventSource:FakeSource});
  const controller = new AbortController();
  const events = [];
  api.stream('a', 4, {signal:controller.signal, onEvent:event => events.push(event), onError:assert.fail});
  const source = FakeSource.instances.at(-1);
  const url = new URL(source.url, 'https://example.test');
  assert.equal(url.searchParams.get('user_name'), identity.name);
  assert.equal(url.searchParams.get('user_role'), 'engineer');
  assert.equal(url.searchParams.get('after'), '4');
  source.emit('QUESTION', {text:'장비?', missing:['tool']}, '5');
  source.emit('DONE', {seq:6, type:'DONE', payload:{report:{demo:true}}});
  assert.equal(events[0].seq, 5);
  assert.equal(events[0].payload.text, '장비?');
  assert.equal(events[1].payload.report.demo, true);
  controller.abort();
  assert.equal(source.closed, true);
  source.emit('DONE', {seq:7});
  assert.equal(events.length, 2);
  assert.match(streamUrl('a', identity, 6), /after=6/);
});
test('SSE malformed events and disconnect become recoverable errors', () => {
  const errors = [];
  const api = createApi(identity, {EventSource:FakeSource});
  api.stream('a', 0, {onEvent:assert.fail, onError:error => errors.push(error)});
  let source = FakeSource.instances.at(-1);
  source.emit('DONE', {});
  assert.equal(source.closed, true);
  api.stream('a', 0, {onEvent:assert.fail, onError:error => errors.push(error)});
  source = FakeSource.instances.at(-1);
  source.onerror();
  assert.equal(source.closed, true);
  assert.equal(errors.length, 2);
});
test('event replay merges and deduplicates numeric sequence', () => {
  const events = mergeEvents([{seq:2, type:'RUNNING'}], [
    {seq:1, type:'QUEUED'}, {seq:'2', type:'RUNNING'}, {seq:3, type:'QUESTION'}, {seq:0}
  ]);
  assert.deepEqual(events.map(event => event.seq), [1, 2, 3]);
});

// A tiny DOM boundary exercises controller behavior without adding a framework.
const appSource = await readFile(new URL('./app.js', import.meta.url), 'utf8');
function harness(storedRecords = null) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value:'', innerHTML:'', textContent:'', hidden:false, disabled:false, style:{},
      classList:{add(){}, remove(){}, toggle(){}}, dataset:{},
      addEventListener(){}, setAttribute(){}, focus(){}, close(){this.open = false;},
      showModal(){this.open = true;}, querySelectorAll(){return [];}, scrollIntoView(){}
    });
    return elements.get(id);
  }
  const calls = [];
  const api = {
    async history(){return [];}, async list(){return [];}, async detail(id){return {id, status:'WAITING_INPUT', user_name:identity.name, user_role:identity.role, events:[]};},
    async create(question){calls.push(['create', question]); return {taskId:'task-1'};},
    async message(id, value){calls.push(['message', id, value]);},
    async approval(id, body){calls.push(['approval', id, body]);},
    stream(){return () => calls.push(['close']);}
  };
  const context = vm.createContext({
    createApi:() => api, mountSops(){}, mergeEvents, AbortController, console, Intl, Date,
    document:{getElementById:element, querySelector:element, querySelectorAll(){return [];}, addEventListener(){}},
    window:{addEventListener(){}}, localStorage:{getItem(){return storedRecords;}},
    matchMedia:() => ({matches:true})
  });
  vm.runInContext(appSource.replace(/^import .*;\n/gm, '') +
    '\nglobalThis.hooks = {state, selectRecord, renderRecords, recordTitle, renderDetail, legacyRecords, isOwner, openEvidence, renderReport, renderConversation, canReview, submitQuestion, resetInvestigation, openReview, submitReview, syncTask, connectStream};', context);
  return {hooks:context.hooks, element, calls, api};
}
test('all report input is escaped including attributes and numeric fallbacks', () => {
  const {hooks} = harness();
  const attack = '<img src=x onerror=alert(1)>"';
  const html = hooks.renderReport({context:{equipment:attack}, summary:attack,
    metrics:[{key:attack, value:attack, severity:attack}],
    causeCases:[{id:attack, cause:attack, action:attack, docs:[attack]}], docIds:[attack]});
  assert.ok(!html.includes('<img'));
  assert.ok(html.includes('&lt;img'));
  assert.ok(html.includes('&quot;'));
  assert.ok(!html.includes('NaN'));
});
test('persisted clarification and its replay event render one assistant message', () => {
  const {hooks, element} = harness();
  hooks.state.task = {
    id:'a', status:'WAITING_INPUT',
    messages:[{role:'assistant', text:'fixture-followup'}]
  };
  hooks.state.events = [{seq:1, type:'QUESTION', payload:{text:'fixture-followup'}}];
  hooks.renderConversation();
  assert.equal(
    (element('conversation').innerHTML.match(/assistant-message/g) || []).length, 1
  );
});
test('review permissions: engineer waiting only, not worker/admin/legacy', () => {
  const {hooks} = harness();
  const task = {status:'WAITING_APPROVAL'};
  assert.equal(hooks.canReview(task), true);
  for (const role of ['worker', 'admin']) {
    hooks.state.identity.role = role;
    assert.equal(hooks.canReview(task), false);
  }
  hooks.state.identity.role = 'engineer';
  assert.equal(hooks.canReview({...task, legacy:true}), false);
  assert.equal(hooks.canReview({status:'DONE'}), false);
});
test('owner identity survives a role change and modal citations expose evidence', () => {
  const {hooks, element} = harness();
  hooks.state.identity.role = 'worker';
  assert.equal(hooks.isOwner({user_name:identity.name, user_role:'engineer'}), true);
  assert.equal(hooks.isOwner({user_name:'another-worker', user_role:'worker'}), false);
  element('reportDialog').open = true;
  hooks.openEvidence('DOC#1');
  assert.equal(element('reportDialog').open, false);
});
test('old local records stay read-only and never become authoritative approvals', () => {
  const {hooks} = harness(JSON.stringify([{
    id:'OLD-1', context:{equipment:'ETCH-07', symptom:'fixture'},
    metrics:[], causes:[], documents:[{id:'DOC#1', title:'fixture', text:'fixture'}]
  }]));
  const [record] = hooks.legacyRecords();
  assert.equal(record.legacy, true);
  assert.equal(record.legacyId, 'OLD-1');
  assert.equal(hooks.canReview(record), false);
  assert.equal(record.report.documents[0].id, 'DOC#1');
});
test('send creates once, continues only owned waiting task, reset aborts old work', async () => {
  const {hooks, element, calls} = harness();
  element('questionInput').value = '새 질문';
  await hooks.submitQuestion({preventDefault(){}});
  assert.deepEqual(calls[0], ['create', '새 질문']);
  element('questionInput').value = '추가';
  await hooks.submitQuestion({preventDefault(){}});
  assert.deepEqual(calls.find(call => call[0] === 'message'), ['message', 'task-1', '추가']);
  const signal = hooks.state.controller.signal;
  hooks.resetInvestigation();
  assert.equal(signal.aborted, true);
  assert.equal(hooks.state.task, null);
  assert.equal(hooks.state.after, 0);
});
test('review sends server actor metadata and revise requires comment', async () => {
  const {hooks, element, calls} = harness();
  hooks.openReview({id:'a', status:'WAITING_APPROVAL', report:{}});
  assert.equal(element('recordReviewer').value, identity.name);
  await hooks.submitReview({preventDefault(){}, submitter:{value:'revise'}});
  assert.equal(calls.length, 0);
  element('reviewComment').value = '다시 확인';
  element('recordTime').value = '2026-10-20T10:00';
  element('recordLot').value = 'LOT-1';
  await hooks.submitReview({preventDefault(){}, submitter:{value:'revise'}});
  const call = calls.find(item => item[0] === 'approval');
  assert.equal(call[2].action, 'revise');
  assert.equal(call[2].comment, '다시 확인');
  assert.equal(call[2].lot_id, 'LOT-1');
  assert.ok(call[2].event_time.endsWith('Z'));
});
test('detail status survives replay of an old approval after revision', async () => {
  const {hooks, api} = harness();
  hooks.state.task = {id:'a', status:'RUNNING'};
  hooks.state.events = [{seq:1, type:'APPROVAL_REQUIRED', payload:{}}];
  hooks.state.after = 1;
  api.detail = async () => ({id:'a', status:'RUNNING', events:hooks.state.events});
  await hooks.syncTask();
  assert.equal(hooks.state.task.status, 'RUNNING');
});
test('late live callbacks cannot bleed into a new investigation', () => {
  const {hooks, api} = harness();
  let receive;
  api.stream = (id, after, handlers) => {receive = handlers.onEvent; return () => {};};
  hooks.state.task = {id:'a', status:'RUNNING'};
  hooks.connectStream();
  hooks.resetInvestigation();
  receive({seq:1, type:'DONE', payload:{report:{summary:'old'}}});
  assert.equal(hooks.state.task, null);
});
test('pending create disables duplicate sends without timing waits', async () => {
  const {hooks, api, element, calls} = harness();
  let accept;
  api.create = question => {
    calls.push(['create', question]);
    return new Promise(resolve => {accept = resolve;});
  };
  element('questionInput').value = '한 번만';
  const pending = hooks.submitQuestion({preventDefault(){}});
  await hooks.submitQuestion({preventDefault(){}});
  assert.equal(calls.filter(call => call[0] === 'create').length, 1);
  accept({taskId:'one'});
  await pending;
});
test('newer detail requests win even if older requests finish later', async () => {
  const {hooks, api} = harness();
  hooks.state.task = {id:'a', status:'RUNNING'};
  const responses = [];
  api.detail = () => new Promise(resolve => responses.push(resolve));
  const first = hooks.syncTask();
  const second = hooks.syncTask();
  responses[1]({id:'a', status:'DONE', events:[]});
  await second;
  responses[0]({id:'a', status:'RUNNING', events:[]});
  await first;
  assert.equal(hooks.state.task.status, 'DONE');
});
test('live events arriving during a detail request retain their newer state', async () => {
  const {hooks, api} = harness();
  hooks.state.task = {id:'a', status:'RUNNING'};
  let complete;
  api.detail = () => new Promise(resolve => {complete = resolve;});
  const pending = hooks.syncTask();
  hooks.state.after = 2;
  hooks.state.events = [{seq:2, type:'APPROVAL_REQUIRED', payload:{report:{summary:'new'}}}];
  hooks.state.task.status = 'WAITING_APPROVAL';
  hooks.state.task.report = {summary:'new'};
  complete({id:'a', status:'RUNNING', events:[]});
  await pending;
  assert.equal(hooks.state.task.status, 'WAITING_APPROVAL');
  assert.equal(hooks.state.task.report.summary, 'new');
});


test('history list and detail use the dedicated history gateway', async () => {
  const calls = [];
  const api = createApi({name:'작업자', role:'worker'}, {
    fetch: async (url, options) => {
      calls.push({url, options});
      return {ok:true, status:200, text:async () => '[]'};
    }
  });
  await api.history();
  await api.historyDetail('task/1');
  assert.equal(calls[0].url, '/api/ai/investigations');
  assert.equal(calls[1].url, '/api/ai/investigations/task%2F1');
  assert.equal(calls[0].options.headers['X-User-Name'], encodeURIComponent('작업자'));
});


test('saved history displays the approved report without conversation timeline', () => {
  const {hooks, element} = harness();
  hooks.renderDetail({
    id:'saved-1', status:'DONE', question:'endpoint 지연',
    report:{summary:'승인된 조사 결과'}, approved_by:'엔지니어', lot_id:'LOT-1',
    messages:[{text:'private-conversation'}],
    events:[{seq:1, type:'QUESTION', payload:{text:'private-event'}}],
    reviews:[{comment:'private-review'}]
  });
  const html = element('recordDetail').innerHTML;
  assert.ok(html.includes('승인된 조사 결과'));
  assert.ok(html.includes('LOT-1'));
  assert.ok(!html.includes('private-conversation'));
  assert.ok(!html.includes('private-event'));
  assert.ok(!html.includes('private-review'));
  assert.ok(!html.includes('class="timeline"'));
});


test('history titles describe the report and retain internal IDs only for selection', () => {
  const {hooks, element} = harness();
  const record = {id:'b99436a6-8282-4760-8ba5-1e8e4caeba93', status:'DONE',
    report:{context:{equipment:'ETCH-07', symptom:'endpoint 지연'}, summary:'조사 요약'}};
  assert.equal(hooks.recordTitle(record), 'ETCH-07 · endpoint 지연');
  assert.equal(hooks.recordTitle({report:{summary:'장비 점검 필요'}}), '장비 점검 필요');
  assert.equal(hooks.recordTitle({id:record.id}), '조사 결과');
  hooks.state.records = [record];
  hooks.renderRecords();
  assert.ok(element('recordList').innerHTML.includes('<strong>ETCH-07 · endpoint 지연</strong>'));
  assert.ok(element('recordList').innerHTML.includes(`data-record-id="${record.id}"`));
  hooks.renderDetail(record);
  assert.ok(element('recordDetail').innerHTML.includes('<h3>ETCH-07 · endpoint 지연</h3>'));
  assert.ok(!element('recordDetail').innerHTML.includes(record.id));
});


test('approval completed before stream reconnect immediately refreshes history count', async () => {
  const {hooks, api, element} = harness();
  const saved = {id:'a', status:'DONE', report:{summary:'승인 결과'}};
  hooks.state.task = {id:'a', status:'WAITING_APPROVAL', report:{}};
  hooks.openReview(hooks.state.task);
  let stored = false;
  api.approval = async () => {stored = true;};
  // Model an older list snapshot returned just after approval acceptance.
  let reads = 0;
  api.history = async () => ++reads === 1 ? [] : [saved];
  api.detail = async () => ({...saved, events:[]});
  await hooks.submitReview({preventDefault(){}, submitter:{value:'approve'}});
  assert.equal(stored, true);
  assert.equal(hooks.state.task.status, 'DONE');
  assert.equal(element('recordNavCount').textContent, 1);
  assert.equal(reads, 2);
});

test('live completion updates history count without opening the history panel', async () => {
  const {hooks, api, element} = harness();
  hooks.state.task = {id:'a', status:'RUNNING'};
  let receive, deliver;
  api.stream = (id, after, handlers) => {receive = handlers.onEvent; return () => {};};
  api.history = () => new Promise(resolve => {deliver = resolve;});
  api.detail = async () => ({id:'a', status:'DONE', events:[]});
  hooks.connectStream();
  receive({seq:1, type:'DONE', payload:{report:{summary:'저장됨'}}});
  deliver([{id:'a', status:'DONE', report:{summary:'저장됨'}}]);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(element('recordNavCount').textContent, 1);
});


test('record selection shows saved report immediately and ignores late detail replies', async () => {
  const {hooks, api, element} = harness();
  hooks.state.records = [
    {id:'a', report:{summary:'첫 번째 결과'}},
    {id:'b', report:{summary:'두 번째 결과'}}
  ];
  const replies = {};
  api.historyDetail = id => new Promise(resolve => {replies[id] = resolve;});
  const first = hooks.selectRecord('a');
  assert.ok(element('recordDetail').innerHTML.includes('첫 번째 결과'));
  const second = hooks.selectRecord('b');
  assert.ok(element('recordDetail').innerHTML.includes('두 번째 결과'));
  replies.b({id:'b', report:{summary:'두 번째 최신 결과'}});
  await second;
  replies.a({id:'a', report:{summary:'오래된 응답'}});
  await first;
  assert.equal(hooks.state.selected.id, 'b');
  assert.ok(element('recordDetail').innerHTML.includes('두 번째 최신 결과'));
});

test('failed detail refresh keeps the saved report readable', async () => {
  const {hooks, api, element} = harness();
  hooks.state.records = [{id:'a', report:{summary:'저장된 조사 결과'}}];
  api.historyDetail = async () => {throw new Error('조회 실패');};
  await hooks.selectRecord('a');
  assert.ok(element('recordDetail').innerHTML.includes('저장된 조사 결과'));
  assert.equal(element('networkMessage').textContent, '조회 실패');
});
