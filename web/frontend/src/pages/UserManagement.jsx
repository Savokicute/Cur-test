import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Popconfirm,
  Tooltip,
  Typography,
  Badge,
  Tabs,
  Empty,
  Spin,
  Alert,
} from 'antd';
import {
  UserOutlined,
  EditOutlined,
  StopOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  SearchOutlined,
  TeamOutlined,
  HistoryOutlined,
  SafetyOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import { usersApi } from '../services/api';

const { Text } = Typography;

// ========== 角色标签颜色 ==========
const ROLE_TAG_COLORS = {
  super_admin: { color: 'red', text: '超级管理员' },
  user: { color: 'blue', text: '普通用户' },
};

// ========== 状态标签 ==========
const STATUS_CONFIG = {
  true: { color: 'success', icon: <CheckCircleOutlined />, text: '启用' },
  false: { color: 'error', icon: <StopOutlined />, text: '禁用' },
};

// ========== 操作类型映射 ==========
const ACTION_MAP = {
  update_role: { label: '修改角色', color: 'orange' },
  disable: { label: '禁用账号', color: 'red' },
  enable: { label: '启用账号', color: 'green' },
  batch_update: { label: '批量操作', color: 'purple' },
  update_info: { label: '编辑信息', color: 'blue' },
};

export default function UserManagement() {
  // ---- 用户列表状态 ----
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);

  // ---- 搜索/筛选状态 ----
  const [keyword, setKeyword] = useState('');
  const [roleFilter, setRoleFilter] = useState(undefined);
  const [statusFilter, setStatusFilter] = useState(undefined);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });

  // ---- 编辑弹窗状态 ----
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [editForm] = Form.useForm();
  const [editLoading, setEditLoading] = useState(false);

  // ---- 批量操作状态 ----
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchType, setBatchType] = useState('role'); // 'role' | 'status'
  const [batchValue, setBatchValue] = useState('');
  const [batchLoading, setBatchLoading] = useState(false);

  // ---- 操作日志状态 ----
  const [logs, setLogs] = useState([]);
  const [logTotal, setLogTotal] = useState(0);
  const [logLoading, setLogLoading] = useState(false);
  const [logPagination, setLogPagination] = useState({ current: 1, pageSize: 20 });
  const [logActionFilter, setLogActionFilter] = useState(undefined);

  // ---- 当前用户信息 ----
  const [currentUser, setCurrentUser] = useState(null);

  // ---- Tab 状态 ----
  const [activeTab, setActiveTab] = useState('users');

  // ========== 加载用户列表 ==========
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await usersApi.getList({
        page: pagination.current,
        size: pagination.pageSize,
        keyword: keyword || undefined,
        role: roleFilter || undefined,
        is_active: statusFilter !== undefined ? statusFilter : undefined,
        sort_by: 'created_at',
        sort_order: 'desc',
      });
      setUsers(res.data?.items || res.items || []);
      setTotal(res.data?.total || res.total || 0);
    } catch (err) {
      console.error('加载用户列表失败:', err);
      message.error('加载用户列表失败');
    } finally {
      setLoading(false);
    }
  }, [pagination.current, pagination.pageSize, keyword, roleFilter, statusFilter]);

  useEffect(() => {
    if (activeTab === 'users') {
      fetchUsers();
    }
  }, [fetchUsers, activeTab]);

  // ========== 加载当前用户 ==========
  useEffect(() => {
    usersApi.getMe()
      .then((res) => {
        const data = res.data || res;
        setCurrentUser(data);
      })
      .catch(() => {});
  }, []);

  // ========== 加载操作日志 ==========
  const fetchLogs = useCallback(async () => {
    setLogLoading(true);
    try {
      const res = await usersApi.getLogs({
        page: logPagination.current,
        size: logPagination.pageSize,
        action: logActionFilter || undefined,
      });
      setLogs(res.data?.items || res.items || []);
      setLogTotal(res.data?.total || res.total || 0);
    } catch (err) {
      console.error('加载操作日志失败:', err);
      message.error('加载操作日志失败');
    } finally {
      setLogLoading(false);
    }
  }, [logPagination.current, logPagination.pageSize, logActionFilter]);

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    }
  }, [fetchLogs, activeTab]);

  // ========== 搜索 ==========
  const handleSearch = () => {
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  // ========== 编辑用户 ==========
  const handleEdit = (user) => {
    setEditingUser(user);
    setEditModalOpen(true);
    editForm.setFieldsValue({
      nickname: user.nickname || '',
      email: user.email || '',
      role: user.role,
      is_active: user.is_active ?? true,
      remark: user.remark || '',
    });
  };

  const handleEditSubmit = async () => {
    try {
      const values = await editForm.validateFields();
      setEditLoading(true);

      // 更新基本信息
      await usersApi.update(editingUser.username, {
        nickname: values.nickname || undefined,
        email: values.email || undefined,
        remark: values.remark || undefined,
      });

      // 如果角色有变化，单独更新角色
      if (values.role !== editingUser.role) {
        await usersApi.updateRole(editingUser.username, values.role);
      }

      message.success('用户信息已更新');
      setEditModalOpen(false);
      fetchUsers();
    } catch (err) {
      if (err?.errorFields) return; // 表单校验错误
      console.error('更新用户失败:', err);
      const detail = err.response?.data?.detail;
      message.error(detail || '更新用户失败');
    } finally {
      setEditLoading(false);
    }
  };

  // ========== 禁用/启用 ==========
  const handleToggleStatus = async (username, isActive) => {
    try {
      await usersApi.updateStatus(username, isActive);
      message.success(`用户已${isActive ? '启用' : '禁用'}`);
      fetchUsers();
    } catch (err) {
      console.error('修改状态失败:', err);
      const detail = err.response?.data?.detail;
      message.error(detail || '修改状态失败');
    }
  };

  // ========== 批量操作 ==========
  const handleBatchAction = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择用户');
      return;
    }
    setBatchValue('');
    setBatchModalOpen(true);
  };

  const handleBatchSubmit = async () => {
    if (!batchValue && batchType === 'role') {
      message.warning('请选择目标角色');
      return;
    }

    try {
      setBatchLoading(true);
      let res;
      if (batchType === 'role') {
        res = await usersApi.batchUpdateRole(selectedRowKeys, batchValue);
      } else {
        res = await usersApi.batchUpdateStatus(selectedRowKeys, batchValue === 'enable');
      }

      const data = res.data || res;
      message.success(data.message || '批量操作完成');
      setBatchModalOpen(false);
      setSelectedRowKeys([]);
      fetchUsers();
    } catch (err) {
      console.error('批量操作失败:', err);
      message.error('批量操作失败');
    } finally {
      setBatchLoading(false);
    }
  };

  // ========== 表格列定义 ==========
  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 140,
      fixed: 'left',
      render: (text) => (
        <Space>
          <UserOutlined style={{ color: '#3B82F6' }} />
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      key: 'nickname',
      width: 120,
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 120,
      filters: [
        { text: '超级管理员', value: 'super_admin' },
        { text: '普通用户', value: 'user' },
      ],
      onFilter: (value, record) => record.role === value,
      render: (role) => {
        const cfg = ROLE_TAG_COLORS[role];
        return <Tag color={cfg?.color}>{cfg?.text || role}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      align: 'center',
      render: (active) => {
        const cfg = STATUS_CONFIG[active];
        return (
          <Tag color={cfg?.color} icon={cfg?.icon}>{cfg?.text}</Tag>
        );
      },
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      width: 170,
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '登录次数',
      dataIndex: 'login_count',
      key: 'login_count',
      width: 90,
      align: 'center',
      sorter: (a, b) => a.login_count - b.login_count,
      render: (count) => count || 0,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={record.is_active ? '确定禁用该用户？' : '确定启用该用户？'}
            onConfirm={() => handleToggleStatus(record.username, !record.is_active)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title={record.is_active ? '禁用' : '启用'}>
              <Button
                type="link"
                size="small"
                danger={record.is_active}
                icon={record.is_active ? <StopOutlined /> : <CheckCircleOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ========== 操作日志表格列 ==========
  const logColumns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作人',
      dataIndex: 'operator',
      key: 'operator',
      width: 120,
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      filters: Object.entries(ACTION_MAP).map(([k, v]) => ({ text: v.label, value: k })),
      onFilter: (value, record) => record.action === value,
      render: (action) => {
        const cfg = ACTION_MAP[action];
        return <Tag color={cfg?.color}>{cfg?.label || action}</Tag>;
      },
    },
    {
      title: '目标用户',
      dataIndex: 'target_user',
      key: 'target_user',
      width: 130,
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: '详情',
      dataIndex: 'detail',
      key: 'detail',
      ellipsis: true,
      render: (text) => {
        if (!text) return '-';
        try {
          const obj = JSON.parse(text);
          return (
            <Tooltip title={<pre style={{ margin: 0 }}>{JSON.stringify(obj, null, 2)}</pre>}>
              <Text type="secondary" ellipsis style={{ maxWidth: 200 }}>
                {JSON.stringify(obj)}
              </Text>
            </Tooltip>
          );
        } catch {
          return <Text type="secondary" ellipsis style={{ maxWidth: 200 }}>{text}</Text>;
        }
      },
    },
  ];

  // ========== 行选择配置 ==========
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
    getCheckboxProps: (record) => ({
      disabled: record.username === currentUser?.username && !record.is_active,
      name: record.username,
    }),
  };

  // ========== 渲染 ==========
  const tabItems = [
    {
      key: 'users',
      label: (
        <span><TeamOutlined /> 用户列表</span>
      ),
      children: (
        <Card>
          {/* 工具栏 */}
          <div style={{ marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <Input.Search
              placeholder="搜索用户名/昵称"
              allowClear
              style={{ width: 220 }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={handleSearch}
              enterButton={<SearchOutlined />}
            />

            <Select
              placeholder="角色筛选"
              allowClear
              style={{ width: 140 }}
              value={roleFilter}
              onChange={(v) => { setRoleFilter(v); setPagination((p) => ({ ...p, current: 1 })); }}
              options={[
                { label: '超级管理员', value: 'super_admin' },
                { label: '普通用户', value: 'user' },
              ]}
            />

            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 120 }}
              value={statusFilter}
              onChange={(v) => { setStatusFilter(v); setPagination((p) => ({ ...p, current: 1 })); }}
              options={[
                { label: '已启用', value: true },
                { label: '已禁用', value: false },
              ]}
            />

            <div style={{ flex: 1 }} />

            {/* 批量操作按钮 */}
            {selectedRowKeys.length > 0 && (
              <Space>
                <Badge count={selectedRowKeys.length} size="small" offset={[0, -4]}>
                  <Button
                    icon={<SafetyOutlined />}
                    onClick={() => { setBatchType('role'); handleBatchAction(); }}
                  >
                    批量改角色
                  </Button>
                </Badge>
                <Button
                  icon={<StopOutlined />}
                  onClick={() => { setBatchType('status'); setBatchValue('disable'); handleBatchAction(); }}
                  danger
                >
                  批量禁用
                </Button>
                <Button
                  icon={<CheckCircleOutlined />}
                  onClick={() => { setBatchType('status'); setBatchValue('enable'); handleBatchAction(); }}
                >
                  批量启用
                </Button>
              </Space>
            )}

            <Button icon={<ReloadOutlined />} onClick={fetchUsers}>
              刷新
            </Button>
          </div>

          {/* 表格 */}
          <Table
            rowKey="username"
            columns={columns}
            dataSource={users}
            rowSelection={rowSelection}
            loading={loading}
            scroll={{ x: 1200 }}
            pagination={{
              ...pagination,
              total,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (t) => `共 ${t} 名用户`,
              pageSizeOptions: ['10', '20', '50'],
              onChange: (page, size) =>
                setPagination({ current: page, pageSize: size }),
            }}
            locale={{ emptyText: <Empty description="暂无用户数据" /> }}
            size="middle"
          />
        </Card>
      ),
    },
    {
      key: 'logs',
      label: (
        <span><HistoryOutlined /> 操作日志</span>
      ),
      children: (
        <Card>
          <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
            <Select
              placeholder="操作类型筛选"
              allowClear
              style={{ width: 160 }}
              value={logActionFilter}
              onChange={(v) => { setLogActionFilter(v); setLogPagination((p) => ({ ...p, current: 1 })); }}
              options={Object.entries(ACTION_MAP).map(([k, v]) => ({ label: v.label, value: k }))}
            />
            <div style={{ flex: 1 }} />
            <Button icon={<ReloadOutlined />} onClick={fetchLogs}>刷新</Button>
          </div>

          <Table
            rowKey="id"
            columns={logColumns}
            dataSource={logs}
            loading={logLoading}
            pagination={{
              ...logPagination,
              total: logTotal,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 条记录`,
              pageSizeOptions: ['10', '20', '50'],
              onChange: (page, size) =>
                setLogPagination({ current: page, pageSize: size }),
            }}
            locale={{ emptyText: <Empty description="暂无操作日志" /> }}
            size="middle"
          />
        </Card>
      ),
    },
  ];

  return (
    <div className="page-container" style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          <UserOutlined style={{ marginRight: 8 }} />
          用户管理
        </Typography.Title>
        {currentUser && (
          <Tag color={currentUser.role === 'super_admin' ? 'red' : 'blue'} icon={<SafetyOutlined />}>
            当前身份：{currentUser.role_name || currentUser.role}
          </Tag>
        )}
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />

      {/* 编辑用户弹窗 */}
      <Modal
        title={`编辑用户 — ${editingUser?.username || ''}`}
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={handleEditSubmit}
        confirmLoading={editLoading}
        okText="保存"
        cancelText="取消"
        width={520}
        destroyOnClose
      >
        <Form
          form={editForm}
          layout="vertical"
          initialValues={{
            is_active: true,
          }}
        >
          <Form.Item
            name="nickname"
            label="昵称"
            rules={[{ max: 50, message: '昵称最多50个字符' }]}
          >
            <Input placeholder="请输入昵称" maxLength={50} />
          </Form.Item>

          <Form.Item
            name="email"
            label="邮箱"
            rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>

          <Form.Item
            name="role"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select
              options={[
                { label: '超级管理员', value: 'super_admin' },
                { label: '普通用户', value: 'user' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="账号状态"
            valuePropName="checked"
          >
            <Switch
              checkedChildren="启用"
              unCheckedChildren="禁用"
              disabled={editingUser?.username === currentUser?.username}
            />
            {editingUser?.username === currentUser?.username && (
              <Alert
                type="info"
                showIcon
                message="不能禁用自己的账号"
                style={{ marginTop: 8, padding: '4px 8px' }}
              />
            )}
          </Form.Item>

          <Form.Item
            name="remark"
            label="备注"
          >
            <Input.TextArea rows={3} placeholder="管理员备注信息（可选）" maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 批量操作弹窗 */}
      <Modal
        title={
          batchType === 'role'
            ? `批量修改角色 (${selectedRowKeys.length} 个用户)`
            : `批量修改状态 (${selectedRowKeys.length} 个用户)`
        }
        open={batchModalOpen}
        onCancel={() => setBatchModalOpen(false)}
        onOk={handleBatchSubmit}
        confirmLoading={batchLoading}
        okText="确认执行"
        cancelText="取消"
        width={420}
      >
        {batchType === 'role' ? (
          <Form layout="vertical">
            <Form.Item label="目标角色">
              <Select
                value={batchValue}
                onChange={setBatchValue}
                placeholder="请选择目标角色"
                options={[
                  { label: '超级管理员', value: 'super_admin' },
                  { label: '普通用户', value: 'user' },
                ]}
              />
            </Form.Item>
            <Alert
              type="warning"
              showIcon
              message="注意：不能将最后一个超级管理员降级为普通用户"
              style={{ marginBottom: 0 }}
            />
          </Form>
        ) : (
          <Form layout="vertical">
            <Form.Item label="目标状态">
              <Select
                value={batchValue}
                onChange={setBatchValue}
                placeholder="请选择目标状态"
                options={[
                  { label: '启用', value: 'enable' },
                  { label: '禁用', value: 'disable' },
                ]}
              />
            </Form.Item>
            {batchValue === 'disable' && (
              <Alert
                type="warning"
                showIcon
                message="包含当前登录用户时将自动跳过"
                style={{ marginBottom: 0 }}
              />
            )}
          </Form>
        )}

        <div style={{ marginTop: 16 }}>
          <Text type="secondary">选中用户：</Text>
          <div style={{ maxHeight: 120, overflowY: 'auto', marginTop: 8 }}>
            {selectedRowKeys.map((u) => (
              <Tag key={u} style={{ margin: 2 }}>{u}</Tag>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  );
}
