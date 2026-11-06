<script setup>
// 颜色以 1×1 小砖表示，rgb 为后端返回的十六进制色值
defineProps({ rgb: String, name: String })
</script>

<template>
  <span class="colorchip">
    <i :style="{ background: rgb ? `#${rgb.replace('#', '')}` : '#ccc' }" aria-hidden="true" />
    {{ name }}
  </span>
</template>

<style scoped>
.colorchip { display: inline-flex; align-items: center; gap: 8px; }
i {
  position: relative; flex: none; width: 18px; height: 16px; border-radius: 3px;
  box-shadow: inset 0 -3px 0 rgba(0,0,0,.18), 0 0 0 1px rgba(0,0,0,.15);
}
i::after {
  content: ""; position: absolute; left: 50%; top: -3px; width: 9px; height: 4px; transform: translateX(-50%);
  border-radius: 2px 2px 0 0; background: inherit; box-shadow: 0 0 0 1px rgba(0,0,0,.12);
}
</style>
