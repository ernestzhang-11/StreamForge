<template>
  <div id="app">
    <div class="app-container">
      <!-- 侧边栏 -->
      <Sidebar />

      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 产品管理视图 -->
        <ProductManage v-if="appStore.currentView === 'product-manage'" />

        <!-- 当前工作视图 -->
        <CurrentWork v-else-if="appStore.currentView === 'current-work'" />

        <!-- 历史记录视图 -->
        <HistoryView v-else-if="appStore.currentView === 'history'" />

        <!-- 设置视图 -->
        <SettingsView v-else-if="appStore.currentView === 'settings'" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import Sidebar from '@/components/Sidebar.vue'
import ProductManage from '@/views/ProductManage.vue'
import CurrentWork from '@/views/CurrentWork.vue'
import HistoryView from '@/views/HistoryView.vue'
import SettingsView from '@/views/SettingsView.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

onMounted(() => {
  // 初始化：加载一些模拟数据
  initMockData()
})

function initMockData() {
  // 添加一些示例产品
  const mockProducts = [
    { id: 1, name: '精华液', description: '美容护肤产品', searchCount: 5, createdAt: new Date().toISOString() },
    { id: 2, name: '面霜', description: '保湿滋润产品', searchCount: 3, createdAt: new Date().toISOString() },
    { id: 3, name: '口红', description: '彩妆产品', searchCount: 8, createdAt: new Date().toISOString() }
  ]

  mockProducts.forEach(product => {
    appStore.addProduct(product)
  })

  // 默认视图
  appStore.setCurrentView('current-work')
}
</script>

<style>
#app {
  width: 100%;
  height: 100%;
}

.app-container {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
}

.main-content {
  flex: 1;
  height: 100%;
  overflow: hidden;
  background: #f5f7fa;
}
</style>
