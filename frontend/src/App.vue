<template>
  <div class="shell">
    <template v-if="route.path !== '/login'">
      <header class="topbar">
        <router-link to="/" class="logo">DataPilot</router-link>
        <nav class="nav">
          <router-link to="/" class="nav-item">首页</router-link>
          <router-link to="/upload" class="nav-item">上传</router-link>
          <router-link to="/history" class="nav-item">历史</router-link>
          <router-link to="/reports" class="nav-item">报告</router-link>
          <router-link v-if="auth.user?.role === 'admin'" to="/users" class="nav-item">用户</router-link>
        </nav>
        <div style="flex:1"></div>
        <div v-if="auth.isLoggedIn" style="display:flex;align-items:center;gap:8px;font-size:13px">
          <span style="color:#5c5c5c">{{ auth.user?.username }}</span>
          <el-button size="small" text @click="handleLogout" style="font-size:12px;color:#828282">退出</el-button>
        </div>
      </header>
      <main class="main">
        <router-view />
      </main>
    </template>
    <template v-else>
      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './stores/useAuth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

onMounted(() => { auth.checkAuth() })

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --gray-0: #fbfbfb; --gray-1: #f5f5f5; --gray-2: #ededed; --gray-3: #e5e5e5;
  --gray-5: #b0b0b0; --gray-6: #828282; --gray-7: #5c5c5c; --gray-9: #1a1a1a;
  --accent: #5e6ad2; --accent-hover: #4f5cc7; --accent-light: #f0f1fd;
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --radius-sm: 6px; --radius: 8px; --radius-lg: 10px; --transition: 0.15s ease;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px; line-height: 1.5; color: var(--gray-9); background: var(--gray-0);
  -webkit-font-smoothing: antialiased;
}

.shell { min-height: 100vh; display: flex; flex-direction: column; }

.topbar {
  height: 44px; background: rgba(255,255,255,0.8);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--gray-3);
  display: flex; align-items: center; padding: 0 20px;
  position: sticky; top: 0; z-index: 100;
}
.logo { font-size: 14px; font-weight: 650; color: var(--gray-9); text-decoration: none; letter-spacing: -0.01em; margin-right: 28px; }
.nav { display: flex; gap: 1px; }
.nav-item {
  padding: 5px 14px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 480;
  color: var(--gray-7); text-decoration: none; transition: all var(--transition);
}
.nav-item:hover { color: var(--gray-9); background: var(--gray-2); }
.nav-item.router-link-active { color: var(--gray-9); background: var(--gray-3); font-weight: 520; }

.main { flex: 1; padding: 32px 36px; width: 100%; max-width: 1360px; margin: 0 auto; }

/* Element Plus overrides */
:root {
  --el-color-primary: var(--accent);
  --el-border-radius-base: var(--radius); --el-font-size-base: 14px;
  --el-border-color: var(--gray-3); --el-bg-color-page: transparent;
}
.el-card {
  border-radius: var(--radius-lg) !important; border: 1px solid var(--gray-3) !important;
  box-shadow: var(--shadow-xs) !important; transition: box-shadow var(--transition), transform var(--transition) !important;
}
.el-card:hover { box-shadow: var(--shadow-md) !important; transform: translateY(-1px); }
.el-table {
  --el-table-header-bg-color: var(--gray-1); --el-table-row-hover-bg-color: var(--gray-1);
  font-size: 13px; border-radius: var(--radius-lg);
}
.el-table th.el-table__cell { font-weight: 550; font-size: 11px; color: var(--gray-6); text-transform: uppercase; letter-spacing: 0.04em; padding: 10px 12px; }
.el-button { font-weight: 500; transition: all var(--transition); }
.el-button--primary { box-shadow: var(--shadow-xs); }
.el-button--primary:hover { box-shadow: var(--shadow-sm); }
.el-input__wrapper, .el-textarea__inner { border-radius: var(--radius-sm) !important; box-shadow: none !important; }
.el-input.is-focus .el-input__wrapper { box-shadow: 0 0 0 2px var(--accent-light), 0 0 0 1px var(--accent) !important; }
.el-tabs__item { font-size: 13px; font-weight: 480; color: var(--gray-6); }
.el-tabs__item.is-active { color: var(--gray-9); font-weight: 550; }
.el-tabs__active-bar { background: var(--accent); height: 2px; }
.el-upload-dragger { border: 1px dashed var(--gray-5) !important; border-radius: var(--radius-lg) !important; background: #fff !important; }
.el-upload-dragger:hover { border-color: var(--accent) !important; background: var(--accent-light) !important; }
</style>
