// src/services/notifications.js
import api from './api';

/**
 * 通知管理 API 服务
 */
const notificationsApi = {
  /**
   * 获取订阅列表
   */
  getSubscriptions: async (params = {}) => {
    const { is_active, subscription_type, limit = 50, offset = 0 } = params;
    const queryParams = new URLSearchParams();

    if (is_active !== undefined) queryParams.append('is_active', is_active);
    if (subscription_type) queryParams.append('subscription_type', subscription_type);
    if (limit) queryParams.append('limit', limit);
    if (offset) queryParams.append('offset', offset);

    return api.get(`/notifications/subscriptions?${queryParams.toString()}`);
  },

  /**
   * 获取单个订阅详情
   */
  getSubscription: async (id) => {
    return api.get(`/notifications/subscriptions/${id}`);
  },

  /**
   * 创建订阅
   */
  createSubscription: async (data) => {
    return api.post('/notifications/subscriptions', data);
  },

  /**
   * 更新订阅
   */
  updateSubscription: async (id, data) => {
    return api.put(`/notifications/subscriptions/${id}`, data);
  },

  /**
   * 删除订阅
   */
  deleteSubscription: async (id) => {
    return api.delete(`/notifications/subscriptions/${id}`);
  },

  /**
   * 手动触发订阅
   */
  triggerSubscription: async (id) => {
    return api.post(`/notifications/subscriptions/${id}/trigger`);
  },

  /**
   * 测试订阅发送
   */
  testSubscription: async (id) => {
    return api.post(`/notifications/subscriptions/${id}/test`);
  },

  /**
   * 获取通知日志列表
   */
  getNotificationLogs: async (params = {}) => {
    const { subscription_id, status, limit = 50, offset = 0 } = params;
    const queryParams = new URLSearchParams();

    if (subscription_id) queryParams.append('subscription_id', subscription_id);
    if (status) queryParams.append('status', status);
    if (limit) queryParams.append('limit', limit);
    if (offset) queryParams.append('offset', offset);

    return api.get(`/notifications/logs?${queryParams.toString()}`);
  },

  /**
   * 获取通知统计信息
   */
  getNotificationStats: async () => {
    return api.get('/notifications/stats');
  },

  /**
   * 获取通知模板列表
   */
  getNotificationTemplates: async () => {
    return api.get('/notifications/templates');
  },
};

export default notificationsApi;
