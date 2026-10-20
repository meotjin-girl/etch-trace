<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSop, listSops, type Sop, type SopSummary } from '@/api/sop'
import { renderMarkdown } from '@/lib/markdown'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()
const summaries = ref<SopSummary[]>([])
const listError = ref('')
const document = ref<Sop | null>(null)
const detailError = ref('')
const loading = ref(false)
const detail = ref<HTMLElement>()
const selected = computed(() => route.params.id as string | undefined)
let request = 0

const filtered = computed(() => {
  const term = ui.sopQuery.trim().toLocaleLowerCase()
  return summaries.value.filter(item =>
    [item.id, item.title, item.category, item.description, ...(item.tags || [])]
      .join(' ').toLocaleLowerCase().includes(term))
})

async function load(id: string) {
  const current = ++request
  loading.value = true
  detailError.value = ''
  try {
    const item = await getSop(id)
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
    summaries.value = await listSops()
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
  <section id="sopPage" class="sop-page" aria-label="SOP 목록">
    <div class="sop-sample-notice">샘플 페이지 · 아래 문서는 화면 구성을 위한 예시이며 실제 작업 지침이 아닙니다.</div>
    <div class="sop-layout">
      <section class="sop-list-panel" aria-label="SOP 문서 목록">
        <p class="sop-count" role="status">{{ listError ? '문서를 불러오지 못했습니다.' : summaries.length ? `${filtered.length}개 문서 · 샘플` : '문서를 불러오는 중…' }}</p>
        <div>
          <p v-if="listError" class="sop-empty" role="alert">{{ listError }}</p>
          <template v-else-if="filtered.length">
            <RouterLink v-for="item in filtered" :key="item.id" v-slot="{ navigate }" :to="`/sop/${encodeURIComponent(item.id)}`" custom>
              <button type="button" class="sop-list-item" :class="{active: item.id === selected}" :aria-pressed="item.id === selected" @click="navigate">
                <span class="sop-document-id">{{ item.id }} <span>v{{ item.version }}</span></span>
                <strong>{{ item.title }}</strong><span class="sop-description">{{ item.description }}</span>
                <span class="sop-list-meta">{{ item.category }} · {{ item.updatedAt }}</span>
              </button>
            </RouterLink>
          </template>
          <p v-else-if="summaries.length" class="sop-empty">검색 결과가 없습니다. 다른 키워드로 검색해 주세요.</p>
        </div>
      </section>
      <article ref="detail" class="sop-detail" aria-label="SOP 문서 상세">
        <p v-if="loading" class="sop-empty" role="status">문서를 불러오는 중…</p>
        <p v-else-if="detailError" class="sop-empty" role="alert">{{ detailError }}</p>
        <template v-else-if="document">
          <header class="sop-document-header">
            <div class="sop-document-id">{{ document.id }} <span class="sop-sample-badge">샘플 문서</span></div>
            <h2 tabindex="-1">{{ document.title }}</h2>
            <p>{{ document.description }}</p>
            <dl class="sop-metadata">
              <div><dt>버전</dt><dd>{{ document.version }}</dd></div>
              <div><dt>최근 개정</dt><dd>{{ document.updatedAt }}</dd></div>
              <div><dt>담당</dt><dd>{{ document.owner }}</dd></div>
            </dl>
            <div class="sop-tags"><span v-for="tag in document.tags" :key="tag">{{ tag }}</span></div>
          </header>
          <!-- renderMarkdown escapes raw HTML; this is the only v-html in the app. -->
          <div class="sop-markdown" v-html="renderMarkdown(document.markdown)"></div>
        </template>
        <p v-else class="sop-empty">목록에서 문서를 선택해 주세요.</p>
      </article>
    </div>
  </section>
</template>
