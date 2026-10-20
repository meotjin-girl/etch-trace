<script setup lang="ts">
import { ref } from 'vue'
import ChatMessage from '@/components/ChatMessage.vue'
import ReportView from '@/components/ReportView.vue'
import { text } from '@/lib/format'
import { useInvestigationStore } from '@/stores/investigation'

const investigation = useInvestigationStore()
const input = ref<HTMLTextAreaElement>()
const suggestions = [
  {label: 'Endpoint 지연 조사', prompt: 'ETCH-07 CH-B의 OX-120 공정에서 endpoint가 118초로 지연되고 RF reflected power가 29W로 상승했어. 과거 유사 사례와 먼저 점검할 항목을 알려줘.'},
  {label: 'Etch rate 저하', prompt: 'ETCH-09 CH-B의 OX-120 공정에서 etch rate가 430으로 저하되고 chamber pressure가 불안정해. 관련 사례를 찾아줘.'},
  {label: 'RF 반사전력 상승', prompt: 'ETCH-07에서 RF reflected power가 29W로 상승했어. 관련 기준 문서와 점검 순서를 알려줘.'},
]

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
function resize() {
  const element = input.value!
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 140)}px`
}
</script>

<template>
  <section id="conversation" class="conversation" aria-live="polite">
    <template v-if="investigation.task">
      <template v-if="investigation.task.messages?.length">
        <ChatMessage v-for="(item, index) in investigation.task.messages" :key="index" :role="item.role === 'user' ? 'user' : 'assistant'">
          <p class="report-text">{{ text(item.text ?? item.content) }}</p>
        </ChatMessage>
      </template>
      <ChatMessage v-else role="user"><p>{{ investigation.task.question }}</p></ChatMessage>
      <ChatMessage v-for="event in investigation.followUps" :key="event.seq" role="assistant">
        <p class="message-label">추가 정보 필요</p>
        <p>{{ text(event.payload.text) }}</p>
        <p>{{ text(event.payload.missing) }}</p>
      </ChatMessage>
      <ChatMessage v-if="investigation.task.report" role="assistant">
        <ReportView :report="investigation.task.report" @review="investigation.openReview(investigation.task)" />
      </ChatMessage>
      <ChatMessage v-if="investigation.failure !== null" role="assistant"><p>{{ investigation.failure }}</p></ChatMessage>
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
      @keydown="onKeydown" @input="resize"></textarea>
    <button class="send-button" type="submit" aria-label="질문 보내기" :disabled="investigation.inputBlocked"><i class="fi-rr-paper-plane" aria-hidden="true"></i></button>
    <p>Enter로 전송 · Shift + Enter로 줄바꿈</p>
  </form>
</template>
