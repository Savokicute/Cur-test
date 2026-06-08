// src/services/aiAnalysis.js
/**
 * AI 分析服务 - API 调用封装
 *
 * 提供完整的 AI 分析功能接口：
 * - 配置管理（CRUD）
 * - 任务触发和监控
 * - 报告查询和管理
 * - 模板管理
 * - 统计信息获取
 */

import api from './api';

// ========== 配置管理 ==========

/**
 * 获取分析配置列表（分页）
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码 (默认 1)
 * @param {number} params.pageSize - 每页数量 (默认 20)
 * @param {string} params.triggerType - 触发类型筛选
 * @param {boolean} params.isActive - 是否启用筛选
 */
export const getAnalysisConfigs = (params = {}) => {
  return api.get('/ai-analysis/configs', { params });
};

/**
 * 创建分析配置
 * @param {Object} data - 配置数据
 * @param {string} data.name - 配置名称
 * @param {string} data.promptTemplate - 提示词模板
 * @param {string} data.description - 描述（可选）
 * @param {string} data.modelName - 模型名称（默认 gpt-4）
 * @param {number} data.temperature - 温度参数 (0-1)
 * @param {number} data.maxTokens - 最大token数
 * @param {string} data.triggerType - 触发类型
 * @param {string} data.scheduleCron - 定时表达式（可选）
 * @param {boolean} data.isActive - 是否启用
 */
export const createAnalysisConfig = (data) => {
  return api.post('/ai-analysis/configs', {
    name: data.name,
    description: data.description,
    prompt_template: data.promptTemplate || data.prompt_template,
    model_name: data.modelName || data.model_name || 'gpt-4',
    temperature: data.temperature ?? 0.7,
    max_tokens: data.maxTokens ?? data.max_tokens ?? 4096,
    trigger_type: data.triggerType || data.trigger_type || 'manual',
    schedule_cron: data.scheduleCron || data.schedule_cron,
    is_active: data.isActive ?? data.is_active ?? true,
  });
};

/**
 * 更新分析配置
 * @param {number} id - 配置ID
 * @param {Object} data - 要更新的字段
 */
export const updateAnalysisConfig = (id, data) => {
  // 转换驼峰命名为下划线命名
  const payload = {};
  if (data.name !== undefined) payload.name = data.name;
  if (data.description !== undefined) payload.description = data.description;
  if (data.promptTemplate !== undefined || data.prompt_template !== undefined)
    payload.prompt_template = data.promptTemplate || data.prompt_template;
  if (data.modelName !== undefined || data.model_name !== undefined)
    payload.model_name = data.modelName || data.model_name;
  if (data.temperature !== undefined) payload.temperature = data.temperature;
  if (data.maxTokens !== undefined || data.max_tokens !== undefined)
    payload.max_tokens = data.maxTokens ?? data.max_tokens;
  if (data.triggerType !== undefined || data.trigger_type !== undefined)
    payload.trigger_type = data.triggerType || data.trigger_type;
  if (data.scheduleCron !== undefined || data.schedule_cron !== undefined)
    payload.schedule_cron = data.scheduleCron || data.schedule_cron;
  if (data.isActive !== undefined || data.is_active !== undefined)
    payload.is_active = data.isActive ?? data.is_active;

  return api.put(`/ai-analysis/configs/${id}`, payload);
};

/**
 * 删除分析配置
 * @param {number} id - 配置ID
 */
export const deleteAnalysisConfig = (id) => {
  return api.delete(`/ai-analysis/configs/${id}`);
};

/**
 * 获取单个配置详情
 * @param {number} id - 配置ID
 */
export const getAnalysisConfigDetail = (id) => {
  return api.get(`/ai-analysis/configs/${id}`);
};

// ========== 分析任务 ==========

/**
 * 触发AI分析任务（异步执行）
 * @param {number} configId - 配置ID
 * @param {Object} params - 输入参数（可选）
 * @returns {Promise<{reportId: number}>} 返回报告ID用于轮询状态
 */
export const triggerAnalysis = (configId, params = {}) => {
  return api.post('/ai-analysis/trigger', {
    config_id: configId,
    params: params,
  });
};

// ========== 报告管理 ==========

/**
 * 获取分析报告列表（分页）
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.pageSize - 每页数量
 * @param {number} params.configId - 配置ID筛选
 * @param {string} params.status - 状态筛选: pending/running/completed/failed
 * @param {string} params.startDate - 开始日期 (YYYY-MM-DD)
 * @param {string} params.endDate - 结束日期 (YYYY-MM-DD)
 */
export const getAnalysisReports = (params = {}) => {
  const queryParams = {};
  if (params.page !== undefined) queryParams.page = params.page;
  if (params.pageSize !== undefined) queryParams.page_size = params.pageSize;
  if (params.configId !== undefined) queryParams.config_id = params.configId;
  if (params.status !== undefined) queryParams.status = params.status;
  if (params.startDate !== undefined) queryParams.start_date = params.startDate;
  if (params.endDate !== undefined) queryParams.end_date = params.endDate;

  return api.get('/ai-analysis/reports', { params: queryParams });
};

/**
 * 获取单个报告详情（包含完整内容）
 * @param {number} reportId - 报告ID
 */
export const getAnalysisReport = (reportId) => {
  return api.get(`/ai-analysis/reports/${reportId}`);
};

/**
 * 删除分析报告
 * @param {number} reportId - 报告ID
 */
export const deleteAnalysisReport = (reportId) => {
  return api.delete(`/ai-analysis/reports/${reportId}`);
};

/**
 * 轮询报告状态（用于异步分析任务）
 * @param {number} reportId - 报告ID
 * @param {Function} onStatusChange - 状态变化回调
 * @param {number} interval - 轮询间隔毫秒数（默认 3000ms）
 * @param {number} maxAttempts - 最大尝试次数（默认 60次，约3分钟）
 * @returns {Promise<void>}
 */
export const pollReportStatus = async (
  reportId,
  onStatusChange,
  interval = 3000,
  maxAttempts = 60
) => {
  let attempts = 0;

  const poll = async () => {
    attempts++;
    try {
      const response = await getAnalysisReport(reportId);

      if (response?.success && response?.data) {
        const report = response.data;

        // 回调通知状态变化
        if (onStatusChange) {
          onStatusChange(report);
        }

        // 如果已完成或失败，停止轮询
        if (report.status === 'completed' || report.status === 'failed') {
          return; // 成功完成
        }

        // 继续轮询
        if (attempts < maxAttempts) {
          setTimeout(poll, interval);
        } else {
          // 超时
          if (onStatusChange) {
            onStatusChange({ ...report, status: 'timeout' });
          }
        }
      }
    } catch (error) {
      console.error('轮询报告状态失败:', error);
      if (attempts < maxAttempts) {
        setTimeout(poll, interval);
      }
    }
  };

  // 开始轮询
  await poll();
};

// ========== 模板管理 ==========

/**
 * 获取预设模板列表
 * @param {Object} params - 查询参数
 * @param {string} params.category - 分类筛选
 * @param {boolean} params.onlySystem - 是否只返回系统预设（默认 true）
 */
export const getSystemTemplates = (params = {}) => {
  const queryParams = { only_system: true };
  if (params.category !== undefined) queryParams.category = params.category;
  if (params.onlySystem !== undefined) queryParams.only_system = params.onlySystem;

  return api.get('/ai-analysis/templates', { params: queryParams });
};

/**
 * 使用模板创建配置
 * @param {number} templateId - 模板ID
 * @param {Object} options - 选项
 * @param {string} options.customName - 自定义配置名称
 * @param {Object} options.customParams - 自定义参数
 */
export const useTemplate = (templateId, options = {}) => {
  return api.post('/ai-analysis/templates/use', {
    template_id: templateId,
    custom_name: options.customName,
    custom_params: options.customParams,
  });
};

// ========== 统计信息 ==========

/**
 * 获取AI分析统计信息
 * @returns {Promise<Object>} 统计数据
 */
export const getAnalysisStats = () => {
  return api.get('/ai-analysis/stats');
};

// ========== 导出功能 ==========

/**
 * 导出报告为 Markdown 文件
 * @param {Object} report - 报告数据
 * @param {string} filename - 文件名（可选）
 */
export const exportAsMarkdown = (report, filename) => {
  const content = report.content || '';
  const name = filename || `AI分析报告_${report.id}_${new Date().toISOString().slice(0, 10)}.md`;

  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * 导出报告为文本文件
 * @param {Object} report - 报告数据
 * @param {string} filename - 文件名（可选）
 */
export const exportAsText = (report, filename) => {
  // 移除 Markdown 格式标记，转换为纯文本
  let content = report.content || '';

  // 简单的 Markdown 到纯文本转换
  content = content
    .replace(/^#{1,6}\s+/gm, '')     // 移除标题标记
    .replace(/\*\*(.+?)\*\*/g, '$1')   // 移除粗体
    .replace(/\*(.+?)\*/g, '$1')       // 移除斜体
    .replace(/`(.+?)`/g, '$1')         // 移除代码
    .replace(/\[(.+?)\]\(.+?\)/g, '$1') // 移除链接，保留文字
    .replace(/^[-*+]\s+/gm, '• ')      // 列表项转为圆点
    .replace(/^\d+\.\s+/gm, '')        // 有序列表移除编号
    .replace(/^>\s+/gm, '')            // 移除引用
    .replace(/---+/g, '---')           // 分隔线
    .trim();

  const name = filename || `AI分析报告_${report.id}.txt`;

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
