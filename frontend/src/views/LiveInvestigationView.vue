<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import ChatMessage from '@/components/ChatMessage.vue'
import LiveInvestigationDetail from '@/components/LiveInvestigationDetail.vue'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'

const live = useLiveInvestigationsStore()
const route = useRoute()
const id = computed(() => typeof route.params.id === 'string' ? route.params.id : '')
watch(id, value => { if (value) void live.open(value) }, {immediate:true})
onUnmounted(live.close)
function keydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void live.send()
  }
}
</script>

<template>
  <section class="records-page" data-testid="investigation-detail">
    <div class="records-heading">
      <RouterLink to="/" class="secondary-button">조사 목록</RouterLink>
      <button class="secondary-button" type="button" :disabled="live.loading || live.busy || live.approving"
        @click="live.open(id)">새로고침</button>
    </div>
    <div v-if="live.error" class="network-notice" role="alert">
      {{ live.error }}
      <button type="button" class="secondary-button" :disabled="live.loading || live.busy || live.approving"
        @click="live.open(id)">다시 연결</button>
    </div>
    <p v-if="live.loading" role="status">조사와 대화를 불러오는 중…</p>
    <article v-if="live.detail" class="record-detail live-detail">
      <LiveInvestigationDetail :investigation="live.detail" :blocked="live.loading || live.busy || live.approving"
        @approve="live.approve" />
      <section class="live-conversation" aria-labelledby="threadHeading" aria-live="polite" data-testid="thread-conversation">
        <h3 id="threadHeading">조사 대화</h3>
        <ChatMessage v-for="item in live.messages" :key="item.id" :role="item.role">
          <p class="report-text" data-testid="thread-message">{{ item.text }}</p>
        </ChatMessage>
        <p v-if="!live.messages.length && !live.loading">아직 표시할 대화가 없습니다.</p>
        <p v-if="live.busy" role="status">에이전트 실행 중 · 이 대화에 연결되어 있습니다.</p>
      </section>
    </article>
  </section>
  <form v-if="live.detail" class="composer" data-testid="thread-composer" @submit.prevent="live.send()">
    <label class="sr-only" for="threadQuestion">조사 후속 질문</label>
    <textarea id="threadQuestion" v-model="live.draft" rows="2" required :disabled="!live.canSend"
      placeholder="추가 근거나 조치를 질문하세요. 승인 후에도 대화를 이어갈 수 있습니다." @keydown="keydown"></textarea>
    <button type="submit" class="send-button" aria-label="후속 질문 보내기" :disabled="!live.canSend || !live.draft.trim()">
      <i class="fi-rr-paper-plane" aria-hidden="true"></i>
    </button>
    <p>Enter로 전송 · Shift + Enter로 줄바꿈</p>
  </form>
</template>

<style scoped>
.live-detail { max-width: 980px; margin: 0 auto; }
.live-conversation { margin-top: 24px; min-width: 0; }
.live-conversation h3 { font-size: 15px; }
.live-conversation .message { margin-top: 24px; }
.records-heading { flex-wrap: wrap; }
</style>
