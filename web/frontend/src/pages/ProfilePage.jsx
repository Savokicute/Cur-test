import { useState, useEffect } from 'react';
import { Card, Tabs, Form, Input, Button, Avatar, Tag, Descriptions, Table, message, Spin, Divider, Typography } from 'antd';
import {
  UserOutlined,
  SafetyCertificateOutlined,
  HistoryOutlined,
  SafetyCertificateOutlined as ShieldIcon,
  EditOutlined,
  LockOutlined,
  MailOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Text, Title } = Typography;

/**
 * 个人中心页面
 *
 * Tab 1: 基本信息（昵称/邮箱/头像）
 * Tab 2: 安全设置（修改密码/登录历史）
 * Tab 3: 权限信息（角色/权限列表）
 */
export default function ProfilePage() {
  const { user, refreshUser, isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState('basic');
  const [profile, setProfile] = useState(null);
  const [loginHistory, setLoginHistory] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(false);

  // ---- 加载个人数据 ----
  useEffect(() => {
    if (user?.username) loadProfile();
    if (user?.username) loadLoginHistory();
    if (user?.username) loadPermissions();
  }, [user?.username]);

  const getHeaders = () => ({
    'X-Session-Token': localStorage.getItem('trendradar_token') || '',
    'Content-Type': 'application/json',
  });

  const loadProfile = async () => {
    try {
      const res = await fetch('/api/auth/profile', { headers: getHeaders() });
      const data = await res.json();
      if (data.code === 0) setProfile(data.data);
    } catch (e) { console.error(e); }
  };

  const loadLoginHistory = async () => {
    try {
      const res = await fetch('/api/auth/profile/login-history?limit=10', { headers: getHeaders() });
      const data = await res.json();
      if (data.code === 0) setLoginHistory(data.data?.items || []);
    } catch (e) { console.error(e); }
  };

  const loadPermissions = async () => {
    try {
      const res = await fetch('/api/auth/permissions', { headers: getHeaders() });
      const data = await res.json();
      setPermissions(data.permissions || []);
    } catch (e) { console.error(e); }
  };

  // ---- 保存基本信息 ----
  const handleSaveBasic = async (values) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (data.code === 0) {
        message.success(data.message);
        refreshUser?.();
        loadProfile();
      } else {
        message.error(data.message || '保存失败');
      }
    } catch (e) {
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  // ---- 修改密码 ----
  const handleChangePassword = async (values) => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/profile/change-password', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (data.code === 0) {
        message.success(data.message);
        formPwd.resetFields();
      } else {
        message.error(data.detail || data.message || '修改失败');
      }
    } catch (e) {
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  const [formBasic] = Form.useForm();
  const [formPwd] = Form.useForm();

  // ---- 登录历史列定义 ----
  const historyColumns = [
    { title: '时间', dataIndex: 'created_at', key: 'time', width: 180 },
    { title: 'IP 地址', dataIndex: 'ip_address', key: 'ip', width: 150 },
    { title: '状态', key: 'status', width: 80, render: (_, r) =>
      r.success ? <Tag color="green" icon={<CheckCircleOutlined />}>成功</Tag> : <Tag color="red">失败</Tag>
    },
    { title: '原因', dataIndex: 'failure_reason', key: 'reason', render: (v) => v || '-' },
  ];

  // ---- 渲染基本信息 Tab ----
  const renderBasicInfo = () => (
    <Card size="small">
      <Form
        form={formBasic}
        onFinish={handleSaveBasic}
        layout="vertical"
        initialValues={{
          nickname: profile?.nickname || user?.nickname,
          email: profile?.email || user?.email,
          avatar: profile?.avatar || user?.avatar,
        }}
      >
        {/* 头像区域 */}
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Avatar size={80} icon={<UserOutlined />} src={profile?.avatar || user?.avatar}
            style={{ backgroundColor: isAdmin ? '#cf1322' : '#1677ff' }} />
          <div style={{ marginTop: 8 }}>
            <Text strong style={{ fontSize: 16 }}>{user?.username}</Text>
            {isAdmin && <Tag color="red" style={{ marginLeft: 8 }}>超级管理员</Tag>}
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            注册于 {profile?.created_at || user?.loginTime}
          </Text>
        </div>

        <Form.Item name="nickname" label="昵称">
          <Input prefix={<UserOutlined />} placeholder="设置您的昵称" />
        </Form.Item>
        <Form.Item name="email" label="邮箱">
          <Input prefix={<MailOutlined />} placeholder="your@email.com" />
        </Form.Item>
        <Form.Item name="avatar" label="头像 URL">
          <Input placeholder="https://..." />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} icon={<EditOutlined />}>
            保存修改
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );

  // ---- 渲染安全设置 Tab ----
  const renderSecurity = () => (
    <Card size="small" title={<><SafetyCertificateOutlined /> 安全设置</>} style={{ marginBottom: 16 }}>
      <Title level={5}>修改密码</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        密码要求：8位以上，必须包含大小写字母、数字和特殊字符
      </Text>
      <Form form={formPwd} onFinish={handleChangePassword} layout="vertical">
        <Form.Item name="old_password" label="当前密码" rules={[{ required: true }]}>
          <Input.Password prefix={<LockOutlined />} placeholder="输入当前密码" />
        </Form.Item>
        <Form.Item name="new_password" label="新密码"
          rules={[
            { required: true },
            { min: 8, message: '至少 8 位' },
            { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9])/, message: '需包含大小写+数字+特殊字符' },
          ]}>
          <Input.Password prefix={<LockOutlined />} placeholder="输入新密码" />
        </Form.Item>
        <Form.Item name="confirm_password" label="确认新密码" dependencies={['new_password']}
          rules={[
            { required: true },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                return Promise.reject(new Error('两次密码不一致'));
              },
            }),
          ]}>
          <Input.Password prefix={<SafetyCertificateOutlined />} placeholder="再次输入新密码" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} icon={<LockOutlined />}>修改密码</Button>
        </Form.Item>
      </Form>
    </Card>
  );

  // ---- 渲染登录历史 ----
  const renderHistory = () => (
    <Card size="small" title={<><HistoryOutlined /> 最近登录记录</>}>
      <Table columns={historyColumns} dataSource={loginHistory} rowKey="id" pagination={false}
        size="small" locale={{ emptyText: '暂无登录记录' }} />
    </Card>
  );

  // ---- 渲染权限信息 Tab ----
  const renderPermissions = () => (
    <Card size="small">
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
        <Descriptions.Item label="角色">
          <Tag color={isAdmin ? 'red' : 'blue'}>{user?.role_name || (isAdmin ? '超级管理员' : '普通用户')}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="权限数量">{permissions.length} 项</Descriptions.Item>
      </Descriptions>

      <Divider>权限列表</Divider>

      {permissions.length > 0 ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {permissions.map((p) => (
            <Tag key={p} color="processing"><ShieldIcon /> {p}</Tag>
          ))}
        </div>
      ) : (
        <Text type="secondary">暂无权限数据</Text>
      )}
    </Card>
  );

  // ---- Tab 配置 ----
  const tabItems = [
    { key: 'basic', label: (<span><UserOutlined /> 基本信息</span>), children: renderBasicInfo() },
    { key: 'security', label: (<span><SafetyCertificateOutlined /> 安全设置</span>), children: (
      <>
        {renderSecurity()}
        {renderHistory()}
      </>
    )},
    { key: 'permissions', label: (<span><ShieldIcon /> 权限信息</span>), children: renderPermissions() },
  ];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24 }}>
      <Card styles={{ body: { padding: 0 } }}>
        <Tabs activeKey={activeTab} items={tabItems} onChange={setActiveTab} centered size="large" />
      </Card>
    </div>
  );
}
