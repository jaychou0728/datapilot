<template>
  <div class="detail-page" v-loading="store.loading">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <div style="display:flex;align-items:center;gap:10px">
        <el-button text @click="$router.push('/')" style="font-size:16px;padding:0;color:#868e96">&#8592;</el-button>
        <div>
          <h2 style="margin:0;font-size:20px;font-weight:650">{{ store.current?.name }}</h2>
          <div style="font-size:13px;color:#868e96;margin-top:2px">
            {{ store.current?.rows?.toLocaleString() }} 行 · {{ store.current?.columns }} 列
          </div>
        </div>
      </div>
      <div style="display:flex;gap:8px">
        <el-button type="success" size="small" @click="handleAgentRun" :loading="agentRunning" style="background:linear-gradient(135deg,#5e6ad2,#7c3aed);border:none;color:#fff">一键分析</el-button>
        <el-button type="primary" size="small" @click="handleGenerateReport" :loading="generatingReport">生成报告</el-button>
        <el-button size="small" @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>

    <div class="detail-body">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- Tab 1: Data Preview -->
        <el-tab-pane label="数据预览" name="preview">
          <DataTable
            :columns="previewColumns"
            :rows="previewRows"
            :total="previewTotal"
            :page="previewPage"
            :pageSize="50"
            :loading="previewLoading"
            @page-change="loadPreview"
          />
        </el-tab-pane>

        <!-- Tab 2: Data Cleaning -->
        <el-tab-pane label="数据清洗" name="cleaning">
          <div class="cleaning-panel">
            <el-button type="primary" @click="aiAnalyzeData" :loading="analyzing">
              AI 分析数据质量
            </el-button>
            <span v-if="profileSummary" style="margin-left:8px;color:#909399">{{ profileSummary }}</span>

            <div v-if="suggestions.length > 0" style="margin-top: 16px">
              <h4>AI 发现 {{ suggestions.length }} 个问题：</h4>
              <el-checkbox-group v-model="selectedFixIndexes">
                <div v-for="(s, idx) in suggestions" :key="idx" class="suggestion-card">
                  <el-checkbox :value="idx">
                    <div class="suggestion-body">
                      <div class="suggestion-header">
                        <el-tag :type="s.severity === 'high' ? 'danger' : s.severity === 'medium' ? 'warning' : 'info'" size="small">
                          {{ s.severity === 'high' ? '严重' : s.severity === 'medium' ? '中等' : '轻微' }}
                        </el-tag>
                        <strong>{{ s.title }}</strong>
                      </div>
                      <p class="suggestion-desc">{{ s.description }}</p>
                      <p class="suggestion-fix">
                        <el-tag type="success" size="small" effect="plain">{{ s.operation }}</el-tag>
                        {{ s.fix_description }}
                      </p>
                    </div>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
              <div style="margin-top: 16px">
                <el-button type="success" @click="executeAiClean" :disabled="approvedOperations.length === 0" :loading="cleaning">
                  执行选中修复 ({{ approvedOperations.length }})
                </el-button>
                <el-button @click="undoClean" v-if="canUndo">撤销</el-button>
              </div>
            </div>

            <div v-if="cleanResult" style="margin-top: 16px">
              <el-alert type="success" :closable="false">
                <p v-for="c in cleanResult.changes" :key="c">{{ c }}</p>
                <p>{{ cleanResult.rows_before }} → {{ cleanResult.rows_after }} 行</p>
              </el-alert>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 3: Charts -->
        <el-tab-pane label="图表中心" name="charts">
          <div class="chart-panel">
            <div style="display:flex; gap:8px; align-items:center">
              <el-button type="primary" @click="loadCharts" :loading="chartLoading">AI 推荐图表</el-button>
              <template v-if="charts.length > 0">
                <el-button @click="exportAllCharts">逐个下载</el-button>
                <el-button @click="exportMerged">合并下载</el-button>
                <span style="color:#909399;font-size:12px">单个图表悬停右上角可单独导出</span>
              </template>
            </div>
            <div v-if="charts.length > 0" style="margin-top: 16px">
              <div v-for="(chart, idx) in charts" :key="idx" class="chart-item">
                <h4>{{ chart.title }} <el-tag size="small">{{ chart.chart_type }}</el-tag></h4>
                <p class="chart-reason">{{ chart.reason }}</p>
                <ChartPanel :ref="(el: any) => chartRefs[idx] = el" :echarts-option="chart.echarts_option" />
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 4: SQL Query -->
        <el-tab-pane label="SQL 查询" name="query">
          <div class="query-panel">
            <div class="query-input-area">
              <el-radio-group v-model="queryMode" size="small" style="margin-bottom: 8px">
                <el-radio-button value="nl">自然语言</el-radio-button>
                <el-radio-button value="sql">SQL</el-radio-button>
              </el-radio-group>
              <el-input
                v-if="queryMode === 'nl'"
                v-model="nlInput"
                placeholder="例如：统计每月销售额"
                @keyup.enter="runQuery"
              />
              <el-input
                v-else
                v-model="sqlInput"
                type="textarea"
                :rows="3"
                placeholder="SELECT * FROM data WHERE ..."
              />
              <el-button type="primary" @click="runQuery" :loading="queryLoading" style="margin-top: 8px">
                执行
              </el-button>
            </div>
            <div v-if="queryExecutedSql" class="executed-sql">
              <el-tag>执行 SQL:</el-tag> <code>{{ queryExecutedSql }}</code>
            </div>
            <div v-if="queryExplanation" class="ai-explain">
              <el-alert type="info" :closable="false">{{ queryExplanation }}</el-alert>
            </div>
            <DataTable
              v-if="queryResult"
              :columns="queryColumns"
              :rows="queryRows"
              style="margin-top: 16px"
            />
          </div>
        </el-tab-pane>

        <!-- Tab 5: AI Chat -->
        <el-tab-pane label="AI 对话" name="chat">
          <div class="chat-panel">
            <div ref="chatList" class="chat-messages">
              <div v-for="(msg, idx) in chatHistory" :key="idx" :class="['chat-msg', msg.role]">
                <strong>{{ msg.role === 'user' ? '你' : 'AI' }}:</strong>
                <div class="msg-content" v-html="formatChatContent(msg.content)"></div>
                <!-- Query result table inside chat message -->
                <div v-if="msg.queryResult" class="chat-query-result">
                  <div class="query-result-header">
                    <el-tag size="small" type="info">
                      共 {{ msg.queryResult.total_rows }} 行{{ msg.queryResult.rows.length < msg.queryResult.total_rows ? '，显示前 ' + msg.queryResult.rows.length + ' 行' : '' }}
                    </el-tag>
                    <code class="query-result-sql">{{ msg.queryResult.executed_sql }}</code>
                  </div>
                  <div class="query-result-table">
                    <el-table :data="msg.queryResult.rows" stripe border size="small" max-height="200">
                      <el-table-column
                        v-for="col in msg.queryResult.columns"
                        :key="col" :prop="col" :label="col"
                        :min-width="100" show-overflow-tooltip
                      />
                    </el-table>
                  </div>
                </div>
              </div>
              <AiLoading :visible="chatLoading" />
            </div>
            <div class="chat-presets">
              <el-button size="small" @click="quickChat('总结这份数据，有哪些主要发现和结论？')">总结数据</el-button>
              <el-button size="small" @click="quickChat('这份数据存在哪些数据质量问题？')">数据问题</el-button>
              <el-button size="small" @click="quickChat('帮我做一份完整的数据分析，包括概览、趋势、对比和异常')">完整分析</el-button>
              <el-button size="small" @click="quickChat('根据这份数据，有什么业务建议？')">业务建议</el-button>
            </div>
            <div class="chat-input">
              <el-input v-model="chatInput" placeholder="输入问题..." @keyup.enter="sendChat" />
              <el-button type="primary" @click="sendChat" :loading="chatLoading">发送</el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

    </div>

    <TaskProgress v-if="agentTaskId" v-model="showAgentProgress" :task-id="agentTaskId" @done="onAgentDone" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })
import { useDatasetStore } from '../stores/useDataset'
import { previewDataset, getExportUrl } from '../api/datasets'
import { aiAnalyze, aiExecute, undoCleaning } from '../api/cleaning'
import { executeQuery } from '../api/query'
import { recommendCharts, fetchChartData } from '../api/charts'
import { sendMessage } from '../api/chat'
import { generateReport } from '../api/reports'
import { runAgent } from '../api/agent'
import DataTable from '../components/DataTable.vue'
import ChartPanel from '../components/ChartPanel.vue'
import AiLoading from '../components/AiLoading.vue'
import TaskProgress from '../components/TaskProgress.vue'

const route = useRoute()
const router = useRouter()
const store = useDatasetStore()
const activeTab = ref('preview')

// Preview state
const previewColumns = ref<string[]>([])
const previewRows = ref<any[]>([])
const previewTotal = ref(0)
const previewPage = ref(1)
const previewLoading = ref(false)

// Cleaning state (AI-powered)
const suggestions = ref<any[]>([])
const selectedFixIndexes = ref<number[]>([])
const profileSummary = ref('')
const analyzing = ref(false)
const cleaning = ref(false)
const cleanResult = ref<any>(null)
const canUndo = ref(false)

const approvedOperations = computed(() =>
  selectedFixIndexes.value.map(i => suggestions.value[i]).filter((s: any) => s && s.operation)
)

// Chart state
const charts = ref<any[]>([])
const chartRefs = ref<any[]>([])
const chartLoading = ref(false)

// Query state
const queryMode = ref('nl')
const nlInput = ref('')
const sqlInput = ref('')
const queryLoading = ref(false)
const queryResult = ref(false)
const queryColumns = ref<string[]>([])
const queryRows = ref<any[]>([])
const queryExecutedSql = ref('')
const queryExplanation = ref('')

// Chat state
const chatHistory = ref<{ role: string; content: string; queryResult?: any }[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatList = ref<HTMLElement | null>(null)

onMounted(async () => {
  const id = route.params.id as string
  await store.load(id)
  if (store.current) loadPreview(1)
})

async function loadPreview(page: number) {
  previewLoading.value = true
  previewPage.value = page
  try {
    const data: any = await previewDataset(route.params.id as string, page, 50)
    previewColumns.value = data.columns
    previewRows.value = data.rows
    previewTotal.value = data.total_rows
  } finally {
    previewLoading.value = false
  }
}

async function aiAnalyzeData() {
  analyzing.value = true
  suggestions.value = []
  selectedFixIndexes.value = []
  try {
    const data: any = await aiAnalyze(route.params.id as string)
    suggestions.value = data.suggestions || []
    profileSummary.value = data.profile_summary || ''
    selectedFixIndexes.value = suggestions.value.map((_: any, i: number) => i) // all checked by default
  } finally {
    analyzing.value = false
  }
}

async function executeAiClean() {
  if (approvedOperations.value.length === 0) return
  cleaning.value = true
  try {
    const ops = approvedOperations.value.map((s: any) => ({ operation: s.operation, params: s.params || {} }))
    const data: any = await aiExecute(route.params.id as string, ops)
    cleanResult.value = data
    canUndo.value = data.can_undo
    await store.load(route.params.id as string)
    loadPreview(previewPage.value)
  } finally {
    cleaning.value = false
  }
}

async function undoClean() {
  await undoCleaning(route.params.id as string)
  cleanResult.value = null
  canUndo.value = false
  await store.load(route.params.id as string)
  loadPreview(previewPage.value)
}

async function loadCharts() {
  chartLoading.value = true
  chartRefs.value = []
  try {
    const data: any = await recommendCharts(route.params.id as string)
    const rawCharts = data.charts

    // For each chart: either use AI's data_query, or infer one from chart structure
    const filledCharts = await Promise.all(
      rawCharts.map(async (chart: any) => {
        let dq = chart.data_query

        // If AI didn't provide data_query, infer one from chart_type
        if (!dq && store.current?.fields) {
          const fields = store.current.fields
          const catFields = fields.filter((f: any) =>
            f.dtype && !['INT', 'FLOAT', 'DOUBLE', 'BIGINT', 'DECIMAL'].some(t => f.dtype.toUpperCase().includes(t))
          )
          const numFields = fields.filter((f: any) =>
            f.dtype && ['INT', 'FLOAT', 'DOUBLE', 'BIGINT', 'DECIMAL'].some(t => f.dtype.toUpperCase().includes(t))
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
          const result: any = await fetchChartData(route.params.id as string, dq)
          const ctype = dq.type || chart.chart_type
          const opt = JSON.parse(JSON.stringify(chart.echarts_option))

          if (ctype === 'scatter') {
            const pts = result.data || []
            opt.series = [{ type: 'scatter', data: pts, symbolSize: 6 }]
            if (opt.xAxis?.name) opt.xAxis.name = dq.x_col
            if (opt.yAxis?.name) opt.yAxis.name = dq.y_col
          } else if (ctype === 'bar' || ctype === 'line') {
            const cats = result.categories || []
            const vals = result.values || []
            // Sort descending for bar charts
            if (ctype === 'bar' && cats.length > 0) {
              const pairs = cats.map((c: string, i: number) => ({ cat: c, val: vals[i] || 0 }))
              pairs.sort((a: any, b: any) => b.val - a.val)
              opt.xAxis = { ...opt.xAxis, data: pairs.map((p: any) => p.cat), axisLabel: { ...opt.xAxis?.axisLabel, rotate: cats.length > 8 ? 30 : 0 } }
              opt.series = [{ ...(opt.series?.[0] || {}), type: ctype, data: pairs.map((p: any) => p.val), label: { show: true, position: 'top' } }]
            } else {
              opt.xAxis = { ...opt.xAxis, data: cats, axisLabel: { ...opt.xAxis?.axisLabel, rotate: cats.length > 8 ? 30 : 0 } }
              opt.series = [{ ...(opt.series?.[0] || {}), type: ctype, data: vals, label: { show: true, position: 'top' } }]
            }
            opt.yAxis = { ...opt.yAxis, name: `${dq.agg || ''}(${dq.y_col || ''})` }
          } else if (ctype === 'pie') {
            const pieData = (result.data || []).map((d: any) => ({ name: String(d.name), value: d.value }))
            opt.series = [{ type: 'pie', data: pieData, label: { show: true, formatter: '{b}: {c}' }, radius: ['30%', '70%'] }]
          } else if (ctype === 'histogram') {
            opt.xAxis = { ...opt.xAxis, data: result.categories || [] }
            opt.series = [{ type: 'bar', data: result.values || [], label: { show: true, position: 'top' } }]
            opt.yAxis = { ...opt.yAxis, name: '频数' }
          } else if (ctype === 'heatmap') {
            opt.series = [{ type: 'heatmap', data: (result.data || []).map((d: any) => [d[0], d[1], d[2]]) }]
          }

          return { ...chart, echarts_option: opt, data_query: dq }
        } catch {
          return chart
        }
      })
    )

    charts.value = filledCharts
  } finally {
    chartLoading.value = false
  }
}

function exportAllCharts() {
  chartRefs.value.forEach((ref: any, i: number) => {
    setTimeout(() => {
      if (ref && ref.exportPng) {
        ref.exportPng()
      }
    }, i * 300)
  })
}

async function exportMerged() {
  const urls: string[] = []
  for (const ref of chartRefs.value) {
    if (ref && ref.getDataUrl) {
      urls.push(ref.getDataUrl())
    }
  }
  if (urls.length === 0) return

  const images: HTMLImageElement[] = []
  for (const url of urls) {
    const img = await new Promise<HTMLImageElement>((resolve) => {
      const el = new Image()
      el.onload = () => resolve(el)
      el.src = url
    })
    images.push(img)
  }

  const padding = 20
  const maxWidth = Math.max(...images.map(i => i.width))
  const totalHeight = images.reduce((sum, i) => sum + i.height, 0) + padding * (images.length + 1)

  const canvas = document.createElement('canvas')
  canvas.width = maxWidth + padding * 2
  canvas.height = totalHeight
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  let y = padding
  for (const img of images) {
    const x = (maxWidth - img.width) / 2 + padding
    ctx.drawImage(img, x, y)
    y += img.height + padding
  }

  const link = document.createElement('a')
  link.href = canvas.toDataURL('image/png')
  link.download = 'charts_merged.png'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

async function runQuery() {
  queryLoading.value = true
  try {
    const sql = queryMode.value === 'sql' ? sqlInput.value : undefined
    const nl = queryMode.value === 'nl' ? nlInput.value : undefined
    const data: any = await executeQuery(route.params.id as string, sql, nl)
    queryColumns.value = data.columns
    queryRows.value = data.rows
    queryExecutedSql.value = data.executed_sql
    queryExplanation.value = data.ai_explanation
    queryResult.value = true
  } finally {
    queryLoading.value = false
  }
}

function quickChat(prompt: string) {
  chatInput.value = prompt
  sendChat()
}

async function sendChat() {
  if (!chatInput.value.trim()) return
  const msg = chatInput.value.trim()
  chatHistory.value.push({ role: 'user', content: msg })
  chatInput.value = ''
  chatLoading.value = true
  try {
    const data: any = await sendMessage(route.params.id as string, msg, chatHistory.value.slice(0, -1))
    chatHistory.value.push({
      role: 'assistant',
      content: data.answer,
      queryResult: data.query_result || null,
    })
    await nextTick()
    if (chatList.value) chatList.value.scrollTop = chatList.value.scrollHeight
  } finally {
    chatLoading.value = false
  }
}

const generatingReport = ref(false)
const agentRunning = ref(false)
const agentTaskId = ref('')
const showAgentProgress = ref(false)

async function handleAgentRun() {
  agentRunning.value = true
  try {
    const data: any = await runAgent(route.params.id as string)
    agentTaskId.value = data.task_id
    showAgentProgress.value = true
  } finally {
    agentRunning.value = false
  }
}

function onAgentDone(output: any) {
  showAgentProgress.value = false
  if (output?.report_id) {
    router.push(`/reports/${output.report_id}`)
  }
}

async function handleGenerateReport() {
  generatingReport.value = true
  try {
    const data: any = await generateReport(route.params.id as string)
    router.push(`/reports/${data.id}`)
  } finally {
    generatingReport.value = false
  }
}

function exportCsv() {
  const id = route.params.id as string
  window.open(getExportUrl(id), '_blank')
}

function formatChatContent(text: string): string {
  return marked.parse(text) as string
}
</script>

<style scoped>
.detail-page { padding: 0; max-width: 1200px; }
.detail-body { margin-top: 8px; }
.detail-body > .el-tabs { min-width: 0; }
.cleaning-panel, .chart-panel, .query-panel { padding: 8px 0; }
.suggestion-card {
  margin: 12px 0; padding: 16px;
  border: 1px solid #eaeaec; border-radius: 8px; background: #fff;
  display: flex; align-items: flex-start; overflow: hidden;
}
.suggestion-card :deep(.el-checkbox) { align-items: flex-start; padding-top: 2px; flex-shrink: 0; }
.suggestion-body { flex: 1; margin-left: 12px; min-width: 0; overflow: hidden; }
.suggestion-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.suggestion-desc { color: #606266; margin: 8px 0; font-size: 14px; line-height: 1.8; word-break: break-word; }
.suggestion-fix { color: #409eff; margin: 8px 0; font-size: 13px; word-break: break-word; }
.suggestion-sql { margin: 8px 0; overflow-x: auto; }
.suggestion-sql code {
  background: #f5f7fa; padding: 4px 8px; border-radius: 4px;
  font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-all; display: block;
}
.executed-sql { margin: 8px 0; }
.executed-sql code { background: #f5f7fa; padding: 2px 6px; border-radius: 4px; }
.ai-explain { margin: 8px 0; }
.chart-item { margin-bottom: 24px; }
.chart-reason { color: #909399; font-size: 13px; margin: 4px 0 8px; }

.chat-panel { display: flex; flex-direction: column; height: 500px; }
.chat-messages { flex: 1; overflow-y: auto; padding: 12px; background: #f9fafb; border-radius: 8px; margin-bottom: 12px; }
.chat-msg { margin-bottom: 12px; }
.chat-msg.user strong { color: #409eff; }
.chat-msg.assistant strong { color: #67c23a; }
.msg-content { margin-top: 4px; word-break: break-word; line-height: 1.7; }
.msg-content h1, .msg-content h2, .msg-content h3 { margin: 12px 0 6px; }
.msg-content h1 { font-size: 18px; }
.msg-content h2 { font-size: 16px; }
.msg-content h3 { font-size: 14px; }
.msg-content p { margin: 4px 0; }
.msg-content ul, .msg-content ol { margin: 4px 0; padding-left: 20px; }
.msg-content li { margin: 2px 0; }
.msg-content strong { font-weight: 600; }
.msg-content code { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 13px; }
.msg-content pre { background: #f5f7fa; padding: 10px 14px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
.msg-content pre code { background: none; padding: 0; }
.msg-content table { border-collapse: collapse; margin: 8px 0; font-size: 13px; }
.msg-content th, .msg-content td { border: 1px solid #dcdfe6; padding: 4px 10px; text-align: left; }
.msg-content th { background: #f5f7fa; }
.msg-content blockquote { border-left: 3px solid #409eff; padding-left: 12px; color: #606266; margin: 8px 0; }
.chat-presets { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.chat-input { display: flex; gap: 8px; }
.chat-input .el-input { flex: 1; }
.chat-query-result {
  margin-top: 8px; border: 1px solid #dcdfe6; border-radius: 6px; overflow: hidden;
}
.query-result-header {
  display: flex; align-items: center; gap: 8px; padding: 6px 10px;
  background: #f5f7fa; border-bottom: 1px solid #ebeef5;
}
.query-result-sql { font-size: 11px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.query-result-table { max-height: 200px; overflow-y: auto; }
</style>
