<script setup lang="ts">
import { onMounted } from 'vue'
import { date, shortId } from '@/lib/format'
import { useLiveInvestigationsStore } from '@/stores/live-investigations'

const live = useLiveInvestigationsStore()
onMounted(() => { void live.refreshList() })
</script>

<template>
  <section class="records-page" data-testid="investigation-list" :aria-busy="live.loadingList">
    <div class="records-heading">
      <div>
        <span class="record-count">{{ live.records.length }}건</span>
        <button class="secondary-button" type="button" :disabled="live.loadingList" @click="live.refreshList()">새로고침</button>
      </div>
    </div>
    <div v-if="live.listError" class="network-notice" role="alert">{{ live.listError }}
      <button class="secondary-button" type="button" :disabled="live.loadingList" @click="live.refreshList()">다시 연결</button>
    </div>
    <p v-if="live.loadingList && !live.records.length" role="status">조사 목록을 불러오는 중…</p>
    <div v-else-if="!live.records.length && !live.listError" class="records-empty">
      <strong>등록된 조사가 없습니다</strong>
      <p>장비 경보에서 시작된 조사와 원인 후보가 여기에 표시됩니다.</p>
    </div>
    <div class="record-list live-list">
      <RouterLink v-for="item in live.records" :key="item.id" class="record-list-item"
        :data-investigation-id="item.id" :to="`/investigations/${encodeURIComponent(item.id)}`">
        <header>
          <span class="record-id" :title="item.id">#{{ shortId(item.id) }}</span>
          <span class="record-status">{{ item.approved_at ? '승인됨' : '검토 대기' }}</span>
        </header>
        <strong class="record-title">{{ item.summary }}</strong>
        <span>{{ item.tool_id }} · {{ item.chamber_id }} · {{ item.lot_id }}</span>
        <small>후보 {{ item.candidate_count }}개 · 버전 {{ item.revision }} · {{ date(item.updated_at) }} · 데모</small>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.live-list { max-width: 980px; margin: 0 auto; }
.record-list-item { text-decoration: none; }
.records-empty p { word-break: keep-all; }
</style>
