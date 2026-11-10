# Schorder API 契约 v2（评审稿）

> 定位：`/api/v1` 的线上格式与接口清单——请求头、响应包、错误码、分页、幂等。
> 配套：[`architecture.md`](./architecture.md) ｜ [`security.md`](./security.md)
> 状态：**待评审** ｜ Base URL：`/api/v1` ｜ 编码：`application/json; charset=utf-8`
>
> **v2 变更**：认证由 Bearer JWT 改为服务端会话 Cookie；所有写操作增加 `X-CSRF-Token`；新增会话类错误码。

## 所有权

| 内容 | 拥有者 |
| --- | --- |
| 接口清单、字段、错误码、请求/响应示例 | 本文 |
| 分层、表结构、状态机、并发 | [`architecture.md`](./architecture.md) |
| 威胁模型、会话/CSRF 机制、安全验收用例 | [`security.md`](./security.md) |

本文只定义"线上长什么样"；安全机制与验收在 `security.md`，数据结构在 `architecture.md`。三处冲突时：字段以本文为准，安全要求以 `security.md` 为准。

---

## 1. 通用约定

### 1.1 请求头

| 头 | 必填 | 说明 |
| --- | --- | --- |
| `Cookie: __Host-sid` | 需登录接口 | 会话令牌，32 字节随机值；HttpOnly + Secure + SameSite=Lax，JS 不可读 |
| `X-CSRF-Token` | **所有非 GET 请求** | 来自 `GET /auth/session`；缺失或不匹配 → 403 `CSRF_TOKEN_INVALID` |
| `Origin` | 非 GET 请求（可选，服务端校验） | 必须等于配置站点源；缺失时回退校验 `Referer` |
| `Content-Type: application/json` | 有 body 时 | 其他类型直接 415 |
| `X-Request-Id` | 否 | 客户端可传入，缺省由服务端生成 UUID；原样回传 |
| `Idempotency-Key` | 下单、支付必填 | 建议 UUIDv4；同一用户 24 小时内复用同一 key 返回同一结果 |

### 1.2 成功响应包

```json
{
  "ok": true,
  "data": { },
  "meta": { "nextCursor": "eyJ0IjoiMjAyNi0xMS0xMFQxMTo0OTo1OS4xMjNafCIsImlkIjoiMDE5..." }
}
```

- `data` 为对象或数组；无返回体时 `data: null` 且 HTTP 204。
- `meta` 仅分页接口出现。

### 1.3 失败响应包

```json
{
  "ok": false,
  "error": {
    "code": "ORDER_INVALID_TRANSITION",
    "message": "订单当前状态不允许该操作",
    "details": { "from": "completed", "to": "paid" },
    "traceId": "7f3c8c1e-9d0b-4a5e-8a55-2c1f0e9a6b31"
  }
}
```

前端只依赖 `code`，`message` 是兜底文案，`traceId` 用于对日志。

### 1.4 数据格式

| 类型 | 格式 | 示例 |
| --- | --- | --- |
| 金额 | 整数「分」，字段名后缀 `Cents` | `1280` 表示 12.80 元 |
| 时间 | ISO-8601 UTC 带毫秒 | `"2026-11-10T11:49:59.123Z"` |
| ID | UUIDv7 字符串 | `"0192f3c1-..."` |
| 手机号 | 11 位，`^1[3-9]\d{9}$` | `"13800138000"` |

### 1.5 分页

- 请求：`?limit=20&cursor=<opaque>`，`limit` 默认 20、上限 50。
- 响应：`data: [...]` + `meta.nextCursor`（为 `null` 表示到底）。
- 游标编码 `(createdAt, id)`，对客户端不透明，禁止解析。

### 1.6 幂等语义

| 场景 | 行为 |
| --- | --- |
| 同 key + 同参数 | 返回首次结果（HTTP 200，非 201） |
| 同 key + 不同参数 | 409 `IDEMPOTENCY_KEY_REUSED` |
| 未带 key | 400 `IDEMPOTENCY_KEY_REQUIRED` |

---

## 2. 错误码目录

| HTTP | code | 触发场景 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 参数缺失/格式错误（`details.fields` 给出字段级信息） |
| 400 | `REASON_REQUIRED` | 审核驳回、封禁、强制取消等操作未提供理由 |
| 400 | `IDEMPOTENCY_KEY_REQUIRED` | 下单/支付缺少幂等键 |
| 401 | `SESSION_EXPIRED` | 会话缺失、闲置超时或绝对过期 |
| 401 | `SESSION_REVOKED` | 会话已吊销（登出、改密、管理员封禁） |
| 401 | `AUTH_INVALID_CREDENTIALS` | 手机号或密码错误（不区分具体原因，防枚举） |
| 403 | `CSRF_TOKEN_INVALID` | 缺少/不匹配 `X-CSRF-Token`，或 `Origin` 校验失败 |
| 403 | `FORBIDDEN` | 角色不足 |
| 404 | `RESOURCE_NOT_FOUND` | 资源不存在、已下架，**或无权访问**（三者不区分，防枚举） |
| 409 | `ORDER_INVALID_TRANSITION` | 状态机不允许的迁移 |
| 409 | `ORDER_ALREADY_PAID` | 重复支付 |
| 409 | `ORDER_EXPIRED` | 超过支付截止时间 |
| 409 | `STOCK_CONFLICT` | 库存不足（`details.dishId`） |
| 409 | `MENU_CHANGED` | 菜品下架/规格变更导致无法下单 |
| 409 | `EDIT_CONFLICT` | 乐观锁版本冲突 |
| 409 | `IDEMPOTENCY_KEY_REUSED` | 同 key 不同参数 |
| 409 | `STALL_NOT_PENDING` | 审核操作的目标档口不处于 `pending` |
| 409 | `ADMIN_CANNOT_DISABLE_SELF` | 管理员尝试封禁自己 |
| 422 | `MIN_ORDER_NOT_REACHED` | 未达起送价（`details.shortfallCents`） |
| 422 | `STALL_CLOSED` | 档口打烊或停业 |
| 422 | `OPTION_SELECTION_INVALID` | 规格必选未选 / 超选 |
| 422 | `ADDRESS_REQUIRED` | 配送单未提供地址 |
| 423 | `ACCOUNT_LOCKED` | 连续失败触发锁定（`details.retryAfterSeconds`） |
| 429 | `RATE_LIMITED` | 触发限流（`details.retryAfterSeconds`） |
| 500 | `INTERNAL_ERROR` | 未预期异常（不暴露堆栈） |

---

## 3. 认证（`/auth`）

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 注册（默认 `student`），成功后直接建会话 | 公开 |
| POST | `/auth/login` | 登录，签发会话 Cookie 并返回 CSRF 令牌 | 公开 |
| GET | `/auth/session` | 当前会话摘要（用户 + CSRF），前端启动时调用 | Cookie |
| POST | `/auth/logout` | 吊销当前会话并清 Cookie | Cookie + CSRF |
| POST | `/auth/password` | 修改密码，**吊销该用户全部会话** | 登录 + CSRF |

**POST /auth/login**

```http
POST /api/v1/auth/login
Content-Type: application/json

{ "phone": "13800138000", "password": "S3cret!pass" }
```

```json
200 OK
Set-Cookie: __Host-sid=v2Xb9...; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=43200

{
  "ok": true,
  "data": {
    "user": { "id": "019...", "nickname": "小张", "role": "student", "phone": "138****8000" },
    "csrfToken": "cZ1k...",           // 前端存内存，写入型请求通过 X-CSRF-Token 回传
    "idleExpiresAt": "2026-11-10T12:20:00.000Z",
    "absoluteExpiresAt": "2026-11-10T23:50:00.000Z"
  }
}
```

**约束**：

- 失败一律 `AUTH_INVALID_CREDENTIALS`，且对不存在的账号也执行一次等价哈希以抹平时序差异。
- 同手机号 15 分钟内失败 5 次 → 锁定 15 分钟并逐次递增退避，返回 `423 ACCOUNT_LOCKED`。
- 登录成功即**轮换会话**：旧 sid 立即吊销，防会话固定攻击。
- Cookie 在开发环境用 `sid`（httpOnly/SameSite=Lax），生产环境用 `__Host-sid`（强制 Secure + 无 Domain）。
- 响应头 `Cache-Control: no-store`。

---

## 4. 目录（`/catalog`）

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| GET | `/categories` | 档口分类 | 公开 |
| GET | `/stalls` | 档口列表，见下方参数 | 公开 |
| GET | `/stalls/{id}` | 档口详情 + 菜单（分组/菜品/规格）+ 是否营业 | 公开 |
| GET | `/stalls/{id}/reviews` | 评价列表（分页） | 公开 |
| GET | `/search?q=` | 档口名 + 菜品名联合搜索 | 公开 |

**GET /stalls 参数**

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `categoryId` | string | 分类过滤 |
| `keyword` | string | 名称模糊匹配 |
| `sort` | enum | `recommended`（默认）/`sales`/`rating`/`min_order` |
| `openNow` | boolean | 仅营业中 |
| `limit` / `cursor` | — | 分页 |

```json
200 OK
{
  "ok": true,
  "data": [
    {
      "id": "0192...a1",
      "name": "三食堂 · 川湘小炒",
      "logoUrl": "/assets/stalls/stall-01.webp",
      "categoryName": "盖浇饭",
      "rating": 4.6,
      "ratingCount": 128,
      "monthlySales": 940,
      "minOrderCents": 1500,
      "deliveryFeeCents": 200,
      "packingFeeCents": 100,
      "isOpen": true,
      "nextOpenAt": null,
      "estimatedMinutes": 18
    }
  ],
  "meta": { "nextCursor": null }
}
```

**GET /stalls/{id}** 额外返回 `notice`、`businessHours`（7 天）、`menuGroups[]`，每个 `dish` 含 `options: [{ id, name, required, minSelect, maxSelect, options: [{ id, name, priceDeltaCents, available }] }]` 与 `stock`、`status`。

---

## 5. 订单（`/orders`）

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| POST | `/orders/preview` | 试算：校验 + 返回金额明细，**不落库** | 学生 |
| POST | `/orders` | 下单（必带 `Idempotency-Key`） | 学生 |
| GET | `/orders` | 我的订单（`?status=` 过滤，分页） | 学生 |
| GET | `/orders/{id}` | 详情 + 状态时间轴 | 本人 |
| POST | `/orders/{id}/pay` | 模拟支付（必带 `Idempotency-Key`） | 本人 |
| POST | `/orders/{id}/cancel` | 取消（体：`{ reason }`） | 本人 |
| POST | `/orders/{id}/reviews` | 评价（体：`{ rating, content?, isAnonymous? }`） | 本人 |

### 5.1 下单请求

```json
POST /api/v1/orders
X-CSRF-Token: cZ1k...
Idempotency-Key: 3f9a2c7e-1b44-4d0a-9a11-2c7e5d9b0a11

{
  "stallId": "0192...a1",
  "fulfillmentType": "delivery",
  "addressId": "0192...b7",
  "expectedReadyAt": "2026-11-10T12:10:00.000Z",
  "tablewareCount": 1,
  "remark": "不要香菜",
  "items": [
    {
      "dishId": "0192...c3",
      "quantity": 2,
      "optionIds": ["0192...d1", "0192...d2"]
    }
  ]
}
```

### 5.2 下单响应

```json
201 Created
{
  "ok": true,
  "data": {
    "id": "0192...e9",
    "orderNo": "SO20261110001357",
    "status": "pending_payment",
    "fulfillmentType": "delivery",
    "stall": { "id": "0192...a1", "name": "三食堂 · 川湘小炒" },
    "items": [
      {
        "dishName": "农家小炒肉盖饭",
        "unitPriceCents": 1600,
        "optionsAmountCents": 300,
        "options": [{ "groupName": "辣度", "name": "微辣", "priceDeltaCents": 0 },
                    { "groupName": "加料", "name": "加蛋", "priceDeltaCents": 300 }],
        "quantity": 2,
        "lineAmountCents": 3800
      }
    ],
    "amount": {
      "itemsAmountCents": 3800,
      "packingFeeCents": 100,
      "deliveryFeeCents": 200,
      "discountCents": 0,
      "payableCents": 4100
    },
    "expiresAt": "2026-11-10T12:04:59.123Z",
    "createdAt": "2026-11-10T11:49:59.123Z"
  }
}
```

### 5.3 服务端强制校验（与前端无关）

1. 所有 `dishId` 必须属于 `stallId`。
2. 菜品 `status = 'on_sale'` 且 `stock >= quantity`。
3. 规格：`required` 组必须选；选择数满足 `minSelect ≤ n ≤ maxSelect`；选项 `available = true`。
4. 档口 `status = 'active'` 且在营业时段内（`expectedReadyAt` 落在营业时段亦校验）。
5. 配送单必须有 `addressId` 且属于本人；自提单忽略地址。
6. `itemsAmountCents >= stalls.min_order_cents`，否则 422。
7. **金额由服务端重算**，请求中任何价格字段被 schema strip。

### 5.4 订单对象（详情）

```json
{
  "id": "0192...e9",
  "orderNo": "SO20261110001357",
  "status": "delivering",
  "fulfillmentType": "delivery",
  "contact": { "name": "张同学", "phone": "138****8000" },
  "address": { "buildingName": "3 号楼", "room": "405" },
  "remark": "不要香菜",
  "amount": { "itemsAmountCents": 3800, "packingFeeCents": 100, "deliveryFeeCents": 200, "discountCents": 0, "payableCents": 4100 },
  "timeline": [
    { "from": null, "to": "pending_payment", "actorType": "student", "at": "2026-11-10T11:49:59.123Z" },
    { "from": "pending_payment", "to": "paid", "actorType": "student", "at": "2026-11-10T11:50:31.002Z" },
    { "from": "paid", "to": "accepted", "actorType": "merchant", "at": "2026-11-10T11:51:02.771Z" }
  ],
  "allowedActions": ["cancel"],
  "reviewed": false
}
```

`allowedActions` 由服务端按「当前状态 × 角色」计算，前端不自行推断按钮可用性——避免前后端规则漂移。

---

## 6. 个人中心（`/me`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/me` | 资料（手机号脱敏） |
| PATCH | `/me` | 改昵称/头像 |
| GET | `/me/addresses` | 地址列表 |
| POST | `/me/addresses` | 新增（首条自动设默认） |
| PATCH | `/me/addresses/{id}` | 修改 |
| DELETE | `/me/addresses/{id}` | 删除（有进行中订单引用则 409） |
| POST | `/me/addresses/{id}/default` | 设为默认（事务内清旧默认） |

---

## 7. 商家端（`/merchant`）

| 方法 | 路径 | 说明 | 认证 |
| --- | --- | --- | --- |
| GET | `/merchant/stall` | 我的档口（含营业时段） | merchant |
| PATCH | `/merchant/stall` | 改公告/配送费/起送价 | merchant |
| POST | `/merchant/stall/status` | `{ status: "active" \| "suspended" }` | merchant |
| GET | `/merchant/menu` | 分组 + 菜品（含下架） | merchant |
| POST | `/merchant/dishes` | 新增菜品（含规格组） | merchant |
| PATCH | `/merchant/dishes/{id}` | 编辑（必带 `version`） | merchant |
| POST | `/merchant/dishes/{id}/stock` | `{ stock }` 或 `{ soldOut: true }` | merchant |
| DELETE | `/merchant/dishes/{id}` | 软下架 | merchant |
| GET | `/merchant/orders` | 订单队列（`?status=paid,accepted`） | merchant |
| POST | `/merchant/orders/{id}/transition` | `{ to, reason? }` | merchant |
| GET | `/merchant/stats/today` | 今日单量/营业额（P1） | merchant |

**POST /merchant/orders/{id}/transition**

```json
{ "to": "accepted" }
```

```json
200 OK
{ "ok": true, "data": { "id": "0192...e9", "status": "accepted", "allowedActions": ["transition:preparing", "cancel"] } }
```

约束：`to` 必须在状态机表内；`delivering` 仅配送单；`ready` 仅自提单；拒单 `cancelled` 必填 `reason`；所有操作校验 `stalls.owner_user_id = actor.id`。

---

## 8. 管理端（`/admin`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/admin/stats/overview` | 今日单量、成交额、营业中档口数、待审核数、异常单数 |
| GET | `/admin/stalls` | 档口列表，`?status=pending\|active\|suspended` |
| POST | `/admin/stalls/{id}/approve` | 审核通过：`pending → active` |
| POST | `/admin/stalls/{id}/reject` | 审核驳回：`pending → suspended`，必填 `reason` |
| POST | `/admin/stalls/{id}/suspend` | 停业：`active → suspended`，必填 `reason` |
| GET | `/admin/users` | 用户列表，`?role=&status=&keyword=` |
| POST | `/admin/users/{id}/disable` | 封禁，必填 `reason`；**同时吊销该用户全部会话** |
| POST | `/admin/users/{id}/enable` | 解禁 |
| GET | `/admin/orders` | 全局订单，`?status=&stallId=&from=&to=` |
| POST | `/admin/orders/{id}/force-cancel` | 强制取消，必填 `reason`；已支付则写退款记录 |

```json
POST /api/v1/admin/orders/0192...e9/force-cancel
X-CSRF-Token: cZ1k...

{ "reason": "商家反馈餐品污染，全额退款" }
```

```json
200 OK
{ "ok": true, "data": { "id": "0192...e9", "status": "cancelled", "refunded": true } }
```

**约束**

- 所有写操作要求 `role = admin`；每次写操作落 `security_events(type='admin.action', actorId, target, reason)`。
- 强制取消必须走 `OrderService.force_cancel()`，不得绕过状态机：`completed` / 已 `cancelled` 返回 409。
- 已支付订单取消时写 `payments(status='refunded')`，金额取订单 `payable_cents`。
- 审核类操作只对 `pending` 生效，否则 `409 STALL_NOT_PENDING`。
- 管理员不能封禁自己（`409 ADMIN_CANNOT_DISABLE_SELF`），也不能封禁其它管理员（同错误码）。
- 管理端列表接口一律分页；看板接口按日聚合，只接受 `days ∈ {7, 30}`。

---

## 9. 限流

| 接口 | 维度 | 阈值 |
| --- | --- | --- |
| `/auth/login` | 手机号 + IP | 5 次/分钟 |
| `/auth/register` | IP | 3 次/小时 |
| `POST /orders` | 用户 | 10 次/分钟 |
| `POST /orders/{id}/pay` | 用户 | 20 次/分钟 |
| 全局 | IP | 300 次/分钟 |

命中返回 429 + `Retry-After` 头。

---

## 10. 校验规则速查（Pydantic 单一来源）

| 字段 | 规则 |
| --- | --- |
| `phone` | `^1[3-9]\d{9}$` |
| `password` | 长度 10–64，允许任意字符（不做复杂度强制），不得与手机号相同 |
| `quantity` | 1–20 整数 |
| `tablewareCount` | 0–10 整数 |
| `remark` | ≤ 100 字，去除首尾空白 |
| `rating` | 1–5 整数 |
| `content` | ≤ 200 字，纯文本 |
| `expectedReadyAt` | 不早于 now+10min，不晚于当日打烊前 30min |
| `limit` | 1–50 |
| 一切对象 | Pydantic `extra="forbid"`：**未知字段直接拒绝**，不静默丢弃 |

请求/响应模型定义在 `apps/api/src/schorder/schemas/`（Pydantic v2，唯一事实来源）。OpenAPI 由 FastAPI 生成并导出到 `packages/contract/openapi.json`，前端类型通过 `npm run gen:contract` 生成，禁止手写接口类型。

两点实现约定（会影响前端错误处理，先写进契约）：

1. **422 → 400**：FastAPI 默认对校验失败返回 422，本项目在 `exception_handler` 中统一映射为 `400 VALIDATION_ERROR`，并在 `details.fields` 给出字段级信息。
2. **价格字段直接拒绝**：请求体若夹带 `priceCents`/`payableCents`，视为篡改尝试在校验阶段即失败，而不是"纠正后放行"——静默纠正会让攻击探测失去信号。

---

## 11. 版本与兼容

- 破坏性变更（字段删除、语义改变、状态码调整）→ `/api/v2`，`v1` 保留一个迭代周期。
- 新增可选字段不升版本；前端必须容忍未知字段。
- 契约变更的完整链路：改 Pydantic 模型 → 重新导出 `openapi.json` → 重新生成 `types.ts` → 更新本文档。CI 会比较生成物与仓库内容，不一致直接失败。