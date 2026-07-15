import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { aiAnalyze, aiExecute, undoCleaning } from '../api/cleaning'
import { bus } from './eventBus'

export const useCleaningStore = defineStore('cleaning', () => {
  const suggestions = ref<any[]>([])
  const selectedFixIndexes = ref<number[]>([])
  const profileSummary = ref('')
  const totalRows = ref(0)
  const analyzing = ref(false)
  const cleaning = ref(false)
  const cleanResult = ref<any>(null)
  const canUndo = ref(false)

  const approvedOperations = computed(() =>
    selectedFixIndexes.value
      .map(i => suggestions.value[i])
      .filter((s: any) => s && s.operation)
  )

  async function analyze(datasetId: string) {
    analyzing.value = true
    suggestions.value = []
    selectedFixIndexes.value = []
    try {
      const data: any = await aiAnalyze(datasetId)
      suggestions.value = data.suggestions || []
      profileSummary.value = data.profile_summary || ''
      totalRows.value = data.total_rows || 0
      selectedFixIndexes.value = suggestions.value.map((_: any, i: number) => i)
    } finally {
      analyzing.value = false
    }
  }

  async function execute(datasetId: string) {
    if (approvedOperations.value.length === 0) return
    cleaning.value = true
    try {
      const ops = approvedOperations.value.map((s: any) => ({
        operation: s.operation,
        params: s.params || {},
      }))
      const data: any = await aiExecute(datasetId, ops)
      cleanResult.value = data
      canUndo.value = data.can_undo
      bus.emit('dataset:cleaned')
    } finally {
      cleaning.value = false
    }
  }

  async function undo(datasetId: string) {
    await undoCleaning(datasetId)
    cleanResult.value = null
    canUndo.value = false
    bus.emit('dataset:undo')
  }

  return {
    suggestions, selectedFixIndexes, profileSummary, totalRows,
    analyzing, cleaning, cleanResult, canUndo,
    approvedOperations, analyze, execute, undo,
  }
})
