<template>
  <div class="ai-creation">
    <div class="creation-header">
      <h4>第三步：内容创作</h4>
      <el-radio-group v-model="appStore.aiMode" size="small">
        <el-radio-button value="rewrite">标题仿写</el-radio-button>
        <el-radio-button value="content">正文创作</el-radio-button>
      </el-radio-group>
    </div>

    <div class="creation-body">
      <!-- 未选择笔记时的提示 -->
      <div v-if="!appStore.currentNote" class="empty-state">
        <el-empty description="请从左侧选择笔记开始创作">
          <template #image>
            <el-icon :size="100" color="#c0c4cc">
              <EditPen />
            </el-icon>
          </template>
        </el-empty>
      </div>

      <!-- 标题仿写模式 -->
      <div v-else-if="appStore.aiMode === 'rewrite'" class="rewrite-panel">
        <el-scrollbar height="calc(100vh - 240px)">
          <!-- 原始标题 -->
          <div class="section">
            <div class="section-title">
              <el-icon><DocumentCopy /></el-icon>
              <span>原始标题</span>
            </div>
            <div class="original-title">
              <p class="title-text">{{ appStore.currentNote.title }}</p>
              <div class="title-meta">
                <span>作者: {{ appStore.currentNote.author }}</span>
                <span>💗 {{ formatNumber(appStore.currentNote.likes) }}</span>
              </div>
            </div>
          </div>

          <!-- AI配置 -->
          <div class="section">
            <div class="section-title">
              <el-icon><Setting /></el-icon>
              <span>AI 配置</span>
            </div>
            <el-form label-width="100px">
              <el-form-item label="选择模型">
                <el-checkbox-group v-model="selectedModels">
                  <el-checkbox label="gpt">GPT-4o</el-checkbox>
                  <el-checkbox label="claude">Claude Sonnet</el-checkbox>
                  <el-checkbox label="gemini">Gemini Pro</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
              <el-form-item label="Prompt设置">
                <el-select v-model="promptTemplate" style="width: 100%">
                  <el-option label="小红书种草风格" value="xiaohongshu" />
                  <el-option label="电商推广风格" value="ecommerce" />
                  <el-option label="自定义" value="custom" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="promptTemplate === 'custom'" label="">
                <el-input
                  v-model="customPrompt"
                  type="textarea"
                  :rows="4"
                  placeholder="输入自定义 Prompt..."
                />
              </el-form-item>
            </el-form>
            <el-button
              type="primary"
              :loading="generating"
              :icon="MagicStick"
              style="width: 100%"
              @click="handleGenerate"
            >
              开始生成
            </el-button>
          </div>

          <!-- 生成结果 -->
          <div v-if="rewriteResults.length > 0" class="section">
            <div class="section-title">
              <el-icon><List /></el-icon>
              <span>生成结果</span>
              <el-text type="info" size="small">
                生成时间: {{ new Date().toLocaleString() }}
              </el-text>
            </div>
            <div
              v-for="(result, index) in rewriteResults"
              :key="index"
              class="result-card"
            >
              <div class="result-header">
                <el-tag :type="getModelTagType(result.model)">
                  {{ getModelName(result.model) }}
                </el-tag>
              </div>
              <div class="result-content">
                {{ result.text }}
              </div>
              <div class="result-actions">
                <el-button size="small" :icon="CopyDocument" @click="copyText(result.text)">
                  复制
                </el-button>
                <el-button size="small" type="success" :icon="Check" @click="adoptRewrite(result)">
                  采用
                </el-button>
                <el-button size="small" :icon="Refresh" @click="regenerate(result.model)">
                  重生成
                </el-button>
              </div>
            </div>
          </div>
        </el-scrollbar>
      </div>

      <!-- 正文创作模式 -->
      <div v-else-if="appStore.aiMode === 'content'" class="content-panel">
        <el-scrollbar height="calc(100vh - 240px)">
          <!-- 选定标题 -->
          <div class="section">
            <div class="section-title">
              <el-icon><Flag /></el-icon>
              <span>选定标题</span>
            </div>
            <div class="selected-title">
              {{ appStore.currentNote.title }}
            </div>
          </div>

          <!-- 参考原文 -->
          <div class="section">
            <div class="section-title">
              <el-icon><Document /></el-icon>
              <span>参考原文</span>
              <el-button
                text
                size="small"
                @click="showOriginalContent = !showOriginalContent"
              >
                {{ showOriginalContent ? '收起' : '展开' }}
              </el-button>
            </div>
            <el-collapse-transition>
              <div v-show="showOriginalContent" class="original-content">
                {{ appStore.currentNote.content || '暂无原文内容' }}
              </div>
            </el-collapse-transition>
          </div>

          <!-- AI配置 -->
          <div class="section">
            <div class="section-title">
              <el-icon><Setting /></el-icon>
              <span>AI 配置</span>
            </div>
            <el-form label-width="100px">
              <el-form-item label="选择模型">
                <el-radio-group v-model="contentModel">
                  <el-radio label="gpt">GPT-4o</el-radio>
                  <el-radio label="claude">Claude Sonnet</el-radio>
                  <el-radio label="gemini">Gemini Pro</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="Prompt设置">
                <el-select v-model="contentPromptTemplate" style="width: 100%">
                  <el-option label="小红书爆款正文" value="xiaohongshu" />
                  <el-option label="产品详情页" value="product" />
                  <el-option label="自定义" value="custom" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="contentPromptTemplate === 'custom'" label="">
                <el-input
                  v-model="customContentPrompt"
                  type="textarea"
                  :rows="4"
                  placeholder="输入自定义 Prompt..."
                />
              </el-form-item>
              <el-form-item label="字数要求">
                <el-slider
                  v-model="wordCountRange"
                  range
                  :min="100"
                  :max="1000"
                  :step="50"
                  :marks="{ 300: '300', 500: '500', 800: '800' }"
                  style="width: 100%"
                />
                <div class="word-count-display">
                  {{ wordCountRange[0] }} - {{ wordCountRange[1] }} 字
                </div>
              </el-form-item>
            </el-form>
            <el-button
              type="primary"
              :loading="generatingContent"
              :icon="MagicStick"
              style="width: 100%"
              @click="handleGenerateContent"
            >
              生成正文
            </el-button>
          </div>

          <!-- 生成的正文 -->
          <div v-if="generatedContent" class="section">
            <div class="section-title">
              <el-icon><Notebook /></el-icon>
              <span>生成的正文</span>
              <el-button
                text
                size="small"
                :icon="editMode ? Check : Edit"
                @click="editMode = !editMode"
              >
                {{ editMode ? '完成编辑' : '编辑模式' }}
              </el-button>
            </div>
            <el-input
              v-if="editMode"
              v-model="generatedContent"
              type="textarea"
              :rows="12"
              placeholder="编辑正文内容..."
            />
            <div v-else class="generated-content-display">
              {{ generatedContent }}
            </div>
            <div class="content-stats">
              字数统计: {{ generatedContent.length }} / {{ wordCountRange[1] }}
            </div>
            <div class="content-actions">
              <el-button :icon="CopyDocument" @click="copyText(generatedContent)">
                复制全文
              </el-button>
              <el-button type="warning" :icon="MagicStick" @click="handlePolish">
                AI 润色
              </el-button>
              <el-button :icon="Refresh" @click="handleGenerateContent">
                重新生成
              </el-button>
              <el-button type="success" :icon="DocumentAdd" @click="saveDraft">
                保存草稿
              </el-button>
            </div>
          </div>
        </el-scrollbar>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  EditPen,
  DocumentCopy,
  Setting,
  MagicStick,
  List,
  CopyDocument,
  Check,
  Refresh,
  Flag,
  Document,
  Notebook,
  Edit,
  DocumentAdd
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

// 仿写相关
const selectedModels = ref(['gpt', 'claude', 'gemini'])
const promptTemplate = ref('xiaohongshu')
const customPrompt = ref('')
const generating = ref(false)
const rewriteResults = ref([])

// 正文创作相关
const contentModel = ref('gpt')
const contentPromptTemplate = ref('xiaohongshu')
const customContentPrompt = ref('')
const wordCountRange = ref([300, 500])
const generatingContent = ref(false)
const generatedContent = ref('')
const editMode = ref(false)
const showOriginalContent = ref(false)

function formatNumber(num) {
  if (num >= 10000) return (num / 10000).toFixed(1) + 'w'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
  return num
}

function getModelName(model) {
  const names = {
    gpt: 'GPT-4o',
    claude: 'Claude Sonnet',
    gemini: 'Gemini Pro'
  }
  return names[model] || model
}

function getModelTagType(model) {
  const types = {
    gpt: 'success',
    claude: 'warning',
    gemini: 'primary'
  }
  return types[model] || 'info'
}

async function handleGenerate() {
  if (selectedModels.value.length === 0) {
    ElMessage.warning('请至少选择一个模型')
    return
  }

  generating.value = true
  rewriteResults.value = []

  try {
    // TODO: 调用后端API
    await new Promise(resolve => setTimeout(resolve, 2000))

    // 模拟结果
    const mockResults = selectedModels.value.map(model => ({
      model,
      text: `【${getModelName(model)}生成】${generateMockRewrite()}`
    }))

    rewriteResults.value = mockResults
    ElMessage.success('生成成功')
  } catch (error) {
    ElMessage.error('生成失败：' + error.message)
  } finally {
    generating.value = false
  }
}

function generateMockRewrite() {
  const templates = [
    '必入！这款精华真的惊艳到我了',
    '姐妹们冲！这个产品我要吹爆',
    '真香警告！用过就回不去了',
    '绝了！这才是真正的宝藏好物'
  ]
  return templates[Math.floor(Math.random() * templates.length)]
}

async function handleGenerateContent() {
  generatingContent.value = true

  try {
    await new Promise(resolve => setTimeout(resolve, 2000))

    generatedContent.value = `姐妹们！今天要给你们分享一个让我惊艳到的宝藏产品！

【使用感受】
说实话，入手之前我也是抱着试试看的心态。但用了一周之后，我必须站出来给它正名！

质地很清爽，完全不会油腻，上脸吸收超快。每次洗完脸后用它，第二天起来皮肤明显更透亮了。

【产品亮点】
1. 成分安全，敏感肌也能用
2. 性价比超高，学生党也能冲
3. 效果明显，坚持用真的有改善

【使用建议】
建议早晚各用一次，配合按摩效果更好。记得要坚持用哦，护肤是个长期的过程~

有同样困扰的姐妹可以冲了！评论区聊聊你们用过哪些好用的产品呀～`

    ElMessage.success('生成成功')
  } catch (error) {
    ElMessage.error('生成失败：' + error.message)
  } finally {
    generatingContent.value = false
  }
}

async function handlePolish() {
  ElMessage.info('AI 润色功能开发中...')
}

function copyText(text) {
  navigator.clipboard.writeText(text)
  ElMessage.success('复制成功')
}

function adoptRewrite(result) {
  ElMessage.success('已采用该标题')
  appStore.addRewrite(result)
}

function regenerate(model) {
  ElMessage.info(`正在重新生成 ${getModelName(model)} 的结果...`)
}

function saveDraft() {
  appStore.addContent({
    title: appStore.currentNote.title,
    content: generatedContent.value,
    model: contentModel.value,
    createdAt: new Date().toISOString()
  })
  ElMessage.success('草稿保存成功')
}
</script>

<style scoped>
.ai-creation {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.creation-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.creation-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.creation-body {
  flex: 1;
  overflow: hidden;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rewrite-panel,
.content-panel {
  height: 100%;
  padding: 16px;
}

.section {
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.section-title .el-icon {
  color: #409eff;
}

.original-title {
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.title-text {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 8px 0;
}

.title-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.result-card {
  padding: 16px;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 12px;
}

.result-header {
  margin-bottom: 12px;
}

.result-content {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  margin-bottom: 12px;
}

.result-actions {
  display: flex;
  gap: 8px;
}

.selected-title {
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.original-content {
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  font-size: 13px;
  line-height: 1.8;
  color: #606266;
  max-height: 200px;
  overflow-y: auto;
}

.word-count-display {
  text-align: center;
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.generated-content-display {
  padding: 16px;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  margin-bottom: 12px;
}

.content-stats {
  text-align: right;
  font-size: 12px;
  color: #909399;
  margin-bottom: 12px;
}

.content-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
