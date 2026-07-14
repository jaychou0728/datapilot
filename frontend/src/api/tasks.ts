import client from './client'

export function getTask(id: string) {
  return client.get(`/tasks/${id}`)
}
