import { createRouter, createWebHashHistory } from 'vue-router'

export default createRouter({
  history: createWebHashHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', redirect: '/sets' },
    { path: '/sets', component: () => import('./views/SetExplore.vue'), meta: { nav: 'sets' } },
    { path: '/sets/:setNum', component: () => import('./views/SetDetail.vue'), meta: { nav: 'sets' } },
    { path: '/tasks', component: () => import('./views/Tasks.vue'), meta: { nav: 'tasks' } },
    { path: '/tasks/:id', component: () => import('./views/TaskDetail.vue'), meta: { nav: 'tasks' } },
    { path: '/stock', component: () => import('./views/StockReceipts.vue'), meta: { nav: 'stock' } },
    { path: '/records', component: () => import('./views/Records.vue'), meta: { nav: 'records' } },
    { path: '/:pathMatch(.*)*', redirect: '/sets' },
  ],
})
