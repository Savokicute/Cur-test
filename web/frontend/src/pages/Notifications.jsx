// src/pages/Notifications.jsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Switch,
  Tag,
  Space,
  Modal,
  message,
  Spin,
  Empty,
  Typography,
  Tooltip,
  Badge,
  List,
  Avatar,
} from 'antd';
import {
  PlusOutlined,
  BellOutlined,
  SendOutlined,
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  GlobalOutlined,
  ApiOutlined,
  MailOutlined,
  DingtalkOutlined,
  WechatOutlined,
  SlackOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import CreateSubscriptionModal from '../components/notifications/CreateSubscriptionModal';
import NotificationLogPanel from '../components/notifications/NotificationLogPanel';
import notificationsApi from '../services/notifications';

const { Text, Title, Paragraph } = Typography;

// 订阅类型配置
const SUBSCRIPTION_TYPES = {
  rss: {
    icon: <GlobalOutlined />,
    label: 'RSS',
    color: 'orange',
  },
  webhook: {
    icon: <ApiOutlined />,
    label: 'Webhook',
    color: 'blue',
  },
  email: {
    icon: <MailOutlined />,
    label: '邮件',
    color: 'green',
  },
  dingtalk: {
    icon: <DingtalkOutlined />,
    label: '钉钉',
    color: '#0089ff',
  },
  wechat_work: {
    icon: <WechatOutlined />,
    label: '企微',
    color: '#07c160',
  },
  slack: {
    icon: <SlackOutlined />,
    label: 'Slack',
    color: '#4a154b',
  },
};

export default function Notifications() {
  const [loading, setLoading] = useState(false);
  const [subscriptions, setSubscriptions] = useState([]);
  const [stats, setStats] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSubscription, setEditingSubscription] = useState(null);
  const [logPanelVisible, setLogPanelVisible] = useState(false);
  const [selectedSubscriptionId, setSelectedSubscriptionId] = useState(null);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [subsResult, statsResult] = await Promise.all([
        notificationsApi.getSubscriptions({ limit: 100 }),
        notificationsApi.getNotificationStats(),
      ]);

      if (subsResult?.data) {
        setSubscriptions(subsResult.data);
      }
      if (statsResult?.data) {
        setStats(statsResult.data);
      }
    } catch (error) {
      message.error('加载数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 创建订阅
  const handleCreate = () => {
    setEditingSubscription(null);
    setModalVisible(true);
  };

  // 编辑订阅
  const handleEdit = (subscription) => {
    setEditingSubscription(subscription);
    setModalVisible(true);
  };

  // 删除订阅
  const handleDelete = (subscription) => {
    Modal.confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除订阅 "${subscription.name}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await notificationsApi.deleteSubscription(subscription.id);
          message.success('删除成功');
          loadData();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  // 切换启用状态
  const handleToggleActive = async (subscription) => {
    try {
      await notificationsApi.updateSubscription(subscription.id, {
        is_active: !subscription.is_active,
      });
      message.success(`${subscription.is_active ? '已禁用' : '已启用'}`);
      loadData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  // 手动触发
  const handleTrigger = async (subscription) => {
    try {
      message.loading({ content: '正在发送通知...', key: `trigger-${subscription.id}` });
      const result = await notificationsApi.triggerSubscription(subscription.id);

      if (result?.success) {
        message.success({ content: '通知发送成功', key: `trigger-${subscription.id}` });
        loadData();
      } else {
        message.error({ content: result?.message || '发送失败', key: `trigger-${subscription.id}` });
      }
    } catch (error) {
      message.error({ content: '触发失败', key: `trigger-${subscription.id}` });
    }
  };

  // 测试发送
  const handleTest = async (subscription) => {
    try {
      message.loading({ content: '正在测试发送...', key: `test-${subscription.id}` });
      const result = await notificationsApi.testSubscription(subscription.id);

      if (result?.success) {
        message.success({
          content: `测试成功！耗时 ${result.duration_seconds}s`,
          key: `test-${subscription.id}`,
        });
      } else {
        message.error({
          content: result?.error || '测试失败',
          key: `test-${subscription.id}`,
        });
      }
    } catch (error) {
      message.error({ content: '测试失败', key: `test-${subscription.id}` });
    }
  };

  // 查看日志
  const handleViewLogs = (subscriptionId) => {
    setSelectedSubscriptionId(subscriptionId);
    setLogPanelVisible(true);
  };

  // 模态框回调
  const handleModalSuccess = () => {
    setModalVisible(false);
    setEditingSubscription(null);
    loadData();
  };

  // 格式化时间
  const formatTime = (timeStr) => {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 脱敏显示URL
  const maskUrl = (url) => {
    if (!url) return '-';
    try {
      const urlObj = new URL(url);
      return `${urlObj.protocol}//${urlObj.hostname}${urlObj.pathname ? '/...' : ''}`;
    } catch {
      return url.length > 40 ? url.substring(0, 40) + '...' : url;
    }
  };

  return (
    <div className="notifications-page">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="总订阅数"
              value={stats?.total_subscriptions || 0}
              prefix={<BellOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="活跃订阅"
              value={stats?.active_subscriptions || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="今日触发次数"
              value={stats?.today_triggers || 0}
              prefix={<SendOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="成功率"
              value={stats?.success_rate || 0}
              suffix="%"
              precision={1}
              valueStyle={{
                color: (stats?.success_rate || 0) >= 90 ? '#52c41a' : '#faad14',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              通知订阅列表
            </Title>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadData}>
                刷新
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                创建订阅
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 订阅列表 */}
      <Spin spinning={loading}>
        {subscriptions.length === 0 && !loading ? (
          <Empty
            description="暂无订阅配置"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              创建第一个订阅
            </Button>
          </Empty>
        ) : (
          <List
            grid={{ gutter: 16, xs: 1, sm: 1, md: 2, lg: 2, xl: 3 }}
            dataSource={subscriptions}
            renderItem={(item) => {
              const typeConfig = SUBSCRIPTION_TYPES[item.subscription_type] || SUBSCRIPTION_TYPES.webhook;

              return (
                <List.Item>
                  <Card
                    hoverable
                    actions={[
                      <Tooltip title="编辑">
                        <Button
                          type="text"
                          icon={<EditOutlined />}
                          onClick={() => handleEdit(item)}
                        />
                      </Tooltip>,
                      <Tooltip title="测试">
                        <Button
                          type="text"
                          icon={<SendOutlined />}
                          onClick={() => handleTest(item)}
                        />
                      </Tooltip>,
                      <Tooltip title="手动触发">
                        <Button
                          type="text"
                          icon={<PlayCircleOutlined />}
                          onClick={() => handleTrigger(item)}
                        />
                      </Tooltip>,
                      <Tooltip title="查看日志">
                        <Button
                          type="text"
                          icon={<FileTextOutlined />}
                          onClick={() => handleViewLogs(item.id)}
                        />
                      </Tooltip>,
                      <Tooltip title="删除">
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => handleDelete(item)}
                        />
                      </Tooltip>,
                    ]}
                  >
                    <Card.Meta
                      avatar={
                        <Avatar
                          style={{
                            backgroundColor: typeConfig.color,
                            fontSize: 20,
                          }}
                          icon={typeConfig.icon}
                        />
                      }
                      title={
                        <Space>
                          <Text strong>{item.name}</Text>
                          <Tag color={typeConfig.color}>{typeConfig.label}</Tag>
                          {!item.is_active && <Tag color="default">已禁用</Tag>}
                        </Space>
                      }
                      description={
                        <div style={{ marginTop: 8 }}>
                          <div style={{ marginBottom: 4 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              目标地址:
                            </Text>
                            <br />
                            <Text code style={{ fontSize: 11 }}>
                              {maskUrl(item.target_url)}
                            </Text>
                          </div>

                          <Row gutter={8} style={{ marginTop: 8, fontSize: 12 }}>
                            <Col span={12}>
                              <Text type="secondary">最后触发:</Text>
                              <br />
                              <Text>{formatTime(item.last_triggered_at)}</Text>
                            </Col>
                            <Col span={12}>
                              <Text type="secondary">成功率:</Text>
                              <br />
                              <Text style={{ color: item.success_rate >= 80 ? '#52c41a' : '#faad14' }}>
                                {item.success_rate}%
                              </Text>
                              <span style={{ marginLeft: 8, color: '#999' }}>
                                ({item.success_count}/{item.total_triggers})
                              </span>
                            </Col>
                          </Row>

                          <div style={{ marginTop: 8 }}>
                            <Switch
                              size="small"
                              checked={item.is_active}
                              onChange={() => handleToggleActive(item)}
                              checkedChildren="启用"
                              unCheckedChildren="禁用"
                            />
                            <Text type="secondary" style={{ marginLeft: 8 }}>
                              {item.trigger_mode === 'scheduled'
                                ? item.schedule_cron || '定时任务'
                                : item.trigger_mode === 'event'
                                  ? '事件触发'
                                  : '手动触发'}
                            </Text>
                          </div>
                        </div>
                      }
                    />
                  </Card>
                </List.Item>
              );
            }}
          />
        )}
      </Spin>

      {/* 创建/编辑弹窗 */}
      <CreateSubscriptionModal
        visible={modalVisible}
        subscription={editingSubscription}
        onSuccess={handleModalSuccess}
        onCancel={() => {
          setModalVisible(false);
          setEditingSubscription(null);
        }}
      />

      {/* 日志面板 */}
      <NotificationLogPanel
        visible={logPanelVisible}
        subscriptionId={selectedSubscriptionId}
        onClose={() => {
          setLogPanelVisible(false);
          setSelectedSubscriptionId(null);
        }}
      />
    </div>
  );
}
