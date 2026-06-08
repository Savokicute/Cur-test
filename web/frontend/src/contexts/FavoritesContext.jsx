import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { message } from 'antd';

const STORAGE_KEY = 'hotspot-favorites';

const FavoritesContext = createContext(null);

function loadFavorites() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function FavoritesProvider({ children }) {
  const [favorites, setFavorites] = useState(loadFavorites);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
  }, [favorites]);

  // 添加收藏（支持标签和备注）
  const addFavorite = (item, tags = [], remark = '') => {
    const newFavorite = {
      id: item.id || item.url_norm || item.url,
      title: item.title || item.title_snapshot,
      type: item.platform_name ? 'hotspot' : (item.platform === 'wechat' ? 'wechat' : 'article'),
      platform: item.platform_name || item.platform || '未知平台',
      content: item.content || item.markdown,
      tags,
      remark,
      addedAt: new Date().toISOString(),
      url_norm: item.url_norm,
      url: item.url_norm || item.url,
      ...item
    };

    // 检查是否已存在
    const exists = favorites.some(fav => fav.id === newFavorite.id);
    if (exists) {
      message.warning('该内容已收藏');
      return false;
    }

    setFavorites(prev => [newFavorite, ...prev]);
    message.success('收藏成功');
    return true;
  };

  // 移除收藏
  const removeFavorite = (id) => {
    setFavorites(prev => prev.filter(fav => fav.id !== id));
    message.success('已取消收藏');
  };

  // 检查是否已收藏
  const isFavorite = (id) => {
    return favorites.some(fav => fav.id === id || fav.url === id);
  };

  // 更新收藏备注
  const updateRemark = (id, remark) => {
    setFavorites(prev => 
      prev.map(fav => 
        fav.id === id ? { ...fav, remark } : fav
      )
    );
    message.success('备注已更新');
  };

  // 更新收藏标签
  const updateTags = (id, tags) => {
    setFavorites(prev => 
      prev.map(fav => 
        fav.id === id ? { ...fav, tags } : fav
      )
    );
    message.success('标签已更新');
  };

  const value = useMemo(
    () => ({
      favorites,
      addFavorite,
      removeFavorite,
      isFavorite,
      updateRemark,
      updateTags,
    }),
    [favorites],
  );

  return (
    <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>
  );
}

export function useFavorites() {
  const ctx = useContext(FavoritesContext);
  if (!ctx) throw new Error('useFavorites must be used within FavoritesProvider');
  return ctx;
}
