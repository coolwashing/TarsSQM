<template>
  <div class="win-explorer-root" @click="handleGlobalClick" @contextmenu.prevent.stop>
    <!-- ==================== 1. 顶部现代化控制栏 (Modern Command Bar) ==================== -->
    <header class="win-toolbar">
      <!-- 1.1 左侧核心新建下拉按钮与选中上下文操作 -->
      <div class="tool-left-group">
        <el-dropdown trigger="click" @command="handleNewCommand">
          <el-button type="primary" size="small" class="win-action-btn primary-create-btn">
            <el-icon><DocumentAdd /></el-icon>
            <span>+ 新建 ▾</span>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="win-create-menu">
              <el-dropdown-item command="doc">
                <el-icon><DocumentAdd /></el-icon>
                <span>📄 质量规程文档</span>
              </el-dropdown-item>
              <el-dropdown-item command="folder">
                <el-icon><FolderAdd /></el-icon>
                <span>📁 分类目录</span>
              </el-dropdown-item>
              <el-dropdown-item command="shortcut" divided>
                <el-icon><Link /></el-icon>
                <span>🔗 跨项目标准引用</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button size="small" @click="openFileUpload()" title="上传原文件到当前目录">上传文件</el-button>

        <!-- 1.2 选中对象时的快速操作按钮组（去除了重复文件名胶囊，仅保留高频动作） -->
        <transition name="fade">
          <div v-if="selectedItem" class="toolbar-selection-actions">
            <div class="toolbar-v-divider"></div>
            <el-button
              v-if="selectedItem.type !== 'folder'"
              type="primary"
              plain
              size="small"
              class="pill-action-btn"
              @click="openEditorPage(selectedItem, true)"
              :title="selectedItem.type === 'file' ? '下载原始附件' : '在新浏览器标签页中打开编辑'"
            >
              <el-icon><FolderOpened /></el-icon>
              <span>{{ selectedItem.type === 'file' ? '下载原件' : '新标签页编辑 ↗' }}</span>
            </el-button>
            <el-button
              v-else
              type="primary"
              plain
              size="small"
              class="pill-action-btn"
              @click="navigateTo(selectedItem.id)"
              title="打开进入此分类目录"
            >
              <el-icon><FolderOpened /></el-icon>
              <span>打开文件夹</span>
            </el-button>

            <el-button
              size="small"
              class="pill-action-btn"
              @click="handleRenameModal"
              title="重命名 (F2)"
            >
              <el-icon><Edit /></el-icon>
              <span>重命名</span>
            </el-button>
            <el-button
              v-if="selectedItem.type !== 'folder'"
              size="small"
              class="pill-action-btn"
              @click="toggleFavorite(selectedItem)"
              :title="selectedItem.is_favorite ? '取消标星关注' : '添加标星关注'"
            >
              <span>{{ selectedItem.is_favorite ? '⭐ 已关注' : '☆ 标星' }}</span>
            </el-button>
            <el-button
              size="small"
              class="pill-action-btn delete-pill-btn"
              @click="handleDeleteItem"
              title="删除此项 (Delete)"
            >
              <el-icon><Delete /></el-icon>
              <span>删除</span>
            </el-button>
          </div>
        </transition>
      </div>

      <!-- 1.3 右侧视图模式、指标维度、搜索与 AI 工具 -->
      <div class="toolbar-right">
        <!-- 视图分段控制器 (Segmented Control) -->
        <div class="view-segmented-wrap">
          <button
            class="segmented-btn"
            :class="{ active: viewMode === 'grid' }"
            @click="viewMode = 'grid'"
            title="网格卡片视图"
          >
            <el-icon><Grid /></el-icon>
            <span>网格</span>
          </button>
          <button
            class="segmented-btn"
            :class="{ active: viewMode === 'table' }"
            @click="viewMode = 'table'"
            title="详细列表视图"
          >
            <el-icon><Tickets /></el-icon>
            <span>列表</span>
          </button>
        </div>

        <!-- 网格图标尺寸控制 (仅网格模式下展示) -->
        <el-dropdown v-if="viewMode === 'grid'" trigger="click" @command="handleIconSizeChange">
          <el-button size="small" class="win-icon-btn size-pill-btn" title="调整图标卡片尺寸">
            <span>{{ getIconSizeLabel() }} ▾</span>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="small">▫️ 小图标</el-dropdown-item>
              <el-dropdown-item command="medium">◻️ 中等图标</el-dropdown-item>
              <el-dropdown-item command="large">⬛ 大图标</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- 预览窗格开关 -->
        <el-button
          size="small"
          :class="['win-icon-btn preview-toggle-btn', { active: showPreviewPane }]"
          @click="showPreviewPane = !showPreviewPane"
          :title="showPreviewPane ? '收起属性快照预览' : '展开属性快照预览 (Alt+P)'"
        >
          <el-icon><View /></el-icon>
          <span>预览</span>
        </el-button>

        <!-- 指标可设计化切换 -->
        <el-dropdown trigger="click" @command="handleMetricChange">
          <el-button size="small" class="win-icon-btn metric-pill-btn" title="切换指标维度">
            <span>📊 {{ getMetricLabel() }} ▾</span>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="words">📝 字数</el-dropdown-item>
              <el-dropdown-item command="kb">💾 文件大小</el-dropdown-item>
              <el-dropdown-item command="ctq">🎯 CTQ 项</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <div class="tool-divider"></div>

        <!-- 现代化全局检索胶囊按钮 -->
        <div class="search-pill-box" @click="searchModalVisible = true" title="全局质量规程检索 (Ctrl+K)">
          <el-icon><Search /></el-icon>
          <span class="search-tip-text">搜索文档与附件</span>
          <kbd class="shortcut-key-tag">Ctrl+K</kbd>
        </div>

        <!-- ✨ AI 智写助手 -->
        <el-button
          type="primary"
          size="small"
          class="ai-smart-btn"
          @click="aiCopilotVisible = true"
        >
          ✨ AI 助手
        </el-button>

        <!-- 刷新按钮 -->
        <el-button
          size="small"
          circle
          class="refresh-btn"
          :icon="Refresh"
          @click="refreshCurrentFolder"
          title="刷新目录 (F5)"
        />
      </div>
    </header>

    <!-- ==================== 2. 地址导航栏与过滤条 (Address Bar) ==================== -->
    <nav class="win-nav-bar">
      <div class="nav-history-arrows">
        <!-- 侧栏收起/展开控制按钮 -->
        <button
          class="nav-circle-btn sidebar-toggle-btn"
          :class="{ 'is-collapsed': !showNavPane }"
          @click="showNavPane = !showNavPane"
          :title="showNavPane ? '收起目录侧栏' : '展开目录侧栏'"
        >
          <el-icon><Fold v-if="showNavPane" /><Expand v-else /></el-icon>
        </button>
        <span class="nav-btn-divider"></span>
        <button
          class="nav-circle-btn"
          :disabled="historyIndex <= 0"
          @click="navBack"
          title="后退 (Alt+←)"
        >
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <button
          class="nav-circle-btn"
          :disabled="historyIndex >= historyStack.length - 1"
          @click="navForward"
          title="前进 (Alt+→)"
        >
          <el-icon><ArrowRight /></el-icon>
        </button>
        <button
          class="nav-circle-btn"
          :disabled="pathCrumbs.length <= 1"
          @click="navUp"
          title="向上一级 (Alt+↑)"
        >
          <el-icon><ArrowUp /></el-icon>
        </button>
      </div>

      <!-- 可点击的面包屑地址栏 -->
      <div class="address-container">
        <span class="address-drive-icon">📚</span>
        <div class="address-crumbs-track">
          <template v-for="(crumb, idx) in pathCrumbs" :key="crumb.id ?? 'root'">
            <span
              class="crumb-node"
              :class="{ 'is-active': idx === pathCrumbs.length - 1 }"
              @click="navigateTo(crumb.id)"
            >
              {{ crumb.name }}
            </span>
            <span v-if="idx < pathCrumbs.length - 1" class="crumb-separator">›</span>
          </template>
        </div>
      </div>

      <!-- 当前文件夹实时检索过滤框 -->
      <div class="filter-box">
        <el-input
          v-model="filterKeyword"
          size="small"
          placeholder="搜索此文件夹..."
          clearable
          :prefix-icon="Search"
        />
      </div>
    </nav>

    <!-- ==================== 3. 资源管理器主工作区 (三段式布局) ==================== -->
    <main class="win-body-area" v-loading="loading">
      <!-- 3.1 左侧快速访问与项目结构导航 (Navigation Pane，支持收起/展开) -->
      <aside class="nav-side-pane" :class="{ 'is-collapsed': !showNavPane }">
        <!-- 常用快捷入口 -->
        <div class="nav-section-header-row">
          <span class="nav-section-header">常用</span>
          <button
            class="nav-collapse-btn"
            @click="showNavPane = false"
            title="收起目录侧栏"
          >
            <el-icon><Fold /></el-icon>
          </button>
        </div>
        <div class="quick-access-list">
          <!-- 全部规程入口 -->
          <div
            class="nav-list-item"
            :class="{ active: !isViewingFavorites && currentFolderId === null }"
            @click="navigateTo(null)"
          >
            <span class="item-badge-icon">📂</span>
            <span class="item-name-text">全部规程</span>
          </div>

          <!-- 标星规程专属入口 (带徽标) -->
          <div
            class="nav-list-item star-quick-item"
            :class="{ active: isViewingFavorites }"
            @click="toggleViewFavorites"
          >
            <span class="item-badge-icon">⭐</span>
            <span class="item-name-text">标星规程</span>
            <span v-if="starredCount > 0" class="star-badge-pill">{{ starredCount }}</span>
          </div>
        </div>

        <!-- 规程分类结构树 -->
        <div class="nav-section-header" style="margin-top: 14px;" title="拖到节点中间可移入文件夹，上下边缘可移为同级；右键可选择移动位置">规程目录</div>
        <div class="tree-container">
          <el-tree
            ref="navTreeRef"
            :data="navTreeData"
            node-key="id"
            default-expand-all
            highlight-current
            :expand-on-click-node="false"
            :draggable="!movingTreeNode"
            :allow-drop="allowNavTreeDrop"
            class="win-nav-tree"
            @node-click="handleNavTreeNodeClick"
            @node-drop="handleNavTreeNodeDrop"
            @node-contextmenu="handleNavTreeContextMenu"
          >
            <template #default="{ data }">
              <div class="tree-item-row" :class="{ 'is-selected': currentFolderId === data.id }" :title="data.title">
                <span class="tree-item-icon">{{ data.icon || (data.is_folder ? '📁' : '📄') }}</span>
                <span class="tree-item-title">{{ data.title }}</span>
              </div>
            </template>
          </el-tree>
        </div>
      </aside>

      <!-- 3.2 中间文件资源浏览区 (Explorer Viewport) -->
      <section class="explorer-viewport" :class="{ 'is-file-drop': fileDragActive }" @contextmenu.prevent.stop="handleViewportContextMenu"
        @dragover="handleFileDragOver" @dragleave="handleFileDragLeave" @drop="handleFileDrop">
        <div v-if="fileDragActive" class="file-drop-hint">松开后上传到当前目录</div>
        <!-- 网格卡片模式 (Grid Mode) -->
        <div
          v-if="viewMode === 'grid'"
          class="grid-layout-container"
          :class="`size-${cardZoomSize}`"
        >
          <div
            v-for="item in displayItems"
            :key="item.id"
            class="file-card"
            :class="[
              `card-${cardZoomSize}`,
              { selected: selectedItem?.id === item.id }
            ]"
            @click.stop="handleSelectItem(item)"
            @dblclick.stop="handleItemDoubleClick(item)"
            @contextmenu.prevent.stop="handleItemContextMenu($event, item)"
          >
            <!-- 卡片顶层：标星 ⭐ 与状态胶囊 -->
            <div class="card-top-bar" v-if="item.type !== 'folder'">
              <button
                class="star-toggle-btn"
                :class="{ 'is-starred': item.is_favorite }"
                @click.stop="toggleFavorite(item)"
                :title="item.is_favorite ? '取消标星' : '添加标星关注'"
              >
                {{ item.is_favorite ? '⭐' : '☆' }}
              </button>
            </div>

            <div class="file-card-icon-wrap">
              <span class="file-card-icon">{{ item.icon || (item.type === 'folder' ? '📁' : '📄') }}</span>
              <!-- Windows 经典软引用快捷方式角标 ↗ -->
              <span
                v-if="item.is_shortcut"
                class="shortcut-badge"
                title="快捷方式软引用: 自动关联通用标准源文档"
              >
                ↗
              </span>
            </div>

            <div class="file-card-name" :title="item.name">
              {{ item.name }}
            </div>
          </div>

          <!-- 空白文件夹 / 无标星友好提示 -->
          <div v-if="displayItems.length === 0" class="empty-folder-box">
            <el-empty :description="isViewingFavorites ? '暂无标星收藏文档' : '此文件夹为空'">
              <div class="empty-actions" v-if="!isViewingFavorites">
                <el-button type="primary" size="small" :icon="DocumentAdd" @click="openCreateModal('doc')">
                  新建规程文档
                </el-button>
                <el-button size="small" :icon="FolderAdd" @click="openCreateModal('folder')">
                  新建子目录
                </el-button>
              </div>
              <div class="empty-actions" v-else>
                <p style="font-size: 12px; color: #94a3b8; margin: 0 0 10px 0;">
                  在浏览规程时，点击文档右上角或快照中的 ⭐ 即可将关键标准加星标以便快速查阅
                </p>
                <el-button type="primary" size="small" @click="navigateTo(null)">
                  📂 浏览全部规程
                </el-button>
              </div>
            </el-empty>
          </div>
        </div>

        <!-- 详细信息表格模式 (Details List Mode) -->
        <div v-else class="table-layout-container">
          <table class="win-detail-table">
            <thead>
              <tr>
                <th style="width: 38px; text-align: center;">⭐</th>
                <th style="width: 40%;">名称</th>
                <th style="width: 14%;">修改日期</th>
                <th style="width: 12%;">类型</th>
                <th style="width: 12%;">所属工程/来源</th>
                <th style="width: 10%;">{{ getMetricColumnHeader() }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in displayItems"
                :key="item.id"
                :class="{ selected: selectedItem?.id === item.id }"
                @click.stop="handleSelectItem(item)"
                @dblclick.stop="handleItemDoubleClick(item)"
                @contextmenu.prevent.stop="handleItemContextMenu($event, item)"
              >
                <!-- 标星列 -->
                <td style="text-align: center;">
                  <button
                    v-if="item.type !== 'folder'"
                    class="table-star-btn"
                    :class="{ 'is-starred': item.is_favorite }"
                    @click.stop="toggleFavorite(item)"
                    :title="item.is_favorite ? '取消标星' : '添加标星'"
                  >
                    {{ item.is_favorite ? '⭐' : '☆' }}
                  </button>
                </td>
                <td class="col-name">
                  <div class="name-cell-wrap">
                    <div class="table-icon-wrap">
                      <span>{{ item.icon || (item.type === 'folder' ? '📁' : '📄') }}</span>
                      <span v-if="item.is_shortcut" class="shortcut-badge-mini" title="快捷方式软引用">↗</span>
                    </div>
                    <span class="item-name-text" :title="item.name">{{ item.name }}</span>
                  </div>
                </td>
                <td class="col-date">{{ item.date || '-' }}</td>
                <td class="col-type">
                  <span class="type-pill" :class="item.type">
                    {{ item.type === 'folder' ? '文件夹' : item.type === 'file' ? '附件原件' : (item.is_shortcut ? '快捷方式' : '在线文档') }}
                  </span>
                </td>
                <td class="col-proj" :title="item.proj">{{ item.proj || '-' }}</td>
                <td class="col-size">{{ formatMetric(item) }}</td>
              </tr>
              <tr v-if="displayItems.length === 0">
                <td colspan="6" style="text-align: center; padding: 40px; color: #9ca3af;">
                  {{ isViewingFavorites ? '暂无标星收藏文档' : '此文件夹暂无项目文件' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 3.3 右侧 Windows 预览窗格 (Preview Pane) -->
      <aside
        class="preview-side-pane"
        v-if="showPreviewPane"
        :style="{ width: previewPaneWidth + 'px' }"
      >
        <!-- 窗格宽度拖拽调整柄 (向左拉伸加宽，向右缩减) -->
        <div
          class="preview-resize-bar"
          :class="{ 'is-resizing': isResizingPreview }"
          @mousedown="startPreviewResize"
          title="按住向左/向右拖拽调整预览窗格宽度 (260px - 750px)"
        >
          <div class="resize-handle-line"></div>
        </div>

        <template v-if="selectedItem">
          <div class="preview-header">
            <span class="preview-header-title">
              {{ selectedItem.type === 'folder' ? '📁 文件夹属性' : selectedItem.type === 'file' ? '📎 附件属性' : '📄 文档摘要' }}
            </span>
            <button class="preview-close-btn" @click="showPreviewPane = false" title="关闭预览窗格">×</button>
          </div>

          <div class="preview-body">
            <!-- 图标与主标题 (紧凑精致，支持点击换图标) -->
            <div class="preview-hero">
              <span
                class="preview-hero-icon clickable-hero-icon"
                @click="openIconPickerForItem(selectedItem)"
                title="点击更改此项业务图标"
              >
                {{ selectedItem.icon || (selectedItem.type === 'folder' ? '📁' : '📄') }}
                <span class="icon-edit-mini-badge">✏️</span>
              </span>
              <h3 class="preview-hero-title" :title="selectedItem.name">{{ selectedItem.name }}</h3>
              <!-- 标星与状态 -->
              <div class="preview-hero-tags" v-if="selectedItem.type !== 'folder'">
                <button
                  class="preview-star-btn"
                  :class="{ 'is-starred': selectedItem.is_favorite }"
                  @click="toggleFavorite(selectedItem)"
                  :title="selectedItem.is_favorite ? '取消标星关注' : '添加标星关注'"
                >
                  {{ selectedItem.is_favorite ? '⭐ 已标星' : '☆ 标星' }}
                </button>
              </div>
            </div>

            <!-- 快捷方式特殊标识条 -->
            <div v-if="selectedItem.is_shortcut" class="shortcut-info-banner">
              <span class="banner-icon">🔗</span>
              <div class="banner-desc">
                <strong>跨项目软引用</strong>
                <p>映射主标准库，正文与公差实时联动同步。</p>
              </div>
            </div>

            <!-- 紧凑型属性元数据 2x2 网格 (减负 68% 空间，零滚动条) -->
            <div class="preview-meta-grid">
              <div class="meta-grid-item">
                <span class="meta-k">类型</span>
                <span class="meta-v">{{ selectedItem.type === 'folder' ? '工程目录' : selectedItem.type === 'file' ? '附件原件' : (selectedItem.is_shortcut ? '标准引用' : '在线文档') }}</span>
              </div>
              <div class="meta-grid-item">
                <span class="meta-k">规模</span>
                <span class="meta-v">{{ formatMetric(selectedItem) || '-' }}</span>
              </div>
              <div class="meta-grid-item">
                <span class="meta-k">作者</span>
                <span class="meta-v" :title="selectedItem.author">{{ selectedItem.author || 'SQM质量部' }}</span>
              </div>
              <div class="meta-grid-item">
                <span class="meta-k">修改</span>
                <span class="meta-v">{{ selectedItem.date ? selectedItem.date.slice(5) : '-' }}</span>
              </div>
            </div>

            <div v-if="selectedItem.type === 'file'" class="attachment-index-info">
              <p>{{ selectedItem.index_message || '原件已保存' }}</p>
              <el-button text size="small" :loading="reindexing" @click="reindexSelectedFile">重新索引</el-button>
            </div>

            <!-- 正文预览 / CTQ 公差红线快照 (紧凑自适应高度) -->
            <div class="preview-content-section" v-if="selectedItem.type !== 'folder'">
              <div class="section-title">{{ selectedItem.type === 'file' ? '提取正文摘要' : '文档摘要' }}</div>
              <div class="content-preview-box">
                {{ selectedItem.content_text || '暂无纯文本摘要或正在加载中...' }}
              </div>
            </div>
          </div>

          <!-- 独立固化吸底操作栏 (永不被挤出视野，不在滚动条内) -->
          <div class="preview-footer">
            <template v-if="selectedItem.type !== 'folder'">
              <div class="preview-btn-row">
                <el-button
                  type="primary"
                  size="default"
                  class="preview-primary-btn"
                  @click="openEditorPage(selectedItem, false)"
                >
                  {{ selectedItem.type === 'file' ? '下载原件' : '✏️ 编辑文档' }}
                </el-button>
                <el-button
                  v-if="selectedItem.type !== 'file'"
                  size="default"
                  class="preview-sub-btn"
                  @click="openEditorPage(selectedItem, true)"
                  title="在新浏览器标签页中打开编辑"
                >
                  ↗ 新标签页
                </el-button>
              </div>
              <el-button
                size="default"
                class="preview-ai-btn"
                @click="openAiCopilotForSelected"
              >
                {{ selectedItem.type === 'file' ? '✨ 用此附件提问' : '✨ AI 问答与编辑' }}
              </el-button>
            </template>
            <template v-else>
              <el-button
                type="primary"
                size="default"
                class="preview-full-btn"
                @click="navigateTo(selectedItem.id)"
              >
                📂 打开文件夹
              </el-button>
            </template>
          </div>
        </template>

        <!-- 未选中任何项状态 -->
        <div v-else class="preview-empty">
          <div class="empty-icon">👁️</div>
          <p class="empty-tip">选择文件或文件夹以即刻预览内容、CTQ 公差红线与工程属性</p>
        </div>
      </aside>
    </main>

    <!-- ==================== 4. 底部状态栏 (Status Bar) ==================== -->
    <footer class="win-status-bar">
      <div class="status-left">
        <span>当前目录共 {{ displayItems.length }} 个项目</span>
        <span v-if="selectedItem">| 已选中 1 个项目: {{ selectedItem.name }}</span>
      </div>
      <div class="status-right">
        <span>视图尺寸: {{ getIconSizeLabel() }}</span>
        <span>连接模式: FastAPI 云端就绪</span>
      </div>
    </footer>

    <!-- ==================== 5. 右键上下文菜单 (Context Menu) ==================== -->
    <div
      v-if="contextMenuVisible"
      class="win-context-menu"
      :style="{ left: contextMenuPos.x + 'px', top: contextMenuPos.y + 'px' }"
      @click.stop
    >
      <!-- 场景 A：在具体文件/文件夹上右键 -->
      <template v-if="contextMenuTreeNode">
        <div class="context-item" @click.stop.prevent="handleContextMenuAction('move')">
          <el-icon><FolderOpened /></el-icon>
          <span>移动到…</span>
        </div>
      </template>
      <template v-else-if="contextMenuItem">
        <div class="context-item primary-action" @click.stop.prevent="handleContextMenuAction('openInCurrent')">
          <el-icon><Edit /></el-icon>
          <span>{{ contextMenuItem.type === 'folder' ? '打开文件夹' : contextMenuItem.type === 'file' ? '下载原件' : '进入编辑' }}</span>
        </div>
        <div
          v-if="contextMenuItem.type !== 'folder' && contextMenuItem.type !== 'file'"
          class="context-item"
          @click.stop.prevent="handleContextMenuAction('openInNewTab')"
        >
          <el-icon><FolderOpened /></el-icon>
          <span>在新标签页打开编辑 ↗</span>
        </div>
        <div
          v-if="contextMenuItem.type !== 'folder'"
          class="context-item"
          @click.stop.prevent="handleContextMenuAction('toggleFavorite')"
        >
          <span>{{ contextMenuItem.is_favorite ? '⭐ 取消标星关注' : '⭐ 添加标星关注' }}</span>
        </div>
        <div
          v-if="contextMenuItem.type !== 'folder'"
          class="context-item"
          @click.stop.prevent="handleContextMenuAction('shortcut')"
        >
          <el-icon><Link /></el-icon>
          <span>为此文件创建快捷方式...</span>
        </div>

        <div class="context-divider" v-if="contextMenuItem.type !== 'folder'"></div>

        <div class="context-divider"></div>
        <div v-if="contextMenuItem.type === 'file'" class="context-item" @click.stop.prevent="copySelectedFile">
          <span>复制一份到当前目录</span>
        </div>
        <div class="context-item" @click.stop.prevent="handleContextMenuAction('move')">
          <el-icon><FolderOpened /></el-icon>
          <span>移动到…</span>
        </div>
        <div class="context-item" @click.stop.prevent="handleContextMenuAction('rename')">
          <el-icon><Edit /></el-icon>
          <span>重命名 (F2)</span>
        </div>
        <div class="context-item" @click.stop.prevent="handleContextMenuAction('changeIcon')">
          <span style="font-size: 13px;">🎨</span>
          <span>更改图标...</span>
        </div>
        <div class="context-item delete" @click.stop.prevent="handleContextMenuAction('delete')">
          <el-icon><Delete /></el-icon>
          <span>删除</span>
        </div>
      </template>

      <!-- 场景 B：在空白视口区域右键 (Windows 经典上下文菜单) -->
      <template v-else>
        <div class="context-item" @click="openFileUpload()"><span>上传文件…</span></div>
        <!-- Windows 经典新建子菜单 -->
        <div class="context-item submenu-parent primary-item">
          <el-icon><DocumentAdd /></el-icon>
          <span>新建 ▾</span>
          <div class="context-submenu">
            <div class="context-item" @click="openCreateModalFromContext('doc')">
              <el-icon><DocumentAdd /></el-icon>
              <span>📄 质量规程文档</span>
            </div>
            <div class="context-item" @click="openCreateModalFromContext('folder')">
              <el-icon><FolderAdd /></el-icon>
              <span>📁 分类目录</span>
            </div>
            <div class="context-item" @click="openShortcutModalFromContext">
              <el-icon><Link /></el-icon>
              <span>🔗 跨项目标准引用</span>
            </div>
          </div>
        </div>

        <div class="context-divider"></div>

        <div class="context-item" @click="refreshCurrentFolderFromContext">
          <el-icon><Refresh /></el-icon>
          <span>刷新目录 (F5)</span>
        </div>

        <div class="context-item" @click="togglePreviewPaneFromContext">
          <el-icon><View /></el-icon>
          <span>{{ showPreviewPane ? '收起预览窗格' : '展开预览窗格' }}</span>
        </div>

        <div class="context-divider"></div>

        <!-- 视图尺寸子菜单 -->
        <div class="context-item submenu-parent">
          <el-icon><Grid /></el-icon>
          <span>图标尺寸 ▾</span>
          <div class="context-submenu">
            <div class="context-item" :class="{ active: cardZoomSize === 'small' && viewMode === 'grid' }" @click="handleIconSizeChangeFromContext('small')">▫️ 小图标</div>
            <div class="context-item" :class="{ active: cardZoomSize === 'medium' && viewMode === 'grid' }" @click="handleIconSizeChangeFromContext('medium')">◻️ 中等图标</div>
            <div class="context-item" :class="{ active: cardZoomSize === 'large' && viewMode === 'grid' }" @click="handleIconSizeChangeFromContext('large')">⬛ 大图标</div>
            <div class="context-item" :class="{ active: viewMode === 'table' }" @click="toggleViewModeFromContext">☰ 详细列表</div>
          </div>
        </div>

        <!-- 指标维度子菜单 -->
        <div class="context-item submenu-parent">
          <el-icon><Tickets /></el-icon>
          <span>指标维度 ▾</span>
          <div class="context-submenu">
            <div class="context-item" :class="{ active: metricMode === 'words' }" @click="handleMetricChangeFromContext('words')">📝 正文字数</div>
            <div class="context-item" :class="{ active: metricMode === 'kb' }" @click="handleMetricChangeFromContext('kb')">💾 估算大小 (KB)</div>
            <div class="context-item" :class="{ active: metricMode === 'ctq' }" @click="handleMetricChangeFromContext('ctq')">🎯 CTQ 公差项</div>
          </div>
        </div>
      </template>
    </div>

    <!-- ==================== 6. 新建文档/新建文件夹弹窗 (标准UI/UX与图标系统) ==================== -->
    <el-dialog
      v-model="createModal.visible"
      :title="createModal.type === 'folder' ? '新建工程分类目录' : '新建技术规程文档'"
      width="460px"
      append-to-body
      destroy-on-close
      class="create-item-dialog"
    >
      <el-form label-position="top">
        <el-form-item :label="createModal.type === 'folder' ? '目录名称' : '文档标题'">
          <el-input
            v-model="createModal.name"
            :placeholder="createModal.type === 'folder' ? '例如: 02_减速机与传动模组' : '例如: RV-40E 摆线减速机安装公差规范'"
            @keyup.enter="submitCreateModal"
            autofocus
          />
        </el-form-item>
        <el-form-item label="分类图标">
          <div class="create-icon-selection-wrap">
            <div
              class="active-icon-badge"
              @click="openIconPickerForCreate"
              title="点击更换更多标准业务图标"
            >
              <span class="badge-char">{{ createModal.icon }}</span>
              <span class="badge-hint">更换</span>
            </div>
            <div class="quick-icons-box">
              <div class="quick-chips-row">
                <span
                  v-for="ic in (createModal.type === 'folder' ? quickFolderIcons : quickDocIcons)"
                  :key="ic.char"
                  class="quick-icon-pill"
                  :class="{ active: createModal.icon === ic.char }"
                  @click="createModal.icon = ic.char"
                >
                  {{ ic.char }} {{ ic.label }}
                </span>
              </div>
              <el-button
                size="small"
                text
                type="primary"
                class="more-icons-btn"
                @click="openIconPickerForCreate"
              >
                🎨 更多标准图标...
              </el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createModal.visible = false">取消</el-button>
        <el-button type="primary" @click="submitCreateModal">确定创建</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 8. 标准业务图标选择弹窗 (支持复用：新建/右键更改/快照更改) ==================== -->
    <el-dialog
      v-model="iconPickerModal.visible"
      title="🎨 选择业务图标"
      width="520px"
      append-to-body
      class="icon-picker-dialog"
    >
      <div class="icon-picker-container">
        <!-- 搜索与当前预览条 -->
        <div class="icon-picker-top-bar">
          <div class="icon-current-preview">
            <span class="preview-char-box">{{ iconPickerModal.selectedIcon }}</span>
            <div class="preview-info-box">
              <span class="preview-title">当前选定图标</span>
              <span class="preview-subtitle">点击下方网格即刻替换</span>
            </div>
          </div>
          <div class="icon-search-wrap">
            <el-input
              v-model="iconPickerSearch"
              placeholder="搜索图标或业务词..."
              clearable
              size="small"
              :prefix-icon="Search"
            />
          </div>
        </div>

        <!-- 图标分类滚动区 -->
        <div class="icon-categories-scroll">
          <div
            v-for="cat in filteredIconCategories"
            :key="cat.name"
            class="icon-cat-block"
          >
            <div class="icon-cat-title">{{ cat.name }}</div>
            <div class="icon-grid">
              <button
                v-for="ic in cat.icons"
                :key="ic.char + ic.label"
                type="button"
                class="icon-grid-btn"
                :class="{ active: iconPickerModal.selectedIcon === ic.char }"
                @click="handleSelectIconCell(ic.char)"
                :title="ic.label"
              >
                <span class="grid-icon-char">{{ ic.char }}</span>
                <span class="grid-icon-label">{{ ic.label }}</span>
              </button>
            </div>
          </div>
          <div v-if="filteredIconCategories.length === 0" class="icon-empty-search">
            未找到匹配的图标，您也可以直接在上方手动输入任意字符
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="iconPickerModal.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmIconPicker">应用图标</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 7. 创建快捷方式弹窗 (跨项目软引用) ==================== -->
    <el-dialog
      v-model="shortcutModal.visible"
      title="创建跨项目规程快捷方式 (软链接引用 ↗)"
      width="520px"
      append-to-body
      destroy-on-close
    >
      <div style="font-size: 13px; color: #64748b; margin-bottom: 14px; line-height: 1.5;">
        💡 <strong>Windows 快捷方式原理</strong>：在当前工程目录下创建指向主标准库的软引用。无需物理拷贝，主文档更新时所有快捷方式实时联动同步，避免多项目规范割裂。
      </div>
      <el-form label-position="top">
        <el-form-item label="引用目标文档 (源文件)">
          <el-select
            v-model="shortcutModal.targetId"
            placeholder="请选择要引用的通用技术标准或作业规程"
            filterable
            style="width: 100%;"
            @change="handleShortcutTargetChange"
          >
            <el-option
              v-for="doc in allAvailableDocs"
              :key="doc.id"
              :label="`${doc.icon || '📄'} ${doc.title}`"
              :value="doc.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="快捷方式显示名称">
          <el-input
            v-model="shortcutModal.name"
            placeholder="例如: IQC 来料抽样基准 - 快捷方式.lnk"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shortcutModal.visible = false">取消</el-button>
        <el-button type="primary" :disabled="!shortcutModal.targetId" @click="submitCreateShortcut">
          立即建立快捷链接
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="moveModal.visible"
      title="移动到"
      width="460px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="!movingTreeNode"
      :close-on-press-escape="!movingTreeNode"
      :show-close="!movingTreeNode"
    >
      <p class="move-item-name">移动「{{ moveModal.name }}」</p>
      <el-tree
        v-if="moveModal.visible"
        :data="moveTargetTree"
        node-key="id"
        :props="{ label: 'title' }"
        :current-node-key="moveModal.targetFolderId"
        default-expand-all
        highlight-current
        :expand-on-click-node="false"
        class="move-target-tree"
        @node-click="handleMoveTargetClick"
      >
        <template #default="{ data }">
          <span class="move-target-title" :title="data.title">📁 {{ data.title }}</span>
        </template>
      </el-tree>
      <p class="move-destination">目标位置：{{ moveModal.destination }}</p>
      <template #footer>
        <el-button :disabled="movingTreeNode" @click="moveModal.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="movingTreeNode"
          :disabled="moveModal.targetFolderId === moveModal.sourceParentId"
          @click="submitMoveModal"
        >确认移动</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 8. 重命名弹窗 ==================== -->
    <el-dialog
      v-model="renameModal.visible"
      title="重命名项目"
      width="400px"
      append-to-body
    >
      <el-input
        v-model="renameModal.newName"
        placeholder="请输入新名称..."
        @keyup.enter="submitRename"
      />
      <template #footer>
        <el-button @click="renameModal.visible = false">取消</el-button>
        <el-button type="primary" @click="submitRename">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- ==================== 9. 全局全文/RAG检索弹窗 (Ctrl+K) ==================== -->
    <el-dialog
      v-model="searchModalVisible"
      title="质量知识库全局全文检索"
      width="640px"
      append-to-body
    >
      <el-input
        v-model="searchQuery"
        placeholder="输入检验公差、AQL 抽样、物料图号或 8D 对策关键词..."
        size="large"
        clearable
        :prefix-icon="Search"
        @keyup.enter="performSearch"
      />
      <div class="search-results-box" v-loading="searching">
        <template v-if="searchResults.length > 0">
          <div
            v-for="res in searchResults"
            :key="res.id"
            class="search-res-item"
            @click="jumpToSearchResult(res.id)"
          >
            <div class="res-head">
              <span class="res-icon">{{ res.icon || '📄' }}</span>
              <span class="res-title">{{ res.title }}</span>
              <span class="res-date">{{ formatDate(res.updated_at) }}</span>
            </div>
            <div class="res-snippet" v-html="res.snippet"></div>
            <div class="search-source-location">{{ res.kind === 'file' ? '附件' : '在线文档' }} · {{ res.location }}</div>
          </div>
        </template>
        <div v-else-if="hasSearched" class="no-res">未找到匹配的质量标准条款</div>
        <div v-else class="search-tip">支持直接对全部工程规程及快捷方式正文进行全文模糊检索</div>
      </div>
    </el-dialog>

    <!-- ==================== 10. AI 智写助手弹窗 ==================== -->
    <DocAiCopilot
      v-model="aiCopilotVisible"
      :doc-id="selectedItem?.type === 'folder' ? undefined : selectedItem?.is_shortcut ? selectedItem.target_id || selectedItem.id : selectedItem?.id"
      :doc-title="selectedItem?.name"
      :editable="!!selectedItem && selectedItem.type !== 'folder' && selectedItem.type !== 'file'"
      :folder-id="currentFolderId"
      @confirm-insert="handleConfirmAiInsert"
      @refresh-doc="refreshCurrentFolder"
    />
    <KbFileUpload v-model="fileUploadVisible" :folder-id="currentFolderId" :folder-name="pathCrumbs[pathCrumbs.length - 1]?.name" :files="incomingFiles" @uploaded="refreshCurrentFolder" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import {
  DocumentAdd,
  FolderAdd,
  Link,
  Edit,
  Delete,
  View,
  Tickets,
  Grid,
  Search,
  Refresh,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  FolderOpened,
  Document,
  Fold,
  Expand
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { formatDate } from '@/utils/format'
import DocAiCopilot from './components/DocAiCopilot.vue'
import KbFileUpload from './components/KbFileUpload.vue'

const router = useRouter()

// 接口定义
interface KbExplorerItem {
  id: number
  name: string
  type: 'folder' | 'doc' | 'shortcut' | 'file'
  icon?: string
  date?: string
  proj?: string
  size?: string
  is_shortcut: boolean
  is_favorite?: boolean
  status?: string
  target_id?: number | null
  author?: string
  content_html?: string
  content_text?: string
  file_url?: string
  file_size?: number
  index_status?: string
  index_message?: string
}

interface KbBreadcrumbNode {
  id: number | null | string
  name: string
}

interface KbMoveTargetNode {
  id: number
  title: string
  children: KbMoveTargetNode[]
}

interface KbMoveRequest {
  id: number
  target_folder_id?: number | null
  reference_id?: number
  placement?: 'inside' | 'before' | 'after'
}

// 状态声明
const loading = ref(false)
const currentFolderId = ref<number | null>(null)
const items = ref<KbExplorerItem[]>([])
const pathCrumbs = ref<KbBreadcrumbNode[]>([{ id: null, name: '质量知识库' }])
const selectedItem = ref<KbExplorerItem | null>(null)
const viewMode = ref<'grid' | 'table'>('grid')
const showNavPane = ref(true)
const showPreviewPane = ref(true)
const filterKeyword = ref('')
const fileUploadVisible = ref(false)
const incomingFiles = ref<File[]>([])
const fileDragActive = ref(false)
const reindexing = ref(false)
const copyingFile = ref(false)

const openFileUpload = (files: File[] = []) => {
  contextMenuVisible.value = false
  if (isViewingFavorites.value) {
    ElMessage.info('请先打开要存放附件的目录'); return
  }
  incomingFiles.value = files
  fileUploadVisible.value = true
}
const handleFileDragOver = (event: DragEvent) => {
  if (event.dataTransfer?.types.includes('Files')) { event.preventDefault(); fileDragActive.value = true }
}
const handleFileDragLeave = (event: DragEvent) => {
  if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) fileDragActive.value = false
}
const handleFileDrop = (event: DragEvent) => {
  fileDragActive.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  if (files.length) { event.preventDefault(); event.stopPropagation(); openFileUpload(files) }
}
const copySelectedFile = async () => {
  const item = contextMenuItem.value || selectedItem.value
  contextMenuVisible.value = false
  if (!item || copyingFile.value) return
  if (isViewingFavorites.value) { ElMessage.info('请先打开要存放副本的目录'); return }
  copyingFile.value = true
  try {
    await axios.post(`/api/kb/files/${item.id}/copy`, { parent_id: currentFolderId.value })
    refreshCurrentFolder(); ElMessage.success('已复制为独立附件')
  } catch (error: any) { ElMessage.error(error.response?.data?.detail || '复制未完成，请稍后重试') }
  finally { copyingFile.value = false }
}
const reindexSelectedFile = async () => {
  if (!selectedItem.value || reindexing.value) return
  reindexing.value = true
  try {
    const response = await axios.post(`/api/kb/files/${selectedItem.value.id}/reindex`)
    Object.assign(selectedItem.value, response.data)
    ElMessage.info(response.data.index_message)
  } catch (error: any) { ElMessage.error(error.response?.data?.detail || '索引未完成') }
  finally { reindexing.value = false }
}

// 可设计化配置：卡片尺寸与指标模式
const cardZoomSize = ref<'small' | 'medium' | 'large'>('medium')
const metricMode = ref<'words' | 'kb' | 'ctq'>('words')
const isViewingFavorites = ref(false)

// 历史栈 (前进/后退)
const historyStack = ref<(number | null | string)[]>([null])
const historyIndex = ref(0)

// 导航窗格与树
const quickProjects = ref<any[]>([])
const navTreeData = ref<any[]>([])
const navTreeRef = ref<any>(null)
const movingTreeNode = ref(false)

// 右键上下文菜单
const contextMenuVisible = ref(false)
const contextMenuPos = ref({ x: 0, y: 0 })
const contextMenuItem = ref<KbExplorerItem | null>(null)
const contextMenuTreeNode = ref<{ id: number; name: string } | null>(null)

// 弹窗状态
const moveModal = ref({
  visible: false,
  id: null as number | null,
  name: '',
  sourceParentId: 0,
  targetFolderId: 0,
  destination: '知识库根目录'
})

const moveTargetTree = computed<KbMoveTargetNode[]>(() => {
  const folders = (nodes: any[]): KbMoveTargetNode[] => nodes
    .filter(node => node.is_folder && node.id !== moveModal.value.id)
    .map(node => ({ id: node.id, title: node.title, children: folders(node.children || []) }))
  return [{ id: 0, title: '知识库根目录', children: folders(navTreeData.value) }]
})

const createModal = ref({
  visible: false,
  type: 'doc' as 'doc' | 'folder',
  name: '',
  icon: '📄'
})

const quickDocIcons = [
  { char: '📄', label: '规程' },
  { char: '📋', label: '质检' },
  { char: '⚙️', label: '零件' },
  { char: '🎯', label: 'CTQ' },
  { char: '🏭', label: 'SOP' },
  { char: '🧪', label: '实验' },
  { char: '🛡️', label: '防错' },
  { char: '📚', label: '手册' }
]

const quickFolderIcons = [
  { char: '📁', label: '目录' },
  { char: '📂', label: '资料' },
  { char: '🏷️', label: '分类' },
  { char: '📦', label: '模块' },
  { char: '🏭', label: '车间' },
  { char: '🔬', label: '试验' }
]

// 标准全量图标库体系 (制造业与质量工程分类)
const standardIconCategories = [
  {
    name: '规程与文档',
    icons: [
      { char: '📄', label: '标准规程' },
      { char: '📁', label: '分类目录' },
      { char: '📋', label: '检验基准' },
      { char: '📑', label: '作业指导' },
      { char: '📚', label: '质量手册' },
      { char: '📜', label: '资质认证' },
      { char: '🏷️', label: '标识规范' },
      { char: '📌', label: '关注重点' },
      { char: '💡', label: '改善提案' },
      { char: '🔗', label: '标准引用' }
    ]
  },
  {
    name: '质量与检验',
    icons: [
      { char: '🎯', label: 'CTQ红线' },
      { char: '🔬', label: '实验室' },
      { char: '🧪', label: '理化分析' },
      { char: '🔍', label: '外观检验' },
      { char: '⚖️', label: '计量校准' },
      { char: '📐', label: '几何公差' },
      { char: '🛡️', label: '防错防呆' },
      { char: '⏱️', label: '节拍节律' },
      { char: '📊', label: '统计SPC' },
      { char: '📈', label: 'CPK走势' }
    ]
  },
  {
    name: '工程与制造',
    icons: [
      { char: '⚙️', label: '精密零件' },
      { char: '🏭', label: '车间SOP' },
      { char: '🔩', label: '机械紧固' },
      { char: '🔧', label: '组装治具' },
      { char: '🗜️', label: '冲压模具' },
      { char: '🤖', label: '工业机器' },
      { char: '⚡', label: '电气控制' },
      { char: '🔌', label: '线束接插' },
      { char: '📦', label: '包装仓储' },
      { char: '🚚', label: '供应商交' }
    ]
  },
  {
    name: '状态与警示',
    icons: [
      { char: '🟢', label: '合格受控' },
      { char: '🟡', label: '预警评审' },
      { char: '🔴', label: '拦截遏制' },
      { char: '⚠️', label: '缺陷隐患' },
      { char: '🚨', label: '停线突发' },
      { char: '🛑', label: '8D整改' },
      { char: '⭐', label: '核心关键' },
      { char: '✅', label: '审核准入' }
    ]
  }
]

// 标准通用图标选择弹窗
const iconPickerModal = ref({
  visible: false,
  item: null as KbExplorerItem | null,
  selectedIcon: '📄'
})
const iconPickerSearch = ref('')

const filteredIconCategories = computed(() => {
  const kw = iconPickerSearch.value.trim().toLowerCase()
  if (!kw) return standardIconCategories
  return standardIconCategories.map(cat => {
    const filteredIcons = cat.icons.filter(ic =>
      ic.label.toLowerCase().includes(kw) || ic.char.includes(kw)
    )
    return { ...cat, icons: filteredIcons }
  }).filter(cat => cat.icons.length > 0)
})

const openIconPickerForCreate = () => {
  iconPickerModal.value.item = null
  iconPickerModal.value.selectedIcon = createModal.value.icon || (createModal.value.type === 'folder' ? '📁' : '📄')
  iconPickerSearch.value = ''
  iconPickerModal.value.visible = true
}

const openIconPickerForItem = (item: KbExplorerItem | null) => {
  if (!item) return
  iconPickerModal.value.item = item
  iconPickerModal.value.selectedIcon = item.icon || (item.type === 'folder' ? '📁' : '📄')
  iconPickerSearch.value = ''
  iconPickerModal.value.visible = true
}

const handleSelectIconCell = (char: string) => {
  iconPickerModal.value.selectedIcon = char
}

const confirmIconPicker = async () => {
  const iconChar = iconPickerModal.value.selectedIcon
  if (!iconChar) return
  if (iconPickerModal.value.item) {
    const item = iconPickerModal.value.item
    try {
      await axios.put('/api/kb/explorer/icon', {
        id: item.id,
        icon: iconChar
      })
      item.icon = iconChar
      if (selectedItem.value && selectedItem.value.id === item.id) {
        selectedItem.value.icon = iconChar
      }
      ElMessage.success('图标更新成功')
      fetchNavTreeData()
    } catch (err: any) {
      ElMessage.error(`更新图标失败: ${err.message || '网络异常'}`)
    }
  } else {
    createModal.value.icon = iconChar
  }
  iconPickerModal.value.visible = false
}

const shortcutModal = ref({
  visible: false,
  targetId: null as number | null,
  name: ''
})

const renameModal = ref({
  visible: false,
  item: null as KbExplorerItem | null,
  newName: ''
})

const searchModalVisible = ref(false)
const searchQuery = ref('')
const searching = ref(false)
const searchResults = ref<any[]>([])
const hasSearched = ref(false)

// AI 智写助手
const aiCopilotVisible = ref(false)

// 可供快捷方式引用的所有文档列表
const allAvailableDocs = ref<any[]>([])

// 计算属性：当前视口经过过滤后的项目列表
const displayItems = computed(() => {
  let list = items.value

  if (!filterKeyword.value.trim()) return list
  const kw = filterKeyword.value.trim().toLowerCase()
  return list.filter(
    (item) =>
      item.name.toLowerCase().includes(kw) ||
      (item.proj && item.proj.toLowerCase().includes(kw))
  )
})

// 统计全库标星规程总数
const starredCount = computed(() => {
  let count = 0
  const traverse = (nodes: any[]) => {
    for (const n of nodes) {
      if (n.is_favorite) count++
      if (n.children && n.children.length > 0) traverse(n.children)
    }
  }
  traverse(navTreeData.value)
  return count
})

// 状态文字解析
const getStatusShortLabel = (status?: string) => {
  switch (status) {
    case 'ACTIVE': return '🟢 已生效'
    case 'REVIEW': return '🟡 评审中'
    case 'DRAFT': return '⚪ 草稿'
    case 'OBSOLETE': return '🔴 废止'
    default: return '🟢 已生效'
  }
}

const getIconSizeLabel = () => {
  switch (cardZoomSize.value) {
    case 'small': return '小图标'
    case 'large': return '大图标'
    default: return '中图标'
  }
}

const getMetricLabel = () => {
  switch (metricMode.value) {
    case 'kb': return '大小 (KB)'
    case 'ctq': return 'CTQ项'
    default: return '字数'
  }
}

const getMetricColumnHeader = () => {
  switch (metricMode.value) {
    case 'kb': return '文件大小'
    case 'ctq': return 'CTQ特征'
    default: return '文档规模'
  }
}

// 格式化指标显示
const formatMetric = (item: KbExplorerItem) => {
  if (item.type === 'file') return `${((item.file_size || 0) / 1024).toFixed(1)} KB`
  if (item.type === 'folder') return item.proj || '工程目录'
  if (item.is_shortcut) return item.proj || '软链接引用'

  const textLen = (item.content_text || '').length
  if (metricMode.value === 'kb') {
    const kb = (textLen * 2.1 / 1024).toFixed(1)
    return `${kb} KB`
  }
  if (metricMode.value === 'ctq') {
    // 粗估关键特征条款数
    const matches = (item.content_html || '').match(/CTQ|公差|±|Ø/g)
    return `${matches ? matches.length : 1} 个特征项`
  }
  return `${textLen} 字`
}

// ----------------------------------------------------
// 1. 数据加载与导航
// ----------------------------------------------------
const loadFolderItems = async (folderId: number | null) => {
  loading.value = true
  try {
    const params = folderId ? { folder_id: folderId } : {}
    const [itemsRes, pathRes] = await Promise.all([
      axios.get('/api/kb/explorer/items', { params }),
      axios.get('/api/kb/explorer/path', { params })
    ])
    items.value = itemsRes.data || []
    pathCrumbs.value = pathRes.data || [{ id: null, name: '质量知识库' }]
    currentFolderId.value = folderId

    if (items.value.length > 0) {
      selectedItem.value = items.value[0]
    } else {
      selectedItem.value = null
    }
  } catch (err: any) {
    ElMessage.error(`获取目录列表失败: ${err.message || '网络连接异常'}`)
  } finally {
    loading.value = false
  }
}

const loadFavorites = async () => {
  loading.value = true
  isViewingFavorites.value = true
  try {
    const res = await axios.get('/api/kb/explorer/favorites')
    items.value = res.data || []
    pathCrumbs.value = [
      { id: null, name: '质量知识库' },
      { id: 'favorites', name: '⭐ 标星规程' }
    ]
    if (items.value.length > 0) {
      selectedItem.value = items.value[0]
    } else {
      selectedItem.value = null
    }
  } catch (err: any) {
    ElMessage.error(`获取标星列表失败: ${err.message || '网络异常'}`)
  } finally {
    loading.value = false
  }
}

const navigateTo = (folderId: any, recordHistory = true) => {
  if (folderId === 'favorites') {
    loadFavorites()
    return
  }
  isViewingFavorites.value = false
  if (recordHistory) {
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push(folderId)
    historyIndex.value = historyStack.value.length - 1
  }
  loadFolderItems(folderId)
}

const navBack = () => {
  if (historyIndex.value > 0) {
    historyIndex.value--
    const prev = historyStack.value[historyIndex.value]
    navigateTo(prev, false)
  }
}

const navForward = () => {
  if (historyIndex.value < historyStack.value.length - 1) {
    historyIndex.value++
    const nxt = historyStack.value[historyIndex.value]
    navigateTo(nxt, false)
  }
}

const navUp = () => {
  if (pathCrumbs.value.length > 1) {
    const parentCrumb = pathCrumbs.value[pathCrumbs.value.length - 2]
    navigateTo(parentCrumb.id)
  }
}

const refreshCurrentFolder = () => {
  if (isViewingFavorites.value) {
    loadFavorites()
  } else {
    loadFolderItems(currentFolderId.value)
  }
  fetchNavTreeData()
}

const toggleViewMode = () => {
  viewMode.value = viewMode.value === 'grid' ? 'table' : 'grid'
}

const handleIconSizeChange = (size: 'small' | 'medium' | 'large') => {
  cardZoomSize.value = size
  viewMode.value = 'grid'
}

const handleMetricChange = (mode: 'words' | 'kb' | 'ctq') => {
  metricMode.value = mode
}

const toggleViewFavorites = () => {
  if (isViewingFavorites.value) {
    // 退出标星视图，返回根目录或当前文件夹
    isViewingFavorites.value = false
    loadFolderItems(currentFolderId.value)
  } else {
    loadFavorites()
  }
}

// ----------------------------------------------------
// 2. 左侧树与快速访问
// ----------------------------------------------------
const fetchNavTreeData = async () => {
  try {
    const res = await axios.get('/api/kb/tree')
    navTreeData.value = res.data || []
    quickProjects.value = (res.data || [])
      .filter((n: any) => n.is_folder)
      .map((n: any) => ({ id: n.id, name: n.title, icon: n.icon || '📁' }))
  } catch (err) {
    console.error('加载导航树失败', err)
  }
}

const handleNavTreeNodeClick = async (data: any) => {
  if (data.is_folder) {
    navigateTo(data.id)
  } else {
    isViewingFavorites.value = false
    await loadFolderItems(data.parent_id || null)
    selectedItem.value = items.value.find(item => item.id === data.id) || null
  }
}

const allowNavTreeDrop = (draggingNode: any, dropNode: any, dropType: string) => {
  if (movingTreeNode.value || draggingNode.data.id === dropNode.data.id) return false
  if (dropType === 'inner' && (!dropNode.data.is_folder || draggingNode.data.parent_id === dropNode.data.id)) return false
  let ancestor = dropType === 'inner' ? dropNode : dropNode.parent
  while (ancestor) {
    if (ancestor.data?.id === draggingNode.data.id) return false
    ancestor = ancestor.parent
  }
  return true
}

const moveKbItem = async (payload: KbMoveRequest, successMessage: string): Promise<boolean> => {
  if (movingTreeNode.value) return false
  movingTreeNode.value = true
  try {
    await axios.put('/api/kb/explorer/move', payload)
    await Promise.all([
      fetchNavTreeData(),
      isViewingFavorites.value ? loadFavorites() : loadFolderItems(currentFolderId.value)
    ])
    ElMessage.success(successMessage)
    return true
  } catch (err: any) {
    await fetchNavTreeData()
    ElMessage.error(`移动失败: ${err.response?.data?.detail || err.message || '请重试'}`)
    return false
  } finally {
    movingTreeNode.value = false
  }
}

const handleNavTreeNodeDrop = async (draggingNode: any, dropNode: any, dropType: string) => {
  if (dropType === 'inner') {
    await moveKbItem({ id: draggingNode.data.id, target_folder_id: dropNode.data.id }, `已移至「${dropNode.data.title}」`)
  } else if (dropType === 'before' || dropType === 'after') {
    await moveKbItem({ id: draggingNode.data.id, reference_id: dropNode.data.id, placement: dropType }, '已更新目录位置与顺序')
  }
}

const openMoveModal = (id: number, name: string) => {
  if (movingTreeNode.value) return
  const source = navTreeRef.value?.getNode(id)?.data
  if (!source) {
    ElMessage.warning('目录已变更，请刷新后重试')
    return
  }
  const parentId = source.parent_id ?? 0
  moveModal.value = {
    visible: true,
    id,
    name,
    sourceParentId: parentId,
    targetFolderId: parentId,
    destination: parentId ? navTreeRef.value.getNode(parentId)?.data.title || '当前目录' : '知识库根目录'
  }
}

const handleMoveTargetClick = (data: KbMoveTargetNode, node: any) => {
  if (movingTreeNode.value) return
  moveModal.value.targetFolderId = data.id
  const names: string[] = []
  for (let ancestor = node; ancestor?.data?.title; ancestor = ancestor.parent) {
    names.unshift(ancestor.data.title)
  }
  moveModal.value.destination = names.join(' / ')
}

const submitMoveModal = async () => {
  if (moveModal.value.id === null || moveModal.value.targetFolderId === moveModal.value.sourceParentId) return
  const moved = await moveKbItem({
    id: moveModal.value.id,
    target_folder_id: moveModal.value.targetFolderId || null
  }, `已移至「${moveModal.value.destination}」`)
  if (moved) moveModal.value.visible = false
}

const fetchAllAvailableDocs = async () => {
  try {
    const res = await axios.get('/api/kb/tree')
    const docs: any[] = []
    const traverse = (nodes: any[]) => {
      for (const n of nodes) {
        if (!n.is_folder && n.biz_type !== 'SHORTCUT') {
          docs.push({ id: n.id, title: n.title, icon: n.icon })
        }
        if (n.children && n.children.length > 0) {
          traverse(n.children)
        }
      }
    }
    traverse(res.data || [])
    allAvailableDocs.value = docs
  } catch (err) {
    console.error('加载文档源列表失败', err)
  }
}

// ----------------------------------------------------
// 3. 视口交互：单选与双击打开新页面
// ----------------------------------------------------
const handleSelectItem = (item: KbExplorerItem) => {
  selectedItem.value = item
}

// 双击：文件夹直接下钻，规程文档默认在新标签页开启编辑
const handleItemDoubleClick = (item: KbExplorerItem) => {
  if (item.type === 'folder') {
    navigateTo(item.id)
  } else {
    // 默认在新标签页打开编辑 (更符合工程师多规程对照与查阅习惯，保持工作区目录不丢失)
    openEditorPage(item, true)
  }
}

// 打开独立编辑页面 (可指定当前页直达或新标签页)
const openEditorPage = (item: KbExplorerItem, newTab = false) => {
  if (item.type === 'file') { downloadOriginal(item); return }
  const docId = item.is_shortcut && item.target_id ? item.target_id : item.id
  if (!docId) {
    ElMessage.warning('无效的文档编号')
    return
  }
  const targetPath = `/kb/editor/${docId}`
  if (newTab) {
    const routeData = router.resolve({ path: targetPath })
    const win = window.open(routeData.href || targetPath, '_blank')
    if (!win || win.closed || typeof win.closed === 'undefined') {
      // 浏览器若拦截新弹窗，自动平滑在当前页面直达
      router.push(targetPath)
    }
  } else {
    // 当前标签页平滑路由跳转 (最稳定，0 拦截)
    router.push(targetPath)
  }
}

const downloadOriginal = async (item: KbExplorerItem) => {
  try {
    const response = await axios.get(item.file_url || `/api/kb/files/${item.id}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a'); link.href = url; link.download = item.name
    document.body.appendChild(link); link.click(); link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { ElMessage.error('下载失败，请检查原件是否仍然存在') }
}

// 标星切换 (双向响应式联动)
const toggleFavorite = async (item: KbExplorerItem) => {
  try {
    const res = await axios.put(`/api/kb/explorer/favorite/${item.id}`)
    item.is_favorite = res.data.is_favorite
    ElMessage.success(item.is_favorite ? `已将「${item.name}」标星关注` : '已取消标星关注')
    await fetchNavTreeData()
    if (isViewingFavorites.value) {
      if (!item.is_favorite) {
        items.value = items.value.filter(i => i.id !== item.id)
        if (selectedItem.value?.id === item.id) {
          selectedItem.value = items.value[0] || null
        }
      }
    }
  } catch (err: any) {
    ElMessage.error(`标星操作失败: ${err.message}`)
  }
}

// 变更文档状态
const handleStatusUpdate = async (item: KbExplorerItem, newStatus: string) => {
  try {
    await axios.put(`/api/kb/explorer/status/${item.id}`, { status: newStatus })
    item.status = newStatus
    ElMessage.success(`状态已更新为: ${getStatusShortLabel(newStatus)}`)
    contextMenuVisible.value = false
  } catch (err: any) {
    ElMessage.error(`更新状态失败: ${err.message}`)
  }
}

// ----------------------------------------------------
// 4. 右键上下文菜单与空白处新建对象
// ----------------------------------------------------
const handleItemContextMenu = (event: MouseEvent, item: KbExplorerItem) => {
  contextMenuTreeNode.value = null
  selectedItem.value = item
  contextMenuItem.value = item
  contextMenuPos.value = { x: event.clientX, y: event.clientY }
  contextMenuVisible.value = true
}

const handleNavTreeContextMenu = (event: MouseEvent, data: any) => {
  event.preventDefault()
  event.stopPropagation()
  contextMenuItem.value = null
  contextMenuTreeNode.value = { id: data.id, name: data.title }
  contextMenuPos.value = { x: event.clientX, y: event.clientY }
  contextMenuVisible.value = true
}

const handleViewportContextMenu = (event: MouseEvent) => {
  contextMenuTreeNode.value = null
  contextMenuItem.value = null
  contextMenuPos.value = { x: event.clientX, y: event.clientY }
  contextMenuVisible.value = true
}

const handleGlobalClick = () => {
  contextMenuVisible.value = false
}

// 上下文菜单统一动作分发
const handleContextMenuAction = (action: string) => {
  const targetItem = contextMenuItem.value
  contextMenuVisible.value = false
  if (action === 'move') {
    const moveTarget = contextMenuTreeNode.value || targetItem
    if (moveTarget) openMoveModal(moveTarget.id, moveTarget.name)
    return
  }
  if (!targetItem) return

  if (action === 'openInCurrent') {
    if (targetItem.type === 'folder') {
      navigateTo(targetItem.id)
    } else {
      openEditorPage(targetItem, false)
    }
  } else if (action === 'openInNewTab') {
    openEditorPage(targetItem, true)
  } else if (action === 'toggleFavorite') {
    toggleFavorite(targetItem)
  } else if (action === 'shortcut') {
    shortcutModal.value.targetId = targetItem.is_shortcut
      ? targetItem.target_id || null
      : targetItem.id
    shortcutModal.value.name = `${targetItem.name} - 引用标准`
    shortcutModal.value.visible = true
  } else if (action === 'rename') {
    handleRenameModal()
  } else if (action === 'changeIcon') {
    openIconPickerForItem(targetItem)
  } else if (action === 'delete') {
    handleDeleteItem()
  }
}

// 空白处右键专用辅助指令
const openCreateModalFromContext = (type: 'doc' | 'folder') => {
  contextMenuVisible.value = false
  openCreateModal(type)
}

const openShortcutModalFromContext = () => {
  contextMenuVisible.value = false
  openShortcutModal()
}

const refreshCurrentFolderFromContext = () => {
  contextMenuVisible.value = false
  refreshCurrentFolder()
}

const togglePreviewPaneFromContext = () => {
  contextMenuVisible.value = false
  showPreviewPane.value = !showPreviewPane.value
}

const handleIconSizeChangeFromContext = (size: 'small' | 'medium' | 'large') => {
  contextMenuVisible.value = false
  handleIconSizeChange(size)
}

const handleMetricChangeFromContext = (mode: 'words' | 'kb' | 'ctq') => {
  contextMenuVisible.value = false
  handleMetricChange(mode)
}

const toggleViewModeFromContext = () => {
  contextMenuVisible.value = false
  viewMode.value = 'table'
}

// ----------------------------------------------------
// 5. 新建 / 快捷方式 / 重命名 / 删除
// ----------------------------------------------------
const handleNewCommand = (cmd: string) => {
  if (cmd === 'doc' || cmd === 'folder') {
    openCreateModal(cmd as 'doc' | 'folder')
  } else if (cmd === 'shortcut') {
    openShortcutModal()
  }
}

const openCreateModal = (type: 'doc' | 'folder') => {
  createModal.value.type = type
  createModal.value.name = ''
  createModal.value.icon = type === 'folder' ? '📁' : '📄'
  createModal.value.visible = true
}

const submitCreateModal = async () => {
  if (!createModal.value.name.trim()) {
    ElMessage.warning('名称不能为空')
    return
  }

  try {
    if (createModal.value.type === 'folder') {
      await axios.post('/api/kb/explorer/folder', {
        parent_id: currentFolderId.value,
        name: createModal.value.name.trim(),
        icon: createModal.value.icon
      })
      ElMessage.success('文件夹创建成功')
    } else {
      const res = await axios.post('/api/kb/explorer/doc', {
        parent_id: currentFolderId.value,
        title: createModal.value.name.trim(),
        icon: createModal.value.icon
      })
      ElMessage.success('规范文档创建成功')
      createModal.value.visible = false
      await loadFolderItems(currentFolderId.value)
      fetchNavTreeData()
      openEditorPage(res.data)
      return
    }
    createModal.value.visible = false
    await loadFolderItems(currentFolderId.value)
    fetchNavTreeData()
  } catch (err: any) {
    ElMessage.error(`创建失败: ${err.message || '网络异常'}`)
  }
}

const openShortcutModal = () => {
  fetchAllAvailableDocs()
  if (selectedItem.value && selectedItem.value.type !== 'folder') {
    shortcutModal.value.targetId = selectedItem.value.is_shortcut
      ? selectedItem.value.target_id || null
      : selectedItem.value.id
    shortcutModal.value.name = `${selectedItem.value.name} - 快捷方式.lnk`
  } else {
    shortcutModal.value.targetId = null
    shortcutModal.value.name = ''
  }
  shortcutModal.value.visible = true
}

const handleShortcutTargetChange = (targetId: number) => {
  const target = allAvailableDocs.value.find((d) => d.id === targetId)
  if (target) {
    shortcutModal.value.name = `${target.title} - 快捷方式.lnk`
  }
}

const submitCreateShortcut = async () => {
  if (!shortcutModal.value.targetId) return
  try {
    await axios.post('/api/kb/explorer/shortcut', {
      parent_id: currentFolderId.value,
      target_doc_id: shortcutModal.value.targetId,
      name: shortcutModal.value.name.trim() || undefined
    })
    ElMessage.success('跨项目快捷方式已创建！源文档更新时实时同步')
    shortcutModal.value.visible = false
    await loadFolderItems(currentFolderId.value)
  } catch (err: any) {
    ElMessage.error(`创建快捷方式失败: ${err.message || '异常'}`)
  }
}

const handleRenameModal = () => {
  if (!selectedItem.value) return
  renameModal.value.item = selectedItem.value
  renameModal.value.newName = selectedItem.value.name
  renameModal.value.visible = true
}

const submitRename = async () => {
  if (!renameModal.value.item || !renameModal.value.newName.trim()) return
  try {
    await axios.put('/api/kb/explorer/rename', {
      id: renameModal.value.item.id,
      name: renameModal.value.newName.trim()
    })
    ElMessage.success('重命名成功')
    renameModal.value.visible = false
    await loadFolderItems(currentFolderId.value)
    fetchNavTreeData()
  } catch (err: any) {
    ElMessage.error(`重命名失败: ${err.message || '异常'}`)
  }
}

const handleDeleteItem = async () => {
  if (!selectedItem.value) return
  const isShortcut = selectedItem.value.is_shortcut
  const confirmMsg = isShortcut
    ? `确认删除快捷方式「${selectedItem.value.name}」？此操作不会影响源文档内容。`
    : `确认删除「${selectedItem.value.name}」？删除后无法恢复。`

  try {
    await ElMessageBox.confirm(confirmMsg, '删除确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    await axios.delete(`/api/kb/explorer/items/${selectedItem.value.id}`)
    ElMessage.success('已删除')
    await loadFolderItems(currentFolderId.value)
    fetchNavTreeData()
  } catch {}
}

const openAiCopilotForSelected = () => {
  aiCopilotVisible.value = true
}

const handleConfirmAiInsert = () => {
  if (selectedItem.value) {
    openEditorPage(selectedItem.value)
  }
}

const performSearch = async () => {
  if (!searchQuery.value.trim()) return
  searching.value = true
  hasSearched.value = true
  try {
    const res = await axios.get('/api/kb/search', { params: { q: searchQuery.value.trim() } })
    searchResults.value = res.data || []
  } catch (err: any) {
    ElMessage.error(`检索异常: ${err.message}`)
  } finally {
    searching.value = false
  }
}

const jumpToSearchResult = (docId: number) => {
  searchModalVisible.value = false
  const result = searchResults.value.find((item: any) => item.id === docId)
  openEditorPage({ id: docId, name: result?.title || '附件', type: result?.kind === 'file' ? 'file' : 'doc', is_shortcut: false })
}

// 3.3 预览窗格宽度拖拽调整 (支持本地记忆持久化 260px - 750px)
const getSavedPreviewWidth = (): number => {
  try {
    const val = localStorage.getItem('sqm_kb_preview_width')
    if (val) {
      const num = parseInt(val, 10)
      if (!isNaN(num) && num >= 260 && num <= 750) return num
    }
  } catch {}
  return 360
}

const previewPaneWidth = ref<number>(getSavedPreviewWidth())
const isResizingPreview = ref(false)
let previewResizeStartX = 0
let previewResizeStartWidth = 0

const startPreviewResize = (e: MouseEvent) => {
  e.preventDefault()
  isResizingPreview.value = true
  previewResizeStartX = e.clientX
  previewResizeStartWidth = previewPaneWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'

  const onMouseMove = (moveEvent: MouseEvent) => {
    if (!isResizingPreview.value) return
    // 窗格位于最右侧，鼠标向左拖拽加大宽度
    const dx = previewResizeStartX - moveEvent.clientX
    const newWidth = Math.min(Math.max(previewResizeStartWidth + dx, 260), 750)
    previewPaneWidth.value = newWidth
  }

  const onMouseUp = () => {
    isResizingPreview.value = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
    try {
      localStorage.setItem('sqm_kb_preview_width', String(previewPaneWidth.value))
    } catch {}
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

const handleGlobalKeyDown = (e: KeyboardEvent) => {
  // 当用户在任何输入框、文本域、富文本或浮动提词器/模态弹窗内打字时，严禁拦截任何按键与回车换行！
  const target = e.target as HTMLElement | null
  if (
    target && (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable ||
      target.closest('.teleprompter-floating-panel') ||
      target.closest('.el-dialog') ||
      target.closest('.el-overlay') ||
      target.closest('.win-modal-overlay') ||
      target.closest('.el-select-dropdown')
    )
  ) {
    return
  }

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    searchModalVisible.value = true
  }
  if (selectedItem.value) {
    if (e.key === 'F2') {
      e.preventDefault()
      handleRenameModal()
    } else if (e.key === 'Delete') {
      e.preventDefault()
      handleDeleteItem()
    } else if (e.key === 'Enter') {
      e.preventDefault()
      handleItemDoubleClick(selectedItem.value)
    }
  }
}

onMounted(() => {
  loadFolderItems(null)
  fetchNavTreeData()
  window.addEventListener('keydown', handleGlobalKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleGlobalKeyDown)
})
</script>

<style scoped>
.explorer-viewport { position: relative; }
.file-drop-hint { position: absolute; inset: 8px; z-index: 20; display: grid; place-items: center; pointer-events: none; border: 2px dashed #3b82f6; border-radius: 8px; background: rgba(239, 246, 255, .95); color: #1d4ed8; font-size: 15px; }
.attachment-index-info { padding: 10px 0; color: #64748b; font-size: 12px; line-height: 1.7; }
.attachment-index-info p { margin: 0; overflow-wrap: anywhere; }
.search-source-location { color: #64748b; font-size: 12px; margin-top: 6px; }
/* ==================== 全局 CSS 变量与基础框架 (100% 充满视口) ==================== */
.win-explorer-root {
  --win-bg: #f8fafc;
  --win-header-bg: #ffffff;
  --win-border: #e2e8f0;
  --win-border-dark: #cbd5e1;
  --win-text: #0f172a;
  --win-text-muted: #64748b;
  --win-accent: #0284c7;
  --win-accent-hover: #0369a1;
  --win-accent-light: #e0f2fe;
  --win-hover: #f1f5f9;
  --win-selected: #e0f2fe;
  --win-selected-border: #7dd3fc;

  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  flex: 1;
  min-height: 0;
  background-color: var(--win-bg);
  color: var(--win-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  overflow: hidden;
  position: relative;
  user-select: none;
}

/* ==================== 1. 顶部现代化控制栏 (Modern Command Bar) ==================== */
.win-toolbar {
  height: 48px;
  background: var(--win-header-bg);
  border-bottom: 1px solid var(--win-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  gap: 12px;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}

.tool-left-group {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.primary-create-btn {
  font-weight: 600;
  font-size: 12.5px;
  background: #0284c7;
  border-color: #0284c7;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 1px 2px rgba(2, 132, 199, 0.2);
}
.primary-create-btn:hover {
  background: #0369a1;
  border-color: #0369a1;
}

/* 选中项快速操作工具组 (去除了重复的文件名展示) */
.toolbar-selection-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.toolbar-v-divider {
  width: 1px;
  height: 20px;
  background: var(--win-border);
  margin: 0 4px;
}
.pill-action-btn {
  height: 26px;
  padding: 0 9px;
  font-size: 11.5px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}
.pill-action-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}
.delete-pill-btn {
  color: #dc2626;
  border-color: #fecaca;
}
.delete-pill-btn:hover {
  background: #fee2e2;
  border-color: #f87171;
  color: #b91c1c;
}

/* 视图分段控制器 (Segmented Control) */
.view-segmented-wrap {
  display: inline-flex;
  background: #f1f5f9;
  padding: 2px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}
.segmented-btn {
  border: none;
  background: transparent;
  padding: 3px 8px;
  font-size: 11.5px;
  font-weight: 500;
  color: #64748b;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}
.segmented-btn:hover {
  color: #0f172a;
}
.segmented-btn.active {
  background: #ffffff;
  color: #0284c7;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  font-weight: 600;
}

.size-pill-btn,
.metric-pill-btn,
.preview-toggle-btn {
  font-size: 12px;
  color: var(--win-text);
}
.preview-toggle-btn.active {
  background: var(--win-selected);
  color: var(--win-accent);
  border-color: var(--win-selected-border);
  font-weight: 600;
}

.tool-divider {
  width: 1px;
  height: 18px;
  background: var(--win-border);
  margin: 0 4px;
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-smart-btn {
  background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
  border: none;
  font-weight: 600;
  color: #ffffff;
}

/* 现代化全局检索胶囊按钮 */
.search-pill-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
  color: #64748b;
}
.search-pill-box:hover {
  background: #ffffff;
  border-color: #38bdf8;
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
  color: #0284c7;
}
.shortcut-key-tag {
  background: #e2e8f0;
  color: #475569;
  border-radius: 3px;
  padding: 0 4px;
  font-size: 10px;
  font-family: inherit;
}

.refresh-btn {
  color: #64748b;
}
.refresh-btn:hover {
  color: #0284c7;
}

/* 标星徽标 */
.star-badge-pill {
  margin-left: auto;
  background: #fef08a;
  color: #854d0e;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
}

/* ==================== 2. 地址导航栏 ==================== */
.win-nav-bar {
  height: 44px;
  background: #ffffff;
  border-bottom: 1px solid var(--win-border);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 10px;
  flex-shrink: 0;
}

.nav-history-arrows {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-circle-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  background: transparent;
  color: var(--win-text-muted);
  cursor: pointer;
  transition: all 0.15s;
}
.nav-circle-btn:hover:not(:disabled) {
  background: var(--win-hover);
  color: var(--win-text);
}
.nav-circle-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.address-container {
  flex: 1;
  height: 32px;
  border: 1px solid var(--win-border-dark);
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  background: #ffffff;
  overflow-x: auto;
  scrollbar-width: none;
}
.address-drive-icon {
  margin-right: 8px;
  font-size: 14px;
}
.address-crumbs-track {
  display: flex;
  align-items: center;
  font-size: 12.5px;
}
.crumb-node {
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--win-text);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.12s;
}
.crumb-node:hover {
  background: var(--win-hover);
  color: var(--win-accent);
}
.crumb-node.is-active {
  font-weight: 600;
  color: #0f172a;
}
.crumb-separator {
  color: #94a3b8;
  margin: 0 2px;
  font-size: 13px;
}

.filter-box {
  width: 240px;
}

/* ==================== 3. 主体工作区 ==================== */
.win-body-area {
  flex: 1;
  display: flex;
  overflow: hidden;
  background: #ffffff;
  min-height: 0;
}

.nav-side-pane {
  width: 240px;
  border-right: 1px solid var(--win-border);
  background: #f8fafc;
  padding: 12px 8px;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
  transition: width 0.22s cubic-bezier(0.16, 1, 0.3, 1),
              padding 0.22s cubic-bezier(0.16, 1, 0.3, 1),
              opacity 0.15s ease;
}
.nav-side-pane.is-collapsed {
  width: 0 !important;
  padding: 0 !important;
  border-right: none !important;
  overflow: hidden !important;
  opacity: 0;
  pointer-events: none;
}
.nav-section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 4px;
}
.nav-collapse-btn {
  background: transparent;
  border: none;
  font-size: 13px;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}
.nav-collapse-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}
.nav-btn-divider {
  width: 1px;
  height: 14px;
  background: var(--win-border);
  margin: 0 4px;
}
.nav-circle-btn.sidebar-toggle-btn.is-collapsed {
  color: var(--win-accent);
  background: #e0f2fe;
}
.nav-section-header {
  font-size: 11px;
  font-weight: 700;
  color: var(--win-text-muted);
  padding: 6px 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.nav-list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12.5px;
  color: var(--win-text);
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.1s;
}
.nav-list-item:hover {
  background: var(--win-hover);
}
.nav-list-item.active {
  background: var(--win-selected);
  color: var(--win-accent);
  font-weight: 600;
}
.star-quick-item {
  color: #b45309;
  font-weight: 600;
}
.star-quick-item.active {
  background: #fef3c7;
  color: #92400e;
}

.item-badge-icon {
  font-size: 14px;
}
.item-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-container {
  margin-top: 6px;
}
.win-nav-tree {
  background: transparent;
}
.move-target-tree {
  max-height: min(48vh, 360px);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
.move-target-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.move-item-name,
.move-destination {
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.move-item-name {
  margin: 0 0 12px;
}
.move-destination {
  margin: 12px 0 0;
  color: #64748b;
}
.tree-item-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  width: 100%;
  cursor: grab;
  user-select: none;
}
.tree-item-row:active {
  cursor: grabbing;
}
.tree-item-row.is-selected {
  font-weight: 600;
  color: var(--win-accent);
}
.tree-item-icon {
  font-size: 14px;
}
.tree-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 3.2 资源浏览区 */
.explorer-viewport {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  min-height: 0;
}

/* 网格大图标平铺卡片 - 动态卡片尺寸 */
.grid-layout-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: grid;
  gap: 12px;
  align-content: start;
}
.grid-layout-container.size-small {
  grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
  gap: 8px;
}
.grid-layout-container.size-medium {
  grid-template-columns: repeat(auto-fill, minmax(136px, 1fr));
  gap: 12px;
}
.grid-layout-container.size-large {
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.file-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px 10px 8px;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.12s ease;
  position: relative;
  text-align: center;
}
.file-card.card-small {
  padding: 8px 6px 6px 6px;
}
.file-card.card-large {
  padding: 18px 12px 14px 12px;
}

.file-card:hover {
  background: var(--win-hover);
  border-color: #e2e8f0;
}
.file-card.selected {
  background: var(--win-selected);
  border-color: var(--win-selected-border);
  box-shadow: 0 2px 6px rgba(2, 132, 199, 0.15);
}

/* 卡片顶层栏：标星与状态 */
.card-top-bar {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
  height: 18px;
}
.star-toggle-btn {
  background: transparent;
  border: none;
  font-size: 13px;
  color: #cbd5e1;
  cursor: pointer;
  padding: 0 2px;
  transition: transform 0.1s;
}
.star-toggle-btn:hover {
  transform: scale(1.2);
}
.star-toggle-btn.is-starred {
  color: #eab308;
}

.status-pill-mini {
  font-size: 9.5px;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 500;
}
.status-pill-mini.active { background: #dcfce7; color: #15803d; }
.status-pill-mini.review { background: #fef9c3; color: #a16207; }
.status-pill-mini.draft { background: #f1f5f9; color: #475569; }
.status-pill-mini.obsolete { background: #fee2e2; color: #b91c1c; }

.file-card-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
  position: relative;
}
.card-small .file-card-icon-wrap { width: 38px; height: 38px; }
.card-small .file-card-icon { font-size: 28px; }

.card-medium .file-card-icon-wrap { width: 54px; height: 54px; }
.card-medium .file-card-icon { font-size: 40px; }

.card-large .file-card-icon-wrap { width: 72px; height: 72px; }
.card-large .file-card-icon { font-size: 56px; }

.shortcut-badge {
  position: absolute;
  bottom: 0;
  left: 2px;
  width: 18px;
  height: 18px;
  background: #ffffff;
  border: 1.5px solid #0284c7;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  color: #0284c7;
  box-shadow: 0 2px 4px rgba(0,0,0,0.12);
}

.file-card-name {
  font-size: 12px;
  line-height: 1.4;
  color: var(--win-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  max-width: 100%;
  text-align: center;
  margin-top: 2px;
  margin-bottom: 2px;
  padding: 0 4px;
  box-sizing: border-box;
}
.card-small .file-card-name {
  font-size: 11px;
}
.card-large .file-card-name {
  font-size: 13px;
}
.file-card.selected .file-card-name {
  font-weight: 600;
  color: #0369a1;
}

.file-card-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: var(--win-text-muted);
  max-width: 95%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-folder-box {
  grid-column: 1 / -1;
  padding: 60px 0;
  text-align: center;
}
.empty-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  justify-content: center;
}

/* 详细信息表格视图 */
.table-layout-container {
  flex: 1;
  overflow-y: auto;
}
.win-detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  text-align: left;
}
.win-detail-table th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  padding: 8px 12px;
  border-bottom: 1px solid var(--win-border);
  color: var(--win-text-muted);
  font-weight: 600;
}
.win-detail-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
}
.win-detail-table tr:hover {
  background: var(--win-hover);
}
.win-detail-table tr.selected {
  background: var(--win-selected);
}

.table-star-btn {
  background: transparent;
  border: none;
  font-size: 14px;
  color: #cbd5e1;
  cursor: pointer;
}
.table-star-btn.is-starred {
  color: #eab308;
}

.status-pill-table {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}
.status-pill-table.active { background: #dcfce7; color: #15803d; }
.status-pill-table.review { background: #fef9c3; color: #a16207; }
.status-pill-table.draft { background: #f1f5f9; color: #475569; }
.status-pill-table.obsolete { background: #fee2e2; color: #b91c1c; }
.status-pill-table.folder { color: #cbd5e1; }

.name-cell-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.table-icon-wrap {
  position: relative;
  font-size: 18px;
  display: inline-flex;
}
.shortcut-badge-mini {
  position: absolute;
  bottom: -2px;
  left: -2px;
  font-size: 9px;
  font-weight: 800;
  color: #0284c7;
  background: #ffffff;
  border: 1px solid #0284c7;
  border-radius: 2px;
  line-height: 1;
  padding: 0 1px;
}

.type-pill {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.type-pill.folder { background: #fef3c7; color: #b45309; }
.type-pill.shortcut { background: #e0f2fe; color: #0369a1; font-weight: 600; }
.type-pill.doc { background: #f1f5f9; color: #475569; }

/* 3.3 右侧 Windows 预览窗格 (支持拖拽调整宽度) */
.preview-side-pane {
  position: relative;
  width: 360px;
  border-left: 1px solid var(--win-border);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

/* 窗格边缘拖拽把手 */
.preview-resize-bar {
  position: absolute;
  top: 0;
  left: -4px;
  width: 8px;
  bottom: 0;
  cursor: col-resize;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  transition: background-color 0.15s ease;
}
.preview-resize-bar:hover,
.preview-resize-bar.is-resizing {
  background-color: rgba(99, 102, 241, 0.22);
}
.preview-resize-bar:hover .resize-handle-line,
.preview-resize-bar.is-resizing .resize-handle-line {
  background-color: #6366f1;
  height: 42px;
}
.resize-handle-line {
  width: 2px;
  height: 24px;
  border-radius: 1px;
  background-color: #cbd5e1;
  transition: all 0.15s ease;
}
.preview-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--win-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.preview-header-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--win-text-muted);
}
.preview-close-btn {
  background: transparent;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
}
.preview-close-btn:hover {
  color: #0f172a;
}

.preview-body {
  padding: 12px 14px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
.preview-hero {
  text-align: center;
  margin-bottom: 10px;
}
.preview-hero-icon {
  font-size: 34px;
  display: inline-block;
  margin-bottom: 4px;
  cursor: pointer;
  position: relative;
  transition: transform 0.15s ease;
}
.preview-hero-icon:hover {
  transform: scale(1.15);
}
.clickable-hero-icon {
  position: relative;
}
.icon-edit-mini-badge {
  position: absolute;
  right: -6px;
  bottom: -2px;
  font-size: 11px;
  background: #ffffff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-hero-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--win-text);
  line-height: 1.35;
  margin: 0 0 6px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.preview-hero-tags {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.preview-star-btn {
  background: transparent;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 11px;
  padding: 2px 7px;
  cursor: pointer;
  color: #475569;
}
.preview-star-btn.is-starred {
  background: #fefce8;
  color: #a16207;
  border-color: #fde047;
}

.preview-status-pill {
  font-size: 10.5px;
  padding: 2px 7px;
  border-radius: 4px;
  font-weight: 500;
}
.preview-status-pill.active { background: #dcfce7; color: #15803d; }
.preview-status-pill.review { background: #fef9c3; color: #a16207; }
.preview-status-pill.draft { background: #f1f5f9; color: #475569; }
.preview-status-pill.obsolete { background: #fee2e2; color: #b91c1c; }

.shortcut-info-banner {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 10px;
  display: flex;
  gap: 6px;
  font-size: 11.5px;
  line-height: 1.4;
  color: #0369a1;
}
.banner-desc p {
  margin: 2px 0 0 0;
  color: #0284c7;
}

/* 紧凑型 2x2 元数据网格 (减负空间，零滚动条) */
.preview-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 12px;
  font-size: 11.5px;
}
.meta-grid-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  overflow: hidden;
}
.meta-k {
  color: var(--win-text-muted);
  font-size: 11px;
  white-space: nowrap;
}
.meta-v {
  color: var(--win-text);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: right;
}

.preview-content-section {
  border-top: 1px dashed var(--win-border);
  padding-top: 10px;
}
.section-title {
  font-size: 11.5px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--win-text);
}
.content-preview-box {
  font-size: 11.5px;
  line-height: 1.45;
  color: #334155;
  background: #fafafa;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
  max-height: 85px;
  overflow-y: auto;
  white-space: pre-wrap;
}

/* 固化吸底操作栏 */
.preview-footer {
  flex-shrink: 0;
  padding: 10px 14px;
  border-top: 1px solid var(--win-border);
  background: #ffffff;
}

.preview-action-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.preview-btn-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.preview-primary-btn {
  flex: 1;
}
.preview-sub-btn {
  flex-shrink: 0;
  white-space: nowrap;
}
.preview-ai-btn {
  width: 100%;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #cbd5e1;
  color: #475569;
  font-weight: 500;
  transition: all 0.15s ease;
}
.preview-ai-btn:hover {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  border-color: #94a3b8;
  color: #1e293b;
}
.preview-full-btn {
  width: 100%;
}

/* 新建弹窗图标交互样式 */
.create-icon-selection-wrap {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
}
.active-icon-badge {
  width: 58px;
  height: 58px;
  border: 2px dashed #6366f1;
  border-radius: 8px;
  background: #f5f3ff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s ease;
}
.active-icon-badge:hover {
  background: #ede9fe;
  transform: scale(1.05);
}
.badge-char {
  font-size: 26px;
  line-height: 1;
}
.badge-hint {
  font-size: 10px;
  color: #6366f1;
  margin-top: 2px;
}
.quick-icons-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.quick-chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.quick-icon-pill {
  padding: 3px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 11.5px;
  cursor: pointer;
  user-select: none;
  transition: all 0.12s ease;
}
.quick-icon-pill:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}
.quick-icon-pill.active {
  background: #ede9fe;
  border-color: #6366f1;
  color: #4f46e5;
  font-weight: 600;
}
.more-icons-btn {
  align-self: flex-start;
  padding: 0;
  font-size: 11.5px;
}

/* 标准图标选择器弹窗样式 */
.icon-picker-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.icon-picker-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}
.icon-current-preview {
  display: flex;
  align-items: center;
  gap: 8px;
}
.preview-char-box {
  width: 38px;
  height: 38px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-info-box {
  display: flex;
  flex-direction: column;
}
.preview-title {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
}
.preview-subtitle {
  font-size: 10.5px;
  color: #94a3b8;
}
.icon-search-wrap {
  width: 200px;
}
.icon-categories-scroll {
  max-height: 340px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}
.icon-cat-title {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.icon-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}
.icon-grid-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 6px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.12s ease;
  user-select: none;
}
.icon-grid-btn:hover {
  background: #f8fafc;
  border-color: #6366f1;
  transform: translateY(-1px);
}
.icon-grid-btn.active {
  background: #ede9fe;
  border-color: #6366f1;
  box-shadow: 0 0 0 1px #6366f1;
}
.grid-icon-char {
  font-size: 16px;
  line-height: 1;
}
.grid-icon-label {
  font-size: 11px;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.icon-empty-search {
  padding: 30px 10px;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
}

.preview-empty {
  padding: 60px 20px;
  text-align: center;
  color: var(--win-text-muted);
}
.preview-empty .empty-icon {
  font-size: 36px;
  margin-bottom: 12px;
}
.empty-tip {
  font-size: 12.5px;
  line-height: 1.5;
}

/* ==================== 4. 底部状态栏 ==================== */
.win-status-bar {
  height: 28px;
  background: #ffffff;
  border-top: 1px solid var(--win-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  font-size: 11.5px;
  color: var(--win-text-muted);
  flex-shrink: 0;
}
.status-left, .status-right {
  display: flex;
  gap: 14px;
}

/* ==================== 5. 右键上下文菜单 ==================== */
.win-context-menu {
  position: fixed;
  background: #ffffff;
  border: 1px solid var(--win-border-dark);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.14);
  padding: 4px;
  z-index: 9999;
  min-width: 195px;
}
.context-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--win-text);
  border-radius: 4px;
  cursor: pointer;
  position: relative;
  user-select: none;
}
.context-item > * {
  pointer-events: none;
}
/* 关键修复：确保二级子菜单自身可响应鼠标事件，防止移入时父级 hover 丢失 */
.context-item > .context-submenu {
  pointer-events: auto;
}
.context-item > .context-submenu > .context-item > * {
  pointer-events: none;
}
.context-item:hover {
  background: var(--win-selected);
  color: var(--win-accent);
}
.context-item.primary-action,
.context-item.primary-item {
  font-weight: 600;
  color: #0284c7;
}
.context-item.active {
  background: var(--win-selected);
  color: var(--win-accent);
  font-weight: 600;
}
.context-item.delete {
  color: #ef4444;
}
.context-item.delete:hover {
  background: #fef2f2;
}

.submenu-parent:hover > .context-submenu {
  display: block;
}
.context-submenu {
  display: none;
  position: absolute;
  left: calc(100% - 4px);
  top: -4px;
  background: #ffffff;
  border: 1px solid var(--win-border-dark);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.14);
  padding: 4px;
  min-width: 175px;
  z-index: 10000;
}
/* 隐形防抖鼠标感应桥梁 (Hover Bridge)，保证鼠标斜向滑动时二级菜单不消失 */
.context-submenu::before {
  content: '';
  position: absolute;
  top: 0;
  left: -14px;
  width: 18px;
  bottom: 0;
  background: transparent;
  pointer-events: auto;
}

.context-divider {
  height: 1px;
  background: #f1f5f9;
  margin: 3px 0;
}

/* ==================== 6. 全文检索弹窗 ==================== */
.search-results-box {
  margin-top: 14px;
  max-height: 420px;
  overflow-y: auto;
}
.search-res-item {
  padding: 10px;
  border-radius: 6px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
}
.search-res-item:hover {
  background: var(--win-hover);
}
.res-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}
.res-date {
  margin-left: auto;
  font-size: 11px;
  color: var(--win-text-muted);
  font-weight: normal;
}
.res-snippet {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}
.no-res, .search-tip {
  padding: 30px;
  text-align: center;
  color: var(--win-text-muted);
  font-size: 13px;
}
</style>
