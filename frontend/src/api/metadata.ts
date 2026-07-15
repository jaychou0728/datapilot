import client from './client'

export function getMetadata(datasetId: string): Promise<Record<string, { label: string; unit: string; description: string }>> {
  return client.get(`/metadata/${datasetId}`)
}

export function saveMetadata(datasetId: string, columnName: string, label: string, unit: string, description: string) {
  return client.put('/metadata', { dataset_id: datasetId, column_name: columnName, label, unit, description })
}

export function deleteColumnMeta(datasetId: string, columnName: string) {
  return client.delete(`/metadata/${datasetId}/${columnName}`)
}
