/**
 * 关键词配置服务
 * 
 * 提供关键词配置的读取、保存、解析和验证功能
 */

import api from './api';

/**
 * 获取关键词配置文件内容
 */
export async function getKeywordConfig() {
  return api.get('/keywords/config');
}

/**
 * 保存关键词配置
 * @param {string} content - 配置文件内容
 * @param {boolean} createBackup - 是否创建备份（默认true）
 */
export async function saveKeywordConfig(content, createBackup = true) {
  return api.put('/keywords/config', {
    content,
    create_backup: createBackup,
  });
}

/**
 * 获取解析后的关键词配置（结构化数据）
 */
export async function getParsedKeywords() {
  return api.get('/keywords/parsed');
}

/**
 * 验证关键词配置语法
 * @param {string} content - 要验证的配置内容
 */
export async function validateKeywordConfig(content) {
  return api.post('/keywords/validate', { content });
}

/**
 * 测试标题是否匹配关键词配置
 * @param {string} title - 要测试的标题
 * @param {boolean} useGlobalFilter - 是否使用全局过滤（默认true）
 */
export async function testKeywordMatch(title, useGlobalFilter = true) {
  return api.post('/keywords/test-match', null, {
    params: {
      title,
      use_global_filter: useGlobalFilter,
    },
  });
}

/**
 * 批量匹配关键词（热榜集成专用）
 * @param {string[]} titles - 标题数组
 * @param {boolean} useGlobalFilter - 是否使用全局过滤（默认true）
 */
export async function batchMatchKeywords(titles, useGlobalFilter = true) {
  return api.post('/keywords/batch-match', {
    titles,
    use_global_filter: useGlobalFilter,
  });
}

/**
 * 获取配置备份列表
 */
export async function listBackups() {
  return api.get('/keywords/backups');
}
