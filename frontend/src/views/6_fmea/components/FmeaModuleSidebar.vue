<template>
  <aside
    class="fmea-module-sidebar"
    :class="{ 'is-collapsed': collapsed, 'is-resizing': isResizing }"
    :style="{ width: collapsed ? '0px' : `${sidebarWidth}px` }"
  >
    <!-- 侧边栏右边缘拖拽调整器与折叠收起按钮 -->
    <div
      v-if="!collapsed"
      class="sidebar-resizer"
      :class="{ 'is-resizing': isResizing }"
      title="按住鼠标拖拽调整宽度 (双击恢复默认 270px)"
      @mousedown.prevent.stop="onStartResize"
      @dblclick.prevent.stop="onResetResize"
    >
      <button
        type="button"
        class="sidebar-edge-collapse-btn"
        title="收起左侧栏"
        @mousedown.stop
        @click.stop="emit('toggle-collapse')"
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10 4l-4 4 4 4" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </div>

    <div v-show="!collapsed" class="sidebar-inner">
      <!-- 【信标 1】左栏专属实时导航检索条：同时过滤上方模块画板树与下方当前画板大纲 -->
      <div class="sidebar-filter-bar">
        <div class="sf-box">
          <svg class="sf-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.65">
            <circle cx="7" cy="7" r="4.3" />
            <path d="M10.3 10.3l3 3" stroke-linecap="round" />
          </svg>
          <input
            v-model="sidebarQuery"
            type="text"
            class="sf-input"
            :placeholder="sidebarSearchPlaceholder"
          />
          <button
            v-if="sidebarQuery"
            type="button"
            class="sf-clear"
            title="清空过滤"
            @click="sidebarQuery = ''"
          >
            ×
          </button>
        </div>
      </div>

      <!-- 【信标 2】& 【信标 5】：模式切换 Tab 胶囊栏与新建画板/布局切换 -->
      <div class="sidebar-tabs-bar">
        <div class="tree-mode-pills">
          <button
            type="button"
            class="tm-pill"
            :class="{ active: treeViewMode === 'assembly' }"
            title="SolidWorks 风格多级装配特征结构树：展现系统总成、子装配引用与共用借用件"
            @click="selectTab('assembly')"
          >
            🌳 装配树
          </button>
          <button
            type="button"
            class="tm-pill"
            :class="{ active: treeViewMode === 'grouped' }"
            title="按业务系统分类清单"
            @click="selectTab('grouped')"
          >
            📁 分类
          </button>
          <button
            type="button"
            class="tm-pill"
            :class="{ active: treeViewMode === 'outline' }"
            title="当前画板空间元素大纲 (图纸热点 Pins / 模块节点 / 配合接口)"
            @click="selectTab('outline')"
          >
            📑 大纲
            <span v-if="filteredOutlineTotal > 0" class="tab-badge">{{ filteredOutlineTotal }}</span>
          </button>
        </div>

        <div class="sidebar-tabs-actions">
          <button
            type="button"
            class="icon-mini-btn"
            :class="{ active: treeLayout === 'split' }"
            :title="treeLayout === 'tab' ? '当前为 Tab 独占全高模式，点击切换为上下分屏模式' : '当前为上下分屏模式，点击切换为 Tab 独占全高模式'"
            @click="toggleTreeLayout"
          >
            <svg v-if="treeLayout === 'tab'" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
              <rect x="2.5" y="2.5" width="11" height="11" rx="2" />
              <path d="M2.5 8h11" stroke-dasharray="2 1.5" />
            </svg>
            <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
              <rect x="2.5" y="2.5" width="11" height="11" rx="2" />
              <path d="M2.5 6.5h11" />
            </svg>
          </button>
          <button class="icon-mini-btn" title="新建模块画板" @click="openCreateForm()">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.75">
              <path d="M8 3v10M3 8h10" stroke-linecap="round" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 轻量内嵌新建画板卡片 -->
      <div v-if="creating" class="inline-create-box">
        <input
          ref="newGroupInputRef"
          v-model="form.group_name"
          class="mini-input"
          list="fmea-group-datalist"
          placeholder="系统分组 (如 关节执行器系统)"
        />
        <datalist id="fmea-group-datalist">
          <option v-for="g in groups" :key="g.group_name" :value="g.group_name" />
        </datalist>
        <input
          ref="newBoardNameInputRef"
          v-model="form.name"
          class="mini-input"
          placeholder="模块画板名称 (回车创建)"
          @keyup.enter="submitCreate"
          @keyup.esc="creating = false"
        />
        <div class="create-type-row">
          <div class="type-pills">
            <button
              v-for="tp in ['DFMEA', 'PFMEA', 'MIXED']"
              :key="tp"
              type="button"
              class="tp-pill"
              :class="{ active: form.board_type === tp }"
              @click="form.board_type = tp"
            >
              {{ tp === 'MIXED' ? '综合' : tp }}
            </button>
          </div>
          <div class="create-btns">
            <button type="button" class="txt-btn" @click="creating = false">取消</button>
            <button type="button" class="pri-mini-btn" @click="submitCreate">创建</button>
          </div>
        </div>
      </div>

      <!-- 模块画板目录树（SolidWorks 装配特征树 / 分类） -->
      <div
        v-show="treeLayout === 'split' || treeViewMode !== 'outline'"
        class="sec-block boards-sec"
        :class="{ 'is-full-height': treeLayout === 'tab' }"
      >
        <div class="tree-scroll">
          <!-- 模式 1：SolidWorks 装配特征树 -->
          <div v-if="treeViewMode === 'assembly'" class="assembly-tree-scroll">
            <div v-if="allFlatBoards.length === 0" class="outline-empty">
              未找到匹配的装配画板
            </div>

            <template v-for="b in allFlatBoards" :key="b.id">
              <div
                class="board-item"
                :class="{
                  active: b.id === activeBoardId,
                  'is-dragging': draggedBoard?.id === b.id,
                  'is-drop-target': hoverBoardTargetId === b.id,
                  'is-assembly-root': getBoardBomChildren(b).length > 0
                }"
                draggable="true"
                :title="`${b.name}（按住可拖拽至画布嵌入为子模块，或拖拽至其他画板建立装配引用）`"
                @dragstart="onBoardDragStart($event, b)"
                @dragend="onBoardDragEnd"
                @dragover.prevent="onBoardDragOver($event, b)"
                @dragleave="onBoardDragLeave(b)"
                @drop.prevent="onBoardDropOnBoard($event, b)"
                @click="$emit('select-board', b.id)"
                @contextmenu.prevent="openBoardContextMenu($event, b)"
              >
                <!-- 展开/收起 SolidWorks 装配特征树按钮 -->
                <button
                  v-if="getBoardBomChildren(b).length > 0"
                  type="button"
                  class="board-exp-btn"
                  :class="{ expanded: isBoardExpanded(b.id) }"
                  title="展开/收起 SolidWorks 装配特征树"
                  @click.stop="toggleBoardExpand(b.id, $event)"
                >
                  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </button>
                <span v-else class="board-exp-placeholder" />

                <span class="board-drag-handle" title="按住拖拽至画布嵌入为子模块，或拖拽至其他画板建立引用">⋮⋮</span>

                <!-- 区分装配总成图标 vs 单模块图标 -->
                <span v-if="getBoardBomChildren(b).length > 0" class="assembly-cube-ico" title="SolidWorks 装配体总成">📦</span>
                <svg v-else class="board-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
                  <rect x="2.2" y="2.5" width="11.6" height="11" rx="2.2" />
                  <circle cx="6" cy="6.5" r="1.1" />
                  <circle cx="10.2" cy="9.6" r="1.1" />
                  <path d="M7 7.1l2.2 1.9" stroke-linecap="round" />
                </svg>

                <input
                  v-if="renamingBoardId === b.id"
                  v-model="inlineDraft"
                  class="row-inline-input"
                  @click.stop
                  @blur="commitBoardRename(b)"
                  @keyup.enter="commitBoardRename(b)"
                  @keyup.esc="renamingBoardId = null"
                />
                <span v-else class="board-name" :title="`${b.name} (${b.group_name})`">{{ b.name }}</span>

                <span v-if="getBoardBomChildren(b).length > 0" class="assembly-tag">总成</span>

                <span
                  v-if="b.high_risk_count > 0"
                  class="risk-dot high"
                  :title="`${b.high_risk_count} 项高危 / 共 ${b.total_items} 项`"
                />
                <span v-if="b.total_items > 0" class="board-badge">{{ b.total_items }}</span>
                <button
                  type="button"
                  class="row-more-btn"
                  title="更多操作"
                  @click.stop="openBoardContextMenu($event, b)"
                >
                  ⋯
                </button>
              </div>

              <!-- SolidWorks 装配特征树展开分支 -->
              <div
                v-if="getBoardBomChildren(b).length > 0 && isBoardExpanded(b.id)"
                class="board-bom-branch"
              >
                <div
                  v-for="ch in getBoardBomChildren(b)"
                  :key="ch.node_id"
                  class="bom-child-row"
                  :class="{
                    active: selection?.kind === 'node' && selection?.id === ch.node_id && b.id === activeBoardId
                  }"
                  :title="ch.ref_type === 'sub_board' ? `SolidWorks 子装配引用 <实例${ch.instance_index}>：点击画布定位，双击穿透下钻` : `共用借用件 (${ch.unit_code})`"
                  @click.stop="onBomChildClick(b, ch)"
                  @dblclick.stop="onBomChildDblClick(b, ch)"
                >
                  <span class="tree-branch-line">↳</span>
                  <span
                    v-if="ch.ref_type === 'sub_board'"
                    class="bom-ref-pill sub"
                    :title="`SolidWorks 外部装配引用 <实例 ${ch.instance_index}>`"
                  >
                    🔗 引用&lt;{{ ch.instance_index }}&gt;
                  </span>
                  <span
                    v-else
                    class="bom-ref-pill shared"
                    :title="`跨画板共用借用件 (${ch.unit_code})`"
                  >
                    ⚙️ 借用
                  </span>
                  <span class="bom-child-title" :title="ch.title">{{ ch.title }}</span>
                  <span
                    v-if="ch.high_risk_count > 0"
                    class="risk-dot high"
                    :title="`${ch.high_risk_count} 项高危`"
                  />
                  <button
                    v-if="ch.ref_type === 'sub_board' && ch.sub_board_id"
                    type="button"
                    class="child-drill-btn"
                    title="双击或点击穿透下钻至子模块"
                    @click.stop="onBomChildDblClick(b, ch)"
                  >
                    ↘
                  </button>
                </div>
              </div>
            </template>
          </div>

          <!-- 模式 2：业务系统分组清单（内嵌装配子树展开能力） -->
          <div v-else class="grouped-tree-scroll">
            <div v-if="filteredGroups.length === 0" class="outline-empty">
              未找到匹配的系统或画板
            </div>

            <div v-for="grp in filteredGroups" :key="grp.group_name" class="tree-group">
              <div
                class="group-row"
                :class="{ 'is-drop-group-target': hoverGroupTargetName === grp.group_name }"
                @dragover.prevent="onGroupDragOver($event, grp.group_name)"
                @dragleave="onGroupDragLeave(grp.group_name)"
                @drop.prevent="onGroupDrop($event, grp.group_name)"
                @click="toggleGroup(grp.group_name)"
                @contextmenu.prevent="openGroupContextMenu($event, grp.group_name, grp.boards.length)"
              >
                <svg
                  class="chev-ico"
                  :class="{ folded: isGroupFolded(grp.group_name) }"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.75"
                >
                  <path d="M5 6l3 3 3-3" stroke-linecap="round" stroke-linejoin="round" />
                </svg>

                <input
                  v-if="renamingGroupName === grp.group_name"
                  v-model="inlineDraft"
                  class="row-inline-input"
                  @click.stop
                  @blur="commitGroupRename(grp.group_name)"
                  @keyup.enter="commitGroupRename(grp.group_name)"
                  @keyup.esc="renamingGroupName = null"
                />
                <span v-else class="group-name" :title="grp.group_name">{{ grp.group_name }}</span>

                <span class="group-cnt">{{ grp.boards.length }}</span>
                <button
                  type="button"
                  class="row-more-btn"
                  title="分组操作"
                  @click.stop="openGroupContextMenu($event, grp.group_name, grp.boards.length)"
                >
                  ⋯
                </button>
              </div>

              <div v-show="!isGroupFolded(grp.group_name)" class="group-children">
                <template v-for="b in grp.boards" :key="b.id">
                  <div
                    class="board-item"
                    :class="{
                      active: b.id === activeBoardId,
                      'is-dragging': draggedBoard?.id === b.id,
                      'is-drop-target': hoverBoardTargetId === b.id,
                      'is-assembly-root': getBoardBomChildren(b).length > 0
                    }"
                    draggable="true"
                    :title="`${b.name}（按住可拖拽至画布嵌入为子模块，或拖拽至其他画板建立装配引用）`"
                    @dragstart="onBoardDragStart($event, b)"
                    @dragend="onBoardDragEnd"
                    @dragover.prevent="onBoardDragOver($event, b)"
                    @dragleave="onBoardDragLeave(b)"
                    @drop.prevent="onBoardDropOnBoard($event, b)"
                    @click="$emit('select-board', b.id)"
                    @contextmenu.prevent="openBoardContextMenu($event, b)"
                  >
                    <button
                      v-if="getBoardBomChildren(b).length > 0"
                      type="button"
                      class="board-exp-btn"
                      :class="{ expanded: isBoardExpanded(b.id) }"
                      title="展开/收起 SolidWorks 装配特征树"
                      @click.stop="toggleBoardExpand(b.id, $event)"
                    >
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round" />
                      </svg>
                    </button>
                    <span v-else class="board-exp-placeholder" />

                    <span class="board-drag-handle" title="按住拖拽至画布嵌入为子模块，或拖拽至其他分组">⋮⋮</span>

                    <span v-if="getBoardBomChildren(b).length > 0" class="assembly-cube-ico" title="SolidWorks 装配体总成">📦</span>
                    <svg v-else class="board-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
                      <rect x="2.2" y="2.5" width="11.6" height="11" rx="2.2" />
                      <circle cx="6" cy="6.5" r="1.1" />
                      <circle cx="10.2" cy="9.6" r="1.1" />
                      <path d="M7 7.1l2.2 1.9" stroke-linecap="round" />
                    </svg>

                    <input
                      v-if="renamingBoardId === b.id"
                      v-model="inlineDraft"
                      class="row-inline-input"
                      @click.stop
                      @blur="commitBoardRename(b)"
                      @keyup.enter="commitBoardRename(b)"
                      @keyup.esc="renamingBoardId = null"
                    />
                    <span v-else class="board-name" :title="`${b.name}（可拖拽嵌入画布或拖至其他分组）`">{{ b.name }}</span>

                    <span v-if="getBoardBomChildren(b).length > 0" class="assembly-tag">总成</span>

                    <span
                      v-if="b.high_risk_count > 0"
                      class="risk-dot high"
                      :title="`${b.high_risk_count} 项高危 / 共 ${b.total_items} 项`"
                    />
                    <span v-if="b.total_items > 0" class="board-badge">{{ b.total_items }}</span>
                    <button
                      type="button"
                      class="row-more-btn"
                      title="更多操作（重命名 / 嵌入为子模块 / 复制 / 删除）"
                      @click.stop="openBoardContextMenu($event, b)"
                    >
                      ⋯
                    </button>
                  </div>

                  <!-- SolidWorks 装配特征树展开分支 -->
                  <div
                    v-if="getBoardBomChildren(b).length > 0 && isBoardExpanded(b.id)"
                    class="board-bom-branch"
                  >
                    <div
                      v-for="ch in getBoardBomChildren(b)"
                      :key="ch.node_id"
                      class="bom-child-row"
                      :class="{
                        active: selection?.kind === 'node' && selection?.id === ch.node_id && b.id === activeBoardId
                      }"
                      :title="ch.ref_type === 'sub_board' ? `SolidWorks 子装配引用 <实例${ch.instance_index}>：点击画布定位，双击穿透下钻` : `共用借用件 (${ch.unit_code})`"
                      @click.stop="onBomChildClick(b, ch)"
                      @dblclick.stop="onBomChildDblClick(b, ch)"
                    >
                      <span class="tree-branch-line">↳</span>
                      <span
                        v-if="ch.ref_type === 'sub_board'"
                        class="bom-ref-pill sub"
                        :title="`SolidWorks 外部装配引用 <实例 ${ch.instance_index}>`"
                      >
                        🔗 引用&lt;{{ ch.instance_index }}&gt;
                      </span>
                      <span
                        v-else
                        class="bom-ref-pill shared"
                        :title="`跨画板共用借用件 (${ch.unit_code})`"
                      >
                        ⚙️ 借用
                      </span>
                      <span class="bom-child-title" :title="ch.title">{{ ch.title }}</span>
                      <span
                        v-if="ch.high_risk_count > 0"
                        class="risk-dot high"
                        :title="`${ch.high_risk_count} 项高危`"
                      />
                      <button
                        v-if="ch.ref_type === 'sub_board' && ch.sub_board_id"
                        type="button"
                        class="child-drill-btn"
                        title="双击或点击穿透下钻至子模块"
                        @click.stop="onBomChildDblClick(b, ch)"
                      >
                        ↘
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 下半区/主区：当前画板空间元素大纲 (Pins / 模块节点 / 配合接口) -->
      <div
        v-show="treeLayout === 'split' || treeViewMode === 'outline'"
        class="sec-block outline-sec"
        :class="{ 'is-full-height': treeLayout === 'tab' }"
      >
        <div v-if="treeLayout === 'split'" class="sec-header">
          <span class="sec-title">当前画板大纲</span>
          <span class="sec-meta">{{ filteredOutlineTotal }}</span>
        </div>

        <div class="outline-scroll">
          <div v-if="filteredOutlineTotal === 0" class="outline-empty">
            {{ sidebarQuery ? '大纲无匹配元素' : '画布暂无节点或打点' }}
          </div>

          <!-- 1. 图纸热点 Pins -->
          <template v-if="filteredPins.length > 0">
            <div class="sub-cat">图纸热点</div>
            <div
              v-for="p in filteredPins"
              :key="p.pin.id"
              class="outline-row"
              :class="{ active: selection?.kind === 'pin' && selection?.id === p.pin.id }"
              @click="$emit('focus-element', { kind: 'pin', id: p.pin.id, boardImgId: p.imgId })"
              @contextmenu.prevent="
                openOutlineContextMenu($event, { kind: 'pin', id: p.pin.id, boardImgId: p.imgId }, p.pin.title)
              "
            >
              <span class="pin-idx">#{{ p.pin.num }}</span>

              <input
                v-if="renamingOutlineKey === `pin:${p.pin.id}`"
                v-model="inlineDraft"
                class="row-inline-input"
                @click.stop
                @blur="commitOutlineRename({ kind: 'pin', id: p.pin.id, boardImgId: p.imgId }, p.pin.title)"
                @keyup.enter="commitOutlineRename({ kind: 'pin', id: p.pin.id, boardImgId: p.imgId }, p.pin.title)"
                @keyup.esc="renamingOutlineKey = null"
              />
              <span v-else class="ol-label" :title="p.pin.title">{{ p.pin.title }}</span>

              <span v-if="getPinOrEdgeStat('pin', p.pin.id).high > 0" class="risk-dot high" />
              <span v-if="getPinOrEdgeStat('pin', p.pin.id).total > 0" class="ol-cnt">
                {{ getPinOrEdgeStat('pin', p.pin.id).total }}
              </span>
              <button
                type="button"
                class="row-more-btn"
                title="操作此热点"
                @click.stop="
                  openOutlineContextMenu($event, { kind: 'pin', id: p.pin.id, boardImgId: p.imgId }, p.pin.title)
                "
              >
                ⋯
              </button>
            </div>
          </template>

          <!-- 2. 模块与工序节点（含子模块黑盒节点与跨画板共用节点标识） -->
          <template v-if="filteredNodes.length > 0">
            <div class="sub-cat">模块 / 工序节点</div>
            <div
              v-for="nd in filteredNodes"
              :key="nd.id"
              class="outline-row"
              :class="{ active: selection?.kind === 'node' && selection?.id === nd.id }"
              @click="$emit('focus-element', { kind: 'node', id: nd.id })"
              @dblclick="nd.sub_board_id ? $emit('drill-sub-board', nd.sub_board_id) : undefined"
              @contextmenu.prevent="openOutlineContextMenu($event, { kind: 'node', id: nd.id }, nd.title, nd)"
            >
              <!-- 子画板节点图标 vs 共用件节点图标 vs 普通节点图标 -->
              <svg
                v-if="nd.sub_board_id"
                class="ol-ico is-sub"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                stroke-width="1.65"
              >
                <rect x="2" y="2.5" width="12" height="11" rx="2" />
                <path d="M8 2.5v11M2 8h12" />
              </svg>
              <svg
                v-else-if="nd.unit_code"
                class="ol-ico is-shared"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                stroke-width="1.65"
              >
                <path d="M6.5 9.5l3-3M5.2 11.2a2.5 2.5 0 010-3.5l1.3-1.3M10.8 4.8a2.5 2.5 0 010 3.5l-1.3 1.3" stroke-linecap="round" />
              </svg>
              <svg v-else class="ol-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="2.5" y="3.5" width="11" height="9" rx="2" />
              </svg>

              <input
                v-if="renamingOutlineKey === `node:${nd.id}`"
                v-model="inlineDraft"
                class="row-inline-input"
                @click.stop
                @blur="commitOutlineRename({ kind: 'node', id: nd.id }, nd.title)"
                @keyup.enter="commitOutlineRename({ kind: 'node', id: nd.id }, nd.title)"
                @keyup.esc="renamingOutlineKey = null"
              />
              <span
                v-else
                class="ol-label"
                :title="nd.sub_board_id ? `${nd.title} (双击下钻子画板)` : nd.title"
              >
                {{ nd.title }}
              </span>

              <span v-if="getNodeOutlineStat(nd).high > 0" class="risk-dot high" />
              <span v-if="getNodeOutlineStat(nd).total > 0" class="ol-cnt">
                {{ getNodeOutlineStat(nd).total }}
              </span>
              <button
                type="button"
                class="row-more-btn"
                title="操作此节点"
                @click.stop="openOutlineContextMenu($event, { kind: 'node', id: nd.id }, nd.title, nd)"
              >
                ⋯
              </button>
            </div>
          </template>

          <!-- 3. 配合与传递接口连线 -->
          <template v-if="filteredEdges.length > 0">
            <div class="sub-cat">配合与传递接口</div>
            <div
              v-for="ed in filteredEdges"
              :key="ed.id"
              class="outline-row"
              :class="{ active: selection?.kind === 'edge' && selection?.id === ed.id }"
              @click="$emit('focus-element', { kind: 'edge', id: ed.id })"
              @contextmenu.prevent="openOutlineContextMenu($event, { kind: 'edge', id: ed.id }, ed.label || '配合接口')"
            >
              <svg class="ol-ico" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M2.5 11.5C6 11.5 6 4.5 9.5 4.5h4" stroke-linecap="round" />
                <circle cx="2.5" cy="11.5" r="1.2" />
                <circle cx="13.5" cy="4.5" r="1.2" />
              </svg>

              <input
                v-if="renamingOutlineKey === `edge:${ed.id}`"
                v-model="inlineDraft"
                class="row-inline-input"
                @click.stop
                @blur="commitOutlineRename({ kind: 'edge', id: ed.id }, ed.label)"
                @keyup.enter="commitOutlineRename({ kind: 'edge', id: ed.id }, ed.label)"
                @keyup.esc="renamingOutlineKey = null"
              />
              <span v-else class="ol-label" :title="ed.label">{{ ed.label || '未命名接口' }}</span>

              <span v-if="getPinOrEdgeStat('edge', ed.id).high > 0" class="risk-dot high" />
              <span v-if="getPinOrEdgeStat('edge', ed.id).total > 0" class="ol-cnt">
                {{ getPinOrEdgeStat('edge', ed.id).total }}
              </span>
              <button
                type="button"
                class="row-more-btn"
                title="操作此接口连线"
                @click.stop="openOutlineContextMenu($event, { kind: 'edge', id: ed.id }, ed.label || '配合接口')"
              >
                ⋯
              </button>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 【信标 1】全局轻量右键上下文菜单 -->
    <Teleport to="body">
      <div
        v-if="ctxMenu.visible"
        class="fmea-ctx-backdrop"
        @mousedown="closeContextMenu"
        @contextmenu.prevent="closeContextMenu"
      >
        <div
          class="fmea-ctx-menu"
          :style="{ left: `${ctxMenu.x}px`, top: `${ctxMenu.y}px` }"
          @mousedown.stop
        >
          <!-- A. 画板项菜单 -->
          <template v-if="ctxMenu.kind === 'board' && ctxMenu.board">
            <div class="ctx-head">{{ ctxMenu.board.name }}</div>
            <button type="button" class="ctx-item" @click="triggerBoardInlineRename(ctxMenu.board)">
              <span>重命名画板</span>
            </button>
            <button
              type="button"
              class="ctx-item"
              :disabled="ctxMenu.board.id === activeBoardId"
              :title="ctxMenu.board.id === activeBoardId ? '不能将当前正在编辑的画板嵌入自身' : '作为可双击下钻的子模块黑盒节点放入当前画布'"
              @click="triggerInsertAsSubBoard(ctxMenu.board)"
            >
              <span>作为子模块插入当前画布</span>
              <span class="ctx-tag">BOM</span>
            </button>
            <button type="button" class="ctx-item" @click="triggerDuplicateBoard(ctxMenu.board)">
              <span>复制画板（创建变体）</span>
            </button>
            <button type="button" class="ctx-item" @click="openMoveGroupDialog(ctxMenu.board)">
              <span>移动到其他分组…</span>
            </button>
            <div class="ctx-sep" />
            <button type="button" class="ctx-item danger" @click="openDeleteBoardDialog(ctxMenu.board)">
              <span>删除此画板…</span>
            </button>
          </template>

          <!-- B. 系统分组菜单 -->
          <template v-else-if="ctxMenu.kind === 'group'">
            <div class="ctx-head">{{ ctxMenu.groupName }}</div>
            <button type="button" class="ctx-item" @click="triggerCreateInGroup(ctxMenu.groupName)">
              <span>在此分组新建画板</span>
            </button>
            <button type="button" class="ctx-item" @click="triggerGroupInlineRename(ctxMenu.groupName)">
              <span>重命名系统分组</span>
            </button>
            <div class="ctx-sep" />
            <button type="button" class="ctx-item danger" @click="triggerDissolveGroup(ctxMenu.groupName)">
              <span>解散此分组（移入未分组）</span>
            </button>
          </template>

          <!-- C. 大纲元素菜单 -->
          <template v-else-if="ctxMenu.kind === 'outline' && ctxMenu.sel">
            <div class="ctx-head">{{ ctxMenu.title }}</div>
            <button type="button" class="ctx-item" @click="triggerOutlineLocate(ctxMenu.sel)">
              <span>画布平滑居中定位</span>
            </button>
            <button
              v-if="ctxMenu.node?.sub_board_id"
              type="button"
              class="ctx-item"
              @click="triggerOutlineDrill(ctxMenu.node.sub_board_id)"
            >
              <span>进入子模块画板 ↘</span>
            </button>
            <button type="button" class="ctx-item" @click="triggerOutlineInlineRename(ctxMenu.sel, ctxMenu.title)">
              <span>重命名此元素</span>
            </button>
            <div class="ctx-sep" />
            <button type="button" class="ctx-item danger" @click="triggerOutlineDelete(ctxMenu.sel)">
              <span>从画布移除元素…</span>
            </button>
          </template>
        </div>
      </div>
    </Teleport>

    <!-- 移动画板至分组弹窗 -->
    <el-dialog v-model="moveDialog.visible" title="移动画板所属系统分组" width="380px" append-to-body>
      <div class="dlg-stack">
        <label class="dlg-lbl">目标系统分组（可直接输入新分组名）：</label>
        <input
          v-model="moveDialog.targetGroup"
          type="text"
          class="mini-input lg"
          list="fmea-group-datalist"
          placeholder="输入或选择系统分组名称"
          @keyup.enter="confirmMoveGroup"
        />
      </div>
      <template #footer>
        <el-button size="small" @click="moveDialog.visible = false">取消</el-button>
        <el-button type="primary" size="small" @click="confirmMoveGroup">确认移动</el-button>
      </template>
    </el-dialog>

    <!-- 删除画板双路保护确认弹窗 -->
    <el-dialog v-model="deleteDialog.visible" title="删除模块画板确认" width="430px" append-to-body>
      <div v-if="deleteDialog.board" class="dlg-stack">
        <p class="dlg-desc">
          即将移除画板 <strong>「{{ deleteDialog.board.name }}」</strong>。请选择旗下本地 FMEA 机理卡的处理方式：
        </p>
        <label class="del-radio-card" :class="{ active: !deleteDialog.deleteItems }">
          <input v-model="deleteDialog.deleteItems" type="radio" :value="false" />
          <div>
            <div class="dr-title">仅删画板，保留机理卡至全局台账（推荐）</div>
            <div class="dr-sub">历史失效实拍与防错经验不会丢失，后续仍可在全局台账检索复用</div>
          </div>
        </label>
        <label class="del-radio-card danger" :class="{ active: deleteDialog.deleteItems }">
          <input v-model="deleteDialog.deleteItems" type="radio" :value="true" />
          <div>
            <div class="dr-title">连同画板旗下的本地机理卡彻底删除</div>
            <div class="dr-sub">仅删除归属该画板的专属卡片，跨画板共用件本体经验不受影响</div>
          </div>
        </label>
      </div>
      <template #footer>
        <el-button size="small" @click="deleteDialog.visible = false">取消</el-button>
        <el-button type="danger" size="small" @click="confirmDeleteBoard">确认删除</el-button>
      </template>
    </el-dialog>
  </aside>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import type {
  FmeaBoardGroup,
  FmeaBoardSummary,
  FmeaBomChildSummary,
  BoardCanvasData,
  CanvasModuleNode,
  FmeaItem,
  CanvasSelection,
  BlueprintPin,
  SubBoardRollupStat
} from '@/views/6_fmea/types'

const props = defineProps<{
  collapsed: boolean
  groups: FmeaBoardGroup[]
  activeBoardId: number | null
  canvasData: BoardCanvasData
  boardItems: FmeaItem[]
  subBoardStats?: Record<string, SubBoardRollupStat>
  selection: CanvasSelection | null
}>()

const emit = defineEmits<{
  (e: 'select-board', boardId: number): void
  (e: 'create-board', payload: { group_name: string; name: string; board_type: string }): void
  (e: 'rename-board', payload: { boardId: number; name: string }): void
  (e: 'move-board-group', payload: { boardId: number; groupName: string }): void
  (e: 'duplicate-board', boardId: number): void
  (e: 'delete-board', payload: { boardId: number; deleteItems: boolean }): void
  (e: 'insert-sub-board', board: FmeaBoardSummary): void
  (e: 'bind-sub-board', payload: { parentBoardId: number; childBoard: FmeaBoardSummary }): void
  (e: 'drill-sub-board', boardId: number): void
  (e: 'rename-group', payload: { oldName: string; newName: string }): void
  (e: 'dissolve-group', groupName: string): void
  (e: 'focus-element', sel: CanvasSelection): void
  (e: 'rename-element', payload: { sel: CanvasSelection; title: string }): void
  (e: 'delete-element', sel: CanvasSelection): void
  (e: 'toggle-collapse'): void
}>()

const sidebarQuery = ref('')
const foldedGroups = ref<Set<string>>(new Set())
const creating = ref(false)
const newGroupInputRef = ref<HTMLInputElement | null>(null)
const newBoardNameInputRef = ref<HTMLInputElement | null>(null)
const form = reactive({
  group_name: '关节执行器系统',
  name: '',
  board_type: 'DFMEA'
})

// 行内重命名状态
const inlineDraft = ref('')
const renamingBoardId = ref<number | null>(null)
const renamingGroupName = ref<string | null>(null)
const renamingOutlineKey = ref<string | null>(null)

// 右键菜单状态
const ctxMenu = reactive<{
  visible: boolean
  kind: 'board' | 'group' | 'outline'
  x: number
  y: number
  board: FmeaBoardSummary | null
  groupName: string
  sel: CanvasSelection | null
  node: CanvasModuleNode | null
  title: string
}>({
  visible: false,
  kind: 'board',
  x: 0,
  y: 0,
  board: null,
  groupName: '',
  sel: null,
  node: null,
  title: ''
})

const moveDialog = reactive<{ visible: boolean; board: FmeaBoardSummary | null; targetGroup: string }>({
  visible: false,
  board: null,
  targetGroup: ''
})

const deleteDialog = reactive<{ visible: boolean; board: FmeaBoardSummary | null; deleteItems: boolean }>({
  visible: false,
  board: null,
  deleteItems: false
})

// ==================== 【信标 1】画板拖拽移动与子模块映射绑定 ====================
const draggedBoard = ref<FmeaBoardSummary | null>(null)
const hoverGroupTargetName = ref<string | null>(null)
const hoverBoardTargetId = ref<number | null>(null)

function onBoardDragStart(e: DragEvent, b: FmeaBoardSummary) {
  draggedBoard.value = b
  if (e.dataTransfer) {
    e.dataTransfer.setData('application/json', JSON.stringify({ type: 'fmea-sub-board', board: b }))
    e.dataTransfer.setData('text/plain', b.name)
    e.dataTransfer.effectAllowed = 'copyMove'
  }
}

function onBoardDragEnd() {
  draggedBoard.value = null
  hoverGroupTargetName.value = null
  hoverBoardTargetId.value = null
}

function onGroupDragOver(e: DragEvent, groupName: string) {
  if (!draggedBoard.value) return
  if (draggedBoard.value.group_name !== groupName) {
    hoverGroupTargetName.value = groupName
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  }
}

function onGroupDragLeave(groupName: string) {
  if (hoverGroupTargetName.value === groupName) {
    hoverGroupTargetName.value = null
  }
}

function onGroupDrop(e: DragEvent, groupName: string) {
  hoverGroupTargetName.value = null
  if (!draggedBoard.value) return
  if (draggedBoard.value.group_name === groupName) return
  const b = draggedBoard.value
  draggedBoard.value = null
  emit('move-board-group', { boardId: b.id, groupName })
  foldedGroups.value.delete(groupName)
}

function onBoardDragOver(e: DragEvent, targetBoard: FmeaBoardSummary) {
  if (!draggedBoard.value) return
  if (draggedBoard.value.id !== targetBoard.id) {
    hoverBoardTargetId.value = targetBoard.id
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
  }
}

function onBoardDragLeave(targetBoard: FmeaBoardSummary) {
  if (hoverBoardTargetId.value === targetBoard.id) {
    hoverBoardTargetId.value = null
  }
}

function onBoardDropOnBoard(e: DragEvent, targetBoard: FmeaBoardSummary) {
  hoverBoardTargetId.value = null
  if (!draggedBoard.value) return
  if (draggedBoard.value.id === targetBoard.id) return
  const child = draggedBoard.value
  draggedBoard.value = null
  // 建立装配引用后自动展开目标画板的 SolidWorks 装配特征树
  expandedBoardIds.value.add(targetBoard.id)
  emit('bind-sub-board', { parentBoardId: targetBoard.id, childBoard: child })
}

// ==================== 侧边栏宽度与手动拖拽缩放 ====================
const DEFAULT_SIDEBAR_WIDTH = 270
const MIN_SIDEBAR_WIDTH = 220
const MAX_SIDEBAR_WIDTH = 550

const sidebarWidth = ref<number>(
  (() => {
    const saved = localStorage.getItem('fmea_sidebar_width')
    if (saved) {
      const parsed = parseInt(saved, 10)
      if (!isNaN(parsed) && parsed >= MIN_SIDEBAR_WIDTH && parsed <= MAX_SIDEBAR_WIDTH) {
        return parsed
      }
    }
    return DEFAULT_SIDEBAR_WIDTH
  })()
)

const treeLayout = ref<'tab' | 'split'>(
  (localStorage.getItem('fmea_tree_layout') as 'tab' | 'split') || 'tab'
)

const treeViewMode = ref<'assembly' | 'grouped' | 'outline'>('assembly')

function toggleTreeLayout() {
  treeLayout.value = treeLayout.value === 'tab' ? 'split' : 'tab'
  localStorage.setItem('fmea_tree_layout', treeLayout.value)
}

function selectTab(mode: 'assembly' | 'grouped' | 'outline') {
  treeViewMode.value = mode
  if (treeLayout.value === 'split' && mode === 'outline') {
    // 点击大纲标签时切换至专注 Tab 模式展示全高大纲
    treeLayout.value = 'tab'
    localStorage.setItem('fmea_tree_layout', 'tab')
  }
}

const sidebarSearchPlaceholder = computed(() => {
  if (treeLayout.value === 'tab' && treeViewMode.value === 'outline') {
    return '过滤当前画布 Pins / 节点 / 连线...'
  }
  if (treeViewMode.value === 'assembly') {
    return '搜索装配总成 / 引用子模块 / 借用件...'
  }
  return '搜系统 / 模块 / 画板...'
})

const isResizing = ref(false)
let startX = 0
let startWidth = 0

function onStartResize(e: MouseEvent) {
  if (props.collapsed) return
  isResizing.value = true
  startX = e.clientX
  startWidth = sidebarWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onMouseMoveResize)
  window.addEventListener('mouseup', onStopResize)
}

function onMouseMoveResize(e: MouseEvent) {
  if (!isResizing.value) return
  const deltaX = e.clientX - startX
  const newWidth = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, startWidth + deltaX))
  sidebarWidth.value = newWidth
}

function onStopResize() {
  if (!isResizing.value) return
  isResizing.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('mousemove', onMouseMoveResize)
  window.removeEventListener('mouseup', onStopResize)
  localStorage.setItem('fmea_sidebar_width', sidebarWidth.value.toString())
}

function onResetResize() {
  sidebarWidth.value = DEFAULT_SIDEBAR_WIDTH
  localStorage.setItem('fmea_sidebar_width', DEFAULT_SIDEBAR_WIDTH.toString())
}

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onMouseMoveResize)
  window.removeEventListener('mouseup', onStopResize)
})

// ==================== SolidWorks 装配特征树与多级 BOM 引用 ====================
const expandedBoardIds = ref<Set<number>>(new Set())

function getBoardBomChildren(board: FmeaBoardSummary): FmeaBomChildSummary[] {
  // 1. 如果是当前正在编辑的画板，使用实时 canvasData 计算，保证拖拽增删即时同步
  if (board.id === props.activeBoardId && props.canvasData?.nodes) {
    const list: FmeaBomChildSummary[] = []
    const instCounts: Record<string | number, number> = {}
    for (const nd of props.canvasData.nodes) {
      if (nd.sub_board_id) {
        instCounts[nd.sub_board_id] = (instCounts[nd.sub_board_id] || 0) + 1
        const stat = props.subBoardStats?.[String(nd.sub_board_id)]
        list.push({
          node_id: nd.id,
          title: nd.title,
          ref_type: 'sub_board',
          sub_board_id: nd.sub_board_id,
          sub_board_code: nd.sub,
          instance_index: instCounts[nd.sub_board_id],
          high_risk_count: stat?.high_risk_count || 0,
          total_items: stat?.total_items || 0
        })
      } else if (nd.unit_code) {
        instCounts[nd.unit_code] = (instCounts[nd.unit_code] || 0) + 1
        list.push({
          node_id: nd.id,
          title: nd.title,
          ref_type: 'shared_unit',
          unit_code: nd.unit_code,
          instance_index: instCounts[nd.unit_code],
          high_risk_count: 0,
          total_items: 0
        })
      }
    }
    return list
  }
  // 2. 其它画板从后端 summary.bom_children 获取
  return board.bom_children || []
}

function isBoardExpanded(boardId: number): boolean {
  return expandedBoardIds.value.has(boardId)
}

function toggleBoardExpand(boardId: number, e?: MouseEvent) {
  e?.stopPropagation()
  if (expandedBoardIds.value.has(boardId)) {
    expandedBoardIds.value.delete(boardId)
  } else {
    expandedBoardIds.value.add(boardId)
  }
}

// 自动展开包含子装配引用的画板
watch(
  () => [props.groups, props.canvasData?.nodes],
  () => {
    for (const g of props.groups || []) {
      for (const b of g.boards || []) {
        if (getBoardBomChildren(b).length > 0) {
          expandedBoardIds.value.add(b.id)
        }
      }
    }
  },
  { immediate: true, deep: true }
)

function onBomChildClick(b: FmeaBoardSummary, ch: FmeaBomChildSummary) {
  if (b.id === props.activeBoardId) {
    emit('focus-element', { kind: 'node', id: ch.node_id })
  } else {
    emit('select-board', b.id)
    setTimeout(() => {
      emit('focus-element', { kind: 'node', id: ch.node_id })
    }, 120)
  }
}

function onBomChildDblClick(b: FmeaBoardSummary, ch: FmeaBomChildSummary) {
  if (ch.ref_type === 'sub_board' && ch.sub_board_id) {
    emit('drill-sub-board', ch.sub_board_id)
  }
}

const allFlatBoards = computed(() => {
  const kw = normQuery.value
  const list: FmeaBoardSummary[] = []
  for (const g of props.groups) {
    for (const b of g.boards) {
      if (!kw || b.name.toLowerCase().includes(kw) || b.board_code.toLowerCase().includes(kw)) {
        list.push(b)
      }
    }
  }
  return list.sort((a, b) => {
    const aLen = getBoardBomChildren(a).length
    const bLen = getBoardBomChildren(b).length
    if (aLen > 0 && bLen === 0) return -1
    if (bLen > 0 && aLen === 0) return 1
    return 0
  })
})

// ==================== 目录与大纲实时搜索过滤 ====================

const normQuery = computed(() => sidebarQuery.value.trim().toLowerCase())

const filteredGroups = computed(() => {
  const kw = normQuery.value
  if (!kw) return props.groups
  const res: FmeaBoardGroup[] = []
  for (const g of props.groups) {
    const groupHit = g.group_name.toLowerCase().includes(kw)
    const matchedBoards = g.boards.filter(
      (b) =>
        groupHit ||
        b.name.toLowerCase().includes(kw) ||
        b.board_code.toLowerCase().includes(kw)
    )
    if (matchedBoards.length > 0) {
      res.push({ group_name: g.group_name, boards: matchedBoards })
    }
  }
  return res
})

function isGroupFolded(name: string): boolean {
  if (normQuery.value) return false // 搜索时自动展开命中分组
  return foldedGroups.value.has(name)
}

function toggleGroup(name: string) {
  const next = new Set(foldedGroups.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  foldedGroups.value = next
}

function openCreateForm(presetGroup?: string) {
  if (presetGroup) {
    form.group_name = presetGroup
  } else if (props.groups.length > 0 && !form.group_name) {
    form.group_name = props.groups[0].group_name
  }
  form.name = ''
  creating.value = true
  nextTick(() => {
    if (presetGroup) newBoardNameInputRef.value?.focus()
    else newGroupInputRef.value?.focus()
  })
}

function submitCreate() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入模块画板名称')
    return
  }
  emit('create-board', {
    group_name: form.group_name.trim() || '默认系统分组',
    name: form.name.trim(),
    board_type: form.board_type
  })
  creating.value = false
}

const allPins = computed(() => {
  const list: { imgId: string; pin: BlueprintPin }[] = []
  for (const ib of props.canvasData?.image_boards || []) {
    for (const p of ib.pins || []) {
      list.push({ imgId: ib.id, pin: p })
    }
  }
  return list
})

const filteredPins = computed(() => {
  const kw = normQuery.value
  if (!kw) return allPins.value
  return allPins.value.filter(
    (p) => p.pin.title.toLowerCase().includes(kw) || (p.pin.sub || '').toLowerCase().includes(kw)
  )
})

const filteredNodes = computed(() => {
  const nodes = props.canvasData?.nodes || []
  const kw = normQuery.value
  if (!kw) return nodes
  return nodes.filter(
    (nd) =>
      nd.title.toLowerCase().includes(kw) ||
      (nd.sub || '').toLowerCase().includes(kw) ||
      (nd.unit_code || '').toLowerCase().includes(kw)
  )
})

const filteredEdges = computed(() => {
  const edges = props.canvasData?.edges || []
  const kw = normQuery.value
  if (!kw) return edges
  return edges.filter(
    (ed) => (ed.label || '').toLowerCase().includes(kw) || (ed.sub || '').toLowerCase().includes(kw)
  )
})

const filteredOutlineTotal = computed(
  () => filteredPins.value.length + filteredNodes.value.length + filteredEdges.value.length
)

// 风险统计（支持共用件 shared_unit 与子模块画板 subBoardStats 汇总）
const statMap = computed(() => {
  const map = new Map<string, { total: number; high: number }>()
  for (const it of props.boardItems) {
    const k = `${it.target_kind}:${it.target_id}`
    const cur = map.get(k) || { total: 0, high: 0 }
    cur.total += 1
    if (it.risk_level === 'HIGH') cur.high += 1
    map.set(k, cur)
  }
  return map
})

function getPinOrEdgeStat(kind: string, id: string) {
  return statMap.value.get(`${kind}:${id}`) || { total: 0, high: 0 }
}

function getNodeOutlineStat(nd: CanvasModuleNode) {
  const local = statMap.value.get(`node:${nd.id}`) || { total: 0, high: 0 }
  let total = local.total
  let high = local.high

  if (nd.unit_code) {
    const shared = statMap.value.get(`shared_unit:${nd.unit_code}`)
    if (shared) {
      total += shared.total
      high += shared.high
    }
  }
  if (nd.sub_board_id && props.subBoardStats) {
    const sb = props.subBoardStats[String(nd.sub_board_id)]
    if (sb) {
      total += sb.total_items
      high += sb.high_risk_count
    }
  }
  return { total, high }
}

// ==================== 右键菜单与行内操作 ====================

function clampMenuCoords(clientX: number, clientY: number, estHeight = 190) {
  const x = Math.min(window.innerWidth - 204, Math.max(8, clientX))
  const y = Math.min(window.innerHeight - estHeight, Math.max(8, clientY))
  return { x, y }
}

function openBoardContextMenu(e: MouseEvent, b: FmeaBoardSummary) {
  const pos = clampMenuCoords(e.clientX, e.clientY, 210)
  ctxMenu.kind = 'board'
  ctxMenu.board = b
  ctxMenu.x = pos.x
  ctxMenu.y = pos.y
  ctxMenu.visible = true
}

function openGroupContextMenu(e: MouseEvent, groupName: string, _count: number) {
  const pos = clampMenuCoords(e.clientX, e.clientY, 155)
  ctxMenu.kind = 'group'
  ctxMenu.groupName = groupName
  ctxMenu.x = pos.x
  ctxMenu.y = pos.y
  ctxMenu.visible = true
}

function openOutlineContextMenu(
  e: MouseEvent,
  sel: CanvasSelection,
  title: string,
  node?: CanvasModuleNode
) {
  const pos = clampMenuCoords(e.clientX, e.clientY, 175)
  ctxMenu.kind = 'outline'
  ctxMenu.sel = sel
  ctxMenu.node = node || null
  ctxMenu.title = title
  ctxMenu.x = pos.x
  ctxMenu.y = pos.y
  ctxMenu.visible = true
}

function closeContextMenu() {
  ctxMenu.visible = false
}

function triggerBoardInlineRename(b: FmeaBoardSummary) {
  closeContextMenu()
  inlineDraft.value = b.name
  renamingBoardId.value = b.id
}

function commitBoardRename(b: FmeaBoardSummary) {
  if (renamingBoardId.value !== b.id) return
  renamingBoardId.value = null
  const next = inlineDraft.value.trim()
  if (next && next !== b.name) {
    emit('rename-board', { boardId: b.id, name: next })
  }
}

function triggerInsertAsSubBoard(b: FmeaBoardSummary) {
  if (b.id === props.activeBoardId) return
  closeContextMenu()
  emit('insert-sub-board', b)
}

function triggerDuplicateBoard(b: FmeaBoardSummary) {
  closeContextMenu()
  emit('duplicate-board', b.id)
}

function openMoveGroupDialog(b: FmeaBoardSummary) {
  closeContextMenu()
  moveDialog.board = b
  moveDialog.targetGroup = b.group_name
  moveDialog.visible = true
}

function confirmMoveGroup() {
  if (!moveDialog.board) return
  const nextGroup = moveDialog.targetGroup.trim()
  if (!nextGroup) {
    ElMessage.warning('请输入目标系统分组名')
    return
  }
  emit('move-board-group', { boardId: moveDialog.board.id, groupName: nextGroup })
  moveDialog.visible = false
}

function openDeleteBoardDialog(b: FmeaBoardSummary) {
  closeContextMenu()
  deleteDialog.board = b
  deleteDialog.deleteItems = false
  deleteDialog.visible = true
}

function confirmDeleteBoard() {
  if (!deleteDialog.board) return
  emit('delete-board', {
    boardId: deleteDialog.board.id,
    deleteItems: deleteDialog.deleteItems
  })
  deleteDialog.visible = false
}

function triggerCreateInGroup(groupName: string) {
  closeContextMenu()
  openCreateForm(groupName)
}

function triggerGroupInlineRename(groupName: string) {
  closeContextMenu()
  inlineDraft.value = groupName
  renamingGroupName.value = groupName
}

function commitGroupRename(oldName: string) {
  if (renamingGroupName.value !== oldName) return
  renamingGroupName.value = null
  const next = inlineDraft.value.trim()
  if (next && next !== oldName) {
    emit('rename-group', { oldName, newName: next })
  }
}

function triggerDissolveGroup(groupName: string) {
  closeContextMenu()
  emit('dissolve-group', groupName)
}

function triggerOutlineLocate(sel: CanvasSelection) {
  closeContextMenu()
  emit('focus-element', sel)
}

function triggerOutlineDrill(subBoardId: number) {
  closeContextMenu()
  emit('drill-sub-board', subBoardId)
}

function triggerOutlineInlineRename(sel: CanvasSelection, currTitle: string) {
  closeContextMenu()
  inlineDraft.value = currTitle
  renamingOutlineKey.value = `${sel.kind}:${sel.id}`
}

function commitOutlineRename(sel: CanvasSelection, oldTitle: string) {
  const key = `${sel.kind}:${sel.id}`
  if (renamingOutlineKey.value !== key) return
  renamingOutlineKey.value = null
  const next = inlineDraft.value.trim()
  if (next && next !== oldTitle) {
    emit('rename-element', { sel, title: next })
  }
}

function triggerOutlineDelete(sel: CanvasSelection) {
  closeContextMenu()
  emit('delete-element', sel)
}
</script>

<style scoped>
.fmea-module-sidebar {
  min-width: 0;
  flex-shrink: 0;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: visible;
  user-select: none;
  z-index: 12;
  position: relative;
}

.fmea-module-sidebar.is-resizing {
  transition: none !important;
}

.fmea-module-sidebar.is-collapsed {
  width: 0 !important;
  border-right-color: transparent;
}

.sidebar-inner {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 侧边栏边缘拖拽调整器与折叠触发钮 */
.sidebar-resizer {
  position: absolute;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 25;
  transition: background 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-resizer:hover,
.sidebar-resizer.is-resizing {
  background: rgba(37, 99, 235, 0.35);
}

.sidebar-edge-collapse-btn {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 38px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #94a3b8;
  padding: 0;
  opacity: 0;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.fmea-module-sidebar:hover .sidebar-edge-collapse-btn {
  opacity: 0.85;
}

.sidebar-edge-collapse-btn:hover {
  opacity: 1 !important;
  background: #eff6ff;
  color: #2563eb;
  border-color: #93c5fd;
  transform: translate(-50%, -50%) scale(1.1);
}

.sidebar-edge-collapse-btn svg {
  width: 10px;
  height: 10px;
}

/* 左栏专属快速过滤栏 */
.sidebar-filter-bar {
  padding: 8px 8px 4px;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}

.sf-box {
  height: 27px;
  padding: 0 7px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.14s;
}

.sf-box:focus-within {
  background: #ffffff;
  border-color: #93c5fd;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.08);
}

.sf-ico {
  width: 12.5px;
  height: 12.5px;
  color: #94a3b8;
  flex-shrink: 0;
}

.sf-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  font-size: 11.5px;
  color: #0f172a;
  outline: none;
}

.sf-clear {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
}

.sf-clear:hover {
  color: #0f172a;
}

/* 顶部 Tab 标签栏 */
.sidebar-tabs-bar {
  height: 36px;
  padding: 0 8px 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
  gap: 6px;
}

.sidebar-tabs-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  border-radius: 7px;
  font-size: 9.5px;
  font-weight: 700;
  background: #e2e8f0;
  color: #475569;
  line-height: 1;
}

.tm-pill.active .tab-badge {
  background: #eff6ff;
  color: #2563eb;
}

.sec-block {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.boards-sec {
  flex: 5.5;
  border-bottom: 1px solid #e2e8f0;
}

.boards-sec.is-full-height {
  flex: 1 1 100% !important;
  border-bottom: none !important;
  height: 100%;
}

.outline-sec {
  flex: 4.5;
  background: #fcfcfd;
}

.outline-sec.is-full-height {
  flex: 1 1 100% !important;
  height: 100%;
}

.sec-header {
  height: 32px;
  padding: 0 10px 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.sec-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: #64748b;
}

.sec-meta {
  font-size: 11px;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

.icon-mini-btn {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  border: none;
  background: transparent;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
}

.icon-mini-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.icon-mini-btn svg {
  width: 14px;
  height: 14px;
}

.inline-create-box {
  margin: 0 8px 8px;
  padding: 8px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mini-input {
  width: 100%;
  height: 26px;
  padding: 0 8px;
  font-size: 12px;
  border-radius: 5px;
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #0f172a;
  outline: none;
}

.mini-input.lg {
  height: 32px;
  font-size: 13px;
}

.mini-input:focus {
  border-color: #2563eb;
}

.create-type-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.type-pills {
  display: flex;
  gap: 3px;
}

.tp-pill {
  padding: 2px 5px;
  font-size: 10px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  cursor: pointer;
}

.tp-pill.active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
  font-weight: 600;
}

.create-btns {
  display: flex;
  gap: 4px;
}

.txt-btn {
  border: none;
  background: transparent;
  font-size: 11px;
  color: #64748b;
  cursor: pointer;
  padding: 2px 4px;
}

.pri-mini-btn {
  border: none;
  background: #0f172a;
  color: #fff;
  font-size: 11px;
  border-radius: 4px;
  padding: 2px 8px;
  cursor: pointer;
}

.tree-scroll,
.outline-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 6px 8px;
}

.group-row {
  height: 26px;
  padding: 0 5px 0 6px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #475569;
  font-size: 11.5px;
  font-weight: 600;
}

.group-row:hover {
  background: #f8fafc;
}

.group-row.is-drop-group-target {
  background: #eff6ff;
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1.5px #3b82f6;
}

.chev-ico {
  width: 13px;
  height: 13px;
  color: #94a3b8;
  transition: transform 0.15s;
  flex-shrink: 0;
}

.chev-ico.folded {
  transform: rotate(-90deg);
}

.group-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-cnt {
  font-size: 10.5px;
  color: #94a3b8;
}

.group-children {
  padding-left: 8px;
  margin-bottom: 4px;
}

.board-item {
  height: 28px;
  padding: 0 5px 0 7px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  color: #334155;
  font-size: 12px;
  transition: background 0.12s;
}

.board-item:hover {
  background: #f1f5f9;
}

/* SolidWorks 装配特征树样式 */
.tree-mode-pills {
  display: inline-flex;
  background: #f1f5f9;
  padding: 1.5px;
  border-radius: 6px;
  gap: 1.5px;
}

.tm-pill {
  border: none;
  background: transparent;
  padding: 2px 7px;
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.tm-pill:hover {
  color: #1e293b;
}

.tm-pill.active {
  background: #ffffff;
  color: #1e293b;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.board-exp-btn {
  width: 14px;
  height: 14px;
  padding: 0;
  border: none;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 3px;
  flex-shrink: 0;
  transition: transform 0.15s ease;
}

.board-exp-btn:hover {
  background: #e2e8f0;
  color: #334155;
}

.board-exp-btn svg {
  width: 9px;
  height: 9px;
  transition: transform 0.15s ease;
}

.board-exp-btn.expanded svg {
  transform: rotate(90deg);
}

.board-exp-placeholder {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.assembly-cube-ico {
  font-size: 11px;
  line-height: 1;
  flex-shrink: 0;
}

.assembly-tag {
  font-size: 9px;
  font-weight: 700;
  padding: 0.5px 3.5px;
  border-radius: 3px;
  background: #e0e7ff;
  color: #4338ca;
  flex-shrink: 0;
}

.board-bom-branch {
  margin-left: 20px;
  padding-left: 6px;
  border-left: 1px dashed #cbd5e1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-top: 1px;
  margin-bottom: 3px;
}

.bom-child-row {
  height: 24px;
  padding: 0 4px 0 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #475569;
  cursor: pointer;
  transition: background 0.12s;
}

.bom-child-row:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.bom-child-row.active {
  background: #e0e7ff;
  color: #3730a3;
  font-weight: 600;
}

.tree-branch-line {
  color: #94a3b8;
  font-size: 11px;
  flex-shrink: 0;
}

.bom-ref-pill {
  font-size: 9.5px;
  font-weight: 700;
  padding: 1px 4.5px;
  border-radius: 3px;
  line-height: 1.2;
  flex-shrink: 0;
}

.bom-ref-pill.sub {
  background: #e0e7ff;
  color: #3730a3;
  border: 1px solid #c7d2fe;
}

.bom-ref-pill.shared {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.bom-child-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.child-drill-btn {
  border: none;
  background: transparent;
  color: #6366f1;
  font-size: 11px;
  font-weight: bold;
  padding: 0 3px;
  border-radius: 3px;
  cursor: pointer;
  display: none;
}

.bom-child-row:hover .child-drill-btn {
  display: inline-flex;
}

.child-drill-btn:hover {
  background: #c7d2fe;
  color: #312e81;
}

.board-drag-handle {
  font-size: 11px;
  color: #94a3b8;
  cursor: grab;
  margin-right: -2px;
  opacity: 0;
  transition: opacity 0.15s;
  user-select: none;
}

.board-item:hover .board-drag-handle {
  opacity: 1;
}

.board-item.is-dragging {
  opacity: 0.45;
  background: #f1f5f9;
}

.board-item.is-drop-target {
  background: #e0e7ff;
  color: #4338ca;
  box-shadow: inset 0 0 0 1.5px #6366f1;
}

.board-item.active {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

.board-ico,
.ol-ico {
  width: 13.5px;
  height: 13.5px;
  flex-shrink: 0;
  opacity: 0.78;
}

.ol-ico.is-sub {
  color: #4f46e5;
  opacity: 1;
}

.ol-ico.is-shared {
  color: #0284c7;
  opacity: 1;
}

.board-name,
.ol-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-inline-input {
  flex: 1;
  min-width: 0;
  height: 20px;
  padding: 0 5px;
  border-radius: 4px;
  border: 1px solid #2563eb;
  background: #ffffff;
  font-size: 11.5px;
  color: #0f172a;
  outline: none;
}

.row-more-btn {
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  line-height: 1;
  display: none;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
}

.group-row:hover .row-more-btn,
.board-item:hover .row-more-btn,
.outline-row:hover .row-more-btn {
  display: inline-flex;
}

.row-more-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.risk-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.risk-dot.high {
  background: #ef4444;
}

.board-badge,
.ol-cnt {
  font-size: 10.5px;
  color: #64748b;
  background: #f1f5f9;
  padding: 0 5px;
  border-radius: 8px;
  font-variant-numeric: tabular-nums;
}

.board-item.active .board-badge {
  background: #dbeafe;
  color: #1d4ed8;
}

.sub-cat {
  font-size: 10.5px;
  font-weight: 600;
  color: #94a3b8;
  padding: 6px 6px 3px;
}

.outline-row {
  height: 26px;
  padding: 0 5px 0 7px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #334155;
  cursor: pointer;
}

.outline-row:hover {
  background: #f1f5f9;
}

.outline-row.active {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 500;
}

.pin-idx {
  font-size: 10.5px;
  font-weight: 700;
  color: #dc2626;
  background: #fee2e2;
  padding: 0 4px;
  border-radius: 4px;
  line-height: 16px;
}

.outline-empty {
  padding: 18px 8px;
  text-align: center;
  font-size: 11.5px;
  color: #94a3b8;
}

/* ==================== 全局轻量右键菜单样式 ==================== */
.fmea-ctx-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3200;
}

.fmea-ctx-menu {
  position: fixed;
  width: 192px;
  padding: 5px;
  border-radius: 9px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.15);
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ctx-head {
  padding: 4px 8px 5px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ctx-item {
  height: 28px;
  padding: 0 8px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #1e293b;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  text-align: left;
  cursor: pointer;
}

.ctx-item:hover:not(:disabled) {
  background: #f1f5f9;
}

.ctx-item:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.ctx-item.danger {
  color: #dc2626;
}

.ctx-item.danger:hover {
  background: #fef2f2;
}

.ctx-tag {
  font-size: 9.5px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 4px;
  background: #eef2ff;
  color: #4f46e5;
}

.ctx-sep {
  height: 1px;
  background: #f1f5f9;
  margin: 3px 4px;
}

/* 删除与移动分组弹窗样式 */
.dlg-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dlg-lbl {
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
}

.dlg-desc {
  margin: 0;
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
}

.del-radio-card {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.14s;
}

.del-radio-card input {
  margin-top: 3px;
}

.del-radio-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.del-radio-card.danger.active {
  border-color: #ef4444;
  background: #fef2f2;
}

.dr-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #0f172a;
}

.dr-sub {
  font-size: 11.5px;
  color: #64748b;
  margin-top: 2px;
}
</style>
