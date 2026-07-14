import client from './client'

export function getLineage(datasetId: string) {
  return client.get(`/lineage/${datasetId}`)
}

export function getLineageGraph(datasetId: string) {
  return client.get(`/lineage/${datasetId}/graph`)
}
