import client from './client'

export function getHistory(type?: string) {
  return client.get('/history', { params: type ? { type } : {} })
}
