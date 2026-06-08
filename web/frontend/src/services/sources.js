// src/services/sources.js
import api from './api';

// 热榜源
export const getHotSources = () => api.get('/sources/hot-sources');
export const updateHotSources = (data) => api.put('/sources/hot-sources', data);
export const updateHotSource = (sourceId, data) => api.put(`/sources/hot-sources/${sourceId}`, data);

// 平台状态与重试
export const getPlatformStatus = () => api.get('/sources/hot-sources/status');
export const retryPlatform = (platformId, mode = 'quick') =>
  api.post(`/sources/hot-sources/${platformId}/retry`, { mode });

// 网站源（RSS）
export const getWebsiteSources = () => api.get('/sources/website-sources');
export const addWebsiteSource = (source) => api.post('/sources/website-sources', source);
export const updateWebsiteSource = (sourceId, source) => api.put(`/sources/website-sources/${sourceId}`, source);
export const deleteWebsiteSource = (sourceId) => api.delete(`/sources/website-sources/${sourceId}`);

// 公众号源
export const getWechatMpsSources = () => api.get('/sources/wechat-mps');
export const addWechatMp = (feed) => api.post('/sources/wechat-mps', feed);
export const updateWechatMp = (feedId, feed) => api.put(`/sources/wechat-mps/${feedId}`, feed);
export const deleteWechatMp = (feedId) => api.delete(`/sources/wechat-mps/${feedId}`);
export const searchWechatMps = (keyword) => api.post('/sources/wechat-mps/search', { keyword });
export const triggerWechatFetch = (feedId) => api.post(`/sources/wechat-mps/${feedId}/fetch`);

// 浏览器配置
export const getBrowserProfiles = () => api.get('/sources/browser-profiles');
export const createBrowserProfile = (profile) => api.post('/sources/browser-profiles', profile);
export const updateBrowserProfile = (profileId, profile) => api.put(`/sources/browser-profiles/${profileId}`, profile);
export const deleteBrowserProfile = (profileId) => api.delete(`/sources/browser-profiles/${profileId}`);

// 关联管理
export const getSourceAssociations = () => api.get('/sources/associations');
export const setGlobalDefault = (profileId) => api.post('/sources/associations/set-global-default', { profile_id: profileId });
