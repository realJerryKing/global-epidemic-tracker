# 🌍 Global Epidemic Tracker

> **CDC is dead, we protect the people.**
>
> **El pueblo unido jamás será vencido.**

[![收录于 JerryKing's Trove](https://img.shields.io/badge/收录于-JerryKing's%20Trove-blue)](https://github.com/realJerryKing/JerryKing-s-Trove)

[![Live Dashboard](https://img.shields.io/badge/Live-Dashboard-00d4aa?style=for-the-badge&logo=googlechrome&logoColor=white)](https://realJerryKing.github.io/global-epidemic-tracker/)
[![Auto Update](https://github.com/realJerryKing/global-epidemic-tracker/actions/workflows/update-data.yml/badge.svg)](https://github.com/realJerryKing/global-epidemic-tracker/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

实时全球疫情监控，支持新闻交叉验证。数据来源于 WHO 疾病暴发新闻 API，经独立新闻媒体验证，通过中文交互式仪表板呈现。

---

## 功能概览

```
WHO DON API  →  数据采集器  →  新闻交叉验证  →  仪表板
(所有疾病)     (53种疾病)    (Bing/Google/Reddit)   (中文)
```

- **581 个活跃疫情** 覆盖 **151 个国家**
- **53 种疾病** 包括霍乱、埃博拉、登革热、麻疹、汉坦病毒、猴痘等
- **297 万病例** 和 **13,677 例死亡** 全球监控
- **新闻交叉验证**：每个疫情经 Bing、Google News、Reddit 验证
- **数据源和可信度标注**：每个疾病卡片显示数据来源和验证状态
- **每 6 小时自动更新** 通过 GitHub Actions

## 仪表板

**[→ 打开仪表板](https://realJerryKing.github.io/global-epidemic-tracker/)**

| 功能 | 说明 |
|------|------|
| 交互式地图 | 暗色主题，聚类标记，严重性配色 |
| 趋势图视图 | 点击 📊 切换，显示近一年历史数据折线图 |
| 视图同步 | 地图和趋势图共享筛选条件，数据实时同步 |
| 层级筛选 | 大洲 → 国家，病原体类型 → 疾病 |
| 数据源标注 | 每个疾病显示 WHO、OWID、新闻验证标签 |
| 可信度指标 | 已交叉验证 / 部分验证 / 待验证 |
| 疾病提示 | 鼠标悬停查看疾病描述 |
| 风险警报 | H2H 人传人警告，严重性排名 |
| 新闻滚动 | 最新疫情新闻滚动显示 |
| 疾病详情 | 点击查看 7天/30天/半年 趋势图 |
| 语言 | 中文（简体） |

## 快速开始

```bash
git clone https://github.com/realJerryKing/global-epidemic-tracker.git
cd global-epidemic-tracker
pip install requests

# 获取最新数据 + 新闻验证
python3 scripts/fetch_data.py --fetch --validate --summary

# 导出仪表板数据
python3 scripts/fetch_data.py --fetch --export-json --export-geojson

# 本地打开仪表板
open docs/index.html          # macOS
xdg-open docs/index.html      # Linux
start docs/index.html          # Windows
```

## Python API

```python
from src.collectors.aggregator import EpidemicAggregator

agg = EpidemicAggregator()
agg.fetch_all(validate=True)

# 全球摘要
summary = agg.get_global_summary()
# → 581 outbreaks, 2,970,802 cases, 13,677 deaths

# 按疾病、国家、严重性筛选
cholera = agg.get_outbreaks(disease="Cholera")
japan = agg.get_outbreaks(country="JPN")
critical = agg.get_outbreaks(severity="very_high")

# 按大洲和病原体类型筛选
asia_outbreaks = agg.get_outbreaks(continent="Asia")
virus_outbreaks = agg.get_outbreaks(pathogen_type="Virus")

# 风险评估
risk = agg.get_risk_assessment("JPN")
# → {"level": "low", "total_cases": 0, ...}
```

## Agent 集成

`SKILL.md` 文件使本项目可作为 AI Agent 技能使用。兼容：

- **OpenCode** — `load_skills=["global-epidemic-tracker"]`
- **Claude Code** — 在上下文中引用 `SKILL.md`
- **OpenClaw** / **Hermes** — 在 Agent 上下文中包含 `SKILL.md`

示例查询：
- "现在有哪些霍乱疫情？"
- "亚洲最危险的疫情是什么？"
- "哪些疾病有人传人？"

## 架构

```
global-epidemic-tracker/
├── SKILL.md                          # Agent 技能定义
├── scripts/fetch_data.py             # CLI 数据管道
├── src/
│   ├── collectors/
│   │   ├── who_don.py                # WHO 疾病暴发新闻 API
│   │   ├── who_gho.py                # WHO 全球卫生观测
│   │   ├── owid.py                   # Our World in Data (猴痘)
│   │   └── aggregator.py             # 多源聚合
│   ├── validation/
│   │   └── news_validator.py         # Bing/Google/Reddit 交叉验证
│   └── models/
│       └── __init__.py               # 数据模型
├── docs/
│   ├── index.html                    # 仪表板（单文件，无需服务器）
│   └── data/                         # 实时数据 (JSON/GeoJSON)
├── data/
│   └── processed/                    # 导出数据
└── .github/workflows/
    └── update-data.yml               # 每 6 小时自动更新
```

## 数据源

| 来源 | 内容 | 方法 | 频率 |
|------|------|------|------|
| **WHO DON API** | 全球疫情警报 | REST API | 事件驱动 |
| **WHO GHO** | 年度疾病统计 | REST API | 年度 |
| **OWID** | 猴痘每日数据 | CSV | 每日 |
| **Bing News** | 交叉验证 | RSS | 每次运行 |
| **Google News** | 交叉验证 | RSS | 每次运行 |
| **Reddit** | 社区报告 | API | 每次运行 |

## 追踪的疾病

霍乱 · 埃博拉 · 马尔堡 · 猴痘 · 登革热 · 麻疹 · 流感 · 汉坦病毒 · 黄热病 · 脑膜炎 · 脊髓灰质炎 · MERS · 尼帕 · 裂谷热 · 西尼罗 · 奥罗普切 · 拉沙热 · 克里米亚出血热 · 鼠疫 · 炭疽 · 基孔肯雅 · 白喉 · 戊型肝炎 · 狂犬病 · 寨卡 · 新冠 等（共 53 种）

## 贡献

1. Fork 仓库
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

贡献方向：
- 新数据源采集器
- 疾病名称翻译
- 仪表板改进
- 数据准确性修复

## 许可证

MIT — 自由使用、分发、部署。人民的数据属于人民。
