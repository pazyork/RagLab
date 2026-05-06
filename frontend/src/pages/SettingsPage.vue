<script setup>
import { ref, onMounted } from 'vue'

// ── Toast ─────────────────────────────────────────────────────────────────────
const toast = ref('')
function showToast(msg, duration = 3500) {
  toast.value = msg
  setTimeout(() => { toast.value = '' }, duration)
}

// ── Providers ─────────────────────────────────────────────────────────────────
const providers = ref([])
const showAddProvider = ref(false)
const newProvider = ref({ name: '', api_key: '', base_url: '' })
const savingProvider = ref(false)

async function fetchProviders() {
  try {
    const res = await fetch('/api/providers')
    if (!res.ok) throw new Error(await res.text())
    providers.value = await res.json()
  } catch (e) {
    showToast('Failed to load providers: ' + e.message)
  }
}

async function saveProvider() {
  if (!newProvider.value.name.trim()) { showToast('Provider name is required.'); return }
  savingProvider.value = true
  try {
    const res = await fetch('/api/providers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newProvider.value),
    })
    if (!res.ok) throw new Error(await res.text())
    newProvider.value = { name: '', api_key: '', base_url: '' }
    showAddProvider.value = false
    await fetchProviders()
    showToast('Provider saved.')
  } catch (e) {
    showToast('Save failed: ' + e.message)
  } finally {
    savingProvider.value = false
  }
}

async function deleteProvider(name) {
  if (!confirm(`Delete provider "${name}"?`)) return
  try {
    const res = await fetch(`/api/providers/${encodeURIComponent(name)}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await res.text())
    await fetchProviders()
    showToast('Provider deleted.')
  } catch (e) {
    showToast('Delete failed: ' + e.message)
  }
}

function maskKey(key) {
  if (!key) return '—'
  if (key.length <= 8) return '••••••••'
  return key.slice(0, 4) + '••••••••' + key.slice(-4)
}

// ── Models ────────────────────────────────────────────────────────────────────
const models = ref([])
const showAddModel = ref(false)
const newModel = ref({ provider_name: '', model_name: '' })
const savingModel = ref(false)
const testingModel = ref({})   // { [id]: 'testing' | 'ok' | 'fail' }

async function fetchModels() {
  try {
    const res = await fetch('/api/models')
    if (!res.ok) throw new Error(await res.text())
    models.value = await res.json()
  } catch (e) {
    showToast('Failed to load models: ' + e.message)
  }
}

async function saveModel() {
  if (!newModel.value.model_name.trim()) { showToast('Model name is required.'); return }
  savingModel.value = true
  try {
    const res = await fetch('/api/models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newModel.value),
    })
    if (!res.ok) throw new Error(await res.text())
    newModel.value = { provider_name: '', model_name: '' }
    showAddModel.value = false
    await fetchModels()
    showToast('Model saved.')
  } catch (e) {
    showToast('Save failed: ' + e.message)
  } finally {
    savingModel.value = false
  }
}

async function testModel(id) {
  testingModel.value[id] = 'testing'
  try {
    const res = await fetch(`/api/models/${encodeURIComponent(id)}/test`, { method: 'POST' })
    if (!res.ok) throw new Error(await res.text())
    testingModel.value[id] = 'ok'
    showToast('Model test passed.')
  } catch (e) {
    testingModel.value[id] = 'fail'
    showToast('Model test failed: ' + e.message)
  }
}

async function deleteModel(id) {
  if (!confirm(`Delete model "${id}"?`)) return
  try {
    const res = await fetch(`/api/models/${encodeURIComponent(id)}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await res.text())
    await fetchModels()
    showToast('Model deleted.')
  } catch (e) {
    showToast('Delete failed: ' + e.message)
  }
}

// ── Default Parameters ────────────────────────────────────────────────────────
const config = ref({ chunk_size: 512, overlap: 64, top_k: 5, default_metric: 'cosine' })
const savingConfig = ref(false)

async function fetchConfig() {
  try {
    const res = await fetch('/api/config')
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    config.value = { ...config.value, ...data }
  } catch (e) {
    showToast('Failed to load config: ' + e.message)
  }
}

async function saveConfig() {
  savingConfig.value = true
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config.value),
    })
    if (!res.ok) throw new Error(await res.text())
    showToast('Configuration saved.')
  } catch (e) {
    showToast('Save failed: ' + e.message)
  } finally {
    savingConfig.value = false
  }
}

onMounted(() => {
  fetchProviders()
  fetchModels()
  fetchConfig()
})
</script>

<template>
  <!-- Toast -->
  <div
    v-if="toast"
    style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--surface-high);color:var(--on-surface);padding:10px 20px;border-radius:8px;border:1px solid var(--border);z-index:9999;font-size:13px;pointer-events:none;"
  >
    {{ toast }}
  </div>

  <div style="height:calc(100vh - 48px);overflow-y:auto;padding:32px;">
    <div style="max-width:900px;margin:0 auto;display:flex;flex-direction:column;gap:32px;">

      <!-- ── 1. Provider Management ─────────────────────────────────────── -->
      <div class="rl-card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="material-symbols-outlined" style="color:var(--primary);">key</span>
            <span style="font-size:16px;font-weight:700;">Provider Management</span>
          </div>
          <button class="rl-btn-secondary" @click="showAddProvider = !showAddProvider">
            <span class="material-symbols-outlined" style="font-size:14px;">add</span>
            Add Provider
          </button>
        </div>

        <!-- Add form -->
        <div v-if="showAddProvider" style="background:var(--surface-low);border-radius:8px;padding:16px;margin-bottom:16px;display:flex;flex-direction:column;gap:10px;">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div>
              <label class="rl-label" style="display:block;margin-bottom:4px;">Name</label>
              <input class="rl-input" placeholder="e.g. openai" v-model="newProvider.name" />
            </div>
            <div>
              <label class="rl-label" style="display:block;margin-bottom:4px;">Base URL</label>
              <input class="rl-input" placeholder="https://api.openai.com/v1" v-model="newProvider.base_url" />
            </div>
          </div>
          <div>
            <label class="rl-label" style="display:block;margin-bottom:4px;">API Key</label>
            <input class="rl-input" type="password" placeholder="sk-…" v-model="newProvider.api_key" />
          </div>
          <div style="display:flex;gap:8px;">
            <button class="rl-btn-primary" :disabled="savingProvider" @click="saveProvider" style="width:auto;padding:8px 24px;">
              {{ savingProvider ? 'Saving…' : 'Save' }}
            </button>
            <button class="rl-btn-secondary" @click="showAddProvider = false">Cancel</button>
          </div>
        </div>

        <!-- Table -->
        <table class="rl-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Base URL</th>
              <th>API Key</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in providers" :key="p.name">
              <td>{{ p.name }}</td>
              <td>{{ p.base_url || '—' }}</td>
              <td>{{ maskKey(p.api_key) }}</td>
              <td>
                <button class="rl-btn-icon" @click="deleteProvider(p.name)" title="Delete">
                  <span class="material-symbols-outlined" style="font-size:16px;">delete</span>
                </button>
              </td>
            </tr>
            <tr v-if="!providers.length">
              <td colspan="4" style="text-align:center;color:var(--on-surface-variant);">No providers configured.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ── 2. Model Management ────────────────────────────────────────── -->
      <div class="rl-card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="material-symbols-outlined" style="color:var(--primary);">model_training</span>
            <span style="font-size:16px;font-weight:700;">Model Management</span>
          </div>
          <button class="rl-btn-secondary" @click="showAddModel = !showAddModel">
            <span class="material-symbols-outlined" style="font-size:14px;">add</span>
            Add Model
          </button>
        </div>

        <!-- Add form -->
        <div v-if="showAddModel" style="background:var(--surface-low);border-radius:8px;padding:16px;margin-bottom:16px;display:flex;flex-direction:column;gap:10px;">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div>
              <label class="rl-label" style="display:block;margin-bottom:4px;">Provider</label>
              <select class="rl-select" v-model="newModel.provider_name">
                <option value="">Select provider…</option>
                <option v-for="p in providers" :key="p.name" :value="p.name">{{ p.name }}</option>
              </select>
            </div>
            <div>
              <label class="rl-label" style="display:block;margin-bottom:4px;">Model Name</label>
              <input class="rl-input" placeholder="e.g. text-embedding-3-small" v-model="newModel.model_name" />
            </div>
          </div>
          <div style="display:flex;gap:8px;">
            <button class="rl-btn-primary" :disabled="savingModel" @click="saveModel" style="width:auto;padding:8px 24px;">
              {{ savingModel ? 'Saving…' : 'Save' }}
            </button>
            <button class="rl-btn-secondary" @click="showAddModel = false">Cancel</button>
          </div>
        </div>

        <!-- Table -->
        <table class="rl-table">
          <thead>
            <tr>
              <th>Model Name</th>
              <th>Provider</th>
              <th>Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in models" :key="m.id">
              <td>{{ m.model_name }}</td>
              <td>{{ m.provider_name }}</td>
              <td>{{ m.type ?? 'embedding' }}</td>
              <td style="display:flex;gap:4px;align-items:center;">
                <button
                  class="rl-btn-secondary"
                  style="font-size:11px;padding:4px 8px;"
                  :disabled="testingModel[m.id] === 'testing'"
                  @click="testModel(m.id)"
                >
                  <span
                    class="material-symbols-outlined"
                    style="font-size:13px;"
                    :style="{ color: testingModel[m.id] === 'ok' ? 'var(--secondary)' : testingModel[m.id] === 'fail' ? 'var(--error)' : '' }"
                  >
                    {{ testingModel[m.id] === 'ok' ? 'check_circle' : testingModel[m.id] === 'fail' ? 'error' : 'play_arrow' }}
                  </span>
                  {{ testingModel[m.id] === 'testing' ? 'Testing…' : 'Test' }}
                </button>
                <button class="rl-btn-icon" @click="deleteModel(m.id)" title="Delete">
                  <span class="material-symbols-outlined" style="font-size:16px;">delete</span>
                </button>
              </td>
            </tr>
            <tr v-if="!models.length">
              <td colspan="4" style="text-align:center;color:var(--on-surface-variant);">No models configured.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ── 3. Default Parameters ──────────────────────────────────────── -->
      <div class="rl-card">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
          <span class="material-symbols-outlined" style="color:var(--primary);">sliders</span>
          <span style="font-size:16px;font-weight:700;">Default Parameters</span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
          <div>
            <label class="rl-label" style="display:block;margin-bottom:6px;">Chunk Size</label>
            <input class="rl-input" type="number" min="64" max="4096" v-model.number="config.chunk_size" />
          </div>
          <div>
            <label class="rl-label" style="display:block;margin-bottom:6px;">Overlap</label>
            <input class="rl-input" type="number" min="0" max="512" v-model.number="config.overlap" />
          </div>
          <div>
            <label class="rl-label" style="display:block;margin-bottom:6px;">Top-K</label>
            <input class="rl-input" type="number" min="1" max="100" v-model.number="config.top_k" />
          </div>
          <div>
            <label class="rl-label" style="display:block;margin-bottom:6px;">Default Metric</label>
            <select class="rl-select" v-model="config.default_metric">
              <option value="cosine">Cosine</option>
              <option value="euclidean">Euclidean</option>
              <option value="dot">Dot Product</option>
              <option value="manhattan">Manhattan</option>
            </select>
          </div>
        </div>

        <button class="rl-btn-primary" :disabled="savingConfig" @click="saveConfig" style="width:auto;padding:8px 24px;">
          <span class="material-symbols-outlined" style="font-size:16px;">save</span>
          {{ savingConfig ? 'Saving…' : 'Save Changes' }}
        </button>
      </div>

    </div>
  </div>
</template>
