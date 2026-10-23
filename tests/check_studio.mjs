/** Verify the running Studio protocol without exporting credentials. */
import assert from 'node:assert/strict'
import {mkdir, writeFile} from 'node:fs/promises'

const base = process.env.TRACE_AGENT_URL || 'http://localhost:12024'
const transcript = []
const headers = {
  'X-Internal-Key': process.env.INTERNAL_API_KEY || 'trace-local-development',
  'Content-Type': 'application/json',
}
const searched = await fetch(`${base}/assistants/search`, {
  method: 'POST', headers, body: JSON.stringify({graph_id: 'trace'}),
  signal: AbortSignal.timeout(30_000),
})
assert.equal(searched.status, 200)
const assistants = await searched.json()
assert.ok(assistants.length > 0, 'Default trace assistant is registered')
const assistant = assistants[0].assistant_id
for (const path of ['/ok', `/assistants/${assistant}/graph`, `/assistants/${assistant}/schemas`]) {
  const response = await fetch(base + path, {
    headers,
    signal: AbortSignal.timeout(30_000),
  })
  const body = await response.json()
  transcript.push({
    path, status: response.status,
    headers: Object.fromEntries([...response.headers].filter(([key]) => key !== 'set-cookie')),
    body,
  })
  assert.equal(response.status, 200, JSON.stringify(body))
}
const graph = transcript[1].body
assert.ok(graph.nodes.some(node => node.id === 'publish'), 'Studio graph includes business publication')
const schemas = transcript[2].body
assert.ok(schemas.input_schema.properties.request, 'Studio exposes the request input')
await mkdir('.omo/evidence/agent-server', {recursive: true})
await writeFile('.omo/evidence/agent-server/studio-api.json', JSON.stringify({
  base, result: 'PASS', transcript,
}, null, 2))
console.log('PASS: Studio Agent Server graph and input schema endpoints are ready')
