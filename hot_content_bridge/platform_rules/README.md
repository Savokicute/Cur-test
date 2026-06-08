# 平台过滤规则目录

每个热榜平台一个 YAML 文件，**文件名（不含扩展名）应与 `trendRadar/config/config.yaml` 里 `platforms.sources[].id` 一致**。

| 文件 | 平台 ID |
|------|---------|
| `thepaper.yaml` | thepaper |
| `wallstreetcn-hot.yaml` | wallstreetcn-hot |
| `cls-hot.yaml` | cls-hot |
| `ifeng.yaml` | ifeng |
| `toutiao.yaml` | toutiao（在 trendRadar 中启用后生效） |
| … | 见目录内其它文件 |

`_default.yaml` 为未单独配置平台时的兜底规则。

详细接入说明见仓库根目录 [`docs/PLATFORM_RULES.md`](../../docs/PLATFORM_RULES.md)。

查看已加载规则：

```bash
uv run hot-content-bridge list-platform-rules
```
