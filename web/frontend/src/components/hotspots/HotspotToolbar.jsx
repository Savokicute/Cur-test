import { Input, Segmented, Space, Tag, Tooltip, Select } from 'antd';
import { Moon, Search, Sun, Maximize2, Minimize2, Filter, Keyboard } from 'lucide-react';
import { usePreferences } from '../../contexts/PreferencesContext';
import ViewModeSwitcher from '../common/ViewModeSwitcher';
import dayjs from 'dayjs';
import './HotspotToolbar.css';

const { Option } = Select;

export default function HotspotToolbar({
  viewMode,
  onViewModeChange,
  filterMode = 'keyword',
  onFilterModeChange,
  onSearch,
  lastFetchTime,
  nextFetchTime,
  selectedTrend,
  onTrendChange,
  selectedPlatforms,
  onPlatformsChange,
  availablePlatforms = [],
}) {
  const { 
    isDark, 
    toggleTheme, 
    wideLayout, 
    toggleWideLayout,
    keyboardShortcutsEnabled,
  } = usePreferences();

  const handlePlatformChange = (checkedValues) => {
    onPlatformsChange(checkedValues);
  };

  const handleViewModeToggle = (newMode) => {
    onViewModeChange(newMode);
  };

  return (
    <div className="hotspot-toolbar" role="toolbar" aria-label="热榜筛选工具栏">
      <Space wrap size="middle" className="hotspot-toolbar-left">
        {/* 筛选模式切换 */}
        <Segmented
          value={filterMode}
          onChange={onFilterModeChange}
          options={[
            { label: '关键词', value: 'keyword' },
            { label: 'AI 筛选', value: 'ai' },
          ]}
        />

        {/* 视图模式切换 - 使用新组件 */}
        <ViewModeSwitcher
          value={viewMode}
          onChange={handleViewModeToggle}
          size={16}
        />

        {/* 增强搜索框 */}
        <Input.Search
          placeholder={`搜索热点${keyboardShortcutsEnabled ? ' (按 / 聚焦)' : ''}`}
          allowClear
          onSearch={(value) => {
            onSearch?.(value);
          }}
          onChange={(e) => onSearch?.(e.target.value)}
          style={{ width: 280 }}
          prefix={<Search size={14} aria-hidden />}
          aria-label="搜索热点"
          className="enhanced-search-input"
        />
        
        {/* 平台筛选 */}
        <Select
          placeholder="选择平台（多选）"
          allowClear
          style={{ width: 200 }}
          value={selectedPlatforms}
          onChange={handlePlatformChange}
          mode="multiple"
          prefix={<Filter size={14} />}
          maxTagCount="responsive"
        >
          {availablePlatforms.map((platform) => (
            <Option key={platform} value={platform}>{platform}</Option>
          ))}
        </Select>
        
        {/* 趋势筛选 */}
        <Select
          placeholder="选择趋势"
          allowClear
          style={{ width: 150 }}
          value={selectedTrend}
          onChange={onTrendChange}
        >
          <Option value="up">上升</Option>
          <Option value="down">下降</Option>
          <Option value="same">持平</Option>
          <Option value="new">新增</Option>
        </Select>
      </Space>

      <Space wrap size="middle" className="hotspot-toolbar-right">
        {/* 时间信息 */}
        {lastFetchTime && (
          <Tooltip title={typeof lastFetchTime === 'object' ? lastFetchTime.absolute : ''}>
            <Tag color="blue">上次采集 {typeof lastFetchTime === 'object' ? lastFetchTime.relative : lastFetchTime}</Tag>
          </Tooltip>
        )}
        {nextFetchTime && (
          <Tooltip title={typeof nextFetchTime === 'object' ? nextFetchTime.absolute : ''}>
            <Tag>下次采集 {typeof nextFetchTime === 'object' ? nextFetchTime.relative : nextFetchTime}</Tag>
          </Tooltip>
        )}

        {/* 布局切换 */}
        <Tooltip title={`${wideLayout ? '窄屏阅读' : '宽屏模式'} (W)`}>
          <button type="button" className="toolbar-icon-btn" onClick={toggleWideLayout} aria-label="切换宽屏">
            {wideLayout ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </Tooltip>

        {/* 主题切换 */}
        <Tooltip title={`${isDark ? '浅色模式' : '深色模式'} (D)`}>
          <button type="button" className="toolbar-icon-btn" onClick={toggleTheme} aria-label="切换主题">
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </Tooltip>

        {/* 快捷键提示 */}
        {keyboardShortcutsEnabled && (
          <Tooltip title="键盘快捷键已启用">
            <span className="shortcut-hint-indicator">
              <Keyboard size={14} />
            </span>
          </Tooltip>
        )}
      </Space>
    </div>
  );
}
