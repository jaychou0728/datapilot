<template>
  <div class="detail-page">
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
        <el-button type="success" size="small" @click="handleAgentRun" :loading="agentRunning" :disabled="!!agentTaskId" style="background:linear-gradient(135deg,#5e6ad2,#7c3aed);border:none;color:#fff">一键分析</el-button>
        <el-button type="primary" size="small" @click="handleGenerateReport" :loading="generatingReport" :disabled="!!agentTaskId">生成报告</el-button>
        <el-button size="small" @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>

    <div v-if="agentTaskId && !showAgentProgress" class="task-running-bar" @click="showAgentProgress = true">
      <span class="task-running-dot"></span>
      <span>一键分析运行中，点击查看进度</span>
    </div>

    <el-alert v-if="pageError" type="error" :title="pageError" :closable="true" @close="pageError = ''" style="margin-bottom:16px" />

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
          <CleaningPanel :dataset-id="datasetId" />
        </el-tab-pane>

        <!-- Tab 3: Charts -->
        <el-tab-pane label="图表中心" name="charts">
          <div class="chart-panel">
            <div style="display:flex; gap:8px; align-items:center">
              <el-button type="primary" @click="loadCharts" :loading="chartStore.loading">AI 推荐图表</el-button>
              <template v-if="chartStore.charts.length > 0">
                <el-button @click="exportAllCharts">逐个下载</el-button>
                <el-button @click="exportMerged">合并下载</el-button>
              </template>
            </div>
            <div v-if="chartStore.charts.length > 0" style="margin-top: 16px">
              <div v-for="(chart, idx) in chartStore.charts" :key="idx" class="chart-item">
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
            <DataTable v-if="queryResult" :columns="queryColumns" :rows="queryRows" style="margin-top: 16px" />
          </div>
        </el-tab-pane>

        <!-- Tab 5: AI Chat -->
        <el-tab-pane label="AI 对话" name="chat">
          <div class="chat-panel">
            <div ref="chatList" class="chat-messages">
              <div v-for="(msg, idx) in chatHistory" :key="idx" :class="['chat-msg', msg.role]">
                <strong>{{ msg.role === 'user' ? '你' : 'AI' }}:</strong>
                <div class="msg-content" v-html="formatChatContent(msg.content)"></div>
                <div v-if="msg.queryResult" class="chat-query-result">
                  <div class="query-result-header">
                    <el-tag size="small" type="info">
                      共 {{ msg.queryResult.total_rows }} 行{{ msg.queryResult.rows.length < msg.queryResult.total_rows ? '，显示前 ' + msg.queryResult.rows.length + ' 行' : '' }}
                    </el-tag>
                    <code class="query-result-sql">{{ msg.queryResult.executed_sql }}</code>
                  </div>
                  <div class="query-result-table">
                    <el-table :data="msg.queryResult.rows" stripe border size="small" max-height="200">
                      <el-table-column v-for="col in msg.queryResult.columns" :key="col" :prop="col" :label="col" :min-width="100" show-overflow-tooltip />
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })
import { useDatasetStore } from '../stores/useDataset'
import { useCleaningStore } from '../stores/useCleaning'
import { useChartStore } from '../stores/useChart'
import { bus } from '../stores/eventBus'
import { previewDataset, getExportUrl } from '../api/datasets'
import { executeQuery } from '../api/query'
import { sendMessage } from '../api/chat'
import { generateReport } from '../api/reports'
import { runAgent } from '../api/agent'
import DataTable from '../components/DataTable.vue'
import ChartPanel from '../components/ChartPanel.vue'
import CleaningPanel from '../components/CleaningPanel.vue'
import AiLoading from '../components/AiLoading.vue'
import TaskProgress from '../components/TaskProgress.vue'

const route = useRoute()
const router = useRouter()
const store = useDatasetStore()
const chartStore = useChartStore()
const activeTab = ref('preview')
const datasetId = computed(() => route.params.id as string)

// Preview
const previewColumns = ref<string[]>([])
const previewRows = ref<any[]>([])
const previewTotal = ref(0)
const previewPage = ref(1)
const previewLoading = ref(false)

// Chart
const chartRefs = ref<any[]>([])

// Query
const queryMode = ref('nl')
const nlInput = ref('')
const sqlInput = ref('')
const queryLoading = ref(false)
const queryResult = ref(false)
const queryColumns = ref<string[]>([])
const queryRows = ref<any[]>([])
const queryExecutedSql = ref('')
const queryExplanation = ref('')

// Chat
const chatHistory = ref<{ role: string; content: string; queryResult?: any }[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatList = ref<HTMLElement | null>(null)

// Agent
const generatingReport = ref(false)
const agentRunning = ref(false)
const agentTaskId = ref('')
const showAgentProgress = ref(false)

const cleaningStore = useCleaningStore()

// ── Ctrl+Z undo shortcut ──
function onKeyDown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA') return
    if (cleaningStore.canUndo) {
      e.preventDefault()
      cleaningStore.undo(datasetId.value)
    }
  }
}

// ── Event bus listeners ──
onMounted(() => {
  bus.on('dataset:cleaned', refreshAfterClean)
  bus.on('dataset:undo', refreshAfterClean)
  document.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  bus.off('dataset:cleaned', refreshAfterClean)
  bus.off('dataset:undo', refreshAfterClean)
  document.removeEventListener('keydown', onKeyDown)
})

function refreshAfterClean() {
  loadPreview(previewPage.value)
}

const pageError = ref('')

// ── Init ──
onMounted(async () => {
  try {
    await store.load(datasetId.value)
    if (store.current) loadPreview(1)
    else pageError.value = '数据集不存在或已被删除'
  } catch {
    pageError.value = '加载数据集失败'
  }
})

// ── Preview ──
async function loadPreview(page: number) {
  previewLoading.value = true
  previewPage.value = page
  try {
    const data: any = await previewDataset(datasetId.value, page, 50)
    previewColumns.value = data.columns
    previewRows.value = data.rows
    previewTotal.value = data.total_rows
  } finally {
    previewLoading.value = false
  }
}

// ── Charts ──
async function loadCharts() {
  chartRefs.value = []
  await chartStore.load(datasetId.value, store.current?.fields)
}

function exportAllCharts() {
  chartRefs.value.forEach((ref, i) => {
    setTimeout(() => ref?.exportPng?.(), i * 300)
  })
}

async function exportMerged() {
  const urls: string[] = []
  for (const ref of chartRefs.value) {
    if (ref?.getDataUrl) urls.push(ref.getDataUrl())
  }
  if (!urls.length) return

  const images: HTMLImageElement[] = []
  for (const url of urls) {
    const img = await new Promise<HTMLImageElement>(resolve => {
      const el = new Image()
      el.onload = () => resolve(el)
      el.src = url
    })
    images.push(img)
  }

  const pad = 20
  const maxW = Math.max(...images.map(i => i.width))
  const totalH = images.reduce((s, i) => s + i.height, 0) + pad * (images.length + 1)
  const canvas = document.createElement('canvas')
  canvas.width = maxW + pad * 2
  canvas.height = totalH
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  let y = pad
  for (const img of images) {
    ctx.drawImage(img, (maxW - img.width) / 2 + pad, y)
    y += img.height + pad
  }

  const link = document.createElement('a')
  link.href = canvas.toDataURL('image/png')
  link.download = 'charts_merged.png'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// ── Query ──
async function runQuery() {
  queryLoading.value = true
  try {
    const sql = queryMode.value === 'sql' ? sqlInput.value : undefined
    const nl = queryMode.value === 'nl' ? nlInput.value : undefined
    const data: any = await executeQuery(datasetId.value, sql, nl)
    queryColumns.value = data.columns
    queryRows.value = data.rows
    queryExecutedSql.value = data.executed_sql
    queryExplanation.value = data.ai_explanation
    queryResult.value = true
  } finally {
    queryLoading.value = false
  }
}

// ── Chat ──
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
    const data: any = await sendMessage(datasetId.value, msg, chatHistory.value.slice(0, -1))
    chatHistory.value.push({
      role: 'assistant', content: data.answer,
      queryResult: data.query_result || null,
    })
    await nextTick()
    if (chatList.value) chatList.value.scrollTop = chatList.value.scrollHeight
  } catch {
    chatHistory.value.push({ role: 'assistant', content: '抱歉，AI 服务暂时不可用，请稍后重试。' })
  } finally {
    chatLoading.value = false
  }
}

function formatChatContent(text: string): string {
  return marked.parse(text) as string
}

// ── Agent ──
async function handleAgentRun() {
  agentRunning.value = true
  pageError.value = ''
  try {
    const data: any = await runAgent(datasetId.value)
    agentTaskId.value = data.task_id
    showAgentProgress.value = true
  } catch {
    pageError.value = '启动分析失败，请检查 AI 服务是否可用'
  } finally {
    agentRunning.value = false
  }
}

function onAgentDone(output: any) {
  showAgentProgress.value = false
  agentTaskId.value = ''
  if (output?.report_id) router.push(`/reports/${output.report_id}`)
}

async function handleGenerateReport() {
  generatingReport.value = true
  pageError.value = ''
  try {
    const data: any = await generateReport(datasetId.value)
    router.push(`/reports/${data.id}`)
  } catch {
    pageError.value = '生成报告失败，请检查 AI 服务是否可用'
  } finally {
    generatingReport.value = false
  }
}

function exportCsv() {
  window.open(getExportUrl(datasetId.value), '_blank')
}
</script>

<style scoped>
.detail-page { padding: 0; max-width: 1200px; }
.task-running-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px; margin-bottom: 12px;
  background: linear-gradient(135deg, #f0f1fd, #ede9fe);
  border: 1px solid #d4d5f8; border-radius: 8px;
  cursor: pointer; font-size: 13px; color: #5e6ad2;
  transition: all 0.15s;
}
.task-running-bar:hover { background: linear-gradient(135deg, #e8e9fb, #e0dcfc); }
.task-running-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #5e6ad2; animation: task-pulse 1s ease-in-out infinite;
}
@keyframes task-pulse { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.2); } }
.detail-body { margin-top: 8px; }
.chart-item { margin-bottom: 24px; }
.chart-reason { color: #909399; font-size: 13px; margin: 4px 0 8px; }
.executed-sql { margin: 8px 0; }
.executed-sql code { background: #f5f7fa; padding: 2px 6px; border-radius: 4px; }
.ai-explain { margin: 8px 0; }

.chat-panel { display: flex; flex-direction: column; height: 500px; }
.chat-messages { flex: 1; overflow-y: auto; padding: 12px; background: #f9fafb; border-radius: 8px; margin-bottom: 12px; }
.chat-msg { margin-bottom: 12px; }
.chat-msg.user strong { color: #409eff; }
.chat-msg.assistant strong { color: #67c23a; }
.msg-content { margin-top: 4px; word-break: break-word; line-height: 1.7; }
.msg-content h1, .msg-content h2, .msg-content h3 { margin: 12px 0 6px; }
.msg-content p { margin: 4px 0; }
.msg-content ul, .msg-content ol { margin: 4px 0; padding-left: 20px; }
.msg-content code { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 13px; }
.msg-content pre { background: #f5f7fa; padding: 10px 14px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
.msg-content pre code { background: none; padding: 0; }
.msg-content blockquote { border-left: 3px solid #409eff; padding-left: 12px; color: #606266; margin: 8px 0; }
.chat-presets { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.chat-input { display: flex; gap: 8px; }
.chat-input .el-input { flex: 1; }
.chat-query-result { margin-top: 8px; border: 1px solid #dcdfe6; border-radius: 6px; overflow: hidden; }
.query-result-header { display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: #f5f7fa; border-bottom: 1px solid #ebeef5; }
.query-result-sql { font-size: 11px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.query-result-table { max-height: 200px; overflow-y: auto; }
</style>
