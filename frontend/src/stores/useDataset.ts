import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDataset } from '../api/datasets'

export interface ColumnInfo {
  name: string
  dtype: string
  null_count: number
  sample_values: any[]
}

export interface DatasetInfo {
  id: string
  name: string
  rows: number
  columns: number
  fields: ColumnInfo[]
  created_at: string
}

export const useDatasetStore = defineStore('dataset', () => {
  const current = ref<DatasetInfo | null>(null)
  const loading = ref(false)

  async function load(id: string) {
    loading.value = true
    try {
      current.value = (await getDataset(id)) as unknown as DatasetInfo
    } finally {
      loading.value = false
    }
  }

  function clear() {
    current.value = null
  }

  return { current, loading, load, clear }
})
