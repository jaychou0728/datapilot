import client from './client'

export function uploadDataset(file: File) {
  const form = new FormData()
  form.append('file', file)
  return client.post('/datasets/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getDatasets() {
  return client.get('/datasets')
}

export function getDataset(id: string) {
  return client.get(`/datasets/${id}`)
}

export function deleteDataset(id: string) {
  return client.delete(`/datasets/${id}`)
}

export function previewDataset(id: string, page: number = 1, pageSize: number = 50) {
  return client.get(`/datasets/${id}/preview`, { params: { page, page_size: pageSize } })
}

export function getExportUrl(id: string): string {
  const base = import.meta.env.VITE_API_BASE_URL || '/api'
  return `${base}/datasets/${id}/export`
}
