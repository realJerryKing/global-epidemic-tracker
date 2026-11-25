# 🌍 Global Epidemic Tracker · 疫情观察

> **CDC is dead, we protect the people.**
>
> **El pueblo unido jamás será vencido.**

[公开地图](https://realJerryKing.github.io/global-epidemic-tracker/) · [DSH 插件安装](plugin/README.md) · [后端部署](backend/README.md) · [数据口径](docs/data/README.md) · [地图数据来源](docs/map-sources.html)

在地图查看 WHO 疾病暴发通报、WHO 年度指标和 OWID 累计观测。在 DSH 侧栏查看地区社区周报、参考范围和防护指引，并自愿提交本周签到。公开地图可以独立使用。仓库提供邀请码试点后端，真实参与者需连接项目方部署的服务。

## 先试地图

在仓库根目录运行以下命令，然后打开 http://localhost:8000/ 。用 `?region=440106` 直接查看广州市天河区。

```sh
python -m http.server 8000 --directory docs --bind 127.0.0.1
```

中国视图覆盖 31 个大陆省级行政区，北京和广州支持区级选择。公共报告和自报周报分开展示。WHO 通报按发布日期浏览，年度指标显示统计年，累计观测显示截止日。随代码提供的首批数据从旧快照迁移，界面标记归档时间与覆盖范围。

## 安装侧栏并开通试点

1. 按[插件说明](plugin/README.md)构建并安装与 DSH 版本匹配的 bundle。在当前会话右侧栏打开插件页。
2. 运营者按[后端说明](backend/README.md)准备 PostgreSQL、HTTPS API 和每周聚合任务。生产接入前使用模拟参与者验证授权、撤回、保留期和发布规则。
3. 将同一 API 地址配置在插件 Host 和公开地图的 [config.js](docs/config.js)。邀请码通过私密渠道交付，地图只查询公开汇总。社区发布默认关闭。
4. 每周签到可选本人新发症状、症状延续或无症状，另有可选的身边观察。用户可以修改或撤回保留期内的记录。归档周报按已发布周和地区展示，区级数据不足时标明上级参考范围。

## 官方数据更新

```sh
python scripts/fetch_data.py --fetch --export-json --summary
```

更新器使用 Python 标准库，在所需来源都返回有效数据后生成一对 JSON 和 GeoJSON。唯一发布目录是 [docs/data](docs/data/README.md)。GitHub Pages 可配置为从默认分支的 `/docs` 发布。社区签到由私有 API 接收，个人记录始终存放在后端数据库。

## 开发与测试

```sh
python -m pip install -r backend/requirements-test.txt
python -m unittest discover -s tests -p 'test_official*.py' -v
python -m unittest discover -s backend/tests -v
node tests/dashboard-browser-smoke.mjs
cd plugin
npm run build
npm test
npm pack
```

浏览器测试使用 Node 22+ 和本机 Chromium/Edge，可通过 `BROWSER_BIN` 指定浏览器。PostgreSQL 集成测试通过 `TEST_POSTGRES_URL` 指向一次性测试库，CI 提供隔离数据库。数据模型和分母口径见[官方快照说明](docs/data/README.md)和[社区周报契约](backend/README.md)。

## 许可证

项目代码使用 [MIT](LICENSE)。地图数据的来源与许可见[地图署名](docs/map-sources.html)。
