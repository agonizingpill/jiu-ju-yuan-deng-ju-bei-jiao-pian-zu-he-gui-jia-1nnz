# 旧剧院灯具备胶片组合归架

旧码头舞台器材库对老化色片留档，用非负成分谱协助找片，归架时保留介质、批龄和空位记录。

## 现场工作与联系人

模拟客户为旧码头舞台器材库。色片透过曲线、成分谱、活跃色对白、归架单；老化与新批色片不得在同一收纳盒混归。

- 色片卷与批龄 `gel_reels`，字段为 `family`（介质）、`aged`（老化标志）、`eligible`（可上光台）。模型约束位于 `backend/domain/gel_reels_model.py`，规则位于 `gel_reels_service.py`。
- 可见波段扫描 `gel_curves`，字段为 `reel`（胶片卷）、`bands`（四波段透过率）、`rechecked`（已复测）。模型约束位于 `backend/domain/gel_curves_model.py`，规则位于 `gel_curves_service.py`。
- 成分谱签条 `color_profiles`，字段为 `curve`（色片曲线）、`weights`（非负成分谱）、`dominant`（主成分编号）、`error_value`（重构均误）、`token`（计算凭据）、`baseline`（所依据的统一基准）。模型约束位于 `backend/domain/color_profiles_model.py`，规则位于 `color_profiles_service.py`。
- 统一 NMF 基准 `nmf_baselines`，字段为 `components`（共享成分矩阵）、`status`（active 在用 / staged 待切换 / retired 已退役）、`references`（复测样本数）、`token`、`mean_error`；在盒签条对新基准的换算记录在 `profile_conversions`。模型位于 `backend/domain/nmf_baselines_model.py`，规则位于 `nmf_baselines_service.py`。
- 色片收纳盒 `filter_boxes`，字段为 `kind`（介质）、`aged`（收纳批龄）、`space`（空位）、`contents`（归架签条）。模型约束位于 `backend/domain/filter_boxes_model.py`，规则位于 `filter_boxes_service.py`。

团队为模拟的5 人舞台器材库，负责将备用透光片归入片盒。

库员一边照光台记录一边对片盒挂签。所有成分谱签条与找片都投影到同一套在用 NMF 基准，权重才可比、才能据此找相近备片；新片和老化片容易混放，借出后原归盒记录缺失。

出入库色片和透过率测量进入成分谱工作页，保管员根据签条与老化标记安排归盒和领出。复核员用复测曲线建立待切换基准，把当时在盒签条逐条换算；全部对上后一次性切换为在用基准。换算期间归盒与调出仍按旧基准进行，换算失败或旧凭据过期则用原曲线重算，重试不会重复启用。

### 一天的业务操作

1. 08:40 查阅 REEL-H 老化标志。
2. 09:10 在光台扫描 SP-RUBY 四个波段。
3. 10:20 复核读数。
4. 11:30 获取 NMF-24 成分谱。
5. 13:05 新胶片盒拒收老化色片。
6. 14:10 归入 BOX-H 后剩 1 位，下次修理调出恢复空位。

## 启动

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```

打开 `http://127.0.0.1:18325`。FastAPI OpenAPI 在 `http://127.0.0.1:19325/docs`。
Compose 运行 Nginx、Python FastAPI、独立 Redis 消费进程、SQL 数据库和 Redis，SQL 与 Redis 使用命名卷。
本机开发时，在 Python 3.11 环境安装 `backend/requirements.txt` 后从 backend 目录运行 `uvicorn core.app:app`。须提供 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET`，`SEED_DEMO` 控制演示初始化。

领域测试用 SQLite + fakeredis 跑通服务层、worker 与 HTTP 路由，无需容器：

```sh
pip install -r backend/requirements.txt fakeredis httpx
python -I tests/test_baseline_flow.py       # 统一基准/找片/换版端到端
python -I tests/test_api_integration.py     # 路由、鉴权与 worker 集成
```

| 演示账号 | 权限 |
|---|---|
| operator@demo.test | 提交领域记录和计算请求 |
| reviewer@demo.test | 提交记录并执行有业务约束的复核操作 |
| viewer@demo.test | 浏览业务台账 |

三个本地演示账号均使用 `DemoC0de!2026`。角色在 `backend/core/roles.py` 和 `frontend/src/store.js` 中声明。计算状态在 worker、queueing、API 和同一前端 store 中使用。

## 页面与接口

| 业务任务 | FastAPI 路由 | 页面 |
|---|---|---|
| 色片卷与批龄 | `/gel_reels` /gel_reels/open-light-table | `frontend/src/pages/gel_reels.js` |
| 可见波段扫描 | `/gel_curves` /gel_curves/scan-gel，/gel_curves/recheck-curve | `frontend/src/pages/gel_curves.js` |
| 成分谱签条 | `/color_profiles` /color_profiles/decompose-gel，/color_profiles/save-components | `frontend/src/pages/color_profiles.js` |
| 统一基准与换版 | `/nmf_baselines` /nmf_baselines/build-baseline、/save-baseline、/convert-profile、/settle-conversion、/activate-baseline，/nmf_baselines/conversions | `frontend/src/pages/nmf_baselines.js` |
| 色片收纳盒 | `/filter_boxes` /filter_boxes/store-profile，/filter_boxes/pull-profile，/filter_boxes/find-similar | `frontend/src/pages/filter_boxes.js` |

SQL 实体与约束在 `backend/domain` 下维护。前端使用原生 ES modules。核心算子为 NMF：先在全部复测曲线上拟合一套共享基准（两成分），再用非负最小二乘把单条曲线投影到该基准，报告系数和重构绝对均误。同一时刻只有一条 `active` 基准，待切换基准为 `staged`，换版成功后旧基准置为 `retired`。

### 基准换版与找片规则

1. 待找色片与在盒签条都换算到同一套在用基准，在相同权重空间按余弦相似度排序找相近备片。
2. 复核员用复测曲线拟合新基准并签存为 `staged`；建立期间归盒、调出、找片仍按旧的在用基准。
3. 在盒签条逐条换算到新基准并结算；同一签条同一基准排队中不重复提交，失败或凭据过期后用原曲线重新换算。
4. 仅当当时在盒签条全部换算成功（`/nmf_baselines/conversions` 的 `matched=true`）才允许一次性切换，旧基准退役、在盒签条权重整体改写。
5. 晚到的旧计算签条（无在用基准归属）在归盒与找片时按在用基准即时投影，旧凭据过期则用原曲线重算，不改动其原始凭据。

透过率数据为模拟，片盒记录无外部器材系统联动。

[MIT](LICENSE)
