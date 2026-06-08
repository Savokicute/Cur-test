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
  Tag,
  Typography,
  Divider,
} from 'antd';
import {
  BellOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { getConfig, updateConfigModule } from '../services/config';

const { Text } = Typography;
const { TextArea } = Input;

// ==================== 渠道元数据定义 ====================
const CHANNEL_META = {
  feishu: {
    label: '飞书',
    fields: [{ key: 'webhook_url', label: 'Webhook URL', type: 'input', placeholder: '飞书机器人 Webhook 地址' }],
  },
  dingtalk: {
    label: '钉钉',
    fields: [{ key: 'webhook_url', label: 'Webhook URL', type: 'input', placeholder: '钉钉机器人 Webhook 地址' }],
  },
  wework: {
    label: '企业微信',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'input', placeholder: '企业微信机器人 Webhook 地址' },
      {
        key: 'msg_type',
        label: '消息类型',
        type: 'select',
        options: [
          { value: 'markdown', label: 'Markdown' },
          { value: 'text', label: '纯文本' },
        ],
      },
    ],
  },
  telegram: {
    label: 'Telegram',
    fields: [
      { key: 'bot_token', label: 'Bot Token', type: 'input', placeholder: 'Telegram Bot Token' },
      { key: 'chat_id', label: 'Chat ID', type: 'input', placeholder: '目标 Chat ID 或频道名' },
    ],
  },
  email: {
    label: '邮件',
    fields: [
      { key: 'from', label: '发件人地址', type: 'input', placeholder: 'sender@example.com' },
      { key: 'to', label: '收件人地址', type: 'input', placeholder: 'recipient@example.com' },
      { key: 'password', label: 'SMTP 密码 / 授权码', type: 'password' },
      { key: 'smtp_server', label: 'SMTP 服务器', type: 'input', placeholder: 'smtp.example.com' },
      { key: 'smtp_port', label: 'SMTP 端口', type: 'input', placeholder: '465 / 587' },
    ],
  },
  ntfy: {
    label: 'ntfy',
    fields: [
      { key: 'server_url', label: '服务器地址', type: 'input', placeholder: 'https://ntfy.sh' },
      { key: 'topic', label: 'Topic', type: 'input', placeholder: '通知主题名称' },
      { key: 'token', label: 'Token（可选）', type: 'input', placeholder: '访问令牌，留空为公开' },
    ],
  },
  bark: {
    label: 'Bark',
    fields: [{ key: 'url', label: 'Bark URL', type: 'input', placeholder: 'https://api.day.app/YOUR_KEY' }],
  },
  slack: {
    label: 'Slack',
    fields: [{ key: 'webhook_url', label: 'Webhook URL', type: 'input', placeholder: 'Slack Incoming Webhook URL' }],
  },
  generic_webhook: {
    label: '通用Webhook',
    fields: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'input', placeholder: '目标 Webhook 地址' },
      { key: 'payload_template', label: 'Payload 模板', type: 'textarea', placeholder: '自定义 JSON 模板，支持 {{变量}} 占位符', rows: 3 },
    ],
  },
};

// 判断渠道是否已配置（以 webhook_url 或 url 为主要依据）
function isChannelConfigured(channelKey, channelData) {
  if (channelKey === 'telegram') return !!(channelData?.bot_token && channelData?.chat_id);
  if (channelKey === 'email') return !!channelData?.from;
  if (channelKey === 'ntfy') return !!(channelData?.server_url && channelData?.topic);
  if (channelKey === 'generic_webhook') return !!channelData?.webhook_url;
  // feishu, dingtalk, wework, bark, slack — 以 webhook_url/url 判断
  const urlField = channelKey === 'bark' ? 'url' : 'webhook_url';
  return !!channelData?.[urlField];
}

export default function NotifyStorage() {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState({});
  const [activeTab, setActiveTab] = useState('notification');
  const [lastSavedTime, setLastSavedTime] = useState(null);

  // 加载完整配置
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

  // 保存指定模块
  const saveModule = async (moduleKey, value) => {
    setSaving((prev) => ({ ...prev, [moduleKey]: true }));
    try {
      const res = await updateConfigModule(moduleKey, value);
      if (res?.success) {
        message.success(`[${moduleKey}] 已保存`);
        setConfig((prev) => ({ ...prev, [moduleKey]: value }));
        setLastSavedTime(new Date().toLocaleTimeString());
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

  // ==================== Notification 模块操作 ====================

  /** 更新 notification 顶层字段（如 enabled） */
  const handleNotifTopChange = (field, value) => {
    const notif = JSON.parse(JSON.stringify(config.notification || {}));
    notif[field] = value;
    setConfig((prev) => ({ ...prev, notification: notif }));
    saveModule('notification', notif);
  };

  /** 更新某个渠道的某个字段 */
  const handleChannelFieldChange = (channelKey, fieldKey, value) => {
    const notif = JSON.parse(JSON.stringify(config.notification || {}));
    if (!notif.channels) notif.channels = {};
    if (!notif.channels[channelKey]) notif.channels[channelKey] = {};
    notif.channels[channelKey][fieldKey] = value;
    setConfig((prev) => ({ ...prev, notification: notif }));
    saveModule('notification', notif);
  };

  /** 渲染单个渠道卡片内的字段 */
  const renderChannelField = (channelKey, field, channelData) => {
    const val = channelData?.[field.key] ?? '';

    switch (field.type) {
      case 'select':
        return (
          <Select
            value={val || undefined}
            onChange={(v) => handleChannelFieldChange(channelKey, field.key, v)}
            options={field.options || []}
            style={{ width: '100%' }}
            placeholder={`请选择${field.label}`}
          />
        );
      case 'password':
        return (
          <Input.Password
            value={val || ''}
            onChange={(e) => handleChannelFieldChange(channelKey, field.key, e.target.value)}
            placeholder={field.placeholder || ''}
          />
        );
      case 'textarea':
        return (
          <TextArea
            value={val || ''}
            onChange={(e) => handleChannelFieldChange(channelKey, field.key, e.target.value)}
            rows={field.rows || 3}
            placeholder={field.placeholder || ''}
          />
        );
      case 'number':
        return (
          <InputNumber
            value={val}
            onChange={(v) => handleChannelFieldChange(channelKey, field.key, v)}
            style={{ width: '100%' }}
            min={field.min}
            max={field.max}
          />
        );
      default:
        return (
          <Input
            value={val || ''}
            onChange={(e) => handleChannelFieldChange(channelKey, field.key, e.target.value)}
            placeholder={field.placeholder || ''}
          />
        );
    }
  };

  /** 渲染 Notification Tab 内容 */
  const renderNotification = () => {
    const notif = config.notification || {};
    const channels = notif.channels || {};
    const channelKeys = Object.keys(CHANNEL_META);

    return (
      <div>
        {/* 总开关 */}
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
          <Space>
            <Text strong>推送通知总开关</Text>
            <Switch
              checked={notif.enabled !== false}
              onChange={(v) => handleNotifTopChange('enabled', v)}
              loading={saving.notification}
            />
            <Tag color={notif.enabled !== false ? 'green' : 'default'}>
              {notif.enabled !== false ? '已启用' : '已禁用'}
            </Tag>
          </Space>
        </Card>

        <Divider orientation="left">通知渠道</Divider>

        {/* 渠道卡片列表 */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
            gap: 12,
          }}
        >
          {channelKeys.map((key) => {
            const meta = CHANNEL_META[key];
            const chData = channels[key] || {};
            const configured = isChannelConfigured(key, chData);

            return (
              <Card
                key={key}
                size="small"
                title={<Text strong>{meta.label}</Text>}
                extra={
                  <Tag color={configured ? 'green' : 'default'}>
                    {configured ? '已配置' : '未配置'}
                  </Tag>
                }
              >
                <Form layout="vertical" size="small">
                  {meta.fields.map((f) => (
                    <Form.Item key={f.key} label={f.label} style={{ marginBottom: 10 }}>
                      {renderChannelField(key, f, chData)}
                    </Form.Item>
                  ))}
                </Form>
              </Card>
            );
          })}
        </div>
      </div>
    );
  };

  // ==================== Storage 模块操作 ====================

  /** 更新 storage 字段（支持点分路径如 local.data_dir） */
  const handleStorageChange = (fieldPath, value) => {
    const storage = JSON.parse(JSON.stringify(config.storage || {}));
    if (fieldPath.includes('.')) {
      const parts = fieldPath.split('.');
      let obj = storage;
      for (let i = 0; i < parts.length - 1; i++) {
        if (!obj[parts[i]]) obj[parts[i]] = {};
        obj = obj[parts[i]];
      }
      obj[parts[parts.length - 1]] = value;
    } else {
      storage[fieldPath] = value;
    }
    setConfig((prev) => ({ ...prev, storage }));
    saveModule('storage', storage);
  };

  /** 获取 storage 嵌套字段的值 */
  const getStorageValue = (fieldPath) => {
    try {
      let v = config.storage;
      for (const p of fieldPath.split('.')) {
        if (v && typeof v === 'object') v = v[p];
        else return undefined;
      }
      return v;
    } catch {
      return undefined;
    }
  };

  /** 渲染 Storage Tab 内容 */
  const renderStorage = () => {
    const storage = config.storage || {};

    return (
      <div>
        <Form layout="vertical" style={{ maxWidth: 640 }}>
          {/* 存储后端 */}
          <Form.Item label="存储后端">
            <Select
              value={storage.backend || 'auto'}
              onChange={(v) => handleStorageChange('backend', v)}
              options={[
                { value: 'auto', label: 'auto（自动选择）' },
                { value: 'local', label: 'local（本地存储）' },
                { value: 'remote', label: 'remote（远程存储）' },
              ]}
            />
          </Form.Item>

          {/* 输出格式 */}
          <Divider orientation="left">输出格式</Divider>

          <Space direction="vertical" size="middle" style={{ width: '100%', maxWidth: 400 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Text>SQLite 数据库</Text>
                <InfoCircleOutlined style={{ color: '#999', fontSize: 13 }} />
              </Space>
              <Switch
                size="small"
                checked={storage.formats?.sqlite !== false}
                onChange={(v) => {
                  const s = { ...storage };
                  if (!s.formats) s.formats = {};
                  s.formats.sqlite = v;
                  setConfig((prev) => ({ ...prev, storage: s }));
                  saveModule('storage', s);
                }}
                loading={saving.storage}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Text>TXT 文本</Text>
              </Space>
              <Switch
                size="small"
                checked={storage.formats?.txt === true}
                onChange={(v) => {
                  const s = { ...storage };
                  if (!s.formats) s.formats = {};
                  s.formats.txt = v;
                  setConfig((prev) => ({ ...prev, storage: s }));
                  saveModule('storage', s);
                }}
                loading={saving.storage}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Text>HTML 报告</Text>
              </Space>
              <Switch
                size="small"
                checked={storage.formats?.html !== false}
                onChange={(v) => {
                  const s = { ...storage };
                  if (!s.formats) s.formats = {};
                  s.formats.html = v;
                  setConfig((prev) => ({ ...prev, storage: s }));
                  saveModule('storage', s);
                }}
                loading={saving.storage}
              />
            </div>
          </Space>

          {/* 本地存储 */}
          <Divider orientation="left">本地存储</Divider>

          <Form.Item label="数据目录 (data_dir)">
            <Input
              value={getStorageValue('local.data_dir') || 'output'}
              onChange={(e) => handleStorageChange('local.data_dir', e.target.value)}
              placeholder="输出目录路径，默认 output"
            />
          </Form.Item>

          <Form.Item
            label={
              <Space>
                <span>保留天数</span>
                <Text type="secondary" style={{ fontWeight: 'normal', fontSize: 12 }}>0 = 永不删除</Text>
              </Space>
            }
          >
            <InputNumber
              value={getStorageValue('local.retention_days') ?? 0}
              min={0}
              max={365}
              onChange={(v) => handleStorageChange('local.retention_days', v)}
              style={{ width: 120 }}
            />
          </Form.Item>

          {/* 远程存储 */}
          <Divider orientation="left">远程存储</Divider>

          <Form.Item label="保留天数">
            <InputNumber
              value={getStorageValue('remote.retention_days') ?? 0}
              min={0}
              max={365}
              onChange={(v) => handleStorageChange('remote.retention_days', v)}
              style={{ width: 120 }}
            />
          </Form.Item>

          <Form.Item label="Endpoint URL">
            <Input
              value={getStorageValue('remote.endpoint_url') || ''}
              onChange={(e) => handleStorageChange('remote.endpoint_url', e.target.value)}
              placeholder="S3 兼容端点地址"
            />
          </Form.Item>

          <Form.Item label="Bucket 名称">
            <Input
              value={getStorageValue('remote.bucket_name') || ''}
              onChange={(e) => handleStorageChange('remote.bucket_name', e.target.value)}
              placeholder="存储桶名称"
            />
          </Form.Item>

          <Form.Item label="Access Key ID">
            <Input.Password
              value={getStorageValue('remote.access_key_id') || ''}
              onChange={(e) => handleStorageChange('remote.access_key_id', e.target.value)}
              placeholder="访问密钥 ID"
            />
          </Form.Item>

          <Form.Item label="Secret Access Key">
            <Input.Password
              value={getStorageValue('remote.secret_access_key') || ''}
              onChange={(e) => handleStorageChange('remote.secret_access_key', e.target.value)}
              placeholder="秘密访问密钥"
            />
          </Form.Item>

          <Form.Item label="Region">
            <Input
              value={getStorageValue('remote.region') || ''}
              onChange={(e) => handleStorageChange('remote.region', e.target.value)}
              placeholder="如 us-east-1"
            />
          </Form.Item>

          {/* 远程拉取 */}
          <Divider orientation="left">远程拉取</Divider>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space>
              <Text strong>启用远程拉取</Text>
            </Space>
            <Switch
              size="small"
              checked={storage.pull?.enabled === true}
              onChange={(v) => {
                const s = { ...storage };
                if (!s.pull) s.pull = {};
                s.pull.enabled = v;
                setConfig((prev) => ({ ...prev, storage: s }));
                saveModule('storage', s);
              }}
              loading={saving.storage}
            />
          </div>

          <Form.Item label="拉取天数范围">
            <Space>
              <InputNumber
                value={storage.pull?.days ?? 7}
                min={1}
                max={90}
                onChange={(v) => {
                  const s = { ...storage };
                  if (!s.pull) s.pull = {};
                  s.pull.days = v;
                  setConfig((prev) => ({ ...prev, storage: s }));
                  saveModule('storage', s);
                }}
                style={{ width: 100 }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>1 ~ 90 天</Text>
            </Space>
          </Form.Item>
        </Form>
      </div>
    );
  };

  // ==================== 主渲染 ====================
  const tabItems = [
    {
      key: 'notification',
      label: (
        <span>
          <BellOutlined /> 推送通知
        </span>
      ),
      children: renderNotification(),
    },
    {
      key: 'storage',
      label: (
        <span>
          <DatabaseOutlined /> 存储配置
        </span>
      ),
      children: renderStorage(),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <BellOutlined />
            <span>通知与存储</span>
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
