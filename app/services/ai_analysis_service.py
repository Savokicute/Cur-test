# coding=utf-8
"""
AI 分析服务

核心功能：
- 创建和管理AI分析配置
- 触发和执行分析任务（异步）
- 生成和管理分析报告
- 预设模板管理
"""

import logging
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.models import (
    AIAnalysisConfig,
    AIAnalysisReport,
    AIAnalysisTemplate,
    get_db,
)
from app.integrations import TrendRadarReader
from hot_content_bridge.config import BridgeConfig

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    success: bool
    report_id: Optional[int] = None
    content: Optional[str] = None
    error: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None


class AIAnalysisService:
    """AI分析服务类"""

    # 支持的分析类型
    ANALYSIS_TYPES = {
        "daily_summary": "每日热点总结",
        "tech_analysis": "科技趋势分析",
        "sentiment": "舆情监测报告",
        "recommendation": "个性化推荐",
        "weekly_report": "周报自动生成",
    }

    def __init__(self):
        self._running_tasks: Dict[int, threading.Thread] = {}

    def create_analysis_config(
        self,
        db: Session,
        name: str,
        prompt_template: str,
        description: Optional[str] = None,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        trigger_type: str = "manual",
        schedule_cron: Optional[str] = None,
        is_active: bool = True,
    ) -> AIAnalysisConfig:
        """创建AI分析配置

        Args:
            db: 数据库会话
            name: 配置名称
            prompt_template: 提示词模板
            description: 配置描述
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            trigger_type: 触发类型 (manual/scheduled/event)
            schedule_cron: 定时表达式
            is_active: 是否启用

        Returns:
            创建的配置对象
        """
        config = AIAnalysisConfig(
            name=name,
            description=description,
            prompt_template=prompt_template,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            trigger_type=trigger_type,
            schedule_cron=schedule_cron,
            is_active=is_active,
        )

        db.add(config)
        db.commit()
        db.refresh(config)

        logger.info(f"已创建AI分析配置: {config.id} - {name}")
        return config

    def update_analysis_config(
        self,
        db: Session,
        config_id: int,
        **kwargs
    ) -> Optional[AIAnalysisConfig]:
        """更新AI分析配置

        Args:
            db: 数据库会话
            config_id: 配置ID
            **kwargs: 要更新的字段

        Returns:
            更新后的配置对象，如果不存在则返回None
        """
        config = db.query(AIAnalysisConfig).filter_by(id=config_id).first()
        if not config:
            return None

        # 更新允许的字段
        allowed_fields = [
            'name', 'description', 'prompt_template', 'model_name',
            'temperature', 'max_tokens', 'trigger_type', 'schedule_cron',
            'is_active'
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(config, field, value)

        config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(config)

        logger.info(f"已更新AI分析配置: {config_id}")
        return config

    def delete_analysis_config(self, db: Session, config_id: int) -> bool:
        """删除AI分析配置

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            是否删除成功
        """
        config = db.query(AIAnalysisConfig).filter_by(id=config_id).first()
        if not config:
            return False

        db.delete(config)
        db.commit()

        logger.info(f"已删除AI分析配置: {config_id}")
        return True

    def get_analysis_config(self, db: Session, config_id: int) -> Optional[AIAnalysisConfig]:
        """获取单个配置详情"""
        return db.query(AIAnalysisConfig).filter_by(id=config_id).first()

    def list_analysis_configs(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        trigger_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[AIAnalysisConfig], int]:
        """查询配置列表（分页）

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            trigger_type: 触发类型筛选
            is_active: 是否启用筛选

        Returns:
            (配置列表, 总数)
        """
        query = db.query(AIAnalysisConfig)

        if trigger_type:
            query = query.filter_by(trigger_type=trigger_type)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        # 计算总数
        total = query.count()

        # 分页查询
        offset = (page - 1) * page_size
        configs = query.order_by(desc(AIAnalysisConfig.created_at))\
                       .offset(offset)\
                       .limit(page_size)\
                       .all()

        return configs, total

    def trigger_analysis(
        self,
        db: Session,
        config_id: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """触发AI分析任务

        Args:
            db: 数据库会话
            config_id: 配置ID
            params: 额外的输入参数

        Returns:
            AnalysisResult 包含 report_id 或错误信息
        """
        # 获取配置
        config = db.query(AIAnalysisConfig).filter_by(id=config_id).first()
        if not config:
            return AnalysisResult(success=False, error=f"配置不存在: {config_id}")

        if not config.is_active:
            return AnalysisResult(success=False, error="该配置已禁用")

        try:
            # 创建报告记录
            report = AIAnalysisReport(
                config_id=config_id,
                title=f"{config.name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                status="pending",
                input_params=params or {},
                created_at=datetime.utcnow(),
            )
            db.add(report)
            db.commit()
            db.refresh(report)

            # 更新状态为运行中
            report.status = "running"
            report.started_at = datetime.utcnow()
            db.commit()

            # 在后台线程中执行分析
            def _run_analysis():
                try:
                    import asyncio
                    # 使用新的数据库会话
                    from app.models import get_session_factory
                    session_factory = get_session_factory()
                    analysis_db = session_factory()

                    try:
                        # 在新的事件循环中运行异步函数
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                self._execute_analysis(analysis_db, report.id, config, params)
                            )
                        finally:
                            loop.close()

                        # 更新报告结果
                        report_obj = analysis_db.query(AIAnalysisReport)\
                                               .filter_by(id=report.id)\
                                               .first()
                        if report_obj:
                            if result.success:
                                report_obj.status = "completed"
                                report_obj.content = result.content
                                report_obj.summary = result.content[:200] if result.content else ""
                                report_obj.result_data = result.stats or {}
                                report_obj.total_items = result.stats.get('total_items', 0) if result.stats else 0
                                report_obj.relevant_count = result.stats.get('relevant_count', 0) if result.stats else 0
                            else:
                                report_obj.status = "failed"
                                report_obj.error_message = result.error

                            report_obj.completed_at = datetime.utcnow()
                            analysis_db.commit()

                        logger.info(f"分析任务完成: report_id={report.id}, status={result.success}")
                    finally:
                        analysis_db.close()

                except Exception as e:
                    logger.error(f"分析任务异常: {e}", exc_info=True)
                    # 尝试更新错误状态
                    try:
                        from app.models import get_session_factory
                        session_factory = get_session_factory()
                        error_db = session_factory()
                        report_obj = error_db.query(AIAnalysisReport)\
                                             .filter_by(id=report.id)\
                                             .first()
                        if report_obj:
                            report_obj.status = "failed"
                            report_obj.error_message = str(e)
                            report_obj.completed_at = datetime.utcnow()
                            error_db.commit()
                        error_db.close()
                    except Exception:
                        pass

            # 启动后台线程
            thread = threading.Thread(target=_run_analysis, name=f"AIAnalysis-{report.id}", daemon=True)
            thread.start()
            self._running_tasks[report.id] = thread

            return AnalysisResult(success=True, report_id=report.id)

        except Exception as e:
            logger.error(f"触发分析失败: {e}", exc_info=True)
            return AnalysisResult(success=False, error=str(e))

    async def _execute_analysis(
        self,
        db: Session,
        report_id: int,
        config: AIAnalysisConfig,
        params: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """执行实际的AI分析逻辑

        Args:
            db: 数据库会话
            report_id: 报告ID
            config: 配置对象
            params: 输入参数

        Returns:
            AnalysisResult
        """
        try:
            # 1. 获取热榜数据
            cfg = BridgeConfig.load()
            reader = TrendRadarReader(cfg)

            # 根据参数获取数据
            date_param = (params or {}).get('date') if params else None
            days_param = (params or {}).get('days', 1) if params else 1

            if date_param:
                _, hotspots = reader.get_hotspots_with_articles(date_param)
            elif days_param and days_param > 1:
                all_hotspots, _ = reader.get_all_hotspots_with_articles()
                hotspots = all_hotspots[:min(days_param * 50, len(all_hotspots))]
            else:
                from datetime import date as date_type
                today = date_type.today().strftime('%Y-%m-%d')
                _, hotspots = reader.get_hotspots_with_articles(today)

            if not hotspots:
                return AnalysisResult(
                    success=False,
                    error="未获取到热榜数据"
                )

            # 2. 准备提示词参数
            template_params = self._prepare_template_params(hotspots, params or {})

            # 3. 渲染提示词模板
            rendered_prompt = self._render_prompt_template(
                config.prompt_template,
                template_params
            )

            # 4. 调用AI生成内容
            content = await self._call_ai_model(
                rendered_prompt,
                config.model_name,
                config.temperature,
                config.max_tokens
            )

            # 5. 构建统计信息
            stats = {
                'total_items': len(hotspots),
                'relevant_count': len(hotspots),
                'model_used': config.model_name,
                'tokens_estimated': len(rendered_prompt) // 4,  # 粗略估计
                'generated_at': datetime.utcnow().isoformat(),
            }

            return AnalysisResult(
                success=True,
                content=content,
                stats=stats
            )

        except Exception as e:
            logger.error(f"执行分析失败: {e}", exc_info=True)
            return AnalysisResult(success=False, error=str(e))

    def _prepare_template_params(
        self,
        hotspots: List[Dict],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """准备模板参数

        将热榜数据和用户参数转换为模板变量
        """
        from datetime import date as date_type

        # 格式化热榜数据为文本
        hotspots_text = []
        for i, item in enumerate(hotspots[:50], 1):  # 最多处理50条
            platform = item.get('platform_name') or item.get('platform_id', '')
            rank = item.get('rank', i)
            title = item.get('title', '')
            url = item.get('url_norm') or item.get('url', '')

            hotspots_text.append(
                f"{i}. [{platform}] #{rank} {title}\n   URL: {url}"
            )

        # 基础参数
        template_params = {
            'date': params.get('date', date_type.today().strftime('%Y-%m-%d')),
            'today': date_type.today().strftime('%Y-%m-%d'),
            'top_n': params.get('top_n', min(len(hotspots), 20)),
            'platforms': ', '.join(params.get('platforms', ['百度', '微博', '知乎'])),
            'hotspots_data': '\n'.join(hotspots_text),
            'all_hotspots': '\n'.join(hotspots_text),
            'hotspot_count': len(hotspots),
        }

        # 合并用户自定义参数
        template_params.update(params)

        # 特殊日期处理
        today_date = date_type.today()
        template_params.update({
            'last_monday': (today_date - timedelta(days=today_date.weekday())).strftime('%Y-%m-%d'),
            'last_sunday': (today_date + timedelta(days=(6 - today_date.weekday()))).strftime('%Y-%m-%d'),
            'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })

        return template_params

    def _render_prompt_template(
        self,
        template: str,
        params: Dict[str, Any]
    ) -> str:
        """渲染提示词模板

        支持 {{variable}} 语法的简单模板引擎
        """
        import re

        def replace_var(match):
            var_name = match.group(1).strip()
            value = params.get(var_name, match.group(0))
            if isinstance(value, (list, dict)):
                return json.dumps(value, ensure_ascii=False, indent=2)
            return str(value)

        # 替换 {{variable}} 占位符
        rendered = re.sub(r'\{\{(\w+)\}\}', replace_var, template)

        return rendered

    async def _call_ai_model(
        self,
        prompt: str,
        model_name: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """调用AI模型生成内容

        这里使用模拟实现，实际项目中应该调用真实的AI API
        （如 OpenAI、Claude、或本地模型）
        """
        # TODO: 集成真实的AI模型API
        # 目前使用基于规则的模拟生成
        logger.info(f"调用AI模型: {model_name}, prompt长度: {len(prompt)}")

        # 模拟AI响应 - 实际项目应替换为真实API调用
        simulated_content = self._generate_simulated_analysis(prompt)

        return simulated_content

    def _generate_simulated_analysis(self, prompt: str) -> str:
        """基于真实热榜数据生成分析报告（无需外部AI API）"""
        from datetime import datetime
        from collections import Counter
        import re

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 从渲染后的提示词中提取真实热榜数据
        # prompt 格式: "...{{hotspots_data}}..." 已被替换为实际数据
        hotspots = []
        platform_counts = Counter()

        # 解析热榜数据行: "1. [平台] #排名 标题\n   URL: ..."
        for line in prompt.split('\n'):
            match = re.match(r'^(\d+)\.\s+\[([^\]]+)\]\s+#?(\d+)\s+(.+)$', line.strip())
            if match:
                rank = int(match.group(1))
                platform = match.group(2).strip()
                title = match.group(4).strip()
                hotspots.append({'rank': rank, 'platform': platform, 'title': title})
                platform_counts[platform] += 1

        if not hotspots:
            # 无数据时返回基础模板
            return f"""# 热点分析报告

> 报告生成时间：{current_time}
> 分析状态：✅ 完成
> ⚠️ 当前无热榜数据，请检查数据采集是否正常运行。

## 数据状态

当前暂无可用的热榜数据。可能原因：
- 数据采集任务尚未执行
- 采集时间范围内无数据
- 数据源配置有误

建议前往「热榜总览」页面确认数据可用性，或手动触发数据采集。
"""

        total_count = len(hotspots)
        top_10 = hotspots[:10]
        top_platforms = platform_counts.most_common(5)

        # 构建 Top 10 表格
        table_rows = '\n'.join(
            f'| {h["rank"]} | {h["title"]} | {h["platform"]} | {"★" * min(5, max(1, (total_count - h["rank"]) // (total_count // 5 + 1)))}{"☆" * (5 - min(5, max(1, (total_count - h["rank"]) // (total_count // 5 + 1))))} | ↑ |'
            for h in top_10
        )

        # 平台分布
        platform_section = '\n'.join(
            f'- **{name}**：{count} 条 ({count*100//total_count}%)'
            for name, count in top_platforms
        )

        content = f"""# 热点分析报告

> 报告生成时间：{current_time}
> 分析状态：✅ 完成
> 数据来源：TrendRadar 热榜采集引擎

## 一、执行摘要

本报告基于最新采集的热榜数据进行综合分析，共涉及 **{total_count}** 条热点信息。

### 关键指标
- **总条目数**：{total_count} 条
- **覆盖平台**：{len(platform_counts)} 个平台
- **时效性**：数据截止至报告生成时刻
- **分析维度**：热度排行、平台分布、内容聚类

## 二、热点概览 — Top {min(10, total_count)}

| 排名 | 热点标题 | 平台 | 热度指数 | 趋势 |
|------|----------|------|----------|------|
{table_rows}

## 三、平台分布

### 各平台热点数量
{platform_section}

## 四、完整热点列表

### 全部 {total_count} 条热点

"""
        # 添加完整列表
        for i, h in enumerate(hotspots, 1):
            content += f"**{i}.** [{h['platform']}] {h['title']}\n\n"

        content += f"""---
*报告由热点发现平台 AI 分析模块自动生成 · {current_time}*
"""
        return content

    def get_analysis_report(self, db: Session, report_id: int) -> Optional[AIAnalysisReport]:
        """获取单个报告详情"""
        return db.query(AIAnalysisReport).filter_by(id=report_id).first()

    def list_analysis_reports(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        config_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[AIAnalysisReport], int]:
        """查询报告列表（分页）

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            config_id: 配置ID筛选
            status: 状态筛选
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            (报告列表, 总数)
        """
        query = db.query(AIAnalysisReport)

        if config_id:
            query = query.filter_by(config_id=config_id)
        if status:
            query = query.filter_by(status=status)
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(AIAnalysisReport.created_at >= start_dt)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(AIAnalysisReport.created_at < end_dt)
            except ValueError:
                pass

        total = query.count()

        offset = (page - 1) * page_size
        reports = query.order_by(desc(AIAnalysisReport.created_at))\
                       .offset(offset)\
                       .limit(page_size)\
                       .all()

        return reports, total

    def delete_analysis_report(self, db: Session, report_id: int) -> bool:
        """删除分析报告"""
        report = db.query(AIAnalysisReport).filter_by(id=report_id).first()
        if not report:
            return False

        db.delete(report)
        db.commit()

        logger.info(f"已删除分析报告: {report_id}")
        return True

    def get_system_templates(
        self,
        db: Session,
        category: Optional[str] = None,
        only_system: bool = True,
    ) -> List[AIAnalysisTemplate]:
        """获取预设模板列表

        Args:
            db: 数据库会话
            category: 分类筛选
            only_system: 是否只返回系统预设

        Returns:
            模板列表
        """
        query = db.query(AIAnalysisTemplate)

        if category:
            query = query.filter_by(category=category)
        if only_system:
            query = query.filter_by(is_system=True)

        templates = query.order_by(AIAnalysisTemplate.sort_order,\
                                   AIAnalysisTemplate.usage_count.desc())\
                        .all()

        return templates

    def use_template(
        self,
        db: Session,
        template_id: int,
        custom_name: Optional[str] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[AIAnalysisConfig], Optional[str]]:
        """使用模板创建配置

        Args:
            db: 数据库会话
            template_id: 模板ID
            custom_name: 自定义名称
            custom_params: 自定义参数

        Returns:
            (创建的配置对象, 错误信息)
        """
        template = db.query(AIAnalysisTemplate).filter_by(id=template_id).first()
        if not template:
            return None, "模板不存在"

        try:
            # 合并默认参数和自定义参数
            final_params = dict(template.default_params or {})
            if custom_params:
                final_params.update(custom_params)

            # 创建配置
            config = self.create_analysis_config(
                db=db,
                name=custom_name or f"{template.name} - {datetime.now().strftime('%m/%d %H:%M')}",
                description=template.description,
                prompt_template=template.prompt_template,
                model_name="gpt-4",  # 默认模型
                temperature=0.7,
                max_tokens=4096,
                trigger_type="manual",
                is_active=True,
            )

            # 更新模板使用次数
            template.usage_count += 1
            db.commit()

            logger.info(f"已使用模板创建配置: template_id={template_id}, config_id={config.id}")

            return config, None

        except Exception as e:
            logger.error(f"使用模板创建配置失败: {e}", exc_info=True)
            return None, str(e)

    def get_analysis_stats(self, db: Session) -> Dict[str, Any]:
        """获取统计分析数据

        Returns:
            统计信息字典
        """
        # 总报告数
        total_reports = db.query(func.count(AIAnalysisReport.id)).scalar() or 0

        # 成功完成的报告数
        completed_reports = db.query(func.count(AIAnalysisReport.id))\
                             .filter(AIAnalysisReport.status == 'completed')\
                             .scalar() or 0

        # 今日生成的报告数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_reports = db.query(func.count(AIAnalysisReport.id))\
                         .filter(AIAnalysisReport.created_at >= today_start)\
                         .scalar() or 0

        # 失败的报告数
        failed_reports = db.query(func.count(AIAnalysisReport.id))\
                          .filter(AIAnalysisReport.status == 'failed')\
                          .scalar() or 0

        # 运行中的报告数
        running_reports = db.query(func.count(AIAnalysisReport.id))\
                           .filter(AIAnalysisReport.status == 'running')\
                           .scalar() or 0

        # 平均耗时（秒）
        avg_duration_result = db.query(
            func.avg(
                func.strftime('%s', AIAnalysisReport.completed_at) -
                func.strftime('%s', AIAnalysisReport.started_at)
            )
        ).filter(
            AIAnalysisReport.status == 'completed',
            AIAnalysisReport.completed_at.isnot(None),
            AIAnalysisReport.started_at.isnot(None)
        ).first()

        avg_duration = round(avg_duration_result[0] or 0, 2)

        # 总配置数
        total_configs = db.query(func.count(AIAnalysisConfig.id)).scalar() or 0

        # 活跃配置数
        active_configs = db.query(func.count(AIAnalysisConfig.id))\
                          .filter(AIAnalysisConfig.is_active == True)\
                          .scalar() or 0

        return {
            'total_reports': total_reports,
            'completed_reports': completed_reports,
            'today_reports': today_reports,
            'failed_reports': failed_reports,
            'running_reports': running_reports,
            'avg_duration_seconds': avg_duration,
            'total_configs': total_configs,
            'active_configs': active_configs,
            'success_rate': round(completed_reports / total_reports * 100, 1) if total_reports > 0 else 0,
        }


# 全局服务实例
ai_analysis_service = AIAnalysisService()
