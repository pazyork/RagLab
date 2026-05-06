<script setup>
import { ref, computed, onMounted, watch } from 'vue'

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
const stats = ref(null)   // { time_ms, count, similarity_dist_b64, tsne_b64 }

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
    stats.value = data.stats ?? null
  } catch (e) {
    showToast('Query failed: ' + e.message)
  } finally {
    loading.value = false
  }
}

function scoreClass(score) {
  return score >= 0.8 ? 'rl-score-high' : 'rl-score-mid'
}

// ── Chunk vs Chunk ────────────────────────────────────────────────────────────
const cvcTab = ref('adhoc')
const cvcAdhocText = ref('')
const cvcDataset = ref('')
const cvcMaxN = ref(30)
const cvcLoading = ref(false)
const heatmapB64 = ref('')

const cvcChunks = computed(() => {
  if (!cvcAdhocText.value.trim()) return []
  return cvcAdhocText.value.split(/\n\n+/).map(s => s.trim()).filter(Boolean)
})

watch(() => cvcTab.value, (tab) => {
  if (tab === 'dataset' && !datasets.value.length) fetchDatasets()
})

async function runCvc() {
  cvcLoading.value = true
  heatmapB64.value = ''
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
    heatmapB64.value = data.heatmap_b64 ?? ''
  } catch (e) {
    showToast('Analysis failed: ' + e.message)
  } finally {
    cvcLoading.value = false
  }
}
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
          <select class="rl-select" v-model="selectedDataset">
            <option value="">Select a dataset…</option>
            <option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.name }}</option>
          </select>
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
              <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--on-surface-variant);">#{{ i + 1 }}</span>
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
          <div style="font-size:28px;font-weight:700;color:var(--primary);font-family:'JetBrains Mono',monospace;">
            {{ stats ? stats.time_ms : '—' }}
          </div>
          <div style="font-size:11px;color:var(--on-surface-variant);">ms</div>
        </div>
        <div class="rl-card" style="text-align:center;">
          <div class="rl-label" style="margin-bottom:4px;">Chunks</div>
          <div style="font-size:28px;font-weight:700;color:var(--primary);font-family:'JetBrains Mono',monospace;">
            {{ stats ? stats.count : '—' }}
          </div>
          <div style="font-size:11px;color:var(--on-surface-variant);">retrieved</div>
        </div>
      </div>

      <!-- Similarity Distribution -->
      <div>
        <div class="rl-label" style="margin-bottom:8px;">Similarity Distribution</div>
        <div style="background:var(--surface-input);border-radius:4px;overflow:hidden;min-height:120px;display:flex;align-items:center;justify-content:center;">
          <img
            v-if="stats && stats.similarity_dist_b64"
            :src="'data:image/png;base64,' + stats.similarity_dist_b64"
            style="width:100%;display:block;"
            alt="Similarity distribution chart"
          />
          <span v-else style="color:var(--on-surface-variant);font-size:12px;">No data yet</span>
        </div>
      </div>

      <!-- t-SNE Projection -->
      <div>
        <div class="rl-label" style="margin-bottom:8px;">t-SNE Projection</div>
        <div style="background:var(--surface-input);border-radius:4px;overflow:hidden;min-height:120px;display:flex;align-items:center;justify-content:center;">
          <img
            v-if="stats && stats.tsne_b64"
            :src="'data:image/png;base64,' + stats.tsne_b64"
            style="width:100%;display:block;"
            alt="t-SNE projection chart"
          />
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

    <!-- CENTER: Chunks input -->
    <div class="rl-card" style="display:flex;flex-direction:column;overflow:hidden;min-height:0;">
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
        <select class="rl-select" v-model="cvcDataset">
          <option value="">Select a dataset…</option>
          <option v-for="ds in datasets" :key="ds.id" :value="ds.id">{{ ds.name }}</option>
        </select>
      </div>
    </div>

    <!-- RIGHT: Heatmap -->
    <div class="rl-panel">
      <div class="rl-label">Similarity Heatmap</div>
      <div style="flex:1;background:var(--surface-input);border-radius:4px;overflow:hidden;display:flex;align-items:center;justify-content:center;min-height:200px;">
        <img
          v-if="heatmapB64"
          :src="'data:image/png;base64,' + heatmapB64"
          style="width:100%;height:100%;object-fit:contain;display:block;"
          alt="Similarity heatmap"
        />
        <span v-else style="color:var(--on-surface-variant);font-size:12px;">Run analysis to see heatmap.</span>
      </div>
    </div>
  </div>
</template>
