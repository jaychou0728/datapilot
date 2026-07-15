<template>
  <el-dialog v-model="visible" title="任务进度" width="420px" :close-on-click-modal="true" @close="onDialogClose">
    <div style="text-align:center;padding:20px 0">
      <el-progress
        :percentage="progress"
        :status="status === 'failed' ? 'exception' : status === 'done' ? 'success' : undefined"
        :stroke-width="16"
        :indeterminate="status === 'pending'"
      />
      <p style="margin-top:16px;color:#606266;font-size:14px">{{ statusText }}</p>
      <p v-if="errorMsg" style="color:#f56c6c;font-size:13px;margin-top:8px">{{ errorMsg }}</p>
    </div>
    <template #footer>
      <el-button v-if="status === 'pending' || status === 'running'" @click="onDialogClose">后台运行</el-button>
      <el-button v-else type="primary" @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { ElNotification } from 'element-plus'
import { getTask } from '../api/tasks'

const props = defineProps<{ taskId: string; modelValue: boolean }>()
const emit = defineEmits(['update:modelValue', 'done'])

const visible = ref(props.modelValue)
const progress = ref(0)
const status = ref('pending')
const statusText = ref('准备中...')
const errorMsg = ref('')
let timer: ReturnType<typeof setInterval> | null = null
let emittedDone = false

// Expose for parent to reopen
defineExpose({
  reopen() {
    visible.value = true
  },
  getStatus() {
    return status.value
  },
})

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v && !emittedDone) startPolling()
})
watch(visible, (v) => emit('update:modelValue', v))

const statusLabels: Record<string, string> = {
  pending: '等待执行...',
  running: '正在执行...',
  done: '执行完成',
  failed: '执行失败',
}

function startPolling() {
  if (emittedDone) return
  status.value = 'pending'
  progress.value = 0
  errorMsg.value = ''
  if (timer) clearInterval(timer)
  timer = setInterval(async () => {
    if (emittedDone) { clearInterval(timer!); timer = null; return }
    try {
      const data: any = await getTask(props.taskId)
      status.value = data.status
      progress.value = data.progress || 0
      statusText.value = statusLabels[data.status] || data.status
      if (data.status === 'failed') errorMsg.value = data.error || ''
      if (data.status === 'done' || data.status === 'failed') {
        clearInterval(timer!)
        timer = null
        if (emittedDone) return
        emittedDone = true
        if (!visible.value) {
          if (data.status === 'done') {
            ElNotification({ title: '分析完成', message: '一键分析已完成，正在跳转到报告页面', type: 'success', duration: 4000 })
            emit('done', data.output)
          } else {
            ElNotification({ title: '分析失败', message: data.error || '未知错误', type: 'error', duration: 6000 })
          }
        } else {
          if (data.status === 'done') emit('done', data.output)
        }
      }
    } catch { /* ignore poll errors */ }
  }, 2000)
}

function onDialogClose() {
  visible.value = false
  // Keep polling in background
}

function handleClose() {
  visible.value = false
  if (timer) { clearInterval(timer); timer = null }
}

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>
