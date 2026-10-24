import { array, isObject, object } from './live-models'

export interface ThreadMessage {
  readonly id: string
  readonly role: 'user' | 'assistant'
  readonly text: string
}

export function threadMessages(values: unknown): ThreadMessage[] {
  const state = object(values)
  if (state.messages === undefined) return []
  return array(state.messages).flatMap<ThreadMessage>((value, index) => {
    const message = object(value)
    const role = message.type ?? message.role
    const extra = message.additional_kwargs
    const toolCalls = message.tool_calls ?? (
      isObject(extra) ? extra.tool_calls : undefined
    )
    const content = message.content
    if ((Array.isArray(toolCalls) && toolCalls.length) || (
      Array.isArray(content) && content.some(block => isObject(block) &&
        ['tool_use', 'tool_call'].includes(String(block.type)))
    )) return []
    const text = typeof content === 'string' ? content : Array.isArray(content)
      ? content.flatMap(block => isObject(block) && block.type === 'text' &&
        typeof block.text === 'string' ? [block.text] : []).join('\n') : ''
    if (!text.trim()) return []
    const id = typeof message.id === 'string' ? message.id : `message-${index}`
    switch (role) {
      case 'human': case 'user': return [{id, role:'user', text}]
      case 'ai': case 'assistant': return [{id, role:'assistant', text}]
      // Tool/system/developer messages are not part of the visible conversation.
      default: return []
    }
  })
}
