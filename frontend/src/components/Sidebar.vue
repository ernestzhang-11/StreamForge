<template>
  <div class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <!-- 折叠按钮 -->
    <div class="collapse-btn" @click="appStore.toggleSidebar">
      <el-icon>
        <DArrowLeft v-if="!appStore.sidebarCollapsed" />
        <DArrowRight v-else />
      </el-icon>
    </div>

    <!-- 菜单列表 -->
    <div class="menu-list">
      <!-- 产品管理 -->
      <div
        class="menu-item"
        :class="{ active: appStore.currentView === 'product-manage' }"
        @click="handleViewChange('product-manage')"
      >
        <el-icon class="menu-icon">
          <Box />
        </el-icon>
        <transition name="fade">
          <div v-if="!appStore.sidebarCollapsed" class="menu-content">
            <span class="menu-label">产品管理</span>
            <el-badge
              v-if="appStore.products.length > 0"
              :value="appStore.products.length"
              class="menu-badge"
            />
          </div>
        </transition>
        <el-tooltip
          v-if="appStore.sidebarCollapsed"
          content="产品管理"
          placement="right"
        >
          <div></div>
        </el-tooltip>
      </div>

      <!-- 产品列表（展开状态下显示） -->
      <transition name="slide">
        <div
          v-if="!appStore.sidebarCollapsed && appStore.currentView === 'product-manage'"
          class="product-submenu"
        >
          <div
            v-for="product in appStore.products"
            :key="product.id"
            class="product-item"
            :class="{ active: appStore.currentProduct?.id === product.id }"
            @click.stop="handleProductClick(product)"
          >
            <el-icon><FolderOpened /></el-icon>
            <span class="product-name">{{ product.name }}</span>
            <el-badge
              v-if="product.searchCount > 0"
              :value="product.searchCount"
              type="info"
              class="product-badge"
            />
          </div>
          <div class="add-product-btn" @click.stop="handleAddProduct">
            <el-icon><Plus /></el-icon>
            <span>新建产品</span>
          </div>
        </div>
      </transition>

      <div class="menu-divider"></div>

      <!-- 当前工作 -->
      <div
        class="menu-item"
        :class="{ active: appStore.currentView === 'current-work' }"
        @click="handleViewChange('current-work')"
      >
        <el-icon class="menu-icon">
          <Edit />
        </el-icon>
        <transition name="fade">
          <div v-if="!appStore.sidebarCollapsed" class="menu-content">
            <span class="menu-label">当前工作</span>
            <el-badge
              v-if="appStore.notes.length > 0"
              :value="appStore.notes.length"
              type="success"
              is-dot
            />
          </div>
        </transition>
        <el-tooltip
          v-if="appStore.sidebarCollapsed"
          content="当前工作"
          placement="right"
        >
          <div></div>
        </el-tooltip>
      </div>

      <div class="menu-divider"></div>

      <!-- 历史记录 -->
      <div
        class="menu-item"
        :class="{ active: appStore.currentView === 'history' }"
        @click="handleViewChange('history')"
      >
        <el-icon class="menu-icon">
          <Clock />
        </el-icon>
        <transition name="fade">
          <div v-if="!appStore.sidebarCollapsed" class="menu-content">
            <span class="menu-label">历史记录</span>
            <el-badge
              v-if="appStore.historyList.length > 0"
              :value="appStore.historyList.length"
              type="warning"
            />
          </div>
        </transition>
        <el-tooltip
          v-if="appStore.sidebarCollapsed"
          content="历史记录"
          placement="right"
        >
          <div></div>
        </el-tooltip>
      </div>

      <!-- Spacer -->
      <div class="spacer"></div>

      <!-- 设置 -->
      <div
        class="menu-item"
        :class="{ active: appStore.currentView === 'settings' }"
        @click="handleViewChange('settings')"
      >
        <el-icon class="menu-icon">
          <Setting />
        </el-icon>
        <transition name="fade">
          <span v-if="!appStore.sidebarCollapsed" class="menu-label">设置</span>
        </transition>
        <el-tooltip
          v-if="appStore.sidebarCollapsed"
          content="设置"
          placement="right"
        >
          <div></div>
        </el-tooltip>
      </div>
    </div>

    <!-- 新建产品对话框 -->
    <el-dialog
      v-model="showAddProductDialog"
      title="新建产品"
      width="400px"
    >
      <el-form :model="newProductForm" label-width="80px">
        <el-form-item label="产品名称">
          <el-input
            v-model="newProductForm.name"
            placeholder="请输入产品名称"
            @keyup.enter="submitNewProduct"
          />
        </el-form-item>
        <el-form-item label="产品描述">
          <el-input
            v-model="newProductForm.description"
            type="textarea"
            :rows="3"
            placeholder="选填，描述产品特点"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddProductDialog = false">取消</el-button>
        <el-button type="primary" @click="submitNewProduct">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAppStore } from '@/stores/app'
import {
  Box,
  Edit,
  Clock,
  Setting,
  DArrowLeft,
  DArrowRight,
  FolderOpened,
  Plus
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const appStore = useAppStore()

const showAddProductDialog = ref(false)
const newProductForm = ref({
  name: '',
  description: ''
})

function handleViewChange(view) {
  appStore.setCurrentView(view)
}

function handleProductClick(product) {
  appStore.setCurrentProduct(product)
}

function handleAddProduct() {
  showAddProductDialog.value = true
  newProductForm.value = {
    name: '',
    description: ''
  }
}

function submitNewProduct() {
  if (!newProductForm.value.name.trim()) {
    ElMessage.warning('请输入产品名称')
    return
  }

  const product = {
    id: Date.now(),
    name: newProductForm.value.name,
    description: newProductForm.value.description,
    searchCount: 0,
    createdAt: new Date().toISOString()
  }

  appStore.addProduct(product)
  ElMessage.success('产品创建成功')
  showAddProductDialog.value = false

  // 自动切换到该产品详情页
  appStore.setCurrentProduct(product)
  appStore.setCurrentView('product-manage')
}
</script>

<style scoped>
.sidebar {
  width: 220px;
  height: 100%;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width 0.3s ease;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
}

.sidebar.collapsed {
  width: 70px;
}

.collapse-btn {
  position: absolute;
  right: -12px;
  top: 20px;
  width: 24px;
  height: 24px;
  background: #6366f1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
}

.collapse-btn:hover {
  background: #4f46e5;
  transform: scale(1.1);
}

.collapse-btn .el-icon {
  color: white;
  font-size: 14px;
}

.menu-list {
  flex: 1;
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  margin: 4px 12px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s;
  color: rgba(255, 255, 255, 0.7);
  position: relative;
}

.sidebar.collapsed .menu-item {
  justify-content: center;
  padding: 14px 0;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.menu-item.active {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.menu-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.menu-content {
  display: flex;
  align-items: center;
  margin-left: 12px;
  flex: 1;
  min-width: 0;
}

.menu-label {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}

.menu-badge {
  margin-left: 8px;
}

.menu-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 8px 20px;
}

.product-submenu {
  margin-left: 52px;
  margin-right: 12px;
  margin-top: 8px;
  margin-bottom: 8px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.product-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  cursor: pointer;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  transition: all 0.2s;
}

.product-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.product-item.active {
  background: rgba(99, 102, 241, 0.3);
  color: white;
}

.product-item .el-icon {
  font-size: 16px;
  margin-right: 8px;
}

.product-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-badge {
  margin-left: 8px;
}

.add-product-btn {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-top: 4px;
  cursor: pointer;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  border: 1px dashed rgba(255, 255, 255, 0.3);
  transition: all 0.2s;
}

.add-product-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 255, 255, 0.5);
}

.add-product-btn .el-icon {
  font-size: 16px;
  margin-right: 6px;
}

.spacer {
  flex: 1;
}

/* 过渡动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
