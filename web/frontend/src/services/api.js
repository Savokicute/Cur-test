// src/services/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// 请求拦截器：自动注入认证信息（X-Session-Token + X-Username）
api.interceptors.request.use(
  (config) => {
    // 注入 Session Token（独立认证体系）
    const savedToken = localStorage.getItem('trendradar_token');
    if (savedToken) {
      config.headers['X-Session-Token'] = savedToken;
    }

    // 注入用户名（兼容旧接口）
    const savedUser = localStorage.getItem('trendradar_user');
    if (savedUser) {
      try {
        const userInfo = JSON.parse(savedUser);
        if (userInfo.username) {
          config.headers['X-Username'] = userInfo.username;
        }
      } catch (e) {
        // 解析失败则忽略
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.message;

    if (status === 401) {
      console.warn('[API] 未登录或登录已过期:', detail);
      // 可在此处跳转到登录页
    } else if (status === 403) {
      console.warn('[API] 权限不足:', detail);
    } else if (status >= 500) {
      console.error('[API] 服务器错误:', detail);
    } else {
      console.error('[API Error]', detail);
    }

    return Promise.reject(error);
  }
);

// ========== 用户管理 API ==========

export const usersApi = {
  /** 用户列表（分页/搜索/筛选/排序） */
  getList(params = {}) {
    return api.get('/users', { params });
  },

  /** 当前用户信息（含角色+权限） */
  getMe() {
    return api.get('/users/me');
  },

  /** 用户详情 */
  getDetail(username) {
    return api.get(`/users/${username}`);
  },

  /** 编辑用户信息（昵称/邮箱/备注） */
  update(username, data) {
    return api.put(`/users/${username}`, data);
  },

  /** 修改用户角色 */
  updateRole(username, role) {
    return api.put(`/users/${username}/role`, { role });
  },

  /** 禁用/启用用户 */
  updateStatus(username, is_active) {
    return api.put(`/users/${username}/status`, { is_active });
  },

  /** 批量修改角色 */
  batchUpdateRole(usernames, role) {
    return api.post('/users/batch-role', { usernames, role });
  },

  /** 批量禁用/启用 */
  batchUpdateStatus(usernames, is_active) {
    return api.post('/users/batch-status', { usernames, is_active });
  },

  /** 操作日志列表 */
  getLogs(params = {}) {
    return api.get('/users/logs', { params });
  },

  /** 当前用户的权限列表 */
  getMyPermissions() {
    return api.get('/users/auth/permissions');
  },

  /** 角色元数据（下拉框用） */
  getRolesMeta() {
    return api.get('/users/meta/roles');
  },

  /** 权限元数据（展示用） */
  getPermissionsMeta(category) {
    const params = category ? { category } : {};
    return api.get('/users/meta/permissions', { params });
  },
};

export default api;
