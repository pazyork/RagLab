<script setup>
import { ref, computed, shallowRef } from 'vue'
import PlaygroundPage from './pages/PlaygroundPage.vue'
import DatasetsPage from './pages/DatasetsPage.vue'
import SettingsPage from './pages/SettingsPage.vue'
import AnimatedBg from './components/AnimatedBg.vue'

const page = ref('playground')
const view = ref('query_vs_chunks')
const lang = ref('EN')

const pages = {
  playground: PlaygroundPage,
  datasets: DatasetsPage,
  settings: SettingsPage,
}

const currentPage = computed(() => pages[page.value])

function toggleLang() {
  lang.value = lang.value === 'EN' ? '中文' : 'EN'
}
</script>

<template>
  <AnimatedBg />
  <div id="app-shell" style="position:relative;z-index:1;">
    <!-- Header -->
    <header id="app-header">
      <span style="font-size:16px;font-weight:700;color:#ffffff;letter-spacing:0.06em;flex-shrink:0;font-family:'Inter',sans-serif;">RAGLab</span>

      <!-- View toggle — only on playground -->
      <div style="flex:1;display:flex;justify-content:center;">
        <div v-if="page === 'playground'" class="rl-view-toggle">
          <button
            class="rl-view-btn"
            :class="{ active: view === 'query_vs_chunks' }"
            @click="view = 'query_vs_chunks'"
          >
            <span class="material-symbols-outlined" style="font-size:16px;">search</span>
            Query vs Chunks
          </button>
          <button
            class="rl-view-btn"
            :class="{ active: view === 'chunk_vs_chunk' }"
            @click="view = 'chunk_vs_chunk'"
          >
            <span class="material-symbols-outlined" style="font-size:16px;">grid_view</span>
            Chunk vs Chunk
          </button>
        </div>
      </div>

      <!-- Language toggle -->
      <button class="rl-btn-secondary" style="width:auto;padding:4px 12px;font-size:12px;" @click="toggleLang">
        {{ lang }}
      </button>
    </header>

    <div id="app-body">
      <!-- Sidebar -->
      <nav id="app-sidebar">
        <button
          class="rl-nav-btn"
          :class="{ active: page === 'playground' }"
          @click="page = 'playground'"
          title="Playground"
        >
          <span class="material-symbols-outlined">science</span>
        </button>
        <button
          class="rl-nav-btn"
          :class="{ active: page === 'datasets' }"
          @click="page = 'datasets'"
          title="Datasets"
        >
          <span class="material-symbols-outlined">database</span>
        </button>

        <!-- Settings pinned to bottom -->
        <div style="flex:1;"></div>
        <button
          class="rl-nav-btn"
          :class="{ active: page === 'settings' }"
          @click="page = 'settings'"
          title="Settings"
        >
          <span class="material-symbols-outlined">settings</span>
        </button>
      </nav>

      <!-- Main content -->
      <main id="app-main">
        <component :is="currentPage" :view="view" />
      </main>
    </div>
  </div>
</template>

<style scoped>
#app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
#app-header {
  height: 48px;
  background: var(--surface-low);
  border-bottom: 1px solid var(--outline-variant);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 16px;
  flex-shrink: 0;
}
#app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}
#app-sidebar {
  width: 64px;
  background: var(--surface-low);
  border-right: 1px solid var(--outline-variant);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  flex-shrink: 0;
  gap: 8px;
}
#app-main {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}
</style>
