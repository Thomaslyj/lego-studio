<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({ setNum: String, name: String, theme: String })
const failed = ref(false)
watch(() => props.setNum, () => { failed.value = false })

const src = computed(() => `https://cdn.rebrickable.com/media/sets/${encodeURIComponent((props.setNum || '').toLowerCase())}.jpg`)
// 无图时按主题名固定取一种积木色
const COLORS = ['#E3000B', '#006CB7', '#FFD500', '#00852B', '#F57D20', '#4F5559', '#A0A5A9', '#7C3F9B']
const color = computed(() => {
  let h = 0
  for (const ch of props.theme || props.setNum || '') h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return COLORS[h % COLORS.length]
})
</script>

<template>
  <div class="setimg">
    <img v-if="!failed" :src="src" :alt="name || setNum" loading="lazy" @error="failed = true" />
    <div v-else class="fallback studs" :style="{ '--c': color }" role="img" :aria-label="`${name || setNum}（暂无图片）`">
      <span>{{ setNum }}</span>
    </div>
  </div>
</template>

<style scoped>
.setimg { position: relative; width: 100%; height: 100%; display: grid; place-items: center; background: #fff; overflow: hidden; }
img { max-width: 100%; max-height: 100%; object-fit: contain; }
.fallback { --s: 28px; width: 100%; height: 100%; display: grid; place-items: center; }
.fallback span {
  padding: 6px 12px; border-radius: 4px; background: rgba(255,255,255,.92); color: var(--ink);
  font: 800 14px/1 var(--font-num); box-shadow: 0 2px 0 rgba(0,0,0,.2);
}
</style>
