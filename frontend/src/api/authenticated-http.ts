import type { SessionAuth } from '@/auth'
import { ApiError, type Transport } from './client'

export function createAuthenticatedHttp(auth: SessionAuth, transport: Transport = {}) {
  const fetcher = transport.fetch || globalThis.fetch.bind(globalThis)
  async function response(url: string, init: RequestInit = {}) {
    const token = await auth.getToken()
    init.signal?.throwIfAborted()
    const headers = new Headers(init.headers)
    headers.set('Authorization', `Bearer ${token}`)
    if (init.body !== undefined) headers.set('Content-Type', 'application/json')
    let result: Response
    try {
      result = await fetcher(url, {...init, headers})
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') throw error
      throw new ApiError('서버에 연결할 수 없습니다. 다시 연결해 주세요.')
    }
    if (result.status === 401) auth.invalidate()
    if (!result.ok) throw new ApiError(`요청을 처리하지 못했습니다 (${result.status}).`, result.status)
    return result
  }
  return {
    response,
    async json(url: string, init?: RequestInit): Promise<unknown> {
      const result = await response(url, init)
      try { return await result.json() }
      catch (error) {
        if (error instanceof SyntaxError) throw new ApiError('서버 응답 JSON이 올바르지 않습니다.')
        throw error
      }
    },
  }
}
