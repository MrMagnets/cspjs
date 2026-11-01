import { defineStore } from 'pinia'
import { authApi } from '@/api'
import { TOKEN_KEY, USER_KEY } from '@/api/client'

function readUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: readUser(),
    ready: false,
  }),

  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    isAdmin: (state) => state.user?.role === 'admin',
    username: (state) => state.user?.username || '',
  },

  actions: {
    setSession(payload) {
      this.token = payload.access_token
      this.user = payload.user
      localStorage.setItem(TOKEN_KEY, payload.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(payload.user))
    },

    async login(username, password) {
      const payload = await authApi.login({ username, password })
      this.setSession(payload)
      this.ready = true
      return payload.user
    },

    async register(username, password) {
      const payload = await authApi.register({ username, password })
      this.setSession(payload)
      this.ready = true
      return payload.user
    },

    async fetchMe() {
      if (!this.token) {
        this.ready = true
        return null
      }
      try {
        const user = await authApi.me()
        this.user = user
        localStorage.setItem(USER_KEY, JSON.stringify(user))
        return user
      } catch (err) {
        if (err?.status === 401) this.logout()
        return null
      } finally {
        this.ready = true
      }
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})
