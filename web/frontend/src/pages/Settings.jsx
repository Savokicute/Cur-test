import React, { useState, useEffect, useCallback } from 'react';
import {
  Layout,
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
  SettingOutlined,
  ScheduleOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  GlobalOutlined,
  BellOutlined,
  BugOutlined,
  RobotOutlined,
  LinkOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { getConfig, updateConfigModule } from '../services/config';

const { Content } = Layout;
const { Text, Paragraph } = Typography;

// ==================== Tab 元信息 ====================
const TAB_META = {
  app: {
    key: 'app',
    label: '基础设置',
    icon: <SettingOutlined />,
    color: '#1677ff',
    description: '应用程序基础配置，包括时区、版本更新提示等全局选项。',
  },
  schedule: {
    key: 'schedule',
    label: '调度策略',
    icon: <ScheduleOutlined />,
    color: '#722ed1',
    description: '定时任务调度配置，控制抓取与推送的时间节奏和预设模式。',
  },
  advanced: {
    key: 'advanced',
    label: '高级设置',
    icon: <ToolOutlined />,
    color: '#595959',
    description: '爬虫、RSS、权重等底层参数调优，仅建议高级用户修改。',
  },
};

// ==================== 选项常量 ====================
const TIMEZONE_OPTIONS = [
  { value: 'Asia/Shanghai', label: 'Asia/Shanghai（中国标准时间）' },
  { value: 'America/New_York', label: 'America/New_York（美国东部时间）' },
  { value: 'Europe/London', label: 'Europe/London（格林威治时间）' },
];

const SCHEDULE_PRESET_OPTIONS = [
  { value: 'always_on', label: 'always_on（全天持续运行）' },
  { value: 'morning_evening', label: 'morning_evening（全天推送 + 晚间汇总）' },
  { value: 'office_hours', label: 'office_hours（工作日三段式）' },
  { value: 'night_owl', label: 'night_owl（午后速览 + 深夜汇总）' },
  { value: 'custom', label: 'custom（自定义）' },
];

// ==================== 主组件 ====================
export default function Settings() {
  const [config, setConfig] = useState({});
  const [activeTab, setActiveTab] = useState('app');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState({});

  // ---------- 加载配置 ----------
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

  // ---------- 保存模块 ----------
  const saveModule = async (moduleKey, value) => {
    setSaving((prev) => ({ ...prev, [moduleKey]: true }));
    try {
      const res = await updateConfigModule(moduleKey, value);
      if (res?.success) {
        message.success(`[${TAB_META[moduleKey]?.label || moduleKey}] 配置已保存`);
        setConfig((prev) => ({ ...prev, [moduleKey]: value }));
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

  // ---------- 字段变更处理（支持嵌套路径如 crawler.request_interval）----------
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

    // 立即更新本地状态（乐观更新）
    setConfig((prev) => ({ ...prev, [moduleKey]: current }));
    // 立即调用 API 保存
    saveModule(moduleKey, current);
  };

  // ---------- 获取嵌套字段值 ----------
  const getFieldValue = (moduleKey, fieldPath) => {
    try {
      let v = config[moduleKey];
      for (const p of fieldPath.split('.')) {
        if (v && typeof v === 'object') v = v[p];
        else return undefined;
      }
      return v;
    } catch {
      return undefined;
    }
  };

  // ==================== App 模块渲染 ====================
  const renderApp = () => {
    const app = config.app || {};
    return (
      <Form layout="vertical" size="small">
        <Form.Item
          label={
            <Space>
              <Text strong>时区</Text>
              <GlobalOutlined style={{ color: '#999' }} />
            </Space>
          }
          extra="系统使用的时区，影响所有时间相关计算和显示"
        >
          <Select
            value={app.timezone}
            onChange={(v) => handleFieldChange('app', 'timezone', v)}
            options={TIMEZONE_OPTIONS}
            style={{ width: '100%', maxWidth: 440 }}
          />
        </Form.Item>

        <Divider style={{ margin: '16px 0' }} />

        <Form.Item
          label={
            <Space>
              <Text strong>显示版本更新提示</Text>
              <BellOutlined style={{ color: '#999' }} />
            </Space>
          }
          extra="启动时检查并提示是否有新版本可用"
        >
          <Space>
            <Switch
              size="small"
              checked={app.show_version_update ?? true}
              onChange={(v) => handleFieldChange('app', 'show_version_update', v)}
              loading={saving.app}
            />
            <Tag color={app.show_version_update !== false ? 'green' : 'default'}>
              {app.show_version_update !== false ? '已开启' : '已关闭'}
            </Tag>
          </Space>
        </Form.Item>
      </Form>
    );
  };

  // ==================== Schedule 模块渲染 ====================
  const renderSchedule = () => {
    const schedule = config.schedule || {};
    return (
      <Form layout="vertical" size="small">
        {/* 总开关 */}
        <Card
          size="small"
          style={{ marginBottom: 16, background: '#f9f0ff', borderColor: '#d3adf7' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text strong>调度总开关</Text>
              <Switch
                checked={schedule.enabled ?? true}
                onChange={(v) => handleFieldChange('schedule', 'enabled', v)}
                loading={saving.schedule}
              />
              <Tag color={schedule.enabled !== false ? 'green' : 'default'}>
                {schedule.enabled !== false ? '已启用' : '已禁用'}
              </Tag>
            </Space>
          </div>
        </Card>

        <Form.Item
          label={
            <Space>
              <Text strong>预设调度模式</Text>
              <ScheduleOutlined style={{ color: '#999' }} />
            </Space>
          }
          extra="选择预定义的调度模式，将自动配置各时段的抓取与推送频率"
        >
          <Select
            value={schedule.preset || 'always_on'}
            onChange={(v) => handleFieldChange('schedule', 'preset', v)}
            options={SCHEDULE_PRESET_OPTIONS}
            style={{ width: '100%', maxWidth: 480 }}
          />
        </Form.Item>

        {schedule.preset === 'custom' && (
          <>
            <Divider style={{ margin: '16px 0' }} orientation="left">自定义调度说明</Divider>
            <Paragraph type="secondary" style={{ marginBottom: 16 }}>
              选择 custom 模式后，请前往「系统配置」页面手动编辑 schedule 模块的详细时间表。
              可自定义每个时间段的抓取间隔、推送规则等参数。
            </Paragraph>
          </>
        )}
      </Form>
    );
  };

  // ==================== Advanced 模块渲染 ====================
  const renderAdvanced = () => {
    const adv = config.advanced || {};
    const crawler = adv.crawler || {};
    const rss = adv.rss || {};
    const weight = adv.weight || {};

    return (
      <Form layout="vertical" size="small">
        {/* ---- Debug 开关 ---- */}
        <Card
          size="small"
          style={{ marginBottom: 20, background: '#fff7e6', borderColor: '#ffd591' }}
        >
          <Space>
            <BugOutlined style={{ color: '#fa8c16' }} />
            <Text strong>调试模式</Text>
            <Switch
              size="small"
              checked={adv.debug ?? false}
              onChange={(v) => handleFieldChange('advanced', 'debug', v)}
              loading={saving.advanced}
            />
            <Tag color={adv.debug ? 'orange' : 'default'}>
              {adv.debug ? '已开启' : '已关闭'}
            </Tag>
          </Space>
          <Paragraph type="secondary" style={{ margin: '8px 0 0 0', fontSize: 12 }}>
            开启后将输出详细日志，仅用于问题排查，生产环境不建议开启。
          </Paragraph>
        </Card>

        {/* ---- Crawler 设置 ---- */}
        <Divider orientation="left">
          <Space><RobotOutlined /> 爬虫参数</Space>
        </Divider>

        <Form.Item
          label={<Text strong>请求间隔 (ms)</Text>}
          extra="两次爬取请求之间的最小间隔，单位毫秒"
        >
          <InputNumber
            value={crawler.request_interval}
            min={100}
            max={10000}
            step={100}
            onChange={(v) => handleFieldChange('advanced', 'crawler.request_interval', v)}
            style={{ width: 200 }}
            addonAfter="ms"
          />
        </Form.Item>

        <Form.Item label={<Text strong>使用代理</Text>}>
          <Space>
            <Switch
              size="small"
              checked={crawler.use_proxy ?? false}
              onChange={(v) => handleFieldChange('advanced', 'crawler.use_proxy', v)}
              loading={saving.advanced}
            />
            <Tag color={crawler.use_proxy ? 'blue' : 'default'}>
              {crawler.use_proxy ? '已开启' : '未使用'}
            </Tag>
          </Space>
        </Form.Item>

        {crawler.use_proxy && (
          <Form.Item
            label={<Text strong>默认代理地址</Text>}
            extra="格式示例：http://127.0.0.1:7890 或 socks5://user:pass@host:port"
          >
            <Input
              value={crawler.default_proxy || ''}
              onChange={(e) => handleFieldChange('advanced', 'crawler.default_proxy', e.target.value)}
              placeholder="http://127.0.0.1:7890"
              style={{ maxWidth: 400 }}
            />
          </Form.Item>
        )}

        {/* ---- RSS 设置 ---- */}
        <Divider orientation="left" style={{ marginTop: 24 }}>
          <Space><LinkOutlined /> RSS 参数</Space>
        </Divider>

        <Form.Item
          label={<Text strong>RSS 请求间隔 (s)</Text>}
          extra="RSS Feed 轮询间隔，单位秒"
        >
          <InputNumber
            value={rss.request_interval}
            min={10}
            max={3600}
            step={10}
            onChange={(v) => handleFieldChange('advanced', 'rss.request_interval', v)}
            style={{ width: 180 }}
            addonAfter="秒"
          />
        </Form.Item>

        <Form.Item
          label={<Text strong>RSS 超时时间 (s)</Text>}
          extra="单次 RSS 请求的最大等待时间"
        >
          <InputNumber
            value={rss.timeout}
            min={5}
            max={120}
            step={5}
            onChange={(v) => handleFieldChange('advanced', 'rss.timeout', v)}
            style={{ width: 160 }}
            addonAfter="秒"
          />
        </Form.Item>

        <Form.Item label={<Text strong>RSS 使用代理</Text>}>
          <Space>
            <Switch
              size="small"
              checked={rss.use_proxy ?? false}
              onChange={(v) => handleFieldChange('advanced', 'rss.use_proxy', v)}
              loading={saving.advanced}
            />
            <Tag color={rss.use_proxy ? 'blue' : 'default'}>
              {rss.use_proxy ? '已开启' : '未使用'}
            </Tag>
          </Space>
        </Form.Item>

        {/* ---- 权重设置 ---- */}
        <Divider orientation="left" style={{ marginTop: 24 }}>
          <Space><BarChartOutlined /> 排名权重</Space>
        </Divider>

        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          调整各项指标在综合排名中的权重占比。三个权重值之和无需归一化，系统会自动按比例计算。
        </Paragraph>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          <Form.Item label={<Space><Text strong>排名权重</Text><Text type="secondary">(rank)</Text></Space>}>
            <InputNumber
              value={weight.rank}
              min={0}
              max={1}
              step={0.1}
              onChange={(v) => handleFieldChange('advanced', 'weight.rank', v)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label={<Space><Text strong>频率权重</Text><Text type="secondary">(frequency)</Text></Space>}>
            <InputNumber
              value={weight.frequency}
              min={0}
              max={1}
              step={0.1}
              onChange={(v) => handleFieldChange('advanced', 'weight.frequency', v)}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item label={<Space><Text strong>热度权重</Text><Text type="secondary">(hotness)</Text></Space>}>
            <InputNumber
              value={weight.hotness}
              min={0}
              max={1}
              step={0.1}
              onChange={(v) => handleFieldChange('advanced', 'weight.hotness', v)}
              style={{ width: '100%' }}
            />
          </Form.Item>
        </div>
      </Form>
    );
  };

  // ==================== Tab 内容分发 ====================
  const renderTabContent = (key) => {
    switch (key) {
      case 'app': return renderApp();
      case 'schedule': return renderSchedule();
      case 'advanced': return renderAdvanced();
      default: return null;
    }
  };

  // ==================== Tab Items 定义 ====================
  const tabItems = Object.values(TAB_META).map((tab) => ({
    key: tab.key,
    label: (
      <span>
        {tab.icon} {tab.label}
      </span>
    ),
    children: (
      <div>
        {/* Tab 标题区：标题 + 描述 + 状态标签 */}
        <div style={{ marginBottom: 20 }}>
          <Space align="center" size="middle">
            <Typography.Title level={4} style={{ margin: 0 }}>
              {tab.icon} {tab.label}
            </Typography.Title>
            {saving[tab.key] ? (
              <Tag color="processing">保存中...</Tag>
            ) : (
              <Tag icon={<CheckCircleOutlined />} color="success">已就绪</Tag>
            )}
          </Space>
          <Paragraph type="secondary" style={{ marginTop: 6, marginBottom: 0 }}>
            {tab.description}
          </Paragraph>
        </div>

        <Divider style={{ margin: '0 0 20px 0' }} />

        {renderTabContent(tab.key)}
      </div>
    ),
  }));

  // ==================== 渲染 ====================
  return (
    <Content style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>系统设置</span>
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

          <div style={{ minHeight: 400, padding: '4px 0' }}>
            {/* 内容由 Tabs children 渲染，此处保留占位以维持布局稳定 */}
          </div>
        </Spin>
      </Card>
    </Content>
  );
}
