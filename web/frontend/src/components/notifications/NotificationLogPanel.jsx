// src/components/notifications/NotificationLogPanel.jsx
import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Table,
  Tag,
  Space,
  Button,
  Typography,
  Empty,
  Spin,
  Select,
  DatePicker,
  Pagination,
  Card,
  Row,
  Col,
  Descriptions,
  Modal,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import notificationsApi from '../../services/notifications';

const { Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;

const STATUS_MAP = {
  pending: {
    icon: <ClockCircleOutlined />,
    color: 'default',
    text: '待发送',
  },
  sent: {
    icon: <CheckCircleOutlined />,
    color: 'success',
    text: '已发送',
  },
  failed: {
    icon: <CloseCircleOutlined />,
    color: 'error',
    text: '失败',
  },
};

const COLUMNS = [
  {
    title: '时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 160,
    render: (text) => (text ? new Date(text).toLocaleString('zh-CN') : '-'),
    sorter: true,
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: 90,
    filters: [
      { text: '待发送', value: 'pending' },
      { text: '已发送', value: 'sent' },
      { text: '失败', value: 'failed' },
    ],
    onFilter: (value, record) => record.status === value,
    render: (status) => {
      const config = STATUS_MAP[status] || STATUS_MAP.pending;
      return (
        <Tag icon={config.icon} color={config.color}>
          {config.text}
        </Tag>
      );
    },
  },
  {
    title: '内容摘要',
    dataIndex: 'content_summary',
    key: 'content_summary',
    ellipsis: true,
    render: (text) => text || '-',
  },
  {
    title: '条目数',
    dataIndex: 'items_count',
    key: 'items_count',
    width: 80,
    align: 'center',
    render: (count) => count || 0,
  },
  {
    title: '重试次数',
    dataIndex: 'retry_count',
    key: 'retry_count',
    width: 80,
    align: 'center',
    render: (count) => count || 0,
  },
  {
    title: '操作',
    key: 'action',
    width: 80,
    render: (_, record) => (
      <Button
        type="link"
        size="small"
        icon={<EyeOutlined />}
        onClick={() => showDetail(record)}
      >
        详情
      </Button>
    ),
  },
];

export default function NotificationLogPanel({ visible, subscriptionId, onClose }) {
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState(undefined);

  // 详情弹窗
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  // 加载日志数据
  const loadLogs = async (page = currentPage, size = pageSize) => {
    setLoading(true);
    try {
      const params = {
        limit: size,
        offset: (page - 1) * size,
      };

      if (subscriptionId) {
        params.subscription_id = subscriptionId;
      }
      if (statusFilter) {
        params.status = statusFilter;
      }

      const result = await notificationsApi.getNotificationLogs(params);

      if (result?.data) {
        setLogs(result.data);
        setTotal(result.total || 0);
      }
    } catch (error) {
      console.error('加载日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (visible) {
      loadLogs();
    }
  }, [visible, statusFilter]);

  // 查看详情
  const showDetail = (log) => {
    setSelectedLog(log);
    setDetailVisible(true);
  };

  // 刷新
  const handleRefresh = () => {
    loadLogs(currentPage, pageSize);
  };

  // 分页变化
  const handlePageChange = (page, size) => {
    setCurrentPage(page);
    setPageSize(size);
    loadLogs(page, size);
  };

  // 状态筛选变化
  const handleStatusChange = (value) => {
    setStatusFilter(value);
    setCurrentPage(1);
  };

  return (
    <>
      <Drawer
        title={subscriptionId ? `订阅 #${subscriptionId} 的通知日志` : '全部通知日志'}
        placement="right"
        width={720}
        open={visible}
        onClose={onClose}
        extra={
          <Space>
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 120 }}
              onChange={handleStatusChange}
              value={statusFilter}
              options={[
                { value: 'pending', label: '待发送' },
                { value: 'sent', label: '已发送' },
                { value: 'failed', label: '失败' },
              ]}
            />
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
          </Space>
        }
      >
        {/* 统计信息 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Text type="secondary">总记录:</Text> <Text strong>{total}</Text>
            </Col>
            <Col span={8}>
              <Text type="secondary">当前页:</Text>{' '}
              <Text strong>
                {logs.filter((l) => l.status === 'sent').length} 已发送 /{' '}
                {logs.filter((l) => l.status === 'failed').length} 失败
              </Text>
            </Col>
          </Row>
        </Card>

        {/* 日志表格 */}
        <Spin spinning={loading}>
          {logs.length === 0 && !loading ? (
            <Empty description="暂无日志记录" />
          ) : (
            <>
              <Table
                dataSource={logs}
                columns={COLUMNS}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ y: 'calc(100vh - 300px)' }}
              />

              {/* 分页 */}
              <div style={{ textAlign: 'right', marginTop: 16 }}>
                <Pagination
                  current={currentPage}
                  pageSize={pageSize}
                  total={total}
                  showSizeChanger
                  showQuickJumper
                  showTotal={(t) => `共 ${t} 条记录`}
                  onChange={handlePageChange}
                />
              </div>
            </>
          )}
        </Spin>
      </Drawer>

      {/* 日志详情弹窗 */}
      <Modal
        title="通知详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {selectedLog && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="日志ID">{selectedLog.id}</Descriptions.Item>
            <Descriptions.Item label="订阅ID">{selectedLog.subscription_id}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag
                icon={STATUS_MAP[selectedLog.status]?.icon}
                color={STATUS_MAP[selectedLog.status]?.color}
              >
                {STATUS_MAP[selectedLog.status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {selectedLog.created_at
                ? new Date(selectedLog.created_at).toLocaleString('zh-CN')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="发送时间">
              {selectedLog.sent_at
                ? new Date(selectedLog.sent_at).toLocaleString('zh-CN')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="条目数量">{selectedLog.items_count}</Descriptions.Item>
            <Descriptions.Item label="重试次数">{selectedLog.retry_count}</Descriptions.Item>

            {selectedLog.content_summary && (
              <Descriptions.Item label="内容摘要">
                {selectedLog.content_summary}
              </Descriptions.Item>
            )}

            {selectedLog.error_message && (
              <Descriptions.Item label="错误信息">
                <Text type="danger">{selectedLog.error_message}</Text>
              </Descriptions.Item>
            )}

            {selectedLog.sent_content && (
              <Descriptions.Item label="发送内容">
                <Paragraph
                  code
                  style={{
                    maxHeight: 300,
                    overflow: 'auto',
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    whiteSpace: 'pre-wrap',
                    fontSize: 12,
                  }}
                >
                  {selectedLog.sent_content}
                </Paragraph>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </>
  );
}

// 需要导入 Row 和 Col 组件（Ant Design）
