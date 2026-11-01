// Local integration test: synthetic fixtures only; all created records are cleaned up.
import test from 'node:test'
import assert from 'node:assert/strict'
import { writeFile, stat } from 'node:fs/promises'
import path from 'node:path'

const base = 'http://127.0.0.1:8010/api/kb'
async function api(endpoint, method = 'GET', body, status = 200) {
  const response = await fetch(base + endpoint, {
    method, headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(12000)
  })
  const result = await response.json()
  assert.equal(response.status, status, `${method} ${endpoint}: ${JSON.stringify(result)}`)
  return result
}
function crc32(buffer) {
  let crc = 0xffffffff
  for (const byte of buffer) {
    crc ^= byte
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0)
  }
  return (crc ^ 0xffffffff) >>> 0
}
function workbook(marker) {
  const files = {
    '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
    '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
    'xl/workbook.xml': '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="SyntheticInspection" sheetId="1" r:id="rId1"/></sheets></workbook>',
    'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
    'xl/worksheets/sheet1.xml': `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Inspection temperature</t></is></c><c r="B1" t="inlineStr"><is><t>${marker}</t></is></c></row></sheetData></worksheet>`
  }
  const parts = [], central = []
  let offset = 0
  for (const [name, value] of Object.entries(files)) {
    const filename = Buffer.from(name), data = Buffer.from(value), checksum = crc32(data)
    const header = Buffer.alloc(30)
    header.writeUInt32LE(0x04034b50); header.writeUInt16LE(20, 4)
    header.writeUInt32LE(checksum, 14); header.writeUInt32LE(data.length, 18); header.writeUInt32LE(data.length, 22); header.writeUInt16LE(filename.length, 26)
    const directory = Buffer.alloc(46)
    directory.writeUInt32LE(0x02014b50); directory.writeUInt16LE(20, 4); directory.writeUInt16LE(20, 6)
    directory.writeUInt32LE(checksum, 16); directory.writeUInt32LE(data.length, 20); directory.writeUInt32LE(data.length, 24); directory.writeUInt16LE(filename.length, 28); directory.writeUInt32LE(offset, 42)
    parts.push(header, filename, data); central.push(directory, filename)
    offset += header.length + filename.length + data.length
  }
  const directory = Buffer.concat(central), end = Buffer.alloc(22)
  end.writeUInt32LE(0x06054b50); end.writeUInt16LE(Object.keys(files).length, 8); end.writeUInt16LE(Object.keys(files).length, 10)
  end.writeUInt32LE(directory.length, 12); end.writeUInt32LE(offset, 16)
  return Buffer.concat([...parts, directory, end])
}
function pdf(marker) {
  const stream = `BT /F1 12 Tf 60 700 Td (${marker}) Tj ET`
  const objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`]
  let content = '%PDF-1.4\n'
  const offsets = [0]
  for (const [index, object] of objects.entries()) { offsets.push(Buffer.byteLength(content)); content += `${index + 1} 0 obj\n${object}\nendobj\n` }
  const xref = Buffer.byteLength(content)
  content += `xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(n => String(n).padStart(10, '0') + ' 00000 n \n').join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return Buffer.from(content)
}

test('attachments, grounded retrieval and IDE round trip without pasting', async t => {
  const marker = `KB_SYNTHETIC_${Date.now()}`
  const ids = [], tasks = [], attachmentIds = [], fileIds = []
  const create = async (endpoint, body, expected = 201) => {
    const result = await api(endpoint, 'POST', body, expected); ids.push(result.id); return result
  }
  const upload = async (name, bytes, parentId) => {
    const form = new FormData(); form.append('file', new Blob([bytes]), name); form.append('parent_id', String(parentId))
    const response = await fetch(`${base}/files`, { method: 'POST', body: form, signal: AbortSignal.timeout(12000) })
    const value = await response.json(); assert.equal(response.status, 201, JSON.stringify(value))
    ids.push(value.id); fileIds.push(value.id); attachmentIds.push(value.attachment_id); return value
  }
  const makeTask = async payload => {
    const task = await api('/ai/tasks', 'POST', { provider: 'ide', ...payload }, 201); tasks.push(task.id); return task
  }
  const returnResult = async (task, content) => {
    const relative = path.relative(process.cwd(), task.result_path)
    assert.ok(relative && !relative.startsWith('..') && !path.isAbsolute(relative), 'test writes must stay in the workspace')
    await writeFile(task.result_path, JSON.stringify({ task_id: task.id, content_html: content }), 'utf8')
    return api(`/ai/tasks/${task.id}`)
  }
  try {
    const root = await create('/explorer/folder', { name: `__TEST_${marker}`, parent_id: null }, 200)
    const nested = await create('/explorer/folder', { name: 'Synthetic child', parent_id: root.id }, 200)
    const bytes = workbook(marker)
    const spreadsheet = await upload('synthetic-inspection.xlsx', bytes, root.id)
    assert.equal(spreadsheet.index_status, 'indexed', spreadsheet.index_message)
    assert.deepEqual(Buffer.from(await (await fetch(`http://127.0.0.1:8010${spreadsheet.file_url}`)).arrayBuffer()), bytes)
    const hits = await api(`/search?q=${marker}`)
    assert.ok(hits.some(hit => hit.id === spreadsheet.id && hit.location.includes('SyntheticInspection') && hit.snippet.includes(marker)))
    const retrieval = await api(`/retrieve?q=${marker}&folder_id=${root.id}`)
    assert.equal(retrieval.method, 'keyword'); assert.ok(retrieval.references.some(hit => hit.id === spreadsheet.id))
    assert.equal((await api(`/retrieve?q=${marker}&folder_id=${nested.id}`)).references.length, 0)
    t.diagnostic('PASS: original Excel download, cell extraction, source locations and scoped retrieval')

    const copied = await create(`/files/${spreadsheet.id}/copy`, { parent_id: nested.id })
    fileIds.push(copied.id); attachmentIds.push(copied.attachment_id)
    assert.notEqual(copied.attachment_id, spreadsheet.attachment_id)
    assert.deepEqual(Buffer.from(await (await fetch(`http://127.0.0.1:8010${copied.file_url}`)).arrayBuffer()), bytes)
    await api('/explorer/move', 'PUT', { id: copied.id, target_folder_id: root.id })
    const reference = await create('/explorer/shortcut', { parent_id: nested.id, target_doc_id: copied.id }, 200)
    const favorite = await api(`/explorer/favorite/${copied.id}`, 'PUT')
    assert.equal(favorite.is_favorite, true)
    assert.equal((await api('/explorer/favorites')).find(item => item.id === copied.id).type, 'file')
    assert.ok((await api(`/explorer/items?folder_id=${nested.id}`)).find(item => item.id === reference.id).file_url)
    const pdfBytes = pdf(`${marker}_PDF`)
    const pdfFile = await upload('synthetic.pdf', pdfBytes, root.id)
    assert.deepEqual(Buffer.from(await (await fetch(`http://127.0.0.1:8010${pdfFile.file_url}`)).arrayBuffer()), pdfBytes)
    if (pdfFile.index_status === 'indexed') {
      assert.ok((await api(`/search?q=${marker}_PDF`)).some(hit => hit.id === pdfFile.id && hit.location.includes('1')))
      t.diagnostic('PASS: PDF extraction and page citations')
    } else {
      assert.equal(pdfFile.index_status, 'failed'); assert.match(pdfFile.index_message, /依赖/)
      t.diagnostic('LIMITATION: PDF original storage/download passed; pypdf installation is required for text extraction')
    }
    const unknown = await upload('synthetic.bin', Buffer.from('synthetic stored original'), root.id)
    assert.equal(unknown.index_status, 'unsupported')
    t.diagnostic('PASS: independent copies, moving, shortcut downloads, favorites and unsupported-format storage')

    const document = await create('/docs', { title: `${marker} online`, parent_id: root.id })
    const initial = '<h2>Synthetic original</h2><p>Original baseline.</p>'
    await api(`/docs/${document.id}`, 'PUT', { content_html: initial })
    const ask = await makeTask({ operation: 'ask', prompt: marker, folder_id: root.id })
    assert.ok(ask.references.some(item => item.id === spreadsheet.id))
    assert.ok(ask.ide_prompt.includes(ask.result_path))
    assert.equal((await api(`/ai/tasks/${ask.id}`)).status, 'waiting')
    const returned = await returnResult(ask, '<p>Synthetic answer from cited attachment.</p>')
    assert.equal(returned.status, 'ready')
    const saved = await create(`/ai/tasks/${ask.id}/apply`, { mode: 'new', parent_id: root.id, title: `${marker} answer` }, 200)
    assert.ok((await api(`/docs/${saved.id}`)).content_text.includes('Synthetic answer'))
    t.diagnostic('PASS: IDE task file round trip, polling, references and saving an answer as a document')

    const edit = await makeTask({ operation: 'edit', doc_id: document.id, prompt: 'Add a synthetic paragraph', source_html: initial })
    await returnResult(edit, '<p>Synthetic appended content.</p>')
    assert.equal((await api(`/docs/${document.id}`)).content_html, initial)
    await api(`/ai/tasks/${edit.id}/apply`, 'POST', { mode: 'append' })
    const appended = (await api(`/docs/${document.id}`)).content_html
    assert.equal(appended, initial + '<p>Synthetic appended content.</p>')
    await api(`/ai/tasks/${edit.id}/apply`, 'POST', { mode: 'append' })
    assert.equal((await api(`/docs/${document.id}`)).content_html, appended)
    const replacement = await makeTask({ operation: 'edit', doc_id: document.id, prompt: 'Replace synthetic document' })
    await returnResult(replacement, '<h2>Synthetic replacement</h2>')
    await api(`/ai/tasks/${replacement.id}/apply`, 'POST', { mode: 'replace' })
    assert.equal((await api(`/docs/${document.id}`)).content_html, '<h2>Synthetic replacement</h2>')
    const conflict = await makeTask({ operation: 'edit', doc_id: document.id, prompt: 'Synthetic pending edit' })
    await returnResult(conflict, '<p>Candidate result.</p>')
    await api(`/docs/${document.id}`, 'PUT', { content_html: '<p>Newer manual content.</p>' })
    await api(`/ai/tasks/${conflict.id}/apply`, 'POST', { mode: 'replace' }, 409)
    assert.equal((await api(`/docs/${document.id}`)).content_html, '<p>Newer manual content.</p>')
    t.diagnostic('PASS: confirmation-only writes, append, replacement, idempotency and normal edit conflicts')
  } finally {
    for (const taskId of tasks) {
      const response = await fetch(`${base}/ai/tasks/${taskId}`, { method: 'DELETE' }); assert.equal(response.status, 200)
    }
    for (const id of ids.reverse()) {
      const response = await fetch(`${base}/docs/${id}`, { method: 'DELETE' })
      assert.ok(response.status === 200 || response.status === 404, `cleanup document ${id}`)
    }
    for (const id of attachmentIds) assert.equal((await fetch(`http://127.0.0.1:8010/api/storage/file/${id}`)).status, 404)
    for (const id of fileIds) await assert.rejects(stat(path.join(process.cwd(), 'storage/kb-index', `${id}.json`)), { code: 'ENOENT' })
    t.diagnostic('PASS: all synthetic documents, attachment metadata, indexes and tasks removed')
  }
})
