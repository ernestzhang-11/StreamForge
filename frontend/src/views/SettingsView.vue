<template>
  <div class="settings-view">
    <div class="page-header">
      <h2>⚙️ 系统设置</h2>
    </div>

    <div class="settings-content">
      <!-- API 配置 -->
      <el-card shadow="hover" class="settings-section">
        <template #header>
          <div class="section-header">
            <el-icon><Key /></el-icon>
            <span>API 配置</span>
          </div>
        </template>

        <el-form label-width="120px">
          <el-form-item label="GPT API Key">
            <el-input
              v-model="settings.gptApiKey"
              type="password"
              placeholder="sk-..."
              show-password
            >
              <template #append>
                <el-button :icon="Connection" @click="testConnection('gpt')">
                  测试连接
                </el-button>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="Claude API Key">
            <el-input
              v-model="settings.claudeApiKey"
              type="password"
              placeholder="sk-ant-..."
              show-password
            >
              <template #append>
                <el-button :icon="Connection" @click="testConnection('claude')">
                  测试连接
                </el-button>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="Gemini API Key">
            <el-input
              v-model="settings.geminiApiKey"
              type="password"
              placeholder="AIzaSy..."
              show-password
            >
              <template #append>
                <el-button :icon="Connection" @click="testConnection('gemini')">
                  测试连接
                </el-button>
              </template>
            </el-input>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Prompt 模板管理 -->
      <el-card shadow="hover" class="settings-section">
        <template #header>
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <span>Prompt 模板管理</span>
          </div>
        </template>

        <el-form label-width="120px">
          <el-form-item label="标题仿写模板">
            <el-select v-model="settings.rewriteTemplate" style="width: 100%">
              <el-option label="小红书种草风格" value="xiaohongshu" />
              <el-option label="电商推广风格" value="ecommerce" />
            </el-select>
            <el-button
              style="margin-top: 8px"
              size="small"
              :icon="Plus"
              @click="handleAddTemplate('rewrite')"
            >
              新建模板
            </el-button>
          </el-form-item>

          <el-form-item label="正文创作模板">
            <el-select v-model="settings.contentTemplate" style="width: 100%">
              <el-option label="小红书爆款正文" value="xiaohongshu" />
              <el-option label="产品详情页" value="product" />
            </el-select>
            <el-button
              style="margin-top: 8px"
              size="small"
              :icon="Plus"
              @click="handleAddTemplate('content')"
            >
              新建模板
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 界面设置 -->
      <el-card shadow="hover" class="settings-section">
        <template #header>
          <div class="section-header">
            <el-icon><Monitor /></el-icon>
            <span>界面设置</span>
          </div>
        </template>

        <el-form label-width="120px">
          <el-form-item label="主题">
            <el-radio-group v-model="settings.theme">
              <el-radio label="light">明亮</el-radio>
              <el-radio label="dark">暗黑</el-radio>
              <el-radio label="auto">自动</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="字体大小">
            <el-radio-group v-model="settings.fontSize">
              <el-radio label="small">小</el-radio>
              <el-radio label="medium">中</el-radio>
              <el-radio label="large">大</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 数据管理 -->
      <el-card shadow="hover" class="settings-section">
        <template #header>
          <div class="section-header">
            <el-icon><FolderOpened /></el-icon>
            <span>数据管理</span>
          </div>
        </template>

        <div class="data-actions">
          <el-button :icon="Download" @click="handleExportData">
            导出数据库
          </el-button>
          <el-button :icon="Upload" @click="handleImportData">
            导入数据库
          </el-button>
          <el-button type="warning" :icon="Delete" @click="handleClearHistory">
            清空历史
          </el-button>
          <el-button type="danger" :icon="RefreshLeft" @click="handleResetSettings">
            重置设置
          </el-button>
        </div>
      </el-card>

      <!-- 关于 -->
      <el-card shadow="hover" class="settings-section">
        <template #header>
          <div class="section-header">
            <el-icon><InfoFilled /></el-icon>
            <span>关于</span>
          </div>
        </template>

        <div class="about-info">
          <div class="about-item">
            <strong>应用名称：</strong>
            <span>电商内容工厂 Agent</span>
          </div>
          <div class="about-item">
            <strong>版本号：</strong>
            <span>v1.0.0</span>
          </div>
          <div class="about-item">
            <strong>开发者：</strong>
            <span>Claude & Human</span>
          </div>
        </div>
      </el-card>

      <!-- 保存按钮 -->
      <div class="save-actions">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :icon="Check" @click="handleSaveSettings">
          保存设置
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  Key,
  Connection,
  Document,
  Plus,
  Monitor,
  FolderOpened,
  Download,
  Upload,
  Delete,
  RefreshLeft,
  InfoFilled,
  Check
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const settings = ref({
  gptApiKey: '',
  claudeApiKey: '',
  geminiApiKey: '',
  rewriteTemplate: 'xiaohongshu',
  contentTemplate: 'xiaohongshu',
  theme: 'light',
  fontSize: 'medium'
})

function testConnection(provider) {
  ElMessage.info(`正在测试 ${provider.toUpperCase()} 连接...`)
  // TODO: 实际调用API测试
  setTimeout(() => {
    ElMessage.success(`${provider.toUpperCase()} 连接成功`)
  }, 1000)
}

function handleAddTemplate(type) {
  ElMessage.info(`新建${type === 'rewrite' ? '标题仿写' : '正文创作'}模板功能开发中...`)
}

function handleExportData() {
  ElMessage.success('数据导出成功')
}

function handleImportData() {
  ElMessage.info('请选择要导入的数据文件')
}

function handleClearHistory() {
  ElMessageBox.confirm(
    '此操作将清空所有历史记录，是否继续？',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    ElMessage.success('历史记录已清空')
  }).catch(() => {})
}

function handleResetSettings() {
  ElMessageBox.confirm(
    '此操作将重置所有设置为默认值，是否继续？',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    settings.value = {
      gptApiKey: '',
      claudeApiKey: '',
      geminiApiKey: '',
      rewriteTemplate: 'xiaohongshu',
      contentTemplate: 'xiaohongshu',
      theme: 'light',
      fontSize: 'medium'
    }
    ElMessage.success('设置已重置')
  }).catch(() => {})
}

function handleSaveSettings() {
  // TODO: 保存设置到后端
  ElMessage.success('设置保存成功')
}

function handleCancel() {
  ElMessage.info('已取消')
}
</script>

<style scoped>
.settings-view {
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

.settings-content {
  max-width: 800px;
}

.settings-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
}

.data-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.about-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.about-item {
  display: flex;
  gap: 12px;
  font-size: 14px;
}

.about-item strong {
  color: #606266;
  min-width: 100px;
}

.about-item span {
  color: #303133;
}

.save-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid #e4e7ed;
}
</style>
