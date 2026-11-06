import axios from 'axios'

const http = axios.create({ baseURL: (import.meta.env.VITE_API_BASE || '') + '/api', timeout: 20000 })

// 统一把后端 detail 转成中文提示
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    let message
    if (typeof detail === 'string') message = detail
    else if (status === 404) message = '记录不存在'
    else if (status === 422) message = '输入不合法，请检查数量等字段'
    else if (!err.response) message = '无法连接服务器，请检查后端是否启动'
    else message = `请求失败（${status}）`
    return Promise.reject(Object.assign(new Error(message), { status }))
  },
)

let themesPromise
export const api = {
  themes: () => http.get('/themes'),
  // 主题很少变化，页面间共用一次请求
  themesCached: () => (themesPromise ||= http.get('/themes').catch((e) => { themesPromise = null; throw e })),
  sets: (params) => http.get('/sets', { params }),
  setVersions: (setNum) => http.get(`/sets/${encodeURIComponent(setNum)}/versions`),
  setDetail: (setNum, params) => http.get(`/sets/${encodeURIComponent(setNum)}`, { params }),
  stock: (params) => http.get('/stock', { params }),

  tasks: () => http.get('/tasks'),
  task: (id) => http.get(`/tasks/${id}`),
  createTask: (body) => http.post('/tasks', body),
  updateTask: (id, body) => http.put(`/tasks/${id}`, body),
  deleteTask: (id) => http.delete(`/tasks/${id}`),
  issueTask: (id) => http.post(`/tasks/${id}/issue`),

  issues: () => http.get('/issues'),
  issue: (id) => http.get(`/issues/${id}`),

  receipts: () => http.get('/receipts'),
  receipt: (id) => http.get(`/receipts/${id}`),
  createReceipt: (items) => http.post('/receipts', { items }),
  updateReceipt: (id, items) => http.put(`/receipts/${id}`, { items }),
  deleteReceipt: (id) => http.delete(`/receipts/${id}`),
  confirmReceipt: (id) => http.post(`/receipts/${id}/confirm`),
}
