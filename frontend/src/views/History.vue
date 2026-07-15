<template>
  <div>
    <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:24px">
      <h2 style="font-size:18px;font-weight:600">操作历史</h2>
      <el-select v-model="filterType" placeholder="全部类型" size="small" clearable style="width:140px" @change="load">
        <el-option label="上传" value="upload" /><el-option label="清洗" value="clean" />
        <el-option label="查询" value="query" /><el-option label="图表" value="chart" />
        <el-option label="报告" value="report" /><el-option label="删除" value="delete" />
        <el-option label="一键分析" value="agent" />
      </el-select>
    </div>
    <div v-if="loading" style="display:flex;justify-content:center;padding:80px 0">
      <el-icon :size="28" style="animation: spin 1s linear infinite"><Loading /></el-icon>
    </div>
    <div v-else-if="logs.length === 0"><el-empty description="暂无操作记录" /></div>
    <div v-else class="timeline">
      <div v-for="log in logs" :key="log.id" class="timeline-item">
        <div class="tl-dot"></div>
        <div class="tl-content">
          <span class="tl-type">{{ labelFor(log.type) }}</span>
          <span class="tl-detail">{{ log.detail }}</span>
          <span class="tl-time">{{ formatDate(log.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getHistory } from '../api/history'
import { formatDate } from '../utils/format'

const logs = ref<any[]>([])
const filterType = ref('')
const loading = ref(true)
onMounted(() => load())
async function load() {
  loading.value = true
  try { logs.value = (await getHistory(filterType.value || undefined)) as unknown as any[] }
  finally { loading.value = false }
}

function labelFor(t: string): string {
  return { upload: '上传', clean: '清洗', query: '查询', chart: '图表', report: '报告', delete: '删除', agent: '一键分析' }[t] || t
}
</script>

<style scoped>
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>

<style scoped>
.timeline { padding-left: 4px; }
.timeline-item { display: flex; gap: 14px; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.tl-dot { width: 8px; height: 8px; border-radius: 50%; background: #5e6ad2; margin-top: 5px; flex-shrink: 0; }
.tl-content { display: flex; align-items: center; gap: 12px; font-size: 13px; flex-wrap: wrap; }
.tl-type { color: #5e6ad2; font-weight: 550; font-size: 12px; }
.tl-detail { color: #1a1a1a; flex: 1; }
.tl-time { color: #b0b0b0; font-size: 12px; }
</style>
