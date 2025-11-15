<template>
  <div class="history-view">
    <div class="page-header">
      <h2>📚 全部历史记录</h2>
    </div>

    <!-- 搜索和筛选 -->
    <div class="filter-section">
      <el-card shadow="never">
        <el-form inline>
          <el-form-item label="搜索">
            <el-input
              v-model="searchQuery"
              placeholder="搜索关键词..."
              clearable
              :prefix-icon="Search"
              style="width: 300px"
            />
          </el-form-item>
          <el-form-item label="产品筛选">
            <el-select v-model="selectedProduct" placeholder="全部产品" clearable>
              <el-option
                v-for="product in appStore.products"
                :key="product.id"
                :label="product.name"
                :value="product.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="时间范围">
            <el-radio-group v-model="timeRange" size="small">
              <el-radio-button label="today">今天</el-radio-button>
              <el-radio-button label="week">最近7天</el-radio-button>
              <el-radio-button label="month">本月</el-radio-button>
              <el-radio-button label="all">全部</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 历史记录列表 -->
    <div class="history-list">
      <!-- 按日期分组 -->
      <div v-for="group in groupedHistory" :key="group.date" class="date-group">
        <div class="date-header">
          <el-icon><Calendar /></el-icon>
          <span>{{ group.date }}</span>
        </div>

        <div class="history-items">
          <el-card
            v-for="item in group.items"
            :key="item.id"
            class="history-item"
            shadow="hover"
          >
            <div class="item-header">
              <div class="item-time">
                <el-icon><Clock /></el-icon>
                <span>{{ item.time }}</span>
              </div>
              <div class="item-product">
                <el-icon><Box /></el-icon>
                <span>{{ item.productName }}</span>
                <el-icon><ArrowRight /></el-icon>
                <span>{{ item.keyword }}</span>
              </div>
            </div>

            <div class="item-stats">
              <el-statistic title="笔记" :value="item.noteCount" suffix="条" />
              <el-divider direction="vertical" />
              <el-statistic title="仿写" :value="item.rewriteCount" suffix="次" />
              <el-divider direction="vertical" />
              <el-statistic title="正文" :value="item.contentCount" suffix="篇" />
            </div>

            <div class="item-preview">
              <div class="preview-label">💡 高频词：</div>
              <div class="preview-tags">
                <el-tag
                  v-for="(word, index) in item.keywords"
                  :key="index"
                  size="small"
                  type="info"
                >
                  {{ word }}
                </el-tag>
              </div>
            </div>

            <div class="item-actions">
              <el-button size="small" type="primary" :icon="View">
                查看详情
              </el-button>
              <el-button size="small" :icon="Promotion">
                加载到工作区
              </el-button>
              <el-button size="small" :icon="Download">
                导出
              </el-button>
              <el-button size="small" type="danger" :icon="Delete">
                删除
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 加载更多 -->
    <div class="load-more">
      <el-button>加载更多...</el-button>
    </div>

    <!-- 批量操作 -->
    <div class="batch-actions">
      <el-button type="danger" :icon="Delete">
        清空30天前的历史
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Search,
  Calendar,
  Clock,
  Box,
  ArrowRight,
  View,
  Promotion,
  Download,
  Delete
} from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const searchQuery = ref('')
const selectedProduct = ref(null)
const timeRange = ref('all')

// 模拟历史数据
const mockHistory = ref([
  {
    id: 1,
    date: '今天',
    time: '14:30',
    productName: '精华液',
    keyword: '精华液推荐',
    noteCount: 20,
    rewriteCount: 5,
    contentCount: 3,
    keywords: ['必买(8)', '绝了(6)', '种草(5)']
  },
  {
    id: 2,
    date: '今天',
    time: '10:15',
    productName: '面霜',
    keyword: '补水面霜',
    noteCount: 15,
    rewriteCount: 3,
    contentCount: 2,
    keywords: ['好用(15)', '推荐(12)', '滋润(10)']
  },
  {
    id: 3,
    date: '昨天',
    time: '16:45',
    productName: '口红',
    keyword: '显白口红',
    noteCount: 30,
    rewriteCount: 8,
    contentCount: 5,
    keywords: ['显白(20)', '必入(15)', '颜色(12)']
  }
])

const groupedHistory = computed(() => {
  const groups = {}

  mockHistory.value.forEach(item => {
    if (!groups[item.date]) {
      groups[item.date] = {
        date: item.date,
        items: []
      }
    }
    groups[item.date].items.push(item)
  })

  return Object.values(groups)
})
</script>

<style scoped>
.history-view {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.filter-section {
  margin-bottom: 24px;
}

.history-list {
  margin-bottom: 24px;
}

.date-group {
  margin-bottom: 32px;
}

.date-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e4e7ed;
  font-size: 16px;
  font-weight: 600;
  color: #606266;
}

.history-items {
  display: grid;
  gap: 16px;
}

.history-item {
  transition: all 0.3s;
}

.history-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.item-time {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #909399;
  font-size: 14px;
}

.item-product {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.item-stats {
  display: flex;
  justify-content: space-around;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.item-preview {
  margin-bottom: 16px;
}

.preview-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.item-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.load-more {
  text-align: center;
  margin-bottom: 24px;
}

.batch-actions {
  text-align: center;
  padding: 20px;
  border-top: 1px solid #e4e7ed;
}
</style>
