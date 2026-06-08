import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Tabs,
  Select,
  Switch,
  InputNumber,
  Input,
  Space,
  Tag,
  Typography,
  Spin,
  message,
  Divider,
  Button,
} from 'antd';
import {
  FileTextOutlined,
  FilterOutlined,
  EyeOutlined,
  SaveOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { getConfig, updateConfigModule } from '../services/config';

const { Text } = Typography;

// ==================== 常量定义 ====================

const TAB_ITEMS = [
  {
    key: 'report',
    label: (
      <span>
        <FileTextOutlined /> 报告模式
      </span>
    ),
  },
  {
    key: 'filter',
    label: (
      <span>
        <FilterOutlined /> 筛选策略
      </span>
    ),
  },
  {
    key: 'display',
    label: (
      <span>
        <EyeOutlined /> 推送内容控制
      </span>
    ),
  },
];

const REPORT_FIELDS = [
  {
    key: 'mode',
    label: '报告模式',
    type: 'select',
    options: [
      { value: 'daily', label: 'daily（每日汇总）' },
      { value: 'current', label: 'current（当前快照）' },
      { value: 'incremental', label: 'incremental（增量更新）' },
    ],
  },
  {
    key: 'display_mode',
    label: '展示维度',
    type: 'select',
    options: [
      { value: 'keyword', label: 'keyword（按关键词）' },
      { value: 'platform', label: 'platform（按平台）' },
    ],
  },
  {
    key: 'sort_by_position_first',
    label: '按排名优先排序',
    type: 'switch',
  },
  {
    key: 'rank_threshold',
    label: '排名阈值',
    type: 'number',
    min: 1,
    max: 50,
  },
  {
    key: 'max_news_per_keyword',
    label: '每关键词最大新闻数',
    type: 'number',
    min: 0,
    max: 50,
  },
];

const FILTER_FIELDS = [
  {
    key: 'method',
    label: '筛选方法',
    type: 'select',
    options: [
      { value: 'keyword', label: 'keyword（关键词匹配）' },
      { value: 'ai', label: 'ai（AI智能筛选）' },
    ],
  },
  {
    key: 'priority_sort_enabled',
    label: '启用优先级排序',
    type: 'switch',
  },
];

// ==================== 主组件 ====================

export default function ContentPolicy() {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState({});
  const [activeTab, setActiveTab] = useState('report');

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
        message.success(`[${moduleKey}] 已保存`);
        setConfig((prev) => ({ ...prev, [moduleKey]: value }));
      } else {
        message.error(res?.message || '保存失败');
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

  // 处理字段变更
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
    saveModule(moduleKey, current);
  };

  // 处理嵌套对象变更（用于 display.standalone.*）
  const handleNestedChange = (moduleKey, parentKey, childKey, value) => {
    const current = JSON.parse(JSON.stringify(config[moduleKey] || {}));
    if (!current[parentKey]) current[parentKey] = {};
    current[parentKey][childKey] = value;
    saveModule(moduleKey, current);
  };

  // ==================== 渲染通用字段 ====================

  const renderField = (modKey, field) => {
    const val = (() => {
      try {
        let v = config[modKey];
        for (const p of (field.key || '').split('.')) {
          if (v && typeof v === 'object') v = v[p];
          else return undefined;
        }
        return v;
      } catch {
        return undefined;
      }
    })();

    switch (field.type) {
      case 'select':
        return (
          <Select
            value={val}
            onChange={(v) => handleFieldChange(modKey, field.key, v)}
            style={{ width: '100%', maxWidth: 400 }}
            options={field.options}
          />
        );
      case 'switch':
        return (
          <Switch
            checked={val ?? false}
            onChange={(v) => handleFieldChange(modKey, field.key, v)}
            loading={saving[modKey]}
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
      default:
        return null;
    }
  };

  // ==================== Report 模块渲染 ====================

  const renderReport = () => {
    return (
      <div>
        {REPORT_FIELDS.map((f) => (
          <div key={f.key} style={{ marginBottom: 24 }}>
            <Space style={{ marginBottom: 8 }}>
              <Text strong>{f.label}</Text>
            </Space>
            <div>{renderField('report', f)}</div>
          </div>
        ))}
      </div>
    );
  };

  // ==================== Filter 模块渲染 ====================

  const renderFilter = () => {
    return (
      <div>
        {FILTER_FIELDS.map((f) => (
          <div key={f.key} style={{ marginBottom: 24 }}>
            <Space style={{ marginBottom: 8 }}>
              <Text strong>{f.label}</Text>
            </Space>
            <div>{renderField('filter', f)}</div>
          </div>
        ))}
      </div>
    );
  };

  // ==================== Display 模块渲染 ====================

  const renderDisplay = () => {
    const display = config.display || {};
    const regions = display.regions || {};
    const regionOrder = display.region_order || [];
    const standalone = display.standalone || {};

    return (
      <div>
        {/* 区域顺序（只读展示） */}
        <Divider orientation="left">区域顺序</Divider>
        <div style={{ marginBottom: 24 }}>
          <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>
            当前配置的区域显示顺序（只读）
          </Text>
          <div>
            {regionOrder.length > 0 ? (
              regionOrder.map((region, index) => (
                <Tag key={region} color="blue" style={{ marginBottom: 4 }}>
                  {index + 1}. {region}
                </Tag>
              ))
            ) : (
              <Tag>暂无区域配置</Tag>
            )}
          </div>
        </div>

        {/* 区域开关控制 */}
        <Divider orientation="left">区域显示控制</Divider>
        <div style={{ marginBottom: 24 }}>
          {regionOrder.length > 0 ? (
            regionOrder.map((region) => (
              <Card
                key={region}
                size="small"
                style={{
                  marginBottom: 8,
                  background: regions[region] ? '#f6ffed' : '#fafafa',
                  borderColor: regions[region] ? '#b7eb8f' : '#d9d9d9',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <Space>
                    <Tag color="blue">{region}</Tag>
                    <Tag color={regions[region] ? 'green' : 'default'}>
                      {regions[region] ? '显示' : '隐藏'}
                    </Tag>
                  </Space>
                  <Switch
                    size="small"
                    checked={!!regions[region]}
                    onChange={(v) => {
                      const d = JSON.parse(JSON.stringify(display));
                      if (!d.regions) d.regions = {};
                      d.regions[region] = v;
                      saveModule('display', d);
                    }}
                    loading={saving.display}
                  />
                </div>
              </Card>
            ))
          ) : (
            <Text type="secondary">暂无区域可控制</Text>
          )}
        </div>

        {/* 独立模块设置 */}
        <Divider orientation="left">独立模块 (standalone)</Divider>
        <Card size="small" style={{ background: '#fafafa' }}>
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              平台列表
            </Text>
            <Input
              value={standalone.platforms || ''}
              onChange={(e) =>
                handleNestedChange('display', 'standalone', 'platforms', e.target.value)
              }
              placeholder="输入平台列表，如：weibo,douyin,baidu"
              style={{ maxWidth: 500 }}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              RSS Feeds
            </Text>
            <Input
              value={standalone.rss_feeds || ''}
              onChange={(e) =>
                handleNestedChange('display', 'standalone', 'rss_feeds', e.target.value)
              }
              placeholder="输入 RSS Feed 列表"
              style={{ maxWidth: 500 }}
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>
              最大条目数
            </Text>
            <InputNumber
              value={standalone.max_items ?? 20}
              onChange={(v) =>
                handleNestedChange('display', 'standalone', 'max_items', v)
              }
              min={1}
              max={100}
              style={{ width: 200 }}
            />
          </div>
        </Card>
      </div>
    );
  };

  // ==================== Tab 内容路由 ====================

  const renderTabContent = () => {
    switch (activeTab) {
      case 'report':
        return renderReport();
      case 'filter':
        return renderFilter();
      case 'display':
        return renderDisplay();
      default:
        return null;
    }
  };

  // ==================== 主渲染 ====================

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <span>内容策略配置</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadConfig}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={TAB_ITEMS}
            type="card"
            size="middle"
            style={{ marginTop: 4 }}
          />

          <div style={{ minHeight: 400, padding: '20px 4px' }}>{renderTabContent()}</div>
        </Spin>
      </Card>
    </div>
  );
}
