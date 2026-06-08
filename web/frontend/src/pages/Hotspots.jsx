import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Empty,
  Spin,
  Tabs,
  Typography,
  message,
  DatePicker,
  Statistic,
  Row,
  Col,
  Card,
  Tag,
  Space,
  Pagination,
} from 'antd';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import PageHeader, { StatusBadge } from '../components/common/PageHeader';
import HotspotCard from '../components/hotspots/HotspotCard';
import HotspotToolbar from '../components/hotspots/HotspotToolbar';
import TrendIndicator from '../components/common/TrendIndicator';
import HeatScoreBar from '../components/common/HeatScoreBar';
import PlatformTag from '../components/common/PlatformTag';
import { usePreferences } from '../contexts/PreferencesContext';
import { useFavorites } from '../contexts/FavoritesContext';
import { getHotspots, getHotspotDates } from '../services/hotspots';
import { batchMatchKeywords } from '../services/keywords';
import FavoriteModal from '../components/common/FavoriteModal';
import { usePageState, useScrollPosition } from '../hooks/usePageState';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text } = Typography;
const { RangePicker } = DatePicker;

const Hotspots = () => {
  const navigate = useNavigate();
  const { viewMode, setViewMode, isDark } = usePreferences();
  const { addFavorite, removeFavorite, isFavorite } = useFavorites();
  const [data, setData] = useState([]);
  const [meta, setMeta] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterMode, setFilterMode] = useState('keyword');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTrend, setSelectedTrend] = useState(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [favoriteModalVisible, setFavoriteModalVisible] = useState(false);
  const [currentItemToFavorite, setCurrentItemToFavorite] = useState(null);
  const [defaultDateApplied, setDefaultDateApplied] = useState(false);

  // ========== 关键词分组相关状态 ==========
  const [keywordGroups, setKeywordGroups] = useState([]);
  const [keywordMatchMap, setKeywordMatchMap] = useState({});
  const [keywordLoading, setKeywordLoading] = useState(false);

  // ========== 日期范围选择相关状态 ==========
  const [dateRange, setDateRange] = useState([null, null]);
  const [availableDates, setAvailableDates] = useState([]);
  const [datesLoading, setDatesLoading] = useState(false);

  // ========== 页面状态保持（返回时恢复） ==========
  const { saveState, loadState, clearState, shouldRestore } = usePageState('hotspots');
  const { captureAndSave: saveScrollPos, restoreScroll: restoreScrollPos } = useScrollPosition();
  const restoredRef = useRef(false);
  const pendingScrollYRef = useRef(0);
  const isRestoringStateRef = useRef(false);
  // 标记是否正在从快照恢复（防止恢复过程中触发重复数据请求）
  const isRestoringFromSnapshotRef = useRef(false);

  // ========== 分页状态 ==========
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(() => {
    // 从 localStorage 恢复用户偏好的每页条数
    try { return parseInt(localStorage.getItem('hotspots_pageSize')) || 20; }
    catch { return 20; }
  });

  // ========== 页面状态快照与恢复 ==========

  const captureSnapshot = useCallback(() => ({
    filterMode,
    searchQuery,
    activeTab,
    selectedDate: selectedDate ? selectedDate.toISOString() : null,
    selectedTrend,
    selectedPlatforms,
    dateRange: [dateRange[0] ? dateRange[0].toISOString() : null, dateRange[1] ? dateRange[1].toISOString() : null],
    defaultDateApplied,
    keywordGroups,
    keywordMatchMap,
    scrollY: window.scrollY,
    _hasData: data.length > 0,
  }), [filterMode, searchQuery, activeTab, selectedDate, selectedTrend, selectedPlatforms, dateRange, defaultDateApplied, keywordGroups, keywordMatchMap, data.length]);

  const applySnapshot = useCallback((snapshot) => {
    if (!snapshot) return false;
    if (snapshot.filterMode !== undefined) setFilterMode(snapshot.filterMode);
    if (snapshot.searchQuery !== undefined) setSearchQuery(snapshot.searchQuery);
    if (snapshot.activeTab !== undefined) setActiveTab(snapshot.activeTab);
    if (snapshot.selectedDate) setSelectedDate(dayjs(snapshot.selectedDate));
    if (snapshot.selectedTrend !== undefined) setSelectedTrend(snapshot.selectedTrend);
    if (snapshot.selectedPlatforms !== undefined) setSelectedPlatforms(snapshot.selectedPlatforms);
    if (snapshot.dateRange) setDateRange([
      snapshot.dateRange[0] ? dayjs(snapshot.dateRange[0]) : null,
      snapshot.dateRange[1] ? dayjs(snapshot.dateRange[1]) : null,
    ]);
    if (snapshot.defaultDateApplied !== undefined) setDefaultDateApplied(snapshot.defaultDateApplied);
    if (snapshot.keywordGroups) setKeywordGroups(snapshot.keywordGroups);
    if (snapshot.keywordMatchMap) setKeywordMatchMap(snapshot.keywordMatchMap);
    if (snapshot.scrollY > 0) {
      pendingScrollYRef.current = snapshot.scrollY;
    }
    return true;
  }, []);

  // 从详情页返回时恢复状态
  useEffect(() => {
    if (shouldRestore && !restoredRef.current) {
      restoredRef.current = true;
      const saved = loadState();
      if (saved && saved._hasData) {
        // 标记恢复中，防止状态变更触发重复请求
        isRestoringStateRef.current = true;
        applySnapshot(saved);
        // 使用 rAF 确保DOM更新后再清除标记
        const rafId = requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            isRestoringStateRef.current = false;
            isRestoringFromSnapshotRef.current = false;
          });
        });
        // 安全超时：即使 rAF 失败也在 300ms 后强制清除
        setTimeout(() => {
          isRestoringStateRef.current = false;
          isRestoringFromSnapshotRef.current = false;
        }, 300);
        return () => cancelAnimationFrame(rafId);
      } else {
        clearState();
      }
    }
    if (!shouldRestore) {
      restoredRef.current = false;
    }
  }, [shouldRestore, loadState, clearState, applySnapshot]);

  // 加载可用日期列表
  const loadAvailableDates = useCallback(async () => {
    setDatesLoading(true);
    try {
      const res = await getHotspotDates();
      // API返回 { success: true, data: { dates: [...], total: N } }
      const datesArray = res?.data?.dates || (Array.isArray(res?.data) ? res.data : []);
      if (res?.success && Array.isArray(datesArray)) {
      // 过滤并按日期降序排序（最新在前），只保留有效日期
      const validDates = datesArray
        .map((d) => {
          const parsed = dayjs(d);
          return { raw: d, parsed, valid: parsed.isValid() };
        })
        .filter((item) => item.valid)
        .sort((a, b) => dayjs(b.parsed).valueOf() - dayjs(a.parsed).valueOf())
        .map((item) => item.raw);

      setAvailableDates(validDates);

        // 自动选择最新可用日期（仅首次，且用户未手动选择过）
        if (!defaultDateApplied && validDates.length > 0) {
          const latestDateStr = validDates[0];
          const parsed = dayjs(latestDateStr);
          if (parsed.isValid()) {
            setSelectedDate(parsed);
            setDefaultDateApplied(true);
          }
        }
      }
    } catch (err) {
      console.error('Error loading available dates:', err);
      // 静默失败，不影响主流程
    } finally {
      setDatesLoading(false);
    }
  }, [defaultDateApplied]);

  const fetchHotspots = useCallback(async () => {
    // 从快照恢复期间跳过数据请求，避免覆盖已恢复的状态
    if (isRestoringFromSnapshotRef.current) return;

    setLoading(true);
    setError(null);
    setCurrentPage(1);
    try {
      const params = {};
      // 默认使用当日日期（如果用户未手动选择）
      const effectiveDate = selectedDate || dayjs();
      params.date = effectiveDate.format('YYYY-MM-DD');
      // 如果选择了日期范围，使用范围查询
      if (dateRange[0]) {
        params.date = dateRange[0].format('YYYY-MM-DD');
        if (dateRange[1]) {
          params.end_date = dateRange[1].format('YYYY-MM-DD');
        }
      }
      const response = await getHotspots(params);
      if (response?.success) {
        setData(normalizeItems(response));
        setMeta({
          lastFetchTime: response.data?.last_fetch_time,
          nextFetchTime: response.data?.next_fetch_time,
          total: response.data?.total || data.length,
          dateDistribution: response.data?.date_distribution || null,
        });
      }
    } catch (err) {
      setError(err.message || '获取热榜数据失败');
    } finally {
      setLoading(false);
    }
  }, [selectedDate, dateRange]);

  // 关键词批量匹配（数据变化时触发）
  const performKeywordMatch = useCallback(async (items) => {
    if (!items || items.length === 0) {
      setKeywordMatchMap({});
      setKeywordGroups([]);
      return;
    }

    setKeywordLoading(true);
    try {
      const titles = items.map((item) => item.title || '');
      const res = await batchMatchKeywords(titles);

      if (res?.success && res.data) {
        // 构建索引映射: dataIndex -> matched_group_ids[]
        const matchMap = {};
        res.data.results.forEach((r, idx) => {
          matchMap[idx] = r.matched_group_ids || [];
        });
        setKeywordMatchMap(matchMap);

        // 保存分组定义
        setKeywordGroups(res.data.group_definitions || []);
      }
    } catch (err) {
      console.error('关键词匹配失败:', err);
      setKeywordMatchMap({});
      setKeywordGroups([]);
    } finally {
      setKeywordLoading(false);
    }
  }, []);

  // 数据变化时自动触发关键词匹配
  useEffect(() => {
    if (filterMode === 'keyword' && data.length > 0) {
      performKeywordMatch(data);
    }
  }, [data, filterMode, performKeywordMatch]);

  // filterMode 切换时重置 Tab（状态恢复期间跳过）
  useEffect(() => {
    if (!isRestoringStateRef.current) {
      setActiveTab('all');
    }
  }, [filterMode]);

  useEffect(() => {
    fetchHotspots();
  }, [fetchHotspots]);

  // 数据加载完成后恢复滚动位置（从详情页返回时）
  useEffect(() => {
    if (!loading && pendingScrollYRef.current > 0 && data.length > 0) {
      const targetY = pendingScrollYRef.current;
      pendingScrollYRef.current = 0;
      requestAnimationFrame(() => {
        window.scrollTo({ top: targetY, behavior: 'instant' });
      });
    }
  }, [loading, data.length]);

  // 初始化时加载可用日期
  useEffect(() => {
    loadAvailableDates();
  }, [loadAvailableDates]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        e.preventDefault();
        document.querySelector('[aria-label="搜索热点"]')?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const groups = useMemo(() => {
    const map = new Map();
    data.forEach((item) => {
      const g = item.platform_name ?? item.groupName ?? '默认分组';
      if (!map.has(g)) map.set(g, []);
      map.get(g).push(item);
    });
    return map;
  }, [data]);

  // 按关键词分组组织数据
  const keywordGroupItems = useMemo(() => {
    if (keywordGroups.length === 0 || Object.keys(keywordMatchMap).length === 0) {
      return new Map();
    }

    const map = new Map();
    data.forEach((item, idx) => {
      const matchedIds = keywordMatchMap[idx] || [];
      matchedIds.forEach((groupId) => {
        const groupDef = keywordGroups.find((g) => g.id === groupId);
        if (groupDef) {
          const groupName = groupDef.name;
          if (!map.has(groupName)) map.set(groupName, []);
          map.get(groupName).push(item);
        }
      });
    });
    return map;
  }, [data, keywordGroups, keywordMatchMap]);

  const availablePlatforms = useMemo(() => {
    return Array.from(groups.keys()).sort();
  }, [groups]);

  const filtered = useMemo(() => {
    let list;

    if (filterMode === 'keyword') {
      // 关键词模式：按关键词分组筛选
      if (activeTab === 'all') {
        // 显示所有匹配了任一关键词的数据
        list = data.filter((_, idx) => {
          const ids = keywordMatchMap[idx] || [];
          return ids.length > 0;
        });
      } else if (activeTab === 'unmatched') {
        // 未匹配任何关键词的数据
        list = data.filter((_, idx) => {
          const ids = keywordMatchMap[idx] || [];
          return ids.length === 0;
        });
      } else {
        // 选中的关键词分组
        list = keywordGroupItems.get(activeTab) || [];
      }
    } else {
      // AI模式或默认平台模式
      list = activeTab === 'all' ? data : groups.get(activeTab) || [];
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter((item) => (item.title || '').toLowerCase().includes(q));
    }

    if (selectedTrend) {
      list = list.filter((item) => item.trend === selectedTrend);
    }

    if (selectedPlatforms && selectedPlatforms.length > 0) {
      list = list.filter((item) => {
        const platform = item.platform_name || item.platform || item.groupName;
        return selectedPlatforms.includes(platform);
      });
    }

    return list;
  }, [data, groups, keywordGroupItems, keywordMatchMap, activeTab, searchQuery, selectedTrend, selectedPlatforms, filterMode]);

  // 分页数据
  const paginatedFiltered = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, currentPage, pageSize]);

  const tabItems = useMemo(() => {
    if (filterMode === 'keyword') {
      const items = [
        { key: 'all', label: `全部匹配 (${data.filter((_, idx) => (keywordMatchMap[idx] || []).length > 0).length})` },
        { key: 'unmatched', label: `未匹配 (${data.filter((_, idx) => (keywordMatchMap[idx] || []).length === 0).length})` },
      ];

      const groupEntries = Array.from(keywordGroupItems.entries());
      groupEntries.sort((entryA, entryB) => entryB[1].length - entryA[1].length);

      for (const [name, itemsList] of groupEntries) {
        items.push({ key: name, label: `${name} (${itemsList.length})` });
      }

      return items;
    } else {
      const items = [{ key: 'all', label: `全部 (${data.length})` }];
      groups.forEach((itemsList, name) => {
        items.push({ key: name, label: `${name} (${itemsList.length})` });
      });
      return items;
    }
  }, [data.length, groups, filterMode, keywordGroupItems, keywordMatchMap, data]);

  // 计算统计数据
  const statistics = useMemo(() => {
    const total = data.length;
    let dateInfo = '';

    if (dateRange[0] && dateRange[1]) {
      const start = dateRange[0].format('YYYY-MM-DD');
      const end = dateRange[1].format('YYYY-MM-DD');
      dateInfo = `${start} ~ ${end}`;
    } else if (dateRange[0]) {
      dateInfo = dateRange[0].format('YYYY-MM-DD');
    } else if (selectedDate) {
      dateInfo = selectedDate.format('YYYY-MM-DD');
    } else {
      dateInfo = dayjs().format('YYYY-MM-DD');
    }

    // 如果有按天分布的数据
    const distribution = meta.dateDistribution;
    const dailyStats = distribution
      ? Object.entries(distribution)
          .map(([date, count]) => {
            const parsed = dayjs(date);
            return { date, count, valid: parsed.isValid(), parsed };
          })
          .filter((item) => item.valid)
          .sort((a, b) => dayjs(b.parsed).valueOf() - dayjs(a.parsed).valueOf())
          .map(({ date, count }) => ({ date, count }))
      : null;

    return {
      total,
      dateInfo,
      dailyStats,
    };
  }, [data.length, dateRange, selectedDate, meta.dateDistribution]);

  const handleNavigate = (item) => {
    saveState(captureSnapshot());
    const url = item.url_norm || item.url;
    if (!url) return;
    const params = new URLSearchParams();
    if (item._source_date) params.set('date', item._source_date);
    const qs = params.toString();
    navigate(`/articles/${encodeURIComponent(url)}${qs ? '?' + qs : ''}`);
  };

  const handleFavoriteClick = (item, favorited, e) => {
    e.stopPropagation();
    if (favorited) {
      const id = item.id || item.url_norm || item.url;
      removeFavorite(id);
    } else {
      setCurrentItemToFavorite(item);
      setFavoriteModalVisible(true);
    }
  };

  const handleConfirmFavorite = (tags, remark) => {
    if (currentItemToFavorite) {
      addFavorite(currentItemToFavorite, tags, remark);
    }
    setFavoriteModalVisible(false);
    setCurrentItemToFavorite(null);
  };

  // 处理日期范围变化
  const handleDateRangeChange = (dates) => {
    setDateRange(dates || [null, null]);
    // 清除单选日期
    if (dates && dates[0]) {
      setSelectedDate(null);
    }
  };

  const resetFilters = () => {
    setSearchQuery('');
    setSelectedDate(null);
    setSelectedTrend(null);
    setSelectedPlatforms([]);
    setActiveTab('all');
    setDateRange([null, null]);
    setDefaultDateApplied(false);
    setFilterMode('keyword');
    message.info('筛选条件已重置');
  };

  return (
    <div className="hotspots-page">
      <PageHeader
        title="热榜总览"
        description="实时聚合多平台热点，支持关键词与 AI 筛选"
        tags={<StatusBadge status={error ? 'warn' : 'ok'} text={error ? '数据异常' : '采集中'} />}
      />

      {error && (
        <Alert
          message="无法加载热榜"
          description={
            <>
              {error}。请确认已运行{' '}
              <code>uv run python scripts/start_platform.py</code>
            </>
          }
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* ==================== 数据统计区域 ==================== */}
      <Card size="small" style={{ marginBottom: 16 }} bordered={false}>
        <Row gutter={[16, 8]} align="middle">
          <Col>
            <Statistic
              title="热点总数"
              value={statistics.total}
              suffix="条"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>选择日期</Text>
              <br />
              <Text strong>{statistics.dateInfo}</Text>
            </div>
          </Col>

          {/* 日期范围选择器 */}
          <Col flex="auto">
            <RangePicker
              value={dateRange}
              onChange={handleDateRangeChange}
              allowClear
              placeholder={['开始日期', '结束日期']}
              style={{ width: '100%', maxWidth: 300 }}
              disabledDate={(current) => {
                // 可选：限制不能选择未来日期
                return current && current > dayjs().endOf('day');
              }}
            />
          </Col>

          {/* 快速日期选择 */}
          <Col>
            <Space wrap size="small">
              <Tag.CheckableTag
                checked={!dateRange[0] && !selectedDate}
                onChange={() => {
                  setDateRange([null, null]);
                  setSelectedDate(null);
                }}
              >
                今天
              </Tag.CheckableTag>
              {availableDates
                .slice(0, 5)
                .filter((dateStr) => {
                  // 过滤掉无法解析的无效日期
                  const parsed = dayjs(dateStr);
                  return parsed.isValid();
                })
                .map((dateStr) => {
                  const parsed = dayjs(dateStr);
                  return (
                    <Tag.CheckableTag
                      key={dateStr}
                      checked={
                        dateRange[0]?.format('YYYY-MM-DD') === dateStr ||
                        selectedDate?.format('YYYY-MM-DD') === dateStr
                      }
                      onChange={() => {
                        setDateRange([parsed, parsed]);
                        setSelectedDate(null);
                      }}
                    >
                      {parsed.format('MM/DD')}
                    </Tag.CheckableTag>
                  );
                })}
            </Space>
          </Col>
        </Row>

        {/* 多日分布情况 */}
        {statistics.dailyStats && statistics.dailyStats.length > 1 && (
          <Row gutter={[8, 8]} style={{ marginTop: 12 }}>
            <Col span={24}>
              <Text type="secondary" style={{ fontSize: 12 }}>每日分布：</Text>
              {statistics.dailyStats.map(({ date, count }) => {
                const parsed = dayjs(date);
                return (
                  <Tag
                    key={date}
                    color={count >= 50 ? 'red' : count >= 20 ? 'orange' : 'blue'}
                    style={{ marginBottom: 4 }}
                  >
                    {parsed.isValid() ? parsed.format('MM/DD') : date} ({count})
                  </Tag>
                );
              })}
            </Col>
          </Row>
        )}
      </Card>

      <HotspotToolbar
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              filterMode={filterMode}
              onFilterModeChange={setFilterMode}
              onSearch={setSearchQuery}
              lastFetchTime={formatTime(meta.lastFetchTime)}
              nextFetchTime={formatTime(meta.nextFetchTime)}
              selectedTrend={selectedTrend}
              onTrendChange={setSelectedTrend}
              selectedPlatforms={selectedPlatforms}
              onPlatformsChange={setSelectedPlatforms}
              availablePlatforms={availablePlatforms}
            />

      {/* AI 模式提示 */}
      {filterMode === 'ai' && (
        <Alert
          message="AI 筛选模式"
          description="AI 筛选功能正在开发中，请先使用关键词模式。如需启用 AI 筛选，请在关键词配置页面提供 AI 模型 API Key。"
          type="info"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 关键词匹配加载提示 */}
      {filterMode === 'keyword' && keywordLoading && (
        <Alert
          message="正在匹配关键词..."
          description="后台正在对热榜标题进行关键词分组匹配，请稍候"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        type="card"
        style={{ marginBottom: 16 }}
      />

      <Spin spinning={loading}>
        {paginatedFiltered.length > 0 ? (
          viewMode === 'card' ? (
            <div
              className="hotspot-grid"
              role="feed"
              aria-busy={loading}
              key={`grid-page-${currentPage}`}
              style={{ animation: 'fadeIn 0.25s ease-in' }}
            >
              {paginatedFiltered.map((item, index) => (
                <HotspotCard
                  key={item.id || index}
                  item={{
                    ...item,
                    favorited: isFavorite(item.id || item.url_norm || item.url),
                  }}
                  index={index}
                  onNavigate={handleNavigate}
                  onFavorite={handleFavoriteClick}
                />
              ))}
            </div>
          ) : (
            <div
              role="feed"
              aria-busy={loading}
              key={`list-page-${currentPage}`}
              style={{ animation: 'fadeIn 0.25s ease-in' }}
            >
              {paginatedFiltered.map((item, index) => (
                <div
                  key={item.id || index}
                  className="hotspot-list-item"
                  onClick={() => handleNavigate(item)}
                  onKeyDown={(e) => e.key === 'Enter' && handleNavigate(item)}
                  tabIndex={0}
                  role="article"
                >
                  <Text type="secondary" className="list-rank">#{index + 1}</Text>
                  <TrendIndicator trend={item.trend} />
                  <span className="list-title">{item.title}</span>
                  <HeatScoreBar score={item.score} />
                  <PlatformTag platform={item.platform_name || item.platform || 'weibo'} />
                </div>
              ))}
            </div>
          )
        ) : (
          !loading && (
            <Empty description="暂无热榜数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )
        )}
      </Spin>

      {filtered.length > 0 && (
        <div style={{ textAlign: 'center', marginTop: 16, padding: '8px 0', background: isDark ? '#1f1f1f' : '#fafafa', borderRadius: 8 }}>
          <Pagination
            current={currentPage}
            pageSize={pageSize}
            total={filtered.length}
            onChange={(page, size) => {
              setCurrentPage(page);
              if (size !== pageSize) {
                setPageSize(size);
                localStorage.setItem('hotspots_pageSize', String(size));
                setCurrentPage(1); // 切换每页条数时回到第1页
              }
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            showSizeChanger
            showTotal={(total, range) => `共 ${total} 条 · 第 ${range[0]}-${range[1]} 条`}
            showQuickJumper
            size="small"
            pageSizeOptions={['10', '20', '50', '100']}
          />
        </div>
      )}

      <FavoriteModal
        visible={favoriteModalVisible}
        item={currentItemToFavorite}
        onCancel={() => {
          setFavoriteModalVisible(false);
          setCurrentItemToFavorite(null);
        }}
        onConfirm={handleConfirmFavorite}
      />
    </div>
  );
};

// 从响应数据中提取出条目，规范化
const normalizeItems = (response) => {
  const hotspotsData = response?.data;
  const items = [];
  if (hotspotsData?.groups) {
    if (Array.isArray(hotspotsData.groups)) {
      hotspotsData.groups.forEach((group) => {
        (group.hotspots || []).forEach((item) => {
          items.push({ 
            ...item, 
            groupName: group.name,
            // 保留原始时间字段，优先使用 publish_time
            publish_time: item.publish_time || item.created_at || item.pub_time,
            url_norm: item.url_norm || item.url,
          });
        });
      });
    } else {
      Object.entries(hotspotsData.groups).forEach(([platform, list]) => {
        (list || []).forEach((item) => {
          items.push({ 
            ...item, 
            platform_name: item.platform_name || platform,
            // 保留原始时间字段，优先使用 publish_time
            publish_time: item.publish_time || item.created_at || item.pub_time,
            url_norm: item.url_norm || item.url,
          });
        });
      });
    }
  } else if (hotspotsData?.items) {
    hotspotsData.items.forEach((item) => items.push({
      ...item,
      // 保留原始时间字段，优先使用 publish_time
      publish_time: item.publish_time || item.created_at || item.pub_time,
      url_norm: item.url_norm || item.url,
    }));
  }
  return items.map((item, i) => ({
    ...item,
    trend: item.trend || TRENDS[i % TRENDS.length],
    score: item.score ?? item.hot_score ?? Math.max(50, 100 - i * 3),
    // 确保时间字段被正确保留
    publish_time: item.publish_time || null,
    url_norm: item.url_norm || item.url || null,
  }));
};

const TRENDS = ['up', 'down', 'flat', 'new'];

// 格式化时间
const formatTime = (time) => {
  if (!time) return null;
  const d = dayjs(time);
  // 如果是相对时间超过1天，同时显示绝对时间
  const fromNow = d.fromNow();
  const absolute = d.format('MM-DD HH:mm');
  return { relative: fromNow, absolute, raw: time };
};

export default Hotspots;
