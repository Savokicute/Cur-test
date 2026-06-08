import React, { useState, useEffect, useCallback } from 'react';
import {
  Drawer,
  Typography,
  Tag,
  Space,
  Button,
  Descriptions,
  Statistic,
  Row,
  Col,
  Card,
  Divider,
  Spin,
  Alert,
  Empty,
  Dropdown,
  message,
  Tooltip,
  Progress,
} from 'antd';
import {
  FileText,
  Download,
  Share2,
  Trash2,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
  Copy,
  Eye,
  BarChart3,
  Calendar,
  Settings,
  ArrowLeft,
} from 'lucide-react';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  getAnalysisReport,
  deleteAnalysisReport,
  triggerAnalysis,
  exportAsMarkdown,
  exportAsText,
  pollReportStatus,
} from '../../services/aiAnalysis';

dayjs.extend(relativeTime);

const { Title, Text, Paragraph } = Typography;

/**
 * ReportDetail - 报告详情展示组件
 *
 * 功能特性：
 * - 报告头部：标题、状态、时间戳、配置信息
 * - 内容区域：Markdown 渲染（react-markdown）
 * - 统计面板：处理条目数、相关条目数、耗时
 * - 操作栏：导出（PDF/Markdown）、分享、删除
 * - 相关热榜链接（点击跳转）
 *
 * @param {Object} props
 * @param {boolean} visible - 是否显示
 * @param {number} reportId - 报告ID
 * @param {Function} onClose - 关闭回调
 * @param {Function} onDelete - 删除成功回调
 */
const ReportDetail = ({
  visible,
  reportId,
  onClose,
  onDelete,
}) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [activeTab, setActiveTab] = useState('content'); // 'content' | 'stats' | 'params'

  // 加载报告详情
  const loadReport = useCallback(async (id) => {
    if (!id) return;

    setLoading(true);
    try {
      const response = await getAnalysisReport(id);
      if (response?.success && response?.data) {
        setReport(response.data);
      } else {
        message.error('加载报告失败');
      }
    } catch (error) {
      console.error('加载报告失败:', error);
      message.error('加载报告失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 当 reportId 变化时加载报告
  useEffect(() => {
    if (visible && reportId) {
      loadReport(reportId);

      // 如果报告还在运行中，启动轮询
      setPolling(true);
    }

    return () => {
      setPolling(false); // 清理轮询
    };
  }, [visible, reportId, loadReport]);

  // 轮询正在运行的报告
  useEffect(() => {
    if (!polling || !reportId || !visible) return;

    let isCancelled = false;

    const startPolling = async () => {
      await pollReportStatus(
        reportId,
        (updatedReport) => {
          if (isCancelled) return;

          setReport(updatedReport);

          // 如果完成或失败，停止轮询
          if (updatedReport.status === 'completed' || updatedReport.status === 'failed') {
            setPolling(false);
            message.success(
              updatedReport.status === 'completed'
                ? '分析任务已完成'
                : `分析失败: ${updatedReport.error_message || '未知错误'}`
            );
          }
        },
        3000,  // 3秒轮询一次
        120     // 最多6分钟
      );
    };

    startPolling();

    return () => {
      isCancelled = true;
    };
  }, [polling, reportId, visible]);

  /**
   * 获取状态标签配置
   */
  const getStatusConfig = (status) => {
    const configs = {
      pending: { color: 'default', icon: <Clock size={14} />, text: '等待中' },
      running: { color: 'processing', icon: <Loader2 size={14} className="spin" />, text: '分析中' },
      completed: { color: 'success', icon: <CheckCircle2 size={14} />, text: '已完成' },
      failed: { color: 'error', icon: <XCircle size={14} />, text: '失败' },
      timeout: { color: 'warning', icon: <Clock size={14} />, text: '超时' },
    };

    return configs[status] || { color: 'default', icon: null, text: status };
  };

  /**
   * 删除报告
   */
  const handleDelete = async () => {
    if (!report?.id) return;

    try {
      const confirmed = window.confirm('确定要删除这个报告吗？此操作不可恢复。');
      if (!confirmed) return;

      const response = await deleteAnalysisReport(report.id);
      if (response?.success) {
        message.success('报告已删除');
        onClose?.();
        onDelete?.(report.id);
      } else {
        message.error('删除失败');
      }
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败');
    }
  };

  /**
   * 重新生成报告
   */
  const handleRegenerate = async () => {
    if (!report?.config_id) return;

    try {
      const response = await triggerAnalysis(report.config_id, report.input_params);
      if (response?.success) {
        message.success('已触发重新分析，请稍候...');
        // 切换到新报告
        onClose?.();
        // 可以选择跳转到新报告
        setTimeout(() => {
          loadReport(response.data.report_id);
        }, 500);
      } else {
        message.error('触发失败');
      }
    } catch (error) {
      console.error('重新生成失败:', error);
      message.error('重新生成失败');
    }
  };

  /**
   * 导出操作菜单
   */
  const exportMenuItems = [
    {
      key: 'markdown',
      label: (
        <Space>
          <FileText size={16} />
          导出为 Markdown (.md)
        </Space>
      ),
      onClick: () => {
        if (report) {
          exportAsMarkdown(report);
          message.success('导出成功');
        }
      },
    },
    {
      key: 'text',
      label: (
        <Space>
          <Download size={16} />
          导出为纯文本 (.txt)
        </Space>
      ),
      onClick: () => {
        if (report) {
          exportAsText(report);
          message.success('导出成功');
        }
      },
    },
    {
      key: 'copy',
      label: (
        <Space>
          <Copy size={16} />
          复制到剪贴板
        </Space>
      ),
      onClick: () => {
        if (report?.content) {
          navigator.clipboard.writeText(report.content)
            .then(() => message.success('已复制'))
            .catch(() => message.error('复制失败'));
        }
      },
    },
  ];

  // 如果没有报告ID，不渲染
  if (!reportId) return null;

  const statusConfig = getStatusConfig(report?.status);

  return (
    <Drawer
      title={
        <Space>
          <FileText size={20} />
          <span>报告详情</span>
        </Space>
      }
      open={visible}
      onClose={onClose}
      width={720}
      destroyOnClose
      extra={
        <Space>
          {/* 操作按钮组 */}
          <Dropdown menu={{ items: exportMenuItems }} placement="bottomRight">
            <Button icon={<Download size={16} />}>
              导出
            </Button>
          </Dropdown>

          <Tooltip title="分享">
            <Button
              type="text"
              icon={<Share2 size={16} />}
              onClick={() => message.info('分享功能开发中')}
            />
          </Tooltip>

          {(report?.status === 'completed' || report?.status === 'failed') && (
            <Tooltip title="重新生成">
              <Button
                type="text"
                icon={<RefreshCw size={16} />}
                onClick={handleRegenerate}
                disabled={!report?.config_id}
              />
            </Tooltip>
          )}

          <Tooltip title="删除">
            <Button
              type="text"
              danger
              icon={<Trash2 size={16} />}
              onClick={handleDelete}
            />
          </Tooltip>
        </Space>
      }
    >
      <Spin spinning={loading}>
        {!report ? (
          <Empty description="未找到报告" />
        ) : (
          <div className="report-detail">
            {/* 报告头部 */}
            <Card size="small" className="report-header" style={{ marginBottom: 16 }}>
              <Row align="middle" gutter={[16, 12]}>
                <Col flex="auto">
                  <Title level={4} style={{ margin: 0 }}>
                    {report.title || `报告 #${report.id}`}
                  </Title>
                  <div style={{ marginTop: 8 }}>
                    <Space wrap>
                      <Tag color={statusConfig.color} icon={statusConfig.icon}>
                        {statusConfig.text}
                      </Tag>
                      {report.config_name && (
                        <Tag icon={<Settings size={12} />}>
                          {report.config_name}
                        </Tag>
                      )}
                    </Space>
                  </div>
                </Col>
              </Row>

              <Descriptions column={{ xs: 1, sm: 2 }} size="small" style={{ marginTop: 12 }}>
                <Descriptions.Item label="创建时间">
                  {dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}
                  {' '}({dayjs(report.created_at).fromNow()})
                </Descriptions.Item>
                <Descriptions.Item label="开始时间">
                  {report.started_at
                    ? dayjs(report.started_at).format('YYYY-MM-DD HH:mm:ss')
                    : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="完成时间">
                  {report.completed_at
                    ? dayjs(report.completed_at).format('YYYY-MM-DD HH:mm:ss')
                    : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="耗时">
                  {report.duration_seconds != null
                    ? `${report.duration_seconds.toFixed(1)} 秒`
                    : '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 错误信息提示 */}
            {report.status === 'failed' && report.error_message && (
              <Alert
                message="分析失败"
                description={report.error_message}
                type="error"
                showIcon
                closable
                style={{ marginBottom: 16 }}
              />
            )}

            {/* 统计面板 */}
            <Card
              size="small"
              title={
                <Space>
                  <BarChart3 size={16} />
                  统计信息
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="处理条目"
                    value={report.total_items || 0}
                    suffix="条"
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="相关条目"
                    value={report.relevant_count || 0}
                    suffix="条"
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="处理效率"
                    value={
                      report.total_items > 0 && report.duration_seconds > 0
                        ? ((report.relevant_count / report.total_items) * 100).toFixed(1)
                        : 0
                    }
                    suffix="%"
                    valueStyle={{ fontSize: 18 }}
                  />
                </Col>
              </Row>

              {report.total_items > 0 && (
                <div style={{ marginTop: 12 }}>
                  <Progress
                    percent={Math.round((report.relevant_count / report.total_items) * 100)}
                    status={report.status === 'completed' ? 'success' : 'active'}
                    format={(percent) => `${percent}% 相关`}
                  />
                </div>
              )}
            </Card>

            {/* 内容区域 */}
            <Card
              size="small"
              title={
                <Space>
                  <Eye size={16} />
                  分析内容
                </Space>
              }
              className="report-content-card"
            >
              {report.status === 'running' ? (
                <div className="running-state">
                  <Loader2 size={32} className="spin" />
                  <p>AI 正在分析中，请稍候...</p>
                  <Text type="secondary">预计需要 30-60 秒</Text>
                </div>
              ) : report.content ? (
                <div className="markdown-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {report.content}
                  </ReactMarkdown>
                </div>
              ) : report.status === 'pending' ? (
                <Empty description="等待开始分析..." />
              ) : (
                <Empty description="暂无内容" />
              )}
            </Card>

            {/* 输入参数（可折叠） */}
            {report.input_params && Object.keys(report.input_params).length > 0 && (
              <Card
                size="small"
                title={
                  <Space>
                    <Settings size={16} />
                    输入参数
                  </Space>
                }
                style={{ marginTop: 16 }}
              >
                <pre className="params-display">
                  {JSON.stringify(report.input_params, null, 2)}
                </pre>
              </Card>
            )}

            {/* 结果数据（如果有） */}
            {report.result_data && Object.keys(report.result_data).length > 0 && (
              <Card
                size="small"
                title={
                  <Space>
                    <BarChart3 size={16} />
                    结果数据
                  </Space>
                }
                style={{ marginTop: 16 }}
              >
                <pre className="params-display">
                  {JSON.stringify(report.result_data, null, 2)}
                </pre>
              </Card>
            )}
          </div>
        )}
      </Spin>

      <style jsx>{`
        .report-detail {
          padding-bottom: 24px;
        }

        .report-header :global(.ant-descriptions-item-label) {
          font-weight: 500;
        }

        .running-state {
          text-align: center;
          padding: 40px 20px;
          color: #999;
        }

        .running-state p {
          margin-top: 12px;
          font-size: 15px;
        }

        .markdown-content {
          font-size: 14px;
          line-height: 1.7;
          color: #333;
        }

        .markdown-content h1,
        .markdown-content h2,
        .markdown-content h3,
        .markdown-content h4 {
          margin-top: 20px;
          margin-bottom: 10px;
          font-weight: 600;
        }

        .markdown-content h1:first-child,
        .markdown-content h2:first-child {
          margin-top: 0;
        }

        .markdown-content p {
          margin-bottom: 12px;
        }

        .markdown-content ul,
        .markdown-content ol {
          padding-left: 24px;
          margin-bottom: 12px;
        }

        .markdown-content li {
          margin-bottom: 6px;
        }

        .markdown-content blockquote {
          border-left: 3px solid #1677ff;
          padding-left: 16px;
          margin: 16px 0;
          color: #666;
          background: #f6f8fa;
          padding: 12px 16px;
          border-radius: 4px;
        }

        .markdown-content pre {
          background: #f6f8fa;
          padding: 16px;
          border-radius: 6px;
          overflow-x: auto;
          font-size: 13px;
          line-height: 1.5;
        }

        .markdown-content code {
          background: #f0f0f0;
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 13px;
        }

        .markdown-content pre code {
          background: none;
          padding: 0;
        }

        .markdown-content table {
          width: 100%;
          border-collapse: collapse;
          margin: 16px 0;
        }

        .markdown-content th,
        .markdown-content td {
          border: 1px solid #e8e8e8;
          padding: 8px 12px;
          text-align: left;
        }

        .markdown-content th {
          background: #fafafa;
          font-weight: 600;
        }

        .markdown-content a {
          color: #1677ff;
          text-decoration: none;
        }

        .markdown-content a:hover {
          text-decoration: underline;
        }

        .markdown-content img {
          max-width: 100%;
          height: auto;
          border-radius: 4px;
        }

        .markdown-content hr {
          border: none;
          border-top: 1px solid #e8e8e8;
          margin: 24px 0;
        }

        .params-display {
          background: #f6f8fa;
          padding: 16px;
          border-radius: 6px;
          overflow-x: auto;
          font-size: 12px;
          line-height: 1.5;
          margin: 0;
          max-height: 200px;
          overflow-y: auto;
        }

        /* 动画效果 */
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .spin {
          animation: spin 1s linear infinite;
        }

        /* 响应式适配 */
        @media (max-width: 576px) {
          :global(.ant-drawer-body) {
            padding: 16px;
          }

          .markdown-content {
            font-size: 13px;
          }
        }
      `}</style>
    </Drawer>
  );
};

export default ReportDetail;
