import client from './client'

export function executeQuery(datasetId: string, sql?: string, naturalLanguage?: string) {
  return client.post('/query/execute', {
    dataset_id: datasetId,
    sql: sql || null,
    natural_language: naturalLanguage || null,
  })
}
