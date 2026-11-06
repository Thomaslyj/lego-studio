<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/index.js'
import { fmtTime } from '../api/lookup.js'
import StatusTag from '../components/StatusTag.vue'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)
const error = ref('')
const status = ref('all')
const page = ref(1)
const PAGE_SIZE = 15

async function load() {
  loading.value = true
  error.value = ''
  try { tasks.value = await api.tasks() } catch (e) { error.value = e.message } finally { loading.value = false }
}
onMounted(load)

// 任务接口返回全部数组，筛选与分页在前端完成
const counts = computed(() => ({
  all: tasks.value.length,
  draft: tasks.value.filter((t) => t.status === 'draft').length,
  issued: tasks.value.filter((t) => t.status === 'issued').length,
}))
const filtered = computed(() => (status.value === 'all' ? tasks.value : tasks.value.filter((t) => t.status === status.value)))
const rows = computed(() => filtered.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))
function setStatus(s) { status.value = s; page.value = 1 }

const deleting = ref(null)
async function remove(t) {
  try {
    await ElMessageBox.confirm(`删除草稿任务 #${t.id}（${t.set_name}）？删除后不可恢复。`, '删除草稿', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  deleting.value = t.id
  try {
    await api.deleteTask(t.id)
    ElMessage.success(`已删除任务 #${t.id}`)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    deleting.value = null
    load()
  }
}
const TABS = [['all', '全部'], ['draft', '草稿'], ['issued', '已领料']]
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>拼搭任务</h1>
        <p class="muted">从套装详情创建任务；草稿可修改或删除，领料后只读。</p>
      </div>
      <RouterLink to="/sets" class="brick-btn">从套装新建任务</RouterLink>
    </div>

    <div class="bar">
      <div class="seg" role="tablist" aria-label="任务状态">
        <button
          v-for="[k, label] in TABS" :key="k" type="button" role="tab"
          :aria-selected="status === k" :class="{ on: status === k }" @click="setStatus(k)"
        >{{ label }} <span class="tile">{{ counts[k] }}</span></button>
      </div>
      <button class="brick-btn white small no-studs" :disabled="loading" @click="load">刷新</button>
    </div>

    <section class="panel tablebox">
      <div v-if="error" class="inline-error">
        <span>{{ error }}</span>
        <button class="brick-btn white small no-studs" @click="load">重试</button>
      </div>
      <el-table
        v-else v-loading="loading" :data="rows" class="clickable"
        :empty-text="status === 'all' ? '还没有任务，去套装目录挑一套开始备料' : '该状态下没有任务'"
        @row-click="(r) => router.push(`/tasks/${r.id}`)"
      >
        <el-table-column label="任务" width="90">
          <template #default="{ row }"><span class="tile dark num">#{{ row.id }}</span></template>
        </el-table-column>
        <el-table-column label="套装" min-width="260">
          <template #default="{ row }">
            <div class="setcell"><strong>{{ row.set_name }}</strong><span class="muted num">{{ row.set_num }}</span></div>
          </template>
        </el-table-column>
        <el-table-column label="份数" width="80" align="right">
          <template #default="{ row }"><span class="num">{{ row.quantity }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }"><span class="num muted">{{ fmtTime(row.created_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="170" align="right">
          <template #default="{ row }">
            <div class="ops" @click.stop>
              <RouterLink :to="`/tasks/${row.id}`" class="brick-btn white small no-studs">{{ row.status === 'draft' ? '处理' : '查看' }}</RouterLink>
              <button
                v-if="row.status === 'draft'" class="brick-btn small no-studs danger"
                :disabled="deleting === row.id" @click="remove(row)"
              >删除</button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="filtered.length > PAGE_SIZE" class="pager">
        <el-pagination v-model:current-page="page" background layout="prev, pager, next" :total="filtered.length" :page-size="PAGE_SIZE" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.tablebox { padding: 8px 16px 16px; }
.clickable :deep(.el-table__row) { cursor: pointer; }
.setcell { display: flex; flex-direction: column; line-height: 1.35; }
.setcell .muted { font-size: 12px; }
.ops { display: inline-flex; gap: 8px; }
.inline-error { margin-top: 8px; }
.pager { display: flex; justify-content: center; margin-top: 18px; }
</style>
