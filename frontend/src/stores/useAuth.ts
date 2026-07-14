import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getMe } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<any>(null)
  const isLoggedIn = computed(() => !!token.value)

  function setAuth(t: string, u: any) {
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
  }

  async function login(username: string, password: string) {
    const data: any = await apiLogin(username, password)
    setAuth(data.token, data.user)
  }

  async function register(username: string, password: string) {
    const data: any = await apiRegister(username, password)
    setAuth(data.token, data.user)
  }

  async function checkAuth() {
    if (!token.value) return
    try {
      user.value = await getMe()
    } catch {
      token.value = ''
      localStorage.removeItem('token')
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, login, register, checkAuth, logout }
})
