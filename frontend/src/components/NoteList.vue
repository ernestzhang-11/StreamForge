<template>
  <div class="note-list">
    <div class="list-header">
      <div class="header-info">
        <el-icon><Document /></el-icon>
        <span class="current-keyword">{{ appStore.currentKeyword || '未设置关键词' }}</span>
        <el-tag v-if="appStore.notes.length > 0" size="small" type="success">
          已抓取：{{ appStore.notes.length }} 条
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button
          size="small"
          :disabled="appStore.notes.length === 0"
          @click="appStore.selectAllNotes()"
        >
          全选
        </el-button>
        <el-button
          size="small"
          :disabled="appStore.notes.length === 0"
          @click="appStore.clearNoteSelection()"
        >
          清空
        </el-button>
      </div>
    </div>

    <div class="list-body">
      <el-scrollbar v-if="appStore.notes.length > 0" height="calc(100vh - 240px)">
        <div
          v-for="note in appStore.notes"
          :key="note.id"
          class="note-item"
          :class="{ selected: isSelected(note) }"
        >
          <el-checkbox
            :model-value="isSelected(note)"
            @change="appStore.toggleNoteSelection(note)"
          />
          <div class="note-content">
            <div class="note-title">
              <el-tag v-if="note.keyword" size="small" type="info" effect="plain">
                {{ note.keyword }}
              </el-tag>
              <span>{{ note.title }}</span>
            </div>
            <div class="note-meta">
              <span>作者: {{ note.author }}</span>
              <span>💗 {{ formatNumber(note.likes) }}</span>
              <span>💬 {{ formatNumber(note.comments) }}</span>
            </div>
            <div class="note-actions">
              <el-button
                size="small"
                type="primary"
                plain
                @click="handleRewrite(note)"
              >
                仿写
              </el-button>
              <el-button
                size="small"
                type="success"
                plain
                @click="handleCreateContent(note)"
              >
                正文
              </el-button>
            </div>
          </div>
        </div>
      </el-scrollbar>
      <el-empty v-else description="暂无笔记数据" />
    </div>
  </div>
</template>

<script setup>
import { Document } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

function isSelected(note) {
  return appStore.selectedNotes.some(n => n.id === note.id)
}

function formatNumber(num) {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num
}

function handleRewrite(note) {
  appStore.setCurrentNote(note)
  appStore.setAIMode('rewrite')
}

function handleCreateContent(note) {
  appStore.setCurrentNote(note)
  appStore.setAIMode('content')
}
</script>

<style scoped>
.note-list {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.list-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.current-keyword {
  font-weight: 500;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.list-body {
  flex: 1;
  overflow: hidden;
}

.note-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s;
  cursor: pointer;
}

.note-item:hover {
  background: #f5f7fa;
}

.note-item.selected {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.note-content {
  flex: 1;
  min-width: 0;
}

.note-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.note-title span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.note-title .el-tag {
  flex-shrink: 0;
}

.note-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.note-actions {
  display: flex;
  gap: 8px;
}
</style>
