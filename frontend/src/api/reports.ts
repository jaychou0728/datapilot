import client from './client'

export function generateReport(datasetId: string) {
  return client.post('/reports/generate', null, { params: { dataset_id: datasetId } })
}

export function getReports() {
  return client.get('/reports')
}

export function getReport(id: string) {
  return client.get(`/reports/${id}`)
}

export function deleteReport(id: string) {
  return client.delete(`/reports/${id}`)
}
