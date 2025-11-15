import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  // 侧边栏状态
  const sidebarCollapsed = ref(false)
  const currentView = ref('current-work') // 'product-manage' | 'current-work' | 'history' | 'settings'

  // 产品相关
  const products = ref([])
  const currentProduct = ref(null)
  const currentKeyword = ref('')

  // 笔记相关
  const notes = ref([])
  const selectedNotes = ref([])
  const currentNote = ref(null)

  // 词汇分析
  const emotionWords = ref([])
  const sceneWords = ref([])

  // AI创作
  const aiMode = ref('rewrite') // 'rewrite' | 'content'
  const rewrites = ref([])
  const contents = ref([])

  // 历史记录
  const historyList = ref([])
  const currentHistory = ref(null)

  // 计算属性
  const selectedNoteCount = computed(() => selectedNotes.value.length)

  // 方法
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setCurrentView(view) {
    currentView.value = view
  }

  function setCurrentProduct(product) {
    currentProduct.value = product
  }

  function addProduct(product) {
    products.value.push(product)
  }

  function removeProduct(productId) {
    const index = products.value.findIndex(p => p.id === productId)
    if (index !== -1) {
      products.value.splice(index, 1)
    }
  }

  function setNotes(noteList) {
    notes.value = noteList
    selectedNotes.value = []
  }

  function toggleNoteSelection(note) {
    const index = selectedNotes.value.findIndex(n => n.id === note.id)
    if (index === -1) {
      selectedNotes.value.push(note)
    } else {
      selectedNotes.value.splice(index, 1)
    }
  }

  function selectAllNotes() {
    selectedNotes.value = [...notes.value]
  }

  function clearNoteSelection() {
    selectedNotes.value = []
  }

  function setCurrentNote(note) {
    currentNote.value = note
  }

  function addEmotionWord(word) {
    if (!emotionWords.value.includes(word)) {
      emotionWords.value.push(word)
    }
  }

  function removeEmotionWord(word) {
    const index = emotionWords.value.indexOf(word)
    if (index !== -1) {
      emotionWords.value.splice(index, 1)
    }
  }

  function addSceneWord(word) {
    if (!sceneWords.value.includes(word)) {
      sceneWords.value.push(word)
    }
  }

  function removeSceneWord(word) {
    const index = sceneWords.value.indexOf(word)
    if (index !== -1) {
      sceneWords.value.splice(index, 1)
    }
  }

  function setAIMode(mode) {
    aiMode.value = mode
  }

  function addRewrite(rewrite) {
    rewrites.value.push(rewrite)
  }

  function addContent(content) {
    contents.value.push(content)
  }

  return {
    // state
    sidebarCollapsed,
    currentView,
    products,
    currentProduct,
    currentKeyword,
    notes,
    selectedNotes,
    currentNote,
    emotionWords,
    sceneWords,
    aiMode,
    rewrites,
    contents,
    historyList,
    currentHistory,

    // computed
    selectedNoteCount,

    // actions
    toggleSidebar,
    setCurrentView,
    setCurrentProduct,
    addProduct,
    removeProduct,
    setNotes,
    toggleNoteSelection,
    selectAllNotes,
    clearNoteSelection,
    setCurrentNote,
    addEmotionWord,
    removeEmotionWord,
    addSceneWord,
    removeSceneWord,
    setAIMode,
    addRewrite,
    addContent,
  }
})
