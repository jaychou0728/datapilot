import client from './client'

export function getDashboardStats() {
  return client.get('/dashboard/stats')
}
