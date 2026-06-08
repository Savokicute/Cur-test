import { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Button,
  Checkbox,
  Tabs,
  QRCode,
  Typography,
  Space,
  Divider,
  message,
  Progress,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  QrcodeOutlined,
  WechatOutlined,
  SafetyCertificateOutlined,
  MailOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../services/api';

const { Text } = Typography;

/**
 * 登录/注册弹窗组件（增强版）
 *
 * 三个 Tab：
 * - 密码登录（本地账号）
 * - 注册账号（用户名+密码+邮箱选填）
 * - 扫码登录（占位）
 */
export default function LoginModal({ open, onClose, onSuccess }) {
  const { login: authLogin, register } = useAuth();
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();
  const [rememberMe, setRememberMe] = useState(() => {
    return localStorage.getItem('trendradar_remember') === 'true';
  });

  // ---- 密码强度计算 ----
  const calcPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: '', color: '#d9d9d9', percent: 0 };
    let score = 0;
    if (pwd.length >= 8) score++;
    if (/[a-z]/.test(pwd)) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/\d/.test(pwd)) score++;
    if (/[^a-zA-Z0-9]/.test(pwd)) score++;

    const labels = ['', '弱', '较弱', '中等', '强', '非常强'];
    const colors = ['#ff4d4f', '#ff7875', '#ffc53d', '#73d13d', '#389e0d', '#389e0d'];

    return {
      score,
      label: labels[score],
      color: colors[score],
      percent: (score / 5) * 100,
    };
  };

  const [passwordStrength, setPasswordStrength] = useState({ score: 0, label: '', color: '#d9d9d9', percent: 0 });

  // ---- 登录提交 ----
  const handleLoginFinish = async (values) => {
    setLoading(true);
    try {
      const result = await authLogin({
        username: values.username,
        password: values.password,
        rememberMe,
      });
      if (result.success) {
        loginForm.resetFields();
        onSuccess?.(result.user);
        onClose?.();
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || '登录失败';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  // ---- 注册提交 ----
  const handleRegisterFinish = async (values) => {
    setLoading(true);
    try {
      const result = await register({
        username: values.reg_username,
        password: values.reg_password,
        confirm_password: values.reg_confirm_password,
        email: values.reg_email || undefined,
        nickname: values.reg_nickname || undefined,
      });
      if (result.success) {
        message.success(`注册成功！欢迎 ${result.username}`);
        registerForm.resetFields();
        // 注册成功后自动切换到登录 Tab 并填入用户名
        setActiveTab('login');
        loginForm.setFieldValue('username', result.username);
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || '注册失败';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  // ---- 渲染密码强度指示器 ----
  const renderPasswordStrength = () => {
    if (!passwordStrength.label) return null;
    return (
      <div style={{ marginTop: 4 }}>
        <Progress
          percent={passwordStrength.percent}
          showInfo={false}
          strokeColor={passwordStrength.color}
          size="small"
          style={{ height: 4 }}
        />
        <Text type="secondary" style={{ fontSize: 12 }}>
          密码强度：<Text style={{ color: passwordStrength.color }}>{passwordStrength.label}</Text>
        </Text>
      </div>
    );
  };

  // ---- 渲染登录 Tab ----
  const renderLoginForm = () => (
    <Form
      form={loginForm}
      onFinish={handleLoginFinish}
      layout="vertical"
      requiredMark={false}
      size="large"
    >
      <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
        <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" autoFocus />
      </Form.Item>

      <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
        <Input.Password prefix={<LockOutlined />} placeholder="密码" autoComplete="current-password" />
      </Form.Item>

      <Form.Item>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Checkbox checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)}>
            记住我
          </Checkbox>
        </div>
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block size="large" style={{ height: 44, borderRadius: 8 }}>
          登 录
        </Button>
      </Form.Item>
    </Form>
  );

  // ---- 渲染注册 Tab ----
  const renderRegisterForm = () => (
    <Form
      form={registerForm}
      onFinish={handleRegisterFinish}
      layout="vertical"
      requiredMark={false}
      size="large"
    >
      <Form.Item
        name="reg_username"
        rules={[
          { required: true, message: '请输入用户名' },
          { min: 3, message: '至少 3 个字符' },
          { pattern: /^[a-zA-Z0-9_]+$/, message: '仅支持字母、数字和下划线' },
        ]}
      >
        <Input prefix={<UserOutlined />} placeholder="用户名（3-20位字母数字下划线）" />
      </Form.Item>

      <Form.Item
        name="reg_password"
        rules={[
          { required: true, message: '请输入密码' },
          { min: 8, message: '至少 8 位' },
          {
            pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9])/,
            message: '需包含大小写字母、数字和特殊字符',
          },
        ]}
      >
        <Input.Password
          prefix={<LockOutlined />}
          placeholder="密码（8位+大小写+数字+特殊字符）"
          onChange={(e) => setPasswordStrength(calcPasswordStrength(e.target.value))}
        />
      </Form.Item>
      {renderPasswordStrength()}

      <Form.Item
        name="reg_confirm_password"
        dependencies={['reg_password']}
        rules={[
          { required: true, message: '请确认密码' },
          ({ getFieldValue }) => ({
            validator(_, value) {
              if (!value || getFieldValue('reg_password') === value) return Promise.resolve();
              return Promise.reject(new Error('两次输入的密码不一致'));
            },
          }),
        ]}
      >
        <Input.Password prefix={<SafetyCertificateOutlined />} placeholder="确认密码" />
      </Form.Item>

      <Form.Item name="reg_email">
        <Input prefix={<MailOutlined />} placeholder="邮箱（选填）" />
      </Form.Item>

      <Form.Item name="reg_nickname">
        <Input prefix={<UserOutlined />} placeholder="昵称（选填，默认同用户名）" />
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block size="large" style={{ height: 44, borderRadius: 8 }}>
          注 册
        </Button>
      </Form.Item>
    </Form>
  );

  // ---- 扫码占位 ----
  const renderQrCode = () => (
    <div style={{ textAlign: 'center', padding: '24px 0' }}>
      <QRCode value="https://trendradar.dev/qrcode-placeholder" size={180} style={{ marginBottom: 16 }} />
      <div><Text type="secondary">微信扫码登录（即将上线）</Text></div>
      <div style={{ marginTop: 12 }}>
        <Button type="link" onClick={() => setActiveTab('login')}>切换到密码登录</Button>
      </div>
    </div>
  );

  // ---- Tab 配置 ----
  const tabItems = [
    {
      key: 'login',
      label: (<span><LockOutlined /> 登录</span>),
      children: renderLoginForm(),
    },
    {
      key: 'register',
      label: (<span><UserOutlined /> 注册</span>),
      children: renderRegisterForm(),
    },
    {
      key: 'qrcode',
      label: (<span><QrcodeOutlined /> 扫码</span>),
      children: renderQrCode(),
    },
  ];

  return (
    <Modal
      title={null}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnClose
      centered
      width={440}
      closable={!loading}
      maskClosable={!loading}
      styles={{ body: { padding: '24px 32px 8px' } }}
    >
      {/* Logo */}
      <div style={{ textAlign: 'center', marginBottom: 20 }}>
        <div style={{
          width: 56, height: 56, borderRadius: 16,
          background: 'linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12,
        }}>
          <UserOutlined style={{ color: '#fff', fontSize: 28 }} />
        </div>
        <Typography.Title level={4} style={{ margin: 0, marginBottom: 4 }}>
          {activeTab === 'register' ? '创建账号' : '欢迎回来'}
        </Typography.Title>
        <Text type="secondary">
          {activeTab === 'register' ? '加入 TrendRadar 热点发现平台' : '登录以继续使用平台功能'}
        </Text>
      </div>

      <Tabs activeKey={activeTab} items={tabItems} onChange={(key) => { setActiveTab(key); setPasswordStrength({ score: 0, label: '', color: '#d9d9d9', percent: 0 }); }} centered />

      {activeTab !== 'register' && (
        <>
          <Divider plain style={{ margin: '8px 0', fontSize: 13 }}>其他方式</Divider>
          <div style={{ textAlign: 'center' }}>
            <Space size="large">
              <Button shape="circle" size="large" icon={<WechatOutlined style={{ color: '#07C160', fontSize: 20 }} />}
                onClick={() => message.info('微信扫码登录开发中...')} />
            </Space>
          </div>
        </>
      )}
    </Modal>
  );
}
