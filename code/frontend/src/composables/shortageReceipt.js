// 按缺件生成入库草稿：只建草稿，不改库存，由用户在入库页核对后确认
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/index.js'

export function useShortageReceipt() {
  const router = useRouter()
  const creatingReceipt = ref(false)

  async function createFromShortage(items) {
    const lines = items.filter((i) => i.shortage > 0)
      .map((i) => ({ part_num: i.part_num, color_id: i.color_id, quantity: Number(i.shortage) }))
    if (!lines.length || creatingReceipt.value) return
    creatingReceipt.value = true
    try {
      const r = await api.createReceipt(lines)
      ElMessage.success(`已生成入库草稿 #${r.id}，请核对数量后确认入库`)
      router.push({ path: '/stock', query: { tab: 'receipts', receipt: r.id } })
    } catch (e) {
      ElMessage.error(e.status === 404 ? '部分缺件不在库存目录中，无法自动生成，请在入库页手动登记' : e.message)
    } finally {
      creatingReceipt.value = false
    }
  }

  return { creatingReceipt, createFromShortage }
}
