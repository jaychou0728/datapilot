<template>
  <div class="chart-panel">
    <div v-if="!echartsOption" class="chart-placeholder">
      <el-empty description="点击「推荐图表」生成可视化" />
    </div>
    <div v-else class="chart-wrapper">
      <div class="chart-toolbar">
        <el-button size="small" circle @click="doExport" title="导出为图片">
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
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const COLORS = ["#5e6ad2","#91cc75","#fac858","#ee6666","#73c0de","#3ba272","#fc8452","#9a60b4","#ea7ccc"]

const props = defineProps<{ echartsOption?: Record<string, any> | null }>()
const chartRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeHandler: (() => void) | null = null

function render() {
  if (!chartRef.value || !props.echartsOption) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({ color: COLORS }, false)
  chart.setOption(props.echartsOption, true)
}

function doExport() {
  if (!chart) return
  const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
  const a = document.createElement('a')
  a.href = url
  a.download = 'chart.png'
  a.click()
}

function getDataUrl(): string {
  return chart?.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' }) || ''
}

watch(() => props.echartsOption, () => {
  nextTick(render)
}, { deep: true })

onMounted(() => {
  nextTick(render)
  resizeHandler = () => chart?.resize()
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (chart) { chart.dispose(); chart = null }
})

defineExpose({ exportPng: doExport, getDataUrl })
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
