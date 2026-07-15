<template>
  <div class="cleaning-panel">
    <el-button type="primary" @click="store.analyze(datasetId)" :loading="store.analyzing">
      AI 分析数据质量
    </el-button>
    <span v-if="store.profileSummary" class="summary-text">{{ store.profileSummary }}</span>

    <div v-if="store.suggestions.length > 0" class="results-area">
      <div class="results-title">AI 发现 {{ store.suggestions.length }} 个问题</div>
      <el-checkbox-group v-model="store.selectedFixIndexes">
        <div v-for="(s, idx) in store.suggestions" :key="idx" class="suggestion-card">
          <el-checkbox :value="idx" class="card-check" />
          <div class="card-body">
            <!-- 问题标题 -->
            <div class="card-title-row">
              <span class="severity-dot" :class="'sev-' + s.severity"></span>
              <span class="card-title">{{ s.title }}</span>
            </div>

            <!-- 影响范围 -->
            <div class="card-meta">
              <span class="meta-label">涉及字段</span>
              <template v-if="s.affected_columns && s.affected_columns.length">
                <span v-for="col in s.affected_columns" :key="col" class="col-tag">{{ col }}</span>
              </template>
              <span v-else class="meta-na">—</span>
              <span class="meta-sep"></span>
              <span class="meta-label">影响行数</span>
              <span v-if="s.affected_rows_estimate" class="meta-count">
                {{ s.affected_rows_estimate.toLocaleString() }} 行
                <template v-if="store.totalRows > 0">
                  （{{ (s.affected_rows_estimate / store.totalRows * 100).toFixed(1) }}%）
                </template>
              </span>
              <span v-else class="meta-na">—</span>
            </div>

            <!-- 问题描述 -->
            <p class="card-desc">{{ s.description }}</p>

            <!-- 修复预览 -->
            <div class="card-fix">
              <div class="fix-main">
                <code class="fix-op">{{ s.operation }}</code>
                <span class="fix-desc">{{ s.fix_description }}</span>
              </div>
              <div v-if="s.params && Object.keys(s.params).length" class="fix-params">
                <span class="params-label">参数：</span>
                <code v-for="(v, k) in s.params" :key="k" class="param-chip">{{ k }}={{ v }}</code>
              </div>
            </div>
          </div>
        </div>
      </el-checkbox-group>
      <div class="actions-bar">
        <el-button type="success" @click="store.execute(datasetId)" :disabled="store.approvedOperations.length === 0" :loading="store.cleaning">
          执行选中修复 ({{ store.approvedOperations.length }})
        </el-button>
        <el-button @click="store.undo(datasetId)" v-if="store.canUndo">撤销</el-button>
      </div>
    </div>

    <div v-if="store.cleanResult" class="result-alert">
      <el-alert type="success" :closable="false">
        <p v-for="c in store.cleanResult.changes" :key="c">{{ c }}</p>
        <p>{{ store.cleanResult.rows_before.toLocaleString() }} → {{ store.cleanResult.rows_after.toLocaleString() }} 行</p>
      </el-alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useCleaningStore } from '../stores/useCleaning'

defineProps<{ datasetId: string }>()
const store = useCleaningStore()
</script>

<style scoped>
.cleaning-panel { max-width: 720px; }
.summary-text { margin-left: 10px; color: #909399; font-size: 13px; }

.results-area { margin-top: 16px; }
.results-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; color: #1a1a1a; }

.suggestion-card {
  display: flex; align-items: flex-start; gap: 10px;
  margin-bottom: 12px; padding: 18px 20px;
  border: 1px solid #eaeaec; border-radius: 10px; background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.suggestion-card:hover { border-color: #d0d2f0; box-shadow: 0 1px 6px rgba(94,106,210,0.06); }
.card-check { padding-top: 1px; flex-shrink: 0; }
.card-body { flex: 1; min-width: 0; }

/* ── 标题 ── */
.card-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.severity-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sev-high { background: #e5484d; box-shadow: 0 0 0 3px rgba(229,72,77,0.15); }
.sev-medium { background: #f0a020; box-shadow: 0 0 0 3px rgba(240,160,32,0.15); }
.sev-low { background: #909399; box-shadow: 0 0 0 3px rgba(144,147,153,0.12); }
.card-title { font-size: 15px; font-weight: 600; color: #1a1a1a; }

/* ── 影响范围 ── */
.card-meta {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  margin-bottom: 10px; font-size: 12px;
}
.meta-label { color: #909399; }
.col-tag {
  display: inline-block; padding: 1px 8px;
  background: #eef0fd; color: #5e6ad2; border-radius: 4px;
  font-size: 11px; font-weight: 500;
}
.meta-sep { width: 1px; height: 12px; background: #e5e5e5; margin: 0 4px; }
.meta-count { color: #e67e22; font-weight: 550; }
.meta-na { color: #c0c4cc; }

/* ── 描述 ── */
.card-desc {
  margin: 0 0 12px; font-size: 13px; line-height: 1.7; color: #5c5c5c;
  padding-left: 2px;
}

/* ── 修复方案 ── */
.card-fix { background: #f9fafb; border-radius: 6px; padding: 12px 14px; }
.fix-main { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.fix-op {
  background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 4px;
  font-size: 12px; font-weight: 550; font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  white-space: nowrap;
}
.fix-desc { font-size: 13px; color: #3c3c3c; flex: 1; min-width: 0; }
.fix-params { margin-top: 8px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.params-label { font-size: 11px; color: #909399; }
.param-chip {
  background: #fff; border: 1px solid #e5e5e5; border-radius: 4px;
  padding: 2px 8px; font-size: 11px; color: #5c5c5c;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

.actions-bar { margin-top: 18px; }
.result-alert { margin-top: 16px; }
.result-alert p { margin: 2px 0; }
</style>
