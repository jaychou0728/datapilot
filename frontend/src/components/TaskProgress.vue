<template>
  <el-dialog v-model="visible" title="任务进度" width="420px" :close-on-click-modal="false" :show-close="false">
    <div style="text-align:center;padding:20px 0">
      <el-progress
        :percentage="progress"
        :status="status === 'failed' ? 'exception' : status === 'done' ? 'success' : undefined"
        :stroke-width="16"
      />
      <p style="margin-top:16px;color:#606266;font-size:14px">{{ statusText }}</p>
      <p v-if="errorMsg" style="color:#f56c6c;font-size:13px;margin-top:8px">{{ errorMsg }}</p>
    </div>
    <template #footer v-if="status === 'done' || status === 'failed'">
      <el-button type="primary" @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { getTask } from '../api/tasks'

const props = defineProps<{ taskId: string; modelValue: boolean }>()
const emit = defineEmits(['update:modelValue', 'done'])

const visible = ref(props.modelValue)
const progress = ref(0)
const status = ref('pending')
const statusText = ref('准备中...')
const errorMsg = ref('')
let timer: any = null

watch(() => props.modelValue, (v) => { visible.value = v; if (v) startPolling() })
watch(visible, (v) => emit('update:modelValue', v))

const statusLabels: Record<string, string> = {
  pending: '等待执行...',
  running: '正在执行...',
  done: '执行完成',
  failed: '执行失败',
}

function startPolling() {
  status.value = 'pending'
  progress.value = 0
  errorMsg.value = ''
  timer = setInterval(async () => {
    try {
      const data: any = await getTask(props.taskId)
      status.value = data.status
      progress.value = data.progress || 0
      statusText.value = statusLabels[data.status] || data.status
      if (data.status === 'failed') errorMsg.value = data.error || ''
      if (data.status === 'done' || data.status === 'failed') {
        clearInterval(timer)
        if (data.status === 'done') emit('done', data.output)
      }
    } catch { /* ignore poll errors */ }
  }, 2000)
}

function handleClose() {
  visible.value = false
}

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>
