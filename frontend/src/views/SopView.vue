<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Sop, SopSummary } from '@/api/types'
import { renderMarkdown } from '@/lib/markdown'
import { useIdentityStore } from '@/stores/identity'
import PageHeader from '@/components/PageHeader.vue'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()
const identity = useIdentityStore()
const summaries = ref<SopSummary[]>([])
const listError = ref('')
const document = ref<Sop | null>(null)
const detailError = ref('')
const loading = ref(false)
const detail = ref<HTMLElement>()
const selected = computed(() => route.params.id as string | undefined)
let request = 0

// Opened from an investigation: its candidate documents come first as "관련 문서".
const related = computed(() => typeof route.query.related === 'string'
  ? route.query.related.split(',').map(id => id.split('#')[0]!).filter(Boolean) : [])
const filtered = computed(() => {
  const term = ui.search.trim().toLocaleLowerCase()
  return summaries.value.filter(item =>
    [item.id, item.title, item.category, item.description, ...(item.tags || [])]
      .join(' ').toLocaleLowerCase().includes(term))
    .sort((a, b) => Number(related.value.includes(b.id)) - Number(related.value.includes(a.id)))
})

async function load(id: string) {
  const current = ++request
  loading.value = true
  detailError.value = ''
  try {
    const item = await identity.api.sop(id)
    if (current !== request) return
    document.value = item
    loading.value = false
    await nextTick()
    if (matchMedia('(max-width: 720px)').matches) detail.value?.scrollIntoView({block:'start'})
  } catch (error) {
    if (current !== request) return
    document.value = null
    loading.value = false
    detailError.value = (error as Error).message
  }
}

onMounted(async () => {
  try {
    summaries.value = await identity.api.sops()
  } catch (error) {
    listError.value = (error as Error).message
    return
  }
  if (selected.value) load(selected.value)
  else if (summaries.value.length) router.replace(`/sop/${encodeURIComponent(summaries.value[0]!.id)}`)
})
watch(selected, id => { if (id) load(id) })
</script>

<template>
  <PageHeader title="SOP · OCAP 원문" subtitle="독립 문서 열람 메뉴 · 알람 처리 단계와 별개 · 문서는 시연용 샘플" ruled />
  <section id="sopPage" class="sop-grid" aria-label="SOP 목록">
    <div class="t-card">
      <h2>{{ related.length ? '관련 문서' : '문서 목록' }}</h2>
      <p class="t-sub" role="status">{{ listError ? '문서를 불러오지 못했습니다.' : summaries.length ? `${filtered.length}개 문서` : '문서를 불러오는 중…' }}</p>
      <p v-if="listError" class="t-empty" role="alert">{{ listError }}</p>
      <RouterLink v-for="item in filtered" :key="item.id" class="t-inner sop-item"
        :class="{active: item.id === selected, related: related.includes(item.id)}"
        :to="{path:`/sop/${encodeURIComponent(item.id)}`, query:$route.query}" :aria-current="item.id === selected ? 'page' : undefined">
        <strong :class="{['t-accent']: item.id === selected}">{{ item.id }}</strong>
        <span class="t-faint">{{ item.title }} · v{{ item.version }}</span>
      </RouterLink>
      <p v-if="summaries.length && !filtered.length" class="t-empty">검색 결과가 없습니다.</p>
    </div>
    <article ref="detail" class="t-card sop-doc" aria-label="SOP 문서 상세">
      <p v-if="loading" class="t-empty" role="status">문서를 불러오는 중…</p>
      <p v-else-if="detailError" class="t-empty" role="alert">{{ detailError }}</p>
      <template v-else-if="document">
        <h2 tabindex="-1">{{ document.id }}</h2>
        <p class="t-sub">{{ document.title }} · 버전 {{ document.version }} · {{ document.owner }} · {{ document.updatedAt }}</p>
        <hr class="t-rule">
        <!-- renderMarkdown escapes raw HTML; this is the only v-html in the app. -->
        <div class="sop-markdown" v-html="renderMarkdown(document.markdown)"></div>
        <p class="t-faint">문서 연결은 매핑 제안이며, 원인 판정은 재검증 전입니다.</p>
      </template>
      <p v-else class="t-empty">목록에서 문서를 선택해 주세요.</p>
    </article>
  </section>
</template>

<style scoped>
.sop-grid { display: grid; grid-template-columns: minmax(0, 345px) minmax(0, 1fr); gap: 24px; align-items: start; }
.sop-item { display: grid; gap: 8px; margin-top: 14px; color: var(--text); text-decoration: none; }
.sop-item.active { border-color: var(--border-strong); }
.sop-item strong { font-size: 13px; }
.sop-doc :deep(.sop-markdown) { color: var(--text); }
.sop-doc :deep(.sop-markdown pre), .sop-doc :deep(.sop-markdown th), .sop-doc :deep(.sop-markdown :not(pre) > code) { background: var(--surface-2); }
@media (max-width: 1080px) { .sop-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
