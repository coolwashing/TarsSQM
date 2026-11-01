<template>
  <div class="db-studio-container">
    <!-- 左侧数据表导航面板 -->
    <aside class="tables-side-pane">
      <div class="side-pane-header">
        <div class="side-title-row">
          <div class="side-title">
            <el-icon class="mr-1 text-primary"><Coin /></el-icon>
            <span>数据表清单</span>
          </div>
          <el-badge :value="filteredTables.length" type="primary" class="table-count-badge" />
        </div>
        <div class="search-box">
          <el-input
            v-model="tableSearchQuery"
            placeholder="搜索物理表名 / 中文别名..."
            clearable
            :prefix-icon="Search"
            size="small"
          />
        </div>
      </div>

      <el-scrollbar class="tables-scroll-list">
        <div v-if="loadingTables" class="loading-state">
          <el-skeleton :rows="6" animated />
        </div>
        <div v-else-if="filteredTables.length === 0" class="empty-state">
          <el-empty description="未找到匹配的数据表" :image-size="60" />
        </div>
        <div v-else class="tables-list">
          <div
            v-for="tbl in filteredTables"
            :key="tbl.table_name"
            class="table-item-card"
            :class="{ active: currentTable?.table_name === tbl.table_name }"
            @click="handleSelectTable(tbl)"
          >
            <div class="table-card-main">
              <div class="table-icon">
                <el-icon><Tickets /></el-icon>
              </div>
              <div class="table-info">
                <el-tooltip :content="getTableCommentFull(tbl)" placement="top" :show-after="500">
                  <div class="table-name-text">{{ getTableDisplayName(tbl) }}</div>
                </el-tooltip>
                <el-tooltip :content="`物理表名: ${tbl.table_name}`" placement="bottom" :show-after="500">
                  <div class="table-desc-text">{{ tbl.table_name }}</div>
                </el-tooltip>
              </div>
            </div>
            <div class="table-card-meta">
              <span class="row-count-pill" :class="{ 'has-rows': (tbl.real_count ?? tbl.table_rows) > 0 }">
                {{ tbl.real_count ?? tbl.table_rows }} 行
              </span>
            </div>
          </div>
        </div>
      </el-scrollbar>
    </aside>

    <!-- 右侧主体工作台 -->
    <main class="workbench-main">
      <div v-if="!currentTable" class="workbench-empty">
        <el-empty description="请在左侧选择一张数据表查看字典与数据记录" />
      </div>

      <div v-else class="workbench-content">
        <!-- 顶部信息与全局操作条 -->
        <header class="table-detail-header">
          <div class="header-left">
            <div class="table-title-row">
              <el-tooltip
                v-if="currentTable.comment"
                :content="currentTable.comment"
                placement="bottom-start"
                :show-after="500"
              >
                <h2 class="active-table-name">{{ currentTable.table_name }}</h2>
              </el-tooltip>
              <h2 v-else class="active-table-name">{{ currentTable.table_name }}</h2>

              <span class="table-row-count-pill">
                {{ currentTable.real_count ?? currentTable.table_rows }} 条数据
              </span>

              <el-tooltip placement="top" :show-after="500">
                <template #content>
                  <div class="meta-tooltip-box">
                    <div v-if="currentTable.comment" class="meta-tip-row">
                      <span class="meta-tip-label">业务释义：</span>
                      <span>{{ currentTable.comment }}</span>
                    </div>
                    <div class="meta-tip-row">
                      <span class="meta-tip-label">物理引擎：</span>
                      <span>{{ currentTable.engine || 'InnoDB' }}</span>
                    </div>
                    <div class="meta-tip-row">
                      <span class="meta-tip-label">存储空间：</span>
                      <span>{{ currentTable.data_length_kb }} KB</span>
                    </div>
                    <div v-if="currentTable.create_time" class="meta-tip-row">
                      <span class="meta-tip-label">创建时间：</span>
                      <span>{{ currentTable.create_time }}</span>
                    </div>
                  </div>
                </template>
                <el-icon class="meta-info-trigger"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
          </div>

          <div class="header-right">
            <el-button
              type="primary"
              plain
              @click="handleOpenScaffolder"
              title="根据当前物理表字典一键推断并生成 Element-Plus 表格/表单代码 (Alt+S)"
            >
              🛠️ 生成页面代码 (Alt+S)
            </el-button>
            <el-button
              type="primary"
              :icon="Plus"
              v-if="activeTab === 'data'"
              @click="handleOpenCreateRowDialog"
            >
              新增数据记录
            </el-button>
            <el-tooltip content="刷新当前数据" placement="top" :show-after="500">
              <el-button :icon="Refresh" @click="handleRefreshCurrent">
                刷新
              </el-button>
            </el-tooltip>
            <el-tooltip :content="dbConnected ? '数据库连接与异机密码配置' : '数据库未连接，点击配置连接参数'" placement="top" :show-after="500">
              <el-button :icon="Setting" :type="dbConnected ? 'default' : 'danger'" @click="handleOpenDbConfig">
                连接设置
              </el-button>
            </el-tooltip>
          </div>
        </header>

        <!-- 双 Tab 切换区 -->
        <div class="tabs-wrapper">
          <el-tabs v-model="activeTab" class="workbench-tabs" @tab-change="handleTabChange">
            <!-- Tab 1: 数据字典 -->
            <el-tab-pane label="数据字典" name="columns">
              <div class="columns-pane-content">

                <el-table
                  v-loading="loadingColumns"
                  :data="columnsData"
                  border
                  stripe
                  class="dict-table"
                  height="100%"
                >
                  <el-table-column type="index" label="序号" width="60" align="center" />
                  <el-table-column prop="column_name" label="字段物理名" min-width="180">
                    <template #default="{ row }">
                      <div class="col-name-cell">
                        <span class="col-name-text">{{ row.column_name }}</span>
                        <el-tag v-if="row.is_primary" size="small" type="danger" effect="plain" class="pk-tag">
                          🔑 主键
                        </el-tag>
                      </div>
                    </template>
                  </el-table-column>

                  <el-table-column prop="column_comment" min-width="260">
                    <template #header>
                      <div class="comment-col-header">
                        <span>业务注释</span>
                        <el-tooltip content="双击单元格或点击编辑图标，可直接就地修改物理字段的字典释义" placement="top" :show-after="500">
                          <el-icon class="header-tip-icon"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </div>
                    </template>
                    <template #default="{ row }">
                      <div class="comment-edit-cell" @dblclick="handleStartEditComment(row)">
                        <template v-if="editingColComment && editingColComment.column_name === row.column_name">
                          <el-input
                            v-model="editingColComment.tempComment"
                            size="small"
                            placeholder="输入业务释义，回车或失焦保存"
                            autofocus
                            @blur="handleSaveColumnComment(row)"
                            @keyup.enter="handleSaveColumnComment(row)"
                            @keyup.esc="editingColComment = null"
                          />
                        </template>
                        <template v-else>
                          <span class="comment-text" :class="{ 'no-comment': !row.column_comment }">
                            {{ row.column_comment || '（暂无注释，双击补充）' }}
                          </span>
                          <el-button
                            link
                            type="primary"
                            :icon="Edit"
                            size="small"
                            class="edit-comment-btn"
                            @click.stop="handleStartEditComment(row)"
                          />
                        </template>
                      </div>
                    </template>
                  </el-table-column>

                  <el-table-column prop="column_type" label="数据类型" width="160">
                    <template #default="{ row }">
                      <el-tag size="small" type="info" effect="light" class="type-tag">
                        {{ row.column_type }}
                      </el-tag>
                    </template>
                  </el-table-column>

                  <el-table-column prop="is_nullable" label="允许为空" width="95" align="center">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.is_nullable ? 'success' : 'warning'" effect="plain">
                        {{ row.is_nullable ? '是' : '否' }}
                      </el-tag>
                    </template>
                  </el-table-column>

                  <el-table-column prop="column_default" label="默认值" width="130" align="center">
                    <template #default="{ row }">
                      <code class="default-val">{{ row.column_default !== null ? row.column_default : '-' }}</code>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>

            <!-- Tab 2: 真实物理数据浏览与编辑 (接入项目标准 DataTable 组件) -->
            <el-tab-pane label="数据记录" name="data">
              <div class="data-pane-content">
                <DataTable
                  :columns="dynamicTableColumns"
                  :data="rowsData"
                  :loading="loadingRows"
                  :pagination="pagination"
                  @refresh="fetchRows"
                  @page-change="handlePageChange"
                  @size-change="handleSizeChange"
                  @cell-change="handleCellChange"
                >
                  <!-- 顶部搜索 -->
                  <template #search>
                    <div class="rows-search-bar">
                      <el-input
                        v-model="searchKeyword"
                        placeholder="在当前表中检索任意字段内容..."
                        clearable
                        :prefix-icon="Search"
                        style="width: 320px;"
                        @keyup.enter="handleSearchRows"
                        @clear="handleSearchRows"
                      />
                      <el-button type="primary" :icon="Search" @click="handleSearchRows">查询</el-button>
                      <el-button :icon="Refresh" @click="handleResetSearchRows">重置</el-button>
                    </div>
                  </template>

                  <!-- 行操作插槽 -->
                  <template #action="{ row }">
                    <div class="row-actions-group">
                      <el-button
                        link
                        type="primary"
                        :icon="Edit"
                        size="small"
                        @click="handleOpenEditRowDialog(row)"
                      >
                        编辑
                      </el-button>
                      <el-button
                        link
                        type="danger"
                        :icon="Delete"
                        size="small"
                        @click="handleDeleteRow(row)"
                      >
                        删除
                      </el-button>
                    </div>
                  </template>
                </DataTable>
              </div>
            </el-tab-pane>

            <!-- Tab 3: 数据表架构设计与业务规约 (基于 data/table_docs/*.json 与 Tiptap 富文本) -->
            <el-tab-pane label="架构设计" name="docs">
              <div class="docs-pane-content" v-loading="loadingDoc">
                <div class="docs-toolbar">
                  <div class="docs-toolbar-left">
                    <el-tag size="small" type="primary" effect="plain" class="doc-badge">
                      {{ tableDoc.business_module || '架构设计规范' }}
                    </el-tag>
                    <el-tooltip
                      :content="`持久化配置文件：data/table_docs/${currentTable?.table_name}.json (支持离线直接编辑)`"
                      placement="top"
                      :show-after="500"
                    >
                      <span class="doc-storage-pill">
                        <el-icon class="storage-icon"><Document /></el-icon>
                        <span>JSON</span>
                      </span>
                    </el-tooltip>
                    <span class="doc-sync-status" v-if="tableDoc.updated_at">
                      <span class="sync-dot"></span>
                      <span>已同步 {{ formatDocTime(tableDoc.updated_at) }}</span>
                    </span>
                  </div>

                  <div class="docs-toolbar-right">
                    <el-tooltip content="恢复系统出厂标准架构模板" placement="top" :show-after="500">
                      <el-button link type="info" size="small" :icon="RefreshLeft" @click="handleResetDoc">
                        重置模板
                      </el-button>
                    </el-tooltip>
                    <el-button
                      type="primary"
                      size="small"
                      :icon="Check"
                      :loading="savingDoc"
                      @click="handleSaveDoc"
                    >
                      保存文档
                    </el-button>
                  </div>
                </div>

                <div class="docs-editor-wrap">
                  <TiptapEditor
                    v-model="tableDocContent"
                    placeholder="在此编写该数据表的业务定位、关联关系、质量合规与维护规约..."
                    class="studio-tiptap-editor"
                    @ai-click="aiCopilotVisible = true"
                  />
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </main>

    <!-- 数据库配置向导弹窗 -->
    <DbConfigDialog ref="dbConfigDialogRef" @saved="handleDbConfigSaved" />

    <!-- AI 智写助手模态窗 (赋能数据表架构文档生成) -->
    <DocAiCopilot
      v-model="aiCopilotVisible"
      :doc-title="currentTable ? `${getTableDisplayName(currentTable)} (${currentTable.table_name}) 表架构设计` : '数据表架构设计'"
      :doc-content="tableDocContent"
      @confirm-insert="handleAiInsert"
    />

    <!-- 新增 / 编辑数据记录模态窗 -->
    <el-dialog
      v-model="rowDialogVisible"
      :title="isEditMode ? '编辑数据记录' : '新增数据记录'"
      width="680px"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div class="row-dialog-body">
        <el-form
          ref="rowFormRef"
          :model="currentRowForm"
          label-width="140px"
          label-position="right"
          class="row-modal-form"
        >
          <div
            v-for="col in editableColumns"
            :key="col.column_name"
            class="form-col-item"
          >
            <el-form-item
              :label="col.column_comment || col.column_name"
              :prop="col.column_name"
              :rules="getColValidationRules(col)"
            >
              <template #label>
                <div class="custom-form-label">
                  <span class="label-main">{{ col.column_comment || col.column_name }}</span>
                  <span class="label-sub" v-if="col.column_comment">({{ col.column_name }})</span>
                </div>
              </template>

              <!-- 布尔/TinyInt(1) -->
              <el-switch
                v-if="col.data_type === 'tinyint' && col.column_type.includes('(1)')"
                v-model="currentRowForm[col.column_name]"
              />

              <!-- 数值 -->
              <el-input-number
                v-else-if="['int', 'bigint', 'smallint', 'mediumint', 'decimal', 'float', 'double'].includes(col.data_type)"
                v-model="currentRowForm[col.column_name]"
                class="w-full"
                controls-position="right"
              />

              <!-- 日期时间 -->
              <el-date-picker
                v-else-if="col.data_type === 'datetime' || col.data_type === 'timestamp'"
                v-model="currentRowForm[col.column_name]"
                type="datetime"
                placeholder="选择日期时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                class="w-full"
              />

              <!-- 日期 -->
              <el-date-picker
                v-else-if="col.data_type === 'date'"
                v-model="currentRowForm[col.column_name]"
                type="date"
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                class="w-full"
              />

              <!-- 多行长文本 -->
              <el-input
                v-else-if="['text', 'mediumtext', 'longtext', 'json'].includes(col.data_type)"
                v-model="currentRowForm[col.column_name]"
                type="textarea"
                :rows="3"
                placeholder="请输入内容..."
              />

              <!-- 常规字符串 -->
              <el-input
                v-else
                v-model="currentRowForm[col.column_name]"
                placeholder="请输入..."
                clearable
              />
            </el-form-item>
          </div>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="rowDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="savingRow" @click="handleSaveRow">
            确认保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, watch } from 'vue'
import {
  Coin,
  Search,
  Tickets,
  Refresh,
  Setting,
  Plus,
  Edit,
  Delete,
  InfoFilled,
  QuestionFilled,
  Document,
  Check,
  RefreshLeft
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import axios from 'axios'
import DataTable from '@/components/common/DataTable/index.vue'
import type { TableColumn, CellChangeEvent } from '@/components/common/DataTable/types'
import DbConfigDialog from '@/components/dev/DbConfigDialog.vue'
import TiptapEditor from '@/components/editor/TiptapEditor.vue'
import DocAiCopilot from '@/views/4_kb/components/DocAiCopilot.vue'

// 接口类型定义
interface DbTableItem {
  table_name: string
  comment: string
  engine: string
  table_rows: number
  real_count?: number
  data_length_kb: number
  create_time?: string
}

interface DbColumnItem {
  column_name: string
  data_type: string
  column_type: string
  is_nullable: boolean
  column_default: any
  column_comment: string
  is_primary: boolean
  extra?: string
}

// 基础响应状态
const dbConnected = ref(true)
const dbConfigDialogRef = ref<InstanceType<typeof DbConfigDialog>>()

// 数据表列表
const loadingTables = ref(false)
const tablesList = ref<DbTableItem[]>([])
const tableSearchQuery = ref('')
const currentTable = ref<DbTableItem | null>(null)

// 工作区 Tab (记忆上次退出的 Tab 位置)
const savedTab = localStorage.getItem('sqm_db_studio_last_tab') as 'columns' | 'data' | 'docs' | null
const activeTab = ref<'columns' | 'data' | 'docs'>(savedTab || 'columns')

watch(activeTab, (newTab: 'columns' | 'data' | 'docs') => {
  localStorage.setItem('sqm_db_studio_last_tab', newTab)
})

// 架构设计文档状态
const loadingDoc = ref(false)
const savingDoc = ref(false)
const tableDocContent = ref('')
const tableDoc = ref<{
  table_name: string
  title?: string
  business_module?: string
  description?: string
  updated_at?: string
  author?: string
}>({ table_name: '' })

// AI 智写助手与回填逻辑
const aiCopilotVisible = ref(false)

const handleAiInsert = (payload: { html: string; mode: 'insert' | 'replace'; targetSection?: string }) => {
  if (payload.targetSection && payload.targetSection !== 'ALL') {
    const headingClean = payload.targetSection.replace(/^[#\s]+/, '').trim()
    const regex = new RegExp(`(<h[1-3][^>]*>\\s*${headingClean}\\s*<\\/h[1-3]>)([\\s\\S]*?)(?=(<h[1-3]|$))`, 'i')
    if (regex.test(tableDocContent.value)) {
      tableDocContent.value = tableDocContent.value.replace(regex, `$1\n${payload.html}\n`)
      ElMessage.success(`AI 已靶向更新表架构章节【${headingClean}】`)
      return
    }
  }

  if (payload.mode === 'replace') {
    tableDocContent.value = payload.html
  } else {
    tableDocContent.value = (tableDocContent.value || '') + '\n' + payload.html
  }
  ElMessage.success('AI 表架构设计内容已成功写入')
}

// 唤出 UI 字段脚手架
const handleOpenScaffolder = () => {
  if (currentTable.value?.table_name) {
    window.dispatchEvent(
      new CustomEvent('sqm:toggle-schema-scaffolder', {
        detail: { tableName: currentTable.value.table_name }
      })
    )
  } else {
    window.dispatchEvent(new CustomEvent('sqm:toggle-schema-scaffolder'))
  }
}

// 字典列表
const loadingColumns = ref(false)
const columnsData = ref<DbColumnItem[]>([])
const editingColComment = ref<{ column_name: string; tempComment: string } | null>(null)

// 数据行列表 (接入 DataTable)
const loadingRows = ref(false)
const rowsData = ref<Record<string, any>[]>([])
const searchKeyword = ref('')
const primaryKeyCol = ref<string>('id')

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 模态窗状态
const rowDialogVisible = ref(false)
const isEditMode = ref(false)
const savingRow = ref(false)
const rowFormRef = ref<FormInstance>()
const currentRowForm = reactive<Record<string, any>>({})
const currentRowEditingPk = ref<any>(null)

// 数据表系统中文别名预设映射 (解决 alembic_version 等无业务注释表显示生硬的问题)
const SYSTEM_TABLE_ALIASES: Record<string, string> = {
  alembic_version: '数据库迁移版本',
  sys_attachment: '系统附件存储表',
  sqm_supplier: '供应商主数据',
  sqm_part: '零部件基础档案',
  sqm_part_dev: '零件 APQP 试制开发',
  sqm_project: '车型项目主数据',
  sqm_ctq: 'CTQ 关键质量特性',
  sqm_ctq_line: 'CTQ 关键质量特性',
  sqm_quality_issue: '质量异常与 8D 改善',
  sqm_kb_doc: '质量工程知识库'
}

// 获取清洗后的主业务中文名称 (中文优先展示)
const getTableDisplayName = (tbl: DbTableItem): string => {
  if (SYSTEM_TABLE_ALIASES[tbl.table_name]) {
    return SYSTEM_TABLE_ALIASES[tbl.table_name]
  }
  if (tbl.comment && tbl.comment.trim() && !tbl.comment.includes('未注明')) {
    // 清洗提取核心中文名称：截断括号或冒号前的主名
    const clean = tbl.comment.trim().split(/[(（:：]/)[0].trim()
    if (clean) return clean
  }
  return tbl.table_name
}

// 获取完整业务说明
const getTableCommentFull = (tbl: DbTableItem): string => {
  if (tbl.comment && tbl.comment.trim()) return tbl.comment.trim()
  if (SYSTEM_TABLE_ALIASES[tbl.table_name]) return `${SYSTEM_TABLE_ALIASES[tbl.table_name]} (${tbl.table_name})`
  return '系统数据表'
}

// 过滤后的数据表 (支持按中文主标题、注释和物理表名双向模糊搜索)
const filteredTables = computed(() => {
  const q = tableSearchQuery.value.trim().toLowerCase()
  if (!q) return tablesList.value
  return tablesList.value.filter((tbl) => {
    const displayName = getTableDisplayName(tbl).toLowerCase()
    const rawComment = (tbl.comment || '').toLowerCase()
    const tName = tbl.table_name.toLowerCase()
    return displayName.includes(q) || rawComment.includes(q) || tName.includes(q)
  })
})

// 清洗表头显示名称：去除冒号后的枚举长说明与括号技术注释，保证列宽合理
const formatColumnLabel = (col: DbColumnItem) => {
  if (col.is_primary) return '主键ID'
  if (!col.column_comment) return col.column_name
  const raw = col.column_comment.trim()
  const clean = raw.split(/[:：(（;；]/)[0].trim()
  return clean || raw
}

// 动态将字段字典转为 DataTable 的列配置
const dynamicTableColumns = computed<TableColumn[]>(() => {
  if (!columnsData.value.length) return []
  return columnsData.value.map((col) => {
    const isPk = col.is_primary
    return {
      prop: col.column_name,
      label: formatColumnLabel(col),
      minWidth: isPk ? 90 : 150,
      fixed: isPk ? 'left' : undefined,
      align: isPk ? 'center' : 'left',
      sortable: true,
      showOverflowTooltip: true,
      editable: !isPk && !['text', 'mediumtext', 'longtext', 'json'].includes(col.data_type)
    }
  })
})

// 可编辑/新增的表单字段 (排除自增主键)
const editableColumns = computed(() => {
  return columnsData.value.filter((col) => {
    if (col.is_primary && (col.extra || '').toLowerCase().includes('auto_increment')) {
      return false
    }
    return true
  })
})

// 检查数据库状态
const checkDbStatus = async () => {
  try {
    const res = await axios.get('/api/dev/db/status')
    dbConnected.value = res.data.is_connected
  } catch {
    dbConnected.value = false
  }
}

// 获取所有数据表
const fetchTables = async () => {
  loadingTables.value = true
  try {
    const res = await axios.get('/api/dev/db/tables')
    tablesList.value = res.data || []
    if (tablesList.value.length > 0 && !currentTable.value) {
      const savedTableName = localStorage.getItem('sqm_db_studio_last_table')
      const target = tablesList.value.find((t) => t.table_name === savedTableName) || tablesList.value[0]
      handleSelectTable(target)
    }
    dbConnected.value = true
  } catch (err: any) {
    dbConnected.value = false
    ElMessage.error(`获取数据表列表失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    loadingTables.value = false
  }
}

// 选中数据表 (记忆当前表名)
const handleSelectTable = (tbl: DbTableItem) => {
  currentTable.value = tbl
  localStorage.setItem('sqm_db_studio_last_table', tbl.table_name)
  pagination.page = 1
  searchKeyword.value = ''
  fetchColumns()
  if (activeTab.value === 'data') {
    fetchRows()
  } else if (activeTab.value === 'docs') {
    fetchTableDoc()
  }
}

// 获取当前表的列字典
const fetchColumns = async () => {
  if (!currentTable.value) return
  loadingColumns.value = true
  try {
    const res = await axios.get(`/api/dev/db/tables/${currentTable.value.table_name}/columns`)
    columnsData.value = res.data || []
    // 探测主键列
    const pk = columnsData.value.find((c) => c.is_primary)
    primaryKeyCol.value = pk ? pk.column_name : 'id'
  } catch (err: any) {
    ElMessage.error(`获取字段字典失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    loadingColumns.value = false
  }
}

// 开启编辑注释
const handleStartEditComment = (col: DbColumnItem) => {
  editingColComment.value = {
    column_name: col.column_name,
    tempComment: col.column_comment || ''
  }
}

// 保存字段注释修改
const handleSaveColumnComment = async (col: DbColumnItem) => {
  if (!editingColComment.value || !currentTable.value) return
  const newComment = editingColComment.value.tempComment.trim()
  if (newComment === col.column_comment) {
    editingColComment.value = null
    return
  }

  try {
    await axios.put(`/api/dev/db/tables/${currentTable.value.table_name}/columns/comment`, {
      column_name: col.column_name,
      comment: newComment
    })
    col.column_comment = newComment
    ElMessage.success(`字段 [${col.column_name}] 字典注释已更新`)
  } catch (err: any) {
    ElMessage.error(`更新注释失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    editingColComment.value = null
  }
}

// 获取数据行 (接入分页)
const fetchRows = async () => {
  if (!currentTable.value) return
  loadingRows.value = true
  try {
    const res = await axios.get(`/api/dev/db/tables/${currentTable.value.table_name}/rows`, {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize,
        keyword: searchKeyword.value.trim() || undefined
      }
    })
    rowsData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (err: any) {
    ElMessage.error(`获取数据记录失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    loadingRows.value = false
  }
}

// 搜索数据行
const handleSearchRows = () => {
  pagination.page = 1
  fetchRows()
}

const handleResetSearchRows = () => {
  searchKeyword.value = ''
  pagination.page = 1
  fetchRows()
}

// 分页变化
const handlePageChange = (page: number) => {
  pagination.page = page
  fetchRows()
}

const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.page = 1
  fetchRows()
}

// 行内单元格修改 (通过 DataTable 的 cell-change 事件)
const handleCellChange = async (event: CellChangeEvent) => {
  if (!currentTable.value) return
  const pkVal = event.row[primaryKeyCol.value]
  if (pkVal === undefined || pkVal === null) {
    ElMessage.warning('该表未检测到有效主键，无法行内保存')
    return
  }

  try {
    await axios.put(`/api/dev/db/tables/${currentTable.value.table_name}/rows/${pkVal}`, {
      values: {
        [event.prop]: event.value
      },
      primary_col: primaryKeyCol.value
    })
    ElMessage.success(`已保存修改: ${event.prop}`)
  } catch (err: any) {
    // 恢复旧值
    event.row[event.prop] = event.oldValue
    ElMessage.error(`保存修改失败: ${err.response?.data?.detail || err.message}`)
  }
}

// Tab 切换
const handleTabChange = (tabName: string | number) => {
  if (tabName === 'data' && rowsData.value.length === 0) {
    fetchRows()
  } else if (tabName === 'docs') {
    fetchTableDoc()
  }
}

// 刷新当前数据
const handleRefreshCurrent = () => {
  fetchTables()
  fetchColumns()
  if (activeTab.value === 'data') {
    fetchRows()
  } else if (activeTab.value === 'docs') {
    fetchTableDoc()
  }
}

// 获取架构设计文档
const fetchTableDoc = async () => {
  if (!currentTable.value) return
  loadingDoc.value = true
  try {
    const res = await axios.get(`/api/dev/db/tables/${currentTable.value.table_name}/doc`)
    tableDoc.value = res.data
    tableDocContent.value = res.data.html_content || ''
  } catch (err: any) {
    ElMessage.error(`获取架构设计文档失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    loadingDoc.value = false
  }
}

// 保存架构设计文档至 data/table_docs/*.json
const handleSaveDoc = async () => {
  if (!currentTable.value) return
  savingDoc.value = true
  try {
    const res = await axios.put(`/api/dev/db/tables/${currentTable.value.table_name}/doc`, {
      html_content: tableDocContent.value,
      title: tableDoc.value.title,
      business_module: tableDoc.value.business_module,
      description: tableDoc.value.description
    })
    tableDoc.value = res.data.data
    ElMessage.success(`架构文档已保存至 data/table_docs/${currentTable.value.table_name}.json`)
  } catch (err: any) {
    ElMessage.error(`保存架构文档失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    savingDoc.value = false
  }
}

// 重置架构设计文档为系统标准模板
const handleResetDoc = async () => {
  if (!currentTable.value) return
  try {
    await ElMessageBox.confirm(
      `确定将数据表 [${currentTable.value.table_name}] 的架构设计文档重置为标准模板吗？当前修改将会被覆盖。`,
      '重置确认',
      {
        confirmButtonText: '确定重置',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    loadingDoc.value = true
    const res = await axios.post(`/api/dev/db/tables/${currentTable.value.table_name}/doc/reset`)
    tableDoc.value = res.data.data
    tableDocContent.value = res.data.data.html_content || ''
    ElMessage.success('已恢复标准架构模板')
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(`重置失败: ${err.response?.data?.detail || err.message}`)
    }
  } finally {
    loadingDoc.value = false
  }
}

// 格式化文档最后同步时间 (显示优雅的 HH:mm 或 MM-DD HH:mm)
const formatDocTime = (timeStr?: string): string => {
  if (!timeStr) return ''
  const parts = timeStr.trim().split(' ')
  if (parts.length === 2) {
    return parts[1].substring(0, 5) // 返回 HH:mm，如 19:25
  }
  return timeStr
}



// 打开连接配置弹窗
const handleOpenDbConfig = () => {
  dbConfigDialogRef.value?.open()
}

const handleDbConfigSaved = () => {
  checkDbStatus()
  fetchTables()
}

// 字段表单校验规则
const getColValidationRules = (col: DbColumnItem) => {
  const rules: any[] = []
  if (!col.is_nullable && col.column_default === null) {
    rules.push({ required: true, message: `请输入 ${col.column_comment || col.column_name}`, trigger: 'blur' })
  }
  return rules
}

// 打开新增记录模态窗
const handleOpenCreateRowDialog = () => {
  isEditMode.value = false
  currentRowEditingPk.value = null
  // 重置表单
  for (const k in currentRowForm) {
    delete currentRowForm[k]
  }
  for (const col of editableColumns.value) {
    currentRowForm[col.column_name] = col.column_default !== null ? col.column_default : ''
  }
  rowDialogVisible.value = true
}

// 打开编辑记录模态窗
const handleOpenEditRowDialog = (row: any) => {
  isEditMode.value = true
  currentRowEditingPk.value = row[primaryKeyCol.value]
  for (const k in currentRowForm) {
    delete currentRowForm[k]
  }
  for (const col of editableColumns.value) {
    currentRowForm[col.column_name] = row[col.column_name]
  }
  rowDialogVisible.value = true
}

// 保存表单（新增/修改）
const handleSaveRow = async () => {
  const table = currentTable.value
  if (!table || !rowFormRef.value) return
  await rowFormRef.value.validate(async (valid) => {
    if (!valid) return
    savingRow.value = true
    try {
      if (isEditMode.value) {
        await axios.put(`/api/dev/db/tables/${table.table_name}/rows/${currentRowEditingPk.value}`, {
          values: currentRowForm,
          primary_col: primaryKeyCol.value
        })
        ElMessage.success('记录已成功更新')
      } else {
        await axios.post(`/api/dev/db/tables/${table.table_name}/rows`, {
          values: currentRowForm
        })
        ElMessage.success('记录已成功创建')
      }
      rowDialogVisible.value = false
      fetchRows()
      // 更新该表的实时行数计数
      if (table.real_count !== undefined) {
        table.real_count += isEditMode.value ? 0 : 1
      }
    } catch (err: any) {
      ElMessage.error(`保存记录失败: ${err.response?.data?.detail || err.message}`)
    } finally {
      savingRow.value = false
    }
  })
}

// 删除记录（严格遵守 ui-ux.md 二次确认）
const handleDeleteRow = (row: any) => {
  const table = currentTable.value
  if (!table) return
  const pkVal = row[primaryKeyCol.value]
  ElMessageBox.confirm(
    `确定要永久删除 ${table.table_name} 中主键为 [${pkVal}] 的这条物理数据吗？此操作无法撤销。`,
    '高风险破坏性操作警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await axios.delete(`/api/dev/db/tables/${table.table_name}/rows/${pkVal}`, {
        params: { primary_col: primaryKeyCol.value }
      })
      ElMessage.success('物理数据行已删除')
      fetchRows()
      if (table.real_count) {
        table.real_count -= 1
      }
    } catch (err: any) {
      ElMessage.error(`删除失败: ${err.response?.data?.detail || err.message}`)
    }
  }).catch(() => {})
}

onMounted(() => {
  checkDbStatus()
  fetchTables()
})
</script>

<style scoped>
.db-studio-container {
  display: flex;
  height: 100%;
  width: 100%;
  background: #f8fafc;
  overflow: hidden;
  user-select: none;
  box-sizing: border-box;
}

/* 左侧数据表列表面板 */
.tables-side-pane {
  width: 300px;
  min-width: 300px;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

.side-pane-header {
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.side-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.side-title {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.search-box {
  width: 100%;
}

.tables-scroll-list {
  flex: 1;
  padding: 8px 12px;
}

.loading-state,
.empty-state {
  padding: 24px 12px;
}

.tables-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.table-item-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.2s ease;
}

.table-item-card:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.table-item-card.active {
  background: #eff6ff;
  border-color: #93c5fd;
  box-shadow: 0 1px 3px rgba(59, 130, 246, 0.1);
}

.table-card-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.table-icon {
  color: #64748b;
  font-size: 18px;
  display: flex;
  align-items: center;
}

.table-item-card.active .table-icon {
  color: #3b82f6;
}

.table-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.table-name-text {
  font-size: 13.5px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

.table-desc-text {
  font-size: 11.5px;
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  margin-top: 2px;
}

.row-count-pill {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 12px;
  background: #e2e8f0;
  color: #475569;
  font-weight: 500;
  white-space: nowrap;
}

.row-count-pill.has-rows {
  background: #dcfce7;
  color: #15803d;
}

/* 右侧工作台主体 */
.workbench-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workbench-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.workbench-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.table-detail-header {
  background: #ffffff;
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.table-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.active-table-name {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.table-row-count-pill {
  font-size: 11.5px;
  font-weight: 600;
  color: #0284c7;
  background: #e0f2fe;
  padding: 2px 8px;
  border-radius: 99px;
  line-height: 1.4;
}

.meta-info-trigger {
  font-size: 15px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.15s ease;
  margin-left: 2px;
}

.meta-info-trigger:hover {
  color: #0284c7;
}

.meta-tooltip-box {
  font-size: 12px;
  line-height: 1.7;
}

.meta-tip-row {
  display: flex;
  gap: 4px;
}

.meta-tip-label {
  color: #94a3b8;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tabs-wrapper {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  overflow: hidden;
}

.workbench-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

:deep(.el-tabs__header) {
  margin: 0;
  background: #ffffff;
  padding: 0 20px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

:deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  padding: 12px 16px;
  overflow: hidden !important;
  display: flex;
  flex-direction: column;
}

:deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.columns-pane-content {
  height: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 12px 16px;
  overflow: hidden;
}

.dict-table {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.comment-col-header {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.header-tip-icon {
  font-size: 13px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.15s ease;
}

.header-tip-icon:hover {
  color: #0284c7;
}

.col-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.col-name-text {
  font-weight: 600;
  font-family: ui-monospace, monospace;
  color: #1e293b;
}

.comment-edit-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}

.comment-edit-cell:hover {
  background: #f1f5f9;
}

.comment-text.no-comment {
  color: #94a3b8;
  font-style: italic;
}

.edit-comment-btn {
  opacity: 0;
  transition: opacity 0.15s ease;
}

.comment-edit-cell:hover .edit-comment-btn {
  opacity: 1;
}

.default-val {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.data-pane-content {
  height: 100%;
}

.rows-search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.row-actions-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

/* 模态窗表单 */
.row-dialog-body {
  max-height: 60vh;
  overflow-y: auto;
  padding: 4px 12px;
}

.custom-form-label {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.label-main {
  font-weight: 500;
}

.label-sub {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.w-full {
  width: 100%;
}

/* 架构设计 Tab 内容区 */
.docs-pane-content {
  height: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.docs-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.docs-toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.doc-badge {
  font-weight: 500;
}

.doc-storage-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 1px 7px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.doc-storage-pill:hover {
  color: #2563eb;
  background: #e0f2fe;
  border-color: #bfdbfe;
}

.storage-icon {
  font-size: 12px;
}

.doc-sync-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
}

.docs-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.docs-editor-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.studio-tiptap-editor {
  height: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: none !important;
  border-radius: 0 !important;
}

:deep(.studio-tiptap-editor .tiptap-toolbar) {
  padding: 6px 12px;
  background: #fdfdfd;
  border-bottom: 1px solid #f1f5f9;
}

:deep(.studio-tiptap-editor .tiptap-content) {
  flex: 1;
  min-height: 0 !important;
  overflow-y: auto !important;
  padding: 24px 32px;
  background: #ffffff;
}

:deep(.studio-tiptap-editor .ProseMirror) {
  min-height: 100%;
}
</style>

