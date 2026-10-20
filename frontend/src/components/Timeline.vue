<script setup>
defineProps({ events: Array })
const TOOL_KO = {
  get_run_context: '대상 run 조회', find_reference_runs: '비교 run 탐색',
  compare_signals: '신호 통계 비교', search_knowledge: '문서 근거 검색',
}
function line(e) {
  switch (e.type) {
    case 'QUEUED': return ['tone-neutral', '접수', `${e.by} 님의 조사 요청`]
    case 'PLAN': return ['tone-agent', `계획 #${e.turn}`, e.next ? `${TOOL_KO[e.next] || e.next} 선택 — ${e.reason}` : e.reason]
    case 'TOOL_START': return ['tone-info', '도구 실행', `${TOOL_KO[e.name] || e.name} (${e.name})`]
    case 'TOOL_END': return [e.ok ? 'tone-ok' : 'tone-bad', e.ok ? '도구 완료' : '도구 오류', `${e.name} · ${e.ms}ms${e.ok ? '' : ' · ' + (e.result?.error || '')}`]
    case 'TOKEN': return ['tone-agent', '보고서 초안', e.text]
    case 'APPROVAL_REQUIRED': return ['tone-warn', '검토 요청', e.revision ? `수정본 #${e.revision} 검토 대기` : '엔지니어 검토 대기 (상태 저장 후 정지)']
    case 'REVIEWED': return ['tone-neutral', e.action === 'approve' ? '승인' : '수정 요청', `${e.by}${e.comment ? ' — ' + e.comment : ''}`]
    case 'DONE': return ['tone-ok', '완료', e.saved?.saved ? `조사 기록 ${e.saved.investigation_id} 저장` : e.saved?.reason || '종료']
    case 'FAILED': return ['tone-bad', '실패', e.error]
  }
  return ['tone-neutral', e.type, '']
}
</script>
<template>
  <ol class="tl" aria-live="polite">
    <li v-for="e in events" :key="e.seq">
      <span class="badge" :class="line(e)[0]">{{ line(e)[1] }}</span>
      <span class="txt">{{ line(e)[2] }}</span>
      <time class="muted mono">{{ new Date(e.at).toLocaleTimeString('ko-KR') }}</time>
    </li>
    <li v-if="!events.length" class="muted">이벤트를 기다리는 중…</li>
  </ol>
</template>
<style scoped>
.tl { list-style: none; margin: 0; padding: 0 0 0 14px; border-left: 2px solid var(--line); max-height: 420px; overflow-y: auto; }
.tl li { display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: start; padding: 6px 0; position: relative; }
.tl li::before { content: ''; position: absolute; left: -19px; top: 12px; width: 8px; height: 8px; border-radius: 50%; background: var(--line); }
.txt { font-size: 13px; word-break: break-word; } time { font-size: 11px; }
</style>
