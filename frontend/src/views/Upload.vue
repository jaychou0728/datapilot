<template>
  <div style="max-width:600px">
    <h2 style="margin:0 0 24px;font-size:20px;font-weight:650">上传数据</h2>

    <el-upload
      drag
      :auto-upload="false"
      :on-change="handleChange"
      :limit="1"
      accept=".csv,.xlsx,.xls"
    >
      <el-icon :size="36"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖拽文件到此处或点击上传</div>
      <template #tip>
        <div class="el-upload__tip">支持 .csv .xlsx .xls，最大 50MB</div>
      </template>
    </el-upload>

    <div v-if="uploading" style="margin-top:20px">
      <el-progress :percentage="100" :indeterminate="true" :stroke-width="4" />
      <p style="text-align:center;color:#868e96;margin-top:8px">解析中...</p>
    </div>

    <div v-if="result" style="margin-top:20px">
      <el-alert type="success" :closable="false">
        <template #title>
          上传成功：{{ result.name }}
          <span style="font-weight:400;color:#868e96">
            · {{ result.rows?.toLocaleString() }} 行 · {{ result.columns }} 列
          </span>
        </template>
      </el-alert>
      <div style="margin-top:16px;display:flex;gap:8px">
        <el-button type="primary" @click="$router.push(`/datasets/${result.id}`)">查看数据</el-button>
        <el-button @click="result = null">继续上传</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadDataset } from '../api/datasets'
import { ElMessage } from 'element-plus'

const uploading = ref(false)
const result = ref<any>(null)

async function handleChange(file: any) {
  uploading.value = true
  result.value = null
  try {
    result.value = await uploadDataset(file.raw)
    ElMessage.success('上传成功')
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>
