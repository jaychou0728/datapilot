import axios from 'axios'
import { ElMessage } from 'element-plus'

const client = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (res) => {
    const data = res.data
    if (data.code !== 0) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data.data
  },
  (err) => {
    ElMessage.error('网络异常，请稍后重试')
    return Promise.reject(err)
  }
)

export default client
