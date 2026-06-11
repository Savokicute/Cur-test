import { useState } from 'react';
import {
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
  Grid,
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  QrcodeOutlined,
  WechatOutlined,
  SafetyCertificateOutlined,
  MailOutlined,
  AimOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const { Text, Title, Paragraph } = Typography;

/**
 * 全屏独立登录页面 /login
 *
 * 布局：左侧品牌区 + 右侧表单区
 * Tab：登录 / 注册 / 扫码
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const { login: authLogin, register } = useAuth();
  const screens = Grid.useBreakpoint();
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState(null);
  const [capsLockOn, setCapsLockOn] = useState(false);
  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();
  const [rememberMe, setRememberMe] = useState(() =>
    localStorage.getItem('trendradar_remember') === 'true'
  );
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, label: '', color: '#d9d9d9', percent: 0 });

  // ---- 密码强度 ----
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
    return { score, label: labels[score], color: colors[score], percent: (score / 5) * 100 };
  };

  // ---- 大写锁定检测 ----
  const handleCapsLock = (e) => {
    // 通过键盘事件判断 Caps Lock 状态
    if (e.getModifierState) {
      setCapsLockOn(e.getModifierState('CapsLock'));
    }
  };

  const renderCapsLockWarning = () => {
    if (!capsLockOn) return null;
    return (
      <div className="capslock-warning" role="alert">
        <WarningOutlined className="capslock-icon" />
        <span className="capslock-text">大写锁定已开启，输入密码时请注意大小写</span>
      </div>
    );
  };

  // ---- 登录 ----
  const handleLoginFinish = async (values) => {
    setLoading(true);
    setLoginError(null);
    try {
      const result = await authLogin({
        username: values.username,
        password: values.password,
        rememberMe,
      });
      if (result.success) {
        loginForm.resetFields();
        const from = new URLSearchParams(window.location.search).get('from') || '/';
        navigate(from, { replace: true });
      }
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message || '登录失败，请检查用户名和密码';
      setLoginError(errMsg);
      message.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  // ---- 注册 ----
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
        setActiveTab('login');
        loginForm.setFieldValue('username', result.username);
      }
    } catch (err) {
      message.error(err.response?.data?.detail || err.message || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  // ---- 渲染密码强度（带动画） ----
  const renderPasswordStrength = () => {
    if (!passwordStrength.label) return null;
    return (
      <div style={{
        marginTop: 8,
        padding: '8px 12px',
        background: `${passwordStrength.color}08`,
        borderRadius: 6,
        borderLeft: `3px solid ${passwordStrength.color}`,
        transition: 'all 0.3s ease',
        animation: 'fadeIn 0.3s ease',
      }}>
        <Progress
          percent={passwordStrength.percent}
          showInfo={false}
          strokeColor={passwordStrength.color}
          size="small"
          style={{ height: 4, marginBottom: 4 }}
          strokeWidth={4}
        />
        <Text type="secondary" style={{ fontSize: 12 }}>
          密码强度：<Text strong style={{ color: passwordStrength.color }}>{passwordStrength.label}</Text>
        </Text>
      </div>
    );
  };

  // ---- 左侧品牌区域 ----
  const renderBrandArea = () => (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: screens.xl ? 80 : 60,
        background: 'linear-gradient(135deg, #1E40AF 0%, #3B82F6 50%, #6366F1 100%)',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        animation: 'slideInLeft 0.6s ease-out',
      }}
    >
      {/* 装饰圆 */}
      <div style={{
        position: 'absolute', top: -80, right: -80, width: 300, height: 300,
        borderRadius: '50%', background: 'rgba(255,255,255,0.06)',
        animation: 'float 6s ease-in-out infinite',
      }} />
      <div style={{
        position: 'absolute', bottom: -60, left: -60, width: 200, height: 200,
        borderRadius: '50%', background: 'rgba(255,255,255,0.04)',
        animation: 'float 8s ease-in-out infinite reverse',
      }} />
      <div style={{
        position: 'absolute', top: '40%', left: '10%', width: 120, height: 120,
        borderRadius: '50%', background: 'rgba(255,255,255,0.03)',
        animation: 'float 10s ease-in-out infinite',
      }} />

      <div style={{ zIndex: 1, textAlign: 'center' }}>
        <div style={{
          width: 96, height: 96, borderRadius: 28,
          background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(10px)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 32,
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
          transition: 'transform 0.3s ease',
          cursor: 'default',
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05) rotate(5deg)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1) rotate(0deg)'}
        >
          <AimOutlined style={{ fontSize: 48, color: '#fff' }} />
        </div>
        <Title level={2} style={{ color: '#fff', margin: '0 0 16px', fontWeight: 700 }}>
          TrendRadar
        </Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 18, margin: 0, fontWeight: 400 }}>
          热点发现平台
        </Paragraph>
        <Divider style={{ borderColor: 'rgba(255,255,255,0.25)', maxWidth: 260, margin: '28px auto' }} />
        <Space direction="vertical" size={18}>
          {[
            { icon: <ThunderboltOutlined />, text: '实时聚合多平台热点' },
            { icon: <ThunderboltOutlined />, text: 'AI 智能分析与筛选' },
            { icon: <ThunderboltOutlined />, text: '全方位内容监控' },
          ].map((item, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                opacity: 0,
                animation: `fadeInUp 0.5s ease ${index * 0.15}s forwards`,
              }}
            >
              <span style={{
                fontSize: 20, color: '#FBBF24',
                filter: 'drop-shadow(0 2px 4px rgba(251,191,36,0.3))',
              }}>
                {item.icon}
              </span>
              <Text style={{ color: 'rgba(255,255,255,0.9)', fontSize: 16, fontWeight: 500 }}>
                {item.text}
              </Text>
            </div>
          ))}
        </Space>
      </div>

      <div style={{ marginTop: 'auto', paddingTop: 36, textAlign: 'center', zIndex: 1 }}>
        <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 13 }}>
          &copy; 2026 TrendRadar. All rights reserved.
        </Text>
      </div>

      {/* 动画样式 */}
      <style>{`
        @keyframes slideInLeft {
          from { opacity: 0; transform: translateX(-30px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-5px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(15px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-20px); }
        }
      `}</style>
    </div>
  );

  // ---- 右侧表单区域 ----
  const renderFormArea = () => (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: screens.md ? '48px 56px' : '32px 24px',
        maxWidth: screens.lg ? 480 : '100%',
        width: '100%',
        margin: '0 auto',
        boxSizing: 'border-box',
        animation: 'slideInRight 0.6s ease-out',
      }}
    >
      {/* Logo（移动端显示） */}
      <div style={{
        display: screens.lg ? 'none' : 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 32,
        animation: 'fadeIn 0.4s ease',
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: 14,
          background: 'linear-gradient(135deg, #1E40AF, #3B82F6)',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 14px rgba(59,130,246,0.35)',
        }}>
          <AimOutlined style={{ color: '#fff', fontSize: 24 }} />
        </div>
        <Title level={4} style={{ margin: 0, fontWeight: 700 }}>TrendRadar</Title>
      </div>

      <div style={{ animation: 'fadeInUp 0.5s ease' }}>
        <Title level={3} style={{ margin: '0 0 8px', fontWeight: 700 }}>
          {activeTab === 'register' ? '创建账号' : '欢迎回来'}
        </Title>
        <Text type="secondary" style={{ fontSize: 15, display: 'block', marginBottom: 28 }}>
          {activeTab === 'register'
            ? '注册以开始使用 TrendRadar 热点发现平台'
            : '登录以继续使用平台功能'}
        </Text>
      </div>

      {/* Tabs（带过渡动画） */}
      <Tabs
        activeKey={activeTab}
        items={[
          {
            key: 'login',
            label: (<span><LockOutlined /> 登录</span>),
            children: (
              <div>
                {loginError && (
                  <div className="error-alert" role="alert">
                    <div className="error-alert-icon">
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                        <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="1.5" />
                        <line x1="7" y1="7" x2="13" y2="13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        <line x1="13" y1="7" x2="7" y2="13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                    </div>
                    <div className="error-alert-content">
                      <div className="error-alert-title">登录失败</div>
                      <div className="error-alert-desc">{loginError}</div>
                    </div>
                    <button
                      className="error-alert-close"
                      onClick={() => setLoginError(null)}
                      aria-label="关闭"
                      type="button"
                    >
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <line x1="3" y1="3" x2="11" y2="11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        <line x1="11" y1="3" x2="3" y2="11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                    </button>
                  </div>
                )}
              <Form form={loginForm} onFinish={handleLoginFinish} layout="vertical"
                requiredMark={false} size="large" className="login-form">
                <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                  <Input
                    prefix={<UserOutlined className="input-prefix-icon" />}
                    placeholder="用户名"
                    autoComplete="username"
                    autoFocus
                    className="custom-input"
                  />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                  <Input.Password
                    prefix={<LockOutlined className="input-prefix-icon" />}
                    placeholder="密码"
                    autoComplete="current-password"
                    className="custom-input"
                    onKeyDown={handleCapsLock}
                    onKeyUp={handleCapsLock}
                  />
                </Form.Item>
                {renderCapsLockWarning()}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24, alignItems: 'center' }}>
                  <Checkbox checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)}>
                    记住我
                  </Checkbox>
                </div>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  className="login-button"
                  style={{
                    height: 48,
                    borderRadius: 10,
                    fontSize: 16,
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #3B82F6, #6366F1)',
                    border: 'none',
                    boxShadow: '0 4px 14px rgba(59,130,246,0.35)',
                    transition: 'all 0.3s ease',
                  }}
                >
                  登 录
                </Button>
              </Form>
              </div>
            ),
          },
          {
            key: 'register',
            label: (<span><UserOutlined /> 注册</span>),
            children: (
              <Form form={registerForm} onFinish={handleRegisterFinish} layout="vertical"
                requiredMark={false} size="large" className="login-form">
                <Form.Item name="reg_username" rules={[
                  { required: true, message: '请输入用户名' },
                  { min: 3, message: '至少 3 个字符' },
                  { pattern: /^[a-zA-Z0-9_]+$/, message: '仅支持字母、数字和下划线' },
                ]}>
                  <Input prefix={<UserOutlined className="input-prefix-icon" />} placeholder="用户名（3-20位）" className="custom-input" />
                </Form.Item>
                <Form.Item name="reg_password" rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '至少 8 位' },
                  { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9])/, message: '需包含大小写+数字+特殊字符' },
                ]}>
                  <Input.Password
                    prefix={<LockOutlined className="input-prefix-icon" />}
                    placeholder="密码（8位+复杂度）"
                    className="custom-input"
                    onChange={(e) => setPasswordStrength(calcPasswordStrength(e.target.value))}
                    onKeyDown={handleCapsLock}
                    onKeyUp={handleCapsLock}
                  />
                </Form.Item>
                {renderPasswordStrength()}
                {renderCapsLockWarning()}
                <Form.Item name="reg_confirm_password" dependencies={['reg_password']} rules={[
                  { required: true, message: '请确认密码' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('reg_password') === value) return Promise.resolve();
                      return Promise.reject(new Error('两次输入的密码不一致'));
                    },
                  }),
                ]}>
                  <Input.Password prefix={<SafetyCertificateOutlined className="input-prefix-icon" />} placeholder="确认密码" className="custom-input"
                    onKeyDown={handleCapsLock} onKeyUp={handleCapsLock}
                  />
                </Form.Item>
                <Form.Item name="reg_email">
                  <Input prefix={<MailOutlined className="input-prefix-icon" />} placeholder="邮箱（选填）" className="custom-input" />
                </Form.Item>
                <Form.Item name="reg_nickname">
                  <Input prefix={<UserOutlined className="input-prefix-icon" />} placeholder="昵称（选填）" className="custom-input" />
                </Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  className="login-button"
                  style={{
                    height: 48,
                    borderRadius: 10,
                    fontSize: 16,
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #3B82F6, #6366F1)',
                    border: 'none',
                    boxShadow: '0 4px 14px rgba(59,130,246,0.35)',
                    transition: 'all 0.3s ease',
                  }}
                >
                  注 册
                </Button>
              </Form>
            ),
          },
          {
            key: 'qrcode',
            label: (<span><QrcodeOutlined /> 扫码</span>),
            children: (
              <div style={{ textAlign: 'center', padding: '24px 0' }}>
                <QRCode
                  value="https://trendradar.dev/qrcode-placeholder"
                  size={192}
                  style={{ marginBottom: 20 }}
                />
                <Paragraph type="secondary" style={{ fontSize: 14 }}>微信扫码登录（即将上线）</Paragraph>
                <Button type="link" onClick={() => setActiveTab('login')} style={{ fontWeight: 500 }}>
                  切换到密码登录
                </Button>
              </div>
            ),
          },
        ]}
        onChange={(key) => { setActiveTab(key); setPasswordStrength({ score: 0, label: '', color: '#d9d9d9', percent: 0 }); }}
        centered
        style={{
          '.ant-tabs-nav': { marginBottom: 28 },
          '.ant-tabs-tab': {
            padding: '10px 20px',
            fontSize: 15,
            fontWeight: 500,
            transition: 'all 0.3s ease',
          },
          '.ant-tabs-tab:hover': { color: '#3B82F6' },
          '.ant-tabs-tab-active .ant-tabs-tab-btn': {
            color: '#3B82F6',
            fontWeight: 600,
          },
          '.ant-tabs-ink-bar': {
            background: 'linear-gradient(90deg, #3B82F6, #6366F1)',
            height: 3,
            borderRadius: 2,
          },
        }}
      />

      {activeTab !== 'register' && (
        <>
          <Divider plain style={{ margin: '24px 0', fontSize: 13, color: '#94A3B8' }}>其他方式</Divider>
          <div style={{ textAlign: 'center', animation: 'fadeIn 0.4s ease' }}>
            <Space size={24}>
              <Button
                shape="circle"
                size="large"
                icon={<WechatOutlined style={{ color: '#07C160', fontSize: 22 }} />}
                onClick={() => message.info('微信扫码登录开发中...')}
                style={{
                  transition: 'all 0.3s ease',
                  border: '1px solid #E2E8F0',
                }}
                className="social-button"
              />
            </Space>
          </div>
        </>
      )}

      {/* 底部条款 */}
      <div style={{ textAlign: 'center', marginTop: 28, animation: 'fadeIn 0.5s ease' }}>
        <Text type="secondary" style={{ fontSize: 13, color: '#94A3B8' }}>
          登录即表示同意我们的{' '}
          <Link to="#" onClick={(e) => e.preventDefault()} style={{ color: '#3B82F6', fontWeight: 500 }}>服务条款</Link>
          {' '}和{' '}
          <Link to="#" onClick={(e) => e.preventDefault()} style={{ color: '#3B82F6', fontWeight: 500 }}>隐私政策</Link>
        </Text>
      </div>

      {/* 表单区域动画和样式 */}
      <style>{`
        @keyframes slideInRight {
          from { opacity: 0; transform: translateX(30px); }
          to { opacity: 1; transform: translateX(0); }
        }

        @keyframes shakeAlert {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-8px); }
          40% { transform: translateX(8px); }
          60% { transform: translateX(-6px); }
          80% { transform: translateX(6px); }
        }

        /* 大写锁定提示 */
        .capslock-warning {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 14px;
          margin-top: -12px;
          margin-bottom: 16px;
          background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(251,191,36,0.05));
          border: 1px solid rgba(245,158,11,0.25);
          border-left: 3px solid #F59E0B;
          border-radius: 8px;
          animation: capslockFadeIn 0.3s ease;
        }
        .capslock-icon {
          color: #F59E0B;
          font-size: 16px;
          flex-shrink: 0;
        }
        .capslock-text {
          color: #92400E;
          font-size: 13px;
          line-height: 1.5;
          font-weight: 500;
        }
        @keyframes capslockFadeIn {
          from { opacity: 0; transform: translateY(-6px); }
          to { opacity: 1; transform: translateY(0); }
        }

        /* 自定义输入框样式 */
        .custom-input {
          border-radius: 8px !important;
          transition: all 0.3s ease !important;
          border: 1.5px solid #E2E8F0 !important;
        }
        .custom-input:hover {
          border-color: #94A3B8 !important;
        }
        .custom-input:focus,
        .custom-input.ant-input-affix-wrapper-focused {
          border-color: #3B82F6 !important;
          box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
        }
        .input-prefix-icon {
          color: #94A3B8;
          transition: color 0.3s ease;
          font-size: 16px;
        }
        .custom-input:focus .input-prefix-icon,
        .custom-input.ant-input-affix-wrapper-focused .input-prefix-icon {
          color: #3B82F6;
        }

        /* 登录按钮悬停效果 */
        .login-button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(59,130,246,0.45) !important;
          background: linear-gradient(135deg, #2563EB, #4F46E5) !important;
        }
        .login-button:active:not(:disabled) {
          transform: translateY(0);
          box-shadow: 0 2px 10px rgba(59,130,246,0.3) !important;
        }

        /* 社交按钮效果 */
        .social-button:hover {
          transform: translateY(-3px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          border-color: #07C160 !important;
        }

        /* 表单项间距 */
        .login-form .ant-form-item {
          margin-bottom: 20px;
        }

        /* 自定义错误提示样式 */
        .error-alert {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          padding: 14px 16px;
          margin-bottom: 20px;
          border-radius: 12px;
          background: linear-gradient(135deg, rgba(239, 68, 68, 0.06) 0%, rgba(249, 115, 22, 0.05) 100%);
          border: 1px solid rgba(239, 68, 68, 0.12);
          position: relative;
          overflow: hidden;
          animation: slideInShake 0.5s ease;
        }
        .error-alert::before {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 3px;
          background: linear-gradient(180deg, #EF4444, #F97316);
          border-radius: 0 2px 2px 0;
        }
        .error-alert-icon {
          flex-shrink: 0;
          width: 36px;
          height: 36px;
          border-radius: 10px;
          background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(249, 115, 22, 0.08));
          display: flex;
          align-items: center;
          justify-content: center;
          color: #EF4444;
        }
        .error-alert-content {
          flex: 1;
          min-width: 0;
          padding-top: 1px;
        }
        .error-alert-title {
          font-size: 14px;
          font-weight: 600;
          color: #DC2626;
          margin-bottom: 3px;
          line-height: 1.4;
        }
        .error-alert-desc {
          font-size: 13px;
          color: #7F1D1D;
          opacity: 0.8;
          line-height: 1.5;
          word-break: break-word;
        }
        .error-alert-close {
          flex-shrink: 0;
          width: 28px;
          height: 28px;
          border: none;
          background: transparent;
          border-radius: 6px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #9CA3AF;
          transition: all 0.2s ease;
          margin-top: 1px;
        }
        .error-alert-close:hover {
          background: rgba(239, 68, 68, 0.08);
          color: #EF4444;
        }

        @keyframes slideInShake {
          0% { opacity: 0; transform: translateY(-8px); }
          20% { opacity: 1; transform: translateY(0) translateX(-6px); }
          40% { transform: translateX(6px); }
          60% { transform: translateX(-4px); }
          80% { transform: translateX(3px); }
          100% { transform: translateX(0); }
        }

        /* 复选框样式 */
        .ant-checkbox-wrapper:hover .ant-checkbox-inner {
          border-color: #3B82F6;
        }
      `}</style>
    </div>
  );

  // ---- 主布局 ----
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      background: '#F8FAFC',
      overflow: 'hidden',
    }}>
      {/* 左侧品牌区（桌面端显示，移动端隐藏） */}
      {screens.lg && (
        <div style={{ display: 'flex' }}>
          {renderBrandArea()}
        </div>
      )}

      {/* 右侧表单区 */}
      {renderFormArea()}
    </div>
  );
}
