<script setup lang="ts">
import TraceIcon from '@/components/TraceIcon.vue'
import { nextTick, ref, watch } from 'vue'
import ChatMessage from '@/components/ChatMessage.vue'
import ReportView from '@/components/ReportView.vue'
import { useInvestigationStore, type ChatItem } from '@/stores/investigation'

const investigation = useInvestigationStore()
const input = ref<HTMLTextAreaElement>()
const suggestions = [
  {label: 'Endpoint 지연 조사', prompt: 'ETCH-07 CH-B의 OX-120 공정에서 endpoint가 118초로 지연되고 RF reflected power가 29W로 상승했어. 과거 유사 사례와 먼저 점검할 항목을 알려줘.'},
  {label: 'Etch rate 저하', prompt: 'ETCH-09 CH-B의 OX-120 공정에서 etch rate가 430으로 저하되고 chamber pressure가 불안정해. 관련 사례를 찾아줘.'},
  {label: 'RF 반사전력 상승', prompt: 'ETCH-07에서 RF reflected power가 29W로 상승했어. 관련 기준 문서와 점검 순서를 알려줘.'},
  {label: '물리 계산 검증', prompt: 'ETCH-07 CH-B OX-120에서 식각 속도 500 nm/min, 식각 시간 120초, 식각 전 막 두께 1000nm, 식각 후 막 두께 400nm야. 계산값과 문서 근거를 함께 검토해줘.'},
]

// Quick replies attach to the prompt they answer, or to the last bubble if it has no event.
function pendingHere(item: ChatItem) {
  const pending = investigation.pending
  if (!pending || investigation.streaming) return false
  return pending.seq === undefined ? item === investigation.chat.at(-1) : item.seq === pending.seq
}
function suggest(prompt: string) {
  investigation.draft = prompt
  input.value?.focus()
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    investigation.submitQuestion()
  }
}
// Grow with the text however it changes (typing, suggestion buttons, clearing after send).
// scrollHeight excludes the 1px borders under border-box sizing, so add them back.
function resize() {
  const element = input.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight + 2, 140)}px`
}
watch(() => investigation.draft, () => nextTick(resize), {immediate:true})
</script>

<template>
  <section id="conversation" class="conversation" aria-live="polite">
    <template v-if="investigation.task">
      <ChatMessage v-for="item in investigation.chat" :key="item.key" :role="item.role">
        <template v-if="item.kind === 'report' && item.report">
          <p v-if="item.text" class="message-label">{{ item.text }}</p>
          <ReportView :report="item.report" />
        </template>
        <template v-else>
          <p v-if="item.kind === 'question'" class="message-label">추가 정보 필요</p>
          <p class="report-text">{{ item.text }}</p>
        </template>
        <div v-if="pendingHere(item)" class="quick-replies" role="group" aria-label="빠른 답변">
          <button v-for="option in investigation.pending!.options" :key="option" type="button"
            :class="investigation.pending!.decision && option === '승인' ? 'primary-button' : 'secondary-button'"
            @click="investigation.choose(option)">{{ option }}</button>
        </div>
      </ChatMessage>
      <ChatMessage v-if="investigation.streaming" role="assistant">
        <p class="report-text streaming-text" aria-live="polite">{{ investigation.streaming.text }}</p>
      </ChatMessage>
    </template>
    <div v-else class="message assistant-message intro-message">
      <div class="avatar" aria-hidden="true">AI</div>
      <div class="message-body">
        <p class="message-label">Investigation Assistant</p>
        <h2>어떤 이상을 조사할까요?</h2>
        <p>장비·챔버·레시피와 관찰된 현상을 알려주세요. 과거 사례와 관련 문서를 찾아 수치 근거와 함께 답변합니다.</p>
        <div class="example-block">
          <span>질문 예시</span>
          <p>ETCH-07 CH-B의 OX-120 공정에서 endpoint가 118초로 지연되고 RF reflected power가 29W로 상승했어. 무엇을 먼저 점검해야 해?</p>
        </div>
        <div class="suggestions" aria-label="추천 질문">
          <button v-for="item in suggestions" :key="item.label" type="button" @click="suggest(item.prompt)">{{ item.label }}</button>
        </div>
      </div>
    </div>
  </section>

  <form id="questionForm" class="composer" @submit.prevent="investigation.submitQuestion()">
    <label for="questionInput" class="sr-only">이상 조사 질문</label>
    <textarea id="questionInput" ref="input" v-model="investigation.draft" rows="1" required
      :placeholder="investigation.placeholder" :disabled="investigation.inputBlocked"
      @keydown="onKeydown"></textarea>
    <button class="send-button" type="submit" aria-label="질문 보내기" :disabled="investigation.inputBlocked"><TraceIcon name="send" /></button>
    <p>Enter로 전송 · Shift + Enter로 줄바꿈</p>
  </form>
</template>
