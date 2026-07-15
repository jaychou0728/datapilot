import client from './client'

export function listVersions(datasetId: string) {
  return client.get(`/versions/${datasetId}`)
}

export function rollbackVersion(datasetId: string, versionId: string) {
  return client.post('/versions/rollback', { dataset_id: datasetId, version_id: versionId })
}

export function createSnapshot(datasetId: string) {
  return client.post(`/versions/snapshot/${datasetId}`)
}
