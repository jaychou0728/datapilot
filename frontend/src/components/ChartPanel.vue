<template>
  <div class="chart-panel">
    <div v-if="!echartsOption" class="chart-placeholder">
      <el-empty description="点击「推荐图表」生成可视化" />
    </div>
    <div v-else class="chart-wrapper">
      <div class="chart-toolbar">
        <el-button size="small" circle @click="exportPng" title="导出为图片">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
            <path d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2v9.67z"/>
          </svg>
        </el-button>
      </div>
      <div ref="chartRef" class="chart-container"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ echartsOption?: Record<string, any> | null }>()
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function renderChart() {
  if (!chartRef.value || !props.echartsOption) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  chartInstance.setOption(props.echartsOption, true)
}

function exportPng() {
  const url = getDataUrl()
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.download = 'chart.png'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

watch(() => props.echartsOption, async (opt) => {
  if (opt) {
    await nextTick()
    renderChart()
  }
}, { deep: true })

onMounted(() => {
  if (props.echartsOption) renderChart()
  window.addEventListener('resize', () => chartInstance?.resize())
})

function getDataUrl(): string {
  if (!chartInstance) return ''
  return chartInstance.getDataURL({
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#fff',
  })
}

defineExpose({ exportPng, getDataUrl })
</script>

<style scoped>
.chart-panel { width: 100%; min-height: 350px; position: relative; }
.chart-wrapper { position: relative; }
.chart-toolbar {
  position: absolute; top: -4px; right: 0; z-index: 10;
  opacity: 0; transition: opacity 0.2s;
}
.chart-wrapper:hover .chart-toolbar { opacity: 1; }
.chart-container { width: 100%; height: 350px; }
.chart-placeholder { display: flex; align-items: center; justify-content: center; min-height: 350px; }
</style>
