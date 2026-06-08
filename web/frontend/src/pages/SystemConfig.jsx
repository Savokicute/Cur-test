import React, { useState, useEffect, useCallback } from 'react';
import {
  Layout,
  Card,
  Tabs,
  Button,
  Switch,
  Input,
  InputNumber,
  Select,
  Form,
  message,
  Spin,
  Space,
  Tag,
  Tooltip,
  Modal,
  Divider,
  Typography,
  Alert,
  Table,
  Popconfirm,
  Badge,
  Empty,
} from 'antd';
import {
  SettingOutlined,
  SaveOutlined,
  ReloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  CloudServerOutlined,
  LinkOutlined,
  ScheduleOutlined,
  FilterOutlined,
  RobotOutlined,
  BellOutlined,
  DatabaseOutlined,
  ApiOutlined,
  ExperimentOutlined,
  TranslationOutlined,
  ToolOutlined,
  EyeOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { getConfig, getConfigSchema, updateConfigModule, listBackups, restoreBackup } from '../services/config';

const { Content } = Layout;
const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const MODULE_META = {
  app: { label: '基础设置', icon: <SettingOutlined />, color: '#1677ff' },
  schedule: { label: '调度系统', icon: <ScheduleOutlined />, color: '#722ed1' },
  platforms: { label: '热榜平台', icon: <CloudServerOutlined />, color: '#13c2c2' },
  rss: { label: 'RSS订阅', icon: <LinkOutlined />, color: '#fa8c16' },
  report: { label: '报告模式', icon: <FileTextOutlined />, color: '#52c41a' },
  filter: { label: '筛选策略', icon: <FilterOutlined />, color: '#eb2f96' },
  ai_filter: { label: 'AI筛选参数', icon: <RobotOutlined />, color: '#1890ff' },
  display: { label: '推送内容', icon: <EyeOutlined />, color: '#faad14' },
  notification: { label: '推送通知', icon: <BellOutlined />, color: '#f5222d' },
  storage: { label: '存储配置', icon: <DatabaseOutlined />, color: '#8c8c8c' },
  ai: { label: 'AI模型', icon: <ApiOutlined />, color: '#2f54eb' },
  ai_analysis: { label: 'AI分析', icon: <ExperimentOutlined />, color: '#13c2c2' },
  ai_translation: { label: 'AI翻译', icon: <TranslationOutlined />, color: '#52c41a' },
  advanced: { label: '高级设置', icon: <ToolOutlined />, color: '#595959' },
};

export default function SystemConfig() {
  const [config, setConfig] = useState({});
  const [schema, setSchema] = useState({});
  const [activeTab, setActiveTab] = useState('platforms');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState({});
  const [lastSavedTime, setLastSavedTime] = useState(null);

  // 弹窗状态
  const [platformModalVisible, setPlatformModalVisible] = useState(false);
  const [editingPlatform, setEditingPlatform] = useState(null);
  const [platformForm] = Form.useForm();
  const [rssModalVisible, setRssModalVisible] = useState(false);
  const [editingFeed, setEditingFeed] = useState(null);
  const [rssForm] = Form.useForm();

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cfgRes, schRes] = await Promise.all([getConfig(), getConfigSchema()]);
      if (cfgRes?.success) setConfig(cfgRes.data.parsed || {});
      if (schRes?.success) setSchema(schRes.data.modules || {});
    } catch (e) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const saveModule = async (moduleKey, value) => {
    setSaving((prev) => ({ ...prev, [moduleKey]: true }));
    try {
      const res = await updateConfigModule(moduleKey, value);
      if (res?.success) {
        message.success(`[${MODULE_META[moduleKey]?.label || moduleKey}] 已保存`);
        setConfig((prev) => ({ ...prev, [moduleKey]: value }));
        setLastSavedTime(new Date().toLocaleTimeString());
      }
    } catch (e) {
      message.error('保存失败');
    } finally {
      setSaving((prev) => { const n = { ...prev }; delete n[moduleKey]; return n; });
    }
  };

  const handleFieldChange = (moduleKey, fieldPath, value) => {
    const current = JSON.parse(JSON.stringify(config[moduleKey] || {}));
    if (fieldPath.includes('.')) {
      const parts = fieldPath.split('.');
      let obj = current;
      for (let i = 0; i < parts.length - 1; i++) { if (!obj[parts[i]]) obj[parts[i]] = {}; obj = obj[parts[i]]; }
      obj[parts[parts.length - 1]] = value;
    } else {
      current[fieldPath] = value;
    }
    setConfig((prev) => ({ ...prev, [moduleKey]: current }));
    saveModule(moduleKey, current);
  };

  // ==================== 平台操作 ====================
  const openAddPlatform = () => { setEditingPlatform(null); platformForm.resetFields(); setPlatformModalVisible(true); };
  const openEditPlatform = (record) => { setEditingPlatform(record); platformForm.setFieldsValue({ platformId: record.id, platformName: record.name }); setPlatformModalVisible(true); };
  const confirmPlatform = async () => {
    try {
      const v = await platformForm.validateFields();
      const platforms = JSON.parse(JSON.stringify(config.platforms || {}));
      const sources = platforms.sources || [];
      if (editingPlatform) {
        const idx = sources.findIndex((s) => s.id === editingPlatform.id);
        if (idx >= 0) { sources[idx] = { ...sources[idx], id: v.platformId, name: v.platformName }; }
      } else {
        if (sources.some((s) => s.id === v.platformId)) { message.warning('平台 ID 已存在'); return; }
        sources.push({ id: v.platformId, name: v.platformName, enabled: true });
      }
      platforms.sources = sources;
      setPlatformModalVisible(false);
      saveModule('platforms', platforms);
    } catch {}
  };

  const deletePlatform = (pid) => {
    const platforms = JSON.parse(JSON.stringify(config.platforms || {}));
    platforms.sources = (platforms.sources || []).filter((s) => s.id !== pid);
    saveModule('platforms', platforms);
  };

  const togglePlatformEnabled = (pid, enabled) => {
    const platforms = JSON.parse(JSON.stringify(config.platforms || {}));
    platforms.sources = (platforms.sources || []).map((s) => s.id === pid ? { ...s, enabled } : s);
    setConfig((prev) => ({ ...prev, platforms }));
    saveModule('platforms', platforms);
  };

  // ==================== RSS 操作 ====================
  const openAddRss = () => { setEditingFeed(null); rssForm.resetFields(); setRssModalVisible(true); };
  const openEditRss = (record) => { setEditingFeed(record); rssForm.setFieldsValue(record); setRssModalVisible(true); };
  const confirmRss = async () => {
    try {
      const v = await rssForm.validateFields();
      const rss = JSON.parse(JSON.stringify(config.rss || {}));
      const feeds = rss.feeds || [];
      if (editingFeed) {
        const idx = feeds.findIndex((f) => f.id === editingFeed.id);
        if (idx >= 0) feeds[idx] = { ...feeds[idx], ...v };
      } else {
        if (feeds.some((f) => f.id === v.id)) { message.warning(' Feed ID 已存在'); return; }
        feeds.push(v);
      }
      rss.feeds = feeds;
      setRssModalVisible(false);
      saveModule('rss', rss);
    } catch {}
  };

  const deleteRss = (fid) => {
    const rss = JSON.parse(JSON.stringify(config.rss || {}));
    rss.feeds = (rss.feeds || []).filter((f) => f.id !== fid);
    saveModule('rss', rss);
  };

  // ==================== 渲染器 ====================
  const renderField = (modKey, field) => {
    const val = (() => {
      try {
        let v = config[modKey];
        for (const p of (field.key || '').split('.')) { if (v && typeof v === 'object') v = v[p]; else return undefined; }
        return v;
      } catch { return undefined; }
    })();

    switch (field.type) {
      case 'switch':
        return <Switch size="small" checked={val ?? false} onChange={(v) => handleFieldChange(modKey, field.key, v)} />;
      case 'select':
        return (
          <Select
            value={val}
            onChange={(v) => handleFieldChange(modKey, field.key, v)}
            style={{ width: '100%', maxWidth: 400 }}
            options={(field.options || []).map((o) => typeof o === 'string' ? { value: o, label: o } : { value: o[0], label: o[1] })}
          />
        );
      case 'number':
        return (
          <InputNumber
            value={val}
            onChange={(v) => handleFieldChange(modKey, field.key, v)}
            style={{ width: 200 }}
            min={field.min} max={field.max} step={field.step ?? 1}
          />
        );
      case 'password':
        return <Input.Password value={val || ''} onChange={(e) => handleFieldChange(modKey, field.key, e.target.value)} style={{ maxWidth: 400 }} />;
      case 'textarea':
        return <TextArea value={val || ''} onChange={(e) => handleFieldChange(modKey, field.key, e.target.value)} rows={3} style={{ maxWidth: 500 }} />;
      default:
        return <Input value={val ?? ''} onChange={(e) => handleFieldChange(modKey, field.key, e.target.value)} style={{ maxWidth: 400 }} />;
    }
  };

  const renderSimpleModule = (modKey) => {
    const def = schema[modKey];
    const fields = def?.fields || [];
    if (!fields.length) return <Empty description="暂无可编辑字段" />;
    return (
      <div>
        {fields.map((f) => (
          <div key={f.key} style={{ marginBottom: 20 }}>
            <Space style={{ marginBottom: 6 }}>
              <Text strong>{f.label || f.key}</Text>
              {f.description && <Tooltip title={f.description}><InfoCircleOutlined style={{ color: '#999', fontSize: 12 }} /></Tooltip>}
              {saving[modKey] && <Badge status="processing" text="保存中..." />}
            </Space>
            <div>{renderField(modKey, f)}</div>
          </div>
        ))}
      </div>
    );
  };

  // ==================== 热榜平台 Tab ====================
  const renderPlatforms = () => {
    const plat = config.platforms || {};
    const sources = (plat.sources || []).filter((s) => s && !String(s.id).startsWith('#'));
    return (
      <div>
        {/* 总开关 */}
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text strong>热榜抓取总开关</Text>
              <Switch
                checked={plat.enabled !== false}
                onChange={(v) => {
                  const p = JSON.parse(JSON.stringify(plat)); p.enabled = v; setConfig((prev) => ({ ...prev, platforms: p })); saveModule('platforms', p);
                }}
                loading={saving.platforms}
              />
              <Tag color={plat.enabled !== false ? 'green' : 'default'}>{plat.enabled !== false ? '已启用' : '已禁用'}</Tag>
            </Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={openAddPlatform}>添加平台</Button>
          </div>
        </Card>

        {/* 预设未启用平台提示 */}
        {(plat.sources || []).some((s) => s && String(s.id).startsWith('#')) && (
          <Alert
            message="以下预设平台尚未启用（在 config.yaml 中注释掉了），可点击「添加平台」启用"
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
          />
        )}

        {/* 平台表格 */}
        <Table
          dataSource={sources}
          rowKey="id"
          pagination={false}
          size="middle"
          columns={[
            { title: '平台 ID', dataIndex: 'id', key: 'id', width: 200, fixed: 'left' },
            { title: '显示名称', dataIndex: 'name', key: 'name' },
            {
              title: '状态', key: 'enabled', width: 100,
              render: (_, r) => (
                <Switch
                  size="small"
                  checked={r.enabled !== false}
                  onChange={(v) => togglePlatformEnabled(r.id, v)}
                  loading={saving.platforms}
                />
              ),
            },
            {
              title: '操作', key: 'actions', width: 160,
              render: (_, r) => (
                <Space>
                  <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditPlatform(r)}>编辑</Button>
                  <Popconfirm title="确定删除？" onConfirm={() => deletePlatform(r.id)}>
                    <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />

        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 12 }}>
          共 {sources.length} 个平台，已启用 {sources.filter((s) => s.enabled !== false).length} 个
        </Text>

        {/* 添加/编辑平台弹窗 */}
        <Modal
          title={editingPlatform ? '编辑平台' : '添加热榜平台'}
          open={platformModalVisible}
          onOk={confirmPlatform}
          onCancel={() => setPlatformModalVisible(false)}
          width={480}
        >
          <Alert
            message="常用预设平台 ID"
            description="toutiao(今日头条)、baidu(百度热搜)、weibo(微博)、douyin(抖音)、zhihu(知乎)、bilibili-hot-search(B站热搜)、tieba(贴吧)"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Form form={platformForm} layout="vertical">
            <Form.Item label="平台 ID" name="platformId" rules={[{ required: true, message: '请输入平台ID' }]}>
              <Input placeholder="如：weibo、douyin" disabled={!!editingPlatform} />
            </Form.Item>
            <Form.Item label="显示名称" name="platformName" rules={[{ required: true, message: '请输入显示名称' }]}>
              <Input placeholder="如：微博热搜" />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    );
  };

  // ==================== RSS 订阅 Tab ====================
  const renderRss = () => {
    const rss = config.rss || {};
    const feeds = rss.feeds || [];
    return (
      <div>
        {/* 总开关 + 新鲜度 */}
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Space>
                <Text strong>RSS 抓取总开关</Text>
                <Switch
                  checked={rss.enabled !== false}
                  onChange={(v) => {
                    const r = JSON.parse(JSON.stringify(rss)); r.enabled = v; setConfig((prev) => ({ ...prev, rss: r })); saveModule('rss', r);
                  }}
                  loading={saving.rss}
                />
              </Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={openAddRss}>添加 Feed</Button>
            </div>
            <Divider style={{ margin: '8px 0' }} plain />
            <div>
              <Text style={{ marginRight: 12 }}>新鲜度过滤：</Text>
              <Switch
                size="small"
                checked={rss.freshness_filter?.enabled !== false}
                onChange={(v) => {
                  const r = JSON.parse(JSON.stringify(rss));
                  if (!r.freshness_filter) r.freshness_filter = {};
                  r.freshness_filter.enabled = v;
                  setConfig((prev) => ({ ...prev, rss: r })); saveModule('rss', r);
                }}
              />
              <span style={{ marginLeft: 16, marginRight: 8 }}>最大年龄(天)：</span>
              <InputNumber
                size="small"
                value={rss.freshness_filter?.max_age_days ?? 1}
                min={0}
                max={365}
                style={{ width: 80 }}
                onChange={(v) => {
                  const r = JSON.parse(JSON.stringify(rss));
                  if (!r.freshness_filter) r.freshness_filter = {};
                  r.freshness_filter.max_age_days = v;
                  setConfig((prev) => ({ ...prev, rss: r })); saveModule('rss', r);
                }}
              />
            </div>
          </Space>
        </Card>

        {/* Feed 表格 */}
        {feeds.length > 0 ? (
          <Table
            dataSource={feeds}
            rowKey="id"
            pagination={false}
            size="middle"
            columns={[
              { title: 'ID', dataIndex: 'id', key: 'id', width: 160 },
              { title: '名称', dataIndex: 'name', key: 'name' },
              { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
              {
                title: '启用', dataIndex: 'enabled', key: 'enabled', width: 80,
                render: (e) => <Tag color={e !== false ? 'green' : 'default'}>{e !== false ? '启用' : '禁用'}</Tag>,
              },
              {
                title: '操作', key: 'actions', width: 160,
                render: (_, r) => (
                  <Space>
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditRss(r)}>编辑</Button>
                    <Popconfirm title="确定删除？" onConfirm={() => deleteRss(r.id)}>
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        ) : (
          <Empty description="暂无 RSS 订阅，点击上方按钮添加">
            <Button type="primary" icon={<PlusOutlined />} onClick={openAddRss}>添加第一个 Feed</Button>
          </Empty>
        )}

        {/* 添加/编辑 Feed 弹窗 */}
        <Modal
          title={editingFeed ? '编辑 Feed' : '添加 RSS Feed'}
          open={rssModalVisible}
          onOk={confirmRss}
          onCancel={() => setRssModalVisible(false)}
          width={560}
        >
          <Form form={rssForm} layout="vertical">
            {!editingFeed && (
              <Form.Item label="标识 ID" name="id" rules={[{ required: true }]}>
                <Input placeholder="如 hacker-news" />
              </Form.Item>
            )}
            <Form.Item label="名称" name="name" rules={[{ required: true }]}>
              <Input placeholder="显示名称" />
            </Form.Item>
            <Form.Item label="URL 地址" name="url" rules={[{ required: true }, { type: 'url' }]}>
              <Input placeholder="https://example.com/feed.xml" />
            </Form.Item>
            <Form.Item label="启用" name="enabled" valuePropName="checked">
              <Switch defaultChecked />
            </Form.Item>
          </Form>
        </Modal>
      </div>
    );
  };

  // ==================== 推送通知 Tab ====================
  const renderNotification = () => {
    const notif = config.notification || {};
    const channels = notif.channels || {};
    const channelList = Object.entries(channels).map(([key, val]) => ({ key, ...val }));

    return (
      <div>
        <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
          <Space>
            <Text strong>推送通知总开关</Text>
            <Switch
              checked={notif.enabled !== false}
              onChange={(v) => {
                const n = JSON.parse(JSON.stringify(notif)); n.enabled = v;
                setConfig((prev) => ({ ...prev, notification: n })); saveModule('notification', n);
              }}
              loading={saving.notification}
            />
          </Space>
        </Card>

        <Divider orientation="left">通知渠道</Divider>
        {channelList.map(([key, cfg]) => (
          <Card
            key={key}
            size="small"
            title={<Text strong>{key}</Text>}
            style={{ marginBottom: 12 }}
            extra={
              <Tag color={cfg.webhook_url ? 'green' : 'default'}>
                {cfg.webhook_url ? '已配置' : '未配置'}
              </Tag>
            }
          >
            <Form layout="vertical" size="small">
              <Form.Item label="Webhook URL" style={{ marginBottom: 8 }}>
                <Input
                  value={cfg.webhook_url || ''}
                  onChange={(e) => {
                    const ch = JSON.parse(JSON.stringify(channels));
                    ch[key] = { ...(ch[key] || {}), webhook_url: e.target.value };
                    const n = JSON.parse(JSON.stringify(notif)); n.channels = ch;
                    setConfig((prev) => ({ ...prev, notification: n })); saveModule('notification', n);
                  }}
                  placeholder="留空表示不使用此渠道"
                />
              </Form.Item>
            </Form>
          </Card>
        ))}
      </div>
    );
  };

  // ==================== 存储配置 Tab ====================
  const renderStorage = () => {
    const storage = config.storage || {};
    const local = storage.local || {};

    return (
      <div>
        <Form layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item label="存储后端">
            <Select
              value={storage.backend || 'auto'}
              onChange={(v) => handleFieldChange('storage', 'backend', v)}
              options={[
                { value: 'auto', label: 'auto（自动）' },
                { value: 'local', label: 'local（本地）' },
                { value: 'remote', label: 'remote（远程）' },
              ]}
            />
          </Form.Item>
          <Divider />
          <Text strong>本地存储</Text>
          <Form.Item label="数据目录" style={{ marginTop: 12 }}>
            <Input
              value={local.data_dir || 'output'}
              onChange={(e) => {
                const l = { ...local, data_dir: e.target.value };
                handleFieldChange('storage', 'local', l);
              }}
            />
          </Form.Item>
          <Form.Item label="保留天数">
            <Space>
              <InputNumber
                value={local.retention_days ?? 0}
                min={0}
                onChange={(v) => {
                  const l = { ...local, retention_days: v };
                  handleFieldChange('storage', 'local', l);
                }}
                style={{ width: 100 }}
              />
              <Text type="secondary">0 = 永不删除</Text>
            </Space>
          </Form.Item>
        </Form>
      </div>
    );
  };

  // ==================== 推送内容控制 Tab ====================
  const renderDisplay = () => {
    const display = config.display || {};
    const regions = display.regions || {};
    return (
      <div>
        <Text strong style={{ display: 'block', marginBottom: 12 }}>展示区域控制</Text>
        {(display.region_order || []).map((region) => (
          <div key={region} style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '8px 12px',
            marginBottom: 6,
            background: regions[region] ? '#f6ffed' : '#fff',
            border: `1px solid ${regions[region] ? '#b7eb8f' : '#d9d9d9'}`,
            borderRadius: 6,
          }}>
            <Space>
              <Text>{region}</Text>
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
                setConfig((prev) => ({ ...prev, display: d })); saveModule('display', d);
              }}
              loading={saving.display}
            />
          </div>
        ))}
      </div>
    );
  };

  // ==================== 主渲染器：根据模块选择 ====================
  const renderModuleContent = (key) => {
    switch (key) {
      case 'platforms': return renderPlatforms();
      case 'rss': return renderRss();
      case 'notification': return renderNotification();
      case 'storage': return renderStorage();
      case 'display': return renderDisplay();
      default: return renderSimpleModule(key);
    }
  };

  const tabItems = Object.keys(MODULE_META)
    .filter((k) => config.hasOwnProperty(k))
    .map((key) => ({
      key,
      label: (
        <span>
          {MODULE_META[key].icon} {MODULE_META[key].label}
        </span>
      ),
    }));

  return (
    <Content style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>系统配置</span>
            {lastSavedTime && (
              <Tag icon={<CheckCircleOutlined />} color="success" style={{ marginLeft: 8 }}>
                已同步 {lastSavedTime}
              </Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>
              刷新
            </Button>
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
            style={{ marginTop: 4 }}
          />

          <div style={{ minHeight: 360, padding: '20px 4px' }}>
            {renderModuleContent(activeTab)}
          </div>
        </Spin>
      </Card>
    </Content>
  );
}
