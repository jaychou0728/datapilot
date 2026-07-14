<template>
  <div>
    <h2 style="margin-bottom:20px;font-size:20px;font-weight:650">用户管理</h2>
    <el-table :data="users" stripe>
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">{{ row.role === 'admin' ? '管理员' : '普通用户' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button
            v-if="row.role !== 'admin'"
            size="small"
            type="primary"
            text
            @click="setRole(row.id, 'admin')"
          >设为管理员</el-button>
          <el-button
            v-else
            size="small"
            type="warning"
            text
            @click="setRole(row.id, 'user')"
          >取消管理员</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listUsers, updateRole } from '../api/auth'

const users = ref<any[]>([])

async function load() {
  const data: any = await listUsers()
  users.value = data
}

async function setRole(userId: string, role: string) {
  await updateRole(userId, role)
  load()
}

onMounted(load)
</script>
