<template>
  <div class="crawl-panel">
    <div class="panel-header">
      <h3>第一步：小红书笔记采集</h3>
    </div>
    <div class="panel-body">
      <el-form :model="form" label-width="100px">
        <el-form-item label="搜索关键词">
          <el-input
            v-model="form.keyword"
            placeholder="请输入搜索关键词"
            clearable
            @keyup.enter="handleCrawl"
          />
        </el-form-item>
        <el-form-item label="抓取数量">
          <el-input-number
            v-model="form.count"
            :min="1"
            :max="100"
            :step="5"
            controls-position="right"
          />
          <span class="unit">条</span>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="crawling"
            :icon="Search"
            @click="handleCrawl"
          >
            开始抓取
          </el-button>
          <span v-if="statusText" class="status-text" :class="statusClass">
            {{ statusText }}
          </span>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const form = ref({
  keyword: '',
  count: 20
})

const crawling = ref(false)
const statusText = ref('')
const statusClass = ref('')

async function handleCrawl() {
  if (!form.value.keyword.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  if (!appStore.currentProduct) {
    ElMessage.warning('请先选择或创建一个产品')
    return
  }

  crawling.value = true
  statusText.value = '抓取中...'
  statusClass.value = 'status-loading'

  try {
    // TODO: 调用后端API进行抓取
    // const response = await axios.get('/api/xhs/search_notes', {
    //   params: {
    //     keyword: form.value.keyword,
    //     limit: form.value.count
    //   }
    // })

    // 模拟抓取
    await new Promise(resolve => setTimeout(resolve, 2000))

    // 模拟数据
    const mockNotes = Array.from({ length: form.value.count }, (_, i) => ({
      id: Date.now() + i,
      noteId: `note_${Date.now()}_${i}`,
      title: `这是第${i + 1}条笔记标题 - ${form.value.keyword}`,
      content: '这是笔记的内容描述...',
      author: `作者${i + 1}`,
      likes: Math.floor(Math.random() * 10000),
      comments: Math.floor(Math.random() * 1000)
    }))

    appStore.setNotes(mockNotes)
    appStore.currentKeyword = form.value.keyword

    statusText.value = `抓取完成 ✓`
    statusClass.value = 'status-success'
    ElMessage.success(`成功抓取 ${mockNotes.length} 条笔记`)

    // 自动切换到当前工作视图
    appStore.setCurrentView('current-work')

    // 3秒后清除状态
    setTimeout(() => {
      statusText.value = ''
    }, 3000)
  } catch (error) {
    statusText.value = '抓取失败 ✗'
    statusClass.value = 'status-error'
    ElMessage.error('抓取失败：' + (error.message || '未知错误'))

    setTimeout(() => {
      statusText.value = ''
    }, 3000)
  } finally {
    crawling.value = false
  }
}
</script>

<style scoped>
.crawl-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.panel-header {
  padding: 16px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.panel-body {
  padding: 24px;
}

.el-form {
  display: flex;
  align-items: flex-end;
  gap: 16px;
}

.el-form-item {
  margin-bottom: 0;
}

.unit {
  margin-left: 8px;
  color: #606266;
}

.status-text {
  margin-left: 12px;
  font-size: 14px;
  font-weight: 500;
}

.status-loading {
  color: #409eff;
}

.status-success {
  color: #67c23a;
}

.status-error {
  color: #f56c6c;
}
</style>
