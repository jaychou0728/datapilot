import client from './client'

export function recommendCharts(datasetId: string, hint?: string) {
  return client.post('/charts/recommend', {
    dataset_id: datasetId,
    hint: hint || null,
  })
}

export function fetchChartData(datasetId: string, query: Record<string, any>) {
  return client.post('/charts/data', {
    dataset_id: datasetId,
    query,
  })
}
