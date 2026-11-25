---
name: global-epidemic-tracker
description: 查询全球官方来源记录、中国地区自愿签到周报与防护指引。
---

已安装 DSH 疫情观察插件时，使用只读工具 `epidemic_snapshot` 查询地区公开摘要。地区代码用插件行政区目录中的六位代码。提到周报时一并说明统计周、用户请求的地区和实际提供证据的地区。样本受限或数据过期时，明确显示这一状态。

用户想参与、修改或撤回每周签到时，请引导其使用插件内的私密表单。邀请码和个人健康信息应在该表单中输入。

没有试点服务时仍可打开[公开地图](https://realJerryKing.github.io/global-epidemic-tracker/)，或在仓库根目录运行 `python -m http.server 8000 --directory docs --bind 127.0.0.1` 查看本地版本。引用数值时保留来源、统计周期及原文链接。WHO 通报发布日期、年度指标和累计观测各有不同含义，详见[快照契约](docs/data/README.md)。
