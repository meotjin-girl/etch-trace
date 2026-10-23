import type { SessionAuth } from '@/auth'
import { ApiError, type Transport } from './client'
import { createAuthenticatedHttp } from './authenticated-http'
import { array, object, string } from './live-models'
import { readAgentStream, type ThreadStream } from './agent-stream'
import { threadMessages } from './thread-messages'

export interface AgentRun {
  readonly run_id: string
  readonly status: string
}
export const activeRun = (runs: readonly AgentRun[]) =>
  runs.find(run => run.status === 'pending' || run.status === 'running')

export function createAgentApi(auth: SessionAuth, transport: Transport = {}) {
  const http = createAuthenticatedHttp(auth, transport)
  const path = (id: string) => `/agent/threads/${encodeURIComponent(id)}`
  async function consume(response: Response, stream: ThreadStream) {
    if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
      throw new ApiError('에이전트 스트림 응답이 올바르지 않습니다.')
    }
    stream.signal.throwIfAborted()
    stream.onAccepted?.()
    await readAgentStream(response.body, stream)
  }
  return {
    async state(id: string, signal: AbortSignal) {
      const state = object(await http.json(`${path(id)}/state`, {signal}))
      return threadMessages(state.values)
    },
    async runs(id: string, signal: AbortSignal): Promise<AgentRun[]> {
      return array(await http.json(`${path(id)}/runs?limit=100`, {signal})).map(value => {
        const run = object(value)
        return {run_id:string(run.run_id), status:string(run.status)}
      })
    },
    async send(id: string, content: string, stream: ThreadStream) {
      const response = await http.response(`${path(id)}/runs/stream`, {
        method:'POST', signal:stream.signal, headers:{Accept:'text/event-stream'},
        body:JSON.stringify({
          assistant_id:'trace', input:{request:{role:'user', content}},
          stream_mode:['values'], multitask_strategy:'reject', on_disconnect:'continue',
        }),
      })
      await consume(response, stream)
    },
    async join(id: string, runId: string, stream: ThreadStream) {
      const response = await http.response(
        `${path(id)}/runs/${encodeURIComponent(runId)}/stream?stream_mode=values&cancel_on_disconnect=false`,
        {signal:stream.signal, headers:{Accept:'text/event-stream'}, cache:'no-store'},
      )
      await consume(response, stream)
    },
  }
}
