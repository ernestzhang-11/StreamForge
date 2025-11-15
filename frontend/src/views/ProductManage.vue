<template>
  <div class="product-manage-view">
    <!-- 产品列表视图 -->
    <div v-if="!appStore.currentProduct" class="product-list-container">
      <div class="page-header">
        <h2>产品词库管理</h2>
      </div>

      <!-- 新建产品 -->
      <div class="add-product-section">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Plus /></el-icon>
              <span>新建产品</span>
            </div>
          </template>
          <el-form :model="newProduct" label-width="80px">
            <el-form-item label="产品名称">
              <el-input
                v-model="newProduct.name"
                placeholder="请输入产品名称"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Check" @click="handleCreateProduct">
                创建
              </el-button>
              <el-button @click="resetForm">取消</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 产品列表 -->
      <div class="products-grid">
        <el-card
          v-for="product in appStore.products"
          :key="product.id"
          class="product-card"
          shadow="hover"
          @click="selectProduct(product)"
        >
          <div class="product-icon">
            <el-icon :size="32"><Box /></el-icon>
          </div>
          <div class="product-name">{{ product.name }}</div>
          <div class="product-stats">
            <el-statistic title="搜索次数" :value="product.searchCount" />
            <el-divider direction="vertical" />
            <el-statistic title="总笔记" :value="product.totalNotes || 0" />
            <el-divider direction="vertical" />
            <el-statistic title="仿写" :value="product.totalRewrites || 0" />
          </div>
          <div class="product-actions">
            <el-button size="small" type="primary" @click.stop="selectProduct(product)">
              查看详情
            </el-button>
            <el-button
              size="small"
              type="danger"
              :icon="Delete"
              @click.stop="handleDeleteProduct(product)"
            >
              删除
            </el-button>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 产品详情视图（关键词列表） -->
    <div v-else class="product-detail-container">
      <div class="page-header">
        <el-button :icon="ArrowLeft" @click="backToList">返回产品列表</el-button>
        <h2>产品：{{ appStore.currentProduct.name }}</h2>
      </div>

      <!-- 新增搜索 -->
      <div class="search-section">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Search /></el-icon>
              <span>新增搜索</span>
            </div>
          </template>
          <el-form inline>
            <el-form-item label="关键词">
              <el-input
                v-model="newSearch.keyword"
                placeholder="请输入搜索关键词"
                style="width: 300px"
              />
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="newSearch.count" :min="1" :max="100" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Search" @click="handleStartCrawl">
                开始抓取
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 综合统计 -->
      <div class="stats-section">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><TrendCharts /></el-icon>
              <span>综合数据统计</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic
                title="总搜索次数"
                :value="mockHistoryList.length"
                suffix="次"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="总笔记数" :value="87" suffix="条">
                <template #prefix>
                  <el-icon><Document /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="总仿写" :value="23" suffix="次">
                <template #prefix>
                  <el-icon><Edit /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="总正文" :value="12" suffix="篇">
                <template #prefix>
                  <el-icon><Notebook /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </el-card>
      </div>

      <!-- 历史搜索列表 -->
      <div class="history-section">
        <div class="history-header">
          <h3>搜索历史</h3>
          <div class="history-actions">
            <el-button
              size="small"
              :disabled="selectedHistoryItems.length === 0"
              @click="selectAllHistory"
            >
              {{ selectedHistoryItems.length === mockHistoryList.length ? '取消全选' : '全选' }}
            </el-button>
            <el-button
              type="primary"
              size="small"
              :disabled="selectedHistoryItems.length === 0"
              :icon="Promotion"
              @click="loadToWorkspace"
            >
              加载到工作区 ({{ selectedHistoryItems.length }})
            </el-button>
          </div>
        </div>

        <div
          v-for="item in mockHistoryList"
          :key="item.id"
          class="history-card"
          :class="{ selected: isHistorySelected(item) }"
        >
          <el-card shadow="hover">
            <div class="history-checkbox">
              <el-checkbox
                :model-value="isHistorySelected(item)"
                @change="toggleHistorySelection(item)"
              />
            </div>
            <div class="history-content">
              <div class="history-header-row">
                <div class="history-time">
                  <el-icon><Clock /></el-icon>
                  <span>{{ item.time }}</span>
                </div>
                <el-tag>{{ item.keyword }}</el-tag>
              </div>
              <div class="history-stats">
                <span>📊 笔记：{{ item.noteCount }}条</span>
                <span>✍️ 仿写：{{ item.rewriteCount }}次</span>
                <span>📝 正文：{{ item.contentCount }}篇</span>
              </div>
              <div class="history-preview">
                💡 高频词：{{ item.keywords.join('、') }}
              </div>
              <div class="history-item-actions">
                <el-button size="small" type="primary" @click="loadSingleToWorkspace(item)">
                  单独加载
                </el-button>
                <el-button size="small">查看详情</el-button>
                <el-button size="small" :icon="Download">导出</el-button>
                <el-button size="small" type="danger" :icon="Delete">删除</el-button>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  Plus,
  Check,
  Box,
  Delete,
  ArrowLeft,
  Search,
  TrendCharts,
  Document,
  Edit,
  Notebook,
  Clock,
  Download,
  Promotion
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const newProduct = ref({
  name: '',
  description: ''
})

const newSearch = ref({
  keyword: '',
  count: 20
})

const mockHistoryList = ref([
  {
    id: 1,
    time: '今天 14:30',
    keyword: '精华液推荐',
    noteCount: 20,
    rewriteCount: 5,
    contentCount: 3,
    keywords: ['必买(8)', '绝了(6)', '种草(5)']
  },
  {
    id: 2,
    time: '今天 10:15',
    keyword: '平价精华液',
    noteCount: 15,
    rewriteCount: 3,
    contentCount: 2,
    keywords: ['平价(12)', '性价比(9)', '学生党(7)']
  },
  {
    id: 3,
    time: '昨天 16:45',
    keyword: '美白精华液',
    noteCount: 25,
    rewriteCount: 8,
    contentCount: 5,
    keywords: ['美白(18)', '提亮(12)', '淡斑(10)']
  }
])

const selectedHistoryItems = ref([])

function handleCreateProduct() {
  if (!newProduct.value.name.trim()) {
    ElMessage.warning('请输入产品名称')
    return
  }

  const product = {
    id: Date.now(),
    name: newProduct.value.name,
    description: newProduct.value.description,
    searchCount: 0,
    totalNotes: 0,
    totalRewrites: 0,
    createdAt: new Date().toISOString()
  }

  appStore.addProduct(product)
  ElMessage.success('产品创建成功')
  resetForm()
}

function resetForm() {
  newProduct.value = {
    name: '',
    description: ''
  }
}

function selectProduct(product) {
  appStore.setCurrentProduct(product)
}

function backToList() {
  appStore.setCurrentProduct(null)
}

function handleDeleteProduct(product) {
  ElMessageBox.confirm(
    `确定要删除产品"${product.name}"吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    appStore.removeProduct(product.id)
    ElMessage.success('删除成功')
  }).catch(() => {})
}

function handleStartCrawl() {
  if (!newSearch.value.keyword.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  ElMessage.success('开始抓取，请稍候...')
  // 这里会调用后端API
  // 抓取成功后自动切换到当前工作视图
  setTimeout(() => {
    appStore.setCurrentView('current-work')
  }, 500)
}

// 历史记录选择相关
function isHistorySelected(item) {
  return selectedHistoryItems.value.some(i => i.id === item.id)
}

function toggleHistorySelection(item) {
  const index = selectedHistoryItems.value.findIndex(i => i.id === item.id)
  if (index === -1) {
    selectedHistoryItems.value.push(item)
  } else {
    selectedHistoryItems.value.splice(index, 1)
  }
}

function selectAllHistory() {
  if (selectedHistoryItems.value.length === mockHistoryList.value.length) {
    selectedHistoryItems.value = []
  } else {
    selectedHistoryItems.value = [...mockHistoryList.value]
  }
}

function loadToWorkspace() {
  if (selectedHistoryItems.value.length === 0) {
    ElMessage.warning('请至少选择一条搜索记录')
    return
  }

  // 合并所有选中的笔记数据
  const mergedNotes = []
  const mergedKeywords = []

  selectedHistoryItems.value.forEach(item => {
    mergedKeywords.push(item.keyword)

    // 模拟生成该关键词下的笔记数据
    for (let i = 0; i < item.noteCount; i++) {
      mergedNotes.push({
        id: `${item.id}_${i}_${Date.now()}`,
        noteId: `note_${item.id}_${i}`,
        title: `【${item.keyword}】这是第${i + 1}条笔记标题`,
        content: '这是笔记的内容描述...',
        author: `作者${i + 1}`,
        likes: Math.floor(Math.random() * 10000),
        comments: Math.floor(Math.random() * 1000),
        keyword: item.keyword
      })
    }
  })

  // 更新 store
  appStore.setNotes(mergedNotes)
  appStore.currentKeyword = mergedKeywords.join(' + ')

  // 切换到当前工作视图
  appStore.setCurrentView('current-work')

  ElMessage.success(`已合并加载 ${selectedHistoryItems.value.length} 个关键词，共 ${mergedNotes.length} 条笔记`)

  // 清空选择
  selectedHistoryItems.value = []
}

function loadSingleToWorkspace(item) {
  // 单独加载某个关键词的笔记
  const notes = []
  for (let i = 0; i < item.noteCount; i++) {
    notes.push({
      id: `${item.id}_${i}_${Date.now()}`,
      noteId: `note_${item.id}_${i}`,
      title: `【${item.keyword}】这是第${i + 1}条笔记标题`,
      content: '这是笔记的内容描述...',
      author: `作者${i + 1}`,
      likes: Math.floor(Math.random() * 10000),
      comments: Math.floor(Math.random() * 1000),
      keyword: item.keyword
    })
  }

  appStore.setNotes(notes)
  appStore.currentKeyword = item.keyword
  appStore.setCurrentView('current-work')

  ElMessage.success(`已加载"${item.keyword}"的 ${notes.length} 条笔记`)
}
</script>

<style scoped>
.product-manage-view {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.add-product-section {
  margin-bottom: 24px;
  max-width: 600px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.product-card {
  cursor: pointer;
  transition: all 0.3s;
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.product-icon {
  text-align: center;
  color: #409eff;
  margin-bottom: 16px;
}

.product-name {
  text-align: center;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.product-stats {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin-bottom: 16px;
}

.product-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.search-section,
.stats-section {
  margin-bottom: 24px;
}

.history-section {
  display: grid;
  gap: 16px;
}

.history-section > .history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e4e7ed;
}

.history-section > .history-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.history-section > .history-header .history-actions {
  display: flex;
  gap: 8px;
}

.history-card {
  width: 100%;
  position: relative;
  transition: all 0.3s;
}

.history-card.selected {
  transform: translateX(4px);
}

.history-card.selected .el-card {
  border: 2px solid #409eff;
  background: #ecf5ff;
}

.history-card .el-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.history-checkbox {
  padding-top: 4px;
}

.history-content {
  flex: 1;
  min-width: 0;
}

.history-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.history-time {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

.history-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #606266;
}

.history-preview {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
  color: #303133;
  margin-bottom: 12px;
}

.history-item-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
