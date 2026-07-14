<template>
  <div class="sidebar">
    <h4>表结构</h4>
    <el-tag v-for="field in fields" :key="field.name" class="field-tag" :type="tagType(field.dtype)">
      {{ field.name }}
      <span class="dtype">{{ field.dtype }}</span>
    </el-tag>
  </div>
</template>

<script setup lang="ts">
defineProps<{ fields: { name: string; dtype: string }[] }>()

function tagType(dtype: string): string {
  const t = dtype.toLowerCase()
  if (t.includes('int') || t.includes('float') || t.includes('double')) return 'warning'
  if (t.includes('date') || t.includes('time')) return 'success'
  return 'info'
}
</script>

<style scoped>
.sidebar { padding: 12px; }
.sidebar h4 { margin: 0 0 8px; font-size: 14px; color: #606266; }
.field-tag { margin: 4px 4px 4px 0; display: inline-flex; align-items: center; }
.dtype { font-size: 11px; opacity: 0.7; margin-left: 4px; }
</style>
