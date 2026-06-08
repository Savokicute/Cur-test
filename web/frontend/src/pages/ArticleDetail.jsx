import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Typography,
  Card,
  Spin,
  Alert,
  Button,
  Space,
  Tag,
  Empty,
  message,
  Image,
  Tooltip,
  Skeleton,
  Result
} from 'antd';
import {
  ArrowLeft,
  ExternalLink,
  Heart,
  RefreshCw,
  ImageOff,
  Play
} from 'lucide-react';
import { PlayCircleOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import PageHeader from '../components/common/PageHeader';
import HeatScoreBar from '../components/common/HeatScoreBar';
import { getArticleById, refetchArticle } from '../services/articles';
import { getMediaUrl } from '../services/media';
import { useFavorites } from '../contexts/FavoritesContext';
import FavoriteModal from '../components/common/FavoriteModal';

const { Text } = Typography;

/**
 * 优化图片展示组件 (功能 9.6)
 * - 点击放大预览
 * - 响应式布局
 * - 懒加载
 * - 骨架屏加载状态
 * - 加载失败降级显示（功能 9.8）
 */
const OptimizedImage = ({ src, alt, ...props }) => {
  const [imageError, setImageError] = useState(false);
  const [loading, setLoading] = useState(true);

  // 获取媒体 URL
  const imageUrl = getMediaUrl(src) || src;

  // 图片加载失败时的降级 UI
  const renderFallback = () => (
    <div
      style={{
        width: '100%',
        maxWidth: props.width || '100%',
        minHeight: 200,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#fafafa',
        border: '1px dashed #d9d9d9',
        borderRadius: 8,
        padding: 24,
        cursor: 'pointer'
      }}
      onClick={() => imageUrl && window.open(imageUrl, '_blank')}
    >
      <ImageOff size={48} color="#999" style={{ marginBottom: 12 }} />
      <Text type="secondary" style={{ fontSize: 14 }}>
        图片加载失败
      </Text>
      <Text type="secondary" style={{ fontSize: 12, marginTop: 4 }}>
        点击访问原图
      </Text>
      {imageUrl && (
        <ExternalLink size={16} color="#1890ff" style={{ marginTop: 8 }} />
      )}
    </div>
  );

  if (imageError || !imageUrl) {
    return renderFallback();
  }

  return (
    <div style={{ width: '100%', position: 'relative' }}>
      {/* 加载中骨架屏 */}
      {loading && (
        <div style={{ width: '100%' }}>
          <Skeleton.Image
            active
            style={{
              width: '100%',
              height: 300,
              borderRadius: 8
            }}
          />
        </div>
      )}

      {/* 使用 Ant Design Image 组件 */}
      <Image
        src={imageUrl}
        alt={alt || ''}
        preview={{
          mask: (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: 24, marginBottom: 4 }}>点击查看大图</span>
            </div>
          ),
          maskClosable: true
        }}
        placeholder={
          <Skeleton.Image
            active
            style={{
              width: '100%',
              height: 300,
              borderRadius: 8
            }}
          />
        }
        loading="lazy"
        onError={() => {
          setImageError(true);
          setLoading(false);
        }}
        onLoad={() => setLoading(false)}
        style={{
          width: '100%',
          maxWidth: '100%',
          height: 'auto',
          display: loading ? 'none' : 'block',
          borderRadius: 8,
          objectFit: 'cover'
        }}
        fallback={renderFallback()}
        {...props}
      />
    </div>
  );
};

/**
 * 视频播放器组件 (功能 9.7)
 * - 显示封面图 + 播放按钮覆盖层
 * - 点击后在新窗口打开原始链接
 * - 封面图圆角、阴影效果
 * - 无封面图时显示灰色占位区域 + 播放按钮
 */
const VideoPlayer = ({ url, poster, title }) => {
  const [posterError, setPosterError] = useState(false);

  // 视频封面加载失败或无封面时的占位 UI
  const renderPlaceholder = () => (
    <div
      style={{
        width: '100%',
        aspectRatio: '16/9',
        backgroundColor: '#f0f0f0',
        borderRadius: 12,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
        transition: 'all 0.3s ease',
        position: 'relative',
        overflow: 'hidden'
      }}
      onClick={() => window.open(url, '_blank')}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.02)';
        e.currentTarget.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.15)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)';
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
      }}
    >
      <PlayCircleOutlined
        style={{
          fontSize: 64,
          color: '#fff',
          filter: 'drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3))',
          marginBottom: 12
        }}
      />
      <Text style={{ color: '#666', fontSize: 14 }}>
        {title || '点击播放视频'}
      </Text>

      {/* 播放按钮动画效果 */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: 'rgba(24, 144, 255, 0.9)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.3s ease'
        }}
      >
        <Play size={32} color="#fff" fill="#fff" style={{ marginLeft: 4 }} />
      </div>
    </div>
  );

  // 有封面图的正常渲染
  if (!posterError && poster) {
    const posterUrl = getMediaUrl(poster) || poster;
    return (
      <div
        style={{
          width: '100%',
          position: 'relative',
          borderRadius: 12,
          overflow: 'hidden',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          cursor: 'pointer',
          transition: 'all 0.3s ease'
        }}
        onClick={() => window.open(url, '_blank')}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.02)';
          e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.25)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        }}
      >
        <img
          src={posterUrl}
          alt={title || '视频封面'}
          style={{
            width: '100%',
            height: 'auto',
            display: 'block',
            borderRadius: 12
          }}
          onError={() => setPosterError(true)}
          loading="lazy"
        />

        {/* 播放按钮覆盖层 */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'background-color 0.3s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              backgroundColor: 'rgba(24, 144, 255, 0.95)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 16px rgba(24, 144, 255, 0.4)',
              transition: 'all 0.3s ease',
              marginBottom: 12
            }}
          >
            <Play size={36} color="#fff" fill="#fff" style={{ marginLeft: 4 }} />
          </div>
          <Text
            style={{
              color: '#fff',
              fontSize: 14,
              fontWeight: 500,
              textShadow: '0 2px 4px rgba(0, 0, 0, 0.5)'
            }}
          >
            点击播放
          </Text>
        </div>
      </div>
    );
  }

  return renderPlaceholder();
};

/**
 * 自定义 Markdown 渲染组件
 * 处理图片和视频的特殊展示逻辑
 */
const CustomMarkdownRenderer = ({ content }) => {
  // 自定义图片渲染
  const renderImage = ({ node, ...props }) => {
    return (
      <OptimizedImage
        key={props.src}
        src={props.src}
        alt={props.alt}
        style={{ margin: '16px 0' }}
      />
    );
  };

  // 自定义链接渲染（检测视频链接）
  const renderLink = ({ node, href, children, ...props }) => {
    // 检测是否为视频链接
    const videoExtensions = ['.mp4', '.webm', '.ogg', '.mov'];
    const videoPlatforms = ['youtube.com', 'youtu.be', 'vimeo.com', 'bilibili.com'];

    const isVideoLink =
      videoExtensions.some((ext) => href?.toLowerCase().includes(ext)) ||
      videoPlatforms.some((platform) => href?.toLowerCase().includes(platform));

    if (isVideoLink && href) {
      return (
        <VideoPlayer
          key={href}
          url={href}
          title={typeof children === 'string' ? children : '视频'}
          style={{ margin: '16px 0' }}
        />
      );
    }

    return (
      <a
        key={href}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    );
  };

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        img: renderImage,
        a: renderLink
      }}
    >
      {content}
    </ReactMarkdown>
  );
};

const ArticleDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // 支持从热榜页面传入的日期参数，用于查看非当日文章
  const sourceDate = searchParams.get('_source_date') || searchParams.get('date');
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refetching, setRefetching] = useState(false);
  const [favoriteModalVisible, setFavoriteModalVisible] = useState(false);
  // 区分"文章不存在"和"文章尚未抓取"
  const [notYetCrawled, setNotYetCrawled] = useState(false);
  const { addFavorite, removeFavorite, isFavorite } = useFavorites();

  useEffect(() => {
    if (id) {
      fetchArticle();
    }
  }, [id, sourceDate]);

  const fetchArticle = async () => {
    setLoading(true);
    setError(null);
    try {
      const urlNorm = decodeURIComponent(id);
      // 将日期参数传给后端，支持查看历史日期的文章
      const params = {};
      if (sourceDate) {
        params.date = sourceDate;
      }
      const response = await getArticleById(urlNorm, params);
      if (response?.success && response.data) {
        setArticle(response.data);
        setNotYetCrawled(false);
        setError(null);
      } else if (response?.success && !response.data && response.message) {
        // API返回成功但data为空（文章尚未抓取）
        setNotYetCrawled(true);
        setError(response.message);
        setArticle(null);
      } else if (response?.data) {
        // 兼容：部分接口直接返回数据
        setArticle(response.data);
        setNotYetCrawled(false);
      } else {
        setError(response?.message || '获取文章详情失败');
        setNotYetCrawled(false);
      }
    } catch (err) {
      setError(err.message || '获取文章详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefetch = async () => {
    setRefetching(true);
    setError(null);
    try {
      const urlNorm = decodeURIComponent(id);
      const response = await refetchArticle(urlNorm);
      if (response?.success) {
        message.success('重新抓取任务已启动！');
        // 刷新一下，等待一下再重新获取
        setTimeout(() => {
          fetchArticle();
        }, 2000);
      }
    } catch (err) {
      message.error('重新抓取失败：' + (err.message || '未知错误'));
      setError(err.message || '重新抓取失败');
    } finally {
      setRefetching(false);
    }
  };

  const favoriteId = article?.id || article?.url_norm || article?.url;
  const favorited = isFavorite(favoriteId);

  const handleFavoriteClick = () => {
    if (favorited) {
      removeFavorite(favoriteId);
    } else {
      setFavoriteModalVisible(true);
    }
  };

  const handleConfirmFavorite = (tags, remark) => {
    if (article) {
      addFavorite(article, tags, remark);
    }
    setFavoriteModalVisible(false);
  };

  const articleTitle = article?.title_snapshot || article?.extracted_title || '内容详情';
  const articleContent = article?.markdown;
  const articleUrl = article?.url_norm;
  const platformName = article?.platform_id;

  return (
    <div className="article-detail-page">
      <PageHeader
        title={articleTitle}
        breadcrumb={[
          { title: '热榜总览', href: '/' },
          ...(sourceDate ? [{ title: sourceDate, href: '/' }] : []),
          { title: '内容详情' },
        ]}
        extra={
          <Space wrap>
            <Button icon={<ArrowLeft size={16} />} onClick={() => navigate(-1)}>
              返回
            </Button>
            {articleUrl && (
              <Button
                icon={<ExternalLink size={16} />}
                href={articleUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                查看原文
              </Button>
            )}
            <Button
              icon={<RefreshCw size={16} />}
              loading={refetching}
              onClick={handleRefetch}
            >
              重新抓取
            </Button>
            <Button
              type={favorited ? 'primary' : 'default'}
              icon={<Heart size={16} fill={favorited ? 'currentColor' : 'none'} />}
              onClick={handleFavoriteClick}
            >
              {favorited ? '已收藏' : '收藏'}
            </Button>
          </Space>
        }
      />

      {error && (
        notYetCrawled ? (
          <Card style={{ marginBottom: 16, textAlign: 'center', padding: '32px 16px' }}>
            <Result
              icon={<FileTextOutlined style={{ color: '#faad14' }} />}
              title="文章正文尚未抓取"
              description={
                <div>
                  <p>{error}</p>
                  {sourceDate && (
                    <p style={{ color: '#888', fontSize: 13 }}>
                      当前查看日期：<Tag color="blue">{sourceDate}</Tag>
                      {sourceDate !== new Date().toISOString().split('T')[0] && 
                        <span>（非今日数据，正文可能未被自动采集）</span>}
                    </p>
                  )}
                </div>
              }
              extra={[
                <Button type="primary" icon={<ReloadOutlined />} loading={refetching} onClick={handleRefetch}>
                  立即抓取正文
                </Button>,
                <Button href={articleUrl || id} target="_blank" rel="noopener noreferrer">
                  查看原文网站
                </Button>,
              ]}
            />
          </Card>
        ) : (
          <Alert
            message="错误"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )
      )}

      <Spin spinning={loading}>
        {article ? (
        <Card className="detail-card">
          <Space wrap style={{ marginBottom: 16 }}>
            {platformName && <Tag color="blue">{platformName}</Tag>}
            {article?.status && (
              <Tag color={article.status === 'success' ? 'green' : 'orange'}>
                {article.status === 'success' ? '已抓取' : article.status}
              </Tag>
            )}
            {article?.fetched_at && (
              <Text type="secondary">
                抓取时间：{new Date(article.fetched_at).toLocaleString()}
              </Text>
            )}
          </Space>

          {article?.error && (
            <Alert
              type="warning"
              message="抓取时出现错误"
              description={article.error}
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {articleContent ? (
            <article className="markdown-body">
              {/* 使用自定义的 Markdown 渲染器 */}
              <CustomMarkdownRenderer content={articleContent} />
            </article>
          ) : (
            <Alert
              type="info"
              message="正文尚未抓取"
              description="点击「重新抓取」触发正文爬取任务"
              showIcon
            />
          )}
        </Card>
      ) : (
        !loading && (
          <Empty
            description="没有找到这篇文章"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )
      )}
      </Spin>

      <FavoriteModal
        visible={favoriteModalVisible}
        item={article}
        onCancel={() => setFavoriteModalVisible(false)}
        onConfirm={handleConfirmFavorite}
      />
    </div>
  );
};

export default ArticleDetail;
