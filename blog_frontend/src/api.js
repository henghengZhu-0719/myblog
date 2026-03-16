import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// Add a request interceptor to include the token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login = (username, password) => api.post('/auth/login', { username, password });
export const register = (username, password, avatar) => api.post('/users', { username, password, avatar });
export const getArticles = (username, page = 1, size = 10) =>
  api.get(`/users/${username}/articles`, { params: { page, size } });
export const getArticleDetail = (id) => api.get(`/articles/${id}`);
export const publishArticle = (data) => api.post('/articles', data);
export const searchUsers = (searchname, page = 1, size = 10) => api.get('/users', { params: { searchname, page, size } });
export const getUserById = (id) => api.get(`/users/${id}`);
export const deleteArticle = (id) => api.delete(`/articles/${id}`);
export const editArticle = (id, data) => api.put(`/articles/${id}`, data);
export const getJobs = (date, range = 'weekly') => api.get('/jobs', { params: { query_date: date, range } });
export const triggerCrawl = () => api.post('/actions/crawl');
export const getCrawlResult = () => api.get('/actions/crawl/result');
export const analyzeBills = (formData) => api.post('/actions/bill', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});
export const createBill = (data) => api.post('/bills', data);
export const getBills = (date, range = 'weekly') => api.get('/bills', { params: { query_date: date, range } });
export const crawlBoss = (urls) => api.post('/boss/crawl', urls);
export const createBoss = (data) => api.post('/boss', data);

export default api;
