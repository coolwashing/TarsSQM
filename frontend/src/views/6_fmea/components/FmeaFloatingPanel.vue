<template>
  <transition name="slide-panel">
    <aside
      v-if="selection && activeTarget"
      class="fmea-floating-panel fmea-module-drawer"
      :style="{ width: `${drawerWidth}px` }"
      :class="{ 'is-resizing': isResizing }"
      @mousedown.stop
      @paste="onPanelPaste"
    >
      <!-- 左侧宽度拖拽调节手柄 (初始 70%，支持自由左右拉伸) -->
      <div
        class="drawer-resizer-handle"
        title="按住左右拖拽调整抽屉宽度"
        @mousedown.prevent="startResize"
      >
        <div class="resizer-bar" />
      </div>

      <!-- 1. 顶部抽屉工具栏：所属要素 + 标题编辑 + 共用本体状态 + 搜索过滤 + 快捷操作 -->
      <div class="drawer-header">
        <div class="dh-left">
          <!-- 要素属性徽章 -->
          <span class="elem-badge" :class="kindPillClass">{{ shortKindLabel }}</span>

          <!-- 模块标题 (行内可改名) -->
          <input
            :value="activeTarget.title"
            type="text"
            class="clean-title-input"
            :placeholder="selection.kind === 'edge' ? '输入接口名(如 油脂飞溅)' : '输入模块或热点名称'"
            @change="onTitleChange(($event.target as HTMLInputElement).value)"
          />

          <!-- 模块编码 / 跨画板共用胶囊 -->
          <template v-if="selection.kind === 'node' && selectedNode">
            <div v-if="selectedNode.unit_code" class="shared-unit-chip">
              <span class="suc-label">共用:</span>
              <span class="suc-code">{{ selectedNode.unit_code }}</span>

              <!-- 借用处雷达反查 -->
              <el-popover placement="bottom-start" :width="260" trigger="click">
                <template #reference>
                  <button type="button" class="suc-where-btn">
                    {{ currentUnitWhereUsed.length || 1 }} 处借用 ▾
                  </button>
                </template>
                <div class="where-used-pop">
                  <div class="wu-head">「{{ selectedNode.unit_code }}」跨画板借用反查</div>
                  <div class="wu-list">
                    <button
                      v-for="(wu, idx) in currentUnitWhereUsed"
                      :key="`${wu.board_id}_${wu.node_id || idx}`"
                      type="button"
                      class="wu-item"
                      :class="{ current: wu.board_id === activeBoardId }"
                      @click="$emit('jump-to-board', { boardId: wu.board_id, nodeId: wu.node_id || undefined })"
                    >
                      <div class="wui-main">
                        <span class="wui-board">{{ wu.board_name }}</span>
                        <span v-if="wu.board_id === activeBoardId" class="wui-cur-tag">当前画板</span>
                      </div>
                      <div class="wui-sub">{{ wu.group_name }} · 节点: {{ wu.node_title }}</div>
                    </button>
                  </div>
                </div>
              </el-popover>

              <button
                type="button"
                class="suc-unbind-btn"
                title="解除共用单元绑定，恢复为普通独立模块"
                @click="unbindUnitCode"
              >
                解除
              </button>
            </div>

            <!-- 普通独立节点编码 -->
            <div v-else class="simple-code-row">
              <input
                :value="selectedNode.sub || ''"
                type="text"
                class="clean-sub-input"
                placeholder="代号 (如 PRT-102)"
                @change="onSubChange(($event.target as HTMLInputElement).value)"
              />
              <button
                type="button"
                class="enable-share-link"
                title="将此模块设为跨画板共用件"
                @click="enableSharedUnit"
              >
                以「{{ selectedNode.sub || selectedNode.title }}」开启共用
              </button>
            </div>
          </template>

          <!-- 嵌套子画板下钻 -->
          <div v-else-if="selectedNode?.sub_board_id" class="sub-board-strip">
            <span class="sbs-meta">
              内部 <strong>{{ currentSubBoardStat?.total_items || 0 }}</strong> 项 ·
              <span class="hi">{{ currentSubBoardStat?.high_risk_count || 0 }} 高危</span>
            </span>
            <button
              type="button"
              class="sbs-drill-btn"
              @click="$emit('drill-sub-board', selectedNode.sub_board_id!)"
            >
              下钻子画板 ↘
            </button>
          </div>

          <!-- 设计极限公差 -->
          <div v-else-if="selection.kind === 'pin' && selectedPin" class="pin-mini-strip">
            <button
              type="button"
              class="pin-limit-pill"
              :class="{ active: selectedPin.is_limit }"
              @click="togglePinLimit"
            >
              <span>{{ selectedPin.is_limit ? '设计极限公差' : '设为设计极限' }}</span>
            </button>
            <input
              v-if="selectedPin.is_limit"
              :value="selectedPin.limit_spec || ''"
              type="text"
              class="pin-spec-input"
              placeholder="极限公差 (如 R0.15 倒角)..."
              @change="onPinLimitSpecChange(($event.target as HTMLInputElement).value)"
            />
          </div>

          <!-- 工艺挑战 -->
          <div v-else-if="selection.kind === 'edge' && selectedEdge" class="edge-mini-strip">
            <button
              type="button"
              class="edge-pill"
              :class="{ active: selectedEdge.kind === 'process_challenge' }"
              @click="setEdgeKind(selectedEdge.kind === 'process_challenge' ? 'normal' : 'process_challenge')"
            >
              {{ selectedEdge.kind === 'process_challenge' ? '制程挑战' : '装配配合' }}
            </button>
          </div>
        </div>

        <div class="dh-right">
          <!-- 模块内快速过滤 -->
          <input
            v-model="tableFilterText"
            type="text"
            class="table-search-input"
            placeholder="搜索当前表格失效模式/机理..."
          />

          <!-- 风险快捷筛选 -->
          <div class="risk-filter-pills">
            <button
              type="button"
              class="rf-pill"
              :class="{ active: riskFilter === 'ALL' }"
              @click="riskFilter = 'ALL'"
            >
              全部 ({{ currentDisplayItems.length }})
            </button>
            <button
              type="button"
              class="rf-pill r-high"
              :class="{ active: riskFilter === 'HIGH' }"
              @click="riskFilter = 'HIGH'"
            >
              高危 ({{ highRiskCount }})
            </button>
          </div>

          <!-- 核心操作：新增该模块机理行 (行内即录入) -->
          <button type="button" class="add-item-btn" @click="handleQuickAddRow">
            + 补充失效行
          </button>

          <!-- 移除要素 -->
          <button
            type="button"
            class="icon-ghost-btn"
            :title="`移除此${kindLabel}`"
            @click="$emit('delete-target')"
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" class="icon-svg">
              <path d="M3 4.5h10M6 4.5V3h4v1.5M5 4.5l.6 8.5h4.8l.6-8.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>

          <!-- 关闭抽屉 -->
          <button type="button" class="icon-ghost-btn close-btn" title="收起抽屉 (Esc)" @click="$emit('close')">
            ×
          </button>
        </div>
      </div>

      <!-- 2. 范围切换栏：本模块 / 关联接口 / 全画板 -->
      <div class="drawer-sub-bar">
        <div class="scope-mode-tabs">
          <button
            type="button"
            class="smt-btn"
            :class="{ active: scopeMode === 'module' }"
            @click="scopeMode = 'module'"
          >
            本{{ shortKindLabel }} ({{ (items || []).length }})
          </button>
          <button
            v-if="selection?.kind === 'node' && (connectedEdgeItems || []).length > 0"
            type="button"
            class="smt-btn"
            :class="{ active: scopeMode === 'interfaces' }"
            @click="scopeMode = 'interfaces'"
          >
            关联接口 ({{ (connectedEdgeItems || []).length }})
          </button>
          <button
            type="button"
            class="smt-btn"
            :class="{ active: scopeMode === 'board' }"
            @click="scopeMode = 'board'"
          >
            全画板 ({{ (allBoardItems || []).length }})
          </button>
        </div>
      </div>

      <!-- 3. 【核心】模块 FMEA 一行一行结构化工作表 -->
      <div class="drawer-table-shell">
        <table class="module-fmea-table">
          <thead>
            <tr>
              <th style="width: 105px;">编号</th>
              <th style="min-width: 190px;">失效模式</th>
              <th style="width: 160px; min-width: 160px;">实拍对比</th>
              <th style="min-width: 180px;">失效机理</th>
              <th style="min-width: 160px;">失效后果</th>
              <th style="min-width: 180px;">预防措施</th>
              <th style="min-width: 180px;">探测措施</th>
              <th style="width: 95px;">风险等级</th>
              <th style="width: 110px;">关联标签</th>
              <th class="th-actions" style="width: 130px; text-align: center;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="filteredItems.length === 0">
              <td colspan="10" class="empty-cell">
                <div class="empty-hint-box">
                  <p class="empty-txt">
                    {{ tableFilterText ? '暂未找到匹配的失效记录' : `当前范围尚未录入任何 FMEA 失效记录` }}
                  </p>
                  <button type="button" class="pri-ghost-btn" @click="handleQuickAddRow">
                    + 录入首条 FMEA 失效行
                  </button>
                </div>
              </td>
            </tr>

            <tr
              v-for="card in filteredItems"
              :key="card.id"
              :data-card-id="card.id"
              :data-target-id="card.target_id"
              class="fmea-row"
              :class="{
                'is-active': activeCardId === card.id,
                'is-dragover': dragOverCardId === card.id,
                'is-target-matched': isRowTargetMatched(card)
              }"
              title="双击整行可打开完整详情弹窗"
              @mouseenter="onCardMouseEnter(card.id)"
              @mouseleave="onCardMouseLeave(card.id)"
              @click="onCardClick(card.id)"
              @dblclick="$emit('edit-item', card)"
            >
              <!-- 1. 编号与类型 -->
              <td class="col-code">
                <div class="code-wrap">
                  <button
                    type="button"
                    class="fmea-type-badge-btn"
                    :class="`ft-${card.fmea_type.toLowerCase()}`"
                    title="点击切换 DFMEA / PFMEA"
                    @click.stop="toggleCardType(card)"
                  >
                    {{ card.fmea_type }}
                  </button>
                  <span
                    class="code-text"
                    title="点击复制编号"
                    @click.stop="copyText(card.fmea_code)"
                  >
                    {{ card.fmea_code }}
                  </span>
                  <span v-if="card.target_kind === 'shared_unit'" class="scope-shared-badge" title="跨画板共用本体经验">
                    共用
                  </span>

                  <!-- 行内保存状态反馈微标 -->
                  <div v-if="savingCardId === card.id" class="save-status saving" title="正在保存变更">
                    <span class="save-spinner" /> 保存中
                  </div>
                  <div v-else-if="savedCardId === card.id" class="save-status saved" title="已成功保存至数据库">
                    ✓ 已保存
                  </div>
                </div>
              </td>

              <!-- 2. 潜在失效模式 (直接点击输入编辑) -->
              <td class="col-mode">
                <div class="mode-cell-wrap">
                  <textarea
                    v-model="card.failure_mode"
                    class="cell-editor mode-editor"
                    rows="2"
                    placeholder="点击录入潜在失效表现 (如: 螺栓孔微动磨损松动)..."
                    title="点击直接修改失效模式，离开后自动保存"
                    @change="onInlineFieldChange(card, 'failure_mode', card.failure_mode)"
                    @keydown.enter.exact.prevent="($event.target as HTMLElement).blur()"
                  />

                  <!-- 挂接的现场质量单短标 -->
                  <div v-if="getCardQualityIssues(card).length > 0" class="qi-inline-list">
                    <span
                      v-for="(iss, iIdx) in getCardQualityIssues(card)"
                      :key="`${iss.code}_${iIdx}`"
                      class="qi-tag"
                      title="点击跳转现场质量问题台账"
                      @click.stop="openIssueInTab(iss.code)"
                    >
                      🚨 {{ iss.code }} ↗
                    </span>
                  </div>
                </div>
              </td>

              <!-- 3. 实拍/标准对比图单元格 (醒目图片维护、支持拖拽、直接 Ctrl+V 粘贴、灯箱大图) -->
              <td
                class="col-photo"
                :class="{ 'is-dragover': dragOverCardId === card.id }"
                @dragover.prevent="onCardDragOver(card.id)"
                @dragleave="onCardDragLeave(card.id)"
                @drop.prevent="onCardDrop($event, card)"
              >
                <!-- 已有实拍图片缩略列表 -->
                <div v-if="card.photos && card.photos.length > 0" class="photo-thumbs-container">
                  <div class="photo-thumbs-list">
                    <div
                      v-for="(ph, pIdx) in card.photos"
                      :key="ph.id || pIdx"
                      class="photo-thumb-card"
                      :class="ph.tag === 'OK' ? 'is-ok' : 'is-ng'"
                      title="点击放大检视或修改描述"
                      @click.stop="openLightbox(ph, card, pIdx)"
                    >
                      <img :src="ph.url" :alt="ph.caption || '实拍图'" />
                      <span class="pt-tag-pill" :class="ph.tag === 'OK' ? 'is-ok' : 'is-ng'">
                        {{ ph.tag === 'OK' ? 'OK 标准' : 'NG 缺陷' }}
                      </span>
                      <!-- 悬浮快捷操作 -->
                      <div class="pt-hover-overlay">
                        <button
                          type="button"
                          class="pho-btn tag"
                          title="切换 NG / OK 标签"
                          @click.stop="togglePhotoTag(card, pIdx)"
                        >
                          ⇄
                        </button>
                        <button
                          type="button"
                          class="pho-btn del"
                          title="移除此图"
                          @click.stop="removePhotoFromCard(card, pIdx)"
                        >
                          ×
                        </button>
                      </div>
                    </div>

                    <!-- 续传小入口 -->
                    <button
                      type="button"
                      class="photo-add-more-btn"
                      title="继续添加实拍或对比图 (支持拖拽/粘贴)"
                      @click.stop="triggerQuickPhoto(card)"
                    >
                      <span class="pam-plus">+</span>
                      <span class="pam-txt">续传</span>
                    </button>
                  </div>
                  <div class="photo-strip-hint">共 {{ card.photos.length }} 张 · 可直接 Ctrl+V 粘贴</div>
                </div>

                <!-- 空态提示：大号、醒目、易懂的上传与粘贴卡片 -->
                <div
                  v-else
                  class="photo-dropzone-empty"
                  title="点击选择图片，或拖入图片，或在此行按 Ctrl+V 粘贴"
                  @click.stop="triggerQuickPhoto(card)"
                >
                  <div class="pde-icon">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
                      <path d="M4 6h3l1.5-2.5h3L13 6h3a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z" />
                      <circle cx="10" cy="12" r="3.2" />
                    </svg>
                  </div>
                  <div class="pde-text">+ 上传/粘贴实拍</div>
                  <div class="pde-hint">支持拖拽与 Ctrl+V</div>
                </div>
              </td>

              <!-- 4. 失效机理与根本原因 -->
              <td class="col-mech">
                <textarea
                  v-model="card.failure_mech"
                  class="cell-editor text-editor mech-accent"
                  rows="3"
                  placeholder="录入微观物理机理或工艺失控原因..."
                  title="点击修改失效机理，离开后自动保存"
                  @change="onInlineFieldChange(card, 'failure_mech', card.failure_mech)"
                />
              </td>

              <!-- 5. 潜在失效后果 -->
              <td class="col-effect">
                <textarea
                  v-model="card.failure_effect"
                  class="cell-editor text-editor effect-accent"
                  rows="3"
                  placeholder="录入对模块功能、寿命或整机安全的影响..."
                  title="点击修改失效后果，离开后自动保存"
                  @change="onInlineFieldChange(card, 'failure_effect', card.failure_effect)"
                />
              </td>

              <!-- 6. 现行预防控制 -->
              <td class="col-prevent">
                <textarea
                  v-model="card.prevention_measure"
                  class="cell-editor text-editor prevent-accent"
                  rows="3"
                  placeholder="录入设计防呆与工艺预防控制措施..."
                  title="点击修改预防控制措施，离开后自动保存"
                  @change="onInlineFieldChange(card, 'prevention_measure', card.prevention_measure)"
                />
              </td>

              <!-- 7. 现行探测控制 -->
              <td class="col-detect">
                <textarea
                  v-model="card.detection_measure"
                  class="cell-editor text-editor detect-accent"
                  rows="3"
                  placeholder="录入在线检验、测试治具或出厂验证标准..."
                  title="点击修改探测验证标准，离开后自动保存"
                  @change="onInlineFieldChange(card, 'detection_measure', card.detection_measure)"
                />
              </td>

              <!-- 8. 风险定级 -->
              <td class="col-risk">
                <el-popover placement="bottom-end" :width="230" trigger="click">
                  <template #reference>
                    <button type="button" class="risk-badge-btn" :class="`rk-${card.risk_level.toLowerCase()}`">
                      <i class="dot" />
                      <span>{{ riskText(card.risk_level) }}</span>
                      <span v-if="card.rpn" class="rpn-val">·{{ card.rpn }}</span>
                    </button>
                  </template>
                  <div class="quick-risk-pop">
                    <div class="qr-title">切换风险定级</div>
                    <div class="qr-btns">
                      <button
                        v-for="lv in (['HIGH', 'MED', 'LOW'] as const)"
                        :key="lv"
                        type="button"
                        class="qr-btn"
                        :class="{ active: card.risk_level === lv }"
                        @click="$emit('quick-risk', card, lv)"
                      >
                        {{ riskText(lv) }}
                      </button>
                    </div>
                    <div v-if="card.rpn" class="qr-sod-note">
                      打分：S{{ card.severity }} · O{{ card.occurrence }} · D{{ card.detection }} = RPN {{ card.rpn }}
                    </div>
                  </div>
                </el-popover>
              </td>

              <!-- 9. 软关联标签 -->
              <td class="col-refs">
                <div class="refs-chip-cell">
                  <SoftRefChip
                    v-for="(rf, rIdx) in card.linked_refs"
                    :key="`${card.id}_rf_${rIdx}`"
                    :item="rf"
                  />
                  <span v-if="!card.linked_refs || card.linked_refs.length === 0" class="muted-dash">-</span>
                </div>
              </td>

              <!-- 10. 操作 (固定在最右侧，绝不被遮挡) -->
              <td class="col-actions">
                <div class="act-btns">
                  <button
                    type="button"
                    class="tbl-btn photo-btn"
                    :class="{ 'has-pic': (card.photos || []).length > 0 }"
                    title="上传或管理实拍图"
                    @click.stop="triggerQuickPhoto(card)"
                  >
                    图片 ({{ (card.photos || []).length }})
                  </button>
                  <button
                    type="button"
                    class="tbl-btn edit"
                    title="打开完整详情弹窗 (配置S·O·D/关联质量单/派发整改任务)"
                    @click.stop="$emit('edit-item', card)"
                  >
                    详情
                  </button>
                  <button
                    type="button"
                    class="tbl-btn del"
                    title="删除此失效记录"
                    @click.stop="$emit('delete-item', card)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 隐藏的文件选择器 -->
      <input
        ref="quickPhotoInputRef"
        type="file"
        accept="image/*"
        style="display: none"
        @change="onQuickPhotoSelected"
      />

      <!-- 全屏高清大图灯箱与照片维护 -->
      <el-dialog
        v-model="lightboxVisible"
        :title="lightboxPhoto?.caption || '失效实拍 / 防错标准大图检视'"
        width="760px"
        append-to-body
      >
        <div v-if="lightboxPhoto" class="lightbox-wrap">
          <img :src="lightboxPhoto.url" alt="大图预览" class="lightbox-img" />
          <div class="lightbox-footer">
            <div class="lf-tag-bar">
              <span class="lf-label">照片性质：</span>
              <button
                type="button"
                class="lf-tag-btn"
                :class="{ active: lightboxPhoto.tag === 'NG' }"
                @click="setLightboxPhotoTag('NG')"
              >
                ● NG 缺陷实拍
              </button>
              <button
                type="button"
                class="lf-tag-btn"
                :class="{ active: lightboxPhoto.tag === 'OK' }"
                @click="setLightboxPhotoTag('OK')"
              >
                ● OK 防错标准
              </button>
            </div>
            <div class="lf-caption-row">
              <input
                v-model="lightboxPhoto.caption"
                type="text"
                class="lf-cap-input"
                placeholder="在此输入失效实拍图的说明或防错判定标准..."
                @change="saveLightboxCaption"
              />
              <button
                type="button"
                class="lf-del-btn"
                @click="deleteCurrentLightboxPhoto"
              >
                🗑️ 删除此照片
              </button>
            </div>
          </div>
        </div>
      </el-dialog>
    </aside>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type {
  BoardCanvasData,
  CanvasSelection,
  FmeaItem,
  FmeaPhoto,
  RiskLevel,
  SubBoardRollupStat,
  WhereUsedRef
} from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import { useFmeaUpload } from '@/views/6_fmea/composables/useFmeaUpload'
import SoftRefChip from './SoftRefChip.vue'

const router = useRouter()

const props = defineProps<{
  activeBoardId?: number | null
  selection: CanvasSelection | null
  canvasData: BoardCanvasData
  items: FmeaItem[] // 归属该模块的失效项 (节点直属 + 共用件 + 模块热点)
  connectedEdgeItems?: FmeaItem[] // 归属该模块关联连线/接口的失效项
  allBoardItems?: FmeaItem[] // 全画板所有失效项
  subBoardStats?: Record<string, SubBoardRollupStat>
  unitWhereUsed?: Record<string, WhereUsedRef[]>
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (
    e: 'rename-target',
    payload: {
      title?: string
      sub?: string
      unit_code?: string | null
      is_limit?: boolean
      limit_spec?: string
      kind?: 'normal' | 'process_challenge'
    }
  ): void
  (e: 'delete-target'): void
  (e: 'drill-sub-board', subBoardId: number): void
  (e: 'jump-to-board', payload: { boardId: number; nodeId?: string }): void
  (e: 'create-item'): void
  (e: 'item-created', item: FmeaItem): void
  (e: 'item-updated', item: FmeaItem): void
  (e: 'edit-item', item: FmeaItem): void
  (e: 'delete-item', item: FmeaItem): void
  (e: 'quick-risk', item: FmeaItem, risk: RiskLevel): void
  (e: 'append-photo', item: FmeaItem, photo: FmeaPhoto): void
}>()

const { uploadImageFile, extractImagesFromClipboard, extractImagesFromDrop } = useFmeaUpload()

// 抽屉宽度：初始 70%，支持左侧把手自由拖拽拉伸
const drawerWidth = ref(Math.round(window.innerWidth * 0.70))
const isResizing = ref(false)

function onWindowResize() {
  if (!isResizing.value && drawerWidth.value > window.innerWidth * 0.94) {
    drawerWidth.value = Math.round(window.innerWidth * 0.92)
  }
}

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startX = e.clientX
  const startW = drawerWidth.value

  function onMouseMove(ev: MouseEvent) {
    const delta = startX - ev.clientX
    const minW = 540
    const maxW = Math.round(window.innerWidth * 0.95)
    drawerWidth.value = Math.max(minW, Math.min(maxW, startW + delta))
  }

  function onMouseUp() {
    isResizing.value = false
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

onMounted(() => {
  window.addEventListener('resize', onWindowResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowResize)
})

const quickPhotoInputRef = ref<HTMLInputElement | null>(null)
const quickPhotoTargetCard = ref<FmeaItem | null>(null)

// 大图灯箱
const lightboxVisible = ref(false)
const lightboxPhoto = ref<FmeaPhoto | null>(null)
const lightboxCard = ref<FmeaItem | null>(null)
const lightboxIndex = ref<number>(-1)

// 范围切换：'module' (本模块专属) | 'interfaces' (关联工序接口) | 'board' (全画板所有失效)
const scopeMode = ref<'module' | 'interfaces' | 'board'>('module')

// 表格内检索与风险过滤
const tableFilterText = ref('')
const riskFilter = ref<'ALL' | 'HIGH'>('ALL')

// 行内即时保存状态追踪
const savingCardId = ref<number | null>(null)
const savedCardId = ref<number | null>(null)
let saveTimer: any = null

const currentDisplayItems = computed(() => {
  if (scopeMode.value === 'board') return props.allBoardItems || []
  if (scopeMode.value === 'interfaces') return props.connectedEdgeItems || []
  return props.items || []
})

const highRiskCount = computed(() => {
  return currentDisplayItems.value.filter((it) => it.risk_level === 'HIGH').length
})

const filteredItems = computed(() => {
  let list = currentDisplayItems.value
  if (riskFilter.value === 'HIGH') {
    list = list.filter((it) => it.risk_level === 'HIGH')
  }
  const q = tableFilterText.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((it) => {
    return (
      it.failure_mode.toLowerCase().includes(q) ||
      (it.failure_mech || '').toLowerCase().includes(q) ||
      (it.failure_effect || '').toLowerCase().includes(q) ||
      (it.prevention_measure || '').toLowerCase().includes(q) ||
      (it.detection_measure || '').toLowerCase().includes(q) ||
      it.fmea_code.toLowerCase().includes(q)
    )
  })
})

// 拖拽与鼠标焦点卡片追踪
const activeCardId = ref<number | null>(null)
const hoveredCardId = ref<number | null>(null)
const dragOverCardId = ref<number | null>(null)

const selectedNode = computed(() => {
  if (props.selection?.kind !== 'node') return null
  return props.canvasData.nodes.find((n) => n.id === props.selection!.id) || null
})

const currentUnitWhereUsed = computed<WhereUsedRef[]>(() => {
  const code = selectedNode.value?.unit_code
  if (!code || !props.unitWhereUsed) return []
  return props.unitWhereUsed[code] || []
})

const currentSubBoardStat = computed<SubBoardRollupStat | null>(() => {
  const sbId = selectedNode.value?.sub_board_id
  if (!sbId || !props.subBoardStats) return null
  return props.subBoardStats[String(sbId)] || null
})

function isRowTargetMatched(card: FmeaItem): boolean {
  if (!props.selection) return false
  if (card.target_id === props.selection.id) return true
  if (props.selection.kind === 'node') {
    const uc = selectedNode.value?.unit_code
    if (uc && (card.target_id === uc || (card.ref_codes_text || '').includes(uc))) return true
  }
  return false
}

function scrollToActiveSelection(targetId?: string) {
  if (!targetId) return
  nextTick(() => {
    let el = document.querySelector(`.fmea-row[data-target-id="${targetId}"]`) as HTMLElement | null
    if (!el && selectedNode.value?.unit_code) {
      el = document.querySelector(`.fmea-row[data-target-id="${selectedNode.value.unit_code}"]`) as HTMLElement | null
    }
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      el.classList.add('row-pulse-highlight')
      setTimeout(() => el.classList.remove('row-pulse-highlight'), 2200)
    }
  })
}

watch(
  () => props.selection?.id,
  (newId) => {
    activeCardId.value = null
    hoveredCardId.value = null
    dragOverCardId.value = null
    tableFilterText.value = ''
    scopeMode.value = 'module'
    if (newId) {
      scrollToActiveSelection(newId)
    }
  },
  { immediate: true }
)

const kindLabel = computed(() => {
  if (props.selection?.kind === 'pin') return '图纸剖面热点'
  if (props.selection?.kind === 'edge') return '配合接口'
  if (selectedNode.value?.sub_board_id) return '嵌套子模块'
  if (selectedNode.value?.unit_code) return '共用件'
  return '模块节点'
})

const shortKindLabel = computed(() => {
  if (props.selection?.kind === 'pin') return '剖面热点'
  if (props.selection?.kind === 'edge') return '接口'
  if (selectedNode.value?.sub_board_id) return '子模块'
  if (selectedNode.value?.unit_code) return '共用件'
  return '模块'
})

const kindPillClass = computed(() => {
  if (props.selection?.kind === 'pin') return 'k-pin'
  if (props.selection?.kind === 'edge') return 'k-edge'
  if (selectedNode.value?.sub_board_id) return 'k-sub'
  if (selectedNode.value?.unit_code) return 'k-shared'
  return 'k-node'
})

const activeTarget = computed(() => {
  const sel = props.selection
  if (!sel) return null
  if (sel.kind === 'node') {
    const nd = props.canvasData.nodes.find((n) => n.id === sel.id)
    return nd ? { title: nd.title, sub: nd.sub || '' } : null
  }
  if (sel.kind === 'edge') {
    const ed = props.canvasData.edges.find((e) => e.id === sel.id)
    return ed ? { title: ed.label, sub: ed.sub || '' } : null
  }
  for (const ib of props.canvasData.image_boards) {
    const p = ib.pins.find((pin) => pin.id === sel.id)
    if (p) return { title: p.title, sub: p.sub || ib.title }
  }
  return null
})

const selectedPin = computed(() => {
  if (props.selection?.kind !== 'pin') return null
  for (const ib of props.canvasData.image_boards) {
    const p = ib.pins.find((pin) => pin.id === props.selection!.id)
    if (p) return p
  }
  return null
})

const selectedEdge = computed(() => {
  if (props.selection?.kind !== 'edge') return null
  return props.canvasData.edges.find((e) => e.id === props.selection!.id) || null
})

function togglePinLimit() {
  if (!selectedPin.value) return
  emit('rename-target', { is_limit: !selectedPin.value.is_limit })
}

function onPinLimitSpecChange(val: string) {
  emit('rename-target', { limit_spec: val.trim() })
}

function setEdgeKind(k: 'normal' | 'process_challenge') {
  emit('rename-target', { kind: k })
}

function getCardQualityIssues(card: FmeaItem) {
  const list: { code: string; label: string; ref_id?: number | null }[] = []
  const seen = new Set<string>()
  for (const r of card.linked_refs || []) {
    if (r.type === 'issue' && r.code) {
      list.push({ code: r.code, label: r.label, ref_id: r.ref_id })
      seen.add(r.code)
    }
  }
  if (card.source_issue_no && !seen.has(card.source_issue_no)) {
    list.push({ code: card.source_issue_no, label: '现场挂接异常单' })
  }
  return list
}

function openIssueInTab(code: string) {
  const routeUrl = router.resolve({
    path: '/issue',
    query: { keyword: code }
  })
  window.open(routeUrl.href, '_blank')
}

function riskText(r: RiskLevel) {
  if (r === 'HIGH') return '高危'
  if (r === 'MED') return '中危'
  return '低危'
}

function copyText(txt: string) {
  navigator.clipboard.writeText(txt).then(() => {
    ElMessage.success(`已复制 ${txt}`)
  })
}

function onTitleChange(val: string) {
  emit('rename-target', { title: val.trim() })
}

function onSubChange(val: string) {
  emit('rename-target', { sub: val.trim() })
}

function enableSharedUnit() {
  const nd = selectedNode.value
  if (!nd) return
  const code = (nd.sub || nd.title || 'PRT-UNIT').trim().toUpperCase()
  emit('rename-target', { unit_code: code, sub: code })
  ElMessage.success(`已将此模块启用为共用件「${code}」`)
}

function unbindUnitCode() {
  emit('rename-target', { unit_code: null })
  ElMessage.info('已解除共用件绑定')
}

// ==================== 【重点】单元格行内即时维护与保存 ====================

async function onInlineFieldChange(card: FmeaItem, field: string, val: any) {
  savingCardId.value = card.id
  try {
    const payload: Partial<FmeaItem> = {
      [field]: typeof val === 'string' ? val.trim() : val
    }
    await fmeaApi.updateItem(card.id, payload)
    savingCardId.value = null
    savedCardId.value = card.id
    clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      savedCardId.value = null
    }, 2000)
    emit('item-updated', { ...card, ...payload })
  } catch (err: any) {
    savingCardId.value = null
    ElMessage.error('自动保存失败：' + (err?.message || '网络异常'))
  }
}

async function toggleCardType(card: FmeaItem) {
  const nextType = card.fmea_type === 'DFMEA' ? 'PFMEA' : 'DFMEA'
  card.fmea_type = nextType
  await onInlineFieldChange(card, 'fmea_type', nextType)
  ElMessage.info(`已切换为 ${nextType}`)
}

async function handleQuickAddRow() {
  if (!props.selection || !props.activeBoardId) return
  try {
    const title = activeTarget.value?.title || '新失效分析项'
    const defaultPartCode =
      selectedNode.value?.unit_code ||
      (selectedNode.value?.sub?.startsWith('PRT-') ? selectedNode.value.sub : '')
    const refs = defaultPartCode
      ? [{ type: 'part' as const, ref_id: null, code: defaultPartCode, label: title }]
      : []

    const newItem = await fmeaApi.createItem({
      board_id: props.activeBoardId,
      target_kind: props.selection.kind,
      target_id: props.selection.id,
      target_title_snapshot: title,
      fmea_type: 'DFMEA',
      failure_mode: '',
      failure_mech: '',
      failure_effect: '',
      prevention_measure: '',
      detection_measure: '',
      risk_level: 'MED',
      severity: 6,
      occurrence: 4,
      detection: 4,
      photos: [],
      linked_refs: refs
    })

    emit('item-created', newItem)
    ElMessage.success('已新建失效行，直接在单元格输入即可')

    setTimeout(() => {
      const el = document.querySelector(
        `.fmea-row[data-card-id="${newItem.id}"] .mode-editor`
      ) as HTMLTextAreaElement | null
      el?.focus()
    }, 120)
  } catch {
    ElMessage.error('新建失效行失败')
  }
}

// ==================== 【重点】图片维护与上传 / 拖拽 / Ctrl+V ====================

function openLightbox(ph: FmeaPhoto, card: FmeaItem, pIdx: number) {
  lightboxPhoto.value = { ...ph }
  lightboxCard.value = card
  lightboxIndex.value = pIdx
  lightboxVisible.value = true
}

async function setLightboxPhotoTag(tag: 'NG' | 'OK') {
  if (!lightboxPhoto.value || !lightboxCard.value || lightboxIndex.value < 0) return
  lightboxPhoto.value.tag = tag
  await togglePhotoTag(lightboxCard.value, lightboxIndex.value, tag)
}

async function saveLightboxCaption() {
  if (!lightboxPhoto.value || !lightboxCard.value || lightboxIndex.value < 0) return
  const card = lightboxCard.value
  const pIdx = lightboxIndex.value
  const nextPhotos = [...(card.photos || [])]
  if (nextPhotos[pIdx]) {
    nextPhotos[pIdx] = { ...nextPhotos[pIdx], caption: lightboxPhoto.value.caption }
    await fmeaApi.updateItem(card.id, { photos: nextPhotos })
    card.photos = nextPhotos
    ElMessage.success('已更新图片说明')
  }
}

async function deleteCurrentLightboxPhoto() {
  if (!lightboxCard.value || lightboxIndex.value < 0) return
  const card = lightboxCard.value
  const pIdx = lightboxIndex.value
  lightboxVisible.value = false
  await removePhotoFromCard(card, pIdx)
}

// 拖拽贴图交互
function onCardMouseEnter(cardId: number) {
  hoveredCardId.value = cardId
}

function onCardMouseLeave(cardId: number) {
  if (hoveredCardId.value === cardId) {
    hoveredCardId.value = null
  }
}

function onCardClick(cardId: number) {
  activeCardId.value = cardId
}

function onCardDragOver(cardId: number) {
  dragOverCardId.value = cardId
}

function onCardDragLeave(cardId: number) {
  if (dragOverCardId.value === cardId) {
    dragOverCardId.value = null
  }
}

async function onCardDrop(e: DragEvent, card: FmeaItem) {
  dragOverCardId.value = null
  const files = extractImagesFromDrop(e)
  if (!files.length) return
  for (const f of files) {
    await doUploadPhotoToCard(card, f)
  }
}

// 抽屉全局 Ctrl+V 粘贴监听
async function onPanelPaste(e: ClipboardEvent) {
  const targetTag = (e.target as HTMLElement)?.tagName?.toLowerCase()
  if (targetTag === 'input' || targetTag === 'textarea') {
    // 若正在纯文本框里输入文字，允许正常粘贴文本；只有在剪贴板有文件时才贴图
    if (!e.clipboardData?.files?.length) return
  }

  const files = extractImagesFromClipboard(e)
  if (!files.length) return

  e.preventDefault()
  let targetCard: FmeaItem | undefined
  if (activeCardId.value) {
    targetCard = filteredItems.value.find((c) => c.id === activeCardId.value)
  }
  if (!targetCard && hoveredCardId.value) {
    targetCard = filteredItems.value.find((c) => c.id === hoveredCardId.value)
  }
  if (!targetCard && filteredItems.value.length === 1) {
    targetCard = filteredItems.value[0]
  }

  if (!targetCard) {
    ElMessage.info('请先点击表格中的任意一行 FMEA，再按 Ctrl+V 粘贴实拍图片')
    return
  }

  for (const f of files) {
    await doUploadPhotoToCard(targetCard, f)
  }
}

function triggerQuickPhoto(card: FmeaItem) {
  quickPhotoTargetCard.value = card
  quickPhotoInputRef.value?.click()
}

async function onQuickPhotoSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  const card = quickPhotoTargetCard.value
  if (!f || !card) return
  await doUploadPhotoToCard(card, f)
}

async function doUploadPhotoToCard(card: FmeaItem, file: File) {
  const uploaded = await uploadImageFile(file, 'fmea_photo', card.id)
  if (!uploaded) return
  const autoTag: 'NG' | 'OK' = (card.photos || []).some((p) => p.tag === 'NG') ? 'OK' : 'NG'
  const newPhoto: FmeaPhoto = {
    id: `ph_${Date.now().toString(36)}`,
    attachment_id: uploaded.attachment_id,
    url: uploaded.url,
    tag: autoTag,
    caption: ''
  }
  const nextPhotos = [...(card.photos || []), newPhoto]
  try {
    await fmeaApi.updateItem(card.id, { photos: nextPhotos })
    card.photos = nextPhotos
    emit('append-photo', card, newPhoto)
    ElMessage.success('实拍照片已贴入该 FMEA 失效行')
  } catch {
    ElMessage.error('照片贴入失败')
  }
}

async function togglePhotoTag(card: FmeaItem, pIdx: number, specificTag?: 'NG' | 'OK') {
  const nextPhotos = [...(card.photos || [])]
  const cur = nextPhotos[pIdx]
  if (!cur) return
  const nextTag = specificTag || (cur.tag === 'NG' ? 'OK' : 'NG')
  nextPhotos[pIdx] = {
    ...cur,
    tag: nextTag
  }
  await fmeaApi.updateItem(card.id, { photos: nextPhotos })
  card.photos = nextPhotos
  ElMessage.success(`已切换为 ${nextTag === 'OK' ? 'OK 标准' : 'NG 实拍'} 标签`)
}

async function removePhotoFromCard(card: FmeaItem, pIdx: number) {
  const nextPhotos = [...(card.photos || [])]
  nextPhotos.splice(pIdx, 1)
  await fmeaApi.updateItem(card.id, { photos: nextPhotos })
  card.photos = nextPhotos
  ElMessage.success('已移除该实拍照片')
}
</script>

<style scoped>
/* 100% 高度、贴合边缘的抽屉容器 (图层高于画布所有元素 z-index: 200) */
.fmea-module-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  height: 100%;
  background: #ffffff;
  border-left: 1px solid #cbd5e1;
  border-radius: 0;
  box-shadow: -12px 0 40px rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 200;
  transition: box-shadow 0.2s ease;
}

.fmea-module-drawer.is-resizing {
  user-select: none !important;
  cursor: col-resize !important;
}

.slide-panel-enter-active,
.slide-panel-leave-active {
  transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
}

.slide-panel-enter-from,
.slide-panel-leave-to {
  transform: translateX(48px);
  opacity: 0;
}

/* 左侧拖拽调整抽屉宽度手柄 */
.drawer-resizer-handle {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 10px;
  cursor: col-resize;
  z-index: 210;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drawer-resizer-handle:hover .resizer-bar,
.fmea-module-drawer.is-resizing .resizer-bar {
  background: #2563eb;
  height: 72px;
  opacity: 1;
}

.resizer-bar {
  width: 3px;
  height: 48px;
  border-radius: 2px;
  background: #cbd5e1;
  opacity: 0.7;
  transition: all 0.15s;
}

/* 1. 顶部抽屉工具栏 */
.drawer-header {
  height: 52px;
  padding: 0 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}

.dh-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.elem-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  flex-shrink: 0;
}

.elem-badge.k-pin { background: #fee2e2; color: #dc2626; }
.elem-badge.k-node { background: #eff6ff; color: #1d4ed8; }
.elem-badge.k-shared { background: #e0f2fe; color: #0284c7; }
.elem-badge.k-sub { background: #eef2ff; color: #4338ca; }
.elem-badge.k-edge { background: #f5f3ff; color: #6d28d9; }

.clean-title-input {
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  outline: none;
  background: transparent;
  max-width: 220px;
  text-overflow: ellipsis;
  transition: all 0.14s;
}

.clean-title-input:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.clean-title-input:focus {
  background: #ffffff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.shared-unit-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  flex-shrink: 0;
}

.suc-label {
  font-size: 10.5px;
  color: #0369a1;
  font-weight: 500;
}

.suc-code {
  font-family: monospace;
  font-weight: 700;
  color: #0c4a6e;
}

.suc-where-btn {
  border: none;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 3px;
  cursor: pointer;
  font-weight: 600;
}

.suc-where-btn:hover {
  background: #bae6fd;
}

.suc-unbind-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 10.5px;
  cursor: pointer;
}

.suc-unbind-btn:hover {
  color: #dc2626;
}

.simple-code-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.clean-sub-input {
  border: 1px solid transparent;
  background: transparent;
  border-radius: 3px;
  padding: 1px 5px;
  font-size: 11.5px;
  color: #64748b;
  outline: none;
  width: 130px;
}

.clean-sub-input:hover {
  background: #f8fafc;
}

.clean-sub-input:focus {
  background: #ffffff;
  border-color: #cbd5e1;
}

.enable-share-link {
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 11px;
  cursor: pointer;
  padding: 0 4px;
}

.enable-share-link:hover {
  text-decoration: underline;
}

.sub-board-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #eef2ff;
  border-radius: 4px;
  padding: 2px 7px;
}

.sbs-meta {
  font-size: 11px;
  color: #3730a3;
}

.sbs-meta .hi {
  color: #dc2626;
  font-weight: 700;
}

.sbs-drill-btn {
  border: none;
  background: #4f46e5;
  color: #ffffff;
  font-size: 10.5px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
}

.pin-mini-strip,
.edge-mini-strip {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pin-limit-pill,
.edge-pill {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  cursor: pointer;
}

.pin-limit-pill.active {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #b45309;
  font-weight: 600;
}

.edge-pill.active {
  border-color: #8b5cf6;
  background: #f5f3ff;
  color: #6d28d9;
  font-weight: 600;
}

.pin-spec-input {
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  width: 140px;
}

.dh-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.table-search-input {
  width: 160px;
  height: 28px;
  padding: 0 9px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 11.5px;
  background: #f8fafc;
  outline: none;
  transition: all 0.14s;
}

.table-search-input:focus {
  width: 200px;
  border-color: #2563eb;
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.risk-filter-pills {
  display: flex;
  background: #f1f5f9;
  padding: 2px;
  border-radius: 6px;
}

.rf-pill {
  border: none;
  background: transparent;
  font-size: 11px;
  color: #64748b;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.14s;
}

.rf-pill.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.rf-pill.r-high.active {
  background: #fee2e2;
  color: #dc2626;
}

.add-item-btn {
  height: 28px;
  padding: 0 11px;
  border-radius: 6px;
  border: none;
  background: #0f172a;
  color: #ffffff;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: background 0.14s;
}

.add-item-btn:hover {
  background: #2563eb;
}

.icon-ghost-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  cursor: pointer;
  transition: all 0.12s;
}

.icon-ghost-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.close-btn {
  font-size: 18px;
  line-height: 1;
}

.close-btn:hover {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fecaca;
}

/* 2. 次级范围选择栏 */
.drawer-sub-bar {
  padding: 8px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}

.scope-mode-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #e2e8f0;
  padding: 2.5px;
  border-radius: 7px;
}

.smt-btn {
  border: none;
  background: transparent;
  font-size: 11.5px;
  font-weight: 600;
  color: #475569;
  padding: 4px 10px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.14s;
}

.smt-btn:hover {
  color: #0f172a;
}

.smt-btn.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.1);
}

.sub-bar-hint {
  font-size: 11px;
  color: #64748b;
}

/* 3. 工作表格壳容器 (支持横向和纵向滚动) */
.drawer-table-shell {
  flex: 1;
  overflow: auto;
  position: relative;
  background: #f8fafc;
}

.module-fmea-table {
  width: 100%;
  min-width: 1450px;
  border-collapse: separate;
  border-spacing: 0;
  background: #ffffff;
}

.module-fmea-table thead {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #f8fafc;
}

.module-fmea-table th {
  padding: 9px 10px;
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  text-align: left;
  border-bottom: 2px solid #cbd5e1;
  border-right: 1px solid #f1f5f9;
  background: #f8fafc;
  white-space: nowrap;
}

.module-fmea-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  border-right: 1px solid #f1f5f9;
  vertical-align: top;
  color: #1e293b;
  line-height: 1.45;
  background: #ffffff;
}

.fmea-row {
  transition: background 0.12s;
}

.fmea-row:hover td {
  background: #fcfdfe;
}

.fmea-row.is-active td {
  background: #eff6ff !important;
}

.fmea-row.is-target-matched td {
  background: #f8fafc;
}

.fmea-row.row-pulse-highlight td {
  background: #eff6ff !important;
  box-shadow: inset 0 0 0 1.5px #2563eb;
  transition: all 0.3s ease;
}

.fmea-row.is-dragover td {
  background: #dbeafe !important;
  outline: 2px dashed #2563eb;
}

/* 列特定样式 */
.col-code .code-wrap {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.code-text {
  font-family: monospace;
  font-size: 11px;
  font-weight: 700;
  color: #0f172a;
  cursor: pointer;
}

.code-text:hover {
  color: #2563eb;
  text-decoration: underline;
}

.fmea-type-badge-btn {
  font-size: 9.5px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  width: fit-content;
  border: 1px solid transparent;
  background: #eff6ff;
  color: #1d4ed8;
  cursor: pointer;
}

.fmea-type-badge-btn:hover {
  opacity: 0.85;
}

.fmea-type-badge-btn.ft-pfmea { background: #ecfdf5; color: #047857; }
.fmea-type-badge-btn.ft-lesson { background: #fffbeb; color: #b45309; }

.scope-shared-badge {
  font-size: 9.5px;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 3px;
  background: #e0f2fe;
  color: #0369a1;
  width: fit-content;
}

.save-status {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  width: fit-content;
}

.save-status.saving {
  background: #eff6ff;
  color: #2563eb;
}

.save-status.saved {
  background: #ecfdf5;
  color: #059669;
  font-weight: 600;
}

.save-spinner {
  width: 7px;
  height: 7px;
  border: 1.5px solid #2563eb;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 单元格行内编辑器 */
.cell-editor {
  width: 100%;
  font-family: inherit;
  font-size: 12px;
  line-height: 1.45;
  color: #1e293b;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 4px 6px;
  outline: none;
  resize: vertical;
  transition: border-color 0.14s, background 0.14s, box-shadow 0.14s;
  box-sizing: border-box;
}

.cell-editor:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.cell-editor:focus {
  background: #ffffff;
  border-color: #2563eb !important;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.14) !important;
}

.mode-editor {
  font-size: 12.5px;
  font-weight: 700;
  color: #0f172a;
}

.mech-accent {
  border-left: 3px solid #f59e0b;
}

.effect-accent {
  border-left: 3px solid #64748b;
}

.prevent-accent {
  border-left: 3px solid #2563eb;
}

.detect-accent {
  border-left: 3px solid #059669;
}

.mode-cell-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qi-inline-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.qi-tag {
  font-size: 10px;
  background: #fff1f2;
  border: 1px solid #fecdd3;
  color: #e11d48;
  font-family: monospace;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  cursor: pointer;
}

.qi-tag:hover {
  background: #fee2e2;
}

/* 照片单元格 (醒目上传与维护) */
.col-photo {
  min-width: 170px;
  width: 170px;
  vertical-align: top;
}

.photo-dropzone-empty {
  border: 1.5px dashed #cbd5e1;
  border-radius: 6px;
  background: #f8fafc;
  padding: 8px 6px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.photo-dropzone-empty:hover,
.col-photo.is-dragover .photo-dropzone-empty {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.pde-icon svg {
  width: 20px;
  height: 20px;
  color: #64748b;
}

.photo-dropzone-empty:hover .pde-icon svg {
  color: #2563eb;
}

.pde-text {
  font-size: 11.5px;
  font-weight: 600;
  color: #334155;
}

.pde-hint {
  font-size: 10px;
  color: #94a3b8;
}

.photo-thumbs-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.photo-thumbs-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.photo-thumb-card {
  position: relative;
  width: 52px;
  height: 52px;
  border-radius: 5px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
  cursor: pointer;
  background: #0f172a;
  flex-shrink: 0;
}

.photo-thumb-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.pt-tag-pill {
  position: absolute;
  bottom: 2px;
  left: 2px;
  padding: 1px 4px;
  font-size: 8.5px;
  font-weight: 700;
  border-radius: 3px;
  line-height: 1.1;
  z-index: 2;
}

.pt-tag-pill.is-ok {
  background: #059669;
  color: #ffffff;
}

.pt-tag-pill.is-ng {
  background: #dc2626;
  color: #ffffff;
}

.pt-hover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.14s;
  z-index: 3;
}

.photo-thumb-card:hover .pt-hover-overlay {
  opacity: 1;
}

.pho-btn {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  color: #0f172a;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pho-btn.del:hover {
  background: #ef4444;
  color: #ffffff;
}

.pho-btn.tag:hover {
  background: #2563eb;
  color: #ffffff;
}

.photo-add-more-btn {
  width: 52px;
  height: 52px;
  border-radius: 5px;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #64748b;
  font-size: 10px;
  font-weight: 600;
  transition: all 0.14s;
  flex-shrink: 0;
}

.photo-add-more-btn:hover {
  border-color: #2563eb;
  background: #eff6ff;
  color: #2563eb;
}

.photo-strip-hint {
  font-size: 9.5px;
  color: #94a3b8;
}

/* 风险定级胶囊 */
.risk-badge-btn {
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 10.5px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  white-space: nowrap;
}

.risk-badge-btn .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.risk-badge-btn.rk-high { background: #fee2e2; border-color: #fecaca; color: #dc2626; }
.risk-badge-btn.rk-high .dot { background: #ef4444; }
.risk-badge-btn.rk-med { background: #fef3c7; border-color: #fde68a; color: #d97706; }
.risk-badge-btn.rk-med .dot { background: #f59e0b; }
.risk-badge-btn.rk-low { background: #ecfdf5; border-color: #a7f3d0; color: #059669; }
.risk-badge-btn.rk-low .dot { background: #10b981; }

.rpn-val {
  opacity: 0.85;
  font-variant-numeric: tabular-nums;
}

.refs-chip-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.muted-dash {
  color: #cbd5e1;
}

/* 固定在最右侧的操作列 */
.col-actions {
  position: sticky;
  right: 0;
  background: #ffffff !important;
  box-shadow: -6px 0 12px rgba(15, 23, 42, 0.05);
  z-index: 10;
}

.th-actions {
  position: sticky;
  right: 0;
  background: #f8fafc !important;
  box-shadow: -6px 0 12px rgba(15, 23, 42, 0.05);
  z-index: 25;
}

.act-btns {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.tbl-btn {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  padding: 3px 6px;
  font-size: 11px;
  border-radius: 4px;
  cursor: pointer;
  color: #475569;
  transition: all 0.12s;
  white-space: nowrap;
}

.tbl-btn.photo-btn {
  color: #0369a1;
  border-color: #bae6fd;
  background: #f0f9ff;
}

.tbl-btn.photo-btn:hover {
  background: #e0f2fe;
}

.tbl-btn.photo-btn.has-pic {
  font-weight: 600;
}

.tbl-btn.edit:hover {
  border-color: #3b82f6;
  color: #2563eb;
  background: #eff6ff;
}

.tbl-btn.del:hover {
  border-color: #fecaca;
  color: #dc2626;
  background: #fef2f2;
}

.empty-cell {
  padding: 40px !important;
  text-align: center;
}

.empty-hint-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.empty-txt {
  font-size: 12.5px;
  color: #64748b;
  margin: 0;
}

.pri-ghost-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 5px;
  border: 1px solid #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
}

/* 风险快速定级弹窗 */
.quick-risk-pop {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qr-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #0f172a;
}

.qr-btns {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 5px;
}

.qr-btn {
  height: 24px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  font-size: 11px;
  cursor: pointer;
}

.qr-btn.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

.qr-sod-note {
  font-size: 10.5px;
  color: #64748b;
}

.where-used-pop {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.wu-head {
  font-size: 11.5px;
  font-weight: 600;
  color: #334155;
  padding-bottom: 4px;
  border-bottom: 1px solid #f1f5f9;
}

.wu-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.wu-item {
  padding: 5px 7px;
  border-radius: 5px;
  border: 1px solid #f1f5f9;
  background: #f8fafc;
  text-align: left;
  cursor: pointer;
}

.wu-item:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.wui-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.wui-board {
  font-size: 11.5px;
  font-weight: 600;
  color: #0f172a;
}

.wui-cur-tag {
  font-size: 9.5px;
  padding: 0 4px;
  border-radius: 3px;
  background: #dbeafe;
  color: #1d4ed8;
}

.wui-sub {
  font-size: 10px;
  color: #64748b;
  margin-top: 1px;
}

.lightbox-wrap {
  background: #0f172a;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.lightbox-img {
  max-width: 100%;
  max-height: 520px;
  object-fit: contain;
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.lightbox-footer {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #1e293b;
  border-radius: 6px;
  padding: 10px 12px;
}

.lf-tag-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lf-label {
  font-size: 12px;
  color: #94a3b8;
}

.lf-tag-btn {
  border: 1px solid #475569;
  background: #0f172a;
  color: #cbd5e1;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s;
}

.lf-tag-btn:hover {
  background: #334155;
}

.lf-tag-btn.active {
  border-color: #3b82f6;
  background: #1d4ed8;
  color: #ffffff;
}

.lf-caption-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lf-cap-input {
  flex: 1;
  height: 28px;
  padding: 0 8px;
  border: 1px solid #475569;
  border-radius: 4px;
  background: #0f172a;
  color: #f8fafc;
  font-size: 11.5px;
  outline: none;
}

.lf-cap-input:focus {
  border-color: #3b82f6;
}

.lf-del-btn {
  height: 28px;
  padding: 0 10px;
  border: 1px solid #7f1d1d;
  background: #450a0a;
  color: #fca5a5;
  font-size: 11px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s;
}

.lf-del-btn:hover {
  background: #dc2626;
  color: #ffffff;
}
</style>
