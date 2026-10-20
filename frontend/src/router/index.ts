import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/api-access', name: 'api-access', meta: { bare: true }, component: () => import('../views/ApiAccessView.vue') },
    { path: '/iframes', name: 'iframes', meta: { bare: true }, component: () => import('../views/IframeLibraryView.vue') },
    { path: '/widgets/penguin', name: 'penguin-widget', meta: { bare: true }, component: () => import('../views/PenguinWidgetView.vue') },
    { path: '/tools/:slug', name: 'tool', component: () => import('../views/ToolView.vue') },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue') },
  ],
})

export default router
