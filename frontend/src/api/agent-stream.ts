import { ApiError } from './client'
import { threadMessages, type ThreadMessage } from './thread-messages'

export interface ThreadStream {
  readonly signal: AbortSignal
  readonly onMessages: (messages: ThreadMessage[]) => void
  readonly onAccepted?: () => void
}

export async function readAgentStream(body: ReadableStream<Uint8Array>, stream: ThreadStream) {
  const reader = body.getReader(), decoder = new TextDecoder()
  let line = '', event = '', skipLF = false, ended = false
  let data: string[] = []
  function consumeLine() {
    if (!line) {
      if (event === 'end') ended = true
      if (event === 'error') throw new ApiError('에이전트 실행에 실패했습니다. 대화를 다시 연결해 주세요.')
      if (event === 'values' && data.length) {
        let value: unknown
        try { value = JSON.parse(data.join('\n')) }
        catch (error) {
          if (error instanceof SyntaxError) throw new ApiError('에이전트 이벤트 형식이 올바르지 않습니다.')
          throw error
        }
        stream.onMessages(threadMessages(value))
      }
      event = ''
      data = []
    } else if (!line.startsWith(':')) {
      const colon = line.indexOf(':')
      const field = colon < 0 ? line : line.slice(0, colon)
      const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '')
      if (field === 'event') event = value
      if (field === 'data') data.push(value)
    }
    line = ''
  }
  function consume(chunk: string) {
    for (const char of chunk) {
      if (stream.signal.aborted || ended) return
      if (skipLF) {
        skipLF = false
        if (char === '\n') continue
      }
      if (char === '\r' || char === '\n') {
        consumeLine()
        skipLF = char === '\r'
      } else line += char
    }
  }
  const abort = () => { void reader.cancel() }
  stream.signal.addEventListener('abort', abort, {once:true})
  try {
    while (!stream.signal.aborted && !ended) {
      const chunk = await reader.read()
      if (stream.signal.aborted) return
      if (chunk.done) { consume(decoder.decode()); return }
      consume(decoder.decode(chunk.value, {stream:true}))
    }
  } finally {
    stream.signal.removeEventListener('abort', abort)
    try { await reader.cancel() } finally { reader.releaseLock() }
  }
}
