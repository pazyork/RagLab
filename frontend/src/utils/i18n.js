import { inject } from 'vue'

export function useI18n() {
  const t = inject('t')
  return { t }
}
