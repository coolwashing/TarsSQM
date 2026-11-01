// Exercise component task lifecycle without browser automation or model calls.
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import vm from 'node:vm'

const requireFrontend = createRequire(new URL('../frontend/package.json', import.meta.url))
const vue = requireFrontend('vue')
const compiler = requireFrontend('@vue/compiler-sfc')
const typescript = requireFrontend('typescript')
const source = await readFile(new URL('../frontend/src/views/4_kb/components/DocAiCopilot.vue', import.meta.url), 'utf8')
const descriptor = compiler.parse(source).descriptor
const compiled = compiler.compileScript(descriptor, { id: 'kb-ai-test' }).content
const commonJs = typescript.transpileModule(compiled, { compilerOptions: { module: typescript.ModuleKind.CommonJS, target: typescript.ScriptTarget.ES2022 } }).outputText

async function panel({ axios, storage = new Map(), overrides = {} }) {
  const clipboard = [], events = [], cleanup = []
  const exports = {}
  const scope = vue.effectScope()
  const context = {
    exports, console, setTimeout, clearTimeout,
    navigator: { clipboard: { async writeText(text) { clipboard.push(text) } } },
    localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) },
    require(name) {
      if (name === 'vue') return { ...vue, onBeforeUnmount: callback => cleanup.push(callback) }
      if (name === 'axios') return { __esModule: true, default: axios }
      if (name === 'element-plus') return { ElMessage: { success() {}, info() {} }, ElMessageBox: { confirm: async () => {} } }
      throw new Error(`Unexpected import ${name}`)
    }
  }
  vm.runInNewContext(commonJs, context)
  const props = vue.reactive({ modelValue: false, docId: 7, docTitle: 'Synthetic document', docContent: '<p>Original</p>',
    folderId: 3, editable: true, beacons: [], initialTarget: {}, ...overrides })
  const state = scope.run(() => exports.default.setup(props, { expose() {}, emit: (...event) => events.push(event) }))
  props.modelValue = true
  await vue.nextTick(); await new Promise(resolve => setImmediate(resolve))
  return { state, props, storage, clipboard, events, stop() { cleanup.forEach(callback => callback()); scope.stop() } }
}

const task = { id: 'synthetic-task', status: 'waiting', provider: 'ide', operation: 'edit', message: 'waiting', prompt: 'Improve this',
  ide_prompt: 'Synthetic task instruction', references: [], before_html: '<p>Original</p>', source_html: '<p>Original</p>', result_html: '', folder_id: null }

test('AI panel creates, copies, receives and explicitly applies a task', async () => {
  const calls = []
  const view = await panel({ axios: {
    async get(url) { return { data: url.includes('/tasks/') ? { ...task, status: 'ready', result_html: '<p>Candidate</p>' } : [] } },
    async post(url, body) { calls.push({ url, body }); return { data: url.endsWith('/apply') ? { id: 7 } : { ...task } } }
  } })
  try {
    view.state.prompt.value = 'Improve this'
    await view.state.createTask()
    assert.equal(view.clipboard[0], task.ide_prompt)
    assert.equal(calls.length, 1)
    assert.equal(calls[0].body.folder_id, null)
    assert.equal(view.storage.get('sqm_kb_ai_7_3'), task.id)
    await view.state.pollTask()
    assert.equal(view.state.task.value.status, 'ready')
    assert.equal(calls.length, 1, 'receiving a result must not apply it')
    await view.state.applyResult('append')
    assert.equal(calls[1].body.mode, 'append')
    assert.equal(view.state.task.value.status, 'applied')
    assert.ok(view.events.some(event => event[0] === 'refresh-doc'))
  } finally { view.stop() }
})

test('AI panel restores saved tasks and preserves newer local drafts', async () => {
  let posted = false
  const view = await panel({ storage: new Map([['sqm_kb_ai_7_3', task.id]]), axios: {
    async get(url) { return { data: url.includes('/tasks/') ? { ...task, status: 'ready', result_html: '<p>Candidate</p>' } : [] } },
    async post() { posted = true; return { data: {} } }
  } })
  try {
    assert.equal(view.state.task.value.id, task.id)
    view.props.docContent = '<p>Newer local draft</p>'
    await view.state.applyResult('replace')
    assert.equal(posted, false)
    assert.match(view.state.errorMessage.value, /已发生变化/)
  } finally { view.stop() }
})

test('temporary connection errors do not forget the pending task', async () => {
  let posted = false
  const view = await panel({ storage: new Map([['sqm_kb_ai_7_3', task.id]]), axios: {
    async get() { throw new Error('Synthetic offline condition') },
    async post() { posted = true; return { data: task } }
  } })
  try {
    assert.equal(view.storage.get('sqm_kb_ai_7_3'), task.id)
    assert.equal(view.state.restoreBlocked.value, true)
    view.state.prompt.value = 'Another task'
    await view.state.createTask()
    assert.equal(posted, false)
  } finally { view.stop() }
})
