<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ReportView from '@/components/ReportView.vue'
import { useIdentityStore } from '@/stores/identity'
import { useInvestigationStore } from '@/stores/investigation'

const investigation = useInvestigationStore()
const identity = useIdentityStore()
const review = investigation.review
const dialog = ref<HTMLDialogElement>()
const comment = ref<HTMLTextAreaElement>()
const locked = computed(() => review.busy || !investigation.canReview(review.task))

watch(() => review.task, task => {
  if (task && !dialog.value?.open) dialog.value?.showModal()
  if (!task && dialog.value?.open) dialog.value.close()
})

async function submit(event: SubmitEvent) {
  const action = (event.submitter as HTMLButtonElement | null)?.value || ''
  if (!await investigation.submitReview(action)) comment.value?.focus()
}
</script>

<template>
  <!-- Escape closes the native dialog; keep the store in sync. -->
  <dialog id="reportDialog" ref="dialog" @close="investigation.closeReview()">
    <form class="report-dialog" @submit.prevent="submit">
      <div class="dialog-header">
        <div><p class="eyebrow">INVESTIGATION RECORD</p><h2>승인용 조사 기록</h2></div>
        <button class="close-dialog" type="button" aria-label="닫기" @click="investigation.closeReview()"><i class="fi-rr-cross-small" aria-hidden="true"></i></button>
      </div>
      <div class="record-meta">
        <label>발생 시각<input v-model="review.time" type="datetime-local"></label>
        <label>Lot ID<input v-model="review.lot" type="text" placeholder="예: L261019-03"></label>
        <label>검토자<input :value="identity.name" type="text" readonly></label>
      </div>
      <div class="report-preview">
        <ReportView v-if="review.task?.report" :report="review.task.report" review />
      </div>
      <label class="review-comment" for="reviewComment">검토 의견 / 수정 요청</label>
      <textarea id="reviewComment" ref="comment" v-model="review.comment" rows="3" placeholder="수정 요청 시 의견을 입력해 주세요"></textarea>
      <p role="status">{{ review.notice }}</p>
      <div class="dialog-actions">
        <button class="secondary-button" type="button" @click="investigation.closeReview()">취소</button>
        <button class="secondary-button" type="submit" value="revise" :disabled="locked">수정 요청</button>
        <button class="primary-button" type="submit" value="approve" :disabled="locked">검토 및 승인</button>
      </div>
    </form>
  </dialog>
</template>
