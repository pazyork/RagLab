<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { fetchJson } from '../utils/api.js'
import { useI18n } from '../utils/i18n.js'

const { t } = useI18n()

// ── State ─────────────────────────────────────────────────────────────────────
const datasets = ref([])
const selectedDataset = ref(null)   // full dataset object
const selectedSource = ref(null)    // dataset currently being viewed/chunked
const viewingSourceName = ref(null) // name of existing source being viewed (null = all/new)

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

// Sources for selected dataset
const sources = ref([])

// Pagination for saved chunks
const chunkPage = ref(0)
const chunkPageSize = ref(50)
const chunkTotal = ref(0)
const chunkTotalPages = ref(0)
const chunkPageSizeOptions = [20, 50, 100]
let _loadPreviewGen = 0  // race condition guard

// Strategy metadata
const strategyOptions = [
  { value: 'recursive', label: 'Recursive' },
  { value: 'fixed',     label: 'Fixed Size' },
  { value: 'lines',     label: 'By Lines'   },
  { value: 'markdown',  label: 'Markdown'   },
]
const currentStrategyDesc = computed(() =>
  t(`datasets.strategy.${chunkStrategy.value}.desc`)
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
    datasets.value = await fetchJson('/api/datasets')
  } catch (e) {
    showToast('Failed to load datasets: ' + e.message)
  }
}

async function fetchSources(datasetId) {
  try {
    sources.value = await fetchJson(`/api/datasets/${datasetId}/sources`)
  } catch (e) {
    showToast('Failed to load sources: ' + e.message)
    sources.value = []
  }
}

async function createDataset() {
  if (!newDatasetName.value.trim()) { showToast('Enter a dataset name.'); return }
  creatingDataset.value = true
  try {
    await fetchJson('/api/datasets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newDatasetName.value.trim() }),
    })
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
    await fetchJson(`/api/datasets/${ds.id}`, { method: 'DELETE' })
    if (selectedDataset.value?.id === ds.id) {
      selectedDataset.value = null
      selectedSource.value = null
      viewingSourceName.value = null
      sources.value = []
    }
    await fetchDatasets()
  } catch (e) {
    showToast('Delete failed: ' + e.message)
  }
}

async function clearSource(source, e) {
  e.stopPropagation()
  if (!confirm(`Delete source "${source.name}" (${source.chunk_count} chunks)?`)) return
  try {
    await fetchJson(`/api/datasets/${selectedDataset.value.id}/sources/${encodeURIComponent(source.name)}`, { method: 'DELETE' })
    if (viewingSourceName.value === source.name) {
      viewingSourceName.value = null
      previewChunks.value = []
      previewCount.value = null
      chunkTotal.value = 0
      chunkTotalPages.value = 0
    }
    await fetchSources(selectedDataset.value.id)
    await fetchDatasets()
    const refreshed = datasets.value.find(d => d.id === selectedDataset.value.id)
    if (refreshed) { selectedDataset.value = refreshed }
    showToast(`Source "${source.name}" deleted.`)
  } catch (e) {
    showToast('Delete failed: ' + e.message)
  }
}

async function deleteChunk(chunk, e) {
  e.stopPropagation()
  try {
    await fetchJson(`/api/datasets/${selectedDataset.value.id}/chunks/${chunk.id}`, { method: 'DELETE' })
    previewChunks.value = previewChunks.value.filter(c => c.id !== chunk.id)
    previewCount.value = previewCount.value ? previewCount.value - 1 : null
    chunkTotal.value = Math.max(0, chunkTotal.value - 1)
    await fetchDatasets()
    await fetchSources(selectedDataset.value.id)
    const refreshed = datasets.value.find(d => d.id === selectedDataset.value.id)
    if (refreshed) { selectedDataset.value = refreshed }
    if (viewingSourceName.value) {
      await loadPreviewBySource(viewingSourceName.value, chunkPage.value)
    }
  } catch (e) {
    showToast('Delete chunk failed: ' + e.message)
  }
}

function selectDataset(ds) {
  selectedDataset.value = ds
  selectedSource.value = ds
  viewingSourceName.value = null
  showUpload.value = false
  showPaste.value = false
  previewChunks.value = []
  sources.value = []
  fetchSources(ds.id)
  loadPreview(ds, 0)
}

function selectSourceItem(source) {
  selectedSource.value = selectedDataset.value
  viewingSourceName.value = source.name
  rawText.value = ''
  rawTextLabel.value = ''
  showUpload.value = false
  showPaste.value = false
  chunkPage.value = 0
  previewChunks.value = []
  loadPreviewBySource(source.name)
}

function startNewSource(preserveText = false) {
  selectedSource.value = selectedDataset.value
  viewingSourceName.value = null
  if (!preserveText) {
    rawText.value = ''
    rawTextLabel.value = ''
  }
  chunkPage.value = 0
  previewChunks.value = []
}

async function loadPreview(ds, page = 0) {
  if (!ds) return
  const gen = ++_loadPreviewGen
  chunkPage.value = page
  try {
    const data = await fetchJson(`/api/datasets/${ds.id}/chunks?page=${page}&page_size=${chunkPageSize.value}`)
    if (gen !== _loadPreviewGen) return  // stale
    if (data.items) {
      // Paginated response
      previewChunks.value = data.items
      chunkTotal.value = data.total
      chunkTotalPages.value = data.total_pages
    } else {
      // Unpaginated fallback
      previewChunks.value = Array.isArray(data) ? data : []
      chunkTotal.value = previewChunks.value.length
      chunkTotalPages.value = 1
    }
  } catch {
    if (gen !== _loadPreviewGen) return
    previewChunks.value = []
    chunkTotal.value = 0
    chunkTotalPages.value = 0
  }
}

async function loadPreviewBySource(sourceName, page = 0) {
  if (!selectedDataset.value) return
  const gen = ++_loadPreviewGen
  chunkPage.value = page
  try {
    const data = await fetchJson(`/api/datasets/${selectedDataset.value.id}/chunks?page=0&page_size=0`)
    if (gen !== _loadPreviewGen) return
    const allItems = Array.isArray(data) ? data : (data.items ?? [])
    const filtered = allItems.filter(c => (c.source_name ?? 'unknown') === sourceName)
    chunkTotal.value = filtered.length
    chunkTotalPages.value = Math.max(1, Math.ceil(filtered.length / chunkPageSize.value))
    const start = page * chunkPageSize.value
    const end = start + chunkPageSize.value
    previewChunks.value = filtered.slice(start, end)
    previewCount.value = null
  } catch {
    if (gen !== _loadPreviewGen) return
    previewChunks.value = []
    chunkTotal.value = 0
    chunkTotalPages.value = 0
  }
}

function goToChunkPage(p) {
  if (p < 0 || p >= chunkTotalPages.value) return
  if (viewingSourceName.value) {
    loadPreviewBySource(viewingSourceName.value, p)
  } else {
    loadPreview(selectedSource.value, p)
  }
}

function chunkPageRange() {
  const pages = []
  const cur = chunkPage.value
  const last = chunkTotalPages.value - 1
  // Always show first page
  pages.push(0)
  // Show pages around current
  for (let i = Math.max(1, cur - 2); i <= Math.min(last - 1, cur + 2); i++) {
    if (!pages.includes(i)) pages.push(i)
  }
  // Always show last page
  if (last > 0) pages.push(last)
  // Insert ellipsis markers
  const result = []
  for (let i = 0; i < pages.length; i++) {
    if (i > 0 && pages[i] - pages[i - 1] > 1) result.push('...')
    result.push(pages[i])
  }
  return result
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
    startNewSource(true)
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
  // Generate unique source name for pasted text
  const base = 'pasted text'
  let name = base
  let i = 1
  while (sources.value.some(s => s.name === name)) {
    name = base + ' ' + (++i)
  }
  rawTextLabel.value = name
  pasteText.value = ''
  showPaste.value = false
  startNewSource(true)
  showToast('Text ready — configure chunking and click Apply.')
}

async function applyChunking() {
  if (!canApply.value) return
  applyingChunks.value = true
  try {
    const data = await fetchJson(`/api/datasets/${selectedSource.value.id}/chunks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: rawText.value,
        strategy: chunkStrategy.value,
        chunk_size: chunkSize.value,
        overlap: chunkOverlap.value,
        source_name: rawTextLabel.value,
      }),
    })
    showToast(`${data.chunk_count} chunks saved from "${data.source_name}".`)
    previewChunks.value = (data.chunks ?? []).map((text, i) => ({ content: text, index: i }))
    rawText.value = ''
    rawTextLabel.value = ''
    await fetchDatasets()
    await fetchSources(selectedSource.value.id)
    const refreshed = datasets.value.find(d => d.id === selectedSource.value.id)
    if (refreshed) { selectedDataset.value = refreshed }
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
        <span class="rl-label">{{ t('datasets.datasets') }}</span>
        <button class="rl-btn-icon" @click="showNewForm = !showNewForm" title="Add dataset">
          <span class="material-symbols-outlined">add</span>
        </button>
      </div>

      <!-- New dataset form -->
      <div v-if="showNewForm" style="padding:8px;border-bottom:1px solid var(--border);flex-shrink:0;">
        <input
          class="rl-input"
          style="margin-bottom:6px;"
          :placeholder="t('datasets.dataset_name_placeholder')"
          v-model="newDatasetName"
          @keydown.enter="createDataset"
        />
        <button class="rl-btn-primary" :disabled="creatingDataset" @click="createDataset" style="font-size:12px;padding:6px 12px;">
          {{ creatingDataset ? t('datasets.creating') : t('datasets.create') }}
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
                  <span style="color:var(--on-surface-variant);"> {{ t('datasets.chunks') }}</span>
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
          {{ t('datasets.no_datasets') }}
        </div>
      </div>
    </div>

    <!-- MIDDLE: Sources (280px) -->
    <div style="width:280px;flex-shrink:0;border-right:1px solid var(--border);background:#0a0a0a;display:flex;flex-direction:column;overflow:hidden;">
      <!-- Header -->
      <div style="padding:12px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;border-bottom:1px solid var(--border);">
        <span class="rl-label">{{ t('datasets.sources') }}</span>
      </div>

      <div v-if="!selectedDataset" style="padding:16px;color:var(--on-surface-variant);font-size:12px;">
        {{ t('datasets.select_dataset_first') }}
      </div>

      <template v-else>
        <!-- Action buttons -->
        <div style="padding:8px;display:flex;gap:8px;flex-shrink:0;border-bottom:1px solid var(--border);">
          <button class="rl-btn-secondary" style="flex:1;font-size:12px;" @click="startNewSource(); showUpload = !showUpload; showPaste = false;">
            <span class="material-symbols-outlined" style="font-size:14px;">upload_file</span>
            {{ t('datasets.upload_file') }}
          </button>
          <button class="rl-btn-secondary" style="flex:1;font-size:12px;" @click="startNewSource(); showPaste = !showPaste; showUpload = false;">
            <span class="material-symbols-outlined" style="font-size:14px;">content_paste</span>
            {{ t('datasets.paste_text') }}
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
            {{ uploadLoading ? t('datasets.uploading') : t('datasets.choose_file') }}
          </button>
        </div>

        <!-- Text paste area -->
        <div v-if="showPaste" style="padding:8px;border-bottom:1px solid var(--border);flex-shrink:0;">
          <textarea
            class="rl-input"
            rows="5"
            :placeholder="t('datasets.paste_placeholder')"
            v-model="pasteText"
            style="margin-bottom:6px;"
          ></textarea>
          <button class="rl-btn-primary" :disabled="pasteLoading" @click="loadPastedText" style="font-size:12px;padding:6px 12px;">
            {{ pasteLoading ? t('datasets.loading') : t('datasets.load') }}
          </button>
        </div>

        <!-- Source list -->
        <div style="flex:1;overflow-y:auto;padding:4px 0;">
          <div
            v-for="source in sources"
            :key="source.name"
            class="rl-dataset-item"
            :class="{ active: viewingSourceName === source.name }"
            @click="selectSourceItem(source)"
            style="margin:4px 8px;padding-right:56px;"
          >
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="material-symbols-outlined" style="font-size:16px;color:var(--on-surface-variant);">description</span>
              <div style="min-width:0;">
                <div style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{{ source.name }}</div>
                <div style="font-size:11px;">
                  <span class="rl-num">{{ source.chunk_count ?? 0 }}</span>
                  <span style="color:var(--on-surface-variant);"> {{ t('datasets.chunks') }}</span>
                </div>
              </div>
            </div>
            <!-- Delete source button -->
            <button
              class="rl-btn-icon"
              style="position:absolute;right:4px;top:50%;transform:translateY(-50%);"
              title="Delete source"
              @click="clearSource(source, $event)"
            >
              <span class="material-symbols-outlined" style="font-size:16px;">delete_sweep</span>
            </button>
          </div>
          <div v-if="!sources.length" style="padding:16px;color:var(--on-surface-variant);font-size:12px;text-align:center;">
            {{ t('datasets.no_sources') }}
          </div>
        </div>
      </template>
    </div>

    <!-- RIGHT: Chunking config + preview -->
    <div style="flex:1;overflow-y:auto;padding:24px;">
      <div v-if="!selectedSource" style="color:var(--on-surface-variant);font-size:13px;">
        {{ t('datasets.select_source_prompt') }}
      </div>

      <template v-else>
        <div style="max-width:800px;">
          <h1 style="font-size:32px;font-weight:700;margin:0 0 24px 0;color:var(--on-surface);">
            {{ viewingSourceName || selectedSource.name }}
          </h1>

          <!-- Viewing source badge -->
          <div v-if="viewingSourceName" style="margin-bottom:16px;font-size:12px;color:var(--primary);">
            <span class="material-symbols-outlined" style="font-size:13px;vertical-align:middle;">visibility</span>
            {{ t('datasets.viewing_source') }}
          </div>

          <!-- Chunking Strategy card -->
          <div v-if="!viewingSourceName" class="rl-card" style="margin-bottom:16px;">
            <div style="font-weight:700;font-size:14px;margin-bottom:16px;display:flex;align-items:center;gap:8px;">
              <span class="material-symbols-outlined" style="color:var(--primary);">cut</span>
              {{ t('datasets.chunking_strategy') }}
            </div>

            <div style="display:flex;flex-direction:column;gap:12px;">
              <div>
                <label class="rl-label" style="display:block;margin-bottom:6px;">{{ t('datasets.strategy') }}</label>
                <select class="rl-select" v-model="chunkStrategy">
                  <option v-for="s in strategyOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
                <p style="margin:4px 0 0;font-size:11px;color:var(--on-surface-variant);">{{ currentStrategyDesc }}</p>
              </div>

              <div v-if="showSizeParams" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div>
                  <label class="rl-label" style="display:block;margin-bottom:6px;">{{ t('datasets.chunk_size') }}</label>
                  <input class="rl-input" type="number" min="64" max="4096" v-model.number="chunkSize" />
                </div>
                <div>
                  <label class="rl-label" style="display:block;margin-bottom:6px;">{{ t('datasets.overlap') }}</label>
                  <input class="rl-input" type="number" min="0" max="512" v-model.number="chunkOverlap" />
                </div>
              </div>

              <!-- Raw text status -->
              <div v-if="rawText" style="font-size:11px;color:var(--primary);display:flex;align-items:center;gap:4px;">
                <span class="material-symbols-outlined" style="font-size:13px;">check_circle</span>
                {{ rawTextLabel }} ready ({{ rawText.length }} chars)
              </div>
              <div v-else-if="selectedSource" style="font-size:11px;color:var(--on-surface-variant);">
                {{ t('datasets.paste_or_upload_prompt') }}
              </div>

              <button class="rl-btn-primary" :disabled="applyingChunks || !canApply" @click="applyChunking" style="width:auto;align-self:flex-start;padding:8px 24px;">
                <span class="material-symbols-outlined" style="font-size:16px;">check</span>
                {{ applyingChunks ? t('datasets.applying') : t('datasets.apply') }}
              </button>
            </div>
          </div>

          <!-- Chunking Preview card -->
          <div class="rl-card">
            <div style="font-weight:700;font-size:14px;margin-bottom:16px;display:flex;align-items:center;gap:8px;">
              <span class="material-symbols-outlined" style="color:var(--primary);">preview</span>
              {{ t('datasets.chunking_preview') }}
              <span v-if="previewLoading" style="font-size:11px;color:var(--on-surface-variant);font-weight:400;">{{ t('datasets.computing') }}</span>
              <span v-else-if="previewCount !== null" style="font-size:11px;color:var(--on-surface-variant);font-weight:400;">
                {{ previewChunks.length }} of {{ previewCount }} {{ t('datasets.chunks') }}
                <span v-if="rawText" style="color:var(--primary);margin-left:4px;">{{ t('datasets.preview_only') }}</span>
              </span>
              <span v-else-if="chunkTotal > 0" style="font-size:11px;color:var(--on-surface-variant);font-weight:400;">
                <span class="rl-num">{{ chunkTotal }}</span> chunks total · page {{ chunkPage + 1 }}/{{ chunkTotalPages }}
              </span>
            </div>

            <div v-if="!previewChunks.length" style="color:var(--on-surface-variant);font-size:12px;">
              <template v-if="viewingSourceName">{{ t('datasets.no_chunks_in_source') }}</template>
              <template v-else>{{ rawText ? t('datasets.computing_preview') : t('datasets.load_text_prompt') }}</template>
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
                  <span style="font-size:10px;color:var(--on-surface-variant);">{{ t('datasets.chars') }}</span>
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

              <!-- Pagination controls -->
              <div v-if="chunkTotalPages > 1 && !rawText" style="display:flex;align-items:center;justify-content:center;gap:4px;padding-top:12px;border-top:1px solid var(--border);">
                <button
                  class="rl-btn-icon"
                  :disabled="chunkPage === 0"
                  @click="goToChunkPage(0)"
                  title="First page"
                >
                  <span class="material-symbols-outlined" style="font-size:16px;">first_page</span>
                </button>
                <button
                  class="rl-btn-icon"
                  :disabled="chunkPage === 0"
                  @click="goToChunkPage(chunkPage - 1)"
                  title="Previous page"
                >
                  <span class="material-symbols-outlined" style="font-size:16px;">chevron_left</span>
                </button>

                <template v-for="p in chunkPageRange()" :key="'cp'+p">
                  <span v-if="p === '...'" style="color:var(--on-surface-variant);font-size:12px;padding:0 4px;">…</span>
                  <button
                    v-else
                    :style="{
                      background: p === chunkPage ? 'var(--highlight)' : 'transparent',
                      color: p === chunkPage ? 'var(--on-highlight)' : 'var(--on-surface-variant)',
                      border: '1px solid ' + (p === chunkPage ? 'var(--highlight)' : 'var(--border)'),
                      borderRadius: '6px', padding: '2px 8px', fontSize: '12px',
                      fontFamily: 'JetBrains Mono, monospace', cursor: 'pointer', minWidth: '28px',
                    }"
                    @click="goToChunkPage(p)"
                  >
                    {{ p + 1 }}
                  </button>
                </template>

                <button
                  class="rl-btn-icon"
                  :disabled="chunkPage >= chunkTotalPages - 1"
                  @click="goToChunkPage(chunkPage + 1)"
                  title="Next page"
                >
                  <span class="material-symbols-outlined" style="font-size:16px;">chevron_right</span>
                </button>
                <button
                  class="rl-btn-icon"
                  :disabled="chunkPage >= chunkTotalPages - 1"
                  @click="goToChunkPage(chunkTotalPages - 1)"
                  title="Last page"
                >
                  <span class="material-symbols-outlined" style="font-size:16px;">last_page</span>
                </button>

                <!-- Page size selector -->
                <div style="display:flex;align-items:center;gap:4px;margin-left:12px;">
                  <span style="font-size:11px;color:var(--on-surface-variant);">{{ t('datasets.per_page') }}</span>
                  <select
                    class="rl-select"
                    :value="chunkPageSize"
                    @change="chunkPageSize = +$event.target.value; goToChunkPage(0)"
                    style="width:56px;padding:2px 4px;font-size:11px;"
                  >
                    <option v-for="s in chunkPageSizeOptions" :key="s" :value="s">{{ s }}</option>
                  </select>
                </div>

                <!-- Jump to page -->
                <div style="display:flex;align-items:center;gap:4px;margin-left:12px;">
                  <span style="font-size:11px;color:var(--on-surface-variant);">{{ t('datasets.go_to') }}</span>
                  <input
                    class="rl-input"
                    type="number"
                    min="1"
                    :max="chunkTotalPages"
                    :value="chunkPage + 1"
                    @keydown.enter="goToChunkPage(+$event.target.value - 1)"
                    style="width:48px;padding:2px 6px;font-size:11px;text-align:center;"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
