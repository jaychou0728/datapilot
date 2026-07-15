import { defineStore } from 'pinia'
import { ref } from 'vue'
import { recommendCharts, fetchChartData } from '../api/charts'

export const useChartStore = defineStore('chart', () => {
  const charts = ref<any[]>([])
  const loading = ref(false)

  async function load(datasetId: string, fields?: any[]) {
    loading.value = true
    try {
      const data: any = await recommendCharts(datasetId)
      const rawCharts = data.charts || []

      const filledCharts = await Promise.all(
        rawCharts.map(async (chart: any) => {
          let dq = chart.data_query
          if (!dq && fields) {
            const catFields = fields.filter((f: any) =>
              f.dtype && !['INT', 'FLOAT', 'DOUBLE', 'BIGINT', 'DECIMAL']
                .some(t => f.dtype.toUpperCase().includes(t))
            )
            const numFields = fields.filter((f: any) =>
              f.dtype && ['INT', 'FLOAT', 'DOUBLE', 'BIGINT', 'DECIMAL']
                .some(t => f.dtype.toUpperCase().includes(t))
            )
            const ct = chart.chart_type
            if (ct === 'pie' && catFields.length > 0) {
              dq = { type: 'pie', group_col: catFields[0].name, limit: 20 }
            } else if (ct === 'scatter' && numFields.length >= 2) {
              dq = { type: 'scatter', x_col: numFields[0].name, y_col: numFields[1].name, limit: 2000 }
            } else if ((ct === 'bar' || ct === 'line') && catFields.length > 0 && numFields.length > 0) {
              dq = { type: ct, x_col: catFields[0].name, y_col: numFields[0].name, agg: 'AVG', limit: 50 }
            } else if (ct === 'histogram' && numFields.length > 0) {
              dq = { type: 'histogram', y_col: numFields[0].name, bins: 10 }
            }
          }
          if (!dq) return chart

          try {
            const result: any = await fetchChartData(datasetId, dq)
            const ctype = dq.type || chart.chart_type
            const opt = JSON.parse(JSON.stringify(chart.echarts_option))

            if (ctype === 'scatter') {
              opt.series = [{ type: 'scatter', data: result.data || [], symbolSize: 6 }]
            } else if (ctype === 'bar' || ctype === 'line') {
              const cats = result.categories || []
              const vals = result.values || []
              if (ctype === 'bar' && cats.length > 0) {
                const pairs = cats.map((c: string, i: number) => ({ cat: c, val: vals[i] || 0 }))
                pairs.sort((a: any, b: any) => b.val - a.val)
                opt.xAxis = { ...opt.xAxis, data: pairs.map((p: any) => p.cat), axisLabel: { rotate: cats.length > 8 ? 30 : 0 } }
                opt.series = [{ ...(opt.series?.[0] || {}), type: ctype, data: pairs.map((p: any) => p.val), label: { show: true, position: 'top' } }]
              } else {
                opt.xAxis = { ...opt.xAxis, data: cats, axisLabel: { rotate: cats.length > 8 ? 30 : 0 } }
                opt.series = [{ ...(opt.series?.[0] || {}), type: ctype, data: vals, label: { show: true, position: 'top' } }]
              }
            } else if (ctype === 'pie') {
              const pieData = (result.data || []).map((d: any) => ({ name: String(d.name), value: d.value }))
              opt.series = [{ type: 'pie', data: pieData, label: { show: true }, radius: ['30%', '70%'] }]
            } else if (ctype === 'histogram') {
              opt.xAxis = { ...opt.xAxis, data: result.categories || [] }
              opt.series = [{ type: 'bar', data: result.values || [], label: { show: true, position: 'top' } }]
            }
            return { ...chart, echarts_option: opt, data_query: dq }
          } catch {
            return chart
          }
        })
      )
      charts.value = filledCharts
    } finally {
      loading.value = false
    }
  }

  return { charts, loading, load }
})
