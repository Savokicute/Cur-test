import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Image,
  Tag,
  Typography,
  Spin,
  Empty,
  Button,
  Space,
  Descriptions,
  Alert,
  Tooltip,
  Badge,
  Statistic,
  Divider,
} from 'antd';
import {
  PictureOutlined,
  LinkOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  ExportOutlined,
  InfoCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { message } from 'antd';

const { Title, Text, Paragraph } = Typography;

export default function MediaTestPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/test/sina-raw');
      const json = await res.json();
      if (json?.success) {
        setData(json.data);
        setItems(json.data.items || []);
      } else {
        setError(json?.error || 'Failed to load test data');
      }
    } catch (e) {
      setError(e.message || 'Network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const copyUrl = (url) => {
    navigator.clipboard.writeText(url).then(() => {
      message.success('URL copied!');
    }).catch(() => {
      message.error('Copy failed');
    });
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin size="large" tip="Loading test results..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 40 }}>
        <Alert
          type="error"
          message="Load Failed"
          description={error}
          showIcon
          action={
            <Button icon={<ReloadOutlined />} onClick={fetchData}>
              Retry
            </Button>
          }
        />
      </div>
    );
  }

  const contentImages = items.filter((item) => {
    const url = item.url?.toLowerCase() || '';
    const alt = (item.alt || '').toLowerCase();
    return !['icon', 'logo', 'qr', 'login'].some(k => url.includes(k) || alt.includes(k));
  });

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size={4}>
              <Title level={3} style={{ margin: 0 }}>
                <PictureOutlined /> Media Extraction Test
              </Title>
              <Text type="secondary">
                {data?.title || 'Sina News Page Test'}
              </Text>
              </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={fetchData}
            >
              Refresh
            </Button>
          </Col>
        </Row>

        <Divider style={{ margin: '16px 0' }} />

        <Row gutter={24}>
          <Col span={6}>
            <Statistic title="Total Found" value={items.length} prefix={<PictureOutlined />} />
          </Col>
          <Col span={6}>
            <Statistic
              title="Content Images"
              value={contentImages.length}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic title="Source" value="Sina News" suffix={<LinkOutlined />} />
          </Col>
          <Col span={6}>
            <a href={data?.url} target="_blank" rel="noreferrer">
              <Button icon={<ExportOutlined />} block>
                View Original Page
              </Button>
            </a>
          </Col>
        </Row>
      </Card>

      {/* Image Gallery */}
      <Card
        title={
          <Space>
            <span>Extracted Images</span>
            <Badge count={contentImages.length} style={{ backgroundColor: '#1890ff' }} />
          </Space>
        }
        extra={
          <Text type="secondary">
            Showing {contentImages.length} content images (from {items.length} total)
          </Text>
        }
      >
        {contentImages.length === 0 ? (
          <Empty description="No images found on this page" />
        ) : (
          <Row gutter={[16, 16]}>
            {contentImages.map((item, idx) => {
              const imgUrl = item.url;
              const hasAlt = item.alt && item.alt.trim().length > 0;

              return (
                <Col key={idx} xs={24} sm={12} md={8} lg={6} xl={4}>
                  <Card
                    size="small"
                    hoverable
                    style={{ height: '100%' }}
                    cover={
                      <div style={{ position: 'relative', overflow: 'hidden', background: '#f5f5f5' }}>
                        <Image
                          src={imgUrl}
                          alt={item.alt || `Image ${idx + 1}`}
                          fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIgIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMzIgZmlsbD0ibm9uZSI+PHJlY3QgeD0iNCIgeT0iNCIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iMTYiIHk9IjE2IiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiPlAvdGV4dD48L3N2Zz4="
                          style={{
                            width: '100%',
                            height: 180,
                            objectFit: 'cover',
                          }}
                          preview={{
                            mask: (
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                                <Text style={{ color: '#fff' }}>Click to preview</Text>
                              </div>
                            ),
                          }}
                        />
                        <Tag
                          color="blue"
                          style={{
                            position: 'absolute',
                            top: 8,
                            left: 8,
                            fontSize: 11,
                          }}
                        >
                          #{idx + 1}
                        </Tag>
                      </div>
                    }
                    actions={[
                      <Tooltip title="Copy URL" key="copy">
                        <Button
                          type="text"
                          size="small"
                          icon={<CopyOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            copyUrl(imgUrl);
                          }}
                        >
                          URL
                        </Button>
                      </Tooltip>,
                      <Tooltip title="Open in new tab" key="open">
                        <Button
                          type="text"
                          size="small"
                          icon={<ExportOutlined />}
                          onClick={() => window.open(imgUrl, '_blank')}
                        >
                          Open
                        </Button>
                      </Tooltip>,
                    ]}
                  >
                    <Card.Meta
                      title={
                        <Text ellipsis style={{ maxWidth: '100%' }} title={item.alt || `Image ${idx + 1}`}>
                          {hasAlt ? item.alt : `Image ${idx + 1}`}
                        </Text>
                      }
                      description={
                        <Space direction="vertical" size={4}>
                          <Text type="secondary" ellipsis style={{ fontSize: 11 }}>
                            {item.source}
                          </Text>
                          <Text
                            copyable={{ text: imgUrl }}
                            ellipsis
                            style={{ fontSize: 10, color: '#999' }}
                          >
                            {imgUrl.replace('https://', '').substring(0, 35)}...
                          </Text>
                        </Space>
                      }
                    />
                  </Card>
                </Col>
              );
            })}
          </Row>
        )}
      </Card>

      {/* All URLs List */}
      <Card
        title={<span>All Extracted URLs ({items.length})</span>}
        style={{ marginTop: 24 }}
        size="small"
      >
        <div style={{ maxHeight: 300, overflowY: 'auto' }}>
          {items.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '6px 0',
                borderBottom: idx < items.length - 1 ? '1px solid #f0f0f0' : 'none',
              }}
            >
              <Space size={8}>
                <Text strong style={{ width: 28 }}>{idx + 1}</Text>
                <Tag>{item.type}</Tag>
                <Text
                  copyable={{ text: item.url }}
                  ellipsis
                  style={{ maxWidth: 400, fontSize: 12 }}
                >
                  {item.url}
                </Text>
              </Space>
              <Space>
                {item.alt && <Tooltip title={item.alt}><Text type="secondary">{item.alt.substring(0, 15)}</Text></Tooltip>}
                <a href={item.url} target="_blank" rel="noreferrer">
                  <ExportOutlined style={{ fontSize: 12, color: '#1890ff' }} />
                </a>
              </Space>
            </div>
          ))}
        </div>
      </Card>

      {/* Info Section */}
      <Card style={{ marginTop: 24 }} type="inner" title="About This Test">
        <Descriptions column={2} size="small" bordered>
          <Descriptions.Item label="Test URL">{data?.url}</Descriptions.Item>
          <Descriptions.Item label="Page Title">{data?.title}</Descriptions.Item>
          <Descriptions.Item label="Extraction Method">BeautifulSoup + HTTPX</Descriptions.Item>
          <Descriptions.Item label="Media Types">img / meta og:image / style bg</Descriptions.Item>
          <Descriptions.Item label="Date">{new Date().toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="Status">
            <Badge status="success" text="Complete" />
          </Descriptions.Item>
        </Descriptions>
        <Divider />
        <Paragraph type="secondary">
          <InfoCircleOutlined /> This page demonstrates media extraction capabilities for news content.
          Images are loaded directly from their original CDN sources. For production use,
          images would be downloaded locally via the MediaService and served through `/api/media/files/`.
        </Paragraph>
      </Card>
    </div>
  );
}
