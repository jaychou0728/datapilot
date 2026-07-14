<template>
  <div class="ai-loading" v-if="visible">
    <div class="dot-pulse"></div>
    <span>{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ visible: boolean; text?: string }>(), { text: 'AI 思考中...' })
</script>

<style scoped>
.ai-loading { display: flex; align-items: center; gap: 8px; padding: 8px 16px; color: #909399; }
.dot-pulse { width: 8px; height: 8px; border-radius: 50%; background: #409eff; animation: pulse 1s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 0.3; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1.2); } }
</style>
