import React, { useState, useCallback, useMemo } from 'react';
import {
  Input,
  Button,
  Tooltip,
  Typography,
  Space,
  Tag,
  Select,
  Card,
} from 'antd';
import {
  Variable,
  Eye,
  Copy,
  FileText,
  Braces,
  Calendar,
  Hash,
  Globe,
  Type,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const { TextArea } = Input;
const { Text } = Typography;

/**
 * PromptEditor - 提示词编辑器组件
 *
 * 功能特性：
 * - 多行文本输入（支持语法高亮提示）
 * - 变量插入按钮（{{date}}, {{keywords}}, {{top_n}}, {{platforms}}）
 * - 实时预览区域（渲染后的效果）
 * - 字数统计
 * - 常用提示词模板快速填充
 * - 支持 Markdown 格式预览
 *
 * @param {Object} props
 * @param {string} value - 编辑器内容（受控）
 * @param {Function} onChange - 内容变化回调
 * @param {number} maxLength - 最大字符限制
 * @param {boolean} showPreview - 是否显示预览区域
 * @param {Object} templateVars - 模板变量值（用于预览）
 */
const PromptEditor = ({
  value = '',
  onChange,
  maxLength = 10000,
  showPreview = true,
  templateVars = {},
  placeholder = '输入AI分析提示词，支持 {{变量}} 语法...',
}) => {
  const [previewMode, setPreviewMode] = useState('raw'); // 'raw' | 'rendered'

  // 可用的变量列表
  const availableVariables = useMemo(() => [
    { name: 'date', label: '日期', icon: <Calendar size={14} />, desc: '分析日期 (YYYY-MM-DD)' },
    { name: 'today', label: '今天', icon: <Calendar size={14} />, desc: '今天的日期' },
    { name: 'top_n', label: '数量', icon: <Hash size={14} />, desc: '热点数量上限' },
    { name: 'platforms', label: '平台', icon: <Globe size={14} />, desc: '平台名称列表' },
    { name: 'hotspots_data', label: '热点数据', icon: <FileText size={14} />, desc: '完整的热点数据文本' },
    { name: 'all_hotspots', label: '全部热点', icon: <FileText size={14} />, desc: '所有热点数据' },
    { name: 'hotspot_count', label: '热点总数', icon: <Hash size={14} />, desc: '热点条目总数' },
    { name: 'week_start', label: '周起始日', icon: <Calendar size={14} />, desc: '本周一日期' },
    { name: 'week_end', label: '周结束日', icon: <Calendar size={14} />, desc: '本周日日期' },
    { name: 'now', label: '当前时间', icon: <Type size={14} />, desc: '当前时间戳' },
  ], []);

  // 常用模板片段
  const quickTemplates = useMemo(() => [
    {
      name: '基础总结模板',
      content: `请对以下热榜数据进行全面分析。

## 数据范围
- 日期：{{date}}
- 平台：{{platforms}}
- 热点数量：{{top_n}} 条

## 分析要求
1. **热点概览**：按热度排序列出前20条热点
2. **趋势分析**：识别3-5个主要趋势方向
3. **关键事件**：重点解读影响力最大的3条热点

## 原始数据
{{hotspots_data}}`,
    },
    {
      name: '深度分析模板',
      content: `请针对以下数据进行深度专业分析。

## 分析目标
识别关键信息、趋势变化和潜在影响

## 分析维度
1. **核心事件**：重大事件及其影响评估
2. **趋势判断**：短期和长期趋势预测
3. **数据支撑**：基于数据的客观分析

## 输出要求
- 使用专业术语但保持可读性
- 提供数据支撑和来源引用
- 给出明确的结论和建议

## 原始数据
{{all_hotspots}}`,
    },
    {
      name: '简洁摘要模板',
      content: `生成一份简洁的热点摘要报告。

**统计信息**：
- 总条目数：{{hotspot_count}}
- 覆盖平台：{{platforms}}
- 日期：{{date}}

**Top 10 要点**：

{{hotspots_data}}

**关键洞察**：
请提炼3-5个最重要的发现。`,
    },
  ], []);

  /**
   * 插入变量到光标位置
   */
  const insertVariable = useCallback((varName) => {
    const variable = `{{${varName}}}`;
    const textarea = document.querySelector('.prompt-editor-textarea');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = value.substring(0, start);
    const after = value.substring(end);
    const newValue = before + variable + after;

    onChange?.(newValue);

    // 恢复光标位置（在下一个事件循环中）
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + variable.length, start + variable.length);
    }, 0);
  }, [value, onChange]);

  /**
   * 应用快速模板
   */
  const applyTemplate = useCallback((template) => {
    onChange?.(template.content);
  }, [onChange]);

  /**
   * 渲染模板变量（用于预览）
   */
  const renderTemplate = useCallback((text) => {
    if (!text) return '';

    let rendered = text;
    // 替换变量为实际值或占位符
    Object.keys(templateVars).forEach((key) => {
      const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
      const value = templateVars[key];
      if (typeof value === 'object') {
        rendered = rendered.replace(regex, JSON.stringify(value, null, 2));
      } else {
        rendered = rendered.replace(regex, String(value));
      }
    });

    // 对于未提供值的变量，保留原样或显示占位符
    rendered = rendered.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
      return `<span style="color:#1677ff;background:#e6f4ff;padding:0 4px;border-radius:2px;font-size:12px;">${match}</span>`;
    });

    return rendered;
  }, [templateVars]);

  /**
   * 复制内容到剪贴板
   */
  const copyToClipboard = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      message.success('已复制到剪贴板');
    } catch (err) {
      console.error('复制失败:', err);
    }
  }, [value]);

  // 字符统计
  const charCount = value.length;
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const lineCount = value.split('\n').length;

  // 预览内容
  const previewContent = useMemo(() => {
    if (previewMode === 'rendered') {
      return renderTemplate(value);
    }
    return value;
  }, [value, previewMode, renderTemplate]);

  return (
    <div className="prompt-editor">
      {/* 工具栏 */}
      <div className="prompt-editor-toolbar">
        <Space wrap size="small">
          {/* 变量插入按钮组 */}
          <Tooltip title="插入变量">
            <Button
              type="text"
              size="small"
              icon={<Variable size={16} />}
            >
              变量
            </Button>
          </Tooltip>

          {availableVariables.map((variable) => (
            <Tooltip key={variable.name} title={`${variable.label}: ${variable.desc}`}>
              <Tag
                className="variable-tag"
                onClick={() => insertVariable(variable.name)}
                style={{ cursor: 'pointer', margin: 2 }}
              >
                {variable.icon}
                {` {{${variable.name}}} `}
              </Tag>
            </Tooltip>
          ))}
        </Space>

        <div className="toolbar-right">
          <Space size="small">
            {/* 快速模板选择 */}
            <Select
              size="small"
              style={{ width: 140 }}
              placeholder="快速模板"
              allowClear
              onChange={(templateName) => {
                const template = quickTemplates.find(t => t.name === templateName);
                if (template) applyTemplate(template);
              }}
              options={quickTemplates.map(t => ({
                value: t.name,
                label: t.name,
              }))}
            />

            {/* 预览模式切换 */}
            {showPreview && (
              <Button.Group size="small">
                <Button
                  type={previewMode === 'raw' ? 'primary' : 'default'}
                  onClick={() => setPreviewMode('raw')}
                >
                  原文
                </Button>
                <Button
                  type={previewMode === 'rendered' ? 'primary' : 'default'}
                  onClick={() => setPreviewMode('rendered')}
                >
                  预览
                </Button>
              </Button.Group>
            )}

            {/* 复制按钮 */}
            <Tooltip title="复制内容">
              <Button
                type="text"
                size="small"
                icon={<Copy size={16} />}
                onClick={copyToClipboard}
              />
            </Tooltip>
          </Space>
        </div>
      </div>

      {/* 编辑器主体 */}
      <div className="prompt-editor-body">
        {/* 左侧：编辑区 */}
        <div className={`editor-area ${showPreview ? 'with-preview' : 'full-width'}`}>
          <TextArea
            className="prompt-editor-textarea"
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            placeholder={placeholder}
            autoSize={{ minRows: 8, maxRows: 20 }}
            maxLength={maxLength}
            showCount={false}
            style={{
              fontFamily: '"Fira Code", "Consolas", monospace',
              fontSize: 13,
              lineHeight: 1.6,
              resize: 'vertical',
            }}
          />

          {/* 底部状态栏 */}
          <div className="editor-status-bar">
            <Space size="middle">
              <Text type="secondary" style={{ fontSize: 12 }}>
                字符: {charCount.toLocaleString()} / {maxLength.toLocaleString()}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                单词: {wordCount}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                行数: {lineCount}
              </Text>
            </Space>

            {charCount > maxLength * 0.9 && (
              <Text type="warning" style={{ fontSize: 12 }}>
                接近字数限制
              </Text>
            )}
          </div>
        </div>

        {/* 右侧：预览区 */}
        {showPreview && (
          <div className="preview-area">
            <div className="preview-header">
              <Eye size={14} />
              <span>实时预览</span>
            </div>
            <div className="preview-content">
              {previewContent ? (
                previewMode === 'rendered' ? (
                  <div className="markdown-preview">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {previewContent}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <pre className="raw-preview">{previewContent}</pre>
                )
              ) : (
                <div className="preview-empty">
                  <Braces size={32} />
                  <p>开始输入以查看预览</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .prompt-editor {
          border: 1px solid #d9d9d9;
          border-radius: 6px;
          overflow: hidden;
          background: #fff;
        }

        .prompt-editor-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 12px;
          background: #fafafa;
          border-bottom: 1px solid #f0f0f0;
          flex-wrap: wrap;
          gap: 8px;
        }

        .toolbar-right {
          display: flex;
          align-items: center;
        }

        .variable-tag {
          transition: all 0.2s;
        }

        .variable-tag:hover {
          background: #1677ff;
          color: #fff;
          transform: scale(1.05);
        }

        .prompt-editor-body {
          display: flex;
          min-height: 300px;
        }

        .editor-area {
          flex: 1;
          display: flex;
          flex-direction: column;
          border-right: 1px solid #f0f0f0;
        }

        .editor-area.full-width {
          border-right: none;
        }

        .editor-area.with-preview {
          flex: 1;
        }

        .editor-status-bar {
          padding: 6px 12px;
          border-top: 1px solid #f0f0f0;
          background: #fafafa;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .preview-area {
          width: 45%;
          max-width: 500px;
          display: flex;
          flex-direction: column;
          background: #fafafa;
        }

        .preview-header {
          padding: 8px 12px;
          font-size: 13px;
          color: #666;
          display: flex;
          align-items: center;
          gap: 6px;
          border-bottom: 1px solid #f0f0f0;
          background: #f5f5f5;
        }

        .preview-content {
          flex: 1;
          padding: 16px;
          overflow-y: auto;
          max-height: 400px;
        }

        .markdown-preview {
          font-size: 14px;
          line-height: 1.7;
          color: #333;
        }

        .markdown-preview h1,
        .markdown-preview h2,
        .markdown-preview h3 {
          margin-top: 16px;
          margin-bottom: 8px;
        }

        .markdown-preview pre {
          background: #f6f8fa;
          padding: 12px;
          border-radius: 4px;
          overflow-x: auto;
        }

        .raw-preview {
          white-space: pre-wrap;
          word-break: break-word;
          font-family: 'Consolas', monospace;
          font-size: 13px;
          line-height: 1.6;
          margin: 0;
        }

        .preview-empty {
          text-align: center;
          color: #999;
          padding: 40px 20px;
        }

        .preview-empty p {
          margin-top: 12px;
          font-size: 14px;
        }

        /* 响应式适配 */
        @media (max-width: 768px) {
          .prompt-editor-body {
            flex-direction: column;
          }

          .editor-area {
            border-right: none !important;
            border-bottom: 1px solid #f0f0f0;
          }

          .preview-area {
            width: 100%;
            max-width: none;
          }

          .prompt-editor-toolbar {
            flex-direction: column;
            align-items: flex-start;
          }

          .toolbar-right {
            width: 100%;
            justify-content: flex-end;
          }
        }
      `}</style>
    </div>
  );
};

export default PromptEditor;
