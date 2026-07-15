import { ref, watch, onMounted, onUnmounted, nextTick, type Ref } from 'vue'
import * as echarts from 'echarts'

const DEFAULT_COLORS = [
  '#5e6ad2', '#91cc75', '#fac858', '#ee6666',
  '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc',
]

export function useChart(option: Ref<Record<string, any> | null | undefined>) {
  const chartRef = ref<HTMLElement | null>(null)
  let instance: echarts.ECharts | null = null

  function render() {
    if (!chartRef.value || !option.value) return
    if (!instance) {
      instance = echarts.init(chartRef.value)
    }
    instance.setOption({ color: DEFAULT_COLORS }, false)
    instance.setOption(option.value, true)
  }

  function exportPng() {
    if (!instance) return
    const link = document.createElement('a')
    link.href = instance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
    link.download = 'chart.png'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  function getDataUrl(): string {
    return instance?.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' }) || ''
  }

  watch(option, async () => {
    await nextTick()
    render()
  }, { deep: true })

  onMounted(() => {
    if (option.value) render()
    const onResize = () => instance?.resize()
    window.addEventListener('resize', onResize)
    onUnmounted(() => window.removeEventListener('resize', onResize))
  })

  onUnmounted(() => {
    if (instance) {
      instance.dispose()
      instance = null
    }
  })

  return { chartRef, exportPng, getDataUrl, render }
}
