import client from './client'

export function sendMessage(datasetId: string, message: string, history?: { role: string; content: string }[]) {
  return client.post('/chat', {
    dataset_id: datasetId,
    message,
    history: history || null,
  })
}
