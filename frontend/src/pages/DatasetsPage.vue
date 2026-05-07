<script setup>
import { ref, computed, watch, onMounted } from 'vue'

// ── State ─────────────────────────────────────────────────────────────────────
const datasets = ref([])
const selectedDataset = ref(null)   // full dataset object
const selectedSource = ref(null)    // { dataset } — for now source === dataset

const showNewForm = ref(false)
const newDatasetName = ref('')
const creatingDataset = ref(false)

const showUpload = ref(false)
const showPaste = ref(false)
const pasteText = ref('')
const uploadLoading = ref(false)
const pasteLoading = ref(false)

// Raw text stored locally — Apply sends this + strategy params to API
const rawText = ref('')
const rawTextLabel = ref('')  // filename or "pasted text"

// Chunking config
const chunkStrategy = ref('recursive')
const chunkSize = ref(512)
const chunkOverlap = ref(64)
const applyingChunks = ref(false)
const previewChunks = ref([])

// Strategy metadata
const strategyOptions = [
  { value: 'recursive', label: 'Recursive', desc: 'Splits on paragraphs → sentences → characters (recommended)' },
  { value: 'fixed',     label: 'Fixed Size', desc: 'Splits every N characters with overlap' },
  { value: 'lines',     label: 'By Lines',   desc: 'One chunk per non-empty line' },
]
const currentStrategyDesc = computed(() =>
  strategyOptions.find(s => s.value === chunkStrategy.value)?.desc ?? ''
)
const showSizeParams = computed(() => chunkStrategy.value !== 'lines')
const canApply = computed(() => !!rawText.value && !!selectedSource.value)

// Live preview (debounced, no DB write)
const previewLoading = ref(false)
const previewCount = ref(null)   // total chunks from last preview call
let _previewTimer = null

async function fetchPreview() {
  if (!rawText.value) return
  previewLoading.value = true
  try {
    const res = await fetch('/api/preview-chunks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: rawText.value,
        strategy: chunkStrategy.value,
        chunk_size: chunkSize.value,
        overlap: chunkOverlap.value,
      }),
    })
    if (!res.ok) return
    const data = await res.json()
    previewCount.value = data.chunk_count
    previewChunks.value = (data.chunks ?? []).map((text, i) => ({ content: text, index: i }))
  } catch { /* silent */ } finally {
    previewLoading.value = false
  }
}

function schedulePreview() {
  if (!rawText.value) return
  clearTimeout(_previewTimer)
  _previewTimer = setTimeout(fetchPreview, 400)
}

watch([rawText, chunkStrategy, chunkSize, chunkOverlap], schedulePreview)

const toast = ref('')

function showToast(msg, duration = 3500) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, duration)
}

// ── API helpers ───────────────────────────────────────────────────────────────
async function fetchDatasets() {
  try {
    const res = await fetch('/api/datasets')
    if (!res.ok) throw new Error(await res.text())
    datasets.value = await res.json()
  } catch (e) {
    showToast('Failed to load datasets: ' + e.message)
  }
}

async function createDataset() {
  if (!newDatasetName.value.trim()) { showToast('Enter a dataset name.'); return }
  creatingDataset.value = true
  try {
    const res = await fetch('/api/datasets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newDatasetName.value.trim() }),
    })
    if (!res.ok) throw new Error(await res.text())
    newDatasetName.value = ''
    showNewForm.value = false
    await fetchDatasets()
  } catch (e) {
    showToast('Create failed: ' + e.message)
  } finally {
    creatingDataset.value = false
  }
}

async function deleteDataset(ds, e) {
  e.stopPropagation()
  if (!confirm(`Delete dataset "${ds.name}"?`)) return
  try {
    const res = await fetch(`/api/datasets/${ds.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await res.text())
    if (selectedDataset.value?.id === ds.id) {
      selectedDataset.value = null
      selectedSource.value = null
    }
    await fetchDatasets()
  } catch (e) {
    showToast('Delete failed: ' + e.message)
  }
}

async function clearSource(ds, e) {
  e.stopPropagation()
  if (!confirm(`Clear all chunks from "${ds.name}"?`)) return
  try {
    const res = await fetch(`/api/datasets/${ds.id}/chunks`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await res.text())
    previewChunks.value = []
    previewCount.value = null
    rawText.value = ''
    rawTextLabel.value = ''
    await fetchDatasets()
    showToast('All chunks cleared.')
  } catch (e) {
    showToast('Clear failed: ' + e.message)
  }
}

async function deleteChunk(chunk, e) {
  e.stopPropagation()
  try {
    const res = await fetch(`/api/datasets/${selectedSource.value.id}/chunks/${chunk.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await res.text())
    previewChunks.value = previewChunks.value.filter(c => c.id !== chunk.id)
    previewCount.value = previewCount.value ? previewCount.value - 1 : null
    await fetchDatasets()
  } catch (e) {
    showToast('Delete chunk failed: ' + e.message)
  }
}

function selectDataset(ds) {
  selectedDataset.value = ds
  selectedSource.value = null
  showUpload.value = false
  showPaste.value = false
  previewChunks.value = []
}

function selectSource(ds) {
  selectedSource.value = ds
  rawText.value = ''
  rawTextLabel.value = ''
  previewChunks.value = []
  loadPreview(ds)
}

async function loadPreview(ds) {
  try {
    const res = await fetch(`/api/datasets/${ds.id}/chunks`)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    previewChunks.value = Array.isArray(data) ? data : (data.chunks ?? [])
  } catch {
    previewChunks.value = []
  }
}

// File upload — read file locally, store as rawText
const fileInput = ref(null)

async function handleFileUpload(e) {
  const file = e.target.files?.[0]
  if (!file || !selectedDataset.value) return
  uploadLoading.value = true
  try {
    rawText.value = await file.text()
    rawTextLabel.value = file.name
    showUpload.value = false
    selectedSource.value = selectedDataset.value
    previewChunks.value = []
    showToast(`"${file.name}" loaded (${rawText.value.length} chars) — configure chunking and click Apply.`)
  } catch (e) {
    showToast('Read failed: ' + e.message)
  } finally {
    uploadLoading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function loadPastedText() {
  if (!pasteText.value.trim() || !selectedDataset.value) return
  rawText.value = pasteText.value.trim()
  rawTextLabel.value = 'pasted text'
  pasteText.value = ''
  showPaste.value = false
  selectedSource.value = selectedDataset.value
  previewChunks.value = []
  showToast('Text ready — configure chunking and click Apply.')
}

async function applyChunking() {
  if (!canApply.value) return
  applyingChunks.value = true
  try {
    const res = await fetch(`/api/datasets/${selectedSource.value.id}/chunks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: rawText.value,
        strategy: chunkStrategy.value,
        chunk_size: chunkSize.value,
        overlap: chunkOverlap.value,
      }),
    })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    showToast(`${data.chunk_count} chunks saved.`)
    // Show preview from response (API returns first 5 as strings)
    previewChunks.value = (data.chunks ?? []).map((text, i) => ({ content: text, index: i }))
    await fetchDatasets()
    // Refresh selectedDataset reference
    const refreshed = datasets.value.find(d => d.id === selectedSource.value.id)
    if (refreshed) { selectedDataset.value = refreshed; selectedSource.value = refreshed }
  } catch (e) {
    showToast('Apply failed: ' + e.message)
  } finally {
    applyingChunks.value = false
  }
}

onMounted(fetchDatasets)
</script>

<template>
  <!-- Toast -->
  <div
    v-if="toast"
    style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--surface-high);color:var(--on-surface);padding:10px 20px;border-radius:8px;border:1px solid var(--border);z-index:9999;font-size:13px;pointer-events:none;"
  >
    {{ toast }}
  </div>

  <div style="display:flex;height:calc(100vh - 48px);overflow:hidden;">

    <!-- LEFT: Dataset list (220px) -->
    <div style="width:220px;flex-shrink:0;border-right:1px solid var(--border);background:#000;display:flex;flex-direction:column;overflow:hidden;">
      <!-- Header -->
      <div style="padding:12px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;border-bottom:1px solid var(--border);">
        <span class="rl-label">Datasets</span>
        <button class="rl-btn-icon" @click="showNewForm = !showNewForm" title="Add dataset">
          <span class="material-symbols-outlined">add</span>
        </button>
      </div>

      <!-- New dataset form -->
      <div v-if="showNewForm" style="padding:8px;border-bottom:1px solid var(--border);flex-shrink:0;">
        <input
          class="rl-input"
          style="margin-bottom:6px;"
          placeholder="Dataset name…"
          v-model="newDatasetName"
          @keydown.enter="createDataset"
        />
        <button class="rl-btn-primary" :disabled="creatingDataset" @click="createDataset" style="font-size:12px;padding:6px 12px;">
          {{ creatingDataset ? 'Creating…' : 'Create' }}
        </button>
      </div>

      <!-- Dataset list -->
      <div style="flex:1;overflow-y:auto;">
        <div
          v-for="ds in datasets"
          :key="ds.id"
          class="rl-dataset-item"
          :class="{ active: selectedDataset?.id === ds.id }"
          @click="selectDataset(ds)"
        >
          <div style="display:flex;align-items:center;gap:8px;padding-right:24px;">
            <span class="material-symbols-outlined" style="font-size:16px;color:var(--on-surface-variant);">folder</span>
            <div style="min-width:0;">
              <div style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{{ ds.name }}</div>
              <div style="font-size:11px;">
                  <span class="rl-num">{{ ds.chunk_count ?? 0 }}</span>
                  <span style="color:var(--on-surface-variant);"> chunks</span>
                </div>
            </div>
          </div>
          <button
            class="rl-btn-icon"
            style="position:absolute;right:4px;top:50%;transform:translateY(-50%);"
            @click="deleteDataset(ds, $event)"
            title="Delete"
          >
            <span class="material-symbols-outlined" style="font-size:16px;">delete</span>
          </button>
        </div>
        <div v-if="!datasets.length" style="padding:16px;color:var(--on-surface-variant);font-size:12px;text-align:center;">
          No datasets yet.
        </div>
      </div>
    </div>

    <!-- MIDDLE: Sources (280px) -->
    <div style="width:280px;flex-shrink:0;border-right:1px solid var(--border);background:#0a0a0a;display:flex;flex-direction:column;overflow:hidden;">
      <!-- Header -->
      <div style="padding:12px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;border-bottom:1px solid var(--border);">
        <span class="rl-label">Sources</span>
      </div>

      <div v-if="!selectedDataset" style="padding:16px;color:var(--on-surface-variant);font-size:12px;">
        Select a dataset first.
      </div>

      <template v-else>
        <!-- Action buttons -->
        <div style="padding:8px;display:flex;gap:8px;flex-shrink:0;border-bottom:1px solid var(--border);">
          <button class="rl-btn-secondary" style="flex:1;font-size:12px;" @click="showUpload = !showUpload; showPaste = false;">
            <span class="material-symbols-outlined" style="font-size:14px;">upload_file</span>
            Upload File
          </button>
          <button class="rl-btn-secondary" style="flex:1;font-size:12px;" @click="showPaste = !showPaste; showUpload = false;">
            <span class="material-symbols-outlined" style="font-size:14px;">content_paste</span>
            Paste Text
          </button>
        </div>

        <!-- File upload area -->
        <div v-if="showUpload" style="padding:8px;border-bottom:1px solid var(--border);flex-shrink:0;">
          <input
            ref="fileInput"
            type="file"
            accept=".txt,.md"
            style="display:none;"
            @change="handleFileUpload"
          />
          <button
            class="rl-btn-secondary"
            style="width:100%;justify-content:center;"
            :disabled="uploadLoading"
            @click="fileInput.click()"
          >
            <span class="material-symbols-outlined" style="font-size:14px;">attach_file</span>
            {{ uploadLoading ? 'Uploading…' : 'Choose .txt / .md' }}
          </button>
        </div>

        <!-- Text paste area -->
        <div v-if="showPaste" style="padding:8px;border-bottom:1px solid var(--border);flex-shrink:0;">
          <textarea
            class="rl-input"
            rows="5"
            placeholder="Paste text here…"
            v-model="pasteText"
            style="margin-bottom:6px;"
          ></textarea>
          <button class="rl-btn-primary" :disabled="pasteLoading" @click="loadPastedText" style="font-size:12px;padding:6px 12px;">
            {{ pasteLoading ? 'Loading…' : 'Load' }}
          </button>
        </div>

        <!-- Source item (dataset itself acts as source) -->
        <div style="flex:1;overflow-y:auto;">
          <div
            class="rl-dataset-item"
            :class="{ active: selectedSource?.id === selectedDataset.id }"
            @click="selectSource(selectedDataset)"
            style="margin:4px;padding-right:56px;"
          >
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="material-symbols-outlined" style="font-size:16px;color:var(--on-surface-variant);">description</span>
              <div>
                <div style="font-size:13px;font-weight:600;">{{ selectedDataset.name }}</div>
                <div style="font-size:11px;">
                  <span class="rl-num">{{ selectedDataset.chunk_count ?? 0 }}</span>
                  <span style="color:var(--on-surface-variant);"> chunks</span>
                </div>
              </div>
            </div>
            <!-- Clear all chunks button -->
            <button
              v-if="(selectedDataset.chunk_count ?? 0) > 0"
              class="rl-btn-icon"
              style="position:absolute;right:4px;top:50%;transform:translateY(-50%);"
              title="Clear all chunks"
              @click="clearSource(selectedDataset, $event)"
            >
              <span class="material-symbols-outlined" style="font-size:16px;">delete_sweep</span>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- RIGHT: Chunking config + preview -->
    <div style="flex:1;overflow-y:auto;padding:24px;">
      <div v-if="!selectedSource" style="color:var(--on-surface-variant);font-size:13px;">
        Select a source to configure chunking.
      </div>

      <template v-else>
        <div style="max-width:800px;">
          <h1 style="font-size:32px;font-weight:700;margin:0 0 24px 0;color:var(--on-surface);">
            {{ selectedSource.name }}
          </h1>

          <!-- Chunking Strategy card -->
          <div class="rl-card" style="margin-bottom:16px;">
            <div style="font-weight:700;font-size:14px;margin-bottom:16px;display:flex;align-items:center;gap:8px;">
              <span class="material-symbols-outlined" style="color:var(--primary);">cut</span>
              Chunking Strategy
            </div>

            <div style="display:flex;flex-direction:column;gap:12px;">
              <div>
                <label class="rl-label" style="display:block;margin-bottom:6px;">Strategy</label>
                <select class="rl-select" v-model="chunkStrategy">
                  <option v-for="s in strategyOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
                <p style="margin:4px 0 0;font-size:11px;color:var(--on-surface-variant);">{{ currentStrategyDesc }}</p>
              </div>

              <div v-if="showSizeParams" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                  <label class="rl-label" style="display:block;margin-bottom:6px;">Chunk Size</label>
                  <input class="rl-input" type="number" min="64" max="4096" v-model.number="chunkSize" />
                </div>
                <div>
                  <label class="rl-label" style="display:block;margin-bottom:6px;">Overlap</label>
                  <input class="rl-input" type="number" min="0" max="512" v-model.number="chunkOverlap" />
                </div>
              </div>

              <!-- Raw text status -->
              <div v-if="rawText" style="font-size:11px;color:var(--primary);display:flex;align-items:center;gap:4px;">
                <span class="material-symbols-outlined" style="font-size:13px;">check_circle</span>
                {{ rawTextLabel }} ready ({{ rawText.length }} chars)
              </div>
              <div v-else-if="selectedSource" style="font-size:11px;color:var(--on-surface-variant);">
                Paste or upload text to enable re-chunking.
              </div>

              <button class="rl-btn-primary" :disabled="applyingChunks || !canApply" @click="applyChunking" style="width:auto;align-self:flex-start;padding:8px 24px;">
                <span class="material-symbols-outlined" style="font-size:16px;">check</span>
                {{ applyingChunks ? 'Applying…' : 'Apply' }}
              </button>
            </div>
          </div>

          <!-- Chunking Preview card -->
          <div class="rl-card">
            <div style="font-weight:700;font-size:14px;margin-bottom:16px;display:flex;align-items:center;gap:8px;">
              <span class="material-symbols-outlined" style="color:var(--primary);">preview</span>
              Chunking Preview
              <span v-if="previewLoading" style="font-size:11px;color:var(--on-surface-variant);font-weight:400;">computing…</span>
              <span v-else-if="previewCount !== null" style="font-size:11px;color:var(--on-surface-variant);font-weight:400;">
                first {{ previewChunks.length }} of {{ previewCount }} chunks
                <span v-if="rawText" style="color:var(--primary);margin-left:4px;">· preview only</span>
              </span>
              <span v-else style="font-size:12px;color:var(--on-surface-variant);font-weight:400;">(first 20 chunks)</span>
            </div>

            <div v-if="!previewChunks.length" style="color:var(--on-surface-variant);font-size:12px;">
              {{ rawText ? 'Computing preview…' : 'Load text to see a live preview.' }}
            </div>

            <div v-else style="display:flex;flex-direction:column;gap:8px;">
              <div
                v-for="(chunk, i) in previewChunks"
                :key="chunk.id ?? i"
                class="rl-chunk-item"
                style="position:relative;"
              >
                <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;padding-right:24px;">
                  <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--on-surface-variant);">#{{ (chunk.index ?? i) + 1 }}</span>
                  <span class="rl-num" style="font-size:10px;">{{ (chunk.content ?? chunk).length }}</span>
                  <span style="font-size:10px;color:var(--on-surface-variant);">chars</span>
                </div>
                <p style="margin:0;font-size:12px;color:var(--on-surface-variant);font-family:'JetBrains Mono',monospace;white-space:pre-wrap;word-break:break-all;">
                  {{ (chunk.content ?? chunk).slice(0, 300) }}{{ (chunk.content ?? chunk).length > 300 ? '…' : '' }}
                </p>
                <!-- Delete single chunk (only when viewing saved chunks, not preview) -->
                <button
                  v-if="chunk.id"
                  class="rl-btn-icon"
                  style="position:absolute;top:6px;right:6px;opacity:0.4;"
                  title="Delete this chunk"
                  @click="deleteChunk(chunk, $event)"
                  @mouseenter="$event.target.closest('button').style.opacity='1'"
                  @mouseleave="$event.target.closest('button').style.opacity='0.4'"
                >
                  <span class="material-symbols-outlined" style="font-size:14px;">close</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
