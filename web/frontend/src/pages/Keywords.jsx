/**
 * 关键词配置页
 *
 * 提供关键词配置的编辑、预览、验证和保存功能
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Input,
  message,
  Tabs,
  Tag,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Alert,
  Spin,
  Modal,
  Form,
  Divider,
  Tooltip,
  Badge,
  List,
} from 'antd';
import {
  SaveOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  ExperimentOutlined,
  CopyOutlined,
  HistoryOutlined,
  InfoCircleOutlined,
  SearchOutlined,
  PlusOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';

import {
  getKeywordConfig,
  saveKeywordConfig,
  getParsedKeywords,
  validateKeywordConfig,
  testKeywordMatch,
} from '../services/keywords';

const { TextArea } = Input;
const { Text, Title, Paragraph } = Typography;

export default function KeywordsPage() {
  // 状态管理
  const [configContent, setConfigContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const [activeTab, setActiveTab] = useState('editor');
  const [modified, setModified] = useState(false);

  // 测试匹配状态
  const [testTitle, setTestTitle] = useState('');
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  // 验证结果
  const [validationResult, setValidationResult] = useState(null);

  // 加载配置
  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getKeywordConfig();
      if (res.success) {
        setConfigContent(res.data.content);
        setOriginalContent(res.data.content);
        setModified(false);
        message.success(`配置加载成功 (${res.data.size} 字符)`);
      }
    } catch (error) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始化加载
  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  // 内容变更处理
  const handleContentChange = (e) => {
    setConfigContent(e.target.value);
    setModified(e.target.value !== originalContent);
  };

  // 保存配置
  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await saveKeywordConfig(configContent, true);
      if (res.success) {
        setOriginalContent(configContent);
        setModified(false);
        message.success('配置保存成功' + (
          res.data.backup_filename ? ` (已备份: ${res.data.backup_filename})` : ''
        ));
        // 重新加载数据
        await loadParsedData();
      }
    } catch (error) {
      message.error('保存失败: ' + error.message);
    } finally {
      setSaving(false);
    }
  };

  // 加载解析后的数据
  const loadParsedData = async () => {
    try {
      const res = await getParsedKeywords();
      if (res.success) {
        setParsedData(res.data);
      }
    } catch (error) {
      console.error('解析数据加载失败:', error);
    }
  };

  // 验证配置
  const handleValidate = async () => {
    setValidating(true);
    try {
      const res = await validateKeywordConfig(configContent);
      if (res.success) {
        setValidationResult(res);
        
        if (res.valid) {
          message.success(`验证通过: ${res.parsed_groups} 个分组, ${res.total_keywords()} 个关键词`);
        } else {
          message.warning(`发现 ${res.errors.length} 个错误`);
        }

        // 如果验证通过，重新加载解析数据
        if (res.valid) {
          await loadParsedData();
        }
      }
    } catch (error) {
      message.error('验证失败');
    } finally {
      setValidating(false);
    }
  };

  // 测试匹配
  const handleTestMatch = async () => {
    if (!testTitle.trim()) {
      message.warning('请输入要测试的标题');
      return;
    }

    setTesting(true);
    try {
      const res = await testKeywordMatch(testTitle);
      if (res.success) {
        setTestResult(res.data);
      }
    } catch (error) {
      message.error('测试失败');
    } finally {
      setTesting(false);
    }
  };

  // 重置为原始内容
  const handleReset = () => {
    Modal.confirm({
      title: '确认重置',
      content: '确定要重置所有修改吗？未保存的更改将丢失。',
      okText: '确认重置',
      onOk() {
        setConfigContent(originalContent);
        setModified(false);
        message.info('已重置为原始内容');
      },
    });
  };

  return (
    <div className="keywords-page">
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>
            <SearchOutlined /> 关键词配置
          </Title>
          {modified && (
            <Tag color="orange">已修改</Tag>
          )}
        </Space>
      </div>

      {/* 统计信息 */}
      {parsedData && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="分组数"
                value={parsedData.group_count}
                prefix={<PlusOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="关键词"
                value={parsedData.total_keywords}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="过滤词"
                value={parsedData.filter_count}
                valueStyle={{ color: parsedData.filter_count > 0 ? '#cf1322' : '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="全局过滤"
                value={parsedData.global_filter_count}
                valueStyle={{ color: parsedData.global_filter_count > 0 ? '#cf1322' : '#3f8600' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主内容区 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'editor',
              label: '配置编辑器',
              children: (
                <div className="editor-tab">
                  <Spin spinning={loading}>
                    <TextArea
                      value={configContent}
                      onChange={handleContentChange}
                      placeholder="正在加载关键词配置..."
                      autoSize={{ minRows: 20, maxRows: 40 }}
                      style={{
                        fontFamily: '"Courier New", Consolas, monospace',
                        fontSize: 13,
                        lineHeight: 1.6,
                      }}
                    />
                  </Spin>

                  {/* 操作按钮 */}
                  <div
                    style={{
                      marginTop: 16,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <Space>
                      <Button
                        type="primary"
                        icon={<SaveOutlined />}
                        loading={saving}
                        onClick={handleSave}
                        disabled={!modified}
                      >
                        保存配置
                      </Button>
                      <Button
                        icon={<CheckCircleOutlined />}
                        loading={validating}
                        onClick={handleValidate}
                      >
                        验证语法
                      </Button>
                      <Button
                        icon={<ReloadOutlined />}
                        onClick={handleReset}
                        disabled={!modified}
                      >
                        重置
                      </Button>
                      <Button icon={<ReloadOutlined />} onClick={loadConfig}>
                        重新加载
                      </Button>
                    </Space>

                    <Text type="secondary">
                      {configContent.length} 字符
                    </Text>
                  </div>

                  {/* 验证结果显示 */}
                  {validationResult && (
                    <div style={{ marginTop: 16 }}>
                      {validationResult.valid ? (
                        <Alert
                          type="success"
                          showIcon
                          message="语法验证通过"
                          description={
                            <span>
                              解析出{' '}
                              <Text strong>{validationResult.parsed_groups}</Text> 个分
                              组, <Text strong>{validationResult.total_keywords()}</Text> 个关
                              键词
                              {validationResult.warnings.length > 0 && (
                                <span>，{validationResult.warnings.length} 个警告</span>
                              )}
                            </span>
                          }
                        />
                      ) : (
                        <Alert
                          type="error"
                          showIcon
                          message={`发现 ${validationResult.errors.length} 个错误`}
                          description={
                            <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                              {validationResult.errors.map((err, idx) => (
                                <li key={idx}>{err}</li>
                              ))}
                            </ul>
                          }
                        />
                      )}

                      {validationResult.warnings.length > 0 && (
                        <Alert
                          style={{ marginTop: 8 }}
                          type="warning"
                          showIcon
                          message={`${validationResult.warnings.length} 个警告`}
                          description={
                            <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                              {validationResult.warnings.map((warn, idx) => (
                                <li key={idx}>{warn}</li>
                              ))}
                            </ul>
                          }
                        />
                      )}
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: 'groups',
              label: `分组列表 (${parsedData?.group_count || 0})`,
              children: (
                <div className="groups-tab">
                  {!parsedData ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <Spin tip="加载中..." />
                    </div>
                  ) : (
                    <List
                      dataSource={parsedData.groups}
                      renderItem={(group) => (
                        <List.Item>
                          <Card size="small" hoverable>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <div>
                                <Text strong>
                                  <Badge
                                    count={group.id}
                                    style={{ marginRight: 8 }}
                                    numberStyle={{ backgroundColor: '#1890ff' }}
                                  />
                                  {group.display_name || group.group_key}
                                </Text>
                                
                                <div style={{ marginTop: 4 }}>
                                  <Space size={[4, 4]} wrap>
                                    {group.normal_words.map((word, idx) => (
                                      <Tooltip key={idx} title={`类型: ${word.is_regex ? '正则' : '普通'}`}>
                                        <Tag
                                          color={word.is_regex ? 'blue' : 'default'}
                                          style={{ fontFamily: 'monospace', fontSize: 12 }}
                                        >
                                          {word.display_name || word.word}
                                          {word.is_regex && ' 🔄'}
                                        </Tag>
                                      </Tooltip>
                                    ))}
                                    {group.required_words.map((word, idx) => (
                                      <Tooltip key={idx} title="必须词">
                                        <Tag
                                          color="green"
                                          style={{ fontFamily: 'monospace', fontSize: 12 }}
                                        >
                                          +{word.display_name || word.word}
                                        </Tag>
                                      </Tooltip>
                                    ))}
                                  </Space>
                                </div>
                              </div>

                              <div style={{ textAlign: 'right' }}>
                                <Statistic
                                  title="关键词数"
                                  value={group.total_words}
                                  valueStyle={{ fontSize: 14 }}
                                />
                                {group.max_count > 0 && (
                                  <Tag color="orange" style={{ marginLeft: 8 }}>
                                    最多 {group.max_count} 条
                                  </Tag>
                                )}
                              </div>
                            </div>
                          </Card>
                        </List.Item>
                      )}
                    />
                  )}
                </div>
              ),
            },
            {
              key: 'test',
              label: '实时测试',
              children: (
                <div className="test-tab">
                  <Card size="small" title="测试标题匹配效果" style={{ marginBottom: 16 }}>
                    <Space.Compact style={{ width: '100%' }}>
                      <Input
                        placeholder="输入要测试的新闻标题..."
                        value={testTitle}
                        onChange={(e) => setTestTitle(e.target.value)}
                        onPressEnter={handleTestMatch}
                        size="large"
                      />
                      <Button
                        type="primary"
                        icon={<ExperimentOutlined />}
                        loading={testing}
                        onClick={handleTestMatch}
                        size="large"
                      >
                        测试
                      </Button>
                    </Space.Compact>
                  </Card>

                  {testResult && (
                    <Card
                      title="匹配结果"
                      size="small"
                      style={{
                        borderColor: testResult.will_show ? '#52c41a' : '#ff4d4f',
                      }}
                    >
                      <Row gutter={[16, 16]}>
                        <Col span={12}>
                          <Statistic
                            title="是否匹配"
                            value={testResult.is_match ? '是' : '否'}
                            valueStyle={{
                              color: testResult.is_match ? '#3f8600' : '#cf1322',
                            }}
                          />
                        </Col>
                        <Col span={12}>
                          <Statistic
                            title="最终显示"
                            value={testResult.will_show ? '显示' : '隐藏'}
                            valueStyle={{
                              color: testResult.will_show ? '#3f8600' : '#cf1322',
                            }}
                          />
                        </Col>
                      </Row>

                      <Divider />

                      {testResult.matched_groups.length > 0 && (
                        <div>
                          <Text strong>匹配的分组：</Text>
                          <div style={{ marginTop: 8 }}>
                            {testResult.matched_groups.map((g) => (
                              <Tag
                                key={g.id}
                                color="blue"
                                style={{ marginBottom: 4 }}
                              >
                                {g.name}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )}

                      {testResult.blocked_by_global_filter && (
                        <Alert
                          style={{ marginTop: 8 }}
                          type="error"
                          message="被全局过滤规则拦截"
                        />
                      )}

                      {testResult.blocked_by_group_filter && (
                        <Alert
                          style={{ marginTop: 8 }}
                          type="warning"
                          message="被分组过滤词拦截"
                        />
                      )}

                      <div style={{ marginTop: 12 }}>
                        <Text type="secondary">原标题：</Text>
                        <Paragraph
                          copyable
                          style={{
                            background: '#f5f5f5',
                            padding: 8,
                            borderRadius: 4,
                            marginTop: 4,
                          }}
                        >
                          {testResult.title}
                        </Paragraph>
                      </div>
                    </Card>
                  )}

                  {/* 快速测试用例 */}
                  <Divider>快速测试</Divider>
                  <Space wrap>
                    {[
                      '华为发布新款手机',
                      '特斯拉股价大涨',
                      '震惊！某明星离婚',
                      'AI技术突破性进展',
                      '苹果公司发布新产品',
                    ].map((title) => (
                      <Button
                        key={title}
                        size="small"
                        onClick={() => {
                          setTestTitle(title);
                          setTimeout(() => handleTestMatch(), 100);
                        }}
                      >
                        {title.substring(0, 10)}...
                      </Button>
                    ))}
                  </Space>
                </div>
              ),
            },
            {
              key: 'help',
              label: '语法帮助',
              children: (
                <div className="help-tab">
                  <Card title="关键词配置语法参考" size="small">
                    <Tabs
                      defaultActiveKey="basic"
                      items={[
                        {
                          key: 'basic',
                          label: '基础语法',
                          children: (
                            <div>
                              <Paragraph>
                                <Text code>关键词</Text> - 普通关键词，标题包含即匹
                                配
                              </Paragraph>
                              <Paragraph>
                                <Text code>/正则/</Text> - 正则表达式匹配（自动忽略大
                                小写）
                              </Paragraph>
                              <Paragraph>
                                <Text code>关键词 =&gt; 别名</Text> - 给关键词指定显示别
                                名
                              </Paragraph>
                              <Paragraph>
                                <Text code>[组别名]</Text> - 词组第一行，给整组指定
                                别名
                              </Paragraph>
                            </div>
                          ),
                        },
                        {
                          key: 'advanced',
                          label: '进阶语法',
                          children: (
                            <div>
                              <Paragraph>
                                <Text code>+关键词</Text> - 必须词，所有必须词都要匹配才
                                算匹配
                              </Paragraph>
                              <Paragraph>
                                <Text code>!关键词</Text> - 过滤词，匹配则排除该条新
                                闻
                              </Paragraph>
                              <Paragraph>
                                <Text code>@数字</Text> - 限制该词组最多显示多少条
                              </Paragraph>
                            </div>
                          ),
                        },
                        {
                          key: 'sections',
                          label: '区域说明',
                          children: (
                            <div>
                              <Paragraph>
                                <Text strong>[GLOBAL_FILTER]</Text> - 全局过滤区：排除不
                                想看的内容
                              </Paragraph>
                              <Paragraph>
                                <Text strong>[WORD_GROUPS]</Text> - 词组定义区：设置想关注
                                的关键词
                              </Paragraph>
                            </div>
                          ),
                        },
                        {
                          key: 'examples',
                          label: '示例',
                          children: (
                            <div>
                              <pre
                                style={{
                                  background: '#f5f5f5',
                                  padding: 12,
                                  borderRadius: 4,
                                  overflow: 'auto',
                                }}
                              >{`# 示例1：简单关键词组
[科技]
人工智能
机器学习

# 示例2：使用正则和别名
/华为|鸿蒙|海思/ => 华为

# 示例3：必须词+过滤词
[苹果新闻]
苹果
!水果
!果园

# 示例4：限制条数
[热门]
热点
@10`}</pre>
                              </div>
                          ),
                        },
                      ]}
                    />

                    <Divider />

                    <Alert
                      type="info"
                      showIcon
                      icon={<InfoCircleOutlined />}
                      message="可视化编辑器"
                      description={
                        <span>
                          可访问{' '}
                          <a
                            href="https://sansan0.github.io/TrendRadar/"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            TrendRadar 在线配置编辑器
                          </a>{' '}
                          进行可视化配置
                        </span>
                      }
                    />
                  </Card>
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
