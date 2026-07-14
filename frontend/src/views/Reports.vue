<template>
  <div>
    <h2 style="font-size:18px;font-weight:600;margin:0 0 24px">分析报告</h2>
    <div v-if="reports.length === 0"><el-empty description="还没有报告" /></div>
    <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px">
      <el-card v-for="r in reports" :key="r.id" shadow="never" style="cursor:pointer" @click="$router.push(`/reports/${r.id}`)">
        <div style="font-size:14px;font-weight:550;margin-bottom:6px">{{ r.title }}</div>
        <div style="font-size:12px;color:#828282;display:flex;justify-content:space-between">
          <span>{{ formatDate(r.created_at) }}</span>
          <el-button type="danger" size="small" text @click.stop="handleDelete(r.id)">删除</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getReports, deleteReport } from '../api/reports'
import { formatDate } from '../utils/format'
import { ElMessageBox } from 'element-plus'

const reports = ref<any[]>([])
onMounted(async () => { reports.value = (await getReports()) as unknown as any[] })

async function handleDelete(id: string) {
  await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
  await deleteReport(id)
  reports.value = reports.value.filter(r => r.id !== id)
}
</script>
