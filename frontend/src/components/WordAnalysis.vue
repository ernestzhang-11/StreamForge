<template>
  <div class="word-analysis">
    <div class="analysis-header">
      <h4>第二步：关键词分析</h4>
    </div>

    <div class="analysis-body">
      <!-- 情绪词库 -->
      <div class="word-section">
        <div class="section-header">
          <el-icon><Sunny /></el-icon>
          <span>情绪词库</span>
        </div>
        <div class="word-table">
          <div class="table-header">
            <span>词汇</span>
            <span>删除</span>
          </div>
          <el-scrollbar max-height="200px">
            <div v-if="appStore.emotionWords.length > 0" class="table-body">
              <div
                v-for="word in appStore.emotionWords"
                :key="word"
                class="word-row"
              >
                <span class="word-text">{{ word }}</span>
                <el-button
                  type="danger"
                  size="small"
                  :icon="Delete"
                  circle
                  @click="appStore.removeEmotionWord(word)"
                />
              </div>
            </div>
            <el-empty v-else description="暂无情绪词" :image-size="60" />
          </el-scrollbar>
        </div>
        <div class="add-word">
          <el-input
            v-model="newEmotionWord"
            size="small"
            placeholder="输入新情绪词"
            @keyup.enter="addEmotionWord"
          >
            <template #append>
              <el-button :icon="Plus" @click="addEmotionWord">添加</el-button>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 场景词库 -->
      <div class="word-section">
        <div class="section-header">
          <el-icon><VideoCamera /></el-icon>
          <span>场景词库</span>
        </div>
        <div class="word-table">
          <div class="table-header">
            <span>词汇</span>
            <span>删除</span>
          </div>
          <el-scrollbar max-height="200px">
            <div v-if="appStore.sceneWords.length > 0" class="table-body">
              <div
                v-for="word in appStore.sceneWords"
                :key="word"
                class="word-row"
              >
                <span class="word-text">{{ word }}</span>
                <el-button
                  type="danger"
                  size="small"
                  :icon="Delete"
                  circle
                  @click="appStore.removeSceneWord(word)"
                />
              </div>
            </div>
            <el-empty v-else description="暂无场景词" :image-size="60" />
          </el-scrollbar>
        </div>
        <div class="add-word">
          <el-input
            v-model="newSceneWord"
            size="small"
            placeholder="输入新场景词"
            @keyup.enter="addSceneWord"
          >
            <template #append>
              <el-button :icon="Plus" @click="addSceneWord">添加</el-button>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="analysis-actions">
        <el-button
          type="primary"
          :icon="Download"
          @click="handleExport"
        >
          导出词库
        </el-button>
        <el-button
          :icon="Refresh"
          @click="handleReanalyze"
        >
          重新分析
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Sunny, VideoCamera, Delete, Plus, Download, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const newEmotionWord = ref('')
const newSceneWord = ref('')

function addEmotionWord() {
  if (!newEmotionWord.value.trim()) {
    ElMessage.warning('请输入情绪词')
    return
  }
  appStore.addEmotionWord(newEmotionWord.value.trim())
  newEmotionWord.value = ''
  ElMessage.success('添加成功')
}

function addSceneWord() {
  if (!newSceneWord.value.trim()) {
    ElMessage.warning('请输入场景词')
    return
  }
  appStore.addSceneWord(newSceneWord.value.trim())
  newSceneWord.value = ''
  ElMessage.success('添加成功')
}

function handleExport() {
  const data = {
    emotionWords: appStore.emotionWords,
    sceneWords: appStore.sceneWords
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `词库_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

function handleReanalyze() {
  // TODO: 调用后端API重新分析
  ElMessage.success('重新分析中...')

  // 模拟分析
  setTimeout(() => {
    // 添加一些示例词汇
    const mockEmotionWords = ['必买', '绝了', '爆款', '真香', '宝藏', '冲']
    const mockSceneWords = ['开箱', '测评', '种草', '分享', '推荐', '好物']

    mockEmotionWords.forEach(word => appStore.addEmotionWord(word))
    mockSceneWords.forEach(word => appStore.addSceneWord(word))

    ElMessage.success('分析完成')
  }, 1000)
}
</script>

<style scoped>
.word-analysis {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.analysis-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.analysis-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.analysis-body {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.word-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.section-header .el-icon {
  font-size: 18px;
  color: #409eff;
}

.word-table {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.table-header {
  display: grid;
  grid-template-columns: 1fr 80px;
  padding: 10px 16px;
  background: #f5f7fa;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  border-bottom: 1px solid #e4e7ed;
}

.table-body {
  max-height: 200px;
}

.word-row {
  display: grid;
  grid-template-columns: 1fr 80px;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.word-row:last-child {
  border-bottom: none;
}

.word-row:hover {
  background: #f5f7fa;
}

.word-text {
  font-size: 13px;
  color: #303133;
}

.add-word {
  margin-top: 8px;
}

.analysis-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.analysis-actions .el-button {
  flex: 1;
}
</style>
