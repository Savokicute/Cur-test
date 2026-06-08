// src/services/hotspots.js
import api from './api';

export const getHotspots = (params = {}) => {
  return api.get('/hotspots', { params });
};

export const getHotspotDates = () => {
  return api.get('/hotspots/dates');
};
