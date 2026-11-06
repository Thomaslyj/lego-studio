<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/index.js'
import { enrich, fmtTime, keyOf, remember } from '../api/lookup.js'
import ColorChip from '../components/ColorChip.vue'
import StatusTag from '../components/StatusTag.vue'

const route = useRoute()
const router = useRouter()
const tab = ref(route.query.tab === 'receipts' ? 'receipts' : 'stock')
function switchTab(t) {
  tab.value = t
  router.replace({ query: t === 'stock' ? {} : { tab: t } })
}

/* ---------- 零件库存 ---------- */
const STOCK_SIZE = 20
const stockSearch = ref('')
const stockPage = ref(1)
const stock = ref({ total: 0, items: [] })
const stockLoading = ref(false)
const stockError = ref('')
async function loadStock() {
  stockLoading.value = true
  stockError.value = ''
  try {
    stock.value = await api.stock({ search: stockSearch.value.trim(), page: stockPage.value, page_size: STOCK_SIZE })
    remember(stock.value.items)
  } catch (e) { stockError.value = e.message } finally { stockLoading.value = false }
}
function searchStock() { stockPage.value = 1; loadStock() }

/* ---------- 入库单列表 ---------- */
const receipts = ref([])
const rLoading = ref(false)
const rError = ref('')
const rStatus = ref('all')
const rPage = ref(1)
const R_SIZE = 15
async function loadReceipts() {
  rLoading.value = true
  rError.value = ''
  try { receipts.value = await api.receipts() } catch (e) { rError.value = e.message } finally { rLoading.value = false }
}
const rFiltered = computed(() => (rStatus.value === 'all' ? receipts.value : receipts.value.filter((r) => r.status === rStatus.value)))
const rRows = computed(() => rFiltered.value.slice((rPage.value - 1) * R_SIZE, rPage.value * R_SIZE))
const rCounts = computed(() => ({
  all: receipts.value.length,
  draft: receipts.value.filter((r) => r.status === 'draft').length,
  posted: receipts.value.filter((r) => r.status === 'posted').length,
}))

/* ---------- 入库单编辑抽屉 ---------- */
const drawer = ref(false)
const editing = ref(null) // { id, status } ；id 为空表示新建
const lines = ref([])
const savedSnapshot = ref('[]')
const dLoading = ref(false)
const busy = ref('') // 'save' | 'confirm' | 'delete'
const readonly = computed(() => editing.value?.status === 'posted')
const snapshot = () => JSON.stringify(lines.value.map((l) => [l.part_num, l.color_id, l.quantity]))
const dirty = computed(() => snapshot() !== savedSnapshot.value)
const totalQty = computed(() => lines.value.reduce((s, l) => s + (l.quantity || 0), 0))
const invalid = computed(() => lines.value.some((l) => !Number.isInteger(l.quantity) || l.quantity < 1))

function openNew(prefill) {
  editing.value = { id: null, status: 'draft' }
  lines.value = prefill ? [{ ...prefill, quantity: 1 }] : []
  savedSnapshot.value = '[]'
  drawer.value = true
}

async function openReceipt(id) {
  drawer.value = true
  dLoading.value = true
  editing.value = { id, status: 'draft' }
  lines.value = []
  try {
    const r = await api.receipt(id)
    editing.value = { id: r.receipt.id, status: r.receipt.status, created_at: r.receipt.created_at }
    lines.value = (await enrich(r.items)).map((i) => ({ ...i, quantity: Number(i.quantity) }))
    savedSnapshot.value = snapshot()
  } catch (e) {
    ElMessage.error(e.message)
    drawer.value = false
  } finally {
    dLoading.value = false
  }
}

async function beforeClose(done) {
  if (!readonly.value && dirty.value && !busy.value) {
    try {
      await ElMessageBox.confirm('入库单有未保存的修改，关闭后修改将丢失。', '放弃修改？', {
        confirmButtonText: '放弃修改', cancelButtonText: '继续编辑', type: 'warning',
      })
    } catch { return }
  }
  done()
}
watch(drawer, (open) => {
  if (!open && route.query.receipt) router.replace({ query: { tab: 'receipts' } })
})

// 选择零件与颜色：远程搜索库存目录
const pickKey = ref('')
const pickQty = ref(1)
const options = ref([])
const optLoading = ref(false)
async function searchParts(text) {
  if (!text.trim()) { options.value = []; return }
  optLoading.value = true
  try {
    const r = await api.stock({ search: text.trim(), page_size: 50 })
    remember(r.items)
    options.value = r.items
  } catch { options.value = [] } finally { optLoading.value = false }
}
function addLine(row = options.value.find((o) => keyOf(o) === pickKey.value), qty = pickQty.value) {
  if (!row) return
  const exist = lines.value.find((l) => keyOf(l) === keyOf(row))
  if (exist) {
    exist.quantity += qty
    ElMessage.info('该零件颜色已在单据中，数量已合并')
  } else {
    lines.value.push({ part_num: row.part_num, color_id: row.color_id, name: row.name, color_name: row.color_name, rgb: row.rgb, quantity: qty })
  }
  pickKey.value = ''
  pickQty.value = 1
}

async function save() {
  if (busy.value || invalid.value || !lines.value.length) return false
  busy.value = 'save'
  const items = lines.value.map((l) => ({ part_num: l.part_num, color_id: l.color_id, quantity: l.quantity }))
  try {
    if (editing.value.id) {
      await api.updateReceipt(editing.value.id, items)
      ElMessage.success(`已保存入库草稿 #${editing.value.id}`)
    } else {
      const r = await api.createReceipt(items)
      editing.value = { id: r.id, status: 'draft' }
      ElMessage.success(`已创建入库草稿 #${r.id}`)
    }
    savedSnapshot.value = snapshot()
    loadReceipts()
    return true
  } catch (e) {
    ElMessage.error(e.status === 404 ? '有零件颜色组合不在库存目录中，请检查明细' : e.message)
    return false
  } finally {
    busy.value = ''
  }
}

async function confirmReceipt(id = editing.value?.id) {
  if (!id || busy.value) return
  busy.value = 'confirm'
  try {
    await ElMessageBox.confirm(`确认入库单 #${id}？库存将按明细增加，确认后单据只读。`, '确认入库', {
      confirmButtonText: '确认入库', cancelButtonText: '取消', type: 'warning',
    })
  } catch { busy.value = ''; return }
  try {
    await api.confirmReceipt(id)
    ElMessage.success(`入库单 #${id} 已入库，库存已更新`)
    if (editing.value?.id === id) editing.value = { ...editing.value, status: 'posted' }
    loadStock()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    busy.value = ''
    loadReceipts()
  }
}

async function removeReceipt(id) {
  try {
    await ElMessageBox.confirm(`删除入库草稿 #${id} 及其全部明细？`, '删除草稿', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  busy.value = 'delete'
  try {
    await api.deleteReceipt(id)
    ElMessage.success(`已删除入库草稿 #${id}`)
    if (editing.value?.id === id) { savedSnapshot.value = snapshot(); drawer.value = false }
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    busy.value = ''
    loadReceipts()
  }
}

onMounted(() => {
  loadStock()
  loadReceipts()
  if (route.query.receipt) openReceipt(Number(route.query.receipt))
})
watch(() => route.query.receipt, (v) => { if (v) { tab.value = 'receipts'; openReceipt(Number(v)) } })
const R_TABS = [['all', '全部'], ['draft', '草稿'], ['posted', '已入库']]
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>库存与入库</h1>
        <p class="muted">库存只随确认入库和确认领料变化；补货先登记草稿，核对后再确认。</p>
      </div>
      <button class="brick-btn" @click="openNew()">新建入库单</button>
    </div>

    <div class="seg tabs" role="tablist" aria-label="库存与入库">
      <button type="button" role="tab" :aria-selected="tab === 'stock'" :class="{ on: tab === 'stock' }" @click="switchTab('stock')">零件库存</button>
      <button type="button" role="tab" :aria-selected="tab === 'receipts'" :class="{ on: tab === 'receipts' }" @click="switchTab('receipts')">
        入库单 <span class="tile" :class="rCounts.draft ? 'yellow' : ''">{{ rCounts.draft }}</span>
      </button>
    </div>

    <!-- 零件库存 -->
    <section v-show="tab === 'stock'" class="panel box">
      <form class="toolbar" @submit.prevent="searchStock">
        <el-input v-model="stockSearch" placeholder="按零件编号或名称搜索" clearable class="grow" @clear="searchStock" />
        <button type="submit" class="brick-btn small">搜索</button>
        <span class="muted">共 <b class="num">{{ stock.total }}</b> 条库存记录</span>
      </form>
      <div v-if="stockError" class="inline-error">
        <span>{{ stockError }}</span>
        <button class="brick-btn white small no-studs" @click="loadStock">重试</button>
      </div>
      <el-table v-else v-loading="stockLoading" :data="stock.items" :empty-text="stockSearch ? '没有匹配的零件，换个编号或名称试试' : '暂无库存记录'">
        <el-table-column label="零件编号" width="150">
          <template #default="{ row }"><span class="num">{{ row.part_num }}</span></template>
        </el-table-column>
        <el-table-column label="名称" prop="name" min-width="260" />
        <el-table-column label="颜色" min-width="170">
          <template #default="{ row }"><ColorChip :rgb="row.rgb" :name="row.color_name" /></template>
        </el-table-column>
        <el-table-column label="当前库存" width="110" align="right">
          <template #default="{ row }">
            <span class="num" :class="{ shortage: row.quantity === 0 }">{{ row.quantity }}</span>
          </template>
        </el-table-column>
        <el-table-column label="" width="120" align="right">
          <template #default="{ row }">
            <button class="brick-btn white small no-studs" @click="openNew(row)">登记入库</button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="stock.total > STOCK_SIZE" class="pager">
        <el-pagination
          v-model:current-page="stockPage" background layout="prev, pager, next, jumper"
          :total="stock.total" :page-size="STOCK_SIZE" @current-change="loadStock"
        />
      </div>
    </section>

    <!-- 入库单 -->
    <section v-show="tab === 'receipts'" class="panel box">
      <div class="toolbar">
        <div class="seg small-seg">
          <button
            v-for="[k, label] in R_TABS" :key="k" type="button" :class="{ on: rStatus === k }"
            @click="rStatus = k; rPage = 1"
          >{{ label }} <span class="tile">{{ rCounts[k] }}</span></button>
        </div>
        <button class="brick-btn white small no-studs" :disabled="rLoading" @click="loadReceipts">刷新</button>
      </div>
      <div v-if="rError" class="inline-error">
        <span>{{ rError }}</span>
        <button class="brick-btn white small no-studs" @click="loadReceipts">重试</button>
      </div>
      <el-table v-else v-loading="rLoading" :data="rRows" :empty-text="rStatus === 'all' ? '还没有入库单，点“新建入库单”登记补货' : '该状态下没有入库单'">
        <el-table-column label="入库单" width="110">
          <template #default="{ row }"><span class="tile dark num">#{{ row.id }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="160">
          <template #default="{ row }"><span class="num muted">{{ fmtTime(row.created_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="290" align="right">
          <template #default="{ row }">
            <div class="ops">
              <template v-if="row.status === 'draft'">
                <button class="brick-btn white small no-studs" @click="openReceipt(row.id)">编辑</button>
                <button class="brick-btn small no-studs" :disabled="!!busy" @click="confirmReceipt(row.id)">确认入库</button>
                <button class="brick-btn small no-studs danger" :disabled="!!busy" @click="removeReceipt(row.id)">删除</button>
              </template>
              <button v-else class="brick-btn white small no-studs" @click="openReceipt(row.id)">查看明细</button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="rFiltered.length > R_SIZE" class="pager">
        <el-pagination v-model:current-page="rPage" background layout="prev, pager, next" :total="rFiltered.length" :page-size="R_SIZE" />
      </div>
    </section>

    <!-- 编辑 / 查看 -->
    <el-drawer v-model="drawer" size="min(720px, 100%)" :before-close="beforeClose" destroy-on-close>
      <template #header>
        <div class="dhead">
          <h2>{{ editing?.id ? `入库单 #${editing.id}` : '新建入库单' }}</h2>
          <StatusTag v-if="editing" :status="editing.status" />
        </div>
      </template>

      <div v-loading="dLoading" class="dbody">
        <template v-if="!readonly">
          <div class="picker">
            <el-select
              v-model="pickKey" filterable remote reserve-keyword clearable :remote-method="searchParts" :loading="optLoading"
              placeholder="输入零件编号或名称，选择颜色" class="grow" no-data-text="没有匹配的库存零件"
            >
              <el-option v-for="o in options" :key="keyOf(o)" :value="keyOf(o)" :label="`${o.part_num} ${o.name} · ${o.color_name}`">
                <div class="opt">
                  <span class="num">{{ o.part_num }}</span>
                  <span class="opt-name">{{ o.name }}</span>
                  <ColorChip :rgb="o.rgb" :name="o.color_name" />
                </div>
              </el-option>
            </el-select>
            <el-input-number v-model="pickQty" :min="1" :max="99999" step-strictly :precision="0" class="qty" />
            <button class="brick-btn yellow small" :disabled="!pickKey || !pickQty" @click="addLine()">添加</button>
          </div>
          <p class="muted tip">同一零件和颜色会合并数量；保存时提交全部明细。</p>
        </template>

        <el-table :data="lines" :empty-text="readonly ? '没有明细' : '还没有明细，先在上方搜索零件'" max-height="520">
          <el-table-column label="零件" min-width="220">
            <template #default="{ row }">
              <div class="part"><strong>{{ row.name || '（名称未查到）' }}</strong><span class="muted num">{{ row.part_num }}</span></div>
            </template>
          </el-table-column>
          <el-table-column label="颜色" min-width="140">
            <template #default="{ row }"><ColorChip :rgb="row.rgb" :name="row.color_name || `颜色 ${row.color_id}`" /></template>
          </el-table-column>
          <el-table-column label="数量" width="150" align="right">
            <template #default="{ row }">
              <span v-if="readonly" class="num">{{ row.quantity }}</span>
              <el-input-number v-else v-model="row.quantity" :min="1" :max="99999" step-strictly :precision="0" size="small" />
            </template>
          </el-table-column>
          <el-table-column v-if="!readonly" width="70" align="right">
            <template #default="{ $index }">
              <button class="linkbtn" :aria-label="`删除第 ${$index + 1} 行`" @click="lines.splice($index, 1)">移除</button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <div class="dfoot">
          <span class="muted">{{ lines.length }} 种零件，共 <b class="num">{{ totalQty }}</b> 件</span>
          <template v-if="readonly">
            <span class="okline">已入库，单据只读</span>
          </template>
          <template v-else>
            <button v-if="editing?.id" class="brick-btn small no-studs danger" :disabled="!!busy" @click="removeReceipt(editing.id)">删除草稿</button>
            <button class="brick-btn white small" :disabled="!dirty || invalid || !lines.length || !!busy" @click="save">
              {{ busy === 'save' ? '正在保存…' : '保存草稿' }}
            </button>
            <button
              class="brick-btn small" :disabled="!editing?.id || dirty || !lines.length || !!busy"
              :title="dirty ? '请先保存修改' : ''" @click="confirmReceipt()"
            >{{ busy === 'confirm' ? '正在入库…' : '确认入库' }}</button>
          </template>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.tabs { margin-bottom: 16px; }
.box { padding: 16px 18px 18px; }
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.grow { flex: 1 1 260px; }
.ops { display: inline-flex; gap: 8px; }
.pager :deep(.el-pagination) { justify-content: center; flex-wrap: wrap; }
.pager { display: flex; justify-content: center; margin-top: 18px; }
.dhead { display: flex; align-items: center; gap: 12px; }
.dhead h2 { font-size: 20px; font-weight: 900; color: var(--ink); }
.dbody { min-height: 200px; }
.picker { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.qty { width: 140px; }
.tip { font-size: 13px; margin: 8px 0 14px; }
.opt { display: flex; align-items: center; gap: 12px; }
.opt-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300px; }
.part { display: flex; flex-direction: column; line-height: 1.35; }
.part .muted { font-size: 12px; }
.linkbtn { border: 0; background: none; color: var(--lego-red); font-weight: 700; cursor: pointer; padding: 4px; }
.linkbtn:hover { text-decoration: underline; }
.dfoot { display: flex; align-items: center; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
.dfoot > .muted { margin-right: auto; }
.okline { color: var(--ok); font-weight: 700; }
</style>
