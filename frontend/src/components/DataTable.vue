<template>
  <div class="data-table-wrapper">
    <el-table
      :data="rows"
      stripe
      border
      v-loading="loading"
      :max-height="maxHeight"
      style="width: 100%"
    >
      <el-table-column
        v-for="col in columns"
        :key="col"
        :prop="col"
        :label="col"
        :min-width="120"
        show-overflow-tooltip
      />
      <template #empty>
        <el-empty :image-size="80" description="暂无数据" />
      </template>
    </el-table>
    <div class="pagination-bar" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="$emit('page-change', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  columns: string[]
  rows: Record<string, any>[]
  total?: number
  page?: number
  pageSize?: number
  loading?: boolean
  maxHeight?: string
}>(), {
  total: 0,
  page: 1,
  pageSize: 50,
  loading: false,
  maxHeight: '500',
})

defineEmits<{ 'page-change': [page: number] }>()

const currentPage = computed(() => props.page)
</script>

<style scoped>
.data-table-wrapper { width: 100%; }
.pagination-bar { display: flex; justify-content: flex-end; margin-top: 12px; }
</style>
