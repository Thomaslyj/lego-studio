<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import IntroScene from './intro/IntroScene.vue'
import legoLogo from './assets/lego-logo.svg'

const route = useRoute()
const showIntro = ref(true)
const nav = [
  { key: 'sets', to: '/sets', label: '套装探索' },
  { key: 'tasks', to: '/tasks', label: '组装任务' },
  { key: 'stock', to: '/stock', label: '库存与入库' },
  { key: 'records', to: '/records', label: '单据记录' },
]
</script>

<template>
  <IntroScene v-if="showIntro" @enter="showIntro = false" />
  <div class="shell" :aria-hidden="showIntro">
    <header class="topbar studs">
      <div class="topbar-inner">
        <RouterLink to="/sets" class="brand" aria-label="返回套装探索">
          <img class="brand-mark" :src="legoLogo" alt="LEGO" />
          <span class="brand-text">组装工作室<small>备料与库存</small></span>
        </RouterLink>
        <nav class="mainnav" aria-label="主导航">
          <RouterLink
            v-for="n in nav" :key="n.key" :to="n.to"
            class="navlink" :class="{ active: route.meta.nav === n.key }"
            :aria-current="route.meta.nav === n.key ? 'page' : undefined"
          >
            <span v-for="(ch, i) in n.label" :key="i" class="navtile" :class="{ amp: ch === '与' }" aria-hidden="true">{{ ch }}</span>
            <span class="navword">{{ n.label }}</span>
          </RouterLink>
        </nav>
      </div>
    </header>
    <main>
      <RouterView v-if="!showIntro" />
    </main>
  </div>
</template>

<style scoped>
.topbar {
  --c: var(--lego-yellow); --s: 22px;
  position: sticky; top: 0; z-index: 20;
  box-shadow: 0 3px 0 var(--lego-yellow-deep), 0 8px 18px -10px rgba(0,0,0,.35);
}
.topbar-inner {
  max-width: 1280px; margin: 0 auto; padding: 10px 28px;
  display: flex; align-items: center; gap: 28px;
}
.brand { display: flex; align-items: center; gap: 12px; text-decoration: none; }
.brand-mark { display: block; width: 52px; height: 52px; }
.brand-text { display: flex; flex-direction: column; font: 800 18px/1.1 var(--font-body); color: var(--ink); }
.brand-text small { font-size: 12px; font-weight: 600; color: rgba(27,27,27,.7); margin-top: 3px; }

.mainnav { display: flex; gap: 18px; margin-left: auto; flex-wrap: wrap; }
.navlink {
  display: flex; gap: 3px; text-decoration: none; padding: 6px 4px 8px;
  transition: transform .1s ease;
}
.navtile {
  display: grid; place-items: center; width: 30px; height: 32px;
  background: #fff; color: var(--ink); border-radius: 4px;
  font: 800 15px/1 var(--font-body);
  box-shadow: 0 3px 0 #C9B000, 0 4px 6px -2px rgba(0,0,0,.25);
  transition: transform .1s ease, box-shadow .1s ease, background .15s;
}
.navtile.amp { width: 22px; background: transparent; box-shadow: none; font-size: 13px; font-weight: 700; }
.navlink:hover .navtile:not(.amp) { transform: translateY(-2px); box-shadow: 0 5px 0 #C9B000, 0 8px 10px -4px rgba(0,0,0,.3); }
.navlink:active .navtile:not(.amp) { transform: translateY(2px); box-shadow: 0 1px 0 #C9B000, inset 0 2px 3px rgba(0,0,0,.2); }
.navlink.active .navtile:not(.amp) { background: var(--lego-red); color: #fff; box-shadow: 0 3px 0 var(--lego-red-deep), 0 4px 6px -2px rgba(0,0,0,.3); }
.navlink:focus-visible { outline: 3px solid var(--lego-blue); outline-offset: 2px; border-radius: 6px; }
/* 桌面用逐字方砖，文字只给读屏；窄屏改为每项一块整砖 */
.navword { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 900px) {
  .topbar-inner { flex-wrap: wrap; gap: 10px 18px; padding: 10px 14px; }
  .mainnav { margin-left: 0; gap: 10px; width: 100%; justify-content: space-between; }
  .navtile { width: 22px; height: 26px; font-size: 13px; }
  .navtile.amp { width: 14px; }
  .brand-mark { width: 42px; height: 42px; }
}
@media (max-width: 720px) {
  .mainnav { gap: 6px; flex-wrap: nowrap; }
  .navlink { flex: 1; padding: 4px 0 6px; }
  .navtile { display: none; }
  .navword {
    position: static; width: 100%; height: 34px; overflow: visible; clip: auto;
    display: grid; place-items: center; padding: 0 4px; border-radius: 4px;
    background: #fff; color: var(--ink); font: 800 13px/1 var(--font-body);
    box-shadow: 0 3px 0 #C9B000, 0 4px 6px -2px rgba(0,0,0,.25);
    transition: transform .1s ease, box-shadow .1s ease;
  }
  .navlink:active .navword { transform: translateY(2px); box-shadow: 0 1px 0 #C9B000, inset 0 2px 3px rgba(0,0,0,.2); }
  .navlink.active .navword { background: var(--lego-red); color: #fff; box-shadow: 0 3px 0 var(--lego-red-deep), 0 4px 6px -2px rgba(0,0,0,.3); }
}
</style>
