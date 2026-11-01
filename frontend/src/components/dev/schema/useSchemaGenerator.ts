export interface ColumnMeta {
  name: string
  type: string
  is_nullable: boolean
  default: any
  is_primary: boolean
  comment: string
}

export type UIControlType =
  | 'input'
  | 'textarea'
  | 'input-number'
  | 'select'
  | 'date-picker'
  | 'switch'

export interface InferredField {
  prop: string
  label: string
  controlType: UIControlType
  dataType: string
  required: boolean
  defaultValue: any
  comment: string
}

/**
 * 将下划线命名转为 PascalCase (如 sqm_supplier -> SqmSupplier)
 */
export function toPascalCase(str: string): string {
  return str
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('')
}

/**
 * 依据数据库物理元数据智能推断前端控件类型与校验规则
 */
export function inferField(col: ColumnMeta): InferredField {
  const cleanLabel = col.comment
    ? col.comment.split(/[（(；;，,]/)[0].trim()
    : col.name

  const lowerType = (col.type || '').toLowerCase()
  const lowerName = col.name.toLowerCase()

  let controlType: UIControlType = 'input'
  let defaultValue: any = ''

  if (
    lowerType.includes('tinyint(1)') ||
    lowerName.startsWith('is_') ||
    lowerName.startsWith('has_')
  ) {
    controlType = 'switch'
    defaultValue = col.default === '1' || col.default === 1 || col.default === true
  } else if (
    lowerName.includes('status') ||
    lowerName.includes('type') ||
    lowerName.includes('rating') ||
    lowerName.includes('level') ||
    lowerName.includes('category')
  ) {
    controlType = 'select'
    defaultValue = col.default !== null && col.default !== undefined ? String(col.default) : ''
  } else if (lowerType.includes('date') || lowerType.includes('time')) {
    controlType = 'date-picker'
    defaultValue = ''
  } else if (
    lowerType.includes('int') ||
    lowerType.includes('decimal') ||
    lowerType.includes('float') ||
    lowerType.includes('double') ||
    lowerType.includes('numeric') ||
    lowerName.includes('score') ||
    lowerName.includes('price') ||
    lowerName.includes('count') ||
    lowerName.includes('weight')
  ) {
    controlType = 'input-number'
    defaultValue = col.default !== null && !isNaN(Number(col.default)) ? Number(col.default) : 0
  } else if (
    lowerType.includes('text') ||
    lowerName.includes('desc') ||
    lowerName.includes('remark') ||
    lowerName.includes('content')
  ) {
    controlType = 'textarea'
    defaultValue = ''
  }

  const required = !col.is_nullable && col.default === null && !col.is_primary

  return {
    prop: col.name,
    label: cleanLabel || col.name,
    controlType,
    dataType: col.type,
    required,
    defaultValue,
    comment: col.comment || cleanLabel
  }
}

/**
 * 生成 Element-Plus 数据展示表格代码
 */
export function generateTableCode(tableName: string, fields: InferredField[]): string {
  const columnsCode = fields
    .map(f => {
      if (f.controlType === 'switch') {
        return `    <el-table-column prop="${f.prop}" label="${f.label}" width="100" align="center">
      <template #default="{ row }">
        <el-tag :type="row.${f.prop} ? 'success' : 'info'" size="small">
          {{ row.${f.prop} ? '是' : '否' }}
        </el-tag>
      </template>
    </el-table-column>`
      }
      if (f.controlType === 'select') {
        return `    <el-table-column prop="${f.prop}" label="${f.label}" min-width="120" align="center">
      <template #default="{ row }">
        <el-tag size="small">{{ row.${f.prop} || '-' }}</el-tag>
      </template>
    </el-table-column>`
      }
      if (f.controlType === 'date-picker') {
        return `    <el-table-column prop="${f.prop}" label="${f.label}" width="160" sortable align="center" />`
      }
      if (f.controlType === 'input-number') {
        return `    <el-table-column prop="${f.prop}" label="${f.label}" width="120" sortable align="right" />`
      }
      return `    <el-table-column prop="${f.prop}" label="${f.label}" min-width="140" show-overflow-tooltip />`
    })
    .join('\n')

  return `<!-- ${tableName} 业务数据展示表格 -->
<el-table :data="tableData" v-loading="loading" stripe border style="width: 100%">
${columnsCode}
    <el-table-column label="操作" width="140" fixed="right" align="center">
      <template #default="{ row }">
        <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
        <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
      </template>
    </el-table-column>
</el-table>`
}

/**
 * 生成 Element-Plus 表单组件与校验规则代码
 */
export function generateFormCode(tableName: string, fields: InferredField[]): { template: string; script: string } {
  const formItems = fields
    .filter(f => f.prop !== 'id' && f.prop !== 'created_at' && f.prop !== 'updated_at')
    .map(f => {
      let controlTag = ''
      switch (f.controlType) {
        case 'textarea':
          controlTag = `<el-input v-model="formData.${f.prop}" type="textarea" :rows="3" placeholder="请输入${f.label}" maxlength="500" show-word-limit />`
          break
        case 'input-number':
          controlTag = `<el-input-number v-model="formData.${f.prop}" :step="1" controls-position="right" style="width: 100%" placeholder="请输入${f.label}" />`
          break
        case 'date-picker':
          controlTag = `<el-date-picker v-model="formData.${f.prop}" type="date" value-format="YYYY-MM-DD" placeholder="请选择${f.label}" style="width: 100%" />`
          break
        case 'select':
          controlTag = `<el-select v-model="formData.${f.prop}" placeholder="请选择${f.label}" clearable style="width: 100%">
          <el-option label="选项A" value="A" />
          <el-option label="选项B" value="B" />
        </el-select>`
          break
        case 'switch':
          controlTag = `<el-switch v-model="formData.${f.prop}" active-text="是" inactive-text="否" />`
          break
        default:
          controlTag = `<el-input v-model="formData.${f.prop}" placeholder="请输入${f.label}" clearable />`
      }

      return `    <el-form-item label="${f.label}" prop="${f.prop}">
      ${controlTag}
    </el-form-item>`
    })
    .join('\n')

  const initialFormObject = fields.reduce((acc, f) => {
    acc[f.prop] = f.defaultValue
    return acc
  }, {} as Record<string, any>)

  const rulesObject = fields
    .filter(f => f.required)
    .reduce((acc, f) => {
      acc[f.prop] = [
        {
          required: true,
          message: `${f.controlType === 'select' || f.controlType === 'date-picker' ? '请选择' : '请输入'}${f.label}`,
          trigger: f.controlType === 'select' || f.controlType === 'date-picker' ? 'change' : 'blur'
        }
      ]
      return acc
    }, {} as Record<string, any>)

  const template = `<!-- ${tableName} 增改业务表单 -->
<el-form
  ref="formRef"
  :model="formData"
  :rules="formRules"
  label-width="120px"
  label-position="right"
>
${formItems}
</el-form>`

  const script = `// 表单响应式数据与校验规则
const formData = reactive(${JSON.stringify(initialFormObject, null, 2)})

const formRules = ${JSON.stringify(rulesObject, null, 2)}`

  return { template, script }
}

/**
 * 生成 TypeScript 实体契约 Interface
 */
export function generateTypeScriptCode(tableName: string, fields: InferredField[]): string {
  const interfaceName = `${toPascalCase(tableName)}Item`
  const lines = fields.map(f => {
    let tsType = 'string'
    if (f.controlType === 'input-number') tsType = 'number'
    if (f.controlType === 'switch') tsType = 'boolean'
    const optionalMark = f.required ? '' : '?'
    return `  /** ${f.comment || f.label} */
  ${f.prop}${optionalMark}: ${tsType}`
  })

  return `/**
 * ${tableName} 数据实体契约
 */
export interface ${interfaceName} {
${lines.join('\n')}
}`
}

/**
 * 生成列表顶部单行搜索筛选栏代码
 */
export function generateFilterBarCode(fields: InferredField[]): string {
  const filterCandidates = fields
    .filter(f => f.prop !== 'id' && f.prop !== 'created_at' && f.prop !== 'updated_at')
    .slice(0, 3)

  const itemsCode = filterCandidates
    .map(f => {
      if (f.controlType === 'select') {
        return `    <el-select v-model="filterParams.${f.prop}" placeholder="${f.label}" clearable size="default" style="width: 160px">
      <el-option label="全部状态" value="" />
    </el-select>`
      }
      return `    <el-input v-model="filterParams.${f.prop}" placeholder="搜索${f.label}..." clearable size="default" style="width: 200px" />`
    })
    .join('\n')

  return `<!-- 顶部轻量搜索筛选栏 -->
<div class="search-filter-bar">
${itemsCode}
  <el-button type="primary" size="default" @click="handleSearch">查询</el-button>
  <el-button size="default" @click="handleResetFilter">重置</el-button>
</div>`
}

/**
 * 生成富文本质量规程 CTQ 规范表格 (HTML)
 */
export function generateCtqHtmlTable(fields: InferredField[]): string {
  const ths = fields.map(f => `      <th>${f.label}</th>`).join('\n')
  const tds = fields
    .map(f => {
      if (f.controlType === 'input-number') return `      <td style="text-align:right;">0.00</td>`
      if (f.controlType === 'switch') return `      <td style="text-align:center;">是</td>`
      return `      <td>示例${f.label}</td>`
    })
    .join('\n')

  return `<table class="sqm-ctq-spec-table" style="width: 100%; border-collapse: collapse; margin: 12px 0;" border="1">
  <thead>
    <tr style="background: #f8fafc;">
${ths}
    </tr>
  </thead>
  <tbody>
    <tr>
${tds}
    </tr>
  </tbody>
</table>`
}
