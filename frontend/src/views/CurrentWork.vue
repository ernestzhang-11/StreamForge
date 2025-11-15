<template>
  <div class="current-work-view">
    <!-- 当前任务信息 -->
    <div class="task-info-panel">
      <el-card shadow="hover">
        <div class="task-header">
          <div class="task-title">
            <el-icon size="24"><Folder /></el-icon>
            <div class="task-meta">
              <h3>当前任务</h3>
              <div class="breadcrumb">
                <span class="product-name">{{ appStore.currentProduct?.name || '未选择产品' }}</span>
                <el-icon v-if="appStore.currentKeyword"><ArrowRight /></el-icon>
                <span v-if="appStore.currentKeyword" class="keyword-name">{{ appStore.currentKeyword }}</span>
              </div>
            </div>
          </div>
          <div class="task-stats">
            <el-statistic title="笔记数" :value="appStore.notes.length" />
            <el-divider direction="vertical" />
            <el-statistic title="已选" :value="appStore.selectedNoteCount" />
            <el-divider direction="vertical" />
            <el-statistic title="仿写" :value="appStore.rewrites.length" />
            <el-divider direction="vertical" />
            <el-statistic title="正文" :value="appStore.contents.length" />
          </div>
          <div class="task-actions">
            <el-button
              type="primary"
              :icon="Back"
              @click="backToProduct"
            >
              返回产品
            </el-button>
            <el-button
              :icon="DocumentAdd"
              :disabled="!appStore.currentProduct"
              @click="startNewSearch"
            >
              新增搜索
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 空状态提示 -->
    <div v-if="appStore.notes.length === 0" class="empty-workspace">
      <el-empty description="暂无笔记数据">
        <template #image>
          <el-icon :size="100" color="#c0c4cc">
            <Document />
          </el-icon>
        </template>
        <template #description>
          <p>还没有抓取笔记哦</p>
          <p style="font-size: 14px; color: #909399; margin-top: 8px;">
            请先在"产品管理"中选择产品并搜索关键词
          </p>
        </template>
        <el-button type="primary" @click="goToProductManage">
          前往产品管理
        </el-button>
      </el-empty>
    </div>

    <!-- 三栏内容区 -->
    <div v-else class="content-grid">
      <!-- 笔记列表 -->
      <div class="grid-column">
        <NoteList />
      </div>

      <!-- 词汇分析 -->
      <div class="grid-column">
        <WordAnalysis />
      </div>

      <!-- AI创作面板 -->
      <div class="grid-column-large">
        <AICreation />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Folder, ArrowRight, Back, DocumentAdd, Document } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'
import NoteList from '@/components/NoteList.vue'
import WordAnalysis from '@/components/WordAnalysis.vue'
import AICreation from '@/components/AICreation.vue'

const appStore = useAppStore()

function backToProduct() {
  if (appStore.currentProduct) {
    appStore.setCurrentView('product-manage')
  }
}

function startNewSearch() {
  if (appStore.currentProduct) {
    appStore.setCurrentView('product-manage')
  }
}

function goToProductManage() {
  appStore.setCurrentView('product-manage')
}
</script>

<style scoped>
.current-work-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 16px;
  overflow: hidden;
}

.task-info-panel {
  flex-shrink: 0;
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.task-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.task-title .el-icon {
  color: #409eff;
  flex-shrink: 0;
}

.task-meta {
  flex: 1;
  min-width: 0;
}

.task-meta h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
}

.product-name {
  font-weight: 500;
  color: #409eff;
}

.keyword-name {
  color: #67c23a;
  font-weight: 500;
}

.task-stats {
  display: flex;
  align-items: center;
  gap: 16px;
}

.task-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.empty-workspace {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 8px;
}

.content-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 16px;
  min-height: 0;
}

.grid-column,
.grid-column-large {
  min-height: 0;
  overflow: hidden;
}
</style>
