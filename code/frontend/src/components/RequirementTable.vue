<script setup>
// 备料明细：套装详情与任务详情共用
import { computed, ref } from 'vue'
import ColorChip from './ColorChip.vue'

const props = defineProps({ items: { type: Array, default: () => [] }, loading: Boolean })
const onlyShort = ref(false)
const rows = computed(() => (onlyShort.value ? props.items.filter((i) => i.shortage > 0) : props.items))
const shortCount = computed(() => props.items.filter((i) => i.shortage > 0).length)
</script>

<template>
  <div class="req">
    <div class="req-head">
      <div class="seg" role="tablist" aria-label="明细范围">
        <button type="button" role="tab" :aria-selected="!onlyShort" :class="{ on: !onlyShort }" @click="onlyShort = false">
          全部零件 <span class="tile">{{ items.length }}</span>
        </button>
        <button type="button" role="tab" :aria-selected="onlyShort" :class="{ on: onlyShort }" @click="onlyShort = true">
          仅看缺件 <span class="tile" :class="shortCount ? 'red' : ''">{{ shortCount }}</span>
        </button>
      </div>
      <slot name="actions" />
    </div>
    <el-table v-loading="loading" :data="rows" max-height="560" :empty-text="onlyShort ? '没有缺件，库存足够' : '暂无零件明细'">
      <el-table-column label="零件" min-width="240">
        <template #default="{ row }">
          <div class="part">
            <strong>{{ row.part_name }}</strong>
            <span class="muted num">{{ row.part_num }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="颜色" min-width="150">
        <template #default="{ row }"><ColorChip :rgb="row.rgb" :name="row.color_name" /></template>
      </el-table-column>
      <el-table-column label="需求" width="90" align="right">
        <template #default="{ row }"><span class="num">{{ row.required_quantity }}</span></template>
      </el-table-column>
      <el-table-column label="库存" width="90" align="right">
        <template #default="{ row }"><span class="num">{{ row.stock_quantity }}</span></template>
      </el-table-column>
      <el-table-column label="缺件" width="90" align="right">
        <template #default="{ row }">
          <span v-if="row.shortage > 0" class="num shortage">{{ row.shortage }}</span>
          <span v-else class="enough" aria-label="足够">✓</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.req-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.part { display: flex; flex-direction: column; line-height: 1.35; }
.part strong { font-weight: 600; }
.part .muted { font-size: 12px; }
</style>
