<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/index.js'
import SetImage from '../components/SetImage.vue'
import RequirementTable from '../components/RequirementTable.vue'
import { useShortageReceipt } from '../composables/shortageReceipt.js'

const route = useRoute()
const router = useRouter()
const setNum = computed(() => route.params.setNum)

const versions = ref([])
const inventoryId = ref(null)
const quantity = ref(1)
const detail = ref(null)
const loading = ref(false)
const error = ref('')
const notFound = ref(false)

async function loadVersions() {
  versions.value = await api.setVersions(setNum.value)
  // 默认最高的可用版本
  const ok = versions.value.find((v) => v.supported)
  inventoryId.value = ok ? ok.id : null
}

async function loadDetail() {
  if (!inventoryId.value) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await api.setDetail(setNum.value, { quantity: quantity.value, inventory_id: inventoryId.value })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function init() {
  notFound.value = false
  error.value = ''
  detail.value = null
  try {
    await loadVersions()
    if (inventoryId.value) await loadDetail()
  } catch (e) {
    if (e.status === 404) notFound.value = true
    else error.value = e.message
  }
}
onMounted(init)
watch(setNum, init)

let timer
watch(quantity, (v) => {
  if (!Number.isInteger(v) || v < 1) return
  clearTimeout(timer)
  timer = setTimeout(loadDetail, 300)
})

const items = computed(() => detail.value?.items || [])
const summary = computed(() => {
  const s = { kinds: items.value.length, need: 0, short: 0, shortKinds: 0 }
  for (const i of items.value) {
    s.need += Number(i.required_quantity)
    s.short += Number(i.shortage)
    if (i.shortage > 0) s.shortKinds++
  }
  return s
})
const set = computed(() => detail.value?.set)
// 套装详情只返回主题编号，名称从主题列表取
const themeNames = ref(new Map())
api.themesCached().then((ts) => { themeNames.value = new Map(ts.map((t) => [t.id, t.name])) }).catch(() => {})
const themeName = computed(() => set.value && themeNames.value.get(set.value.theme_id))
const noSupported = computed(() => versions.value.length > 0 && !versions.value.some((v) => v.supported))

const creating = ref(false)
async function createTask() {
  if (creating.value) return
  creating.value = true
  try {
    const r = await api.createTask({ set_num: setNum.value, quantity: quantity.value, inventory_id: inventoryId.value })
    ElMessage.success(`已创建组装任务 #${r.id}`)
    router.push(`/tasks/${r.id}`)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    creating.value = false
  }
}

const { creatingReceipt, createFromShortage } = useShortageReceipt()
</script>

<template>
  <div class="page">
    <RouterLink :to="{ path: '/sets', query: route.query }" class="back">← 返回套装目录</RouterLink>

    <div v-if="notFound" class="state panel">
      <p>找不到套装 <b class="num">{{ setNum }}</b>，可能编号有误。</p>
      <RouterLink to="/sets" class="brick-btn small">回到目录</RouterLink>
    </div>

    <template v-else>
      <section class="top panel">
        <div class="top-img studs"><div class="frame"><SetImage :set-num="setNum" :name="set?.name" :theme="themeName" /></div></div>
        <div class="top-info">
          <span class="tile dark num">{{ setNum }}</span>
          <h1>{{ set?.name || '套装详情' }}</h1>
          <dl v-if="set" class="facts">
            <div><dt>年份</dt><dd class="num">{{ set.year }}</dd></div>
            <div><dt>目录零件数</dt><dd class="num">{{ set.num_parts }}</dd></div>
            <div v-if="themeName"><dt>主题</dt><dd>{{ themeName }}</dd></div>
          </dl>
          <p class="muted note">备料按所选清单版本计算，不含备用零件；查看需求不会占用库存。</p>
        </div>
      </section>

      <div class="body">
        <section class="panel list">
          <div class="list-title">
            <span class="label-chip">零件明细</span>
          </div>
          <div v-if="error" class="inline-error">
            <span>{{ error }}</span>
            <button class="brick-btn white small no-studs" @click="loadDetail">重试</button>
          </div>
          <div v-else-if="noSupported" class="inline-error">
            该套装的清单都包含嵌套套装或数据不完整，暂不支持备料。
          </div>
          <RequirementTable v-else :items="items" :loading="loading" />
        </section>

        <aside class="side">
          <section class="panel box">
            <h2>备料设置</h2>
            <label class="field">
              <span>清单版本</span>
              <el-select v-model="inventoryId" placeholder="选择版本" :disabled="!versions.length" @change="loadDetail">
                <el-option
                  v-for="v in versions" :key="v.id" :value="v.id" :disabled="!v.supported"
                  :label="`第 ${v.version} 版${v.supported ? '' : '（不支持）'}`"
                />
              </el-select>
            </label>
            <label class="field">
              <span>组装份数</span>
              <el-input-number v-model="quantity" :min="1" :max="999" :step="1" step-strictly :precision="0" />
            </label>
          </section>

          <section class="panel box summary" :class="{ short: summary.short > 0 }">
            <h2>备料摘要</h2>
            <div class="stats">
              <div><span class="tile">{{ summary.kinds }}</span><small>零件种类</small></div>
              <div><span class="tile">{{ summary.need }}</span><small>需求总数</small></div>
              <div><span class="tile" :class="summary.short ? 'red' : ''">{{ summary.short }}</span><small>缺件总数</small></div>
            </div>
            <div v-if="summary.short > 0" class="warn">
              <div class="hazard stripe" aria-hidden="true" />
              <p><b>{{ summary.shortKinds }} 种零件库存不足。</b>可以先创建任务，补货入库后再领料。</p>
            </div>
            <p v-else-if="items.length" class="okline">库存足够，创建任务后即可领料。</p>

            <button class="brick-btn create" :disabled="!inventoryId || !quantity || !items.length || creating" @click="createTask">
              {{ creating ? '正在创建…' : '创建组装任务' }}
            </button>
            <button
              v-if="summary.short > 0" class="brick-btn yellow small"
              :disabled="creatingReceipt" @click="createFromShortage(items)"
            >
              {{ creatingReceipt ? '正在生成…' : '按缺件生成入库草稿' }}
            </button>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.back { display: inline-block; margin-bottom: 16px; font-weight: 700; color: var(--ink-2); text-decoration: none; }
.back:hover { color: var(--lego-red); }
.top { display: grid; grid-template-columns: minmax(260px, 420px) 1fr; gap: 32px; padding: 22px; align-items: center; }
.top-img { --c: var(--lego-yellow); --s: 22px; border-radius: 12px; padding: 16px; box-shadow: 0 4px 0 var(--lego-yellow-deep); }
.frame { aspect-ratio: 4 / 3; background: #fff; border-radius: 8px; padding: 12px; overflow: hidden; }
.top-info { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }
.top-info h1 { font: 900 clamp(26px, 3vw, 40px)/1.1 var(--font-display); }
.facts { display: flex; flex-wrap: wrap; gap: 24px; margin: 4px 0 0; }
.facts dt { font-size: 12px; color: var(--ink-3); }
.facts dd { margin: 0; font-weight: 800; font-size: 17px; }
.note { font-size: 13px; margin: 0; }

.body { display: grid; grid-template-columns: 1fr 340px; gap: 24px; margin-top: 24px; align-items: start; }
.list { padding: 20px; min-width: 0; }
.list-title { margin-bottom: 14px; }
.side { display: flex; flex-direction: column; gap: 20px; position: sticky; top: 96px; }
.box { padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.box h2 { font-size: 17px; font-weight: 800; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field > span { font-size: 13px; font-weight: 700; color: var(--ink-2); }
.field :deep(.el-select), .field :deep(.el-input-number) { width: 100%; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.stats div { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 10px 4px; background: var(--plate); border-radius: 8px; }
.stats .tile { min-width: 56px; height: 36px; font-size: 17px; }
.stats small { font-size: 12px; color: var(--ink-2); }
.warn { border-radius: 8px; overflow: hidden; background: #FFF6D6; }
.warn .stripe { height: 8px; }
.warn p { margin: 0; padding: 10px 12px; font-size: 14px; }
.okline { margin: 0; color: var(--ok); font-weight: 700; }
.create { width: 100%; min-height: 48px; font-size: 16px; }
.summary .brick-btn.small { width: 100%; }
.state { padding: 28px; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.state p { margin: 0; }

@media (max-width: 960px) {
  .top { grid-template-columns: 1fr; }
  .body { grid-template-columns: 1fr; }
  .side { position: static; order: -1; }
}
</style>
