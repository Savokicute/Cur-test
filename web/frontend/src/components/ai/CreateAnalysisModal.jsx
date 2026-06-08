import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Form,
  Input,
  InputNumber,
  Slider,
  Select,
  Switch,
  Button,
  Space,
  Divider,
  Typography,
  Alert,
  Row,
  Col,
  Checkbox,
  Tag,
  message,
} from 'antd';
import {
  Plus,
  Settings,
  Zap,
  FileText,
  CalendarRange,
  Filter,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import dayjs from 'dayjs';
import PromptEditor from './PromptEditor';
import { createAnalysisConfig } from '../../services/aiAnalysis';

const { TextArea } = Input;
const { Text, Title, Paragraph } = Typography;
const { Option } = Select;

/**
 * CreateAnalysisModal - 创建分析配置弹窗
 *
 * 功能特性：
 * - 配置名称输入
 * - 选择/粘贴提示词（集成 PromptEditor）
 * - 模型参数设置（temperature: 0-1滑块, max_tokens: 数字输入）
 * - 数据范围选择（日期范围、平台多选、关键词过滤）
 * - 高级选项（折叠面板）：
 *   * 排除已分析内容
 *   * 最小相关性分数
 *   * 输出格式（Markdown/JSON/纯文本）
 */
const CreateAnalysisModal = ({
  visible,
  onCancel,
  onSuccess,
  initialData = null, // 用于编辑模式
  templates = [],      // 可选的模板列表
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState(['baidu', 'weibo', 'zhihu']);
  const [dateRange, setDateRange] = useState(null);

  // 初始化表单数据
  useEffect(() => {
    if (visible) {
      if (initialData) {
        // 编辑模式：填充现有数据
        form.setFieldsValue({
          name: initialData.name,
          description: initialData.description,
          model_name: initialData.model_name || 'gpt-4',
          temperature: initialData.temperature ?? 0.7,
          max_tokens: initialData.max_tokens ?? 4096,
          trigger_type: initialData.trigger_type || 'manual',
          is_active: initialData.is_active !== false,
        });
        setPromptTemplate(initialData.prompt_template || '');
      } else {
        // 新建模式：重置表单
        form.resetFields();
        setPromptTemplate('');
        setSelectedPlatforms(['baidu', 'weibo', 'zhihu']);
        setDateRange(null);
        setShowAdvanced(false);
      }
    }
  }, [visible, initialData, form]);

  /**
   * 处理模板选择
   */
  const handleTemplateSelect = useCallback((templateId) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setPromptTemplate(template.prompt_template);
      // 可选：自动填充部分字段
      form.setFieldsValue({
        name: form.getFieldValue('name') || `${template.name} - ${dayjs().format('MM/DD HH:mm')}`,
        description: template.description,
      });
      message.success(`已应用模板: ${template.name}`);
    }
  }, [templates, form]);

  /**
   * 提交表单
   */
  const handleSubmit = async () => {
    try {
      // 验证必填字段
      const values = await form.validateFields();

      // 验证提示词不为空
      if (!promptTemplate.trim()) {
        message.error('请输入提示词模板');
        return;
      }

      setLoading(true);

      // 构建请求数据
      const requestData = {
        name: values.name,
        description: values.description,
        prompt_template: promptTemplate,
        model_name: values.model_name,
        temperature: values.temperature,
        max_tokens: values.max_tokens,
        trigger_type: values.trigger_type,
        is_active: values.is_active,
        // 高级选项
        ...(showAdvanced && {
          schedule_cron: values.schedule_cron || null,
        }),
      };

      let response;
      if (initialData?.id) {
        // 编辑模式
        const { updateAnalysisConfig } = require('../../services/aiAnalysis');
        response = await updateAnalysisConfig(initialData.id, requestData);
      } else {
        // 新建模式
        response = await createAnalysisConfig(requestData);
      }

      if (response?.success) {
        message.success(initialData ? '配置更新成功' : '配置创建成功');
        onSuccess?.(response.data);
        handleCancel();
      } else {
        message.error(response?.detail || (initialData ? '更新失败' : '创建失败'));
      }
    } catch (error) {
      console.error('提交失败:', error);
      if (error.errorFields) {
        // 表单验证错误，不处理
        return;
      }
      message.error(initialData ? '更新配置失败' : '创建配置失败');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 取消/关闭弹窗
   */
  const handleCancel = () => {
    form.resetFields();
    setPromptTemplate('');
    setShowAdvanced(false);
    onCancel?.();
  };

  // 平台选项
  const platformOptions = [
    { value: 'baidu', label: '百度热搜' },
    { value: 'weibo', label: '微博热搜' },
    { value: 'zhihu', label: '知乎热榜' },
    { value: 'bilibili-hot-search', label: 'B站热搜' },
    { value: 'douyin', label: '抖音热点' },
    { value: 'toutiao', label: '今日头条' },
    { value: 'thepaper', label: '澎湃新闻' },
  ];

  return (
    <Modal
      title={
        <Space>
          <Plus size={20} />
          <span>{initialData ? '编辑分析配置' : '新建AI分析'}</span>
        </Space>
      }
      open={visible}
      onCancel={handleCancel}
      width={720}
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          取消
        </Button>,
        <Button key="advanced" onClick={() => setShowAdvanced(!showAdvanced)}>
          {showAdvanced ? <>收起高级选项 <ChevronUp size={16} /></> : <>高级选项 <ChevronDown size={16} /></>}
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={loading}
          onClick={handleSubmit}
          icon={<Zap size={16} />}
        >
          {initialData ? '保存修改' : '创建并运行'}
        </Button>,
      ]}
      destroyOnClose
    >
      <div className="create-analysis-modal">
        {/* 基本信息 */}
        <Form
          form={form}
          layout="vertical"
          requiredMark="optional"
          initialValues={{
            name: '',
            description: '',
            model_name: 'gpt-4',
            temperature: 0.7,
            max_tokens: 4096,
            trigger_type: 'manual',
            is_active: true,
          }}
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="name"
                label="配置名称"
                rules={[{ required: true, message: '请输入配置名称' }]}
              >
                <Input
                  placeholder="例如：每日科技热点总结"
                  prefix={<FileText size={16} style={{ color: '#999' }} />}
                  maxLength={100}
                  showCount
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="description" label="描述（可选）">
                <TextArea
                  rows={2}
                  placeholder="简要描述这个分析配置的用途..."
                  maxLength={500}
                  showCount
                />
              </Form.Item>
            </Col>
          </Row>

          {/* 提示词编辑器 */}
          <Divider orientation="left" plain>
            <Space>
              <Settings size={16} />
              提示词配置
            </Space>
          </Divider>

          {/* 模板快速选择 */}
          {templates.length > 0 && (
            <div className="template-selector" style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ fontSize: 13, marginBottom: 8, display: 'block' }}>
                快速使用预设模板：
              </Text>
              <Select
                style={{ width: '100%' }}
                placeholder="选择一个模板快速开始"
                allowClear
                onChange={handleTemplateSelect}
              >
                {templates.map((template) => (
                  <Option key={template.id} value={template.id}>
                    <Space>
                      <Tag color="blue">{template.category}</Tag>
                      <span>{template.name}</span>
                    </Space>
                  </Option>
                ))}
              </Select>
            </div>
          )}

          <Form.Item label="提示词模板" required>
            <PromptEditor
              value={promptTemplate}
              onChange={setPromptTemplate}
              maxLength={8000}
              showPreview={true}
              templateVars={{
                date: dayjs().format('YYYY-MM-DD'),
                today: dayjs().format('YYYY-MM-DD'),
                top_n: 20,
                platforms: selectedPlatforms.join(', '),
                hotspot_count: '--',
                now: dayjs().format('YYYY-MM-DD HH:mm:ss'),
              }}
            />
          </Form.Item>

          {/* 模型参数设置 */}
          <Divider orientation="left" plain>
            <Space>
              <Zap size={16} />
              模型参数
            </Space>
          </Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="model_name" label="模型">
                <Select>
                  <Option value="gpt-4">GPT-4</Option>
                  <Option value="gpt-4-turbo">GPT-4 Turbo</Option>
                  <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
                  <Option value="claude-3">Claude 3</Option>
                  <Option value="local-model">本地模型</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="trigger_type" label="触发方式">
                <Select>
                  <Option value="manual">手动触发</Option>
                  <Option value="scheduled">定时执行</Option>
                  <Option value="event">事件驱动</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="temperature"
                label={`温度参数 (${form.getFieldValue('temperature') || 0.7})`}
                tooltip="值越高输出越随机和创造性，值越低越确定性和一致性"
              >
                <Slider
                  min={0}
                  max={1}
                  step={0.1}
                  marks={{
                    0: '精确',
                    0.5: '平衡',
                    1: '创意',
                  }}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="max_tokens"
                label="最大 Token 数"
                tooltip="控制生成内容的最大长度，约等于字符数/4"
              >
                <InputNumber
                  min={100}
                  max={32000}
                  step={256}
                  style={{ width: '100%' }}
                  formatter={(value) => `${value}`}
                  parser={(value) => Number(value)}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="is_active" label="启用状态" valuePropName="checked">
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>

          {/* 数据范围选择 */}
          <Divider orientation="left" plain>
            <Space>
              <CalendarRange size={16} />
              数据范围
            </Space>
          </Divider>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item label="目标平台">
                <Select
                  mode="multiple"
                  placeholder="选择要分析的平台"
                  value={selectedPlatforms}
                  onChange={setSelectedPlatforms}
                  style={{ width: '100%' }}
                >
                  {platformOptions.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {/* 高级选项（可折叠） */}
          {showAdvanced && (
            <>
              <Divider orientation="left" plain>
                <Space>
                  <Filter size={16} />
                  高级选项
                </Space>
              </Divider>

              <Alert
                message="高级功能"
                description="以下选项适用于有经验的用户，一般情况下无需修改"
                type="info"
                showIcon
                closable
                style={{ marginBottom: 16 }}
              />

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="schedule_cron" label="Cron 表达式">
                    <Input
                      placeholder="例如: 0 9 * * * （每天9点）"
                      disabled={form.getFieldValue('trigger_type') !== 'scheduled'}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="排除已分析">
                    <Checkbox>跳过最近3天内已分析过的内容</Checkbox>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="最小相关性">
                    <Slider
                      min={0}
                      max={1}
                      step={0.1}
                      defaultValue={0.5}
                      marks={{
                        0: '低',
                        0.5: '中',
                        1: '高',
                      }}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="输出格式">
                    <Select defaultValue="markdown">
                      <Option value="markdown">Markdown</Option>
                      <Option value="json">JSON</Option>
                      <Option value="text">纯文本</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
            </>
          )}
        </Form>
      </div>

      <style jsx>{`
        .create-analysis-modal {
          padding: 8px 0;
          max-height: 75vh;
          overflow-y: auto;
        }

        .create-analysis-modal :global(.ant-divider) {
          margin: 20px 0 16px;
        }

        .template-selector {
          background: #f6f8fa;
          padding: 12px;
          border-radius: 6px;
          border: 1px dashed #d9d9d9;
        }

        /* 响应式适配 */
        @media (max-width: 576px) {
          .create-analysis-modal {
            max-height: 85vh;
          }
        }
      `}</style>
    </Modal>
  );
};

export default CreateAnalysisModal;
