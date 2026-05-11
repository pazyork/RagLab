<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, default: null },
  height: { type: String, default: '200px' },
  title: { type: String, default: '' },
})

const chartEl = ref(null)
const modalEl = ref(null)
const showModal = ref(false)
let instance = null
let modalInstance = null

function initChart(el) {
  const inst = echarts.init(el, null, { renderer: 'canvas' })
  if (props.option) inst.setOption(props.option)
  return inst
}

onMounted(() => {
  if (chartEl.value) instance = initChart(chartEl.value)
})

watch(() => props.option, (opt) => {
  if (!opt) return
  if (instance) {
    instance.setOption(opt, true)
  }
  if (modalInstance && showModal.value) {
    modalInstance.setOption(opt, true)
  }
}, { deep: true })

onBeforeUnmount(() => {
  instance?.dispose()
  modalInstance?.dispose()
})

function openModal() {
  showModal.value = true
  nextTick(() => {
    if (!modalEl.value) return
    // Always recreate because v-if destroys the DOM element when closed
    modalInstance?.dispose()
    modalInstance = echarts.init(modalEl.value, null, { renderer: 'canvas' })
    if (props.option) {
      modalInstance.setOption(props.option, true)
    }
    // Allow the browser to paint so the container has real dimensions
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        modalInstance?.resize()
      })
    })
  })
}

function closeModal() {
  showModal.value = false
  modalInstance?.dispose()
  modalInstance = null
}

function download() {
  const src = instance?.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#131313' })
  if (!src) return
  const a = document.createElement('a')
  a.href = src
  a.download = (props.title || 'chart') + '.png'
  a.click()
}

// resize observer
let ro = null
onMounted(() => {
  ro = new ResizeObserver(() => instance?.resize())
  if (chartEl.value) ro.observe(chartEl.value)
})
onBeforeUnmount(() => ro?.disconnect())
</script>

<template>
  <div style="position:relative;">
    <!-- Chart container -->
    <div ref="chartEl" :style="`width:100%;height:${height};`" />

    <!-- Toolbar -->
    <div style="position:absolute;top:4px;right:4px;display:flex;gap:4px;opacity:0;transition:opacity 0.15s;"
         class="echart-toolbar">
      <button @click="download" title="Download PNG"
        style="background:var(--surface-high);border:1px solid var(--border);border-radius:4px;padding:3px 6px;cursor:pointer;color:var(--on-surface-variant);font-size:12px;line-height:1;">
        <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;">download</span>
      </button>
      <button @click="openModal" title="Expand"
        style="background:var(--surface-high);border:1px solid var(--border);border-radius:4px;padding:3px 6px;cursor:pointer;color:var(--on-surface-variant);font-size:12px;line-height:1;">
        <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;">open_in_full</span>
      </button>
    </div>

    <!-- Modal overlay -->
    <Teleport to="body">
      <div v-if="showModal"
        style="position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:9000;display:flex;align-items:center;justify-content:center;"
        @click.self="closeModal">
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;width:80vw;max-width:900px;position:relative;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <span style="font-size:13px;font-weight:700;color:var(--on-surface);">{{ title }}</span>
            <div style="display:flex;gap:8px;">
              <button @click="() => { const src = modalInstance?.getDataURL({ type:'png', pixelRatio:2, backgroundColor:'#131313' }); if(src){const a=document.createElement('a');a.href=src;a.download=(title||'chart')+'.png';a.click()} }"
                style="background:var(--surface-high);border:1px solid var(--border);border-radius:4px;padding:4px 10px;cursor:pointer;color:var(--on-surface-variant);font-size:12px;">
                <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;">download</span>
              </button>
              <button @click="closeModal"
                style="background:var(--surface-high);border:1px solid var(--border);border-radius:4px;padding:4px 10px;cursor:pointer;color:var(--on-surface-variant);font-size:12px;">
                <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle;">close</span>
              </button>
            </div>
          </div>
          <div ref="modalEl" style="width:100%;height:60vh;" />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
div:hover .echart-toolbar { opacity: 1 !important; }
</style>
