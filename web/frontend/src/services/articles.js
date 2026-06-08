// src/services/articles.js
import api from './api';

export const getArticles = (params = {}) => {
  return api.get('/articles', { params });
};

export const getArticleById = (urlNorm, params = {}) => {
  const queryParams = new URLSearchParams(params).toString();
  const queryString = queryParams ? `?${queryParams}` : '';
  return api.get(`/articles/${encodeURIComponent(urlNorm)}${queryString}`);
};

export const refetchArticle = (urlNorm) => {
  return api.post(`/articles/${encodeURIComponent(urlNorm)}/refetch`);
};
