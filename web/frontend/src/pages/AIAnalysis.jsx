import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Statistic,
  Row,
  Col,
  Select,
  DatePicker,
  Input,
  message,
  Empty,
  Spin,
  Pagination,
  Modal,
  Tooltip,
  Badge,
  Alert,
  Dropdown,
} from 'antd';
import {
  Plus,
  FileText,
  Brain,
  TrendingUp,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Eye,
  Trash2,
  RefreshCw,
  Filter,
  Zap,
  LayoutTemplate,
  BarChart3,
  Calendar as CalendarIcon,
  Search,
  MoreVertical,
  Download,
} from 'lucide-react';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import PageHeader, { StatusBadge } from '../components/common/PageHeader';
import CreateAnalysisModal from '../components/ai/CreateAnalysisModal';
import ReportDetail from '../components/ai/ReportDetail';
import {
  getAnalysisReports,
  getAnalysisStats,
  deleteAnalysisReport,
  triggerAnalysis,
  getSystemTemplates,
  useTemplate,
} from '../services/aiAnalysis';

dayjs.extend(relativeTime);

const { Text, Title, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Search: AntSearch } = Input;

/**
 * AIAnalysis - AI分析推送热榜信息页
 *
 * 这是项目的核心差异化功能页面，提供：
 * - 顶部统计卡片：总报告数、成功数、今日生成、平均耗时
 * - 操作工具栏：新建分析、使用模板、状态筛选、时间范围
 * - 报告列表：Table 展示，支持分页和筛选
 * - 空状态引导：首次使用时显示引导提示
 */
const AIAnalysis = () => {
  // ========== 状态定义 ==========
  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState({});
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState(undefined);
  const [dateRange, setDateRange] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  // 弹窗状态
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [reportDetailVisible, setReportDetailVisible] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState(null);

  // ========== 数据加载 ==========

  /**
   * 加载报告列表
   */
  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        pageSize: pageSize,
      };

      if (statusFilter) params.status = statusFilter;
      if (dateRange && dateRange[0]) {
        params.startDate = dateRange[0].format('YYYY-MM-DD');
        if (dateRange[1]) {
          params.endDate = dateRange[1].format('YYYY-MM-DD');
        }
      }

      const response = await getAnalysisReports(params);

      if (response?.success) {
        setReports(response.data.items || []);
        setTotal(response.data.total || 0);
      }
    } catch (error) {
      console.error('加载报告列表失败:', error);
      message.error('加载报告列表失败');
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, statusFilter, dateRange]);

  /**
   * 加载统计数据
   */
  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const response = await getAnalysisStats();
      if (response?.success) {
        setStats(response.data || {});
      }
    } catch (error) {
      console.error('加载统计失败:', error);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  /**
   * 加载预设模板
   */
  const fetchTemplates = useCallback(async () => {
    try {
      const response = await getSystemTemplates();
      if (response?.success) {
        setTemplates(response.data.items || []);
      }
    } catch (error) {
      console.error('加载模板失败:', error);
    }
  }, []);

  // 初始化加载数据
  useEffect(() => {
    fetchReports();
    fetchStats();
    fetchTemplates();
  }, [fetchReports, fetchStats, fetchTemplates]);

  // ========== 事件处理 ==========

  /**
   * 打开创建弹窗
   */
  const handleOpenCreate = () => {
    setCreateModalVisible(true);
  };

  /**
   * 创建成功回调
   */
  const handleCreateSuccess = async (config) => {
    message.success(`配置 "${config.name}" 创建成功`);

    // 可选：自动触发一次分析
    try {
      const response = await triggerAnalysis(config.id);
      if (response?.success) {
        message.info('已自动启动首次分析，请稍候查看结果');
        // 刷新报告列表
        setTimeout(() => {
          setCurrentPage(1);
          fetchReports();
          fetchStats();
        }, 1000);
      }
    } catch (error) {
      console.error('自动触发失败:', error);
    }
  };

  /**
   * 使用模板快速创建
   */
  const handleUseTemplate = async (templateId) => {
    try {
      const response = await useTemplate(templateId);
      if (response?.success) {
        message.success(`已基于模板创建配置: ${response.data.name}`);
        // 刷新数据
        fetchReports();
        fetchStats();
      }
    } catch (error) {
      console.error('使用模板失败:', error);
      message.error('使用模板失败');
    }
  };

  /**
   * 查看报告详情
   */
  const handleViewReport = (reportId) => {
    setSelectedReportId(reportId);
    setReportDetailVisible(true);
  };

  /**
   * 删除报告
   */
  const handleDeleteReport = async (reportId) => {
    try {
      const confirmed = await new Promise((resolve) => {
        Modal.confirm({
          title: '确认删除',
          content: '确定要删除这个报告吗？此操作不可恢复。',
          okText: '删除',
          okType: 'danger',
          cancelText: '取消',
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        });
      });

      if (!confirmed) return;

      const response = await deleteAnalysisReport(reportId);
      if (response?.success) {
        message.success('报告已删除');
        fetchReports();
        fetchStats();

        // 如果当前查看的正是被删除的报告，关闭详情
        if (selectedReportId === reportId) {
          setReportDetailVisible(false);
          setSelectedReportId(null);
        }
      }
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败');
    }
  };

  /**
   * 重新生成报告
   */
  const handleRegenerate = async (record) => {
    if (!record.config_id) {
      message.warning('该报告没有关联的配置，无法重新生成');
      return;
    }

    try {
      message.loading('正在触发重新分析...', 0);
      const response = await triggerAnalysis(record.config_id, record.input_params);
      message.destroy();

      if (response?.success) {
        message.success('已触发重新分析，新报告将在后台生成');
        // 延迟刷新以显示新报告
        setTimeout(() => {
          fetchReports();
          fetchStats();
        }, 2000);
      }
    } catch (error) {
      message.destroy();
      console.error('重新生成失败:', error);
      message.error('重新生成失败');
    }
  };

  /**
   * 分页变化
   */
  const handlePageChange = (page, size) => {
    setCurrentPage(page);
    setPageSize(size);
  };

  /**
   * 重置筛选条件
   */
  const handleResetFilters = () => {
    setStatusFilter(undefined);
    setDateRange(null);
    setSearchQuery('');
    setCurrentPage(1);
    message.info('已重置筛选条件');
  };

  // ========== 表格列定义 ==========

  const columns = [
    {
      title: '报告标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text, record) => (
        <a onClick={() => handleViewReport(record.id)}>
          <Space>
            <FileText size={14} />
            <span>{text || `报告 #${record.id}`}</span>
          </Space>
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      filters: [
        { text: '等待中', value: 'pending' },
        { text: '分析中', value: 'running' },
        { text: '已完成', value: 'completed' },
        { text: '失败', value: 'failed' },
      ],
      render: (status) => {
        const config = {
          pending: { color: 'default', icon: <Clock size={12} />, text: '等待中' },
          running: { color: 'processing', icon: <Loader2 size={12} className="spin" />, text: '分析中' },
          completed: { color: 'success', icon: <CheckCircle2 size={12} />, text: '已完成' },
          failed: { color: 'error', icon: <XCircle size={12} />, text: '失败' },
        };
        const item = config[status] || config.pending;
        return <Tag color={item.color} icon={item.icon}>{item.text}</Tag>;
      },
    },
    {
      title: '配置名称',
      dataIndex: 'config_name',
      key: 'config_name',
      width: 150,
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: '处理条目',
      dataIndex: 'total_items',
      key: 'total_items',
      width: 90,
      align: 'center',
      render: (val) => val ?? 0,
    },
    {
      title: '耗时',
      key: 'duration',
      width: 80,
      align: 'center',
      render: (_, record) =>
        record.duration_seconds != null
          ? `${record.duration_seconds.toFixed(1)}s`
          : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
      render: (text) => (
        <Tooltip title={dayjs(text).format('YYYY-MM-DD HH:mm:ss')}>
          <span>{dayjs(text).fromNow()}</span>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              size="small"
              icon={<Eye size={14} />}
              onClick={() => handleViewReport(record.id)}
            />
          </Tooltip>

          {(record.status === 'completed' || record.status === 'failed') && (
            <Tooltip title="重新生成">
              <Button
                type="text"
                size="small"
                icon={<RefreshCw size={14} />}
                onClick={() => handleRegenerate(record)}
              />
            </Tooltip>
          )}

          <Tooltip title="删除">
            <Button
              type="text"
              size="small"
              danger
              icon={<Trash2 size={14} />}
              onClick={() => handleDeleteReport(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // ========== 搜索过滤逻辑 ==========

  const filteredReports = useMemo(() => {
    if (!searchQuery.trim()) return reports;

    const query = searchQuery.toLowerCase();
    return reports.filter(
      (report) =>
        (report.title || '').toLowerCase().includes(query) ||
        (report.config_name || '').toLowerCase().includes(query) ||
        (report.summary || '').toLowerCase().includes(query)
    );
  }, [reports, searchQuery]);

  // ========== 渲染 ==========

  return (
    <div className="ai-analysis-page">
      {/* 页面头部 */}
      <PageHeader
        title="AI 分析"
        description="利用 AI 智能分析热榜数据，生成深度洞察报告"
        tags={
          <StatusBadge status={stats.running_reports > 0 ? 'active' : 'ok'} text={
            stats.running_reports > 0
              ? `${stats.running_reports} 个任务运行中`
              : '就绪'
          } />
        }
      />

      {/* 统计卡片区域 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <Card size="small" bordered={false} className="stat-card">
            <Statistic
              title="总报告数"
              value={stats.total_reports || 0}
              prefix={<FileText size={18} style={{ color: '#1677ff' }} />}
              valueStyle={{ fontSize: 24 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" bordered={false} className="stat-card">
            <Statistic
              title="成功完成"
              value={stats.completed_reports || 0}
              prefix={<CheckCircle2 size={18} style={{ color: '#52c41a' }} />}
              valueStyle={{ fontSize: 24, color: '#52c41a' }}
              suffix={
                stats.total_reports > 0
                  ? `(${stats.success_rate || 0}%)`
                  : null
              }
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" bordered={false} className="stat-card">
            <Statistic
              title="今日生成"
              value={stats.today_reports || 0}
              prefix={<TrendingUp size={18} style={{ color: '#faad14' }} />}
              valueStyle={{ fontSize: 24, color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small" bordered={false} className="stat-card">
            <Statistic
              title="平均耗时"
              value={stats.avg_duration_seconds || 0}
              prefix={<Clock size={18} style={{ color: '#722ed1' }} />}
              suffix="秒"
              valueStyle={{ fontSize: 24 }}
              precision={1}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作工具栏 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div className="toolbar">
          {/* 左侧操作按钮 */}
          <div className="toolbar-left">
            <Space wrap>
              <Button
                type="primary"
                icon={<Plus size={16} />}
                onClick={handleOpenCreate}
              >
                新建分析
              </Button>

              {/* 快速使用模板 */}
              {templates.length > 0 && (
                <Dropdown
                  menu={{
                    items: templates.map((t) => ({
                      key: t.id,
                      label: (
                        <Space>
                          <LayoutTemplate size={14} />
                          <span>{t.name}</span>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            ({t.usage_count}次)
                          </Text>
                        </Space>
                      ),
                      onClick: () => handleUseTemplate(t.id),
                    })),
                  }}
                  placement="bottomLeft"
                >
                  <Button icon={<LayoutTemplate size={16} />}>
                    使用模板
                  </Button>
                </Dropdown>
              )}
            </Space>
          </div>

          {/* 右侧筛选控件 */}
          <div className="toolbar-right">
            <Space wrap size="middle">
              {/* 状态筛选 */}
              <Select
                placeholder="状态筛选"
                allowClear
                style={{ width: 120 }}
                value={statusFilter}
                onChange={(value) => {
                  setStatusFilter(value);
                  setCurrentPage(1);
                }}
                options={[
                  { value: 'pending', label: '等待中' },
                  { value: 'running', label: '分析中' },
                  { value: 'completed', label: '已完成' },
                  { value: 'failed', label: '失败' },
                ]}
              />

              {/* 日期范围选择 */}
              <RangePicker
                value={dateRange}
                onChange={(dates) => {
                  setDateRange(dates);
                  setCurrentPage(1);
                }}
                placeholder={['开始日期', '结束日期']}
                style={{ width: 240 }}
              />

              {/* 搜索框 */}
              <AntSearch
                placeholder="搜索报告..."
                allowClear
                style={{ width: 180 }}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onSearch={() => setCurrentPage(1)}
              />

              {/* 重置按钮 */}
              {(statusFilter || dateRange || searchQuery) && (
                <Button
                  type="link"
                  size="small"
                  onClick={handleResetFilters}
                >
                  重置筛选
                </Button>
              )}
            </Space>
          </div>
        </div>
      </Card>

      {/* 首次使用引导提示（当没有任何报告时） */}
      {!loading && total === 0 && !searchQuery && !statusFilter && (
        <Alert
          message="开始您的第一次 AI 分析"
          description={
            <div>
              <p>您还没有创建过任何分析报告。</p>
              <ul style={{ paddingLeft: 20, margin: '8px 0' }}>
                <li>点击「新建分析」创建自定义分析配置</li>
                <li>或点击「使用模板」快速开始（推荐）</li>
                <li>系统将自动采集热榜数据并生成专业分析报告</li>
              </ul>
            </div>
          }
          type="info"
          showIcon
          closable
          style={{ marginBottom: 16 }}
          action={
            <Button type="primary" size="small" onClick={handleOpenCreate}>
              立即开始
            </Button>
          }
        />
      )}

      {/* 报告表格 */}
      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={filteredReports}
          rowKey="id"
          pagination={false}
          size="middle"
          scroll={{ x: 900 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  searchQuery
                    ? `未找到匹配 "${searchQuery}" 的报告`
                    : '暂无分析报告'
                }
              >
                {!searchQuery && (
                  <Button type="primary" onClick={handleOpenCreate}>
                    创建第一个分析
                  </Button>
                )}
              </Empty>
            ),
          }}
        />

        {/* 分页器 */}
        {total > pageSize && (
          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Pagination
              current={currentPage}
              pageSize={pageSize}
              total={filteredReports.length > 0 ? filteredReports.length : total}
              onChange={handlePageChange}
              showSizeChanger
              showQuickJumper
              showTotal={(totalNum, range) =>
                `第 ${range[0]}-${range[1]} 条，共 ${totalNum} 条`
              }
              size="small"
            />
          </div>
        )}
      </Spin>

      {/* 创建分析弹窗 */}
      <CreateAnalysisModal
        visible={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onSuccess={handleCreateSuccess}
        templates={templates}
      />

      {/* 报告详情抽屉 */}
      <ReportDetail
        visible={reportDetailVisible}
        reportId={selectedReportId}
        onClose={() => {
          setReportDetailVisible(false);
          setSelectedReportId(null);
          // 关闭后刷新列表
          fetchReports();
          fetchStats();
        }}
        onDelete={() => {
          fetchReports();
          fetchStats();
        }}
      />

      {/* 样式定义 */}
      <style jsx>{`
        .ai-analysis-page {
          max-width: 1400px;
          margin: 0 auto;
        }

        .stat-card {
          background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
          border-radius: 8px;
          transition: transform 0.2s;
        }

        .stat-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }

        .toolbar-left {
          display: flex;
          align-items: center;
        }

        .toolbar-right {
          display: flex;
          align-items: center;
        }

        /* 动画效果 */
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .spin {
          animation: spin 1s linear infinite;
          display: inline-block;
        }

        /* 表格行悬停效果 */
        :global(.ant-table-tbody > tr:hover > td) {
          background: #e6f4ff !important;
        }

        /* 响应式适配 */
        @media (max-width: 768px) {
          .toolbar {
            flex-direction: column;
            align-items: stretch;
          }

          .toolbar-left,
          .toolbar-right {
            justify-content: space-between;
          }

          :global(.ant-statistic-title) {
            font-size: 13px;
          }

          :global(.ant-statistic-content-value) {
            font-size: 20px !important;
          }
        }
      `}</style>
    </div>
  );
};

export default AIAnalysis;
