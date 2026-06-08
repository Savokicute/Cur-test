# coding=utf-8
from pathlib import Path

import yaml

from hot_content_bridge.config import BridgeConfig, PipelineDaemonSettings


def test_pipeline_daemon_defaults(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        yaml.dump({"trendradar": {"root": "trendRadar"}}),
        encoding="utf-8",
    )
    cfg = BridgeConfig.load(path=cfg_path)
    assert isinstance(cfg.pipeline_daemon, PipelineDaemonSettings)
    assert cfg.pipeline_daemon.enabled is True
    assert cfg.pipeline_daemon.run_on_startup is True
    assert cfg.pipeline_daemon.hotlist_interval_minutes == 30
    assert cfg.pipeline_daemon.full_trendradar_sync is False
    assert cfg.pipeline_daemon.crawl_after_hotlist is True


def test_pipeline_daemon_custom(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        yaml.dump(
            {
                "pipeline_daemon": {
                    "hotlist_interval_minutes": 15,
                    "full_trendradar_sync": True,
                    "crawl_limit_per_run": 5,
                }
            }
        ),
        encoding="utf-8",
    )
    cfg = BridgeConfig.load(path=cfg_path)
    assert cfg.pipeline_daemon.hotlist_interval_minutes == 15
    assert cfg.pipeline_daemon.full_trendradar_sync is True
    assert cfg.pipeline_daemon.crawl_limit_per_run == 5
    assert cfg.pipeline_daemon.hotlist_interval_seconds == 15 * 60
