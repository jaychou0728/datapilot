<template>
  <div class="login-page">
    <div class="login-card">
      <h1>DataPilot</h1>
      <p class="subtitle">AI 智能数据分析平台</p>
      <el-tabs v-model="mode" class="login-tabs">
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>
      <el-form @submit.prevent="handleSubmit">
        <el-form-item>
          <el-input v-model="username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="密码" size="large" @keyup.enter="handleSubmit" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" style="width:100%" @click="handleSubmit" :loading="loading">
            {{ mode === 'login' ? '登录' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>
      <p class="error" v-if="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/useAuth'

const router = useRouter()
const auth = useAuthStore()
const mode = ref('login')
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  if (!username.value || !password.value) { error.value = '请填写用户名和密码'; return }
  loading.value = true; error.value = ''
  try {
    if (mode.value === 'login') await auth.login(username.value, password.value)
    else await auth.register(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally { loading.value = false }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f5f5f5; }
.login-card { width: 360px; padding: 40px; background: #fff; border-radius: 12px; box-shadow: 0 2px 16px rgba(0,0,0,0.06); }
.login-card h1 { text-align: center; font-size: 22px; margin: 0 0 4px; }
.subtitle { text-align: center; color: #828282; font-size: 13px; margin: 0 0 24px; }
.login-tabs { margin-bottom: 8px; }
.login-tabs :deep(.el-tabs__header) { margin-bottom: 16px; }
.login-tabs :deep(.el-tabs__nav) { width: 100%; display: flex; }
.login-tabs :deep(.el-tabs__item) { flex: 1; text-align: center; }
.error { color: #e5484d; font-size: 13px; text-align: center; margin: 8px 0 0; }
</style>
