import mammoth from 'mammoth'
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  AlignmentType
} from 'docx'

/**
 * 将用户上传的 Word (.docx) 文件无损转换为 HTML
 */
export async function importWordToHtml(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer()
  const result = await mammoth.convertToHtml(
    { arrayBuffer },
    {
      styleMap: [
        "p[style-name='Heading 1'] => h1:fresh",
        "p[style-name='Heading 2'] => h2:fresh",
        "p[style-name='Heading 3'] => h3:fresh",
        "p[style-name='Quote'] => blockquote:fresh"
      ]
    }
  )
  return result.value
}

/**
 * 将编辑器内的 HTML 内容解析导出为规范的 Word (.docx) 文件并触发下载
 */
export async function exportHtmlToWord(title: string, htmlContent: string): Promise<void> {
  const parser = new DOMParser()
  const docDom = parser.parseFromString(htmlContent, 'text/html')
  const children = Array.from(docDom.body.children)

  const docChildren: (Paragraph | Table)[] = []

  // 1. 文档大标题
  docChildren.push(
    new Paragraph({
      text: title || 'SQM 质量规程文档',
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
      spacing: { after: 300, before: 100 }
    })
  )

  // 2. 遍历顶级 DOM 节点生成 Word 对应元素
  for (const el of children) {
    const tagName = el.tagName.toLowerCase()

    if (tagName === 'h1') {
      docChildren.push(
        new Paragraph({
          text: el.textContent?.trim() || '',
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 240, after: 120 }
        })
      )
    } else if (tagName === 'h2') {
      docChildren.push(
        new Paragraph({
          text: el.textContent?.trim() || '',
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 200, after: 100 }
        })
      )
    } else if (tagName === 'h3') {
      docChildren.push(
        new Paragraph({
          text: el.textContent?.trim() || '',
          heading: HeadingLevel.HEADING_3,
          spacing: { before: 160, after: 80 }
        })
      )
    } else if (tagName === 'table') {
      const rows = Array.from(el.querySelectorAll('tr'))
      const tableRows: TableRow[] = []

      for (let rIdx = 0; rIdx < rows.length; rIdx++) {
        const row = rows[rIdx]
        const cells = Array.from(row.querySelectorAll('th, td'))
        const isHeader = rIdx === 0 || row.querySelector('th') !== null

        const tableCells: TableCell[] = cells.map(c => {
          return new TableCell({
            children: [
              new Paragraph({
                children: [
                  new TextRun({
                    text: c.textContent?.trim() || '',
                    bold: isHeader,
                    color: isHeader ? '0f172a' : '334155'
                  })
                ]
              })
            ],
            shading: isHeader ? { fill: 'F1F5F9' } : undefined,
            borders: {
              top: { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
              bottom: { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
              left: { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' },
              right: { style: BorderStyle.SINGLE, size: 1, color: 'E2E8F0' }
            }
          })
        })

        if (tableCells.length > 0) {
          tableRows.push(new TableRow({ children: tableCells }))
        }
      }

      if (tableRows.length > 0) {
        docChildren.push(
          new Table({
            rows: tableRows,
            width: { size: 100, type: WidthType.PERCENTAGE }
          })
        )
        // 表格后补充留白
        docChildren.push(new Paragraph({ spacing: { after: 120 } }))
      }
    } else if (tagName === 'pre' || el.classList.contains('code-block-wrapper')) {
      const codeText = el.textContent || ''
      docChildren.push(
        new Paragraph({
          children: [
            new TextRun({
              text: codeText,
              font: 'Consolas',
              size: 20,
              color: '1E293B'
            })
          ],
          shading: { fill: 'F8FAFC' },
          spacing: { before: 100, after: 100 }
        })
      )
    } else if (tagName === 'ul' || tagName === 'ol') {
      const lis = Array.from(el.querySelectorAll('li'))
      for (const li of lis) {
        docChildren.push(
          new Paragraph({
            text: `• ${li.textContent?.trim() || ''}`,
            spacing: { before: 40, after: 40 }
          })
        )
      }
    } else if (tagName === 'blockquote') {
      docChildren.push(
        new Paragraph({
          children: [
            new TextRun({
              text: `“ ${el.textContent?.trim() || ''} ”`,
              italics: true,
              color: '0369A1'
            })
          ],
          shading: { fill: 'F0F9FF' },
          spacing: { before: 80, after: 80 }
        })
      )
    } else {
      // 普通段落
      const text = el.textContent?.trim()
      if (text) {
        docChildren.push(
          new Paragraph({
            text,
            spacing: { before: 60, after: 60 }
          })
        )
      }
    }
  }

  // 构建 docx 文档
  const doc = new Document({
    sections: [
      {
        properties: {},
        children: docChildren
      }
    ]
  })

  // 打包并触发下载
  const blob = await Packer.toBlob(doc)
  const downloadUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = downloadUrl
  const safeFilename = (title || '规程文档').replace(/[\\/:*?"<>|]/g, '_')
  a.download = `${safeFilename}.docx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(downloadUrl)
}
