import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { guest: true } },
    { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
    { path: '/datasets/:id', name: 'DatasetDetail', component: () => import('../views/DatasetDetail.vue') },
    { path: '/upload', name: 'Upload', component: () => import('../views/Upload.vue') },
    { path: '/history', name: 'History', component: () => import('../views/History.vue') },
    { path: '/reports', name: 'Reports', component: () => import('../views/Reports.vue') },
    { path: '/reports/:id', name: 'ReportDetail', component: () => import('../views/ReportDetail.vue') },
    { path: '/users', name: 'Users', component: () => import('../views/Users.vue') },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (!token && to.path !== '/login') {
    next('/login')
  } else if (token && to.path === '/login') {
    next('/')
  } else {
    next()
  }
})

export default router
