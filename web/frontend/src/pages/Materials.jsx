import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Card, 
  List, 
  Tabs, 
  Tag, 
  Button, 
  Input, 
  Select, 
  DatePicker, 
  Space, 
  Typography,
  Empty,
  Spin,
  Alert,
  Modal,
  Form,
  Drawer
} from 'antd';
import { 
  BookMarked, 
  Search, 
  Filter, 
  Plus, 
  Trash2, 
  Edit2, 
  ExternalLink,
  Calendar,
  Star,
  Settings
} from 'lucide-react';
import dayjs from 'dayjs';
import PageHeader from '../components/common/PageHeader';
import { useFavorites } from '../contexts/FavoritesContext';

const { Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;
const { TextArea } = Input;

const Materials = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState(null);
  const [dateRange, setDateRange] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { favorites, removeFavorite, updateRemark, updateTags, addFavorite } = useFavorites();
  const [form] = Form.useForm();

  // 过滤数据
  const filtered = useMemo(() => {
    let list = favorites;
    
    if (activeTab !== 'all') {
      list = list.filter(item => item.type === activeTab);
    }
    
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(item => 
        (item.title || '').toLowerCase().includes(q) ||
        (item.remark || '').toLowerCase().includes(q) ||
        (item.tags || []).some(tag => tag.toLowerCase().includes(q))
      );
    }
    
    if (selectedType) {
      list = list.filter(item => item.type === selectedType);
    }
    
    if (dateRange && dateRange[0] && dateRange[1]) {
      const start = dateRange[0].startOf('day');
      const end = dateRange[1].endOf('day');
      list = list.filter(item => {
        const addedAt = dayjs(item.addedAt);
        return addedAt.isAfter(start) && addedAt.isBefore(end);
      });
    }
    
    return list;
  }, [favorites, activeTab, searchQuery, selectedType, dateRange]);

  // 获取类型标签
  const getTypeTag = (type) => {
    const types = {
      hotspot: { color: 'blue', label: '热榜' },
      article: { color: 'green', label: '网站文章' },
      wechat: { color: 'purple', label: '公众号文章' }
    };
    return types[type] || { color: 'gray', label: type };
  };

  // 处理点击查看详情
  const handleViewDetail = (item, e) => {
    e.stopPropagation(); // 防止触发卡片的其他点击事件
    if (item.url_norm) {
      navigate(`/articles/${encodeURIComponent(item.url_norm)}`);
    } else if (item.url) {
      navigate(`/articles/${encodeURIComponent(item.url)}`);
    }
  };

  // 打开编辑
  const openEdit = (item, e) => {
    e.stopPropagation();
    setEditingItem(item);
    form.setFieldsValue({
      tags: item.tags || [],
      remark: item.remark || ''
    });
    setDrawerOpen(true);
  };

  // 保存编辑
  const handleSaveEdit = () => {
    const values = form.getFieldsValue();
    updateTags(editingItem.id, values.tags || []);
    updateRemark(editingItem.id, values.remark || '');
    setDrawerOpen(false);
    setEditingItem(null);
  };

  return (
    <div className="materials-page">
      <PageHeader
        title="素材中心"
        description="管理收藏的内容，添加标签和备注"
        extra={
          <Space>
            <Button 
              icon={<Filter size={16} />} 
              onClick={() => setShowAdvanced(!showAdvanced)}
              type={showAdvanced ? 'primary' : 'default'}
            >
              高级筛选
            </Button>
            <Button type="primary" icon={<Plus size={16} />} onClick={() => {
              Modal.info({
                title: '提示',
                content: '请在热榜总览或内容详情页点击收藏按钮添加内容',
              });
            }}>
              添加收藏
            </Button>
          </Space>
        }
      />

      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle" direction="vertical" style={{ width: '100%' }}>
          <Input.Search
            placeholder="搜索标题、备注或标签"
            prefix={<Search size={16} />}
            allowClear
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: 400 }}
          />
          
          {showAdvanced && (
            <Space wrap size="middle" style={{ width: '100%' }}>
              <Select
                placeholder="选择类型"
                allowClear
                value={selectedType}
                onChange={setSelectedType}
                style={{ width: 150 }}
              >
                <Option value="hotspot">热榜</Option>
                <Option value="article">网站文章</Option>
                <Option value="wechat">公众号文章</Option>
              </Select>

              <RangePicker
                placeholder={['开始日期', '结束日期']}
                value={dateRange}
                onChange={setDateRange}
                allowClear
              />

              <Button 
                type="text" 
                onClick={() => {
                  setSelectedType(null);
                  setDateRange(null);
                  setSearchQuery('');
                  setActiveTab('all');
                }}
              >
                重置所有
              </Button>
            </Space>
          )}
        </Space>
      </Card>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        items={[
          { key: 'all', label: `全部 (${favorites.length})` },
          { key: 'hotspot', label: `热榜 (${favorites.filter(f => f.type === 'hotspot').length})` },
          { key: 'article', label: `网站文章 (${favorites.filter(f => f.type === 'article').length})` },
          { key: 'wechat', label: `公众号文章 (${favorites.filter(f => f.type === 'wechat').length})` },
        ]}
        style={{ marginBottom: 16 }}
      />

      <Spin spinning={false}>
        {filtered.length > 0 ? (
          <List
            grid={{ gutter: 16, column: 1, md: 2, lg: 3 }}
            dataSource={filtered}
            renderItem={(item) => {
              const typeInfo = getTypeTag(item.type);
              return (
                <List.Item>
                  <Card
                    title={
                      <Space>
                        <BookMarked size={16} />
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {item.title}
                        </span>
                      </Space>
                    }
                    hoverable
                    style={{ cursor: 'pointer' }}
                    onClick={(e) => handleViewDetail(item, e)}
                    actions={[
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<ExternalLink size={14} />}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (item.url) {
                            window.open(item.url, '_blank');
                          }
                        }}
                      >
                        查看原文
                      </Button>,
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<Edit2 size={14} />}
                        onClick={(e) => openEdit(item, e)}
                      >
                        编辑
                      </Button>,
                      <Button 
                        type="text" 
                        size="small" 
                        icon={<Trash2 size={14} />}
                        danger
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFavorite(item.id);
                        }}
                      >
                        删除
                      </Button>,
                    ]}
                  >
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Space wrap>
                        <Tag color={typeInfo.color}>{typeInfo.label}</Tag>
                        <Tag>{item.platform}</Tag>
                        {(item.tags || []).map(tag => (
                          <Tag key={tag} color="cyan">{tag}</Tag>
                        ))}
                      </Space>

                      {item.remark && (
                        <Alert
                          message="备注"
                          description={item.remark}
                          type="info"
                          showIcon
                          icon={<Star size={14} />}
                        />
                      )}

                      <Space>
                        <Calendar size={14} />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {dayjs(item.addedAt).format('YYYY-MM-DD HH:mm')}
                        </Text>
                      </Space>
                    </Space>
                  </Card>
                </List.Item>
              );
            }}
          />
        ) : (
          <Empty
            description={searchQuery || selectedType || dateRange ? '没有找到匹配的内容' : '暂无收藏内容'}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            {!searchQuery && !selectedType && !dateRange && (
              <Text type="secondary">
                请在热榜总览或内容详情页点击收藏按钮添加内容
              </Text>
            )}
          </Empty>
        )}
      </Spin>

      <Drawer
        title="编辑收藏"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onOk={handleSaveEdit}
        width={500}
      >
        <Form form={form} layout="vertical">
          <div style={{ marginBottom: 16 }}>
            <Text strong>标题：</Text>
            <Paragraph>{editingItem?.title}</Paragraph>
          </div>

          <Form.Item
            label="标签"
            name="tags"
          >
            <Select
              mode="tags"
              style={{ width: '100%' }}
              placeholder="添加标签（支持自定义）"
              options={[
                { value: '重要', label: '重要' },
                { value: '待阅读', label: '待阅读' },
                { value: '已阅读', label: '已阅读' },
                { value: 'AI', label: 'AI' },
                { value: '科技', label: '科技' },
              ]}
            />
          </Form.Item>

          <Form.Item
            label="备注"
            name="remark"
          >
            <TextArea
              rows={6}
              placeholder="添加备注说明"
            />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  );
};

export default Materials;
