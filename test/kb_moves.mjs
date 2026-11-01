// Run against the local backend: node --test test/kb_moves.mjs
// All writes are limited to clearly named temporary records, removed in finally.
import test from 'node:test'
import assert from 'node:assert/strict'

const baseUrl = 'http://127.0.0.1:8010/api/kb'

async function request(path, method = 'GET', body, expectedStatus = 200) {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10000)
  })
  const result = await response.json()
  assert.equal(response.status, expectedStatus, `${method} ${path}: ${JSON.stringify(result)}`)
  return result
}

function findNode(nodes, id) {
  for (const node of nodes) {
    if (node.id === id) return node
    const child = findNode(node.children || [], id)
    if (child) return child
  }
}

test('knowledge-base hierarchy, sibling order and document references', async t => {
  const createdIds = []
  const marker = `__TEST_KB_MOVE_${Date.now()}_`
  const create = async (type, name, parentId, extra = {}) => {
    const item = await request(`/explorer/${type}`, 'POST', {
      name: `${marker}${name}`, parent_id: parentId, ...extra
    })
    createdIds.push(item.id)
    return item.id
  }
  const move = payload => request('/explorer/move', 'PUT', payload)
  const detail = id => request(`/docs/${id}`)
  const assertOrder = async (parentId, expectedIds) => {
    const tree = await request('/tree')
    const treeIds = findNode(tree, parentId).children.map(node => node.id)
    const items = await request(`/explorer/items?folder_id=${parentId}`)
    assert.deepEqual(treeIds, expectedIds)
    assert.deepEqual(items.map(item => item.id), expectedIds)
  }

  try {
    const root = await create('folder', 'ROOT', null)
    const a = await create('folder', 'A', root)
    const b = await create('folder', 'B', root)
    const moving = await create('folder', 'MOVING', a)
    const child = await create('folder', 'CHILD', moving)
    const doc = await create('doc', 'DOCUMENT', root)
    const shortcut = await create('shortcut', 'REFERENCE', root, { target_doc_id: doc })
    const originalDoc = await detail(doc)
    const originalShortcut = await detail(shortcut)

    await move({ id: moving, reference_id: b, placement: 'before' })
    assert.equal((await detail(moving)).parent_id, root)
    await assertOrder(root, [a, moving, b, doc, shortcut])
    await move({ id: moving, reference_id: b, placement: 'after' })
    await assertOrder(root, [a, b, moving, doc, shortcut])
    // Repeated reloads must retain the same order despite originally tied weights.
    await assertOrder(root, [a, b, moving, doc, shortcut])
    t.diagnostic('PASS: cross-level promotion and persistent before/after ordering')

    await move({ id: moving, target_folder_id: a })
    assert.equal((await detail(child)).parent_id, moving)
    const path = await request(`/explorer/path?folder_id=${child}`)
    assert.deepEqual(path.slice(-4).map(crumb => crumb.id), [root, a, moving, child])
    await move({ id: moving, target_folder_id: null })
    assert.equal((await detail(moving)).parent_id, null)
    assert.ok((await request('/tree')).some(node => node.id === moving))
    await move({ id: moving, target_folder_id: root })
    t.diagnostic('PASS: moving into folders and to root preserves descendants and paths')

    await move({ id: doc, reference_id: a, placement: 'before' })
    await assertOrder(root, [doc, a, b, shortcut, moving])
    await move({ id: doc, target_folder_id: b })
    await move({ id: shortcut, target_folder_id: a })
    const movedDoc = await detail(doc)
    const movedShortcut = await detail(shortcut)
    for (const key of ['id', 'content_html', 'content_text', 'biz_type', 'biz_id']) {
      assert.equal(movedDoc[key], originalDoc[key])
      assert.equal(movedShortcut[key], originalShortcut[key])
    }
    const shortcutItems = await request(`/explorer/items?folder_id=${a}`)
    assert.equal(shortcutItems.find(item => item.id === shortcut).target_id, doc)
    t.diagnostic('PASS: document contents, IDs and shortcut targets survive moves')

    await request('/explorer/move', 'PUT', { id: moving, target_folder_id: moving }, 400)
    await request('/explorer/move', 'PUT', { id: moving, target_folder_id: child }, 400)
    await request('/explorer/move', 'PUT', { id: moving, reference_id: child, placement: 'before' }, 400)
    await request('/explorer/move', 'PUT', { id: moving, target_folder_id: doc }, 400)
    await request('/explorer/move', 'PUT', { id: moving, reference_id: moving, placement: 'after' }, 400)
    await request('/explorer/move', 'PUT', { id: moving, placement: 'before' }, 400)
    await request('/explorer/move', 'PUT', { id: moving, reference_id: -1, placement: 'after' }, 404)
    assert.equal((await detail(moving)).parent_id, root)
    assert.equal((await detail(child)).parent_id, moving)
    t.diagnostic('PASS: invalid destinations leave hierarchy unchanged')

    await request(`/docs/${moving}/move`, 'POST', { target_parent_id: a })
    assert.equal((await detail(moving)).parent_id, a)
    t.diagnostic('PASS: existing move endpoint remains compatible')
  } finally {
    const cleanupErrors = []
    for (const id of createdIds.reverse()) {
      try {
        const response = await fetch(`${baseUrl}/docs/${id}`, {
          method: 'DELETE', signal: AbortSignal.timeout(10000)
        })
        assert.ok(response.status === 200 || response.status === 404, `cleanup ${id}: ${response.status}`)
      } catch (error) {
        cleanupErrors.push(error)
      }
    }
    if (cleanupErrors.length) throw new AggregateError(cleanupErrors, 'Temporary record cleanup failed')
    const tree = await request('/tree')
    for (const id of createdIds) assert.equal(findNode(tree, id), undefined)
    t.diagnostic('PASS: all temporary test records removed')
  }
})
