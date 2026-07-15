<template>
  <div v-loading="loading" style="max-width:800px">
    <div style="margin-bottom:24px">
      <el-button text @click="$router.push('/reports')" style="font-size:14px;color:#868e96;padding:0">&#8592; 报告列表</el-button>
    </div>
    <h1 style="font-size:24px;font-weight:650;margin:0 0 4px">{{ report?.title }}</h1>
    <p style="color:#868e96;font-size:13px;margin:0 0 32px">{{ report?.dataset_name }} · {{ formatDate(report?.generated_at) }}</p>

    <div v-for="(section, idx) in report?.sections" :key="idx" class="report-section">
      <h3>{{ section.title }}</h3>
      <div v-if="section.type === 'text'" class="section-text">{{ section.content }}</div>
      <div v-else-if="section.type === 'chart' && section.echarts_option">
        <ChartPanel :echarts-option="section.echarts_option" />
        <p class="chart-caption">{{ section.content }}</p>
      </div>
    </div>

    <div style="margin-top:32px;display:flex;gap:8px">
      <el-button @click="exportPdf">导出 PDF</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getReport } from '../api/reports'
import { formatDate } from '../utils/format'
import ChartPanel from '../components/ChartPanel.vue'

const route = useRoute()
const report = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try { report.value = await getReport(route.params.id as string) }
  finally { loading.value = false }
})

function exportPdf() {
  const base = import.meta.env.VITE_API_BASE_URL || '/api'
  window.open(`${base}/reports/${route.params.id}/export`, '_blank')
}
</script>

<style scoped>
.report-section { margin-bottom: 28px; }
.report-section h3 { font-size: 16px; font-weight: 600; margin: 0 0 10px; }
.section-text { font-size: 14px; line-height: 1.8; color: #3c3c3c; }
.chart-caption { font-size: 12px; color: #868e96; text-align: center; margin-top: 8px; }
</style>
