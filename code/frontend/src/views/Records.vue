<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/index.js'
import { enrich, fmtTime, remember } from '../api/lookup.js'
import ColorChip from '../components/ColorChip.vue'

const route = useRoute()
const router = useRouter()
const tab = ref(route.query.tab === 'receipts' ? 'receipts' : 'issues')
function switchTab(t) {
  tab.value = t
  selected.value = null
  router.replace({ query: { tab: t } })
}

const issues = ref([])
const receipts = ref([])
const taskMap = ref(new Map())
const loading = ref(false)
const error = ref('')
async function load() {
  loading.value = true
  error.value = ''
  try {
    const [is, rs, ts] = await Promise.all([api.issues(), api.receipts(), api.tasks()])
    issues.value = is
    receipts.value = rs.filter((r) => r.status === 'posted')
    taskMap.value = new Map(ts.map((t) => [t.id, t]))
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const PAGE_SIZE = 12
const page = ref(1)
const list = computed(() => (tab.value === 'issues' ? issues.value : receipts.value))
const rows = computed(() => list.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))
watch(tab, () => { page.value = 1 })

// 选中单据后加载明细
const selected = ref(null) // { kind, id }
const detail = ref(null)
const items = ref([])
const dLoading = ref(false)
const dError = ref('')
async function open(kind, id) {
  selected.value = { kind, id }
  dLoading.value = true
  dError.value = ''
  items.value = []
  try {
    if (kind === 'issue') {
      const r = await api.issue(id)
      detail.value = r.issue
      // 领料明细与任务需求同源，借任务详情补零件和颜色名称
      await api.task(r.issue.task_id).then((t) => remember(t.items)).catch(() => {})
      items.value = await enrich(r.items)
    } else {
      const r = await api.receipt(id)
      detail.value = r.receipt
      items.value = await enrich(r.items)
    }
    router.replace({ query: { tab: tab.value, [kind]: id } })
  } catch (e) {
    dError.value = e.message
  } finally {
    dLoading.value = false
  }
}
const totalQty = computed(() => items.value.reduce((s, i) => s + Number(i.quantity), 0))
const task = computed(() => detail.value && taskMap.value.get(detail.value.task_id))

onMounted(async () => {
  await load()
  if (route.query.issue) { tab.value = 'issues'; open('issue', Number(route.query.issue)) }
  else if (route.query.receipt) { tab.value = 'receipts'; open('receipt', Number(route.query.receipt)) }
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>单据记录</h1>
        <p class="muted">已确认的领料单和入库单，只读查看零件、颜色和数量。</p>
      </div>
      <button class="brick-btn white small no-studs" :disabled="loading" @click="load">刷新</button>
    </div>

    <div class="seg tabs" role="tablist" aria-label="单据类型">
      <button type="button" role="tab" :aria-selected="tab === 'issues'" :class="{ on: tab === 'issues' }" @click="switchTab('issues')">
        领料记录 <span class="tile">{{ issues.length }}</span>
      </button>
      <button type="button" role="tab" :aria-selected="tab === 'receipts'" :class="{ on: tab === 'receipts' }" @click="switchTab('receipts')">
        已入库记录 <span class="tile">{{ receipts.length }}</span>
      </button>
    </div>

    <div v-if="error" class="inline-error">
      <span>{{ error }}</span>
      <button class="brick-btn white small no-studs" @click="load">重试</button>
    </div>

    <div v-else class="layout">
      <section v-loading="loading" class="panel listbox">
        <p v-if="!loading && !list.length" class="empty">
          {{ tab === 'issues' ? '还没有领料记录。任务库存足够时，在任务详情确认领料。' : '还没有已入库的单据。在“库存与入库”确认入库单后会出现在这里。' }}
        </p>
        <ul class="doclist">
          <li v-for="d in rows" :key="d.id">
            <button
              type="button" class="doc"
              :class="{ on: selected && selected.id === d.id && selected.kind === (tab === 'issues' ? 'issue' : 'receipt') }"
              @click="open(tab === 'issues' ? 'issue' : 'receipt', d.id)"
            >
              <span class="tile num" :class="tab === 'issues' ? 'red' : 'yellow'">#{{ d.id }}</span>
              <span class="doc-main">
                <strong v-if="tab === 'issues'">{{ taskMap.get(d.task_id)?.set_name || `任务 #${d.task_id}` }}</strong>
                <strong v-else>入库单 #{{ d.id }}</strong>
                <small class="muted num">
                  <template v-if="tab === 'issues'">任务 #{{ d.task_id }} · </template>{{ fmtTime(d.created_at) }}
                </small>
              </span>
            </button>
          </li>
        </ul>
        <div v-if="list.length > PAGE_SIZE" class="pager">
          <el-pagination v-model:current-page="page" small layout="prev, pager, next" :total="list.length" :page-size="PAGE_SIZE" />
        </div>
      </section>

      <section class="panel detailbox">
        <div v-if="!selected" class="placeholder studs">
          <p>从左侧选择一张单据查看明细</p>
        </div>
        <template v-else>
          <div v-if="dError" class="inline-error">
            <span>{{ dError }}</span>
            <button class="brick-btn white small no-studs" @click="open(selected.kind, selected.id)">重试</button>
          </div>
          <template v-else>
            <header class="dhead">
              <span class="label-chip">{{ selected.kind === 'issue' ? '领料单' : '入库单' }} #{{ selected.id }}</span>
              <span v-if="detail" class="muted num">{{ fmtTime(detail.created_at) }}</span>
              <RouterLink v-if="selected.kind === 'issue' && detail" :to="`/tasks/${detail.task_id}`" class="tasklink">
                来自任务 #{{ detail.task_id }}<template v-if="task"> · {{ task.set_name }} × {{ task.quantity }}</template>
              </RouterLink>
            </header>
            <el-table v-loading="dLoading" :data="items" max-height="560" empty-text="该单据没有明细">
              <el-table-column label="零件" min-width="240">
                <template #default="{ row }">
                  <div class="part"><strong>{{ row.name || '（名称未查到）' }}</strong><span class="muted num">{{ row.part_num }}</span></div>
                </template>
              </el-table-column>
              <el-table-column label="颜色" min-width="150">
                <template #default="{ row }"><ColorChip :rgb="row.rgb" :name="row.color_name || `颜色 ${row.color_id}`" /></template>
              </el-table-column>
              <el-table-column label="数量" width="100" align="right">
                <template #default="{ row }"><span class="num">{{ row.quantity }}</span></template>
              </el-table-column>
            </el-table>
            <p class="total muted">{{ items.length }} 种零件，共 <b class="num">{{ totalQty }}</b> 件</p>
          </template>
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.tabs { margin-bottom: 16px; }
.layout { display: grid; grid-template-columns: 340px 1fr; gap: 22px; align-items: start; }
.listbox { padding: 10px; min-height: 240px; }
.empty { padding: 18px 12px; margin: 0; color: var(--ink-2); }
.doclist { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.doc {
  width: 100%; display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 0; border-radius: 8px;
  background: transparent; text-align: left; cursor: pointer; color: inherit; font: inherit;
  transition: background .12s, transform .12s, box-shadow .12s;
}
.doc:hover { background: var(--plate); }
.doc.on { background: #fff; box-shadow: 0 0 0 2px var(--lego-blue), 0 4px 0 #C9CDD2; transform: translateY(-1px); }
.doc .tile { min-width: 52px; }
.doc-main { display: flex; flex-direction: column; min-width: 0; }
.doc-main strong { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-main small { font-size: 12px; }
.pager { display: flex; justify-content: center; margin-top: 10px; }
.detailbox { padding: 18px 20px; min-height: 320px; }
.placeholder { --c: #F5F6F7; --s: 26px; height: 280px; border-radius: 10px; display: grid; place-items: center; }
.placeholder p { margin: 0; padding: 8px 16px; background: #fff; border-radius: 6px; font-weight: 700; color: var(--ink-2); box-shadow: 0 3px 0 var(--plate-line); }
.dhead { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 14px; }
.tasklink { color: var(--lego-blue); font-weight: 700; margin-left: auto; }
.part { display: flex; flex-direction: column; line-height: 1.35; }
.part .muted { font-size: 12px; }
.total { margin: 12px 0 0; text-align: right; }

@media (max-width: 900px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  .listbox, .detailbox { min-width: 0; }
}
</style>
