# Schorder 安全设计（v1）

> 定位：Schorder 的强制安全基线——威胁模型、凭据与会话、授权模型、安全测试矩阵。
> 配套：[`architecture.md`](./architecture.md) ｜ [`api-contract.md`](./api-contract.md)
> 状态：待评审 ｜ 日期：2026-11-10
> 边界：本文是**强制基线**，不是"安全建议"。任何一条不满足，对应接口不予合并。

## 所有权

| 内容 | 拥有者 |
| --- | --- |
| 威胁模型、凭据与会话、CSRF、授权模型、安全测试矩阵 | 本文 |
| 分层、表结构、订单状态机、并发与事务 | [`architecture.md`](./architecture.md) |
| 接口清单、错误码目录、请求/响应示例 | [`api-contract.md`](./api-contract.md) |

安全要求不允许被接口示例放宽；接口字段以 `api-contract.md` 为准，结构以 `architecture.md` 为准。本文不复制它们的正文。

---

## 1. 安全目标与威胁模型

### 1.1 要保护的资产（按价值排序）

| 资产 | 泄露/破坏后果 | 归属 |
| --- | --- | --- |
| 账号凭据与会话 | 账号被接管，可下单、可操作档口 | auth |
| 订单与地址（姓名/手机号/楼栋房间） | PII 泄露，学生可被定位 | orders / users |
| 金额与库存完整性 | 白吃、超卖、商家损失 | orders / dishes |
| 档口经营数据 | 竞对窃取单量与营业额 | merchant |
| 审计记录 | 无法追责，攻击者擦除痕迹 | audit |

### 1.2 对手模型（谁可能怎么打）

| 对手 | 动机 | 典型手法 |
| --- | --- | --- |
| 恶意学生 | 免单、恶作剧 | 改前端价格、Dirty Order 状态、越权查他人订单、刷单 |
| 被处罚/竞对商家 | 报复、窃取经营数据 | 越权访问他人档口、批量下探 |
| 自动化脚本 | 撞库、薅羊毛 | 高频登录、批量注册、枚举订单号 |
| 供应链 | 投毒 | 恶意 npm/PyPI 包、typosquatting |
| 内部误操作 | 配置错误 | 把测试库连到公网、把密钥提交进仓库 |

**不在威胁模型内**：有 0day 的定向 APT、物理接触服务器、DDoS（无预算对抗，靠云厂商）。

### 1.3 信任边界

```
不可信 ── 浏览器 ──[边界①]── API 进程 ──[边界②]── SQLite 文件 ──[边界③]── 备份介质
```

| 边界 | 必守规则 |
| --- | --- |
| ① 浏览器→API | 一切输入不可信（含 Header、Cookie、JSON、路径参数）；一切输出按最小必要裁剪 |
| ② API→DB | 仅应用层可访问；DB 文件不暴露静态目录；连接串不落日志 |
| ③ 文件→备份 | 备份加密 + 权限收敛 + 可恢复演练 |

---

## 2. STRIDE 威胁与控制矩阵

| 威胁 | 具体场景 | 控制措施 | 验证方式 |
| --- | --- | --- | --- |
| **S**poofing | 撞库、会话窃取、Cookie 重放 | Argon2id、会话轮换、`HttpOnly+Secure+SameSite`、设备指纹（UA/IP 哈希）、绝对+闲置双超时、失败锁定 | 集成测试：伪造 sid → 401；并发登录 → 旧会话失效 |
| **T**ampering | 改价、改状态、改库存、重复下单 | 金额服务端重算、状态机 CAS、条件扣库存、幂等键唯一索引、ORM 参数化 | 单测覆盖价格矩阵；集成测试覆盖非法迁移 |
| **R**epudiation | 否认下过单/接过单 | `order_status_logs` 全量留痕（actor/时间/原因）、`security_events` 审计、日志只追加 | 每次状态变更断言日志条数 |
| **I**nformation disclosure | 越权查单、DTO 多带字段、日志里带手机号 | 查询级归属过滤、DTO 白名单映射、日志脱敏、错误信息不区分"不存在/无权限" | IDOR 矩阵测试（见 §10） |
| **D**enial of service | 刷登录、刷下单、超大 body | 分层限流、body ≤64KB、列表强制上限、SQL 必带 LIMIT | 压测 + 限流单测 |
| **E**levation of privilege | 学生调商家接口、商家操作他人档口 | 角色守卫（路由层）+ 归属校验（服务层）+ 策略函数集中定义 | 每个接口至少一条"他人身份 → 403"用例 |

---

## 3. 身份与凭据

### 3.1 密码

| 项 | 规定 |
| --- | --- |
| 哈希 | **Argon2id**（`argon2-cffi`），`m=19456 KiB, t=2, p=1`，16 字节随机盐，32 字节输出 |
| 降级 | 若 `argon2-cffi` 不可用，退回 `hashlib.scrypt`（`n=2**15, r=8, p=1`，stdlib 无额外依赖），参数写入 `users.password_algo` 以便日后升级重算 |
| 比对 | 恒定时间比较；用户不存在时也对固定假哈希做一次校验，抹平时序差异 |
| 策略 | 长度 ≥10，允许任意字符不加复杂度规则（NIST SP 800-63B）；禁止与手机号相同 |
| 传输 | 仅 HTTPS；生产环境拒绝明文 HTTP 登录（HSTS + 反代强制跳转） |
| 存储 | 哈希与盐只入库，禁止出现在日志、错误、审计明文中 |

### 3.2 会话（v1 的 JWT 方案已否决）

改为**服务端不透明会话**，理由：本项目单实例、无跨域，JWT 的无状态收益为零，而"不可即时吊销"和"令牌可被 JS 读取"是实打实的风险。

| 项 | 规定 |
| --- | --- |
| 令牌形态 | 32 字节 CSPRNG 随机值，Base64url；**服务端只存 SHA-256 哈希** |
| Cookie | `HttpOnly; Secure; SameSite=Lax; Path=/`；生产用 `__Host-sid` 前缀（强制 Secure + 无 Domain） |
| 有效期 | 闲置 30 分钟（每次请求续期，写入做 60s 节流避免写放大）；绝对 12 小时 |
| 轮换 | 登录成功、权限变更、密码修改时签发新 sid 并吊销旧 sid（防会话固定） |
| 设备绑定 | 记录 `UA 哈希 + IP 前 24 位哈希`，变化时记审计事件并降级为「需重新登录」（可配置为仅告警） |
| 吊销 | 登出删当前会话；改密/封禁删该用户全部会话；`SESSION_PEPPER` 轮换即全体失效（事故预案） |
| 每请求成本 | 一次主键查询（SQLite ~0.1ms），可接受 |

**为什么不选 JWT（写清楚，评审可直接引用）**：无状态只在多实例横向扩展时才值钱；本项目单实例，换来的是无法即时吊销、无法感知设备变化、令牌必须放在 JS 可读处（内存也会被 XSS 读走）。

### 3.3 CSRF

SameSite=Lax 已挡住绝大多数跨站 POST，但按纵深防御仍加两道：

1. **自定义头强制**：所有非 GET 请求必须带 `X-CSRF-Token`，值来自 `GET /auth/session` 下发并保存在会话记录中；缺失或不等 → 403 `CSRF_TOKEN_INVALID`。
2. **来源校验**：校验 `Origin`（缺失时回退 `Referer`）必须等于配置的站点源；不匹配 → 403。

> 自定义头本身就使简单表单跨站提交失效（浏览器预检会拦），这是比双提交 Cookie 更稳的做法。

### 3.4 登录保护

| 控制 | 规则 |
| --- | --- |
| 失败计数 | 同一手机号 5 次/15 分钟 → 锁定 15 分钟，逐次递增退避（指数，上限 1 小时） |
| 同 IP 多账号 | 20 次/小时失败 → 该 IP 登录一律 429 |
| 枚举防护 | 注册与登录统一话术；忘记密码（P1）恒返回"若存在将发送" |
| 审计 | 每次成功/失败写 `security_events`（含 IP 哈希、UA 哈希、结果、原因码） |

---

## 4. 授权模型

### 4.1 三层，缺一不可

```
① 路由守卫：requireAuth / requireRole('merchant')       —— 挡住"根本不该进来的人"
② 策略函数：can(actor, action, resource)                —— 表达"谁能做什么"，集中在一处
③ 查询级过滤：所有查询强制附加 AND owner_id = actor.id  —— 挡住"绕过策略的漏网查询"
```

第③层是重点：**授权必须体现在 SQL 的 WHERE 里**，而不是查出来再 `if` 判断。后者一旦漏写就是 IDOR。

### 4.2 策略矩阵

| 资源 \ 动作 | student（本人） | merchant（本档口） | admin |
| --- | --- | --- | --- |
| `order:read` | ✅ 自己的 | ✅ 本档口的 | ✅ 全部 |
| `order:create` | ✅ | ❌ | ❌ |
| `order:cancel` | ✅ 未接单前 | ✅ 拒单（需理由） | ✅ |
| `order:transition` | ❌ | ✅ 本档口 | ✅ |
| `dish:write` | ❌ | ✅ 本档口 | ✅ |
| `stall:read` | ✅ 公开 | ✅ | ✅ |
| `address:*` | ✅ 自己的 | ❌ | ❌ |
| `review:create` | ✅ 自己的已完成单 | ❌ | ❌ |

实现：`domain/policy.ts` 导出纯函数 `can(actor, action, subject)`，Service 调用它；单元测试对矩阵做全量遍历（8 动作 × 3 角色 × 3 归属关系 = 72 组断言）。

### 4.3 防枚举

订单详情、档口私有资源的 404 与 403 **不作区分**：无权限时一律 404（`RESOURCE_NOT_FOUND`），避免通过状态码探测资源是否存在。

---

## 5. 输入与输出安全

### 5.1 输入

| 控制 | 规定 |
| --- | --- |
| Schema | Zod `strict()`（未知字段直接拒绝，不静默丢弃）；`shared` 包单一来源 |
| 边界 | Body ≤ 64KB，URL ≤ 2KB，数组 ≤ 50 项，字符串 ≤ 1000 字符，JSON 嵌套 ≤ 5 层 |
| 路径参数 | 全部按 UUIDv7 正则校验，非法即 400（不进入业务） |
| 数值 | 金额/数量限定整数与上下界，禁止科学计数法与浮点 |
| 排序/筛选字段 | 白名单枚举映射到列，**绝不拼接进 SQL** |
| 富文本 | 不存在。备注、评价一律纯文本，渲染端不做 HTML 解析 |

### 5.2 输出

| 控制 | 规定 |
| --- | --- |
| DTO 白名单 | 出参由 presenter 显式挑字段（`id/name/...`），禁止 `SELECT *` 直接透传 |
| 手机号 | 非本人视角一律脱敏 `138****8000`；商家端订单仅在后厨履约必需时展示，且记审计 |
| 地址 | 列表接口只回楼栋+房间号，不回联系人手机号 |
| 错误 | 生产环境只回 `code + message + traceId`，绝不回堆栈、SQL、文件路径 |
| 缓存 | 含 PII 的响应 `Cache-Control: no-store` |

---

## 6. 传输与浏览器侧

### 6.1 响应头（生产）

| 头 | 值 |
| --- | --- |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(self)` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `X-Powered-By` | 移除 |

`style-src` 的 `'unsafe-inline'` 是已知妥协（React 内联 `style` 属性），列为技术债并记录：改用 CSS 变量 + 类名后可移除。

### 6.2 前端侧

- 不存任何令牌到 `localStorage`/`sessionStorage`（会话在 HttpOnly Cookie，JS 读不到）。
- 不使用 `dangerouslySetInnerHTML`；`eslint-plugin-react` 开启告警。
- 第三方脚本为零：不引入 CDN、统计、地图 SDK。
- 外链一律 `rel="noopener noreferrer"`。
- 客户端校验只用于体验，不作为安全依据。

---

## 7. 数据保护

| 项 | 规定 |
| --- | --- |
| 最小化 | 不收集生日、学号、身份证；手机号仅用于履约 |
| 落库 | SQLite 文件权限收敛到运行用户；不放在静态资源目录 |
| 静态加密 | 依赖主机全盘加密（BitLocker/LUKS）；应用层不对 DB 做字段加密（会破坏索引且收益有限），记录为有意取舍 |
| 备份 | `VACUUM INTO` 后立即用 `age` 加密，密钥独立保管；保留 7 天；每季度做一次恢复演练 |
| 日志 | 手机号脱敏，不记录密码/令牌/Cookie/完整地址；日志保留 30 天 |
| 删除权 | 注销账号 → 账号 `disabled` + PII 置空 + 订单保留（法定/审计需要），30 天后彻底匿名化 |

---

## 8. 审计与监控

### 8.1 审计事件（`security_events` 表）

| 事件 | 字段 |
| --- | --- |
| `auth.login_success` / `auth.login_failed` / `auth.locked` | userId?, phoneHash, ipHash, uaHash, result, reason |
| `auth.session_rotated` / `auth.logout` | sessionId 前缀 |
| `authz.denied` | actorId, action, resourceType, resourceId |
| `order.transition` | orderId, from, to, actorType, actorId |
| `admin.action` | action, targetType, targetId |

只追加，不更新不删除（DB 层面用触发器禁止 UPDATE/DELETE，属于低成本高收益的约束）。

### 8.2 监控与告警（轻量）

| 指标 | 阈值动作 |
| --- | --- |
| 登录失败率 | 5 分钟内 > 50 次 → 日志告警 |
| `authz.denied` 突增 | 同一用户 1 分钟内 > 10 次 → 记录并限流 |
| 5xx 率 | > 1% 持续 5 分钟 → 告警 |
| 慢查询 | > 200ms 打印 SQL 指纹 |

不引入 Prometheus/Grafana（单机项目），先落地结构化日志 + 日志检索命令。

---

## 9. 依赖与供应链

| 控制 | 规定 |
| --- | --- |
| 锁文件 | `package-lock.json`（前端）与 `requirements.lock`（后端，pip-compile 产出）入库；CI 用 `npm ci` / `pip install --require-hashes -r` |
| 版本 | 固定主版本，禁止 `latest`；升级走 PR 并跑全量测试 |
| 审计 | 前端 `npm audit --omit=dev --audit-level=high`；后端 `pip-audit -r requirements.lock`；两者 + `osv-scanner` 高危阻断 |
| 安装脚本 | CI 与生产 `--ignore-scripts`（本项目依赖均无需 postinstall） |
| 依赖数量 | 新增依赖需在 PR 写明：用途、体积、维护活跃度、替代方案 |
| 密钥扫描 | pre-commit 跑 `gitleaks`，`.env` 永不入库 |

当前最小依赖集（后端 Python / 前端 TS 分开）：

- 后端：`fastapi` `uvicorn` `sqlalchemy` `alembic` `pydantic` `pydantic-settings` `argon2-cffi` `structlog` `slowapi`（可选）
- 前端：`react` `react-router` `@tanstack/react-query` `zustand` `zod` `tailwindcss`

---

## 10. 安全测试矩阵（每条都必须是自动化用例）

| 类别 | 用例 | 期望 |
| --- | --- | --- |
| 认证 | 无 Cookie 访问 `/orders` | 401 |
| 认证 | 过期 / 已吊销 sid | 401 `SESSION_EXPIRED` |
| 认证 | 伪造 sid（随机 32 字节） | 401 |
| 认证 | 登录 6 次错误密码 | 第 5 次后 423 `ACCOUNT_LOCKED` |
| 认证 | 用户不存在 vs 密码错误 | 响应体与耗时无差异（容差 30ms） |
| CSRF | POST 不带 `X-CSRF-Token` | 403 `CSRF_TOKEN_INVALID` |
| CSRF | `Origin` 为外站 | 403 |
| 越权 | 学生 A 查学生 B 订单 | 404（非 403） |
| 越权 | 商家 A 改商家 B 菜品 | 404 |
| 越权 | 学生调用 `/merchant/*` | 403 `FORBIDDEN` |
| 越权 | 管理员以外的角色调 `/admin/*` | 403 |
| 篡改 | 请求体夹带 `payableCents` | 被 strict schema 拒绝（400），或字段被剥离 |
| 篡改 | 直接 PATCH 订单 status | 路由不存在（404） |
| 业务 | `completed → paid` 迁移 | 409 `ORDER_INVALID_TRANSITION` |
| 业务 | 库存 1 时两个并发下单 | 1 成功 1 失败 409 |
| 业务 | 同幂等键并发 5 次 | 只产生 1 单 |
| 注入 | 菜品名含 `'; DROP TABLE` | 正常存储与展示，表存在 |
| 注入 | `sort` 传非白名单值 | 400，不进入 SQL |
| 洪水 | 1 分钟 11 次下单 | 第 11 次 429 |
| 头部 | 任意响应断言安全头齐全（CSP/HSTS/nosniff/Referrer-Policy） | 全部存在 |
| 依赖 | `pip-audit` / `npm audit` 高危 | CI 失败 |

这些用例放在 `server/tests/security/`，与功能测试分开跑，但共用同一套 CI 门禁。

---

## 11. 安全开发生命周期（评审用清单）

每个涉及数据读写的 PR 必须自查：

- [ ] 这个查询是否强制带上了 `actor` 归属条件？
- [ ] 新增字段是否可能把 PII 带进 DTO 或日志？
- [ ] 这个写操作是否在事务内？失败路径会不会留下半成品？
- [ ] 状态变更是否走了状态机与 CAS，而不是直接 UPDATE？
- [ ] 新接口是否需要限流？阈值是多少？
- [ ] 错误分支返回的 code 是否泄露资源是否存在？
- [ ] 是否有对应的安全测试用例？

---

## 12. 事件响应（Runbook）

| 场景 | 处置 |
| --- | --- |
| 会话令牌疑似泄露 | 轮换 `SESSION_PEPPER`（全体下线）→ 强制改密 → 查 `security_events` 定位来源 |
| 发现越权漏洞 | 立即加回归测试 → 修复 → 全量跑 IDOR 矩阵 → 记 ADR |
| 依赖投毒告警 | 锁定版本回滚 → `pip install --require-hashes` / `npm ci` 重建 → 审计构建产物 |
| DB 文件泄露 | 视为全部 PII 泄露：通报 + 强制改密 + 评估上报义务 |
| 备份损坏 | 用最近可用备份恢复，核对订单计数与金额汇总 |

---

## 13. 剩余风险（明确接受）

| 风险 | 为什么接受 | 补偿控制 |
| --- | --- | --- |
| 单机单实例，限流与会话都在内存/本地库 | 无预算上 Redis | 单实例部署；接口已抽象，可切换 |
| SQLite 无细粒度权限 | 嵌入式数据库特性 | 文件 ACL + 全盘加密 + 最小进程权限 |
| 无 WAF / DDoS 防护 | 校园内网/小流量 | 反代层基础限流 |
| `style-src 'unsafe-inline'` | React 内联样式 | 列为技术债，逐步消除 |
| 无多因素认证 | 成本与体验 | 强密码策略 + 设备变化告警 |

---

## 14. 与 v1 的差异

| 项 | v1 | v2（本文） | 原因 |
| --- | --- | --- | --- |
| 会话 | JWT 30min + 刷新令牌轮换 | 服务端不透明会话 + HttpOnly Cookie | 可即时吊销、JS 读不到、无需维护两套令牌 |
| CSRF | 依赖 SameSite | SameSite + 自定义头 + Origin 校验 | 纵深防御 |
| 数据访问 | 手写 SQL | SQLAlchemy 2.0（参数化 + 类型约束） | 消除拼接 SQL 的空间 |
| 审计 | 仅订单状态日志 | 独立 `security_events` + 只追加约束 | 可追责、可告警 |
| 授权 | 中间件 + 服务层校验 | 三层：守卫 / 策略函数 / 查询级过滤 | 收敛 IDOR 面 |