import client from './client'

export function register(username: string, password: string) {
  return client.post('/auth/register', { username, password })
}

export function login(username: string, password: string) {
  return client.post('/auth/login', { username, password })
}

export function getMe() {
  return client.get('/auth/me')
}

export function listUsers() {
  return client.get('/auth/users')
}

export function updateRole(userId: string, role: string) {
  return client.put('/auth/role', { user_id: userId, role })
}
