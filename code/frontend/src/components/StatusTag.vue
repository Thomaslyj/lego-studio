<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const MAP = {
  draft: { text: '草稿', cls: 'draft' },
  issued: { text: '已领料', cls: 'done' },
  posted: { text: '已入库', cls: 'done' },
}
const s = computed(() => MAP[props.status] || { text: props.status, cls: 'draft' })
</script>

<template>
  <span class="status" :class="s.cls">{{ s.text }}</span>
</template>

<style scoped>
.status {
  display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 10px; border-radius: 4px;
  font: 700 13px/1 var(--font-body); white-space: nowrap;
}
.status::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.draft { background: #FFF4BF; color: #7A5D00; }
.done { background: #E3F2E7; color: var(--ok); }
</style>
