# Schorder 架构设计（v3 · 评审稿）

> 定位：单校区档口点餐系统的结构基线——分层、18 张表、状态机、并发与 ADR。
> 范围：学生端 + 商家端 + 管理端 ｜ 状态：**待评审（v4）** ｜ 日期：2026-11-10
> 技术基线：React 19 + TS + Vite（前端）／ **Python 3.13 + FastAPI + SQLAlchemy 2.0**（后端）／ SQLite
> 安全基线：[`security.md`](./security.md)（强制项）｜ 契约：[`api-contract.md`](./api-contract.md)

## 所有权

| 内容 | 拥有者 |
| --- | --- |
| 分层、表结构、状态机、并发/事务、ADR | 本文 |
| 威胁模型、凭据与会话、授权基线、安全用例 | [`security.md`](./security.md)（强制） |
| 接口清单、错误码、请求/响应示例 | [`api-contract.md`](./api-contract.md) |

本文只定结构，不定安全策略；安全要求以 `security.md` 为准，接口字段以 `api-contract.md` 为准。

## 变更摘要

| 版本 | 关键变化 | 驱动 |
| --- | --- | --- |
| v1 → v2 | 认证改服务端会话；安全独立成文；三层授权 | 以安全为核心 |
| v2 → v3 | **后端由 Node/Express/Drizzle 改为 Python/FastAPI/SQLAlchemy**；契约改为 OpenAPI 生成 | 你的要求 |
| v3 → v4 | 确认 FastAPI；**管理端纳入本期**；确认单 worker 部署；新增档口审核流 | 你的决定 |

v3 不是"换个语言重写"：会话模型、状态机、CAS、幂等、三层授权全部保留，因为它们是**协议层与领域层**的设计，与语言无关。改变的只有三件事——HTTP 框架、ORM、契约产物的生成方向。

---

## 1. 设计目标与约束

### 1.1 质量属性

| 优先级 | 属性 | 落点 |
| --- | --- | --- |
| 1 | **安全** | `security.md`：三层授权、可吊销会话、strict 校验、审计 |
| 2 | 正确性 | 金额整数分、条件扣库存、状态机 CAS |
| 3 | 可维护性 | 分层单向依赖、模块边界、契约单一来源 |
| 4 | 可测试性 | 领域纯函数；`create_app()` 工厂 + TestClient |
| 5 | 性能 | 单机校园规模；不为性能牺牲以上四项 |

### 1.2 硬约束与实测环境

| 项 | 实测 |
| --- | --- |
| Python | 3.13.9（`D:\Python\python.exe`），`venv` / `sqlite3 3.50.4` 可用 |
| pip | 25.2，PyPI 可直连（fastapi 0.162.2 可见） |
| Node | v24.21.0（仅前端构建用） |
| 其他 | 无 Docker、无 psql、无 uv/poetry；Windows + PowerShell（`npm.cmd`） |

单机部署、SQLite 单写者、无真实支付/短信/对象存储。

### 1.3 主动回避的过度设计

| 不采用 | 理由 |
| --- | --- |
| 微服务 / 消息队列 / Redis | 单团队单部署单元；补偿用轮询，限流用内存 |
| CQRS / Event Sourcing | 订单是可枚举有限状态机，事件溯源收益为负 |
| GraphQL | 只有两端；REST + OpenAPI 更容易做安全评审 |
| Django 全家桶 | 其自带 auth/admin 会与「三层授权 + 策略函数」冲突，见 ADR-015 |
| 异步 ORM（asyncpg/aiosqlite） | SQLite 写串行，异步只增加复杂度不增吞吐，见 ADR-016 |
| 多租户 / 多校区 | 当前单校区，预留字段而非抽象 |

---

## 2. 系统上下文（C4-L1）

| 参与者 | 交互 | 安全边界 |
| --- | --- | --- |
| 学生 | 浏览、下单、模拟支付、查单、评价 | 仅触达自己的订单/地址/评价 |
| 商家 | 接单、出餐、菜品与营业管理 | 仅触达自己名下档口 |
| 管理员 | 档口审核、用户封禁、全局查单与强制处置、经营看板 | 跨档口读 + 受审计的写（破坏性操作必填理由） |

外部系统：**无**。支付为进程内模拟，不接短信、不接 OAuth、前端不加载任何第三方脚本。

---

## 3. 容器与部署视图（C4-L2）

```
┌──────────────────────────────┐
│ 浏览器（React SPA）           │  Cookie: __Host-sid (HttpOnly)
│  学生端 / 商家端 /merchant    │  Header: X-CSRF-Token
└──────────────┬───────────────┘
               │ HTTPS 同源 · JSON
┌──────────────▼───────────────────────────┐      ┌──────────────────────┐
│ uvicorn（1 worker）· FastAPI              │      │ SQLite（WAL）         │
│  /api/v1/*  ·  /assets/*  ·  /healthz     │─────>│ data/schorder.db     │
│  静态文件由 FastAPI StaticFiles 托管        │      └──────────────────────┘
└───────────────────────────────────────────┘
```

| 环境 | 形态 | 端口 |
| --- | --- | --- |
| 开发 | uvicorn `--reload`（8000）+ Vite（5173）代理 `/api` | 8000 / 5173 |
| 生产 | 单进程 uvicorn 托管 `apps/web/dist` + API，同源 | 8000 |
| 测试 | 临时 SQLite（`tmp_path`）+ 每用例事务回滚 | — |

**必须 1 个 worker**：限流计数在内存、SQLite 单写者；多 worker 会让限流失真并放大锁争用。这是显式约束，不是默认值。

---

## 4. 后端分层

### 4.1 依赖方向

```
API 层        FastAPI Router · Depends · Pydantic 出入参 · 响应模型
   ↓
服务层        Service：事务编排、策略校验、调用领域与仓储
   ↓
领域层        纯函数：定价 · 状态机 · 营业时间 · 授权策略 · 领域异常
   ↓
基础设施层    Repository（SQLAlchemy）· 引擎/会话 · Alembic · ID · 时钟 · 日志 · 密码学
```

**硬性禁令**（评审按此验收）：

- Router 里出现 SQL、业务判断、金额计算 → 不通过。
- Repository 里出现业务规则 → 不通过。
- Service 直接读 `Request`/返回 `Response` 对象 → 不通过（只接收 DTO 与 `Actor`）。
- 跨模块直调他人 Repository → 不通过（只走 Service）。
- 领域层 import SQLAlchemy / FastAPI / 日志 → 不通过。
- 涉及用户数据的查询缺少归属条件 → 不通过。

### 4.2 仓库结构（前后端 + 契约三层）

```
Schorder/
├─ apps/
│  ├─ api/                          # Python
│  │  ├─ pyproject.toml
│  │  ├─ alembic.ini
│  │  ├─ alembic/versions/          # 迁移脚本（入库、必评审）
│  │  ├─ src/schorder/
│  │  │  ├─ main.py                 # create_app()：中间件/路由/异常处理器装配
│  │  │  ├─ config.py               # pydantic-settings，缺失即启动失败
│  │  │  ├─ api/
│  │  │  │  ├─ deps.py              # get_session / current_actor / require_role / csrf
│  │  │  │  ├─ middleware.py        # request_id · 安全头 · 限流
│  │  │  │  ├─ errors.py            # DomainError → 统一错误体
│  │  │  │  └─ routers/{auth,catalog,orders,profile,merchant,admin}.py
│  │  │  ├─ services/{auth,catalog,order,review,merchant,admin}.py
│  │  │  ├─ domain/{pricing,state_machine,business_hours,policy,errors}.py
│  │  │  ├─ repositories/{auth,catalog,order,review}.py
│  │  │  ├─ db/{engine.py, session.py, models/*.py}
│  │  │  ├─ schemas/{common,auth,catalog,order}.py   # Pydantic 出入参
│  │  │  └─ infra/{security,ids,clock,logging,audit}.py
│  │  ├─ scripts/{seed.py, export_openapi.py}
│  │  └─ tests/{unit,integration,security}/
│  └─ web/                          # React + Vite
│     └─ src/{app,features,shared}/
├─ packages/contract/               # 由 OpenAPI 生成，禁止手改
│  ├─ openapi.json
│  └─ src/{types.ts, client.ts}
├─ scripts/{dev.ps1, gen-contract.ps1, verify.ps1}
└─ docs/
```

### 4.3 一次请求的链路（FastAPI 的 Depends 链）

```
POST /api/v1/orders
  request_id_middleware → security_headers
    Depends(get_session)            # 每请求一个 Session，退出时 commit/rollback
    Depends(current_actor)          # 读 sid Cookie → 查 sessions → 校验超时/吊销
    Depends(require_csrf)           # 非 GET：X-CSRF-Token 与 Origin
    Depends(require_role("student"))
    body: CreateOrderIn             # Pydantic extra="forbid"，多余字段直接 422
      → OrderService.create(session, actor, cmd)
          ├─ 幂等命中？→ 返回既有订单
          ├─ 载入档口/菜品/规格（查询即带状态与归属过滤）
          ├─ 校验营业、上架、库存、起送价、规格
          ├─ pricing.compute()（纯函数）
          ├─ 事务：条件扣库存 → 插订单/明细/日志/支付意图
          └─ 返回聚合
      → OrderOut（response_model 白名单序列化）→ 201
  DomainError → { code, message, details?, traceId }；未知异常 → 500 且不泄露内部信息
```

`response_model` 是做 **DTO 白名单**的原生位置：多查出来的列不会自动出现在响应里，比手工挑字段更不容易漏。

---

## 5. 模块划分

| 模块 | 职责 | 拥有的表 |
| --- | --- | --- |
| auth | 注册、登录、登出、会话生命周期、锁定 | `users`, `sessions`, `security_events`, `login_attempts` |
| catalog | 分类、档口、菜单、营业判定、搜索 | `categories`, `stalls`, `stall_business_hours`, `menu_groups`, `dishes`, `dish_option_groups`, `dish_options` |
| orders | 预览、下单、支付、取消、状态流转、超时补偿 | `orders`, `order_items`, `order_status_logs`, `payments` |
| reviews | 评价与评分聚合 | `reviews` |
| merchant | 商家资料、菜品维护、订单队列 | 复用 catalog/orders 的写能力 |
| admin | 档口审核、用户状态、全局订单处置、看板聚合 | 只做编排：写操作一律调用所属模块的 Service，自身不直接碰表 |

跨模块只调 Service；`orders` 通过 catalog 的只读接口取菜品。

**管理端的关键纪律**：管理员的"强制取消订单"不是在 admin 模块里直接 `UPDATE orders`，而是调用 `OrderService.force_cancel(order_id, reason)`——状态机、库存回补、退款记录、审计日志只有一条实现路径。否则同一业务规则会出现两份，且必然分叉。

---

## 6. 数据模型

### 6.1 ORM 选型：SQLAlchemy 2.0 + Alembic

| 维度 | SQLAlchemy 2.0（选） | Django ORM | Peewee / Tortoise |
| --- | --- | --- | --- |
| 类型与 IDE 支持 | `Mapped[]` 注解，mypy 严格模式可查 | 弱，需插件 | 一般 |
| 事务控制 | `Session` 显式管理，`rowcount` 可判 CAS | `atomic()` 够用但隐式 | 一般 |
| 迁移 | Alembic，脚本可评审 | 自带，但与应用耦合 | 各自方案 |
| 与 FastAPI 配合 | 官方推荐组合 | 需 Django 全家桶 | 生态较小 |

选它的理由：**条件和更新能拿到 `rowcount`**（本项目三条核心不变量都依赖它：库存扣减、状态 CAS、乐观锁），且 `Mapped[]` 让 mypy 能在 CI 里挡住字段拼写错误。

**建模规则**：

1. `db/models/` 是唯一表结构来源；禁止在服务里写 DDL。
2. 迁移只用 Alembic，**autogenerate 后必须人工审阅**（它检测不到部分约束变更）；禁止 `alembic stamp head` 掩盖差异。
3. 所有列显式 `nullable=False`，除非有明确 NULL 语义；金额列加 `CheckConstraint`。
4. 唯一约束与索引在 `__table_args__` 声明，迁移里必须可见。
5. Repository 返回领域对象（dataclass 或 ORM 实体），不把 `Session` 泄漏到上层。
6. 禁止拼接 SQL 字符串；需要表达式时用 `text()` 且必须绑定参数。

### 6.2 建模原则

| 主题 | 决策 | 理由 |
| --- | --- | --- |
| 主键 | `TEXT` UUIDv7（`uuid6` 库或自实现） | 不泄露业务量、时间有序、索引局部性好 |
| 金额 | `Integer` 分，列名 `*_cents` | 杜绝浮点误差 |
| 时间 | `TEXT` ISO-8601 UTC（毫秒） | 可读、可字典序比较；业务时区固定 `Asia/Shanghai` |
| 枚举 | `String` + `CheckConstraint`（或 Python `StrEnum` 校验） | 类型层与 DB 层双约束 |
| 快照 | 订单行冗余名称/单价/规格 JSON | 改价改名不影响历史单 |
| 删除 | 状态位，不物理删除 | 可审计；菜品用 `off_shelf` |
| 并发 | 状态 CAS + `version` 乐观锁 | 见 §9 |

### 6.3 表清单（18 张）

| 表 | 作用 | 关键列 |
| --- | --- | --- |
| `users` | 账号 | `phone`(unique) `password_hash` `password_algo` `role` `status` |
| `sessions` | 服务端会话 | `token_hash`(unique) `user_id` `csrf_token` `idle_expires_at` `absolute_expires_at` `revoked_at` `ip_hash` `ua_hash` |
| `security_events` | 安全审计（只追加） | `type` `actor_id` `ip_hash` `result` `reason` |
| `login_attempts` | 失败计数与锁定 | `key` `count` `locked_until` |
| `addresses` | 地址簿 | `user_id` `building_code` `room` `is_default` |
| `categories` | 档口分类 | `name` `sort_order` |
| `stalls` | 档口 | `owner_user_id` `min_order_cents` `delivery_fee_cents` `rating_sum` `rating_count` `monthly_sales` `status`(pending/active/suspended) `reviewed_by` `reviewed_at` |
| `stall_business_hours` | 营业时段 | `stall_id` `weekday` `open_time` `close_time`（支持跨夜） |
| `menu_groups` | 菜单分组 | `stall_id` `name` `sort_order` |
| `dishes` | 菜品 | `stall_id` `price_cents` `stock` `status` `sold_count` `version` |
| `dish_option_groups` | 规格组 | `dish_id` `required` `min_select` `max_select` |
| `dish_options` | 规格项 | `group_id` `price_delta_cents` `is_available` |
| `orders` | 订单主表 | 见 6.4 |
| `order_items` | 明细快照 | 见 6.5 |
| `order_status_logs` | 状态审计 | `from_status` `to_status` `actor_type` `actor_id` `reason` |
| `payments` | 支付/退款（模拟） | `order_id` `provider` `status` `transaction_no` |
| `reviews` | 评价（一单一评） | `order_id`(unique) `rating` `content` |
| `alembic_version` | 迁移版本 | 由 Alembic 维护 |

### 6.4 订单模型（节选）

```python
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_no: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    stall_id: Mapped[str] = mapped_column(ForeignKey("stalls.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    fulfillment_type: Mapped[str] = mapped_column(String(10), nullable=False)
    address_snapshot_json: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str] = mapped_column(String(50), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    tableware_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_ready_at: Mapped[str | None] = mapped_column(String(24))
    remark: Mapped[str | None] = mapped_column(String(100))
    items_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    packing_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payable_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    cancel_reason: Mapped[str | None] = mapped_column(String(200))
    expires_at: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[str] = mapped_column(String(24), nullable=False)
    paid_at: Mapped[str | None] = mapped_column(String(24))
    accepted_at: Mapped[str | None] = mapped_column(String(24))
    ready_at: Mapped[str | None] = mapped_column(String(24))
    completed_at: Mapped[str | None] = mapped_column(String(24))
    cancelled_at: Mapped[str | None] = mapped_column(String(24))
    updated_at: Mapped[str] = mapped_column(String(24), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="ux_orders_idem"),
        Index("ix_orders_user_time", "user_id", "created_at"),
        Index("ix_orders_stall_state", "stall_id", "status", "created_at"),
        Index("ix_orders_state_exp", "status", "expires_at"),
        CheckConstraint("payable_cents >= 0", name="ck_orders_payable"),
        CheckConstraint("items_amount_cents >= 0 AND discount_cents >= 0", name="ck_orders_fee"),
        CheckConstraint(
            "fulfillment_type = 'pickup' OR address_snapshot_json IS NOT NULL",
            name="ck_orders_delivery_addr",
        ),
    )
```

### 6.5 明细快照

```python
class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    dish_id: Mapped[str] = mapped_column(ForeignKey("dishes.id"))    # 仅溯源
    dish_name: Mapped[str] = mapped_column(String(80), nullable=False)   # 快照
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    options_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_item_qty"),)
```

### 6.6 迁移策略（Alembic）

- `alembic revision --autogenerate -m "..."` → **人工审阅生成的脚本**（补约束、改索引、写回滚说明）。
- 启动时只**校验**版本一致，不自动迁移生产库：`current != head` → 拒绝启动并打印差异。
- 开发态可用 `alembic upgrade head`（脚本 `npm run db:migrate`）。
- 迁移前强制 `VACUUM INTO` 备份；已应用的迁移禁止修改。
- 种子数据独立脚本、固定 ID、可重复执行。

---

## 7. 关键业务流程

### 7.1 下单

```python
def create_order(session: Session, actor: Actor, cmd: CreateOrderCommand) -> OrderDetail:
    with session.begin():
        if existing := order_repo.find_by_idempotency_key(session, actor.id, cmd.idempotency_key):
            return existing                                    # 幂等命中

        stall = catalog_repo.get_sellable_stall(session, cmd.stall_id)
        dishes = catalog_repo.get_dishes_for_order(session, stall.id, cmd.items)
        priced = compute_pricing(stall=stall, dishes=dishes, cmd=cmd)   # 纯函数

        if priced.items_amount_cents < stall.min_order_cents:
            raise MinOrderNotReached(shortfall_cents=stall.min_order_cents - priced.items_amount_cents)

        for line in priced.lines:
            result = session.execute(
                update(Dish)
                .where(Dish.id == line.dish_id, Dish.status == "on_sale", Dish.stock >= line.qty)
                .values(stock=Dish.stock - line.qty, sold_count=Dish.sold_count + line.qty)
            )
            if result.rowcount != 1:
                raise StockConflict(dish_id=line.dish_id)      # 抛异常 → 整单回滚

        return order_repo.insert_with_items(session, priced, cmd, actor)
```

- 并发同幂等键：唯一索引兜底，捕获 `IntegrityError` → `rollback()` → 回查返回既有订单。
- 金额只由 `compute_pricing` 产出；请求体里任何价格字段会被 Pydantic `extra="forbid"` 直接拒绝。

### 7.2 模拟支付

事务内 CAS `pending_payment → paid`；`rowcount == 0` 即 409（已支付/已取消/已过期），不存在"读到旧状态再写"的窗口。

### 7.3 商家状态流转

```python
def transition(session: Session, actor: Actor, order_id: str, to: OrderStatus, reason: str | None) -> Order:
    with session.begin():
        order = order_repo.get_for_merchant(session, order_id, actor.id)   # 归属内联在 WHERE
        assert_transition(order.status, to, order.fulfillment_type)        # 纯函数抛 DomainError
        policy.require(actor, "order:transition", order)
        updated = order_repo.cas_status(session, order.id, order.status, to, reason=reason)
        order_repo.append_status_log(session, order, to, actor, reason)
        return updated
```

```python
def cas_status(session, order_id: str, expected: str, new: str, **patch) -> None:
    result = session.execute(
        update(Order)
        .where(Order.id == order_id, Order.status == expected)
        .values(status=new, updated_at=utc_now_iso(), **patch)
    )
    if result.rowcount != 1:
        raise OrderInvalidTransition(from_status=expected, to_status=new)
```

### 7.4 超时取消（补偿任务）

`apscheduler`（进程内）或 FastAPI 启动时的 `asyncio` 循环，每 60 秒：

```
查 status='pending_payment' AND expires_at <= now LIMIT 100
  → 逐条 CAS 为 cancelled(PAYMENT_TIMEOUT)
  → CAS 成功才回补库存 → 写日志
```

单实例直接跑；多实例需选主或改外部调度（ADR-008）。

### 7.5 评价

仅 `completed` 且未评价可写；插评价与更新 `stalls.rating_sum/rating_count` 同事务；均分读时计算。

---

## 8. 订单状态机

| 状态 | 含义 | 终态 |
| --- | --- | --- |
| `pending_payment` | 待支付 | 否 |
| `paid` | 已支付待接单 | 否 |
| `accepted` | 已接单 | 否 |
| `preparing` | 备餐中 | 否 |
| `ready` | 待自提 | 否 |
| `delivering` | 配送中 | 否 |
| `completed` | 已完成 | 是 |
| `cancelled` | 已取消（含超时） | 是 |

| from | to | 触发者 | 守卫 |
| --- | --- | --- | --- |
| pending_payment | paid | 学生 | 未过期、金额一致 |
| pending_payment | cancelled | 学生 / 系统 | 学生仅本人 |
| paid | accepted | 商家 | 归属校验 |
| paid | cancelled | 学生 / 商家 | 学生：接单前；商家：拒单需理由 |
| accepted | preparing | 商家 | — |
| accepted | cancelled | 商家 | 需理由 |
| preparing | ready | 商家 | 自提单 |
| preparing | delivering | 商家 | 配送单 |
| ready | completed | 商家 | — |
| delivering | completed | 商家 | — |
| paid / accepted / preparing | cancelled | 管理员 | 强制取消，必填理由；已支付则写模拟退款记录 |

实现为常量字典 `TRANSITIONS: dict[OrderStatus, dict[OrderStatus, Guard]]`，不是散落的 `if`；新增状态先改表再补测试。

---

## 9. 一致性、并发与事务

| 问题 | 方案 |
| --- | --- |
| 超卖 | `UPDATE ... WHERE stock >= qty` + `rowcount == 1` 校验，事务内回滚 |
| 重复下单 | 唯一索引 `(user_id, idempotency_key)`；`IntegrityError` → rollback → 回查 |
| 状态竞态 | CAS：`update().where(status == expected)`，`rowcount == 0` → 409 |
| 商家并发编辑 | `version` 乐观锁：`where(version == v)`，冲突 409 |
| 事务边界 | Service 内 `with session.begin():`；Session 由依赖注入按请求创建/释放 |
| SQLite 锁 | WAL + `busy_timeout=5000`；写事务用 `BEGIN IMMEDIATE` 避免读升级写时死锁；读事务保持 DEFERRED |
| Session 泄漏 | `get_session` 依赖 `try/finally` 关闭；异常路径 rollback |
| 会话写放大 | 每请求只读；`last_seen` 续期 60 秒节流 |
| 多 worker | 禁止：限流在内存、SQLite 单写者 |

**BEGIN IMMEDIATE 的落地方式**（容易写错，单独说明）：通过 `Session` 的 `after_begin` 事件或自定义 `Session` 子类，仅在写事务开始前执行 `BEGIN IMMEDIATE`；不要对所有事务一刀切，否则会串行化全部读请求。

**明确不做**：分布式锁、两阶段提交、事件总线。

---

## 10. API 设计原则

细节见 [`api-contract.md`](./api-contract.md)。

| 原则 | 约定 |
| --- | --- |
| 版本 | `/api/v1`，破坏性变更升版本 |
| 资源 | 复数名词；状态流转走 `POST /orders/:id/transition`，绝不 `PATCH status` |
| 状态码 | 200/201/204；400/422 参数、401 未认证、403 越权/CSRF、404 不存在（含无权）、409 冲突、423 锁定、429 限流 |
| 响应包 | `{ ok, data, meta? }` / `{ ok:false, error:{ code, message, details?, traceId } }` |
| 错误码 | 稳定字符串，前端按 code 映射文案 |
| 分页 | 游标制 + **HMAC 签名**（防篡改游标注入） |
| 幂等 | 订单、支付必带 `Idempotency-Key` |
| 写操作 | 必须带 `X-CSRF-Token`，并校验 `Origin` |
| 契约 | OpenAPI 由 FastAPI 生成 → 前端生成类型与客户端（见 §12.6） |
| 缓存 | 含 PII 响应 `no-store` |

---

## 11. 安全

完整基线见 [`security.md`](./security.md)。Python 侧的落地对照：

| 面 | v3 实现 |
| --- | --- |
| 会话 | 不透明令牌，DB 存 SHA-256；`HttpOnly + Secure + SameSite=Lax`；30m 闲置 / 12h 绝对；轮换与全体吊销 |
| CSRF | 自定义头 + `Origin` 校验（依赖 `require_csrf`） |
| 授权 | 路由守卫 → `policy.require()` → 查询级 `WHERE owner_id = :actor` |
| 密码 | `argon2-cffi`（Argon2id），降级 `hashlib.scrypt` |
| 输入 | Pydantic `model_config = ConfigDict(extra="forbid")` |
| 输出 | `response_model` 白名单 + 手机号脱敏 |
| 依赖 | `pip-audit` + `pip-compile` 锁定 + `--require-hashes`（可选） |
| 审计 | `security_events` 只追加（SQLite 触发器禁 UPDATE/DELETE） |

---

## 12. 前端架构

### 12.1 路由

| 路由 | 页面 | 护栏 |
| --- | --- | --- |
| `/` `/stalls` `/stalls/:id` `/search` | 浏览 | 公开 |
| `/cart` | 购物车 | 公开（本地态） |
| `/checkout` `/orders` `/orders/:id` | 结算与订单 | 需登录 |
| `/me` `/me/addresses` | 个人中心 | 需登录 |
| `/login` `/register` | 登录注册 | 未登录 |
| `/merchant` `/merchant/orders` `/merchant/menu` `/merchant/settings` | 商家端 | 需 `merchant` 角色 |
| `/admin` `/admin/stalls` `/admin/users` `/admin/orders` | 管理端 | 需 `admin` 角色 |

`CustomerLayout` / `MerchantLayout` / `AuthLayout`；全部懒加载。

### 12.2 状态分层

| 类型 | 载体 | 规则 |
| --- | --- | --- |
| 会话 | HttpOnly Cookie + 内存 `user`/`csrfToken` | 启动调 `GET /auth/session`；**不进 localStorage** |
| 服务端状态 | TanStack Query | 不复制进 Zustand |
| 客户端状态 | Zustand | 购物车持久化，带版本与迁移 |
| 表单 | React Hook Form + Zod | Zod 只做 UX 级校验；**服务端才是权威** |

### 12.3 目录

```
apps/web/src/
├─ app/{router.tsx, providers.tsx, layouts/}
├─ features/{auth,catalog,cart,checkout,orders,profile,merchant}/
└─ shared/{ui/, api/{client.ts,errors.ts,queryKeys.ts}, lib/}
```

### 12.4 请求层

- `client.ts`：`credentials: 'include'`、注入 `X-CSRF-Token` 与 `X-Request-Id`、超时、错误归一化为 `ApiError`。
- 401 → 清空内存用户态并跳登录；403 CSRF → 重新拉 `/auth/session` 后重试一次。
- 写操作按钮 `pending` 禁用（与后端幂等双保险）。
- 错误文案按 `code` 映射，禁止直接展示后端 `message`。

### 12.5 样式与规范

Tailwind v4 + `@theme` 令牌；移动优先（375px 基准，`sm 640 / lg 1024`）；组件内置三态；对话框焦点陷阱 + `aria-live`。

### 12.6 契约生成（跨语言的关键）

```
Pydantic 模型（唯一事实来源）
   → FastAPI 生成 /api/v1/openapi.json
   → scripts/export_openapi.py 导出到 packages/contract/openapi.json
   → openapi-typescript 生成 packages/contract/src/types.ts
   → 前端 api 层用这些类型标注请求/响应
```

- CI 校验：重新生成后 `git diff --exit-code packages/contract`，不一致即失败（防止后端改了字段、前端没跟上）。
- `openapi.json` 与生成物**入库**，评审时能直接看到接口变化。
- 前端不手写接口类型；手写一律视为 bug。

---

## 13. 可观测性与运维

| 项 | 方案 |
| --- | --- |
| 日志 | `structlog` JSON：`request_id` `user_id` `route` `status` `duration_ms`；手机号脱敏；禁记令牌 |
| 追踪 | 中间件生成/透传 `X-Request-Id`，贯穿日志与错误响应 |
| 健康 | `/healthz`（存活）、`/readyz`（`SELECT 1` + Alembic 版本一致） |
| 备份 | 每日 `VACUUM INTO` + 加密，保留 7 天，季度恢复演练 |
| 清理 | 每日清理过期会话、90 天前 `login_attempts` |
| 关闭 | uvicorn `--graceful-timeout`，`lifespan` 中关引擎 |
| 配置 | `pydantic-settings` 读 env，缺失/类型错即启动失败；`.env.example` 入库 |

---

## 14. 测试策略

| 层 | 覆盖 | 工具 | 目标 |
| --- | --- | --- | --- |
| 单元 | 定价、状态机全迁移矩阵、营业时间（跨夜）、policy 矩阵 | pytest | 领域层 ≥90% |
| 集成 | 下单/支付/取消/超时/越权/限流 | pytest + `TestClient` + 临时 SQLite | 每接口 ≥1 正例 + 2 反例 |
| 安全 | `security.md` §10 的 21 条 | pytest（独立目录） | 全绿才合并 |
| 契约 | 导出 OpenAPI 后比对生成物 | CI diff | 无 drift |
| E2E | 学生主流程、商家接单流程 | Playwright | 2 条稳定通过 |

测试库用 `tmp_path` 建临时文件 + 每用例事务回滚；种子数据固定，含「售罄/打烊/规格加价/满减」四种边界。

---

## 15. 工程规范

### 15.1 后端（Python）

| 项 | 规定 |
| --- | --- |
| 版本 | 3.13；`pyproject.toml` + venv；依赖锁定（pip-compile 产出 `requirements.lock`） |
| 类型 | mypy `strict`，`disallow_untyped_defs`；公共函数必须带注解 |
| 风格 | `ruff check` + `ruff format`（替代 black/isort/flake8） |
| 命名 | 模块 snake_case；类 PascalCase；常量 UPPER；DB 列 snake_case；API JSON camelCase（Pydantic alias 在边界转换） |
| 错误 | 领域异常继承 `DomainError(code, http_status)`；禁止裸 `Exception` 抛到 API 层 |
| 日志 | 禁 `print`；统一 `structlog.get_logger()` 绑 `request_id` |
| SQL | 只用 SQLAlchemy 表达式；`text()` 必须绑定参数，并在 PR 说明 |
| 事务 | `with session.begin():`；禁止在 Service 外 commit |
| 提交 | Conventional Commits；一次提交一个意图 |
| 评审 | PR 必过 CI + `security.md` §11 清单 |

### 15.2 前端（TS）

`strict` + `noUncheckedIndexedAccess`；禁 `any`；`ruff` 的对位是 ESLint + Prettier；文件 kebab-case；跨 feature 只能走 `api.ts`。

### 15.3 CI

```
api:  ruff check · ruff format --check · mypy · pytest（含安全用例） · pip-audit · 导出 OpenAPI diff
web:  eslint · tsc --noEmit · vitest · build
e2e:  Playwright（单独 job）
```

`scripts/verify.ps1` 一键跑全部，供本地与 CI 共用。

---

## 16. 里程碑

| 里程碑 | 落点 | 交付 |
| --- | --- | --- |
| M0 | §4 分层、§6.6 Alembic、§13 日志健康、§12.6 契约管线 | venv + FastAPI 骨架 + Alembic + Vite + `/healthz` + 契约生成跑通 |
| M1 | §6 数据模型、§10 契约 | 建表 + 种子 + 浏览链路 |
| M2 | §7.1、§9、§12.4 | 购物车 + 结算 + 下单 + 模拟支付 |
| M3 | §7.4、§8 | 订单闭环 + 补偿任务 |
| M4 | §7.3、§11 授权 | 商家端 + 菜品管理 |
| M5 | §5 admin、§8 审核流 | 管理端：档口审核 + 用户封禁 + 全局订单处置 + 看板 |
| M6 | §14、§13 | 安全矩阵 + E2E + 部署文档 |

总期约 **20 个工作日**（含 Python 脚手架 +1 天、管理端 +3 天）。若管理端一期只做「只读看板 + 档口审核」，可压到 18 天，用户封禁与强制处置放到下一迭代。

---

## 17. 架构决策记录（ADR）

| ID | 决策 | 替代 | 后果 |
| --- | --- | --- | --- |
| ADR-001 | 四层分层 | 纯 MVC | 多两目录，换领域可单测 |
| ADR-002 | SQLite + WAL | PostgreSQL | 零安装；单写者，扩容改仓储层 |
| ADR-003 | 金额整数分 | 浮点/Decimal | 无精度问题 |
| ADR-004 | 订单行快照 | 关联查历史价 | 历史准确，存冗余 |
| ADR-005 | 服务端不透明会话 | JWT + 刷新令牌 | 可即时吊销、JS 不可读；每请求一次主键查询 |
| ADR-006 | CAS 条件更新 | 分布式锁 / 行锁 | 无锁无死锁；迁移必须走同一函数 |
| ADR-007 | 幂等落在订单唯一索引 | 通用幂等表 | 少一张表；只覆盖订单类接口 |
| ADR-008 | 轮询 + 定时补偿 | WebSocket / MQ | 简单可解释；状态延迟 ≤15s |
| **ADR-009** | **SQLAlchemy 2.0 + Alembic** | Django ORM / 手写 SQL | 可拿 `rowcount` 做 CAS；迁移需人工审阅 |
| **ADR-010** | **OpenAPI 生成前端类型（单向）** | 双端各自维护 schema | 消除 drift；代价是构建链多一步 |
| ADR-011 | feature 化前端 + Query/Zustand 分工 | Redux 全局 store | 边界清晰；两类状态需理解 |
| ADR-012 | CSRF：自定义头 + Origin 校验 | 双提交 Cookie | 简单且覆盖表单攻击 |
| ADR-013 | Pydantic `extra="forbid"` + `response_model` | 宽松模型 + 手工过滤 | 未知字段即失败；前端需跟契约 |
| ADR-014 | `security_events` 只追加（触发器） | 普通表 | 防篡改；清理需专门脚本 |
| **ADR-015** | **FastAPI（已定）；管理端用 React 自建** | Django + DRF + Django Admin | OpenAPI 原生、与三层授权一致；管理端 +3 天，但不引入第二套权限模型 |
| **ADR-016** | **同步 SQLAlchemy（线程池）而非异步 ORM** | asyncpg/aiosqlite | 少一层 async 传染；SQLite 写串行，异步无收益 |

---

## 18. 已知风险与技术债

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| SQLite 单写者 | 高峰排队 | 写事务毫秒级；压测 50 并发下单；busy_timeout |
| 单 worker 限制（已接受） | 无法横向扩 | 写入部署约束；扩容需先换 DB 与限流后端 |
| 管理端权限过大 | 误操作或滥用 | 破坏性操作必填理由 + 全量审计；一期不做批量操作 |
| 审核流引入更多档口状态 | 状态判断散落 | 三态 `pending/active/suspended` 收敛到状态机，禁止任意置位 |
| Alembic autogenerate 漏检 | 迁移与模型不一致 | 强制人工审阅 + 启动版本校验 + 集成测试跑真实迁移 |
| Python 同步端点占线程池 | 高并发下排队 | 单机校园规模足够；压测确认 p95 |
| mypy 对 SQLAlchemy 2.0 的类型推断 | 偶发 `Any` | 开启插件；对动态属性显式注解 |
| 前后端分离构建链 | M0 复杂度上升 | 一键 `verify.ps1`；契约生成纳入 CI |
| `style-src 'unsafe-inline'` | CSP 削弱 | 列技术债，改 CSS 变量后移除 |
| 测试欠账 | 回归 | 价格/状态机/越权三类不可省 |

---

## 19. 评审重点（已定项不再讨论）

**已定**：FastAPI（ADR-015）、单 worker（部署约束）、管理端纳入本期。

剩余分歧点，按我判断的优先级排序：

1. **管理员的权限边界**：强制取消 / 封禁是一票通过，还是要双人复核？后者要加审批流（约 +1 天），但能挡住单人误操作。
2. **档口审核流**：注册即建档口并置 `pending`（表单少），还是"申请 → 审核 → 开通"两步（更像真实业务，多一套状态与页面）。
3. **管理端一期范围**：20 天全量，还是 18 天的「看板 + 审核」最小版，用户封禁与强制处置延后。
4. **同步 SQLAlchemy + 线程池**：不为异步而异步，但线程池是硬上限，接受吗。
5. **契约单向生成**：改接口必须先改后端，这个纪律会不会拖慢前端联调。
6. **三层授权是否冗余**：守卫 + policy + 查询过滤。
7. **monorepo（npm workspaces + Python venv 两套工具链）**：3 人以下是否值得。
8. **`security_events` 用触发器禁改**：多一层 DB 魔法，值不值。

---

## 20. 待你决策的开放问题

已定：管理端纳入本期、FastAPI、单 worker。

1. 配送费是否按楼栋阶梯？需要则 `delivery_fee` 升级为规则表。
2. 是否需要完整「预约出餐」（`expectedReadyAt`）？
3. 部署目标：本地 / 校园服务器 / 云主机？（决定是否写 Nginx 与 systemd 配置）
4. 「设备指纹变化仅告警不踢人」是否接受？
5. 管理端是否需要导出（订单 CSV / 商家对账单）？会新增文件下载与下载权限这一面。

---

## 21. 下一步

1. 你按 §19 挑刺，尤其第 1–3 条（管理端权限边界、审核流形态、一期范围），它们直接决定 M5 的设计与工期。
2. 定稿后按 M0 → M6 交付，每个里程碑给可运行提交点与 `verify.ps1` 输出。