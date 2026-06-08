import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Input,
  Button,
  Spin,
  message,
  Tooltip,
  Empty,
  Space,
  Dropdown,
  Modal,
} from 'antd';
import {
  Send,
  Square,
  Trash2,
  History,
  Bot,
  User,
  Copy,
  Check,
  ChevronDown,
  MoreVertical,
  RefreshCw,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import QuickActions from '../components/assistant/QuickActions';
import api from '../services/api';
import './Assistant.css';

const { TextArea } = Input;

/**
 * 智能助手页面 - 完整的聊天界面UI
 *
 * 功能特性:
 * - 多轮对话支持（上下文管理）
 * - 消息列表展示（用户/AI消息区分）
 * - Markdown 渲染AI回复
 * - 快捷查询预设
 * - 流式响应支持
 * - 对话历史持久化
 */
const Assistant = () => {
  // ========== 状态定义 ==========
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const [copiedId, setCopiedId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ========== 初始化 ==========
  useEffect(() => {
    // 生成或恢复会话ID
    const savedSessionId = localStorage.getItem('assistant_session_id');
    if (savedSessionId) {
      setSessionId(savedSessionId);
      loadHistory(savedSessionId);
    }

    // 聚焦输入框
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  // ========== 核心方法 ==========

  /**
   * 加载历史记录
   */
  const loadHistory = useCallback(async (sid) => {
    try {
      const response = await api.get('/assistant/history', {
        params: { session_id: sid, limit: 50 },
      });

      if (response.success && response.data) {
        setMessages(response.data.items || []);
      }
    } catch (error) {
      console.error('加载历史记录失败:', error);
    }
  }, []);

  /**
   * 发送消息
   */
  const handleSend = async () => {
    const text = inputValue.trim();
    if (!text || loading) return;

    // 清空输入框
    setInputValue('');

    // 添加用户消息到列表
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // 隐藏快捷操作面板
    setShowQuickActions(false);

    // 设置加载状态
    setLoading(true);
    setIsStreaming(true);
    setStreamingContent('');

    try {
      // 使用流式响应
      await sendStreamMessage(text);
    } catch (error) {
      console.error('发送消息失败:', error);
      message.error('发送失败，请重试');

      // 添加错误消息
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: '抱歉，处理您的请求时出现了错误。请稍后重试。',
          timestamp: new Date().toISOString(),
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
      setIsStreaming(false);
      setStreamingContent('');

      // 重新聚焦输入框
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
    }
  };

  /**
   * 发送流式消息
   */
  const sendStreamMessage = async (text) => {
    try {
      const response = await fetch('/api/assistant/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.event === 'message' && data.content) {
                fullContent += data.delta || data.content;
                setStreamingContent(fullContent);
              }

              if (data.event === 'start' && data.session_id) {
                setSessionId(data.session_id);
                localStorage.setItem('assistant_session_id', data.session_id);
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }

      // 流式传输完成，添加完整消息
      if (fullContent) {
        const assistantMessage = {
          id: Date.now(),
          role: 'assistant',
          content: fullContent,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error('流式请求失败:', error);
      throw error;
    }
  };

  /**
   * 处理快捷操作选择
   */
  const handleQuickActionSelect = (text) => {
    setInputValue(text);
    handleSend();
  };

  /**
   * 清空对话
   */
  const handleClearChat = () => {
    Modal.confirm({
      title: '确认清空',
      content: '确定要清空当前对话历史吗？此操作不可撤销。',
      okText: '确认清空',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.post('/assistant/history/clear', {
            session_id: sessionId,
          });
          setMessages([]);
          setShowQuickActions(true);
          message.success('对话已清空');
        } catch (error) {
          console.error('清空失败:', error);
          message.error('清空失败，请重试');
        }
      },
    });
  };

  /**
   * 复制消息内容
   */
  const handleCopy = async (content, id) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      message.success('已复制到剪贴板');

      // 2秒后重置复制状态
      setTimeout(() => setCopiedId(null), 2000);
    } catch (error) {
      console.error('复制失败:', error);
      message.error('复制失败');
    }
  };

  /**
   * 重新生成回复
   */
  const handleRegenerate = async (index) => {
    if (index <= 0) return;

    // 找到对应的用户消息
    const userMessage = messages[index - 1];
    if (!userMessage || userMessage.role !== 'user') return;

    // 删除从该用户消息开始的所有后续消息
    setMessages((prev) => prev.slice(0, index - 1));

    // 重新发送用户消息
    setInputValue(userMessage.content);
    setTimeout(() => handleSend(), 100);
  };

  /**
   * 停止生成
   */
  const handleStopGeneration = () => {
    // 注意：实际实现需要中止 fetch 请求
    // 这里简化处理
    setLoading(false);
    setIsStreaming(false);

    if (streamingContent) {
      const partialMessage = {
        id: Date.now(),
        role: 'assistant',
        content: streamingContent + '\n\n*(回复被中断)*',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, partialMessage]);
    }

    setStreamingContent('');
    message.info('已停止生成');
  };

  /**
   * 键盘事件处理
   */
  const handleKeyDown = (e) => {
    // Enter 发送，Shift+Enter 换行
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /**
   * 滚动到底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // ========== 渲染方法 ==========

  /**
   * 渲染单条消息
   */
  const renderMessage = (msg, index) => {
    const isUser = msg.role === 'user';
    const isAssistant = msg.role === 'assistant';
    const isError = msg.isError;

    return (
      <div
        key={msg.id}
        className={`message-item ${isUser ? 'message-user' : ''} ${isAssistant ? 'message-assistant' : ''} ${isError ? 'message-error' : ''}`}
      >
        <div className="message-avatar">
          {isUser ? <User size={18} /> : <Bot size={18} />}
        </div>

        <div className="message-body">
          <div className="message-header">
            <span className="message-role">
              {isUser ? '你' : 'AI 助手'}
            </span>
            <span className="message-time">
              {formatTime(msg.timestamp)}
            </span>
          </div>

          <div className={`message-content ${isUser ? 'content-user' : 'content-assistant'}`}>
            {isAssistant ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // 自定义渲染组件 - code block
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    const language = match ? match[1] : '';

                    if (!inline && language) {
                      return (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }

                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                  a({ href, children, ...props }) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        {...props}
                      >
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {msg.content}
              </ReactMarkdown>
            ) : (
              <p>{msg.content}</p>
            )}
          </div>

          {/* 操作按钮 */}
          {isAssistant && !isError && (
            <div className="message-actions">
              <Tooltip title="复制">
                <button
                  className="action-btn"
                  onClick={() => handleCopy(msg.content, msg.id)}
                >
                  {copiedId === msg.id ? (
                    <Check size={14} />
                  ) : (
                    <Copy size={14} />
                  )}
                </button>
              </Tooltip>
              <Tooltip title="重新生成">
                <button
                  className="action-btn"
                  onClick={() => handleRegenerate(index)}
                >
                  <RefreshCw size={14} />
                </button>
              </Tooltip>
            </div>
          )}
        </div>
      </div>
    );
  };

  /**
   * 格式化时间显示
   */
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // 小于1分钟
    if (diff < 60000) {
      return '刚刚';
    }

    // 小于1小时
    if (diff < 3600000) {
      return `${Math.floor(diff / 60000)} 分钟前`;
    }

    // 今天
    if (date.toDateString() === now.toDateString()) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      });
    }

    // 昨天
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
      return `昨天 ${date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      })}`;
    }

    // 更早
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // ========== 主渲染 ==========
  return (
    <div className="assistant-page">
      {/* 页面头部 */}
      <div className="assistant-header">
        <div className="header-left">
          <Bot size={24} className="header-icon" />
          <h1 className="header-title">智能助手</h1>
          <span className="header-badge">Beta</span>
        </div>

        <div className="header-right">
          <Tooltip title="清空对话">
            <Button
              type="text"
              icon={<Trash2 size={18} />}
              onClick={handleClearChat}
              disabled={messages.length === 0}
            />
          </Tooltip>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="assistant-main">
        {/* 消息列表 */}
        <div className="messages-container">
          {messages.length === 0 && !isStreaming ? (
            /* 空状态：显示欢迎信息和快捷操作 */
            <div className="welcome-section">
              <div className="welcome-icon">
                <Bot size={48} />
              </div>
              <h2 className="welcome-title">你好，我是热点发现平台智能助手</h2>
              <p className="welcome-description">
                我可以帮助你搜索热榜、查看文章、分析趋势和统计数据。
                选择下方的快捷查询或直接输入你的问题。
              </p>

              <QuickActions onSelect={handleQuickActionSelect} />
            </div>
          ) : (
            <>
              {/* 快捷操作（有消息时折叠显示） */}
              {showQuickActions && messages.length > 0 && (
                <div className="quick-actions-inline">
                  <QuickActions onSelect={handleQuickActionSelect} />
                </div>
              )}

              {/* 消息列表 */}
              <div className="messages-list">
                {messages.map((msg, index) => renderMessage(msg, index))}

                {/* 流式输出中的消息 */}
                {isStreaming && streamingContent && (
                  <div className="message-item message-assistant streaming">
                    <div className="message-avatar">
                      <Bot size={18} />
                    </div>
                    <div className="message-body">
                      <div className="message-content content-assistant">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {streamingContent}
                        </ReactMarkdown>
                        <span className="cursor-blink" />
                      </div>
                    </div>
                  </div>
                )}

                {/* 加载指示器 */}
                {loading && !streamingContent && (
                  <div className="message-item message-assistant loading">
                    <div className="message-avatar">
                      <Bot size={18} />
                    </div>
                    <div className="message-body">
                      <div className="loading-indicator">
                        <Spin size="small" />
                        <span>思考中...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </>
          )}
        </div>

        {/* 输入区域 */}
        <div className="input-area">
          {loading && (
            <div className="stop-button-wrapper">
              <Button
                type="primary"
                danger
                icon={<Square size={16} />}
                onClick={handleStopGeneration}
              >
                停止生成
              </Button>
            </div>
          )}

          <div className="input-container">
            <TextArea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                messages.length === 0
                  ? '输入你的问题，例如："今天最热的10条新闻"'
                  : '继续对话...'
              }
              autoSize={{ minRows: 1, maxRows: 6 }}
              disabled={loading}
              className="chat-input"
            />

            <Button
              type="primary"
              icon={<Send size={18} />}
              onClick={handleSend}
              loading={loading && !isStreaming}
              disabled={!inputValue.trim() || loading}
              className="send-button"
            >
              发送
            </Button>
          </div>

          <div className="input-footer">
            <span className="footer-hint">
              按 Enter 发送，Shift+Enter 换行
            </span>
            {sessionId && (
              <span className="session-info">
                会话 ID: {sessionId.slice(0, 8)}...
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Assistant;
