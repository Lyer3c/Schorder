# Schorder · 校园外卖点餐

学生 / 商家 / 管理三端的校园点餐系统。前端 React + TypeScript，后端 FastAPI + SQLAlchemy + SQLite。

> 当前进度：**M1 已完成**（数据表、种子数据、目录接口、档口浏览页）。
> 设计与决策见 [`docs/architecture.md`](docs/architecture.md)、[`docs/security.md`](docs/security.md)、[`docs/api-contract.md`](docs/api-contract.md)。

---

## 1. 环境要求

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.13+ | 已实测 3.13.9 |
| Node.js | 20.19+ | 已实测 v24.21.0 |
| npm | 10+ | 已实测 11.19.0 |

仓库里已配好国内镜像：`apps/api/pip.ini`（清华源）、`.npmrc`（npmmirror）。

## 2. 首次初始化

```powershell
# 1) Python 虚拟环境与依赖（在仓库根执行）
cd apps\api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 2) 建库（执行迁移）
.\.venv\Scripts\python.exe -m alembic upgrade head

# 3) 灌演示数据（可重复执行）
.\.venv\Scripts\python.exe scripts\seed.py

# 4) 前端依赖
cd ..\..
npm install --ignore-scripts
```

> 依赖清单在 `apps/api/requirements*.txt`；`pyproject.toml` 只放工具配置（ruff/mypy/pytest）。
> 不要用 `pip install -e .`：本机沙箱下构建隔离会丢弃 `PYTHONPATH` 垫片并卡死。

> `--ignore-scripts` 是本机沙箱环境下必需的（npm 的 postinstall 需要管道式子进程）。
> 普通开发机可以直接 `npm install`。

## 3. 日常命令

| 命令 | 作用 |
| --- | --- |
| `npm run dev` | 同时起 API(8000) 与 Web(5173) |
| `npm run verify` | lint → 类型 → 测试 → 契约 → 前端类型 → 构建 |
| `npm run gen:contract` | 由 Pydantic 模型重新生成 `openapi.json` 与前端 `types.ts` |

单独启动：

```powershell
# 后端
cd apps\api
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m uvicorn schorder.main:app --reload --port 8000

# 前端
cd apps\web
node ..\..\node_modules\vite\bin\vite.js --port 5173
```

打开：

- 前端 <http://127.0.0.1:5173>
- 接口文档 <http://127.0.0.1:8000/docs>
- 存活探针 <http://127.0.0.1:8000/healthz>，可用探针 <http://127.0.0.1:8000/readyz>

## 4. 目录结构

```
apps/
  api/                     Python 后端
    src/schorder/
      api/                 路由、中间件、错误出口、依赖
      db/                  引擎、会话、Alembic 辅助
      domain/              领域异常、枚举、营业时间（M2 起加定价与状态机）
      infra/               日志、ID、时钟、密码哈希
      schemas/             Pydantic 出入参
      config.py            配置（env + 校验）
      main.py              create_app()
    alembic/versions/      迁移脚本（入库、必评审）
    tests/                 单元 / 集成 / 安全用例
  web/                     React 前端
    src/app/               路由、布局、Provider
    src/features/          按业务切分（home / merchant / admin …）
    src/shared/            请求层、UI 基础件
packages/contract/         OpenAPI 与生成的 TS 类型（禁止手改）
scripts/                   dev / verify / gen-contract
docs/                      架构、安全、接口契约
```

## 5. 契约生成（前后端唯一事实来源）

```
Pydantic 模型 → FastAPI → openapi.json → openapi-typescript → types.ts
```

- 改接口：先改后端模型，再 `npm run gen:contract`，前端类型自动跟上。
- `types.ts` 与 `openapi.json` 都入库，PR 里能直接看到接口变化。
- 前端禁止手写接口类型；`npm run verify` 会重生成并检查漂移。

## 6. 已实现（M0 + M1）

**M0 骨架**

- [x] `create_app()` 工厂 + 依赖注入，`app.state` 持有 engine/sessionmaker/settings
- [x] 配置走环境变量，缺失或类型错误启动即失败
- [x] 统一错误包 `{ ok, error: { code, message, details, traceId } }`，Pydantic 校验失败映射为 `400 VALIDATION_ERROR`
- [x] 请求标识（`X-Request-Id` 透传/生成）、64KB 体积上限、安全响应头（CSP/HSTS 等）
- [x] `/healthz` 与 `/readyz`（后者比对 Alembic 版本，未迁移返回 503）
- [x] Alembic 基线迁移，SQLite WAL + 外键 + busy_timeout
- [x] React 路由壳 + Tailwind v4 设计令牌
- [x] 契约生成链路（`/api/v1/meta` 作为端到端样例）

**M1 目录**

- [x] 17 张业务表 + 迁移 `0002`（统一约束命名、CHECK 约束、部分唯一索引）
- [x] 可重复执行的种子数据：5 分类 / 6 档口 / 18 菜品 / 29 规格
- [x] 只读接口：`GET /categories`、`GET /stalls`（筛选 / 排序 / 游标分页）、`GET /stalls/{id}`、`GET /search`
- [x] 前端：首页分类与推荐、档口列表（URL 同步筛选）、档口详情（菜单分组 / 售罄 / 规格组）
- [x] 26 条后端测试、ruff、mypy strict 全绿

## 7. 本机环境的两个特殊说明

1. **`apps/api/pip.ini`**：指向清华源，并关闭 HTTP 缓存。直连 PyPI 索引在本机会卡死；缓存目录在用户目录下不可写，开启缓存会让 pip 卡在写盘重试。
2. **`.pyshim/sitecustomize.py`**：本机沙箱不允许访问 `0700` 权限的目录，而 `tempfile.mkdtemp`、pytest 的临时目录都用 0700。该垫片把 0700 放宽为 0777。**生产环境不要带上这个目录**，`dev.ps1` / `verify.ps1` 只通过 `PYTHONPATH` 引用它。

## 8. 下一步（M2）

购物车、结算、下单（服务端重算价格 / 条件扣库存 / 幂等键）、模拟支付，以及登录与会话
（`users`、`sessions` 两张表已经建好，M2 接上鉴权与 CSRF）。

## 9. 提交规范（Conventional Commits）

格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

| type | 用于 |
| --- | --- |
| `feat` | 新增用户可见的能力 |
| `fix` | 修复缺陷 |
| `docs` | 只改文档 |
| `style` | 只改格式（空格、分号），不影响逻辑 |
| `refactor` | 重构，既不新增功能也不修 bug |
| `perf` | 性能优化 |
| `test` | 增删改测试 |
| `build` | 依赖、构建脚本、打包配置 |
| `ci` | CI 配置与脚本 |
| `chore` | 杂务（脚手架、版本号、注释），不影响 src 与测试 |
| `revert` | 回滚某次提交 |

约定：

- `scope` 取模块或层：`api` `web` `contract` `docs` `deps` `tooling` `git`，跨模块可省略。
- `subject` 用祈使句描述结果（"增加"而不是"增加了"），不加句号，≤ 50 个字符。
- `body` 说明**为什么**改，不写"怎么改"（diff 已经说明）。
- 破坏性变更要在 type 后加 `!`，并在 footer 写 `BREAKING CHANGE: 说明`。
- 关联 issue 用 footer：`Closes #12`。

校验钩子已随仓库提供：

```powershell
git config core.hooksPath Schorder/.githooks   # 当前仓库根在 D:\Try_1
# 仓库迁到 Schorder/ 之后改为：git config core.hooksPath .githooks
```

不符合格式的提交会被拒绝；确有需要时用 `git commit --no-verify` 绕过。