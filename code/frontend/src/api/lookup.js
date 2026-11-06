// 单据明细只返回零件编号和颜色编号，这里补上名称和色值
import { api } from './index.js'

const cache = new Map() // `${part_num}|${color_id}` -> 库存行

export const keyOf = (i) => `${i.part_num}|${i.color_id}`

export function remember(rows) {
  for (const r of rows) cache.set(keyOf(r), { name: r.name ?? r.part_name, color_name: r.color_name, rgb: r.rgb })
}

// 按零件编号查库存目录；同一零件只查一次，最多 4 个并发
export async function enrich(items) {
  const parts = [...new Set(items.filter((i) => !cache.has(keyOf(i))).map((i) => i.part_num))]
  const queue = [...parts]
  const worker = async () => {
    while (queue.length) {
      const p = queue.shift()
      try {
        const r = await api.stock({ search: p, page_size: 100 })
        remember(r.items.filter((x) => x.part_num === p))
      } catch { /* 查不到时只显示编号 */ }
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, queue.length) }, worker))
  return items.map((i) => ({ ...i, ...(cache.get(keyOf(i)) || {}) }))
}

export function fmtTime(s) {
  if (!s) return ''
  return String(s).replace('T', ' ').slice(0, 16)
}
