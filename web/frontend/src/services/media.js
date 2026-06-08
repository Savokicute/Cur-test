import api from './api';

/**
 * 获取媒体文件 URL
 * @param {string} path - 媒体文件路径
 * @returns {string} 完整的媒体文件 URL
 */
export const getMediaUrl = (path) => {
  if (!path) return '';
  // 如果已经是完整 URL，直接返回
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  return `/api/media/files/${encodeURIComponent(path)}`;
};

/**
 * 获取文章关联的媒体文件列表
 * @param {string} articleId - 文章 ID
 * @returns {Promise} 媒体文件列表
 */
export const getMediaItems = (articleId) => {
  return api.get(`/media/items?article_id=${encodeURIComponent(articleId)}`);
};
