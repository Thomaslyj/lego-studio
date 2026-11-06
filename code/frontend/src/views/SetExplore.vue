<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/index.js'
import SetImage from '../components/SetImage.vue'

const route = useRoute()
const router = useRouter()
const PAGE_SIZE = 24
const PARTS = [
  { value: 0, label: '不限' }, { value: 100, label: '100 件以上' }, { value: 500, label: '500 件以上' },
  { value: 1000, label: '1000 件以上' }, { value: 2000, label: '2000 件以上' },
]
const YEARS = Array.from({ length: 2026 - 1949 + 1 }, (_, i) => 2026 - i)

// 筛选条件保存在地址栏，返回时保持
const q = reactive({ search: '', theme_id: null, year: null, min_parts: 0, page: 1 })
function readQuery() {
  const r = route.query
  q.search = r.search || ''
  q.theme_id = r.theme_id ? Number(r.theme_id) : null
  q.year = r.year ? Number(r.year) : null
  q.min_parts = Number(r.min_parts) || 0
  q.page = Number(r.page) || 1
}
function pushQuery(resetPage = true) {
  if (resetPage) q.page = 1
  const query = {}
  for (const [k, v] of Object.entries(q)) if (v !== '' && v !== null && v !== 0) query[k] = String(v)
  if (q.page === 1) delete query.page
  router.push({ query })
}

const list = ref({ total: 0, items: [] })
const loading = ref(false)
const error = ref('')
async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page: q.page, page_size: PAGE_SIZE, search: q.search, min_parts: q.min_parts }
    if (q.theme_id) params.theme_id = q.theme_id
    if (q.year) params.year = q.year
    list.value = await api.sets(params)
  } catch (e) {
    error.value = e.message
    list.value = { total: 0, items: [] }
  } finally {
    loading.value = false
  }
}
watch(() => route.query, () => { readQuery(); load() })

const themes = ref([])
const themeTree = computed(() => {
  const byId = new Map(themes.value.map((t) => [t.id, { value: t.id, label: t.name, children: [] }]))
  const roots = []
  for (const t of themes.value) {
    const node = byId.get(t.id)
    const parent = t.parent_id && byId.get(t.parent_id)
    parent ? parent.children.push(node) : roots.push(node)
  }
  const strip = (n) => { if (!n.children.length) delete n.children; else n.children.forEach(strip); return n }
  return roots.map(strip)
})

// 主视觉：从大型套装中按日期轮换一套
const hero = ref(null)
async function loadHero() {
  try {
    const r = await api.sets({ min_parts: 1500, page_size: 30 })
    if (r.items.length) hero.value = r.items[new Date().getDate() % r.items.length]
  } catch { /* 主视觉失败不影响目录 */ }
}

const filtered = computed(() => q.search || q.theme_id || q.year || q.min_parts)
function clearAll() {
  Object.assign(q, { search: '', theme_id: null, year: null, min_parts: 0 })
  pushQuery()
}

onMounted(async () => {
  readQuery()
  load()
  loadHero()
  try { themes.value = await api.themesCached() } catch { /* 主题加载失败时仍可按名称搜索 */ }
})
</script>

<template>
  <section v-if="hero" class="hero">
    <div class="hero-inner">
      <div class="hero-copy">
        <span class="label-chip">今日推荐</span>
        <h1>{{ hero.name }}</h1>
        <dl class="hero-meta">
          <div><dt>编号</dt><dd class="num">{{ hero.set_num }}</dd></div>
          <div><dt>主题</dt><dd>{{ hero.theme_name }}</dd></div>
          <div><dt>年份</dt><dd class="num">{{ hero.year }}</dd></div>
          <div><dt>零件</dt><dd class="num">{{ hero.num_parts }}</dd></div>
        </dl>
        <RouterLink :to="{ path: `/sets/${hero.set_num}`, query: route.query }" class="brick-btn">开始备料</RouterLink>
      </div>
      <div class="hero-img studs">
        <div class="hero-frame">
          <SetImage :set-num="hero.set_num" :name="hero.name" :theme="hero.theme_name" />
        </div>
      </div>
    </div>
  </section>

  <div class="page">
    <div class="head">
      <h2>套装目录</h2>
      <span class="muted">共 <b class="num">{{ list.total }}</b> 套{{ filtered ? '符合条件' : '' }}</span>
    </div>

    <form class="filters panel" @submit.prevent="pushQuery()">
      <el-input v-model="q.search" placeholder="按套装名称搜索" clearable class="f-search" @clear="pushQuery()" />
      <el-tree-select
        v-model="q.theme_id" :data="themeTree" :cache-data="themes.map((t) => ({ value: t.id, label: t.name }))" placeholder="全部主题" clearable filterable check-strictly
        :render-after-expand="false" class="f-theme" @change="pushQuery()"
      />
      <el-select v-model="q.year" placeholder="全部年份" clearable filterable class="f-year" @change="pushQuery()">
        <el-option v-for="y in YEARS" :key="y" :label="`${y} 年`" :value="y" />
      </el-select>
      <el-select v-model="q.min_parts" class="f-parts" @change="pushQuery()">
        <el-option v-for="p in PARTS" :key="p.value" :label="p.value ? p.label : '零件数不限'" :value="p.value" />
      </el-select>
      <button type="submit" class="brick-btn small">搜索</button>
      <button v-if="filtered" type="button" class="brick-btn white small no-studs" @click="clearAll">清空筛选</button>
    </form>
    <p class="hint muted">主题只匹配所选主题本身，不含其子主题。</p>

    <div v-if="error" class="state panel">
      <p><b>目录加载失败：</b>{{ error }}</p>
      <button class="brick-btn small" @click="load">重新加载</button>
    </div>
    <div v-else-if="!loading && !list.items.length" class="state panel">
      <p>没有符合条件的套装。可以换个名称，或放宽主题、年份和零件数。</p>
      <button v-if="filtered" class="brick-btn white small" @click="clearAll">清空筛选</button>
    </div>

    <div v-else v-loading="loading" class="grid">
      <RouterLink v-for="s in list.items" :key="s.set_num" :to="{ path: `/sets/${s.set_num}`, query: route.query }" class="card">
        <div class="card-img"><SetImage :set-num="s.set_num" :name="s.name" :theme="s.theme_name" /></div>
        <div class="card-body">
          <h3 :title="s.name">{{ s.name }}</h3>
          <p class="card-theme">{{ s.theme_name }}</p>
          <div class="card-meta">
            <span class="tile dark num">{{ s.set_num }}</span>
            <span class="num">{{ s.year }} 年</span>
            <span class="num">{{ s.num_parts }} 件</span>
          </div>
          <span class="card-cta">查看备料</span>
        </div>
      </RouterLink>
    </div>

    <div v-if="list.total > PAGE_SIZE" class="pager">
      <el-pagination
        background layout="prev, pager, next, jumper" :total="list.total" :page-size="PAGE_SIZE"
        :current-page="q.page" @current-change="(p) => { q.page = p; pushQuery(false) }"
      />
    </div>
  </div>
</template>

<style scoped>
.hero { background: var(--lego-yellow); border-bottom: 6px solid var(--ink); }
.hero-inner {
  max-width: 1280px; margin: 0 auto; padding: 40px 28px 44px;
  display: grid; grid-template-columns: 1fr 1.05fr; gap: 40px; align-items: center;
}
.hero-copy { display: flex; flex-direction: column; align-items: flex-start; gap: 18px; }
.hero h1 { font: 900 clamp(30px, 4vw, 52px)/1.05 var(--font-display); letter-spacing: -.02em; max-width: 14em; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 10px; margin: 0; }
.hero-meta div { background: #fff; border-radius: 6px; padding: 8px 14px; box-shadow: 0 3px 0 var(--lego-yellow-deep); }
.hero-meta dt { font-size: 12px; color: var(--ink-3); }
.hero-meta dd { margin: 0; font-weight: 800; }
.hero-img { --c: var(--lego-red); --s: 26px; border-radius: var(--r-lg); padding: 22px; box-shadow: 0 6px 0 var(--lego-red-deep); }
.hero-frame { aspect-ratio: 4 / 3; border-radius: 10px; overflow: hidden; background: #fff; padding: 16px; }

.head { display: flex; align-items: baseline; gap: 16px; margin: 8px 0 16px; }
.head h2 { font: 900 28px/1.1 var(--font-display); }
.filters { display: flex; flex-wrap: wrap; gap: 12px; padding: 16px; align-items: center; }
.f-search { flex: 1 1 260px; }
.f-theme { width: 220px; }
.f-year { width: 140px; }
.f-parts { width: 150px; }
.hint { font-size: 13px; margin: 8px 4px 22px; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 22px; min-height: 200px; }
.card {
  display: flex; flex-direction: column; text-decoration: none; color: inherit;
  background: #fff; border-radius: var(--r-md); overflow: hidden;
  box-shadow: 0 3px 0 var(--plate-line), 0 6px 14px -10px rgba(0,0,0,.3);
  transition: transform .15s ease, box-shadow .15s ease;
}
.card:hover { transform: translateY(-4px); box-shadow: 0 6px 0 var(--plate-line), var(--lift); }
.card:focus-visible { outline: 3px solid var(--lego-blue); outline-offset: 3px; }
.card-img { aspect-ratio: 4 / 3; padding: 14px; border-bottom: 1px solid var(--plate-line); }
.card-body { flex: 1; display: flex; flex-direction: column; gap: 6px; padding: 14px 16px 16px; }
.card h3 { font-size: 16px; font-weight: 800; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-theme { margin: 0; font-size: 13px; color: var(--ink-3); }
.card-meta { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--ink-2); margin-top: 2px; }
.card-meta .tile { height: 24px; font-size: 12px; }
.card-cta { margin-top: auto; padding-top: 10px; font-weight: 800; color: var(--lego-red); }
.card:hover .card-cta { text-decoration: underline; text-underline-offset: 4px; }

.state { padding: 28px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.state p { margin: 0; }
.pager :deep(.el-pagination) { justify-content: center; flex-wrap: wrap; }
.pager { display: flex; justify-content: center; margin-top: 32px; }

@media (max-width: 900px) {
  .hero-inner { grid-template-columns: 1fr; padding: 24px 14px 28px; gap: 22px; }
  .f-theme, .f-year, .f-parts { flex: 1 1 140px; width: auto; }
}
</style>
