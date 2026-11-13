<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/index.js'
import { fmtTime } from '../api/lookup.js'
import RequirementTable from '../components/RequirementTable.vue'
import StatusTag from '../components/StatusTag.vue'
import SetImage from '../components/SetImage.vue'
import { useShortageReceipt } from '../composables/shortageReceipt.js'

const route = useRoute()
const router = useRouter()
const id = computed(() => Number(route.params.id))

const task = ref(null)
const items = ref([])
const setName = ref('')
const issueId = ref(null)
const versions = ref([])
const loading = ref(false)
const error = ref('')
const notFound = ref(false)
const checkedAt = ref('')

// 编辑表单
const formVersion = ref(null)
const formQty = ref(1)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const r = await api.task(id.value)
    task.value = r.task
    items.value = r.items
    formVersion.value = r.task.inventory_id
    formQty.value = r.task.quantity
    checkedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch (e) {
    if (e.status === 404) notFound.value = true
    else error.value = e.message
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  // 套装名称和领料单号来自列表接口
  const [tasks, issues] = await Promise.all([api.tasks(), task.value?.status === 'issued' ? api.issues() : []])
  setName.value = tasks.find((t) => t.id === id.value)?.set_name || ''
  issueId.value = issues.find((i) => i.task_id === id.value)?.id ?? null
  if (task.value?.status === 'draft') versions.value = await api.setVersions(task.value.set_num)
}

async function init() {
  notFound.value = false
  await load()
  if (task.value) loadMeta().catch(() => {})
}
onMounted(init)
watch(id, init)

const isDraft = computed(() => task.value?.status === 'draft')
const shortKinds = computed(() => items.value.filter((i) => i.shortage > 0).length)
const shortTotal = computed(() => items.value.reduce((s, i) => s + Number(i.shortage), 0))
const dirty = computed(() => task.value && (formVersion.value !== task.value.inventory_id || formQty.value !== task.value.quantity))
const currentVersion = computed(() => versions.value.find((v) => v.id === task.value?.inventory_id)?.version)

const saving = ref(false)
async function save() {
  if (saving.value || !formQty.value) return
  saving.value = true
  try {
    await api.updateTask(id.value, { set_num: task.value.set_num, quantity: formQty.value, inventory_id: formVersion.value })
    ElMessage.success('已保存修改，需求已按新设置重新计算')
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

const issuing = ref(false)
async function issue() {
  if (issuing.value) return
  issuing.value = true
  try {
    await ElMessageBox.confirm(
      `确认为任务 #${id.value} 领料？将一次性扣减 ${items.value.length} 种零件的库存，领料后任务只读。`,
      '确认领料', { confirmButtonText: '确认领料', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { issuing.value = false; return }
  try {
    const r = await api.issueTask(id.value)
    ElMessage.success(`领料完成，领料单 #${r.id}`)
    issueId.value = r.id
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    issuing.value = false
    await load()
    loadMeta().catch(() => {})
  }
}

const removing = ref(false)
async function remove() {
  try {
    await ElMessageBox.confirm(`删除草稿任务 #${id.value}？删除后不可恢复。`, '删除草稿', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  removing.value = true
  try {
    await api.deleteTask(id.value)
    ElMessage.success(`已删除任务 #${id.value}`)
    router.push('/tasks')
  } catch (e) {
    ElMessage.error(e.message)
    removing.value = false
  }
}

const { creatingReceipt, createFromShortage } = useShortageReceipt()
</script>

<template>
  <div class="page">
    <RouterLink to="/tasks" class="back">← 返回任务列表</RouterLink>

    <div v-if="notFound" class="state panel">
      <p>任务 <b class="num">#{{ id }}</b> 不存在，可能已被删除。</p>
      <RouterLink to="/tasks" class="brick-btn small">回到任务列表</RouterLink>
    </div>
    <div v-else-if="error && !task" class="state panel">
      <p><b>任务加载失败：</b>{{ error }}</p>
      <button class="brick-btn small" @click="init">重新加载</button>
    </div>

    <template v-else-if="task">
      <section class="top panel">
        <div class="thumb"><SetImage :set-num="task.set_num" :name="setName" /></div>
        <div class="top-info">
          <div class="ids">
            <span class="tile dark num">任务 #{{ task.id }}</span>
            <StatusTag :status="task.status" />
          </div>
          <h1>{{ setName || task.set_num }}</h1>
          <p class="muted">
            <RouterLink :to="`/sets/${task.set_num}`" class="num">{{ task.set_num }}</RouterLink>
            <span class="sep" />份数 <b class="num">{{ task.quantity }}</b>
            <template v-if="currentVersion"><span class="sep" />第 {{ currentVersion }} 版清单</template>
            <span class="sep" />创建于 <span class="num">{{ fmtTime(task.created_at) }}</span>
          </p>
        </div>
      </section>

      <div class="body">
        <section class="panel list">
          <div class="list-title">
            <span class="label-chip">零件明细</span>
            <span class="muted small">{{ isDraft ? `库存检查于 ${checkedAt}` : '已领料，库存列为当前库存' }}</span>
          </div>
          <RequirementTable :items="items" :loading="loading" />
        </section>

        <aside class="side">
          <section v-if="isDraft" class="panel box">
            <h2>修改草稿</h2>
            <label class="field">
              <span>清单版本</span>
              <el-select v-model="formVersion" placeholder="选择版本">
                <el-option
                  v-for="v in versions" :key="v.id" :value="v.id" :disabled="!v.supported"
                  :label="`第 ${v.version} 版${v.supported ? '' : '（不支持）'}`"
                />
              </el-select>
            </label>
            <label class="field">
              <span>组装份数</span>
              <el-input-number v-model="formQty" :min="1" :max="999" step-strictly :precision="0" />
            </label>
            <button class="brick-btn white small" :disabled="!dirty || !formQty || saving" @click="save">
              {{ saving ? '正在保存…' : '保存修改' }}
            </button>
          </section>

          <section class="panel box" :class="{ blocked: isDraft && shortKinds }">
            <h2>领料</h2>
            <template v-if="isDraft">
              <div v-if="shortKinds" class="warn">
                <div class="hazard stripe" aria-hidden="true" />
                <p><b>缺 {{ shortKinds }} 种、共 {{ shortTotal }} 件，暂不能领料。</b>先补货入库，再重新检查库存。</p>
              </div>
              <p v-else-if="items.length" class="okline">库存足够，可以领料。</p>
              <p v-if="dirty" class="muted small">有未保存的修改，领料按已保存的设置执行。</p>

              <button class="brick-btn create" :disabled="!!shortKinds || !items.length || issuing || loading" @click="issue">
                {{ issuing ? '正在领料…' : '确认领料' }}
              </button>
              <button class="brick-btn white small" :disabled="loading" @click="load">重新检查库存</button>
              <button v-if="shortKinds" class="brick-btn yellow small" :disabled="creatingReceipt" @click="createFromShortage(items)">
                {{ creatingReceipt ? '正在生成…' : '按缺件生成入库草稿' }}
              </button>
              <button class="brick-btn small no-studs danger" :disabled="removing" @click="remove">删除草稿</button>
            </template>
            <template v-else>
              <p class="okline">该任务已领料，内容只读。</p>
              <RouterLink
                v-if="issueId" class="brick-btn white small"
                :to="{ path: '/records', query: { tab: 'issues', issue: issueId } }"
              >查看领料单 #{{ issueId }}</RouterLink>
            </template>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back { display: inline-block; margin-bottom: 16px; font-weight: 700; color: var(--ink-2); text-decoration: none; }
.back:hover { color: var(--lego-red); }
.top { display: grid; grid-template-columns: 150px 1fr; gap: 24px; padding: 18px 22px; align-items: center; }
.thumb { aspect-ratio: 4 / 3; border-radius: 8px; overflow: hidden; box-shadow: inset 0 0 0 1px var(--plate-line); padding: 6px; }
.top-info { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.ids { display: flex; gap: 10px; align-items: center; }
.top-info h1 { font: 900 clamp(22px, 2.6vw, 32px)/1.15 var(--font-display); }
.top-info p { margin: 0; display: flex; flex-wrap: wrap; align-items: center; }
.top-info a { color: var(--lego-blue); font-weight: 700; }
.sep { width: 1px; height: 14px; background: var(--plate-line); margin: 0 12px; }

.body { display: grid; grid-template-columns: 1fr 340px; gap: 24px; margin-top: 24px; align-items: start; }
.list { padding: 20px; min-width: 0; }
.list-title { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.small { font-size: 13px; }
.side { display: flex; flex-direction: column; gap: 20px; position: sticky; top: 96px; }
.box { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.box h2 { font-size: 17px; font-weight: 800; }
.box p { margin: 0; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field > span { font-size: 13px; font-weight: 700; color: var(--ink-2); }
.field :deep(.el-select), .field :deep(.el-input-number) { width: 100%; }
.warn { border-radius: 8px; overflow: hidden; background: #FFF6D6; }
.warn .stripe { height: 8px; }
.warn p { padding: 10px 12px; font-size: 14px; }
.okline { color: var(--ok); font-weight: 700; }
.create { width: 100%; min-height: 48px; font-size: 16px; }
.box .brick-btn.small { width: 100%; }
.state { padding: 28px; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.state p { margin: 0; }

@media (max-width: 960px) {
  .body { grid-template-columns: 1fr; }
  .side { position: static; order: -1; }
  .top { grid-template-columns: 100px 1fr; }
}
</style>
