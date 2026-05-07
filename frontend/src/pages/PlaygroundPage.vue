<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import EChart from '../components/EChart.vue'

// ── ECharts theme helpers ─────────────────────────────────────────────────────
const C = { primary: '#7ab8d4', grid: '#1e1e1e', text: '#8a8884', bg: '#0a0a0a', surface: '#141414', green: '#39d98a', orange: '#e8a855', red: '#e8655a' }

function makeHistOption(scores, title = '') {
  if (!scores?.length) return null
  const min = Math.min(...scores), max = Math.max(...scores)
  const bins = 10
  const step = (max - min) / bins || 0.1
  const counts = Array(bins).fill(0)
  scores.forEach(s => {
    const i = Math.min(Math.floor((s - min) / step), bins - 1)
    counts[i]++
  })
  const xData = counts.map((_, i) => (min + i * step + step / 2).toFixed(2))
  return {
    backgroundColor: C.bg,
    tooltip: { trigger: 'axis', formatter: p => `Score: ${p[0].name}<br/>Count: ${p[0].value}` },
    grid: { left: 40, right: 16, top: 16, bottom: 36 },
    xAxis: { type: 'category', data: xData, axisLabel: { color: C.text, fontSize: 10 }, axisLine: { lineStyle: { color: C.grid } }, splitLine: { show: false } },
    yAxis: { type: 'value', axisLabel: { color: C.text, fontSize: 10 }, axisLine: { lineStyle: { color: C.grid } }, splitLine: { lineStyle: { color: C.grid } } },
    series: [{ type: 'bar', data: counts, itemStyle: { color: C.green, borderRadius: [2, 2, 0, 0] }, barMaxWidth: 32 }],
  }
}

function makeHeatmapOption(matrix, labels) {
  if (!matrix?.length) return null
  const n = matrix.length
  const data = []
  const diagData = []
  // Compute min/max excluding diagonal for proper color scaling
  let offMin = 1, offMax = 0
  for (let i = 0; i < n; i++)
    for (let j = 0; j < n; j++) {
      const v = +matrix[i][j].toFixed(3)
      if (i === j) {
        diagData.push([j, i, v])
      } else {
        data.push([j, i, v])
        if (v < offMin) offMin = v
        if (v > offMax) offMax = v
      }
    }
  // Round bounds for cleaner legend
  const vmMin = Math.floor(offMin * 10) / 10
  const vmMax = Math.ceil(offMax * 10) / 10
  const shortLabels = labels.map((l, i) => `#${i+1} ${l.slice(0, 18)}${l.length > 18 ? '…' : ''}`)
  return {
    backgroundColor: C.bg,
    tooltip: {
      position: 'top',
      formatter: p => {
        const isDiag = p.seriesIndex === 1
        const val = p.data[2]
        return `${shortLabels[p.data[1]]} × ${shortLabels[p.data[0]]}<br/>Similarity: <b>${val}</b>${isDiag ? ' (self)' : ''}`
      }
    },
    grid: { left: 160, right: 80, top: 16, bottom: 120 },
    xAxis: { type: 'category', data: shortLabels, axisLabel: { color: C.text, fontSize: 10, rotate: 30, interval: 0 }, axisLine: { lineStyle: { color: C.grid } }, splitArea: { show: true, areaStyle: { color: [C.bg, C.surface] } } },
    yAxis: { type: 'category', data: shortLabels, axisLabel: { color: C.text, fontSize: 10 }, axisLine: { lineStyle: { color: C.grid } }, splitArea: { show: true, areaStyle: { color: [C.bg, C.surface] } } },
    visualMap: { min: vmMin, max: vmMax, calculable: true, orient: 'vertical', right: 8, top: 'center', textStyle: { color: C.text, fontSize: 10 }, inRange: { color: ['#2a1a1a', '#e8655a', '#e8a855', '#39d98a'] } },
    series: [
      {
        type: 'heatmap', data,
        label: { show: n <= 12, formatter: p => p.data[2].toFixed(2), fontSize: 9, color: '#fff' },
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.5)' } }
      },
      {
        type: 'heatmap', data: diagData,
        label: { show: n <= 12, formatter: '1.00', fontSize: 9, color: '#555' },
        itemStyle: { borderColor: '#333', borderWidth: 1, color: '#1a1a1a' },
        emphasis: { itemStyle: { shadowBlur: 0 } }
      }
    ],
  }
}

function makeScatterOption(points) {
  if (!points?.length) return null
  const chunks = points.filter(p => p.type === 'chunk')
  const query = points.filter(p => p.type === 'query')
  return {
    backgroundColor: C.bg,
    labelLayout: { hideOverlap: true },
    tooltip: {
      trigger: 'item',
      formatter: p => {
        const d = p.data
        const label = d[3] === 'query' ? 'Query' : `#${d[2] + 1}`
        const text = d[4]?.length > 60 ? d[4].slice(0, 60) + '…' : d[4]
        return `<b style="color:${C.primary}">${label}</b><br/><span style="color:${C.text}">${text}</span>`
      }
    },
    grid: { left: 24, right: 24, top: 16, bottom: 24 },
    xAxis: { type: 'value', axisLabel: { show: false }, axisLine: { lineStyle: { color: C.grid } }, splitLine: { lineStyle: { color: C.grid, opacity: 0.3 } } },
    yAxis: { type: 'value', axisLabel: { show: false }, axisLine: { lineStyle: { color: C.grid } }, splitLine: { lineStyle: { color: C.grid, opacity: 0.3 } } },
    series: [
      {
        name: 'Chunks', type: 'scatter',
        data: chunks.map(p => [p.x, p.y, p.index, p.type, p.text]),
        symbolSize: 10,
        itemStyle: { color: C.green },
        label: {
          show: true,
          formatter: p => {
            const idx = p.data[2] + 1
            const txt = (p.data[4] || '').slice(0, 16)
            return `#${idx} ${txt}${p.data[4]?.length > 16 ? '…' : ''}`
          },
          position: 'top', fontSize: 9, color: C.text,
        },
      },
      ...(query.length ? [{
        name: 'Query', type: 'scatter',
        data: query.map(p => [p.x, p.y, p.index, p.type, p.text]),
        symbol: 'diamond', symbolSize: 14,
        itemStyle: { color: C.orange },
        label: { show: true, formatter: 'Query', position: 'top', fontSize: 9, color: C.orange },
      }] : []),
    ],
  }
}

function makeCvcScatterOption(points) {
  if (!points?.length) return null
  return {
    backgroundColor: C.bg,
    labelLayout: { hideOverlap: true },
    tooltip: {
      trigger: 'item',
      formatter: p => {
        const d = p.data
        const text = d[3]?.length > 60 ? d[3].slice(0, 60) + '…' : d[3]
        return `<b style="color:${C.primary}">#${d[2] + 1}</b><br/><span style="color:${C.text}">${text}</span>`
      }
    },
    grid: { left: 24, right: 24, top: 16, bottom: 24 },
    xAxis: { type: 'value', axisLabel: { show: false }, axisLine: { lineStyle: { color: C.grid } }, splitLine: { lineStyle: { color: C.grid, opacity: 0.3 } } },
    yAxis: { type: 'value', axisLabel: { show: false }, axisLine: { lineStyle: { color: C.grid } }, splitLine: { lineStyle: { color: C.grid, opacity: 0.3 } } },
    series: [{
      type: 'scatter',
      data: points.map(p => [p.x, p.y, p.index, p.text]),
      symbolSize: 10,
      itemStyle: { color: C.green },
      label: {
        show: true,
        formatter: p => {
          const idx = p.data[2] + 1
          const txt = (p.data[3] || '').slice(0, 16)
          return `#${idx} ${txt}${p.data[3]?.length > 16 ? '…' : ''}`
        },
        position: 'top', fontSize: 9, color: C.text,
      },
    }],
  }
}

const props = defineProps({
  view: {
    type: String,
    default: 'query_vs_chunks',
  },
})

// ── Shared state ──────────────────────────────────────────────────────────────
const models = ref([])
const selectedModel = ref('')
const strategy = ref('dense')
const topK = ref(5)
const threshold = ref(0)
const loading = ref(false)
const toast = ref('')

function showToast(msg, duration = 3000) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, duration)
}

async function fetchModels() {
  try {
    const res = await fetch('/api/models')
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    models.value = data
    if (data.length) selectedModel.value = data[0].id
  } catch (e) {
    showToast('Failed to load models: ' + e.message)
  }
}

onMounted(fetchModels)

// ── Query vs Chunks ───────────────────────────────────────────────────────────
const query = ref('')
const chunksTab = ref('adhoc')   // 'adhoc' | 'dataset'
const adhocText = ref('')
const datasets = ref([])
const selectedDataset = ref('')
const results = ref([])
const stats = ref(null)   // { time_ms, count }
const distOption = ref(null)
const tsneOption = ref(null)

const adhocChunks = computed(() => {
  if (!adhocText.value.trim()) return []
  return adhocText.value.split(/\n\n+/).map(s => s.trim()).filter(Boolean)
})

const activeChunks = computed(() => {
  if (chunksTab.value === 'adhoc') return adhocChunks.value
  return []   // dataset chunks are resolved server-side via dataset id
})

async function fetchDatasets() {
  try {
    const res = await fetch('/api/datasets')
    if (!res.ok) throw new Error(await res.text())
    datasets.value = await res.json()
  } catch (e) {
    showToast('Failed to load datasets: ' + e.message)
  }
}

// Dataset preview pagination (Query vs Chunks)
const dsPreviewOpen = ref(false)
const dsPreviewChunks = ref([])
const dsPreviewPage = ref(0)
const dsPreviewTotal = ref(0)
const dsPreviewTotalPages = ref(0)
const dsPreviewPageSize = 10

async function toggleDsPreview() {
  if (dsPreviewOpen.value) {
    dsPreviewOpen.value = false
    return
  }
  if (!selectedDataset.value) return
  dsPreviewOpen.value = true
  dsPreviewPage.value = 0
  await loadDsPreview(0)
}

async function loadDsPreview(page) {
  if (!selectedDataset.value) return
  dsPreviewPage.value = page
  try {
    const res = await fetch(`/api/datasets/${selectedDataset.value}/chunks?page=${page}&page_size=${dsPreviewPageSize}`)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    if (data.items) {
      dsPreviewChunks.value = data.items
      dsPreviewTotal.value = data.total
      dsPreviewTotalPages.value = data.total_pages
    } else {
      dsPreviewChunks.value = Array.isArray(data) ? data : []
      dsPreviewTotal.value = dsPreviewChunks.value.length
      dsPreviewTotalPages.value = 1
    }
  } catch {
    dsPreviewChunks.value = []
  }
}

function dsPageRange() {
  const pages = []
  const cur = dsPreviewPage.value
  const last = dsPreviewTotalPages.value - 1
  pages.push(0)
  for (let i = Math.max(1, cur - 2); i <= Math.min(last - 1, cur + 2); i++) {
    if (!pages.includes(i)) pages.push(i)
  }
  if (last > 0) pages.push(last)
  const result = []
  for (let i = 0; i < pages.length; i++) {
    if (i > 0 && pages[i] - pages[i - 1] > 1) result.push('...')
    result.push(pages[i])
  }
  return result
}

watch(() => chunksTab.value, (tab) => {
  if (tab === 'dataset' && !datasets.value.length) fetchDatasets()
})

async function runQuery() {
  if (!query.value.trim()) { showToast('Enter a query first.'); return }
  loading.value = true
  results.value = []
  stats.value = null
  try {
    const body = {
      query: query.value,
      chunks: chunksTab.value === 'adhoc' ? activeChunks.value : [],
      dataset_id: chunksTab.value === 'dataset' ? selectedDataset.value : null,
      strategy: strategy.value,
      model_id: selectedModel.value,
      top_k: topK.value,
      threshold: threshold.value,
    }
    const res = await fetch('/api/playground/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    results.value = data.results ?? []
    stats.value = { time_ms: data.elapsed_ms ?? null, count: data.total ?? 0 }
    distOption.value = makeHistOption(data.scores ?? [], 'Similarity Distribution')
    tsneOption.value = makeScatterOption(data.tsne_points ?? null)
  } catch (e) {
    showToast('Query failed: ' + e.message)
  } finally {
    loading.value = false
  }
}

function scoreClass(score) {
  if (score >= 0.8) return 'rl-score-high'
  if (score >= 0.5) return 'rl-score-mid'
  return 'rl-score-low'
}

// ── Chunk vs Chunk ────────────────────────────────────────────────────────────
const cvcTab = ref('adhoc')
const cvcAdhocText = ref('')
const cvcDataset = ref('')
const cvcMaxN = ref(30)
const cvcLoading = ref(false)
const cvcAvgSim = ref(null)
const cvcCohesion = ref(null)
const heatmapOption = ref(null)
const cvcDistOption = ref(null)
const cvcTsneOption = ref(null)

const cvcChunks = computed(() => {
  if (!cvcAdhocText.value.trim()) return []
  return cvcAdhocText.value.split(/\n\n+/).map(s => s.trim()).filter(Boolean)
})

// CVC dataset preview pagination
const cvcPreviewOpen = ref(false)
const cvcPreviewChunks = ref([])
const cvcPreviewPage = ref(0)
const cvcPreviewTotal = ref(0)
const cvcPreviewTotalPages = ref(0)
const cvcPreviewPageSize = 10

async function toggleCvcPreview() {
  if (cvcPreviewOpen.value) {
    cvcPreviewOpen.value = false
    return
  }
  if (!cvcDataset.value) return
  cvcPreviewOpen.value = true
  cvcPreviewPage.value = 0
  await loadCvcPreview(0)
}

async function loadCvcPreview(page) {
  if (!cvcDataset.value) return
  cvcPreviewPage.value = page
  try {
    const res = await fetch(`/api/datasets/${cvcDataset.value}/chunks?page=${page}&page_size=${cvcPreviewPageSize}`)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    if (data.items) {
      cvcPreviewChunks.value = data.items
      cvcPreviewTotal.value = data.total
      cvcPreviewTotalPages.value = data.total_pages
    } else {
      cvcPreviewChunks.value = Array.isArray(data) ? data : []
      cvcPreviewTotal.value = cvcPreviewChunks.value.length
      cvcPreviewTotalPages.value = 1
    }
  } catch {
    cvcPreviewChunks.value = []
  }
}

function cvcPageRange() {
  const pages = []
  const cur = cvcPreviewPage.value
  const last = cvcPreviewTotalPages.value - 1
  pages.push(0)
  for (let i = Math.max(1, cur - 2); i <= Math.min(last - 1, cur + 2); i++) {
    if (!pages.includes(i)) pages.push(i)
  }
  if (last > 0) pages.push(last)
  const result = []
  for (let i = 0; i < pages.length; i++) {
    if (i > 0 && pages[i] - pages[i - 1] > 1) result.push('...')
    result.push(pages[i])
  }
  return result
}

watch(() => cvcTab.value, (tab) => {
  if (tab === 'dataset' && !datasets.value.length) fetchDatasets()
})

async function runCvc() {
  cvcLoading.value = true
  cvcAvgSim.value = null
  cvcCohesion.value = null
  heatmapOption.value = null
  cvcDistOption.value = null
  cvcTsneOption.value = null
  try {
    const body = {
      chunks: cvcTab.value === 'adhoc' ? cvcChunks.value : [],
      dataset_id: cvcTab.value === 'dataset' ? cvcDataset.value : null,
      strategy: strategy.value,
      model_id: selectedModel.value,
      max_n: cvcMaxN.value,
    }
    const res = await fetch('/api/playground/chunk-vs-chunk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    cvcAvgSim.value = data.avg_sim ?? null
    cvcCohesion.value = data.cohesion ?? null
    heatmapOption.value = makeHeatmapOption(data.matrix ?? null, data.labels ?? [])
    cvcDistOption.value = makeHistOption(data.off_diag_scores ?? [], 'Similarity Distribution')
    cvcTsneOption.value = makeCvcScatterOption(data.tsne_points ?? null)
  } catch (e) {
    showToast('Analysis failed: ' + e.message)
  } finally {
    cvcLoading.value = false
  }
}

// All charts now use ECharts via EChart.vue component
</script>

<template>
  <!-- Toast notification -->
  <div
    v-if="toast"
    style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--surface-high);color:var(--on-surface);padding:10px 20px;border-radius:8px;border:1px solid var(--border);z-index:9999;font-size:13px;pointer-events:none;"
  >
    {{ toast }}
  </div>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- VIEW: query_vs_chunks                                                   -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <div
    v-if="view === 'query_vs_chunks'"
    style="display:grid;grid-template-columns:3fr 6fr 3fr;height:calc(100vh - 48px);padding:16px;gap:16px;overflow:hidden;"
  >
    <!-- LEFT: Retrieval Configuration -->
    <div class="rl-panel">
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="material-symbols-outlined" style="color:var(--primary);">tune</span>
        <span style="font-weight:700;font-size:14px;">Retrieval Configuration</span>
      </div>

      <!-- Embedding Model -->
      <div style="display:flex;flex-direction:column;gap:6px;">
        <label class="rl-label">Embedding Model</label>
        <select class="rl-select" v-model="selectedModel">
          <option v-for="m in models" :key="m.id" :value="m.id">
            {{ m.provider_name }}/{{ m.model_name }}
          </option>
          <option v-if="!models.length" value="">Loading…</option>
        </select>
      </div>

      <!-- Strategy -->
      <div style="display:flex;flex-direction:column;gap:6px;">
        <label class="rl-label">Strategy</label>
        <div class="rl-strategy-toggle">
          <button class="rl-strategy-btn" :class="{ active: strategy === 'dense' }" @click="strategy = 'dense'">Dense</button>
          <button class="rl-strategy-btn" :class="{ active: strategy === 'bm25' }" @click="strategy = 'bm25'">BM25</button>
        </div>
      </div>

      <!-- Top-K -->
      <div style="display:flex;flex-direction:column;gap:6px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <label class="rl-label">Top-K</label>
          <span style="font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--primary);">{{ topK }}</span>
        </div>
        <input type="range" min="1" max="20" step="1" v-model.number="topK" />
      </div>

      <!-- Similarity Threshold -->
      <div style="display:flex;flex-direction:column;gap:6px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <label class="rl-label">Similarity Threshold</label>
          <span style="font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--primary);">{{ threshold.toFixed(2) }}</span>
        </div>
        <input type="range" min="0" max="1" step="0.01" v-model.number="threshold" />
      </div>

      <div style="flex:1;"></div>

      <button class="rl-btn-primary" :disabled="loading" @click="runQuery">
        <span class="material-symbols-outlined" style="font-size:16px;">refresh</span>
        {{ loading ? 'Running…' : 'Re-run Query' }}
      </button>
    </div>

    <!-- CENTER -->
    <div style="display:flex;flex-direction:column;gap:16px;overflow:hidden;min-height:0;">
      <!-- Query input card -->
      <div class="rl-card" style="position:relative;flex-shrink:0;">
        <label class="rl-label" style="display:block;margin-bottom:8px;">Query</label>
        <textarea
          class="rl-input"
          rows="3"
          placeholder="Enter your query…"
          v-model="query"
          style="padding-right:48px;"
          @keydown.ctrl.enter="runQuery"
        ></textarea>
        <button
          class="rl-btn-icon"
          style="position:absolute;bottom:20px;right:20px;background:var(--primary);color:var(--on-primary);border-radius:8px;padding:6px;"
          :disabled="loading"
          @click="runQuery"
          title="Run (Ctrl+Enter)"
        >
          <span class="material-symbols-outlined" style="font-size:18px;">send</span>
        </button>
      </div>

      <!-- Chunks card -->
      <div class="rl-card" style="flex:1;overflow:hidden;display:flex;flex-direction:column;min-height:0;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-shrink:0;">
          <span style="font-weight:700;font-size:13px;">Top-Retrieved Chunks</span>
          <span
            v-if="results.length"
            style="background:var(--surface-high);color:var(--primary);font-family:'JetBrains Mono',monospace;font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--border);"
          >{{ results.length }} results</span>
        </div>

        <!-- Tab bar -->
        <div class="rl-tab-bar" style="flex-shrink:0;">
          <button class="rl-tab-btn" :class="{ active: chunksTab === 'adhoc' }" @click="chunksTab = 'adhoc'">Ad-hoc</button>
          <button class="rl-tab-btn" :class="{ active: chunksTab === 'dataset' }" @click="chunksTab = 'dataset'">Dataset</button>
        </div>

        <!-- Ad-hoc tab -->
        <div v-if="chunksTab === 'adhoc'" style="flex-shrink:0;margin-bottom:8px;">
          <textarea
            class="rl-input"
            rows="4"
            placeholder="Paste chunks here, separated by blank lines…"
            v-model="adhocText"
          ></textarea>
          <div style="font-size:11px;color:var(--on-surface-variant);margin-top:4px;">
            {{ adhocChunks.length }} chunk{{ adhocChunks.length !== 1 ? 's' : '' }} detected
          </div>
        </div>

        <!-- Dataset tab -->
        <div v-if="chunksTab === 'dataset'" style="flex-shrink:0;margin-bottom:8px;">
          <select class="rl-select" v-model="selectedDataset" @change="dsPreviewOpen = false">
            <option value="">Select a dataset…</option>
            <option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.name }}</option>
          </select>
          <div style="margin-top:6px;">
            <button
              class="rl-btn-secondary"
              style="font-size:11px;padding:4px 10px;width:auto;"
              :disabled="!selectedDataset"
              @click="toggleDsPreview"
            >
              <span class="material-symbols-outlined" style="font-size:14px;">preview</span>
              {{ dsPreviewOpen ? 'Hide' : 'Preview' }} Chunks
              <span v-if="dsPreviewOpen && dsPreviewTotal > 0" style="font-family:'JetBrains Mono',monospace;margin-left:4px;">({{ dsPreviewTotal }})</span>
            </button>
          </div>

          <!-- Dataset chunks preview with pagination -->
          <div v-if="dsPreviewOpen && dsPreviewChunks.length" style="margin-top:8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-input);overflow-y:auto;flex-shrink:1;min-height:0;">
            <div
              v-for="(chunk, i) in dsPreviewChunks"
              :key="chunk.id ?? i"
              style="padding:6px 8px;border-bottom:1px solid var(--border);font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--on-surface-variant);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
            >
              <span style="color:var(--on-surface-variant);font-size:10px;">#{{ (chunk.index ?? i) + 1 }}</span>
              {{ (chunk.content ?? '').slice(0, 80) }}{{ (chunk.content ?? '').length > 80 ? '…' : '' }}
            </div>
            <!-- Pagination -->
            <div v-if="dsPreviewTotalPages > 1" style="display:flex;align-items:center;justify-content:center;gap:3px;padding:6px;border-top:1px solid var(--border);">
              <button class="rl-btn-icon" :disabled="dsPreviewPage === 0" @click="loadDsPreview(0)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">first_page</span>
              </button>
              <button class="rl-btn-icon" :disabled="dsPreviewPage === 0" @click="loadDsPreview(dsPreviewPage - 1)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">chevron_left</span>
              </button>
              <template v-for="p in dsPageRange()" :key="'dp'+p">
                <span v-if="p === '...'" style="color:var(--on-surface-variant);font-size:10px;padding:0 2px;">…</span>
                <button
                  v-else
                  :style="{
                    background: p === dsPreviewPage ? 'var(--primary)' : 'transparent',
                    color: p === dsPreviewPage ? 'var(--on-primary)' : 'var(--on-surface-variant)',
                    border: '1px solid ' + (p === dsPreviewPage ? 'var(--primary)' : 'var(--border)'),
                    borderRadius: '4px', padding: '1px 6px', fontSize: '10px',
                    fontFamily: 'JetBrains Mono, monospace', cursor: 'pointer', minWidth: '22px',
                  }"
                  @click="loadDsPreview(p)"
                >{{ p + 1 }}</button>
              </template>
              <button class="rl-btn-icon" :disabled="dsPreviewPage >= dsPreviewTotalPages - 1" @click="loadDsPreview(dsPreviewPage + 1)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">chevron_right</span>
              </button>
              <button class="rl-btn-icon" :disabled="dsPreviewPage >= dsPreviewTotalPages - 1" @click="loadDsPreview(dsPreviewTotalPages - 1)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">last_page</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Results list -->
        <div style="flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:8px;min-height:0;">
          <div
            v-for="(r, i) in results"
            :key="i"
            class="rl-chunk-item"
            :class="{ top: i === 0 }"
          >
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
              <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--on-surface-variant);">#{{ r.index + 1 }}</span>
              <span class="rl-score-badge" :class="scoreClass(r.score)">{{ r.score.toFixed(4) }}</span>
            </div>
            <p style="margin:0;font-size:12px;color:var(--on-surface-variant);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">
              {{ r.text }}
            </p>
          </div>
          <div v-if="!results.length && !loading" style="color:var(--on-surface-variant);font-size:13px;text-align:center;padding:24px 0;">
            Run a query to see results.
          </div>
          <div v-if="loading" style="color:var(--on-surface-variant);font-size:13px;text-align:center;padding:24px 0;">
            Retrieving…
          </div>
        </div>
      </div>
    </div>

    <!-- RIGHT: Stats -->
    <div class="rl-panel">
      <!-- Stats grid -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="rl-card" style="text-align:center;">
          <div class="rl-label" style="margin-bottom:4px;">Retrieval Time</div>
          <div class="rl-num" style="font-size:28px;">
            {{ stats ? stats.time_ms : '—' }}
          </div>
          <div style="font-size:11px;color:var(--on-surface-variant);">ms</div>
        </div>
        <div class="rl-card" style="text-align:center;">
          <div class="rl-label" style="margin-bottom:4px;">Chunks</div>
          <div class="rl-num" style="font-size:28px;">
            {{ stats ? stats.count : '—' }}
          </div>
          <div style="font-size:11px;color:var(--on-surface-variant);">retrieved</div>
        </div>
      </div>

      <!-- Similarity Distribution -->
      <div>
        <div class="rl-label" style="margin-bottom:8px;">SIMILARITY DISTRIBUTION</div>
        <div style="background:var(--surface-input);border-radius:4px;overflow:hidden;min-height:120px;display:flex;align-items:center;justify-content:center;">
          <EChart v-if="distOption" :option="distOption" height="140px" title="Similarity Distribution" style="width:100%;" />
          <span v-else style="color:var(--on-surface-variant);font-size:12px;">No data yet</span>
        </div>
      </div>

      <!-- t-SNE Projection -->
      <div>
        <div class="rl-label" style="margin-bottom:8px;">T-SNE PROJECTION</div>
        <div style="background:var(--surface-input);border-radius:4px;overflow:hidden;min-height:160px;display:flex;align-items:center;justify-content:center;">
          <EChart v-if="tsneOption" :option="tsneOption" height="200px" title="t-SNE Projection" style="width:100%;" />
          <span v-else style="color:var(--on-surface-variant);font-size:12px;">No data yet</span>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!-- VIEW: chunk_vs_chunk                                                    -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <div
    v-else-if="view === 'chunk_vs_chunk'"
    style="display:grid;grid-template-columns:3fr 6fr 3fr;height:calc(100vh - 48px);padding:16px;gap:16px;overflow:hidden;"
  >
    <!-- LEFT: Config -->
    <div class="rl-panel">
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="material-symbols-outlined" style="color:var(--primary);">tune</span>
        <span style="font-weight:700;font-size:14px;">Analysis Configuration</span>
      </div>

      <!-- Embedding Model -->
      <div style="display:flex;flex-direction:column;gap:6px;">
        <label class="rl-label">Embedding Model</label>
        <select class="rl-select" v-model="selectedModel">
          <option v-for="m in models" :key="m.id" :value="m.id">
            {{ m.provider_name }}/{{ m.model_name }}
          </option>
          <option v-if="!models.length" value="">Loading…</option>
        </select>
      </div>

      <!-- Strategy -->
      <div style="display:flex;flex-direction:column;gap:6px;">
        <label class="rl-label">Strategy</label>
        <div class="rl-strategy-toggle">
          <button class="rl-strategy-btn" :class="{ active: strategy === 'dense' }" @click="strategy = 'dense'">Dense</button>
          <button class="rl-strategy-btn" :class="{ active: strategy === 'bm25' }" @click="strategy = 'bm25'">BM25</button>
        </div>
      </div>

      <!-- Matrix Size -->
      <div style="display:flex;flex-direction:column;gap:6px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <label class="rl-label">Matrix Size (max N)</label>
          <span style="font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--primary);">{{ cvcMaxN }}</span>
        </div>
        <input type="range" min="2" max="100" step="1" v-model.number="cvcMaxN" />
      </div>

      <div style="flex:1;"></div>

      <button class="rl-btn-primary" :disabled="cvcLoading" @click="runCvc">
        <span class="material-symbols-outlined" style="font-size:16px;">analytics</span>
        {{ cvcLoading ? 'Running…' : 'Run Analysis' }}
      </button>
    </div>

    <!-- CENTER: Chunks input + Similarity Matrix -->
    <div style="display:flex;flex-direction:column;gap:16px;overflow:hidden;min-height:0;">

      <!-- Chunks input card -->
      <div class="rl-card" style="display:flex;flex-direction:column;flex:1;overflow:hidden;min-height:0;">
        <div style="font-weight:700;font-size:13px;margin-bottom:8px;flex-shrink:0;">Chunks</div>

        <div class="rl-tab-bar" style="flex-shrink:0;">
          <button class="rl-tab-btn" :class="{ active: cvcTab === 'adhoc' }" @click="cvcTab = 'adhoc'">Ad-hoc</button>
          <button class="rl-tab-btn" :class="{ active: cvcTab === 'dataset' }" @click="cvcTab = 'dataset'">Dataset</button>
        </div>

        <div v-if="cvcTab === 'adhoc'" style="flex:1;display:flex;flex-direction:column;min-height:0;">
          <textarea
            class="rl-input"
            style="flex:1;resize:none;"
            placeholder="Paste chunks here, separated by blank lines…"
            v-model="cvcAdhocText"
          ></textarea>
          <div style="font-size:11px;color:var(--on-surface-variant);margin-top:6px;flex-shrink:0;">
            {{ cvcChunks.length }} chunk{{ cvcChunks.length !== 1 ? 's' : '' }} detected
          </div>
        </div>

        <div v-if="cvcTab === 'dataset'" style="flex-shrink:0;">
          <select class="rl-select" v-model="cvcDataset" @change="cvcPreviewOpen = false">
            <option value="">Select a dataset…</option>
            <option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.name }}</option>
          </select>
          <div style="margin-top:6px;">
            <button
              class="rl-btn-secondary"
              style="font-size:11px;padding:4px 10px;width:auto;"
              :disabled="!cvcDataset"
              @click="toggleCvcPreview"
            >
              <span class="material-symbols-outlined" style="font-size:14px;">preview</span>
              {{ cvcPreviewOpen ? 'Hide' : 'Preview' }} Chunks
              <span v-if="cvcPreviewOpen && cvcPreviewTotal > 0" style="font-family:'JetBrains Mono',monospace;margin-left:4px;">({{ cvcPreviewTotal }})</span>
            </button>
          </div>
          <div v-if="cvcPreviewOpen && cvcPreviewChunks.length" style="margin-top:8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-input);overflow-y:auto;flex-shrink:1;min-height:0;">
            <div
              v-for="(chunk, i) in cvcPreviewChunks"
              :key="chunk.id ?? i"
              style="padding:6px 8px;border-bottom:1px solid var(--border);font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--on-surface-variant);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
            >
              <span style="color:var(--on-surface-variant);font-size:10px;">#{{ (chunk.index ?? i) + 1 }}</span>
              {{ (chunk.content ?? '').slice(0, 80) }}{{ (chunk.content ?? '').length > 80 ? '…' : '' }}
            </div>
            <div v-if="cvcPreviewTotalPages > 1" style="display:flex;align-items:center;justify-content:center;gap:3px;padding:6px;border-top:1px solid var(--border);">
              <button class="rl-btn-icon" :disabled="cvcPreviewPage === 0" @click="loadCvcPreview(0)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">first_page</span>
              </button>
              <button class="rl-btn-icon" :disabled="cvcPreviewPage === 0" @click="loadCvcPreview(cvcPreviewPage - 1)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">chevron_left</span>
              </button>
              <template v-for="p in cvcPageRange()" :key="'cvp'+p">
                <span v-if="p === '...'" style="color:var(--on-surface-variant);font-size:10px;padding:0 2px;">…</span>
                <button
                  v-else
                  :style="{
                    background: p === cvcPreviewPage ? 'var(--primary)' : 'transparent',
                    color: p === cvcPreviewPage ? 'var(--on-primary)' : 'var(--on-surface-variant)',
                    border: '1px solid ' + (p === cvcPreviewPage ? 'var(--primary)' : 'var(--border)'),
                    borderRadius: '4px', padding: '1px 6px', fontSize: '10px',
                    fontFamily: 'JetBrains Mono, monospace', cursor: 'pointer', minWidth: '22px',
                  }"
                  @click="loadCvcPreview(p)"
                >{{ p + 1 }}</button>
              </template>
              <button class="rl-btn-icon" :disabled="cvcPreviewPage >= cvcPreviewTotalPages - 1" @click="loadCvcPreview(cvcPreviewPage + 1)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">chevron_right</span>
              </button>
              <button class="rl-btn-icon" :disabled="cvcPreviewPage >= cvcPreviewTotalPages - 1" @click="loadCvcPreview(cvcPreviewTotalPages - 1)" style="padding:2px;">
                <span class="material-symbols-outlined" style="font-size:14px;">last_page</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Similarity Matrix (heatmap) -->
      <div class="rl-card" style="flex-shrink:0;">
        <div class="rl-label" style="margin-bottom:8px;">SIMILARITY MATRIX (NxN)</div>
        <div style="background:var(--surface-input);border-radius:4px;overflow:hidden;display:flex;align-items:center;justify-content:center;min-height:180px;">
          <EChart v-if="heatmapOption" :option="heatmapOption" height="320px" title="Similarity Matrix" style="width:100%;" />
          <span v-else style="color:var(--on-surface-variant);font-size:12px;">Run analysis to generate matrix.</span>
        </div>
      </div>
    </div>

    <!-- RIGHT: Stats + Distribution + t-SNE -->
    <div class="rl-panel">

      <!-- Stat cards -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;flex-shrink:0;">
        <div style="background:var(--surface-high);border:1px solid var(--border);border-radius:6px;padding:12px;text-align:center;">
          <div class="rl-label" style="margin-bottom:4px;">AVG SIMILARITY</div>
          <div class="rl-num" style="font-size:28px;line-height:1;">
            {{ cvcAvgSim !== null ? cvcAvgSim.toFixed(2) : '—' }}
          </div>
        </div>
        <div style="background:var(--surface-high);border:1px solid var(--border);border-radius:6px;padding:12px;text-align:center;">
          <div class="rl-label" style="margin-bottom:4px;">COHESION</div>
          <div class="rl-num" style="font-size:28px;line-height:1;">
            {{ cvcCohesion !== null ? cvcCohesion.toFixed(0) + '%' : '—' }}
          </div>
        </div>
      </div>

      <!-- Similarity Distribution -->
      <div style="flex-shrink:0;">
        <div class="rl-label" style="margin-bottom:6px;">SIMILARITY DISTRIBUTION</div>
        <div style="background:var(--surface-input);border-radius:4px;overflow:hidden;min-height:80px;display:flex;align-items:center;justify-content:center;">
          <EChart v-if="cvcDistOption" :option="cvcDistOption" height="120px" title="Similarity Distribution" style="width:100%;" />
          <span v-else style="color:var(--on-surface-variant);font-size:12px;">No data yet</span>
        </div>
      </div>

      <!-- Clustering (t-SNE) -->
      <div style="flex-shrink:0;">
        <div class="rl-label" style="margin-bottom:6px;">CLUSTERING (T-SNE)</div>
        <div style="background:var(--surface-input);border-radius:4px;overflow:hidden;min-height:160px;display:flex;align-items:center;justify-content:center;">
          <EChart v-if="cvcTsneOption" :option="cvcTsneOption" height="200px" title="Clustering (t-SNE)" style="width:100%;" />
          <span v-else style="color:var(--on-surface-variant);font-size:12px;">No data yet</span>
        </div>
      </div>
    </div>
  </div>
</template>
