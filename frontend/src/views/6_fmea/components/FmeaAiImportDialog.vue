<template>
  <el-dialog
    :model-value="modelValue"
    title="AI 智能图文录入 — 自动拆解 FMEA 并归入画布节点"
    width="760px"
    destroy-on-close
    append-to-body
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="ai-fmea-body" @paste="onPasteImages">
      <!-- 步骤一：输入现场异常文本 / 外部 JSON + 粘贴截图 -->
      <div class="source-box">
        <div class="sb-head">
          <span class="sb-title">1. 粘贴现场异常记录、8D 报告片段或失效照片（支持 <kbd>Ctrl+V</kbd> 贴图）</span>
          <div class="sb-tools">
            <button type="button" class="link-mini-btn" @click="fillSampleText">填入示例</button>
            <button type="button" class="link-mini-btn" @click="copyExternalPrompt">
              复制外部大模型提示词
            </button>
          </div>
        </div>

        <textarea
          v-model="rawText"
          rows="4"
          class="raw-textarea"
          placeholder="例如：二代旋转关节老化测试 20h 后谐波柔轮 PRT-102（绿的谐波 SUP-008）齿根出现疲劳微裂纹，原因是过渡圆角仅 R0.15 应力集中；要求图纸强标圆角 R≥0.30 并增加喷丸工艺（或直接粘贴外部大模型输出的 JSON 代码块）..."
        />

        <!-- 已粘贴的现场图片列表 -->
        <div v-if="pastedPhotos.length > 0" class="pasted-strip">
          <div v-for="(ph, idx) in pastedPhotos" :key="ph.id || idx" class="ps-item">
            <img :src="ph.url" alt="粘贴截图" />
            <span class="ps-tag">{{ ph.tag }}</span>
            <button type="button" class="ps-rm" @click="pastedPhotos.splice(idx, 1)">×</button>
          </div>
        </div>

        <div class="parse-bar">
          <span class="parse-hint">将自动匹配库内零件图号、供应商与当前画板模块节点</span>
          <el-button type="primary" size="small" :loading="parsing || uploading" @click="runAiParse">
            智能拆解预览
          </el-button>
        </div>
      </div>

      <!-- 步骤二：拆解草稿预览与画布落点确认 -->
      <div v-if="drafts.length > 0" class="drafts-sec">
        <div class="ds-head">
          <span class="ds-title">
            2. 已拆解 {{ drafts.length }} 条 FMEA 卡片草稿
            <small class="engine-badge">{{ engineModeLabel }}</small>
          </span>
        </div>

        <div class="draft-list">
          <div v-for="(d, idx) in drafts" :key="idx" class="draft-card">
            <div class="dc-top">
              <select v-model="d.fmea_type" class="mini-sel">
                <option value="DFMEA">DFMEA</option>
                <option value="PFMEA">PFMEA</option>
                <option value="LESSON">历史教训</option>
              </select>
              <input v-model="d.failure_mode" class="dc-mode-input" placeholder="失效模式" />
              <select v-model="d.risk_level" class="mini-sel">
                <option value="HIGH">高危</option>
                <option value="MED">中危</option>
                <option value="LOW">低危</option>
              </select>
              <button type="button" class="dc-del" title="移除此草稿" @click="drafts.splice(idx, 1)">×</button>
            </div>

            <div class="dc-grid">
              <input v-model="d.failure_mech" class="dc-input" placeholder="失效机理与根因" />
              <input v-model="d.control_measure" class="dc-input" placeholder="防错与探测规范" />
            </div>

            <div class="dc-route-bar">
              <span class="rt-lbl">归入画布位置：</span>
              <select v-model="d.routeChoice" class="route-sel">
                <option value="__NEW_NODE__">
                  + 自动在画布新建节点：「{{ d.suggested_node_title || '新模块单元' }}」
                </option>
                <option v-for="nd in canvasData.nodes" :key="nd.id" :value="`node:${nd.id}`">
                  已有模块节点：{{ nd.title }}
                </option>
                <option v-for="ed in canvasData.edges" :key="ed.id" :value="`edge:${ed.id}`">
                  已有配合接口：{{ ed.label }}
                </option>
              </select>

              <div class="dc-refs">
                <SoftRefChip v-for="(rf, rIdx) in d.linked_refs" :key="rIdx" :item="rf" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dlg-foot">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button
          type="primary"
          :disabled="drafts.length === 0"
          :loading="committing"
          @click="commitDraftsToBoard"
        >
          确认写入画板与台账 ({{ drafts.length }})
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { BoardCanvasData, FmeaPhoto, FmeaAiDraft } from '@/views/6_fmea/types'
import { fmeaApi } from '@/api/fmea'
import { useFmeaUpload } from '@/views/6_fmea/composables/useFmeaUpload'
import SoftRefChip from './SoftRefChip.vue'

interface EditableDraft extends FmeaAiDraft {
  routeChoice: string
}

const props = defineProps<{
  modelValue: boolean
  boardId: number | null
  canvasData: BoardCanvasData
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'committed'): void
}>()

const { uploading, uploadImageFile, extractImagesFromClipboard } = useFmeaUpload()
const rawText = ref('')
const pastedPhotos = ref<FmeaPhoto[]>([])
const parsing = ref(false)
const committing = ref(false)
const engineMode = ref('')
const drafts = ref<EditableDraft[]>([])

const engineModeLabel = computed(() => {
  if (engineMode.value === 'llm') return '在线大模型引擎'
  if (engineMode.value === 'json_bridge') return '外部大模型 JSON 直解'
  return 'SQM 工程语义引擎'
})

function fillSampleText() {
  rawText.value =
    '1. 关节模组连续高负载温升测试中，无框电机定子 PRT-205 引出线根部环氧胶锐边磨损绝缘皮；导致对壳体耐压击穿报警；对策要求增加氟橡胶护线套并执行 AC1500V 全检。\n' +
    '2. EOL总装工位涂脂过量（超 4.5g），高速运转时油脂甩入双圈磁编读头 PRT-115；导致零位多圈跳变；要求定量注脂机闭环称重 3.2±0.2g 并增设迷宫挡油环。'
}

async function copyExternalPrompt() {
  const nodeNames = props.canvasData.nodes.map((n) => `${n.id}:${n.title}`).join(', ') || '无'
  const prompt = `请作为资深 DFMEA/PFMEA 专家，将以下现场异常/图片拆解为 JSON 数组代码块输出，字段格式：
[{"fmea_type":"DFMEA","failure_mode":"20字内失效模式","failure_mech":"失效机理","failure_effect":"失效后果","control_measure":"防错与探测标准","risk_level":"HIGH","suggested_node_title":"建议模块短名","linked_refs":["零件图号或自由标签"]}]
当前画板已有模块节点：[${nodeNames}]
待分析素材：\n${rawText.value || '（请在此处粘贴文字或附带失效图片）'}`
  await navigator.clipboard.writeText(prompt)
  ElMessage.success('已复制专属提示词！发给任意多模态大模型后将返回的 JSON 粘回此处即可秒级入库')
}

async function onPasteImages(e: ClipboardEvent) {
  const files = extractImagesFromClipboard(e)
  if (!files.length) return
  e.preventDefault()
  for (const f of files) {
    const res = await uploadImageFile(f, 'fmea_photo', props.boardId)
    if (res) {
      pastedPhotos.value.push({
        id: `ph_${Date.now().toString(36)}`,
        attachment_id: res.attachment_id,
        url: res.url,
        tag: 'NG',
        caption: 'AI录入实拍'
      })
    }
  }
  ElMessage.success('已捕获剪贴板图片')
}

async function runAiParse() {
  if (!rawText.value.trim() && !pastedPhotos.value.length) {
    ElMessage.warning('请先粘贴异常描述文本或失效截图')
    return
  }
  parsing.value = true
  try {
    const res = await fmeaApi.aiParseDrafts({
      raw_text: rawText.value,
      board_id: props.boardId,
      photos: pastedPhotos.value
    })
    engineMode.value = res.engine_mode
    drafts.value = res.drafts.map((d) => {
      const matchedNode = d.suggested_target_id
        ? props.canvasData.nodes.find((n) => n.id === d.suggested_target_id)
        : null
      return {
        ...d,
        routeChoice: matchedNode ? `node:${matchedNode.id}` : '__NEW_NODE__'
      }
    })
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '拆解失败')
  } finally {
    parsing.value = false
  }
}

async function commitDraftsToBoard() {
  if (!props.boardId || !drafts.value.length) return
  committing.value = true
  try {
    let layoutMutated = false

    for (let i = 0; i < drafts.value.length; i++) {
      const d = drafts.value[i]
      let targetKind: 'node' | 'edge' | 'unassigned' = 'node'
      let targetId: string | null = null
      let targetSnap = ''

      if (d.routeChoice === '__NEW_NODE__') {
        const title = (d.suggested_node_title || d.failure_mode.slice(0, 8) || '新模块').trim()
        // 若同名节点刚被上一条草稿创建，直接复用
        let existNd = props.canvasData.nodes.find((n) => n.title === title)
        if (!existNd) {
          const idx = props.canvasData.nodes.length
          existNd = {
            id: `nd_${Date.now().toString(36)}_${i}`,
            title,
            sub: d.linked_refs.find((r) => r.code)?.code || '',
            x: 500 + (idx % 2) * 240,
            y: 60 + Math.floor(idx / 2) * 124
          }
          props.canvasData.nodes.push(existNd)
          layoutMutated = true
        }
        targetKind = 'node'
        targetId = existNd.id
        targetSnap = existNd.title
      } else if (d.routeChoice.startsWith('node:')) {
        targetKind = 'node'
        targetId = d.routeChoice.slice(5)
        targetSnap = props.canvasData.nodes.find((n) => n.id === targetId)?.title || ''
      } else if (d.routeChoice.startsWith('edge:')) {
        targetKind = 'edge'
        targetId = d.routeChoice.slice(5)
        targetSnap = props.canvasData.edges.find((ed) => ed.id === targetId)?.label || ''
      }

      await fmeaApi.createItem({
        board_id: props.boardId,
        target_kind: targetKind,
        target_id: targetId,
        target_title_snapshot: targetSnap,
        fmea_type: d.fmea_type,
        risk_level: d.risk_level,
        failure_mode: d.failure_mode,
        failure_mech: d.failure_mech,
        failure_effect: d.failure_effect,
        control_measure: d.control_measure,
        photos: i === 0 ? pastedPhotos.value : [],
        linked_refs: d.linked_refs
      })
    }

    if (layoutMutated) {
      await fmeaApi.updateBoard(props.boardId, { canvas_data: props.canvasData })
    }

    ElMessage.success(`已成功沉淀 ${drafts.value.length} 条 FMEA 机理卡至画板`)
    drafts.value = []
    rawText.value = ''
    pastedPhotos.value = []
    emit('committed')
    emit('update:modelValue', false)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '批量写入失败')
  } finally {
    committing.value = false
  }
}
</script>

<style scoped>
.ai-fmea-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-box {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sb-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.sb-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #1e293b;
}

.sb-title kbd {
  padding: 1px 5px;
  border-radius: 4px;
  background: #fff;
  border: 1px solid #cbd5e1;
  font-size: 11px;
}

.sb-tools {
  display: flex;
  gap: 8px;
}

.link-mini-btn {
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.link-mini-btn:hover {
  text-decoration: underline;
}

.raw-textarea {
  width: 100%;
  padding: 8px 10px;
  border-radius: 7px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  font-size: 12.5px;
  color: #0f172a;
  resize: vertical;
  outline: none;
  font-family: inherit;
}

.raw-textarea:focus {
  border-color: #2563eb;
}

.pasted-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ps-item {
  position: relative;
  width: 84px;
  height: 58px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
}

.ps-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ps-tag {
  position: absolute;
  left: 3px;
  top: 3px;
  font-size: 9.5px;
  padding: 0 4px;
  border-radius: 3px;
  background: rgba(220, 38, 38, 0.88);
  color: #fff;
}

.ps-rm {
  position: absolute;
  right: 3px;
  top: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: none;
  background: rgba(15, 23, 42, 0.7);
  color: #fff;
  cursor: pointer;
  line-height: 1;
}

.parse-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.parse-hint {
  font-size: 11.5px;
  color: #64748b;
}

.drafts-sec {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ds-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #0f172a;
}

.engine-badge {
  margin-left: 8px;
  padding: 2px 7px;
  border-radius: 10px;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 500;
}

.draft-list {
  max-height: 290px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.draft-card {
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.dc-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mini-sel {
  height: 28px;
  padding: 0 6px;
  border-radius: 5px;
  border: 1px solid #cbd5e1;
  font-size: 12px;
}

.dc-mode-input {
  flex: 1;
  height: 28px;
  padding: 0 8px;
  border-radius: 5px;
  border: 1px solid #cbd5e1;
  font-size: 12.5px;
  font-weight: 600;
}

.dc-del {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
}

.dc-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.dc-input {
  height: 28px;
  padding: 0 8px;
  border-radius: 5px;
  border: 1px solid #e2e8f0;
  font-size: 12px;
}

.dc-route-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.rt-lbl {
  font-size: 11.5px;
  color: #64748b;
}

.route-sel {
  height: 26px;
  padding: 0 8px;
  border-radius: 5px;
  border: 1px solid #93c5fd;
  background: #eff6ff;
  color: #1e40af;
  font-size: 11.5px;
}

.dc-refs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.dlg-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>

