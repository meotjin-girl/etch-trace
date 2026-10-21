import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const apiSource = await readFile(new URL('./api.js', import.meta.url), 'utf8');
const {createApi, mergeEvents, streamUrl, ApiError, readEventStream} = await import(
  `data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`
);
const identity = {name:'이엔지니어', role:'engineer'};
const authenticated = {async getToken(){return 'access-token';}, invalidate(){}};
const {createAuth} = await import('./auth.js');

function authHarness({signedIn = true, configStatus = 200} = {}) {
  const changes = [], calls = [];
  let client;
  class FakeKeycloak {
    constructor(config) {
      this.config = config;
      this.authenticated = signedIn;
      this.token = signedIn ? 'access-token' : undefined;
      this.tokenParsed = {name:identity.name, preferred_username:'username'};
      client = this;
    }
    async init(options) {calls.push(['init', options]); return this.authenticated;}
    async updateToken(seconds) {calls.push(['refresh', seconds]);}
    async login(options) {calls.push(['login', options]);}
    async logout(options) {calls.push(['logout', options]);}
    clearToken() {
      this.token = undefined;
      this.authenticated = false;
      this.onAuthLogout?.();
    }
  }
  const auth = createAuth({
    fetch:async (url, options) => {
      calls.push(['config', url, options]);
      return new Response(JSON.stringify({url:'https://id.example.test', realm:'trace', clientId:'web'}),
        {status:configStatus});
    },
    loadKeycloak:async () => ({default:FakeKeycloak}),
    redirectUri:'https://app.example.test/',
    onChange:session => changes.push(session)
  });
  return {auth, calls, changes, get client(){return client;}};
}
test('Keycloak config and PKCE standard flow keep actor display separate from requests', async () => {
  const {auth, calls, client:before} = authHarness();
  assert.equal(before, undefined);
  await auth.init();
  assert.equal(auth.session.status, 'authenticated');
  assert.equal(auth.session.name, identity.name);
  assert.deepEqual(calls[0], ['config', '/api/auth/config', {cache:'no-store'}]);
  assert.deepEqual(calls[1][1], {
    onLoad:'check-sso', flow:'standard', pkceMethod:'S256',
    responseMode:'fragment', redirectUri:'https://app.example.test/', logoutMethod:'POST'
  });
  assert.equal(await auth.getToken(), 'access-token');
  assert.deepEqual(calls.at(-1), ['refresh', 30]);
});
test('anonymous login, config retry and POST logout expose session states', async () => {
  const anonymous = authHarness({signedIn:false});
  await anonymous.auth.init();
  assert.equal(anonymous.auth.session.status, 'anonymous');
  await anonymous.auth.login();
  assert.equal(anonymous.calls.at(-1)[0], 'login');
  const failed = authHarness({configStatus:503});
  await failed.auth.init();
  assert.equal(failed.auth.session.status, 'error');
  assert.equal(failed.client, undefined);
  const signedIn = authHarness();
  await signedIn.auth.init();
  await signedIn.auth.logout();
  assert.equal(signedIn.auth.session.status, 'anonymous');
  assert.equal(signedIn.client.token, undefined);
  assert.deepEqual(signedIn.calls.at(-1), ['logout', {
    redirectUri:'https://app.example.test/', logoutMethod:'POST'
  }]);
});
test('refresh failure invalidates session and never reaches backend', async () => {
  const fixture = authHarness();
  await fixture.auth.init();
  fixture.client.updateToken = async () => {throw new Error('expired');};
  let calls = 0;
  const api = createApi(fixture.auth, {fetch:async () => {calls++;}});
  await assert.rejects(api.list());
  assert.equal(calls, 0);
  assert.equal(fixture.auth.session.status, 'anonymous');
  assert.equal(fixture.client.token, undefined);
  await assert.rejects(fixture.auth.getToken());
});
test('pending login prevents duplicate redirects and reports navigation failure', async () => {
  const fixture = authHarness({signedIn:false});
  await fixture.auth.init();
  const navigation = Promise.withResolvers();
  let redirects = 0;
  fixture.client.login = () => { redirects++; return navigation.promise; };
  const pending = fixture.auth.login();
  await fixture.auth.login();
  assert.equal(redirects, 1);
  assert.equal(fixture.auth.session.status, 'redirecting');
  navigation.reject(new Error('navigation failed'));
  await pending;
  assert.equal(fixture.auth.session.status, 'error');
});
test('session logout callback invalidates and pending refresh cannot reauthorize', async () => {
  const fixture = authHarness();
  await fixture.auth.init();
  const refresh = Promise.withResolvers();
  fixture.client.updateToken = () => refresh.promise;
  const pending = fixture.auth.getToken();
  fixture.client.onAuthLogout();
  refresh.resolve();
  await assert.rejects(pending);
  assert.equal(fixture.auth.session.status, 'anonymous');
});
test('HTTP 401 invalidates auth while permission failures do not', async () => {
  let invalidations = 0;
  const session = {...authenticated, invalidate(){invalidations++;}};
  for (const status of [403, 401]) {
    await assert.rejects(createApi(session, {fetch:async () =>
      new Response('{"detail":"denied"}', {status})}).list(), {status});
  }
  assert.equal(invalidations, 1);
});

test('HTTP contract: bearer token, routes, JSON bodies and abort signals', async () => {
  const calls = [];
  const controller = new AbortController();
  let refreshes = 0;
  const api = createApi({...authenticated, async getToken(){refreshes++; return 'fresh-token';}}, {fetch:async (url, options) => {
    calls.push({url, ...options});
    return new Response('{"taskId":"t/1"}', {status:202});
  }});
  await api.create('질문', controller.signal);
  await api.message('t/1', '추가 정보', controller.signal);
  await api.approval('t/1', {action:'revise', comment:'확인'}, controller.signal);
  await api.list(controller.signal);
  await api.detail('t/1', controller.signal);
  await api.events('t/1', 7, controller.signal);
  assert.equal(refreshes, 6);
  assert.ok(calls.every(call => call.headers.Authorization === 'Bearer fresh-token'));
  assert.deepEqual(Object.keys(calls[0].headers).sort(), ['Authorization', 'Content-Type']);
  assert.deepEqual(JSON.parse(calls[0].body), {question:'질문'});
  assert.deepEqual(JSON.parse(calls[1].body), {text:'추가 정보'});
  assert.equal(calls[2].url, '/api/ai/tasks/t%2F1/approval');
  assert.equal(calls[3].method, 'GET');
  assert.equal(calls[4].url, '/api/ai/tasks/t%2F1');
  assert.equal(calls[5].url, '/api/ai/tasks/t%2F1/events?after=7');
  assert.ok(calls.every(call => call.signal === controller.signal));
});

test('errors retain server denial and distinguish cancellation/network/bad JSON', async () => {
  await assert.rejects(createApi(authenticated, {fetch:async () =>
    new Response('{"detail":"engineer only"}', {status:403})}).list(),
  error => error instanceof ApiError && error.status === 403 && error.message === 'engineer only');
  await assert.rejects(createApi(authenticated, {fetch:async () => {throw new TypeError('offline');}}).list(), ApiError);
  await assert.rejects(createApi(authenticated, {fetch:async () => new Response('<html>')}).list(), ApiError);
  const abort = new DOMException('cancelled', 'AbortError');
  await assert.rejects(createApi(authenticated, {fetch:async () => {throw abort;}}).list(), error => error === abort);
});

function chunks(values) {
  return new ReadableStream({start(controller) {
    for (const value of values) controller.enqueue(value);
    controller.close();
  }});
}
function sse(value) {
  return new Response(value, {headers:{'Content-Type':'text/event-stream'}});
}
test('SSE parser handles UTF8 chunks CRLF multiline comments IDs and EOF', async () => {
  const bytes = new TextEncoder().encode(': heartbeat\r\nid: 5\r\nevent: QUESTION\r\ndata: {"text":"장비?",\r\ndata: "missing":["tool"]}\r\n\r\nid: 6\nid: ignored\0id\nevent: DONE\ndata: {"payload":{"report":{"demo":true}}}');
  const events = [];
  await readEventStream(chunks([...bytes].map(byte => new Uint8Array([byte]))), {onEvent:event => events.push(event)});
  assert.equal(events[0].seq, 5);
  assert.equal(events[0].type, 'QUESTION');
  assert.equal(events[0].payload.text, '장비?');
  assert.equal(events[1].seq, 6);
  assert.equal(events[1].payload.report.demo, true);
  assert.equal(streamUrl('a/b', 6), '/api/ai/tasks/a%2Fb/stream?after=6');
});
test('SSE expiry EOF refreshes bearer and reconnects with latest cursor', async () => {
  const calls = [], events = [];
  let tokens = 0;
  const done = Promise.withResolvers();
  const api = createApi({...authenticated, async getToken(){return ++tokens === 1 ? 'old' : 'new';}}, {
    fetch:async (url, options) => {
      calls.push({url, ...options});
      return sse(`id: ${calls.length === 1 ? 5 : 6}\nevent: RUNNING\ndata: {"text":"ok"}\n\n`);
    }
  });
  api.stream('a', 4, {onEvent:event => events.push(event), onError:done.resolve});
  assert.ok(await done.promise instanceof ApiError);
  assert.equal(calls.length, 2);
  assert.equal(calls[0].headers.Authorization, 'Bearer old');
  assert.equal(calls[1].headers.Authorization, 'Bearer new');
  assert.equal(calls[1].url, '/api/ai/tasks/a/stream?after=5');
  assert.deepEqual(events.map(event => event.seq), [5, 6]);
});
test('SSE errors require explicit retry instead of immediate reconnect loops', async () => {
  for (const response of [
    () => sse('data: {}\n\n'),
    () => sse('data: not-json\n\n'),
    () => sse(': heartbeat\n\n'),
    () => new Response('', {status:401}),
    () => {throw new TypeError('offline');}
  ]) {
    let calls = 0, invalidations = 0;
    const done = Promise.withResolvers();
    const api = createApi({...authenticated, invalidate(){invalidations++;}}, {
      fetch:async () => {calls++; return response();}
    });
    api.stream('a', 0, {onEvent:assert.fail, onError:done.resolve});
    const error = await done.promise;
    assert.ok(error instanceof ApiError);
    assert.equal(calls, 1);
    if (error.status === 401) assert.equal(invalidations, 1);
  }
});
test('SSE close and abort cancel pending reader without errors or late events', async () => {
  for (const explicit of [false, true]) {
    const reading = Promise.withResolvers(), cancelled = Promise.withResolvers();
    const controller = new AbortController();
    let received = 0, errors = 0;
    const body = new ReadableStream({
      pull(){reading.resolve();},
      cancel(){cancelled.resolve();}
    }, {highWaterMark:0});
    const api = createApi(authenticated, {fetch:async () => sse(body)});
    const close = api.stream('a', 0, {
      signal:controller.signal, onEvent(){received++;}, onError(){errors++;}
    });
    await reading.promise;
    if (explicit) close(); else controller.abort();
    await cancelled.promise;
    assert.equal(received, 0);
    assert.equal(errors, 0);
    close();
  }
});
test('aborted refresh never starts HTTP or streaming calls', async () => {
  let requests = 0;
  const controller = new AbortController();
  const refresh = Promise.withResolvers();
  const api = createApi({...authenticated, getToken:() => refresh.promise}, {
    fetch:async () => {requests++; return new Response('[]');}
  });
  const request = api.list(controller.signal);
  api.stream('a', 0, {signal:controller.signal, onEvent:assert.fail, onError:assert.fail});
  controller.abort();
  refresh.resolve('token');
  await assert.rejects(request, {name:'AbortError'});
  assert.equal(requests, 0);
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
    async list(){return [];}, async detail(id){return {id, status:'WAITING_INPUT', user_name:identity.name, user_role:identity.role, events:[]};},
    async create(question){calls.push(['create', question]); return {taskId:'task-1'};},
    async message(id, value){calls.push(['message', id, value]);},
    async approval(id, body){calls.push(['approval', id, body]);},
    stream(){return () => calls.push(['close']);}
  };
  const context = vm.createContext({
    createApi:() => api, createAuth:() => ({init(){}}), mountSops(){}, mergeEvents, AbortController, console, Intl, Date,
    document:{getElementById:element, querySelector:element, querySelectorAll(){return [];}, addEventListener(){}},
    window:{addEventListener(){}}, localStorage:{getItem(){return storedRecords;}},
    matchMedia:() => ({matches:true})
  });
  vm.runInContext(appSource.replace(/^import .*;\n/gm, '') +
    '\nglobalThis.hooks = {state, sessionChanged, updateControls, refreshRecords, legacyRecords, openEvidence, renderReport, renderConversation, canReview, submitQuestion, resetInvestigation, openReview, submitReview, syncTask, connectStream};', context);
  context.hooks.state.authenticated = true;
  context.hooks.state.name = identity.name;
  context.hooks.updateControls();
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
test('review permissions: all authenticated users waiting only, never legacy', () => {
  const {hooks} = harness();
  const task = {status:'WAITING_APPROVAL'};
  assert.equal(hooks.canReview(task), true);
  hooks.state.authenticated = false;
  assert.equal(hooks.canReview(task), false);
  hooks.state.authenticated = true;
  assert.equal(hooks.canReview({...task, legacy:true}), false);
  assert.equal(hooks.canReview({status:'DONE'}), false);
});
test('modal citations expose evidence for authenticated users', () => {
  const {hooks, element} = harness();
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
test('send creates once, continues shared waiting task, reset aborts old work', async () => {
  const {hooks, element, calls} = harness();
  element('questionInput').value = '새 질문';
  await hooks.submitQuestion({preventDefault(){}});
  assert.deepEqual(calls[0], ['create', '새 질문']);
  hooks.state.task.user_name = 'another-user';
  element('questionInput').value = '추가';
  await hooks.submitQuestion({preventDefault(){}});
  assert.deepEqual(calls.find(call => call[0] === 'message'), ['message', 'task-1', '추가']);
  const signal = hooks.state.controller.signal;
  hooks.resetInvestigation();
  assert.equal(signal.aborted, true);
  assert.equal(hooks.state.task, null);
  assert.equal(hooks.state.after, 0);
});
test('unauthenticated session clears workspace and aborts mutations list and stream', async () => {
  const {hooks, element, calls} = harness();
  hooks.state.task = {id:'a', status:'WAITING_APPROVAL', report:{}};
  hooks.state.records = [{id:'a'}];
  hooks.state.selected = hooks.state.task;
  hooks.state.listController = new AbortController();
  const listSignal = hooks.state.listController.signal;
  const taskSignal = hooks.state.controller.signal;
  hooks.state.closeStream = () => calls.push(['close']);
  hooks.openReview(hooks.state.task);
  hooks.sessionChanged({status:'anonymous', name:'', error:'expired'});
  assert.equal(taskSignal.aborted, true);
  assert.equal(listSignal.aborted, true);
  assert.equal(hooks.state.task, null);
  assert.equal(hooks.state.records.length, 0);
  assert.equal(hooks.state.selected, null);
  assert.equal(element('reportDialog').open, false);
  assert.equal(element('#conversation').inert, true);
  assert.equal(element('questionInput').disabled, true);
  element('questionInput').value = 'blocked';
  await hooks.submitQuestion({preventDefault(){}});
  await hooks.refreshRecords();
  assert.deepEqual(calls, [['close']]);
});
test('clarification remains blocked outside waiting input and for legacy records', async () => {
  const {hooks, calls, element} = harness();
  for (const task of [{status:'RUNNING'}, {status:'WAITING_APPROVAL'}, {status:'WAITING_INPUT', legacy:true}]) {
    hooks.state.task = {id:'a', ...task};
    hooks.updateControls();
    element('questionInput').value = 'no';
    await hooks.submitQuestion({preventDefault(){}});
    assert.equal(element('questionInput').disabled, true);
  }
  assert.equal(calls.length, 0);
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
