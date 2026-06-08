// src/components/notifications/CreateSubscriptionModal.jsx
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Radio,
  Button,
  Space,
  Tabs,
  Card,
  Row,
  Col,
  InputNumber,
  Tag,
  Typography,
  Alert,
  Divider,
  message,
} from 'antd';
import {
  GlobalOutlined,
  ApiOutlined,
  MailOutlined,
  DingtalkOutlined,
  WechatOutlined,
  SlackOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import notificationsApi from '../../services/notifications';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const SUBSCRIPTION_TYPE_OPTIONS = [
  { value: 'rss', label: 'RSS', icon: <GlobalOutlined />, color: 'orange' },
  { value: 'webhook', label: 'Webhook', icon: <ApiOutlined />, color: 'blue' },
  { value: 'email', label: '邮件', icon: <MailOutlined />, color: 'green' },
  { value: 'dingtalk', label: '钉钉', icon: <DingtalkOutlined />, color: '#0089ff' },
  { value: 'wechat_work', label: '企业微信', icon: <WechatOutlined />, color: '#07c160' },
  { value: 'slack', label: 'Slack', icon: <SlackOutlined />, color: '#4a154b' },
];

const PLATFORM_OPTIONS = [
  { value: 'baidu', label: '百度' },
  { value: 'weibo', label: '微博' },
  { value: 'zhihu', label: '知乎' },
  { value: 'toutiao', label: '今日头条' },
  { value: 'bilibili-hot-search', label: 'B站' },
  { value: 'douyin', label: '抖音' },
  { value: 'thepaper', label: '澎湃' },
];

const TRIGGER_MODE_OPTIONS = [
  { value: 'manual', label: '手动触发' },
  { value: 'scheduled', label: '定时执行' },
  { value: 'event', label: '事件触发（新热榜到达时）' },
];

const DEFAULT_TEMPLATES = [
  {
    name: '简洁列表',
    content: `🔥 {{date}} 热点速递

{% for item in items %}
{{loop.index}}. {{item.title}}
   🔗 {{item.url}}
   📊 热度: {{item.hot_score}}
   📍 {{item.platform}}
{% endfor %}

---
由 TrendRadar 自动生成`,
  },
  {
    name: 'Markdown 格式',
    content: `# 🔥 {{date}} 热点速递

## 统计概览
- 总条目数: {{items|length}}
- 最高热度: {% if items %}{{items[0].hot_score}}{% endif %}

## 热点列表

{% for item in items %}
### {{loop.index}}. {{item.title}}

- **热度**: {{item.hot_score}}
- **平台**: {{item.platform}}
- **链接**: [查看详情]({{item.url}})
{% endfor %}

---

*由 TrendRadar 自动生成 | {{generated_at}}*`,
  },
];

export default function CreateSubscriptionModal({ visible, subscription, onSuccess, onCancel }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');
  const [selectedType, setSelectedType] = useState('webhook');

  // 编辑模式：填充表单
  useEffect(() => {
    if (visible) {
      if (subscription) {
        // 编辑模式
        form.setFieldsValue({
          name: subscription.name,
          description: subscription.description,
          subscription_type: subscription.subscription_type,
          target_url: subscription.target_url,
          trigger_mode: subscription.trigger_mode,
          schedule_cron: subscription.schedule_cron,
          is_active: subscription.is_active,
          format_template: subscription.format_template || DEFAULT_TEMPLATES[0].content,

          // 过滤条件
          include_keywords: subscription.filter_config?.include_keywords?.join(', ') || '',
          exclude_keywords: subscription.filter_config?.exclude_keywords?.join(', ') || '',
          platforms: subscription.filter_config?.platforms || [],
          min_hot_score: subscription.filter_config?.min_hot_score || 0,
          max_items: subscription.filter_config?.max_items || 50,

          // 目标配置
          auth_type: subscription.target_config?.auth_type || 'none',
          token: '', // 不回显敏感信息
          msg_type: subscription.target_config?.msg_type || 'text',
          at_all: subscription.target_config?.at_all || false,
          channel: subscription.target_config?.channel || '#general',
          feed_title: subscription.target_config?.feed_title || '',
          feed_description: subscription.target_config?.feed_description || '',
        });
        setSelectedType(subscription.subscription_type);
      } else {
        // 创建模式：重置表单
        form.resetFields();
        form.setFieldsValue({
          subscription_type: 'webhook',
          trigger_mode: 'manual',
          is_active: true,
          format_template: DEFAULT_TEMPLATES[0].content,
          auth_type: 'none',
          max_items: 50,
        });
        setSelectedType('webhook');
      }
      setActiveTab('basic');
    }
  }, [visible, subscription, form]);

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 构建请求数据
      const data = {
        name: values.name.trim(),
        description: values.description?.trim(),
        subscription_type: values.subscription_type,
        target_url: values.target_url?.trim(),
        trigger_mode: values.trigger_mode,
        schedule_cron: values.schedule_cron,
        is_active: values.is_active,
        format_template: values.format_template,

        filter_config: {
          include_keywords: values.include_keywords
            ? values.include_keywords.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
            : undefined,
          exclude_keywords: values.exclude_keywords
            ? values.exclude_keywords.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
            : undefined,
          platforms: values.platforms,
          min_hot_score: values.min_hot_score,
          max_items: values.max_items,
        },

        target_config: {},
      };

      // 根据类型添加特定配置
      if (['webhook', 'dingtalk', 'wechat_work', 'slack'].includes(values.subscription_type)) {
        data.target_config.auth_type = values.auth_type;
        data.target_config.token = values.token;
        data.target_config.msg_type = values.msg_type;
      }

      if (values.subscription_type === 'dingtalk') {
        data.target_config.at_all = values.at_all;
      }

      if (values.subscription_type === 'slack') {
        data.target_config.channel = values.channel;
      }

      if (values.subscription_type === 'rss') {
        data.target_config.feed_title = values.feed_title;
        data.target_config.feed_description = values.feed_description;
        data.target_config.max_items = values.max_items;
      }

      // 调用API
      if (subscription) {
        await notificationsApi.updateSubscription(subscription.id, data);
        message.success('订阅更新成功');
      } else {
        await notificationsApi.createSubscription(data);
        message.success('订阅创建成功');
      }

      onSuccess?.();

    } catch (error) {
      if (error.errorFields) {
        // 表单验证错误，不处理
        return;
      }
      console.error(error);
      message.error(subscription ? '更新失败' : '创建失败');
    } finally {
      setLoading(false);
    }
  };

  // 根据类型渲染特定的配置字段
  const renderTypeSpecificFields = () => {
    switch (selectedType) {
      case 'rss':
        return (
          <>
            <Form.Item label="输出路径" name="target_url" extra="RSS文件保存路径">
              <Input placeholder="/var/www/rss/feed.xml" />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="Feed 标题" name="feed_title">
                  <Input placeholder="TrendRadar 热点推送" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="Feed 描述" name="feed_description">
                  <Input placeholder="实时热点信息聚合" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="最大条目数" name="max_items">
              <InputNumber min={1} max={200} style={{ width: '100%' }} />
            </Form.Item>
          </>
        );

      case 'webhook':
        return (
          <>
            <Form.Item
              label="Webhook URL"
              name="target_url"
              rules={[{ required: true, message: '请输入 Webhook URL' }]}
            >
              <Input placeholder="https://your-webhook-url.com/api/notify" />
            </Form.Item>
            <Form.Item label="认证方式" name="auth_type">
              <Select>
                <Select.Option value="none">无认证</Select.Option>
                <Select.Option value="bearer">Bearer Token</Select.Option>
                <Select.Option value="basic">Basic Auth</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(prev, cur) => prev.auth_type !== cur.auth_type}>
              {({ getFieldValue }) =>
                getFieldValue('auth_type') && getFieldValue('auth_type') !== 'none' ? (
                  <Form.Item
                    label={getFieldValue('auth_type') === 'bearer' ? 'Token' : '密码'}
                    name="token"
                  >
                    <Input.Password placeholder={getFieldValue('auth_type') === 'bearer' ? '输入 Bearer Token' : '输入密码'} />
                  </Form.Item>
                ) : null
              }
            </Form.Item>
          </>
        );

      case 'email':
        return (
          <>
            <Alert
              type="info"
              showIcon
              icon={<InfoCircleOutlined />}
              message="邮件功能需要配置 SMTP 服务后才能使用"
              style={{ marginBottom: 16 }}
            />
            <Form.Item label="收件人" name={['target_config', 'recipients']}>
              <Select mode="tags" placeholder="输入邮箱地址，按回车添加" />
            </Form.Item>
            <Form.Item label="主题模板" name={['target_config', 'subject']}>
              <Input placeholder="🔥 热点速递 - {{date}}" />
            </Form.Item>
          </>
        );

      case 'dingtalk':
        return (
          <>
            <Form.Item
              label="Webhook URL"
              name="target_url"
              rules={[{ required: true, message: '请输入钉钉机器人 Webhook URL' }]}
            >
              <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx" />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="消息类型" name="msg_type">
                  <Select>
                    <Select.Option value="text">文本</Select.Option>
                    <Select.Option value="markdown">Markdown</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="@所有人" name="at_all" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
            </Row>
          </>
        );

      case 'wechat_work':
        return (
          <>
            <Form.Item
              label="Webhook URL"
              name="target_url"
              rules={[{ required: true, message: '请输入企业微信机器人 Webhook URL' }]}
            >
              <Input placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx" />
            </Form.Item>
            <Form.Item label="消息类型" name="msg_type">
              <Select>
                <Select.Option value="text">文本</Select.Option>
                <Select.Option value="markdown">Markdown</Select.Option>
              </Select>
            </Form.Item>
          </>
        );

      case 'slack':
        return (
          <>
            <Form.Item
              label="Webhook URL"
              name="target_url"
              rules={[{ required: true, message: '请输入 Slack Webhook URL' }]}
            >
              <Input placeholder="https://hooks.slack.com/services/Txxx/Bxxx/xxx" />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item label="频道" name="channel">
                  <Input placeholder="#general" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="用户名" name={['target_config', 'username']}>
                  <Input placeholder="TrendRadar Bot" />
                </Form.Item>
              </Col>
            </Row>
          </>
        );

      default:
        return null;
    }
  };

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: (
        <>
          <Form.Item
            label="订阅名称"
            name="name"
            rules={[{ required: true, message: '请输入订阅名称' }]}
          >
            <Input placeholder="例如：每日热点推送" maxLength={256} showCount />
          </Form.Item>

          <Form.Item label="描述" name="description">
            <TextArea rows={2} placeholder="可选：描述此订阅的用途" maxLength={500} showCount />
          </Form.Item>

          <Form.Item
            label="订阅类型"
            name="subscription_type"
            rules={[{ required: true, message: '请选择订阅类型' }]}
          >
            <Select
              onChange={setSelectedType}
              options={SUBSCRIPTION_TYPE_OPTIONS.map((opt) => ({
                value: opt.value,
                label: (
                  <Space>
                    <span style={{ color: opt.color }}>{opt.icon}</span>
                    {opt.label}
                  </Space>
                ),
              }))}
            />
          </Form.Item>

          {/* 类型特定配置 */}
          {renderTypeSpecificFields()}

          <Divider>调度设置</Divider>

          <Form.Item label="触发模式" name="trigger_mode">
            <Radio.Group options={TRIGGER_MODE_OPTIONS} optionType="button" buttonStyle="solid" />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.trigger_mode !== cur.trigger_mode}>
            {({ getFieldValue }) =>
              getFieldValue('trigger_mode') === 'scheduled' ? (
                <Form.Item
                  label="Cron 表达式"
                  name="schedule_cron"
                  extra="例如: 0 9 * * * 表示每天9:00执行"
                  rules={[{ required: true, message: '定时任务需要 Cron 表达式' }]}
                >
                  <Input placeholder="0 9 * * *" />
                </Form.Item>
              ) : null
            }
          </Form.Item>

          <Form.Item label="启用状态" name="is_active" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'filter',
      label: '过滤条件',
      children: (
        <>
          <Alert
            type="info"
            showIcon
            message="设置过滤条件以控制推送的内容范围"
            style={{ marginBottom: 16 }}
          />

          <Form.Item label="包含关键词">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Form.Item name="include_keywords" noStyle>
                <Input placeholder="用逗号分隔多个关键词，如：AI,科技,财经" />
              </Form.Item>
              <Text type="secondary" style={{ fontSize: 12 }}>
                只推送标题中包含这些关键词的热点
              </Text>
            </Space>
          </Form.Item>

          <Form.Item label="排除关键词">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Form.Item name="exclude_keywords" noStyle>
                <Input placeholder="用逗号分隔多个关键词，如：广告,推广" />
              </Form.Item>
              <Text type="secondary" style={{ fontSize: 12 }}>
                排除标题中包含这些关键词的热点
              </Text>
            </Space>
          </Form.Item>

          <Form.Item label="平台过滤">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Form.Item name="platforms" noStyle>
                <Select
                  mode="multiple"
                  placeholder="选择要监控的平台"
                  options={PLATFORM_OPTIONS}
                />
              </Form.Item>
              <Text type="secondary" style={{ fontSize: 12 }}>
                只推送来自选中平台的热点
              </Text>
            </Space>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="最低热度分数" name="min_hot_score">
                <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="最大推送条目数" name="max_items">
                <InputNumber min={1} max={500} style={{ width: '100%' }} placeholder="50" />
              </Form.Item>
            </Col>
          </Row>
        </>
      ),
    },
    {
      key: 'template',
      label: '内容模板',
      children: (
        <>
          <Alert
            type="info"
            showIcon
            message={
              <Space direction="vertical" size={0}>
                <span>支持 Jinja2 模板语法</span>
                <Text code>可用变量:</Text>
                <div>
                  {['{{title}}', '{{url}}', '{{summary}}', '{{hot_score}}', '{{platform}}', '{{rank}}', '{{date}}', '{{generated_at}}'].map(
                    (v) => (
                      <Tag key={v}>{v}</Tag>
                    )
                  )}
                </div>
              </Space>
            }
            style={{ marginBottom: 16 }}
          />

          <Form.Item label="预设模板">
            <Space wrap>
              {DEFAULT_TEMPLATES.map((t) => (
                <Button
                  key={t.name}
                  size="small"
                  onClick={() => form.setFieldsValue({ format_template: t.content })}
                >
                  {t.name}
                </Button>
              ))}
            </Space>
          </Form.Item>

          <Form.Item
            label="自定义模板"
            name="format_template"
            rules={[{ required: true, message: '请输入内容模板' }]}
          >
            <TextArea
              rows={15}
              placeholder="输入自定义模板内容..."
              style={{ fontFamily: 'monospace', fontSize: 13 }}
            />
          </Form.Item>

          <Card size="small" title="实时预览" style={{ marginTop: 8 }}>
            <Paragraph
              style={{
                background: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                whiteSpace: 'pre-wrap',
                maxHeight: 300,
                overflow: 'auto',
                fontSize: 13,
              }}
            >
              {form.getFieldValue('format_template')
                ?.replace(/\{\{date\}\}/g, new Date().toLocaleDateString('zh-CN'))
                .replace(/\{\{generated_at\}\}/g, new Date().toLocaleString('zh-CN'))
                .replace(/\{% for item in items %\}.*\{% endfor \%\}/gs, '  [预览内容将在实际发送时渲染]') ||
                '请在上方输入模板内容'}
            </Paragraph>
          </Card>
        </>
      ),
    },
  ];

  return (
    <Modal
      title={subscription ? '编辑订阅' : '创建新订阅'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      confirmLoading={loading}
      width={720}
      okText={subscription ? '更新' : '创建'}
      cancelText="取消"
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          subscription_type: 'webhook',
          trigger_mode: 'manual',
          is_active: true,
          auth_type: 'none',
          max_items: 50,
        }}
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Form>
    </Modal>
  );
}

// 需要导入 Radio 组件（Ant Design 5.x）
// 如果使用 Ant Design 4.x，可能需要从 antd 导入 Radio
