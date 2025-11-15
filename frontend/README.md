# 电商内容工厂 Agent - 前端

基于 Vue 3 + Element Plus 构建的现代化内容创作工具前端界面。

## 功能特性

- 🎨 **现代化UI设计** - 基于 Element Plus 的精美界面
- 📦 **产品管理** - 支持多产品、多关键词管理
- 🔍 **智能抓取** - 小红书笔记批量采集
- 📝 **AI 创作** - 支持 GPT、Claude、Gemini 多模型
- 🎯 **标题仿写** - 一键生成多个仿写版本
- ✍️ **正文创作** - AI 辅助内容创作和润色
- 📊 **词汇分析** - 自动提取情绪词和场景词
- 📚 **历史管理** - 完整的工作历史记录

## 技术栈

- Vue 3.4
- Element Plus 2.5
- Pinia 2.1 (状态管理)
- Axios (HTTP 客户端)
- Vite 5.0 (构建工具)

## 快速开始

### 安装依赖

\`\`\`bash
cd frontend
npm install
\`\`\`

### 开发模式

\`\`\`bash
npm run dev
\`\`\`

访问 http://localhost:3000

### 生产构建

\`\`\`bash
npm run build
\`\`\`

构建产物输出到 `dist` 目录。

### 预览构建

\`\`\`bash
npm run preview
\`\`\`

## 项目结构

\`\`\`
frontend/
├── public/               # 静态资源
├── src/
│   ├── assets/          # 资源文件
│   ├── components/      # 通用组件
│   │   ├── Sidebar.vue           # 侧边栏导航
│   │   ├── CrawlPanel.vue        # 抓取控制面板
│   │   ├── NoteList.vue          # 笔记列表
│   │   ├── WordAnalysis.vue      # 词汇分析
│   │   └── AICreation.vue        # AI创作面板
│   ├── views/           # 页面视图
│   │   ├── CurrentWork.vue       # 当前工作视图
│   │   ├── ProductManage.vue     # 产品管理视图
│   │   ├── HistoryView.vue       # 历史记录视图
│   │   └── SettingsView.vue      # 设置视图
│   ├── stores/          # Pinia 状态管理
│   │   └── app.js       # 主应用 Store
│   ├── styles/          # 全局样式
│   │   └── main.css     # 主样式文件
│   ├── App.vue          # 根组件
│   └── main.js          # 入口文件
├── index.html           # HTML 模板
├── vite.config.js       # Vite 配置
└── package.json         # 项目配置
\`\`\`

## 配置说明

### 后端 API 代理

在 `vite.config.js` 中配置后端 API 代理：

\`\`\`javascript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:5000',  // 后端服务地址
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
\`\`\`

### 环境变量

创建 `.env` 文件配置环境变量：

\`\`\`
VITE_API_BASE_URL=http://localhost:5000
\`\`\`

## 主要功能模块

### 1. 产品管理

- 创建/编辑/删除产品
- 查看产品统计数据
- 管理产品下的搜索关键词

### 2. 笔记抓取

- 输入关键词批量抓取小红书笔记
- 设置抓取数量
- 自动提取笔记信息（标题、作者、点赞数等）

### 3. 词汇分析

- 自动分析笔记标题中的情绪词和场景词
- 支持手动添加/删除词汇
- 词库导出功能

### 4. AI 创作

#### 标题仿写
- 支持多模型同时生成（GPT、Claude、Gemini）
- 自定义 Prompt 模板
- 一键复制/采用/重生成

#### 正文创作
- 参考原文创作新内容
- 字数范围控制
- AI 润色功能
- 草稿保存

### 5. 历史记录

- 按日期分组展示
- 支持搜索和筛选
- 查看历史工作详情
- 加载历史数据到工作区

### 6. 系统设置

- API Key 配置
- Prompt 模板管理
- 界面主题设置
- 数据导入/导出

## 开发注意事项

### 状态管理

使用 Pinia 进行全局状态管理，主要状态包括：

- `currentView` - 当前视图
- `products` - 产品列表
- `notes` - 笔记列表
- `emotionWords` / `sceneWords` - 词汇库
- `currentNote` - 当前选中的笔记
- `aiMode` - AI 创作模式（rewrite/content）

### 组件通信

- 使用 Pinia store 进行跨组件状态共享
- 事件总线使用 `emit` / `on`
- Props 用于父子组件通信

### API 调用

所有 API 调用都通过 `/api` 前缀代理到后端：

\`\`\`javascript
// 示例
axios.get('/api/xhs/search_notes', {
  params: { keyword: '精华液', limit: 20 }
})
\`\`\`

## 后续开发

- [ ] 接入真实后端 API
- [ ] 添加更多 AI 模型支持
- [ ] 实现数据持久化
- [ ] 添加用户认证
- [ ] 优化移动端适配
- [ ] 添加数据可视化图表

## 许可证

MIT
