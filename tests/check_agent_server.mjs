/**
 * Real Keycloak PKCE -> nginx -> Agent Server -> MCP -> backend investigation QA.
 * Run: uv run --project backend --env-file .env node tests/check_agent_server.mjs
 * TRACE_URL defaults to the isolated QA deployment; tokens are never written.
 */
import assert from 'node:assert/strict'
import {createHash, randomBytes} from 'node:crypto'
import {mkdir, writeFile} from 'node:fs/promises'

const base = process.env.TRACE_URL || 'http://localhost:18081'
const evidence = process.env.TRACE_EVIDENCE || '.omo/evidence/agent-server'
const threadId = process.env.TRACE_THREAD_ID || '00000000-0000-4000-8000-000000002301'
const jar = new Map()
const transcript = []
const deadline = () => AbortSignal.timeout(600_000)

async function authRequest(url, options = {}) {
  const response = await fetch(url, {
    ...options, redirect: 'manual', signal: deadline(),
    headers: {...options.headers, Cookie: [...jar].map(([k, v]) => `${k}=${v}`).join('; ')},
  })
  for (const cookie of response.headers.getSetCookie()) {
    const first = cookie.split(';', 1)[0]
    const index = first.indexOf('=')
    jar.set(first.slice(0, index), first.slice(index + 1))
  }
  return response
}

async function pkceLogin() {
  const verifier = randomBytes(32).toString('base64url')
  const challenge = createHash('sha256').update(verifier).digest('base64url')
  const redirectUri = `${base}/`
  const issuer = `${base}/auth/realms/trace/protocol/openid-connect`
  const url = new URL(`${issuer}/auth`)
  url.search = new URLSearchParams({
    client_id: 'trace-web', redirect_uri: redirectUri, response_type: 'code',
    scope: 'openid', state: randomBytes(16).toString('hex'),
    code_challenge: challenge, code_challenge_method: 'S256',
  })
  let response = await authRequest(url)
  while ([301, 302, 303, 307].includes(response.status)) {
    response = await authRequest(new URL(response.headers.get('location'), base))
  }
  const html = await response.text()
  const action = html.match(/<form[^>]*action="([^"]+)"/)?.[1]?.replaceAll('&amp;', '&')
  assert.ok(action, 'Keycloak login form is present')
  response = await authRequest(action, {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({
      username: process.env.TRACE_QA_USER || 'test',
      password: process.env.TRACE_QA_PASSWORD || 'test', credentialId: '',
    }),
  })
  let location = response.headers.get('location')
  while (location && !new URL(location, base).searchParams.has('code')) {
    response = await authRequest(new URL(location, base))
    location = response.headers.get('location')
  }
  assert.ok(location, 'PKCE returns authorization code')
  const code = new URL(location, base).searchParams.get('code')
  assert.ok(code)
  const exchanged = await fetch(`${issuer}/token`, {
    method: 'POST', signal: deadline(),
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({
      grant_type: 'authorization_code', client_id: 'trace-web', redirect_uri: redirectUri,
      code, code_verifier: verifier,
    }),
  })
  assert.equal(exchanged.status, 200)
  const {access_token} = await exchanged.json()
  const claims = JSON.parse(Buffer.from(access_token.split('.')[1], 'base64url'))
  return {token: access_token, subject: claims.sub}
}

async function call(path, {method = 'GET', body, token, internalKey} = {}) {
  const response = await fetch(base + path, {
    method, signal: deadline(),
    headers: {
      ...(body ? {'Content-Type': 'application/json'} : {}),
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
      ...(internalKey ? {'X-Internal-Key': internalKey} : {}),
    },
    ...(body ? {body: JSON.stringify(body)} : {}),
  })
  const text = await response.text()
  let data
  try { data = JSON.parse(text) } catch { data = text }
  transcript.push({
    request: {method, path, body, authenticated: Boolean(token), internal_key_supplied: Boolean(internalKey)},
    status: response.status,
    headers: Object.fromEntries([...response.headers].filter(([key]) => key !== 'set-cookie')),
    body: data,
  })
  return {status: response.status, data}
}

async function main() {
  await mkdir(evidence, {recursive: true})
  const {token, subject} = await pkceLogin()
  const auth = {token}
  const path = `/api/investigations/${threadId}`
  if (process.env.TRACE_RESET_FAILED_THREAD === '1') {
    assert.equal((await call(path, auth)).status, 404, 'Only reset a failed unpublished QA thread')
    const removed = await fetch(
      `${process.env.TRACE_AGENT_URL || 'http://localhost:12024'}/threads/${threadId}`,
      {
        method: 'DELETE', signal: deadline(),
        headers: {'X-Internal-Key': process.env.INTERNAL_API_KEY || 'trace-local-development'},
      },
    )
    assert.ok([200, 204, 404].includes(removed.status), `QA thread reset: ${removed.status}`)
  }
  for (const target of ['/api/investigations', `/agent/threads/${threadId}/state`]) {
    for (const denied of [{}, {token: 'invalid-token'}]) {
      const response = await call(target, denied)
      assert.ok([401, 403].includes(response.status), `${target}: authentication enforced`)
    }
  }
  const created = await call('/agent/threads', {
    ...auth, method: 'POST', body: {thread_id: threadId},
  })
  assert.equal(created.status, 200, JSON.stringify(created.data))
  assert.equal((await call(path, auth)).status, 404, 'No business record before analysis')
  const alert = '[경보] ETCH-02 / CH-A / Lot QA-LOT / Wafer W01 / RCP-OX-ETCH-EDU-01\n'
    + '- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.4 W (한계 37 W) (OCAP-ETCH-RF)'
  const run = async (role, content) => {
    const response = await call(`/agent/threads/${threadId}/runs/wait`, {
      ...auth, method: 'POST',
      body: {assistant_id: 'trace', input: {request: {role, content}}, multitask_strategy: 'reject'},
    })
    assert.equal(response.status, 200, JSON.stringify(response.data))
    assert.ok(!response.data?.__error__, JSON.stringify(response.data))
    return response.data
  }
  await run('system', alert)
  const initial = await call(path, auth)
  assert.equal(initial.status, 200, JSON.stringify(initial.data))
  assert.ok(initial.data.candidates.length > 0)
  assert.equal(initial.data.thread_id, threadId)
  assert.equal(initial.data.approval, null)
  if (process.env.TRACE_SEED_ONLY === '1') {
    await writeFile(`${evidence}/ui-seed.json`, JSON.stringify({
      base, thread_id: threadId, result: 'PASS', transcript,
    }, null, 2))
    console.log(`PASS: real unapproved AI investigation ready for UI; thread=${threadId}`)
    return
  }
  await run('user', '이것 외에 다른 원인도 조사해 주고 확인할 곳을 보완해 주세요')
  const revised = (await call(path, auth)).data
  assert.equal(revised.id, initial.data.id)
  assert.ok(revised.revision > initial.data.revision, 'Follow-up updates the same business record')
  const approval = {
    candidate_id: revised.candidates[0].id,
    expected_revision: revised.revision, comment: '실제 UI/API 검증',
  }
  const spoof = await call(`${path}/approval`, {
    ...auth, method: 'POST', body: {...approval, approved_by_id: 'forged-reviewer'},
  })
  assert.equal(spoof.status, 422, 'Reviewer identity cannot come from browser payload')
  const approved = await call(`${path}/approval`, {...auth, method: 'POST', body: approval})
  assert.equal(approved.status, 200, JSON.stringify(approved.data))
  assert.equal(approved.data.approved_by_id, subject)
  await run('user', '승인한 원인에서 먼저 확인할 곳을 설명해 주세요')
  const after = (await call(path, auth)).data
  assert.deepEqual(after.approval, approved.data, 'Approval snapshot survives ongoing conversation')
  const list = (await call('/api/investigations', auth)).data
  assert.equal(list.filter(record => record.thread_id === threadId).length, 1)
  const state = await call(`/agent/threads/${threadId}/state`, auth)
  assert.equal(state.status, 200)
  assert.ok(state.data.values.messages.length >= 6, 'Conversation persisted across turns')
  const mutation = await call(`/agent/threads/${threadId}/state`, {...auth, method: 'POST', body: {values: {}}})
  assert.equal(mutation.status, 405)
  const internalBypass = await call('/agent/threads', {
    method: 'POST', body: {}, internalKey: process.env.INTERNAL_API_KEY,
  })
  assert.ok([401, 403].includes(internalBypass.status), 'nginx strips internal service key')
  await writeFile(`${evidence}/http-qa.json`, JSON.stringify({base, thread_id: threadId, result: 'PASS', transcript}, null, 2))
  console.log(`PASS: auth, initial save, same-record updates, reviewer identity, approval, ongoing chat; thread=${threadId}`)
}

try {
  await main()
} catch (error) {
  await mkdir(evidence, {recursive: true})
  await writeFile(`${evidence}/http-qa-failure.json`, JSON.stringify({base, error: String(error), transcript}, null, 2))
  console.error(error)
  process.exitCode = 1
}
