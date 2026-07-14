import client from './client'

export function runAgent(datasetId: string) {
  return client.post('/agent/run', { dataset_id: datasetId })
}
