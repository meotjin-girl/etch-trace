<script setup lang="ts">
import { computed } from 'vue'
import type { Report } from '@/api/types'
import { agentMode, labels, number, stageStatus, text, units } from '@/lib/format'
import { useUiStore } from '@/stores/ui'

// Section order follows develop's report: summary, metrics, specialist stages,
// similar approved history, cause candidates, SOP RAG clauses, document evidence.
const props = defineProps<{ report: Report }>()
const ui = useUiStore()

const heading = computed(() => {
  const context = props.report.context || {}
  return [context.equipment, context.chamber, context.recipe].filter(Boolean).join(' / ') || '조사'
})
const simulationFrame = computed(() => props.report.educationalSimulation?.profile_frames?.at(-1))
const profileHeight = computed(() => Math.min(150, Math.max(
  2, (simulationFrame.value?.aspect_ratio || 0) * 55,
)))
</script>

<template>
  <p class="message-label">근거 기반 조사 결과{{ report.demo === true ? ' · 데모 데이터' : '' }}</p>
  <h2>{{ heading }} 분석 결과</h2>
  <p class="answer-summary report-text">{{ text(report.summary) }}</p>
  <div class="analysis-grid">
    <div v-for="(metric, index) in report.metrics" :key="index" class="metric-card">
      <header><strong>{{ labels[metric.key] || metric.key }}</strong><span class="severity">{{ metric.severity }}</span></header>
      <div class="metric-values"><b>{{ metric.value }}</b><span>{{ units[metric.key] || '' }} · 비교군 평균 {{ number(metric.mean) }}</span></div>
      <div class="delta">평균 대비 {{ number(metric.deltaPct) }}% · z-score {{ number(metric.z) }}</div>
    </div>
    <p v-if="!report.metrics?.length">계측값 미제공</p>
  </div>

  <section v-if="report.physicsResults?.length" class="answer-section">
    <h3>물리 계산 검증</h3>
    <p class="section-note">계산값은 입력 계측값과 표시된 가정으로 산출한 예상값이며 실제 계측 결과가 아닙니다.</p>
    <ol class="stage-list">
      <li v-for="item in report.physicsResults" :key="item.model">
        <header>
          <strong>{{ item.model }}</strong>
          <span class="severity">{{ item.status }}</span>
        </header>
        <p v-if="item.result"><b>계산값:</b> {{ number(item.result.value) }} {{ item.result.unit }} · {{ item.formula }}</p>
        <p v-if="item.inputs?.length"><b>입력:</b> {{ item.inputs.map(input => `${input.key}=${input.value} ${input.unit} (${input.source})`).join(' · ') }}</p>
        <p v-for="assumption in item.assumptions" :key="assumption" class="stage-unknown">가정: {{ assumption }}</p>
        <p v-if="item.missing_fields?.length" class="stage-unknown">추가 데이터 필요: {{ item.missing_fields.join(', ') }}</p>
        <p v-for="warning in item.warnings" :key="warning" class="stage-unknown">주의: {{ warning }}</p>
      </li>
    </ol>
  </section>

  <section v-if="report.quantitativeResults?.length" class="answer-section">
    <h3>고도화 정량 분석</h3>
    <p class="section-note">측정값·계산값·가정 기반 시뮬레이션과 검증 상태를 분리해 표시합니다.</p>
    <ol class="stage-list">
      <li v-for="item in report.quantitativeResults" :key="item.analysis">
        <header><strong>{{ item.problem }}</strong><span class="severity">{{ item.status }} · {{ item.validation_status }}</span></header>
        <p v-if="item.results?.length"><b>결과:</b> {{ item.results.map(value => `${value.key}=${number(value.value)} ${value.unit} (${value.origin})`).join(' · ') }}</p>
        <p v-if="item.interpretation">{{ item.interpretation }}</p>
        <p v-if="item.reference_ids?.length" class="stage-unknown">기준 Run: {{ item.reference_ids.join(', ') }}</p>
        <p v-if="item.missing_fields?.length" class="stage-unknown">추가 데이터 필요: {{ item.missing_fields.join(', ') }}</p>
        <p v-for="warning in item.warnings" :key="warning" class="stage-unknown">주의: {{ warning }}</p>
      </li>
    </ol>
  </section>

  <section v-if="report.sensorAnalysis" class="answer-section">
    <h3>센서 시계열 정량 분석</h3>
    <p class="section-note">{{ report.sensorAnalysis.problem }} · {{ report.sensorAnalysis.status }}</p>
    <ol v-if="report.sensorAnalysis.signals?.length" class="stage-list">
      <li v-for="signal in report.sensorAnalysis.signals" :key="signal.sensor">
        <header><strong>{{ signal.sensor }}</strong><span class="severity">{{ signal.threshold_source }}</span></header>
        <p>평균 {{ number(signal.mean) }} {{ signal.unit }} · 범위 {{ number(signal.minimum) }}~{{ number(signal.maximum) }} {{ signal.unit }}</p>
        <p v-if="signal.first_anomaly_sec != null">최초 이상 {{ number(signal.first_anomaly_sec) }}초 · 지속 {{ number(signal.anomaly_duration_sec) }}초</p>
        <p v-if="signal.cooccurring_sensors?.length" class="stage-unknown">동반 이상: {{ signal.cooccurring_sensors.join(', ') }} — 인과관계 아님</p>
        <p v-if="signal.related_alarms?.length">알람 {{ signal.related_alarms.join(', ') }}</p>
        <p v-if="signal.ocap_ids?.length">관련 OCAP {{ signal.ocap_ids.join(', ') }}</p>
      </li>
    </ol>
    <p v-for="warning in report.sensorAnalysis.warnings" :key="warning" class="stage-unknown">주의: {{ warning }}</p>
  </section>

  <section v-if="report.educationalSimulation" class="answer-section">
    <h3>교육용 식각 시뮬레이션 · 실제 조사 결과와 분리</h3>
    <p class="section-note">
      {{ report.educationalSimulation.status }} · {{ report.educationalSimulation.validation_status }} ·
      실측값 또는 검증된 예측값이 아닙니다.
    </p>
    <template v-if="simulationFrame">
      <p>
        최종 가정 깊이 {{ number(simulationFrame.depth_nm) }} nm ·
        Aspect Ratio {{ number(simulationFrame.aspect_ratio) }} ·
        고정 개구 폭 {{ number(simulationFrame.opening_width_nm) }} nm
      </p>
      <p v-if="report.educationalSimulation.arde_coefficient != null">
        ARDE k={{ number(report.educationalSimulation.arde_coefficient) }} · 미보정 교육용 가정
      </p>
      <svg viewBox="0 0 240 190" role="img" aria-label="고정 폭 직사각형 식각 제거 영역">
        <rect x="20" y="10" width="200" height="18" fill="#9ca3af" />
        <rect x="70" y="10" width="100" :height="profileHeight" fill="#dbeafe" stroke="#2563eb" />
        <text x="120" y="180" text-anchor="middle" font-size="11">교육용 단순 직사각형 · Bowing/Taper 미예측</text>
      </svg>
    </template>
    <p v-if="report.educationalSimulation.relative_rate_series?.length">
      Level 2 상대 식각률 범위
      {{ number(Math.min(...report.educationalSimulation.relative_rate_series.map(item => item.relative_rate))) }}~
      {{ number(Math.max(...report.educationalSimulation.relative_rate_series.map(item => item.relative_rate))) }}
    </p>
    <p v-if="report.educationalSimulation.coefficients?.length">
      미보정 민감도 계수:
      {{ report.educationalSimulation.coefficients.map(item => `${item.variable}=${number(item.value)}`).join(' · ') }}
    </p>
    <p v-for="formula in report.educationalSimulation.formulas" :key="formula"><code>{{ formula }}</code></p>
    <p v-if="report.educationalSimulation.missing_fields?.length" class="stage-unknown">
      추가 입력 필요: {{ report.educationalSimulation.missing_fields.join(', ') }}
    </p>
    <p v-for="assumption in report.educationalSimulation.assumptions" :key="assumption" class="stage-unknown">가정: {{ assumption }}</p>
    <p v-for="warning in report.educationalSimulation.warnings" :key="warning" class="stage-unknown">주의: {{ warning }}</p>
  </section>

  <section v-if="report.stages?.length" class="answer-section">
    <h3>조사 단계별 결과</h3>
    <p class="section-note">데모 사례 분석, 사용자 입력값, 아직 연결되지 않은 실제 시스템 데이터를 구분했습니다.</p>
    <ol class="stage-list">
      <li v-for="stage in report.stages" :key="stage.key">
        <header>
          <strong>{{ stage.title }}</strong>
          <span class="severity">{{ stageStatus[stage.status] || stage.status }} · {{ agentMode(stage.agent_mode) }}</span>
        </header>
        <p v-for="(item, index) in stage.findings" :key="`f${index}`">{{ item }}</p>
        <p v-for="(item, index) in stage.unknowns" :key="`u${index}`" class="stage-unknown">미확인: {{ item }}</p>
      </li>
    </ol>
  </section>

  <section v-if="report.history?.length" class="answer-section">
    <h3>유사 승인 조사 이력</h3>
    <p class="section-note">요청자 권한으로 조회된 과거 승인 기록입니다. 과거 결과가 현재 원인을 확정하지 않습니다.</p>
    <ol class="stage-list">
      <li v-for="item in report.history" :key="item.id">
        <header>
          <strong>{{ item.question }}</strong>
          <span class="severity">승인된 과거 조사 · {{ item.approvedAt }}</span>
        </header>
        <p>{{ item.summary }}</p>
        <p v-for="(cause, index) in item.causes" :key="index">과거 후보: {{ cause }}</p>
        <p class="stage-unknown">조사 ID {{ item.id }}{{ item.lotId ? ` · Lot ${item.lotId}` : '' }}{{ item.eventTime ? ` · 발생 시각 ${item.eventTime}` : '' }}</p>
        <div v-if="item.docIds?.length">
          <button v-for="doc in item.docIds" :key="doc" type="button" class="citation" @click="ui.openEvidence(doc)">[{{ doc }}]</button>
        </div>
      </li>
    </ol>
  </section>

  <section class="answer-section">
    <h3>우선 확인할 항목</h3>
    <div class="cause-list">
      <div v-for="(item, index) in report.causeCases" :key="index" class="cause-item">
        <span>{{ index + 1 }}</span>
        <div><strong>{{ item.cause }}</strong><small>{{ item.action }}</small></div>
        <span class="citation">[{{ item.id }}]</span>
        <div class="cause-docs">
          <button v-for="doc in item.docs" :key="doc" type="button" class="citation" @click="ui.openEvidence(doc)">[{{ doc }}]</button>
        </div>
      </div>
      <p v-if="!report.causeCases?.length">원인 후보를 좁힐 근거가 부족합니다.</p>
    </div>
  </section>

  <section v-if="report.checks?.length" class="answer-section">
    <h3>SOP RAG 검색 결과 · 우선 확인 순서</h3>
    <p class="section-note">RAG MCP가 SOP/WI/SPEC에서 검색해 재순위화한 조항입니다. 실제 장비 센서·정비 데이터를 확인한 결과나 확정 조치가 아닙니다.</p>
    <ol class="stage-list">
      <li v-for="item in report.checks" :key="item.docId || item.title">
        <header>
          <strong>{{ item.title }}</strong>
          <button v-if="item.docId" type="button" class="citation" @click="ui.openEvidence(item.docId)">[{{ item.docId }}]</button>
        </header>
        <p>{{ item.rationale }}</p>
      </li>
    </ol>
  </section>

  <section class="answer-section">
    <h3>문서 근거</h3>
    <button v-for="doc in report.docIds" :key="doc" type="button" class="citation" @click="ui.openEvidence(doc)">[{{ doc }}]</button>
  </section>
</template>
