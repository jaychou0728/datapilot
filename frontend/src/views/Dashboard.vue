<template>
  <div>
    <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:28px">
      <h2 style="font-size:18px;font-weight:600;letter-spacing:-0.01em">全部数据集</h2>
      <el-button type="primary" size="small" @click="$router.push('/upload')">上传数据</el-button>
    </div>

    <div v-if="stats" class="stats-row">
      <div class="stat-card"><div class="stat-value">{{ datasets.length }}</div><div class="stat-label">数据集</div></div>
      <div class="stat-card"><div class="stat-value">{{ stats.reports_count }}</div><div class="stat-label">报告</div></div>
      <div class="stat-card"><div class="stat-value">{{ stats.operations_count }}</div><div class="stat-label">操作记录</div></div>
    </div>
    <div v-if="stats?.recent_activities?.length" class="recent-section">
      <h3 style="font-size:14px;font-weight:600;margin:0 0 12px">最近活动</h3>
      <div v-for="act in stats.recent_activities" :key="act.id" class="activity-item">
        <span class="act-icon">{{ iconFor(act.type) }}</span>
        <span>{{ act.detail }}</span>
        <span class="act-time">{{ formatDate(act.time) }}</span>
      </div>
    </div>

    <div v-if="datasets.length === 0" style="margin-top:100px">
      <el-empty description="还没有数据集">
        <el-button type="primary" @click="$router.push('/upload')">上传第一份数据</el-button>
      </el-empty>
    </div>

    <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px">
      <el-card
        v-for="ds in datasets" :key="ds.id"
        shadow="never"
        style="cursor:pointer;padding:2px"
        @click="$router.push(`/datasets/${ds.id}`)"
      >
        <div style="display:flex;align-items:flex-start;justify-content:space-between">
          <div style="flex:1;min-width:0">
            <div style="font-size:14px;font-weight:550;color:#1a1a1a;margin-bottom:6px;
                        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;letter-spacing:-0.005em">
              {{ ds.name }}
            </div>
            <div style="display:flex;gap:14px;font-size:12px;color:#828282;margin-bottom:4px">
              <span>{{ ds.rows?.toLocaleString() }} 行</span>
              <span>{{ ds.columns }} 列</span>
            </div>
            <div style="font-size:11px;color:#b0b0b0">
              {{ formatDate(ds.created_at) }}
            </div>
          </div>
          <el-button
            type="danger" size="small" text
            style="flex-shrink:0;font-size:12px"
            @click.stop="handleDelete(ds.id)"
          >删除</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDatasets, deleteDataset } from '../api/datasets'
import { getDashboardStats } from '../api/dashboard'
import { formatDate } from '../utils/format'
import { ElMessageBox } from 'element-plus'

const datasets = ref<any[]>([])
const stats = ref<any>(null)

onMounted(async () => {
  datasets.value = (await getDatasets()) as unknown as any[]
  try { stats.value = await getDashboardStats() } catch { /* no-op */ }
})

function iconFor(type: string): string {
  return { upload: '+', clean: String.fromCodePoint(0x2714), query: String.fromCodePoint(0x25B6), chart: String.fromCodePoint(0x25A0), report: String.fromCodePoint(0x25A3) }[type] || String.fromCodePoint(0x25CF)
}

async function handleDelete(id: string) {
  await ElMessageBox.confirm('确定删除？', '确认删除', { type: 'warning' })
  await deleteDataset(id)
  datasets.value = datasets.value.filter(d => d.id !== id)
}
</script>

<style scoped>
.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 32px; }
.stat-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 10px; padding: 18px 20px; }
.stat-value { font-size: 28px; font-weight: 650; letter-spacing: -0.02em; }
.stat-label { font-size: 12px; color: #828282; margin-top: 2px; }
.recent-section { margin-bottom: 32px; }
.activity-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; font-size: 13px; color: #5c5c5c; border-bottom: 1px solid #f0f0f0; }
.act-icon { width: 20px; text-align: center; font-size: 11px; flex-shrink: 0; color: #5e6ad2; }
.act-time { margin-left: auto; font-size: 11px; color: #b0b0b0; flex-shrink: 0; }
</style>

