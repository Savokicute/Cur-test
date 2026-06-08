// src/services/wechat.js
import api from './api';

// 获取微信公众号列表
export const getWechatMps = (params = {}) => {
  return api.get('/wechat/mps', { params });
};

// 搜索微信公众号
export const searchWechatMps = (kw, params = {}) => {
  return api.get(`/wechat/mps/search/${kw}`, { params });
};

// 获取单个公众号详情
export const getWechatMp = (mpId) => {
  return api.get(`/wechat/mps/${mpId}`);
};

// 获取微信文章列表
export const getWechatArticles = (params = {}) => {
  return api.get('/wechat/articles', { params });
};

// 获取微信文章详情
export const getWechatArticle = (articleId, includeContent = false) => {
  return api.get(`/wechat/articles/${articleId}`, {
    params: { include_content: includeContent }
  });
};

// 标记文章为已读
export const markWechatArticleRead = (articleId, isRead = true) => {
  return api.put(`/wechat/articles/${articleId}/read`, {}, {
    params: { is_read: isRead }
  });
};

// 收藏/取消收藏文章
export const markWechatArticleFavorite = (articleId, isFavorite = true) => {
  return api.put(`/wechat/articles/${articleId}/favorite`, {}, {
    params: { is_favorite: isFavorite }
  });
};

// 刷新文章
export const refreshWechatArticle = (articleId) => {
  return api.post(`/wechat/articles/${articleId}/refresh`);
};

// 获取刷新任务状态
export const getWechatRefreshTask = (taskId) => {
  return api.get(`/wechat/articles/refresh/tasks/${taskId}`);
};

// 获取服务状态
export const getWechatStatus = () => {
  return api.get('/wechat/status');
};
