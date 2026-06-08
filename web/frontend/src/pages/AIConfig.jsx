import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Tabs,
  Switch,
  Input,
  InputNumber,
  Select,
  Form,
  message,
  Spin,
  Space,
  Tooltip,
  Typography,
  Tag,
} from 'antd';
import {
  RobotOutlined,
  ApiOutlined,
  FilterOutlined,
  ExperimentOutlined,
  TranslationOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { getConfig, updateConfigModule } from '../services/config';

const { Text } = Typography;

// ==================== 各模块字段定义 ====================

const AI_FIELDS = [
  { key: 'model', label: '模型名称', type: 'input', description: '使用的 AI 模型名称，如 gpt-4o、claude-3' },
  { key: 'api_base', label: 'API 地址', type: 'input', description: 'AI 服务 API 的基础 URL' },
  { key: 'api_key', label: 'API 密钥', type: 'password', description: '用于认证的 API Key，将以密文显示' },
  { key: 'timeout', label: '超时时间(秒)', type: 'number', description: '请求超时时间，单位秒', min: 10, max: 600 },
  { key: 'temperature', label: 'Temperature', type: 'number', description: '生成随机性，值越高输出越随机', min: 0, max: 2, step: 0.1 },
  { key: 'max_tokens', label: '最大 Token 数', type: 'number', description: '单次请求最大生成的 token 数量', min: 100, max: 32000 },
  { key: 'num_retries', label: '重试次数', type: 'number', description: '请求失败后的自动重试次数', min: 0, max: 5 },
];

const AI_FILTER_FIELDS = [
  { key: 'batch_size', label: '批处理大小', type: 'number', description: '每批处理的条目数量', min: 10, max: 1000 },
  { key: 'batch_interval', label: '批处理间隔(秒)', type: 'number', description: '批次之间的等待间隔，单位秒', min: 1, max: 60 },
  { key: 'min_score', label: '最低评分', type: 'number', description: '筛选通过的最低分数阈值', min: 0, max: 1, step: 0.1 },
  { key: 'reclassify_threshold', label: '重分类阈值', type: 'number', description: '触发重分类的置信度阈值', min: 0, max: 1, step: 0.1 },
  { key: 'prompt_file', label: 'Prompt 文件路径', type: 'input', description: '筛选分类所用的 prompt 模板文件路径' },
  { key: 'extract_prompt_file', label: '提取 Prompt 路径', type: 'input', description: '信息提取所用的 prompt 模板文件路径' },
  { key: 'update_tags_prompt_file', label: '标签更新 Prompt 路径', type: 'input', description: '标签更新所用的 prompt 模板文件路径' },
];

const AI_ANALYSIS_FIELDS = [
  { key: 'enabled', label: '启用分析', type: 'switch', description: '是否开启 AI 分析功能' },
  { key: 'language', label: '分析语言', type: 'select', description: '分析报告的目标语言',
    options: [
      { value: 'Chinese', label: 'Chinese（中文）' },
      { value: 'English', label: 'English（英文）' },
    ],
  },
  { key: 'mode', label: '分析模式', type: 'select', description: 'follow_report: 跟随报告模式; standalone: 独立分析模式',
    options: [
      { value: 'follow_report', label: 'follow_report（跟随报告）' },
      { value: 'standalone', label: 'standalone（独立模式）' },
    ],
  },
  { key: 'max_news_for_analysis', label: '最大分析新闻数', type: 'number', description: '单次分析最多处理的新闻条数', min: 10, max: 500 },
  { key: 'include_rss', label: '包含 RSS 新闻', type: 'switch', description: '是否将 RSS 来源的新闻纳入分析范围' },
  { key: 'include_standalone', label: '包含独立来源', type: 'switch', description: '是否将独立抓取的新闻纳入分析范围' },
  { key: 'include_rank_timeline', label: '包含排名时间线', type: 'switch', description: '是否在分析报告中生成排名变化时间线' },
];

const AI_TRANSLATION_FIELDS = [
  { key: 'enabled', label: '启用翻译', type: 'switch', description: '是否开启 AI 自动翻译功能' },
  { key: 'language', label: '目标语言', type: 'input', description: '翻译输出的目标语言，如 English、Japanese' },
  { key: 'scope.hotlist', label: '翻译热榜内容', type: 'switch', description: '是否对热榜抓取的内容进行翻译' },
  { key: 'scope.rss', label: '翻译 RSS 内容', type: 'switch', description: '是否对 RSS 订阅的内容进行翻译' },
  { key: 'scope.standalone', label: '翻译独立来源', type: 'switch', description: '是否对独立抓取的内容进行翻译' },
];

const MODULE_TABS = [
  { key: 'ai', label: 'AI 模型配置', icon: <ApiOutlined />, fields: AI_FIELDS },
  { key: 'ai_filter', label: 'AI 筛选参数', icon: <FilterOutlined />, fields: AI_FILTER_FIELDS },
  { key: 'ai_analysis', label: 'AI 分析功能', icon: <ExperimentOutlined />, fields: AI_ANALYSIS_FIELDS },
  { key: 'ai_translation', label: 'AI 翻译', icon: <TranslationOutlined />, fields: AI_TRANSLATION_FIELDS },
];

export default function AIConfig() {
  const [config, setConfig] = useState({});
  const [activeTab, setActiveTab] = useState('ai');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState({});
  const [lastSavedTime, setLastSavedTime] = useState(null);

  // 加载配置
  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getConfig();
      if (res?.success) {
        setConfig(res.data.parsed || {});
      }
    } catch (e) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  // 保存模块
  const saveModule = async (moduleKey, value) => {
    setSaving((prev) => ({ ...prev, [moduleKey]: true }));
    try {
      const res = await updateConfigModule(moduleKey, value);
      if (res?.success) {
        message.success('配置已保存');
        setLastSavedTime(new Date().toLocaleTimeString());
      }
    } catch (e) {
      message.error('保存失败');
    } finally {
      setSaving((prev) => {
        const next = { ...prev };
        delete next[moduleKey];
        return next;
      });
    }
  };

  // 字段变更：支持嵌套路径（如 scope.hotlist）
  const handleFieldChange = (moduleKey, fieldPath, value) => {
    const current = JSON.parse(JSON.stringify(config[moduleKey] || {}));

    if (fieldPath.includes('.')) {
      const parts = fieldPath.split('.');
      let obj = current;
      for (let i = 0; i < parts.length - 1; i++) {
        if (!obj[parts[i]]) obj[parts[i]] = {};
        obj = obj[parts[i]];
      }
      obj[parts[parts.length - 1]] = value;
    } else {
      current[fieldPath] = value;
    }

    setConfig((prev) => ({ ...prev, [moduleKey]: current }));
    saveModule(moduleKey, current);
  };

  // 读取嵌套字段值
  const getFieldValue = (moduleKey, fieldPath) => {
    try {
      let v = config[moduleKey];
      for (const p of fieldPath.split('.')) {
        if (v && typeof v === 'object') {
          v = v[p];
        } else {
          return undefined;
        }
      }
      return v;
    } catch {
      return undefined;
    }
  };

  // 渲染单个字段控件
  const renderFieldControl = (modKey, field) => {
    const val = getFieldValue(modKey, field.key);

    switch (field.type) {
      case 'switch':
        return (
          <Switch
            size="small"
            checked={val ?? false}
            onChange={(v) => handleFieldChange(modKey, field.key, v)}
            loading={saving[modKey]}
          />
        );

      case 'select':
        return (
          <Select
            value={val}
            onChange={(v) => handleFieldChange(modKey, field.key, v)}
            style={{ width: '100%', maxWidth: 360 }}
            options={field.options || []}
          />
        );

      case 'number':
        return (
          <InputNumber
            value={val}
            onChange={(v) => handleFieldChange(modKey, field.key, v)}
            style={{ width: 200 }}
            min={field.min}
            max={field.max}
            step={field.step ?? 1}
          />
        );

      case 'password':
        return (
          <Input.Password
            value={val || ''}
            onChange={(e) => handleFieldChange(modKey, field.key, e.target.value)}
            style={{ maxWidth: 400 }}
          />
        );

      case 'input':
      default:
        return (
          <Input
            value={val ?? ''}
            onChange={(e) => handleFieldChange(modKey, field.key, e.target.value)}
            style={{ maxWidth: 400 }}
          />
        );
    }
  };

  // 渲染单个 Tab 的表单内容
  const renderTabContent = (tab) => {
    return (
      <Form layout="vertical" size="small" style={{ maxWidth: 600 }}>
        {tab.fields.map((field) => (
          <Form.Item
            key={field.key}
            label={
              <Space>
                <span>{field.label}</span>
                {field.description && (
                  <Tooltip title={field.description}>
                    <InfoCircleOutlined style={{ color: '#999', fontSize: 12 }} />
                  </Tooltip>
                )}
                {saving[tab.key] && <Tag color="processing" style={{ marginLeft: 4 }}>保存中...</Tag>}
              </Space>
            }
          >
            {renderFieldControl(tab.key, field)}
          </Form.Item>
        ))}
      </Form>
    );
  };

  // Tab items
  const tabItems = MODULE_TABS.map((tab) => ({
    key: tab.key,
    label: (
      <span>
        {tab.icon} {tab.label}
      </span>
    ),
    children: renderTabContent(tab),
  }));

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <RobotOutlined />
            <span>AI 智能配置</span>
            {lastSavedTime && (
              <Tag icon={<CheckCircleOutlined />} color="success" style={{ marginLeft: 8 }}>
                已同步 {lastSavedTime}
              </Tag>
            )}
          </Space>
        }
        bordered={false}
      >
        <Spin spinning={loading}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            type="card"
            size="middle"
          />
        </Spin>
      </Card>
    </div>
  );
}
