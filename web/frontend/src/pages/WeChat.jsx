import { useState, useEffect } from 'react';
import { Card, Col, Row, Avatar, Button, Input, Tabs, Tag, Typography, Badge, Space, Spin, Alert, message, Tooltip } from 'antd';
import { Newspaper, Search, ExternalLink, AlertTriangle, LogIn, ArrowRight } from 'lucide-react';
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
  // we-mp-rss 服务连接状态
  const [wempStatus, setWempStatus] = useState('checking'); // 'checking' | 'online' | 'offline'
  
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

  // 检测 we-mp-rss 服务是否在线
  const checkWempStatus = async () => {
    setWempStatus('checking');
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      const res = await fetch('http://localhost:8001/api/v1/system/info', {
        signal: controller.signal,
        mode: 'no-cors',
      });
      clearTimeout(timeoutId);
      setWempStatus('online');
    } catch {
      setWempStatus('offline');
    }
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
    checkWempStatus();
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
              {/* 服务状态指示 */}
              <div className="wemp-status-indicator">
                <span className="wemp-status-dot" data-status={wempStatus} />
                <span className="wemp-status-text">
                  {wempStatus === 'checking' && '正在检测服务...'}
                  {wempStatus === 'online' && 'we-mp-rss 服务已连接'}
                  {wempStatus === 'offline' && 'we-mp-rss 服务未启动'}
                </span>
              </div>
            </Space>
          </div>
        </Col>
        <Col>
          <Button
            type="primary"
            size="large"
            icon={<ArrowRight size={18} />}
            onClick={() => window.open('http://localhost:8001/login', '_blank')}
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
            公众号订阅管理
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            文章自动抓取
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            RSS 输出
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            全文阅读器
          </Tag>
          <Tag style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }}>
            标签分类
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
                        </div>
                      </div>
                    </Space>
                  </Card>
                ))
              ) : (
                <Card title="公众号列表">
                  <Text type="secondary">暂无公众号数据</Text>
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
                        <Button
                          type="text"
                          size="small"
                          icon={<ExternalLink size={14} />}
                          onClick={() => window.open('http://localhost:8001/login', '_blank')}
                        >
                          完整版查看
                        </Button>,
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

      <style>{`
        .wechat-page {
          max-width: 1400px;
          margin: 0 auto;
        }
        
        .management-entry-card .ant-card-body {
          padding: 24px;
        }
        
        .wemp-status-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 6px;
        }

        .wemp-status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #999;
          transition: all 0.3s ease;
          flex-shrink: 0;
        }

        .wemp-status-dot[data-status="checking"] {
          background: #faad14;
          animation: wempPulse 1.5s ease-in-out infinite;
        }

        .wemp-status-dot[data-status="online"] {
          background: #52c41a;
          box-shadow: 0 0 6px rgba(82, 196, 26, 0.5);
        }

        .wemp-status-dot[data-status="offline"] {
          background: #ff4d4f;
        }

        .wemp-status-text {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.85);
        }

        @keyframes wempPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
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
