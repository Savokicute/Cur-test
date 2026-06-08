import React, { useState, useEffect, useMemo } from 'react';
import {
  Layout,
  Card,
  Tabs,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Switch,
  InputNumber,
  message,
  Empty,
  Spin,
  Select,
  Tooltip,
  Popconfirm,
  Descriptions,
  Badge,
  Divider,
  Typography,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SaveOutlined,
  ReloadOutlined,
  GlobalOutlined,
  SettingOutlined,
  CloudServerOutlined,
  LinkOutlined,
  ScheduleOutlined,
  FilterOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  getHotSources,
  updateHotSources,
  getWebsiteSources,
  addWebsiteSource,
  updateWebsiteSource,
  deleteWebsiteSource,
  getPlatformStatus,
  retryPlatform,
} from '../services/sources';
import { updateConfigModule, getConfigModule } from '../services/config';

const { Content } = Layout;
const { Text, Paragraph } = Typography;

export default function Sources() {
  const [activeTab, setActiveTab] = useState('1');

  // ========== 热榜平台状态 (platforms) ==========
  const [platformsData, setPlatformsData] = useState(null);
  const [platformsLoading, setPlatformsLoading] = useState(false);
  const [platformStatus, setPlatformStatus] = useState(null); // 各平台采集状态
  const [retryingPlatformId, setRetryingPlatformId] = useState(null); // 正在重试的平台

  // ========== RSS订阅状态 (rss) ==========
  const [rssData, setRssData] = useState(null);          // DB feeds 数据
  const [rssConfigYaml, setRssConfigYaml] = useState(null); // config.yaml rss 段
  const [rssLoading, setRssLoading] = useState(false);
  const [rssModalVisible, setRssModalVisible] = useState(false);
  const [editingFeed, setEditingFeed] = useState(null);
  const [rssForm] = Form.useForm();

  // ========== 调度系统状态 (schedule) ==========
  const [scheduleData, setScheduleData] = useState(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);

  // ========== 筛选策略状态 (filter) ==========
  const [filterData, setFilterData] = useState(null);
  const [filterLoading, setFilterLoading] = useState(false);

  // ==================== 加载数据方法 ====================

  // 加载热榜平台配置
  const loadPlatformsConfig = async () => {
    setPlatformsLoading(true);
    try {
      const res = await getHotSources();
      if (res?.success && res.data) {
        const rawData = res.data;
        setPlatformsData({
          hotSourcesEnabled: rawData.hotSourcesEnabled ?? rawData.enabled ?? true,
          availablePlatforms: Array.isArray(rawData.availablePlatforms)
            ? rawData.availablePlatforms
            : (Array.isArray(rawData.sources)
              ? rawData.sources.map((s) => ({
                  id: s.id,
                  name: s.name || s.id,
                  enabled: s.enabled !== false,
                }))
              : []),
        });
      }
    } catch (error) {
      console.error('Error loading platforms config:', error);
      message.error('加载平台配置失败');
    } finally {
      setPlatformsLoading(false);
    }
  };

  // 加载RSS配置（config.yaml 设置 + DB feeds）
  const loadRssConfig = async () => {
    setRssLoading(true);
    try {
      const [yamlRes, dbRes] = await Promise.all([
        getConfigModule('rss').catch(() => null),
        getWebsiteSources().catch(() => null),
      ]);

      if (yamlRes?.success && yamlRes.data?.value) {
        setRssConfigYaml(yamlRes.data.value);
      } else {
        setRssConfigYaml({ enabled: true, freshness_filter: { enabled: true, max_age_days: 1 }, feeds: [] });
      }

      if (dbRes?.success) {
        setRssData({
          enabled: dbRes.data.enabled ?? true,
          freshness_filter: dbRes.data.freshness_filter || { enabled: true, max_age_days: 1 },
          feeds: dbRes.data.feeds || [],
        });
      } else {
        setRssData({ enabled: true, freshness_filter: { enabled: true, max_age_days: 1 }, feeds: [] });
      }
    } catch (error) {
      console.error('Error loading RSS config:', error);
      message.error('加载RSS配置失败');
    } finally {
      setRssLoading(false);
    }
  };

  // 加载调度系统配置（模拟数据）
  const loadScheduleConfig = async () => {
    setScheduleLoading(true);
    try {
      const res = await getConfigModule('schedule');
      if (res?.success && res.data?.value) {
        setScheduleData(res.data.value);
      } else {
        setScheduleData({
          enabled: true,
          preset: 'morning_evening',
        });
      }
    } catch (error) {
      console.error('Error loading schedule config:', error);
      setScheduleData({ enabled: true, preset: 'morning_evening' });
    } finally {
      setScheduleLoading(false);
    }
  };

  // 加载筛选策略配置（模拟数据）
  const loadFilterConfig = async () => {
    setFilterLoading(true);
    try {
      const res = await getConfigModule('filter');
      if (res?.success && res.data?.value) {
        setFilterData(res.data.value);
      } else {
        setFilterData({
          method: 'ai',
          priority_sort_enabled: true,
          ai_filter: {
            batch_size: 200,
            batch_interval: 2,
            min_score: 0.7,
            reclassify_threshold: 0.6,
          },
        });
      }
    } catch (error) {
      console.error('Error loading filter config:', error);
      setFilterData({
        method: 'ai', priority_sort_enabled: true,
        ai_filter: { batch_size: 200, batch_interval: 2, min_score: 0.7, reclassify_threshold: 0.6 },
      });
    } finally {
      setFilterLoading(false);
    }
  };

  // ==================== 保存/操作方法 ====================

  // 保存热榜平台配置（仅保存总开关）
  const savePlatformsConfig = async () => {
    if (!platformsData) {
      message.warning('没有可保存的配置数据');
      return;
    }
    try {
      const res = await updateHotSources({
        hotSourcesEnabled: platformsData.hotSourcesEnabled,
      });
      if (res?.success) {
        message.success('平台配置已保存');
        loadPlatformsConfig();
      } else {
        message.error(res?.message || '保存失败：服务器返回异常');
      }
    } catch (error) {
      console.error('Error saving platforms config:', error);
      message.error(error?.response?.data?.message || error?.message || '保存失败，请稍后重试');
    }
  };

  // 切换单个平台启用状态（自动保存到后端）— 已移除，统一由总开关控制

  // 加载平台采集状态
  const loadPlatformStatus = async () => {
    try {
      const res = await getPlatformStatus();
      if (res?.success && res.data) {
        setPlatformStatus(res.data);
      }
    } catch (error) {
      console.error('Error loading platform status:', error);
    }
  };

  // 合并平台列表与采集状态（纯计算，无 setState，不会触发循环）
  const mergedPlatforms = useMemo(() => {
    if (!platformsData?.availablePlatforms) return null;
    if (!platformStatus?.platforms) return platformsData.availablePlatforms;
    const statusMap = {};
    platformStatus.platforms.forEach(p => { statusMap[p.id] = p; });
    return platformsData.availablePlatforms.map(p => ({
      ...p,
      _status: statusMap[p.id]?.status || 'pending',
      _newsCount: statusMap[p.id]?.news_count || 0,
      _failedCount: statusMap[p.id]?.failed_count || 0,
    }));
  }, [platformsData?.availablePlatforms, platformStatus]);

  // 重试指定平台
  const handleRetryPlatform = async (platformId, mode = 'quick') => {
    if (retryingPlatformId === platformId) return;
    setRetryingPlatformId(platformId);
    try {
      const res = await retryPlatform(platformId, mode);
      if (res?.success) {
        message.success(res.message || `已触发 "${platformId}" 重试`);
        // 3秒后刷新状态
        setTimeout(() => loadPlatformStatus(), 3000);
      } else {
        message.error(res?.message || '重试失败');
      }
    } catch (error) {
      console.error('Error retrying platform:', error);
      message.error(error?.response?.data?.detail || '重试请求失败');
    } finally {
      setRetryingPlatformId(null);
    }
  };

  // 切换平台总开关（自动保存到后端）
  const togglePlatformsEnabled = async () => {
    if (!platformsData) return;
    const newEnabled = !platformsData.hotSourcesEnabled;
    setPlatformsData({ ...platformsData, hotSourcesEnabled: newEnabled });
    try {
      const res = await updateHotSources({
        hotSourcesEnabled: newEnabled,
      });
      if (res?.success) {
        message.success(newEnabled ? '热榜抓取已启用' : '热榜抓取已禁用');
      } else {
        message.error(res?.message || '保存失败');
        // 回滚
        setPlatformsData({ ...platformsData, hotSourcesEnabled: !newEnabled });
      }
    } catch (error) {
      console.error('Error toggling platforms:', error);
      message.error('操作失败');
      setPlatformsData({ ...platformsData, hotSourcesEnabled: !newEnabled });
    }
  };

  // ========== 添加平台弹窗状态 ==========
  const [platformModalVisible, setPlatformModalVisible] = useState(false);
  const [platformForm] = Form.useForm();

  // 添加平台（真正实现）
  const handleAddPlatform = () => {
    platformForm.resetFields();
    setPlatformModalVisible(true);
  };

  // 确认添加平台（自动保存到后端）
  const confirmAddPlatform = async () => {
    try {
      const values = await platformForm.validateFields();
      if (!platformsData) return;

      const exists = platformsData.availablePlatforms.some((p) => p.id === values.platformId);
      if (exists) {
        message.warning(`平台 "${values.platformId}" 已存在`);
        return;
      }

      const newPlatform = {
        id: values.platformId,
        name: values.platformName || values.platformId,
        enabled: true,
      };

      const updatedPlatforms = [...platformsData.availablePlatforms, newPlatform];
      setPlatformsData({
        ...platformsData,
        availablePlatforms: updatedPlatforms,
      });
      setPlatformModalVisible(false);

      // 立即同步到后端
      try {
        const res = await updateHotSources({
          hotSourcesEnabled: platformsData.hotSourcesEnabled,
          enabledPlatforms: updatedPlatforms.map((p) => ({
            id: p.id,
            name: p.name,
            enabled: p.enabled,
          })),
        });
        if (res?.success) {
          message.success(`平台 "${values.platformName || values.platformId}" 已添加并同步`);
        } else {
          message.warning('已添加到本地列表，但同步后端失败，请手动保存');
        }
      } catch (err) {
        console.error('Sync new platform to backend failed:', err);
        message.warning('已添加到本地列表，但同步后端失败，请手动保存');
      }
    } catch (error) {
      // 表单验证失败
    }
  };

  // 删除平台
  const handleDeletePlatform = (platformId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个平台吗？',
      okType: 'danger',
      onOk: async () => {
        if (!platformsData) return;
        const updatedPlatforms = platformsData.availablePlatforms.filter((p) => p.id !== platformId);
        setPlatformsData({ ...platformsData, availablePlatforms: updatedPlatforms });
        message.success('平台已删除');
      },
    });
  };

  // 保存RSS总开关（写入 config.yaml）
  const saveRssEnabled = async (enabled) => {
    if (!rssConfigYaml) return;
    const updated = { ...rssConfigYaml, enabled };
    setRssConfigYaml(updated);
    try {
      await updateConfigModule('rss', updated);
      message.success(`RSS抓取已${enabled ? '启用' : '禁用'}`);
    } catch (error) {
      console.error('Error saving RSS enabled:', error);
      message.error('同步RSS开关失败');
    }
  };

  // 保存新鲜度过滤配置（写入 config.yaml）
  const saveFreshnessFilter = async (field, value) => {
    if (!rssConfigYaml) return;
    const updatedFreshness = { ...(rssConfigYaml.freshness_filter || {}), [field]: value };
    const updated = { ...rssConfigYaml, freshness_filter: updatedFreshness };
    setRssConfigYaml(updated);
    try {
      await updateConfigModule('rss', updated);
    } catch (error) {
      console.error('Error saving freshness filter:', error);
      message.error('同步新鲜度配置失败');
    }
  };

  // 打开RSS Feed编辑弹窗
  const openRssModal = (feed = null) => {
    setEditingFeed(feed);
    rssForm.resetFields();
    if (feed) {
      rssForm.setFieldsValue(feed);
    }
    setRssModalVisible(true);
  };

  // 保存RSS Feed
  const saveRssFeed = async () => {
    try {
      const values = await rssForm.validateFields();
      if (editingFeed) {
        await updateWebsiteSource(editingFeed.id, values);
        message.success('Feed已更新');
      } else {
        await addWebsiteSource(values);
        message.success('Feed已添加');
      }
      setRssModalVisible(false);
      loadRssConfig();
    } catch (error) {
      // 表单验证失败或API错误
    }
  };

  // 删除RSS Feed
  const handleDeleteFeed = (feedId) => {
    Popconfirm({
      title: '确定删除？',
      onConfirm: async () => {
        try {
          await deleteWebsiteSource(feedId);
          message.success('Feed已删除');
          loadRssConfig();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  // 保存调度配置
  const saveScheduleConfig = async () => {
    if (!scheduleData) return;
    try {
      const res = await updateConfigModule('schedule', scheduleData);
      if (res?.success) {
        message.success('调度配置已保存并同步');
      } else {
        message.error(res?.message || '保存失败');
      }
    } catch (error) {
      console.error('Error saving schedule config:', error);
      message.error('保存调度配置失败');
    }
  };

  // 保存筛选策略
  const saveFilterConfig = async () => {
    if (!filterData) return;
    try {
      const res = await updateConfigModule('filter', filterData);
      if (res?.success) {
        message.success('筛选策略已保存并同步');
      } else {
        message.error(res?.message || '保存失败');
      }
    } catch (error) {
      console.error('Error saving filter config:', error);
      message.error('保存筛选策略失败');
    }
  };

  useEffect(() => {
    loadPlatformsConfig();
    loadRssConfig();
    loadScheduleConfig();
    loadFilterConfig();
    loadPlatformStatus();
  }, []);

  // ==================== 表格列定义 ====================

  const renderStatusTag = (status, failedCount = 0) => {
    switch (status) {
      case 'success':
        return <Tag icon={<CheckCircleOutlined />} color="success">正常</Tag>;
      case 'partial':
        return <Tooltip title={`${failedCount} 条正文爬取失败`}>
          <Tag icon={<WarningOutlined />} color="warning">部分失败</Tag>
        </Tooltip>;
      case 'failed':
        return <Tag icon={<ExclamationCircleOutlined />} color="error">失败</Tag>;
      case 'pending':
      default:
        return <Tag icon={<ClockCircleOutlined />}>待采集</Tag>;
    }
  };

  const platformColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 200 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '状态',
      key: '_status',
      width: 110,
      render: (_, record) => renderStatusTag(record._status, record._failedCount),
    },
    {
      title: '热榜数',
      key: '_newsCount',
      width: 80,
      align: 'center',
      render: (_, record) => record._newsCount ?? '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          {(record._status === 'failed' || record._status === 'partial') && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              loading={retryingPlatformId === record.id}
              onClick={() => handleRetryPlatform(record.id)}
            >
              重试
            </Button>
          )}
          {record._status === 'success' && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetryPlatform(record.id)}
            >
              重新采集
            </Button>
          )}
          {!record._status || record._status === 'pending' && (
            <Button
              type="primary"
              size="small"
              icon={<ReloadOutlined />}
              loading={retryingPlatformId === record.id}
              onClick={() => handleRetryPlatform(record.id)}
            >
              采集
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const rssFeedColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 140 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
    {
      title: '启用',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (e) => <Tag color={e ? 'green' : 'default'}>{e ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '最大年龄(天)',
      dataIndex: 'max_age_days',
      key: 'max_age_days',
      width: 120,
      render: (v) => (v != null ? v : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, r) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openRssModal(r)}>
            编辑
          </Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDeleteFeed(r.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Content style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>采集源配置</span>
          </Space>
        }
        bordered={false}
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}
          items={[
            {
              key: '1',
              label: <span><CloudServerOutlined />热榜平台</span>,
              children: (
                <Spin spinning={platformsLoading}>
                  {platformsData && (
                    <div>
                      {/* 总开关 + 刷新状态 */}
                      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Space>
                          <Text strong>热榜抓取：</Text>
                          <Switch checked={platformsData.hotSourcesEnabled} onChange={togglePlatformsEnabled} />
                          <Tag color={platformsData.hotSourcesEnabled ? 'green' : 'default'}>
                            {platformsData.hotSourcesEnabled ? '已启用' : '已禁用'}
                          </Tag>
                        </Space>
                        <Space>
                          <Button
                            icon={<ReloadOutlined />}
                            onClick={loadPlatformStatus}
                            size="small"
                          >
                            刷新状态
                          </Button>
                          {platformStatus?.date && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              数据日期: {platformStatus.date}
                            </Text>
                          )}
                        </Space>
                      </div>

                      {/* 平台列表（只读，状态来自采集结果） */}
                      <Table
                        columns={platformColumns}
                        dataSource={mergedPlatforms}
                        rowKey="id"
                        pagination={false}
                        size="middle"
                      />

                      <div style={{ marginTop: 12, color: '#888', fontSize: 12 }}>
                        共 {mergedPlatforms?.length || 0} 个平台（由 config.yaml 定义）
                      </div>

                      {/* 无数据提示 */}
                      {!platformStatus?.db_exists && (
                        <Alert
                          message="暂无今日采集数据"
                          description="请启动采集流水线（start_platform.py --once）后再查看平台状态"
                          type="info"
                          showIcon
                          style={{ marginTop: 12 }}
                        />
                      )}
                    </div>
                  )}
                </Spin>
              ),
            },
            {
              key: '2',
              label: <span><LinkOutlined />RSS订阅</span>,
              children: (
                <Spin spinning={rssLoading}>
                  {rssConfigYaml && rssData && (
                    <div>
                      {/* config.yaml 中的 RSS 配置（可编辑，同步到后端） */}
                      <Alert
                        message="以下配置来自 config.yaml，修改后直接保存至文件"
                        type="info"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />

                      <div style={{ marginBottom: 24, padding: 16, background: '#fafafa', borderRadius: 8 }}>
                        <Space style={{ marginBottom: 12 }}>
                          <Text strong>RSS 抓取（config.yaml）：</Text>
                          <Switch
                            checked={rssConfigYaml.enabled}
                            onChange={(checked) => saveRssEnabled(checked)}
                          />
                          <Tag color={rssConfigYaml.enabled ? 'green' : 'default'}>
                            {rssConfigYaml.enabled ? '已启用' : '已禁用'}
                          </Tag>
                        </Space>

                        {/* 新鲜度过滤配置 */}
                        <Divider orientation="left" plain>新鲜度过滤</Divider>
                        <Space align="center" size="large">
                          <Space>
                            <Text>启用：</Text>
                            <Switch
                              size="small"
                              checked={rssConfigYaml.freshness_filter?.enabled}
                              onChange={(checked) => saveFreshnessFilter('enabled', checked)}
                            />
                          </Space>
                          <Space>
                            <Text>最大年龄（天）：</Text>
                            <InputNumber
                              min={0}
                              max={365}
                              value={rssConfigYaml.freshness_filter?.max_age_days ?? 1}
                              onChange={(value) => saveFreshnessFilter('max_age_days', value)}
                              style={{ width: 80 }}
                            />
                          </Space>
                        </Space>
                      </div>

                      {/* config.yaml 中定义的 Feeds（只读展示） */}
                      <div style={{ marginBottom: 24 }}>
                        <Text strong style={{ display: 'block', marginBottom: 8 }}>
                          config.yaml 中的 Feed 定义
                          <Tag color="blue" style={{ marginLeft: 8 }}>来自配置文件</Tag>
                        </Text>
                        {(rssConfigYaml.feeds?.length > 0) ? (
                          <Table
                            columns={[
                              { title: 'ID', dataIndex: 'id', key: 'id', width: 160 },
                              { title: '名称', dataIndex: 'name', key: 'name' },
                              { title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true },
                              {
                                title: '状态',
                                dataIndex: 'enabled',
                                key: 'enabled',
                                width: 80,
                                render: (e) => <Tag color={e !== false ? 'green' : 'default'}>{e !== false ? '启用' : '禁用'}</Tag>,
                              },
                            ]}
                            dataSource={rssConfigYaml.feeds}
                            rowKey="id"
                            pagination={false}
                            size="small"
                          />
                        ) : (
                          <Empty description="config.yaml 中暂无 Feed 定义（TrendRadar 不采集 RSS）" />
                        )}
                      </div>

                      {/* 数据库中的网站源（独立管理，用于 Web 展示/扩展） */}
                      <Divider>数据库中的网站源（WebsiteSource 表）</Divider>
                      <div style={{ marginBottom: 16, textAlign: 'right' }}>
                        <Button icon={<PlusOutlined />} onClick={() => openRssModal()}>
                          添加网站源
                        </Button>
                      </div>

                      {rssData.feeds.length > 0 ? (
                        <Table
                          columns={rssFeedColumns}
                          dataSource={rssData.feeds}
                          rowKey="id"
                          pagination={false}
                          size="small"
                        />
                      ) : (
                        <Empty description="数据库中暂无网站源" />
                      )}
                    </div>
                  )}
                </Spin>
              ),
            },
            {
              key: '3',
              label: <span><ScheduleOutlined />调度系统</span>,
              children: (
                <Spin spinning={scheduleLoading}>
                  {scheduleData && (
                    <div style={{ maxWidth: 600 }}>
                      <div style={{ marginBottom: 24, padding: 24, background: '#fafafa', borderRadius: 8 }}>
                        <Space direction="vertical" size="large" style={{ width: '100%' }}>
                          {/* 启用开关 */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Space>
                              <Text strong>启用调度系统</Text>
                              <Tooltip title="开启后可按预设时间自动执行任务">
                                <Text type="secondary" style={{ fontSize: 12 }}>(?)</Text>
                              </Tooltip>
                            </Space>
                            <Switch
                              checked={scheduleData.enabled}
                              onChange={(checked) => setScheduleData({ ...scheduleData, enabled: checked })}
                            />
                          </div>

                          <Divider />

                          {/* 预设选择 */}
                          <div>
                            <Text strong style={{ display: 'block', marginBottom: 12 }}>预设模板</Text>
                            <Select
                              value={scheduleData.preset}
                              onChange={(value) => setScheduleData({ ...scheduleData, preset: value })}
                              style={{ width: '100%' }}
                              options={[
                                { value: 'always_on', label: 'always_on - 全天候，有新增即推送' },
                                { value: 'morning_evening', label: 'morning_evening - 全天推送 + 晚间当日汇总（推荐）' },
                                { value: 'office_hours', label: 'office_hours - 工作日三段式，周末增量自由推' },
                                { value: 'night_owl', label: 'night_owl - 午后速览 + 深夜全天汇总' },
                                { value: 'custom', label: 'custom - 完全自定义' },
                              ]}
                            />

                            {/* 预设说明 */}
                            <Paragraph
                              type="secondary"
                              style={{
                                marginTop: 12,
                                fontSize: 12,
                                lineHeight: 1.6,
                                padding: 12,
                                background: '#fff',
                                borderRadius: 4,
                                border: '1px solid #f0f0f0',
                              }}
                            >
                              {scheduleData.preset === 'always_on' && '全天候运行，有新增内容即触发推送通知。'}
                              {scheduleData.preset === 'morning_evening' && '全天推送 + 晚间当日汇总。适合大多数用户，兼顾实时性和总结性。'}
                              {scheduleData.preset === 'office_hours' && '工作日按三段式推送（到岗→午间→收工），周末采用增量模式自由推送。适合上班族。'}
                              {scheduleData.preset === 'night_owl' && '午后快速浏览 + 深夜全天汇总。适合夜猫子用户。'}
                              {scheduleData.preset === 'custom' && '完全自定义调度规则，需在 timeline.yaml 中详细配置。'}
                            </Paragraph>
                          </div>

                          <Divider />

                          {/* 保存按钮 */}
                          <Button
                            type="primary"
                            icon={<SaveOutlined />}
                            onClick={saveScheduleConfig}
                            block
                          >
                            保存调度配置
                          </Button>
                        </Space>
                      </div>
                    </div>
                  )}
                </Spin>
              ),
            },
            {
              key: '4',
              label: <span><FilterOutlined />筛选策略</span>,
              children: (
                <Spin spinning={filterLoading}>
                  {filterData && (
                    <div style={{ maxWidth: 700 }}>
                      <div style={{ marginBottom: 24, padding: 24, background: '#fafafa', borderRadius: 8 }}>
                        <Space direction="vertical" size="large" style={{ width: '100%' }}>
                          {/* 方法选择 */}
                          <div>
                            <Text strong style={{ display: 'block', marginBottom: 12 }}>筛选方法</Text>
                            <Select
                              value={filterData.method}
                              onChange={(value) => setFilterData({ ...filterData, method: value })}
                              style={{ width: '100%' }}
                              options={[
                                { value: 'keyword', label: 'keyword - 关键词匹配（基于 frequency_words.txt）' },
                                { value: 'ai', label: 'ai - AI智能分类（基于兴趣描述）' },
                              ]}
                            />

                            {filterData.method === 'ai' && (
                              <Space style={{ marginTop: 12 }}>
                                <Switch
                                  size="small"
                                  checked={filterData.priority_sort_enabled}
                                  onChange={(checked) =>
                                    setFilterData({ ...filterData, priority_sort_enabled: checked })
                                  }
                                />
                                <Text style={{ fontSize: 13 }}>按标签优先级排序</Text>
                              </Space>
                            )}
                          </div>

                          <Divider />

                          {/* AI 配置预览（只读） */}
                          {filterData.method === 'ai' && filterData.ai_filter && (
                            <div>
                              <Text strong style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                                <RobotOutlined />
                                AI 智能筛选配置
                                <Tag color="blue">只读预览</Tag>
                              </Text>

                              <Descriptions bordered column={1} size="small">
                                <Descriptions.Item label="每批处理数量">
                                  {filterData.ai_filter.batch_size} 条
                                </Descriptions.Item>
                                <Descriptions.Item label="分批间隔">
                                  {filterData.ai_filter.batch_interval} 秒
                                </Descriptions.Item>
                                <Descriptions.Item label="最低分数阈值">
                                  <Tag color={filterData.ai_filter.min_score >= 0.7 ? 'red' : 'orange'}>
                                    {filterData.ai_filter.min_score}
                                  </Tag>
                                </Descriptions.Item>
                                <Descriptions.Item label="全量重分类阈值">
                                  {filterData.ai_filter.reclassify_threshold}
                                </Descriptions.Item>
                              </Descriptions>

                              <Paragraph
                                type="secondary"
                                style={{
                                  marginTop: 12,
                                  fontSize: 12,
                                  lineHeight: 1.6,
                                  padding: 12,
                                  background: '#fff',
                                  borderRadius: 4,
                                  border: '1px solid #f0f0f0',
                                }}
                              >
                                <Text strong>说明：</Text>
                                <br />
                                • min_score 越高，结果越"准"但会漏召回（推荐 0.5~0.7）
                                <br />
                                • reclassify_threshold 越低，越倾向全量重分类（更耗 token）
                                <br />
                                • 如需修改这些参数，请直接编辑 config.yaml 文件
                              </Paragraph>
                            </div>
                          )}

                          <Divider />

                          {/* 保存按钮 */}
                          <Button
                            type="primary"
                            icon={<SaveOutlined />}
                            onClick={saveFilterConfig}
                            block
                          >
                            保存筛选策略
                          </Button>
                        </Space>
                      </div>
                    </div>
                  )}
                </Spin>
              ),
            },
          ]}
        />
      </Card>

      {/* RSS Feed 编辑弹窗 */}
      <Modal
        title={editingFeed ? '编辑 Feed' : '添加 Feed'}
        open={rssModalVisible}
        onOk={saveRssFeed}
        onCancel={() => setRssModalVisible(false)}
        width={560}
      >
        <Form form={rssForm} layout="vertical">
          {!editingFeed && (
            <Form.Item label="标识 ID" name="id" rules={[{ required: true, message: '请输入唯一标识' }]}>
              <Input placeholder="如 hacker-news" disabled={!!editingFeed} />
            </Form.Item>
          )}
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="显示名称" />
          </Form.Item>
          <Form.Item label="URL 地址" name="url" rules={[{ required: true, message: '请输入URL' }, { type: 'url', message: '请输入有效URL' }]}>
            <Input placeholder="RSS 订阅地址" />
          </Form.Item>
          <Form.Item label="启用" name="enabled" valuePropName="checked">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item label="最大年龄（天）" name="max_age_days" extra="留空则使用全局默认值">
            <InputNumber min={0} max={365} style={{ width: '100%' }} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加热榜平台弹窗 */}
      <Modal
        title={<span><PlusOutlined /> 添加热榜平台</span>}
        open={platformModalVisible}
        onOk={confirmAddPlatform}
        onCancel={() => setPlatformModalVisible(false)}
        width={480}
      >
        <Alert
          message="平台 ID 需与 config.yaml 中的预设 ID 一致"
          description="常用预设：toutiao(今日头条)、baidu(百度热搜)、weibo(微博)、douyin(抖音)、zhihu(知乎)、bilibili-hot-search(B站热搜)"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={platformForm} layout="vertical">
          <Form.Item
            label="平台 ID"
            name="platformId"
            rules={[{ required: true, message: '请输入平台 ID' }]}
            extra="英文标识，如 weibo、douyin 等"
          >
            <Input placeholder="如：weibo" />
          </Form.Item>
          <Form.Item
            label="显示名称"
            name="platformName"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="如：微博热搜" />
          </Form.Item>
        </Form>
      </Modal>
    </Content>
  );
}
