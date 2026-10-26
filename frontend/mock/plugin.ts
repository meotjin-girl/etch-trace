// Vite dev-server plugin serving the mock API on /api (enabled by MOCK_API=1).
import type { IncomingMessage, ServerResponse } from 'node:http'
import type { Plugin } from 'vite'
import { MockError, createMockStore, type MockIdentity, type MockStore, type Pushed } from './store'
import { LiveError, createLiveMock } from './live'

function identityOf(req: IncomingMessage): MockIdentity {
  if (req.headers.authorization !== 'Bearer trace-mock-user') throw new MockError(401, '목업 신원 정보가 필요합니다.')
  return {name: '목업 사용자', role: 'user'}
}

async function body(req: IncomingMessage) {
  let raw = ''
  for await (const chunk of req) raw += chunk
  try { return raw ? JSON.parse(raw) : {} } catch { throw new MockError(422, 'JSON 본문이 올바르지 않습니다.') }
}

function cursor(value: string | null | undefined) {
  if (value == null || value === '') return 0
  const parsed = Number(value)
  if (!Number.isSafeInteger(parsed) || parsed < 0) throw new MockError(422, 'after는 0 이상의 정수입니다.')
  return parsed
}

function send(res: ServerResponse, status: number, data: unknown) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.end(JSON.stringify(data))
}

function stream(req: IncomingMessage, res: ServerResponse, store: MockStore, identity: MockIdentity, id: string, after: number) {
  const last = cursor(req.headers['last-event-id'] as string | undefined)
  const replay = store.events(identity, id, Math.max(after, last))
  res.writeHead(200, {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive'})
  const write = (event: Pushed) => {
    // Same shape as backend/main.py: saved events send `{...payload, at}` with the seq in `id:`.
    const data = 'seq' in event ? {...event.payload, at:event.created_at} : event.payload
    res.write(`${'seq' in event ? `id: ${event.seq}\n` : ''}event: ${event.type}\ndata: ${JSON.stringify(data)}\n\n`)
  }
  replay.forEach(write)
  if (store.isTerminal(identity, id)) return res.end()
  const keepAlive = setInterval(() => res.write(': keep-alive\n\n'), 15_000)
  const close = () => { clearInterval(keepAlive); unsubscribe(); res.end() }
  const unsubscribe = store.subscribe(identity, id, event => {
    write(event)
    if (['DONE', 'INCOMPLETE', 'FAILED'].includes(event.type)) close()
  })
  req.on('close', close)
}

export function mockApi(): Plugin {
  return {
    name: 'trace-mock-api',
    configureServer(server) {
      const store = createMockStore()
      const live = createLiveMock()
      server.config.logger.info('  ➜  Mock API: /api, /agent (in-memory, resets on restart)')
      server.middlewares.use('/agent', async (req, res) => {
        try {
          identityOf(req)
          const url = new URL(req.url || '/', 'http://mock')
          const [, threadId = '', resource, sub] = url.pathname.split('/').filter(Boolean).map(decodeURIComponent)
          if (resource === 'state') return send(res, 200, live.state(threadId))
          if (resource === 'runs' && !sub && req.method === 'GET') return send(res, 200, [])
          if (resource === 'runs' && sub === 'stream' && req.method === 'POST') {
            const input = (await body(req)) as {input?: {request?: {content?: string}}}
            const reply = live.ask(threadId, String(input.input?.request?.content ?? ''))
            res.writeHead(200, {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache'})
            return res.end(reply)
          }
          throw new MockError(404, 'Not Found')
        } catch (error) {
          const status = error instanceof MockError || error instanceof LiveError ? error.status : 500
          send(res, status, {detail: (error as Error).message})
        }
      })
      server.middlewares.use('/api', async (req, res) => {
        try {
          const url = new URL(req.url || '/', 'http://mock')
          const parts = url.pathname.split('/').filter(Boolean).map(decodeURIComponent)
          const method = req.method || 'GET'
          if (parts[0] === 'sops' && method === 'GET') {
            identityOf(req)
            return send(res, 200, parts[1] ? store.sop(parts[1]) : store.sops())
          }
          if (parts[0] === 'investigations') {
            identityOf(req)
            const [, id, action] = parts
            if (!id && method === 'GET') return send(res, 200, live.list())
            if (id && !action && method === 'GET') return send(res, 200, live.detail(id))
            if (id && action === 'approval' && method === 'POST') return send(res, 200, live.approve(id, await body(req)))
            if (id && action === 'approval' && method === 'DELETE') { live.cancelApproval(id); res.statusCode = 204; return res.end() }
            if (id && action === 'action' && method === 'POST') return send(res, 200, live.recordAction(id, await body(req)))
            throw new MockError(404, 'Not Found')
          }
          if (parts[0] !== 'ai' || parts[1] !== 'tasks') throw new MockError(404, 'Not Found')
          const [, , id, action] = parts
          const identity = identityOf(req)
          if (!id && method === 'GET') return send(res, 200, store.list(identity))
          if (!id && method === 'POST') return send(res, 202, store.create(identity, await body(req)))
          if (id && !action && method === 'GET') return send(res, 200, store.detail(identity, id))
          if (action === 'messages' && method === 'POST') return send(res, 202, store.message(identity, id!, await body(req)))
          if (action === 'approval' && method === 'POST') return send(res, 202, store.approval(identity, id!, await body(req)))
          if (action === 'events' && method === 'GET') return send(res, 200, store.events(identity, id!, cursor(url.searchParams.get('after'))))
          if (action === 'stream' && method === 'GET') return stream(req, res, store, identity, id!, cursor(url.searchParams.get('after')))
          throw new MockError(404, 'Not Found')
        } catch (error) {
          if (res.headersSent) return res.end()
          send(res, error instanceof MockError || error instanceof LiveError ? error.status : 500, {detail: (error as Error).message})
        }
      })
    },
  }
}
