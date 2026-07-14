import client from './client'

export function aiAnalyze(datasetId: string) {
  return client.post(`/cleaning/${datasetId}/analyze`)
}

export function aiExecute(datasetId: string, operations: Record<string, any>[]) {
  return client.post(`/cleaning/${datasetId}/ai-execute`, { operations })
}

export function executeCleaning(datasetId: string, actions: string[], fillStrategy: string = 'mean') {
  return client.post(`/cleaning/${datasetId}/execute`, {
    dataset_id: datasetId,
    actions,
    fill_strategy: fillStrategy,
  })
}

export function undoCleaning(datasetId: string) {
  return client.post(`/cleaning/${datasetId}/undo`)
}
