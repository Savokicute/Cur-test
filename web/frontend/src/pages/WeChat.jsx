import { useState, useEffect } from 'react';
import { Card, Col, Row, Avatar, Button, Input, Tabs, Tag, Typography, Badge, Space, Spin, Alert, message, Tooltip, Modal, Form, Input as AntInput } from 'antd';
import { Newspaper, RefreshCw, Plus, Search, ExternalLink, AlertTriangle, LogIn, Settings, ArrowRight, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import {
  getWechatMps,
  getWechatArticles,
  getWechatStatus,
} from '../services/wechat';

const { Text, Paragraph } = Typography;

const WeChat = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mps, setMps] = useState([]);
  const [articles, setArticles] = useState([]);
  const [selectedMp, setSelectedMp] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [serviceAvailable, setServiceAvailable] = useState(true);
  const [isMockMode, setIsMockMode] = useState(false);
  
  // SSO 相关状态
  const [ssoModalVisible, setSsoModalVisible] = useState(false);
  const [ssoLoading, setSsoLoading] = useState(false);
  const [ssoStatus, setSsoStatus] = useState(null); // "checking" | "online" | "offline"
  const [loginForm] = Form.useForm();
  const [currentUser, setCurrentUser] = useState(null);

  // 检查 SSO 状态
  const checkSSOStatus = async () => {
    setSsoStatus('checking');
    try {
      const response = await fetch('/api/sso/status');
      const data = await response.json();
      setSsoStatus(data.wemp_online ? 'online' : 'offline');
      
      // 从 localStorage 获取用户信息（如果有）
      const savedUser = localStorage.getItem('trendradar_user');
      if (savedUser) {
        setCurrentUser(JSON.parse(savedUser));
      }
    } catch (err) {
      console.error('检查SSO状态失败:', err);
      setSsoStatus('offline');
    }
  };

  // SSO 登录
  const handleSSOLogin = async (values) => {
    setSsoLoading(true);
    try {
      const response = await fetch('/api/sso/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: values.username,
          password: values.password,
          target_path: '/'  // 跳转到 we-mp-rss 首页
        })
      });
      
      const data = await response.json();
      
      if (data.success && data.auto_login_url) {
        // 保存用户信息
        localStorage.setItem('trendradar_user', JSON.stringify({
          username: values.username,
          loginTime: new Date().toISOString()
        }));
        
        message.success({
          content: '✅ 登录成功！正在跳转...',
          duration: 2
        });
        
        // 延迟一下让用户看到成功提示
        setTimeout(() => {
          window.open(data.auto_login_url, '_blank');
          setSsoModalVisible(false);
        }, 800);
      } else {
        message.error(data.message || '登录失败');
      }
    } catch (err) {
      console.error('SSO登录失败:', err);
      message.error('登录请求失败：' + err.message);
    } finally {
      setSsoLoading(false);
    }
  };

  // 快速跳转（已缓存的用户）
  const handleQuickJump = async () => {
    if (!currentUser) {
      setSsoModalVisible(true);
      return;
    }
    
    setSsoLoading(true);
    try {
      const response = await fetch(`/api/sso/generate-url?username=${currentUser.username}&target=/`);
      const data = await response.json();
      
      if (data.success) {
        window.open(data.url, '_blank');
      } else {
        // 缓存过期，需要重新登录
        message.info('登录已过期，请重新登录');
        setSsoModalVisible(true);
      }
    } catch (err) {
      console.error('快速跳转失败:', err);
      message.error('跳转失败');
    } finally {
      setSsoLoading(false);
    }
  };

  // 检查服务状态（增强版：检测 Mock 模式）
  const checkServiceStatus = async () => {
    try {
      const response = await getWechatStatus();
      if (response?.success) {
        const available = response.data.available;
        const mock = response.mock === true;
        
        setServiceAvailable(available);
        setIsMockMode(mock);
        
        if (mock) {
          console.log('⚠️ 当前处于 Mock 数据模式');
        }
        
        return available;
      }
    } catch (err) {
      setServiceAvailable(false);
      setIsMockMode(true);
      return false;
    }
    return true;
  };
  
  // 获取公众号列表（支持 Mock 模式）
  const fetchMps = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getWechatMps();
      if (response?.success) {
        setMps(response.data || []);
        
        if (response.mock === true) {
          setIsMockMode(true);
          console.log('获取到 Mock 公众号数据');
        }
      }
    } catch (err) {
      setError(err.message || '获取公众号列表失败');
    } finally {
      setLoading(false);
    }
  };
  
  // 获取文章列表（支持 Mock 模式）
  const fetchArticles = async (mpId = null) => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (mpId) {
        params.mp_id = mpId;
      }
      
      const response = await getWechatArticles(params);
      if (response?.success) {
        setArticles(response.data || []);
        
        if (response.mock === true) {
          setIsMockMode(true);
          console.log('获取到 Mock 文章数据');
        }
      }
    } catch (err) {
      setError(err.message || '获取文章列表失败');
    } finally {
      setLoading(false);
    }
  };
  
  // 初始化
  useEffect(() => {
    checkServiceStatus();
    checkSSOStatus();
    fetchMps();
    fetchArticles();
  }, []);
  
  // 当选中公众号变化时
  useEffect(() => {
    fetchArticles(selectedMp);
  }, [selectedMp]);
  
  // 过滤公众号
  const filteredMps = mps.filter(mp => 
    (mp.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (mp.account || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  // SSO 状态指示器
  const renderSSOIndicator = () => (
    <div className="sso-indicator">
      <Space>
        <span style={{ fontSize: 13, color: '#666' }}>
          微信管理服务：
        </span>
        {ssoStatus === 'checking' && (
          <Tag icon={<Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />} color="processing">
            检测中...
          </Tag>
        )}
        {ssoStatus === 'online' && (
          <Tag icon={<CheckCircle2 size={12} />} color="success">
            在线
          </Tag>
        )}
        {ssoStatus === 'offline' && (
          <Tag icon={<XCircle size={12} />} color="error">
            离线
          </Tag>
        )}
      </Space>
    </div>
  );
  
  // 完整管理入口卡片
  const renderManagementCard = () => (
    <Card 
      className="management-entry-card"
      style={{ 
        marginBottom: 20, 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        border: 'none'
      }}
    >
      <Row gutter={16} align="middle">
        <Col flex="auto">
          <div style={{ color: 'white' }}>
            <Space direction="vertical" size={4}>
              <Text strong style={{ fontSize: 18, color: 'white', display: 'flex', alignItems: 'center', gap: 8 }}>
                <LogIn size={22} />
                微信公众号完整管理系统
              </Text>
              <Text style={{ color: 'rgba(255,255,255,0.9)', fontSize: 13 }}>
                订阅、抓取、阅读、收藏 - we-mp-rss 全功能平台
              </Text>
              {renderSSOIndicator()}
            </Space>
          </div>
        </Col>
        <Col>
          <Button
            type="primary"
            size="large"
            icon={<ArrowRight size={18} />}
            loading={ssoLoading}
            disabled={ssoStatus === 'offline'}
            onClick={handleQuickJump}
            style={{ 
              background: 'white', 
              color: '#667eea',
              fontWeight: 600,
              height: 48,
              paddingLeft: 24,
              paddingRight: 24,
              borderRadius: 8,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
            }}
          >
            进入完整管理 →
          </Button>
        </Col>
      </Row>
      
      {/* 功能特性标签 */}
      <div style={{ marginTop: 16 }}>
        <Space wrap size={[8, 8]}>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            ✅ 公众号订阅管理
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            ✅ 文章自动抓取
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            ✅ RSS 输出
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            ✅ 全文阅读器
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            ✅ 标签分类
          </Tag>
        </Space>
      </div>
    </Card>
  );

  return (
    <div className="wechat-page">
      <PageHeader
        title="微信公众号"
        description="订阅公众号文章，统一管理阅读与收藏"
        extra={
          <Space>
            <Button 
              icon={<Settings size={16} />}
              onClick={() => setSsoModalVisible(true)}
            >
              账户设置
            </Button>
            <Button type="primary" icon={<Plus size={16} />} disabled={isMockMode}>
              添加公众号
            </Button>
          </Space>
        }
      />

      {/* 完整管理入口 */}
      {renderManagementCard()}

      {/* Mock 模式提示横幅 */}
      {isMockMode && (
        <Alert
          message={
            <span>
              <AlertTriangle size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              当前显示演示数据（we-mp-rss 服务未连接）
            </span>
          }
          description={
            <div>
              <p>要启用完整功能，请按以下步骤操作：</p>
              <ol style={{ marginLeft: 20, marginBottom: 8 }}>
                <li>安装依赖：<code>cd we-mp-rss &amp;&amp; pip install -r requirements.txt</code></li>
                <li>启动服务：<code>uv run python main.py -job True</code></li>
                <li>刷新本页面</li>
              </ol>
              <p>或者使用一键启动脚本：<code>python scripts/start_platform.py</code></p>
              
              {!isMockMode && ssoStatus === 'online' && (
                <div style={{ marginTop: 12 }}>
                  <Button 
                    type="link" 
                    icon={<LogIn size={14} />}
                    onClick={() => setSsoModalVisible(true)}
                    style={{ padding: 0, color: '#667eea' }}
                  >
                    或直接登录完整管理系统 →
                  </Button>
                </div>
              )}
            </div>
          }
          type="warning"
          showIcon
          closable
          onClose={() => setIsMockMode(false)}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 原有的服务不可用提示（仅在非 Mock 模式且服务不可用时显示） */}
      {!serviceAvailable && !isMockMode && (
        <Alert
          message="服务不可用"
          description="we-mp-rss 服务未启动，请先启动该服务"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {error && (
        <Alert
          message="错误"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        type="card"
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'all', label: '全部' },
          { key: 'tech', label: '科技' },
          { key: 'finance', label: '财经' },
          { key: 'life', label: '生活' },
        ]}
        style={{ marginBottom: 16 }}
      />

      <Input
        placeholder="搜索公众号..."
        prefix={<Search size={16} aria-hidden />}
        allowClear
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        style={{ marginBottom: 20, maxWidth: 360 }}
        aria-label="搜索公众号"
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Spin spinning={loading}>
              {filteredMps.length > 0 ? (
                filteredMps.map((mp) => (
                  <Card
                    key={mp.id}
                    hoverable
                    className="wechat-account-card"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedMp(mp.id)}
                  >
                    <Space align="start">
                      <Badge status={mp.status === 1 ? 'success' : 'default'} dot>
                        <Avatar
                          size={48}
                          src={mp.avatar}
                          style={{ background: mp.avatar ? 'transparent' : '#1E40AF' }}
                        >
                          {(mp.name || '')[0]}
                        </Avatar>
                      </Badge>
                      <div>
                        <Text strong>{mp.name}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {mp.account}
                          {mp.article_count != null && ` · ${mp.article_count} 篇`}
                        </Text>
                        <br />
                        {mp.updated_at && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            更新于 {new Date(mp.updated_at).toLocaleString()}
                          </Text>
                        )}
                        <div style={{ marginTop: 8 }}>
                          <Button
                            size="small"
                            type="link"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedMp(mp.id);
                            }}
                          >
                            查看文章
                          </Button>
                          <Tooltip title={isMockMode ? "需要启动 we-mp-rss 服务" : "抓取最新文章"}>
                            <Button
                              size="small"
                              type="link"
                              icon={<RefreshCw size={12} />}
                              disabled={isMockMode}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (isMockMode) {
                                  message.warning('当前为演示模式，无法抓取文章');
                                  return;
                                }
                                message.info('正在刷新...');
                              }}
                            >
                              抓取
                            </Button>
                          </Tooltip>
                        </div>
                      </div>
                    </Space>
                  </Card>
                ))
              ) : (
                <Card title="公众号列表">
                  <Text type="secondary">暂无公众号数据</Text>
                  
                  {!isMockMode && ssoStatus === 'online' && (
                    <div style={{ marginTop: 12 }}>
                      <Button 
                        type="primary" 
                        icon={<LogIn size={14} />}
                        onClick={() => setSsoModalVisible(true)}
                        block
                      >
                        登录完整管理系统添加公众号
                      </Button>
                    </div>
                  )}
                </Card>
              )}
            </Spin>
          </Space>
        </Col>

        <Col xs={24} lg={16}>
          <Card
            title={selectedMp ? '该公众号文章' : '最新文章'}
            extra={
              <Space>
                <Tag color="blue">{articles.length} 篇</Tag>
                {selectedMp && (
                  <Button size="small" onClick={() => setSelectedMp(null)}>
                    查看全部
                  </Button>
                )}
              </Space>
            }
          >
            <Spin spinning={loading}>
              {articles.length > 0 ? (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  {articles.map((article) => (
                    <Card
                      key={article.id}
                      size="small"
                      hoverable
                      style={{ cursor: 'pointer' }}
                      actions={[
                        <Button
                          type="text"
                          size="small"
                          icon={<ExternalLink size={14} />}
                          onClick={() => {
                            if (article.url && article.url !== '#') {
                              window.open(article.url, '_blank');
                            } else if (isMockMode) {
                              message.info('演示数据无真实链接');
                            }
                          }}
                        >
                          原文链接
                        </Button>,
                        <Tooltip title={isMockMode ? "需要启动 we-mp-rss 服务" : "在完整系统中查看"}>
                          <Button
                            type="text"
                            size="small"
                            icon={<ExternalLink size={14} />}
                            onClick={() => {
                              if (!isMockMode && ssoStatus === 'online') {
                                handleQuickJump();
                              } else {
                                message.warning(isMockMode ? '需要启动服务' : '服务未在线');
                              }
                            }}
                          >
                            完整版查看
                          </Button>
                        </Tooltip>,
                      ]}
                    >
                      <Space align="start">
                        <Newspaper size={20} color="#1E40AF" aria-hidden />
                        <div style={{ flex: 1 }}>
                          <Paragraph strong style={{ marginBottom: 4 }}>
                            {article.title}
                          </Paragraph>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {article.published_at && new Date(article.published_at).toLocaleString()}
                            {article.read_count != null && ` · 阅读 ${article.read_count}`}
                            {article.like_count != null && ` · 点赞 ${article.like_count}`}
                          </Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {article.mp_name}
                            {article.is_favorite && <Tag color="red" style={{ marginLeft: 8 }}>已收藏</Tag>}
                            {article.is_read && <Tag color="green" style={{ marginLeft: 8 }}>已读</Tag>}
                          </Text>
                        </div>
                      </Space>
                    </Card>
                  ))}
                </Space>
              ) : (
                <Text type="secondary">暂无文章数据</Text>
              )}
            </Spin>
          </Card>
        </Col>
      </Row>

      {/* SSO 登录弹窗 */}
      <Modal
        title={
          <Space>
            <LogIn size={20} />
            <span>登录微信管理系统</span>
          </Space>
        }
        open={ssoModalVisible}
        onCancel={() => setSsoModalVisible(false)}
        footer={null}
        width={420}
      >
        <div style={{ padding: '16px 0' }}>
          {ssoStatus === 'offline' ? (
            <Alert
              message="服务未启动"
              description={
                <div>
                  <p>we-mp-rss 服务当前离线。</p>
                  <p style={{ marginTop: 8 }}>请先启动服务：</p>
                  <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 6, marginTop: 8 }}>
{`cd we-mp-rss
python main.py -job True`}
                  </pre>
                </div>
              }
              type="warning"
              showIcon
            />
          ) : (
            <>
              <div style={{ marginBottom: 20, textAlign: 'center' }}>
                <div style={{
                  width: 64, height: 64, borderRadius: '50%',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 16px'
                }}>
                  <LogIn size={32} color="white" />
                </div>
                <Text strong style={{ fontSize: 16 }}>
                  使用热点平台账户登录 we-mp-rss
                </Text>
                <br />
                <Text type="secondary" style={{ fontSize: 13 }}>
                  两个系统将共享相同的账户信息
                </Text>
              </div>
              
              <Form
                form={loginForm}
                onFinish={handleSSOLogin}
                layout="vertical"
                initialValues={currentUser ? { username: currentUser.username } : {}}
              >
                <Form.Item
                  name="username"
                  rules={[{ required: true, message: '请输入用户名' }]}
                >
                  <AntInput 
                    prefix={<span style={{ color: '#999' }}>👤</span>} 
                    placeholder="用户名" 
                    size="large"
                  />
                </Form.Item>
                
                <Form.Item
                  name="password"
                  rules={[{ required: true, message: '请输入密码' }]}
                >
                  <AntInput.Password 
                    prefix={<span style={{ color: '#999' }}>🔒</span>} 
                    placeholder="密码" 
                    size="large"
                  />
                </Form.Item>
                
                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={ssoLoading}
                    block
                    size="large"
                    style={{ 
                      height: 48, 
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      border: 'none',
                      fontWeight: 600,
                      fontSize: 16
                    }}
                  >
                    {ssoLoading ? '正在登录...' : '登录并跳转 →'}
                  </Button>
                </Form.Item>
              </Form>
              
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  💡 提示：首次使用需要在 we-mp-rss 中注册相同账户
                </Text>
              </div>
            </>
          )}
        </div>
      </Modal>

      <style>{`
        .wechat-page {
          max-width: 1400px;
          margin: 0 auto;
        }
        
        .management-entry-card .ant-card-body {
          padding: 24px;
        }
        
        .sso-indicator {
          margin-top: 4px;
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        .wechat-account-card:hover {
          transform: translateY(-2px);
          transition: all 0.3s ease;
        }
      `}</style>
    </div>
  );
};

export default WeChat;
