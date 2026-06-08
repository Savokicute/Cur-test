# 用户管理与权限控制（RBAC）需求文档

> **文档版本**: V1.0
> **创建日期**: 2026-06-04
> **项目**: TrendRadar 热点发现平台
> **状态**: 待评审

---

## 1. 项目背景与目标

### 1.1 背景

TrendRadar 热点发现平台当前已具备基础的 SSO 单点登录功能（与 we-mp-rss 联动），但**缺少细粒度的权限管理体系**。所有认证用户拥有相同的操作权限，无法区分管理员与普通用户的访问范围。

### 1.2 目标

构建基于角色（RBAC）的用户管理与权限控制系统，实现：

- **角色分离**：超级管理员 vs 普通用户，职责清晰
- **权限可控**：用户管理、系统配置、内容数据访问三大类权限
- **管理便捷**：可视化用户管理界面，支持查询、编辑、批量操作
- **可审计**：完整的操作日志记录，追溯管理行为

---

## 2. 角色体系设计

### 2.1 角色定义（固定 2 种）

| 角色 | 标识码 | 描述 |
|------|--------|------|
| **超级管理员** | `super_admin` | 拥有全部功能权限，可管理用户、配置系统、查看所有数据 |
| **普通用户** | `user` | 仅可使用平台核心功能（热点查看、AI 分析等），无法进入管理后台 |

### 2.2 默认规则

- 新注册用户默认角色 = **普通用户**
- 仅超级管理员可将其他用户升级为超级管理员
- 至少保留 1 个超级管理员账号（降级时校验）

---

## 3. 权限模型设计

### 3.1 权限分类（三大类）

#### 3.1.1 用户管理操作（`user:manage`）

| 权限标识 | 描述 | 超级管理员 | 普通用户 |
|----------|------|:----------:|:--------:|
| `user:list` | 查看用户列表 | ✅ | ❌ |
| `user:edit` | 编辑用户信息/角色 | ✅ | ❌ |
| `user:disable` | 禁用/启用账号 | ✅ | ❌ |
| `user:batch` | 批量操作（改角色、禁用） | ✅ | ❌ |

#### 3.1.2 系统配置（`system:config`）

| 权限标识 | 描述 | 超级管理员 | 普通用户 |
|----------|------|:----------:|:--------:|
| `source:manage` | 管理信息源（热榜源/网站源/公众号） | ✅ | ❌ |
| `config:crawler` | 配置爬虫规则和抓取参数 | ✅ | ❌ |
| `config:schedule` | 设置定时任务和调度策略 | ✅ | ❌ |
| `config:notification` | 管理通知渠道和订阅规则 | ✅ | ❌ |

#### 3.1.3 内容/数据访问（`content:access`）

| 权限标识 | 描述 | 超级管理员 | 普通用户 |
|----------|------|:----------:|:--------:|
| `hotspot:view` | 查看热点数据 | ✅ | ✅ |
| `hotspot:export` | 导出热点数据 | ✅ | ❌ |
| `ai:analysis` | 使用 AI 分析功能 | ✅ | ✅ |
| `ai:template_manage` | 管理 AI 分析模板 | ✅ | ❌ |
| `wechat:view` | 查看公众号文章 | ✅ | ✅ |
| `media:view` | 查看媒体文件 | ✅ | ✅ |

### 3.2 权限矩阵总览

```
                    │ 超级管理员 │ 普通用户
───────────────────┼────────────┼──────────
📋 用户管理         │    ✅ 全部   │   ❌ 无
⚙️  系统配置        │    ✅ 全部   │   ❌ 无
🔥 热点数据查看     │    ✅       │   ✅
🔥 热点数据导出     │    ✅       │   ❌
🤖 AI 分析使用      │    ✅       │   ✅
🤖 AI 模板管理     │    ✅       │   ❌
📱 公众号内容       │    ✅       │   ✅
🖼️  媒体文件        │    ✅       │   ✅
```

---

## 4. 功能需求详述

### 4.1 用户管理页面（前端）

#### 4.1.1 用户列表页

**入口**：侧边栏导航 → 「用户管理」（仅超级管理员可见）

**展示字段**：

| 列名 | 字段 | 说明 |
|------|------|------|
| 头像 | `avatar` | 用户头像（默认头像兜底） |
| 用户名 | `username` | 唯一标识 |
| 昵称 | `nickname` | 显示名称 |
| 角色 | `role` | 标签：超级管理员 / 普通用户 |
| 状态 | `is_active` | 启用（绿色）/ 禁用（红色） |
| 注册时间 | `created_at` | 格式：YYYY-MM-DD HH:mm |
| 最后登录 | `last_login_at` | 格式：YYYY-MM-DD HH:mm |
| 登录次数 | `login_count` | 统计值 |
| 操作 | - | 编辑 / 禁用或启用 |

**交互功能**：

- **搜索**：支持按用户名、昵称模糊搜索
- **筛选**：按角色筛选 / 按状态筛选（启用/禁用/全部）
- **排序**：按注册时间、最后登录时间排序
- **分页**：每页 20 条，支持切换 10/20/50

#### 4.1.2 编辑用户（弹窗/抽屉）

**可编辑字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| 昵称 | Input | 最大 50 字符 |
| 邮箱 | Input | 邮箱格式校验 |
| 角色 | Select | 超级管理员 / 普通用户 |
| 状态 | Switch | 启用 / 禁用 |
| 备注 | Textarea | 管理员备注信息（可选） |

**校验规则**：
- 修改角色为「普通用户」时：检查是否为最后一个超级管理员，若是则阻止并提示
- 禁用自身账号：阻止并提示「不能禁用当前登录账号」

#### 4.1.3 批量操作

- **批量改角色**：勾选多个用户 → 选择目标角色 → 确认执行
- **批量禁用/启用**：勾选多个用户 → 执行 → 显示结果（成功 N 个，失败 M 个）
- **全选/反选**：支持

#### 4.1.4 操作日志页

**入口**：用户管理页面内 Tab 切换 → 「操作日志」

**展示字段**：

| 列名 | 字段 | 说明 |
|------|------|------|
| 时间 | `created_at` | 操作发生时间 |
| 操作人 | `operator_username` | 执行操作的管理员 |
| 操作类型 | `action` | 编辑角色 / 禁用账号 / 启用账号 / 批量修改 |
| 目标用户 | `target_username` | 被操作的用户 |
| 详情 | `detail` | 变更前后的值（JSON diff） |

**筛选**：按时间范围 / 操作类型 / 操作人筛选

---

## 5. 后端 API 设计

### 5.1 用户管理 API

| 方法 | 路径 | 描述 | 权限要求 |
|------|------|------|----------|
| GET | `/api/users` | 用户列表（分页/搜索/筛选） | `user:list` |
| GET | `/api/users/{username}` | 用户详情 | `user:list` |
| PUT | `/api/users/{username}` | 编辑用户信息 | `user:edit` |
| PUT | `/api/users/{username}/role` | 修改用户角色 | `user:edit` |
| PUT | `/api/users/{username}/status` | 禁用/启用用户 | `user:disable` |
| POST | `/api/users/batch-role` | 批量修改角色 | `user:batch` |
| POST | `/api/users/batch-status` | 批量禁用/启用 | `user:batch` |
| GET | `/api/users/logs` | 操作日志列表 | `user:list` |

### 5.2 权限校验 API（中间件依赖）

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/auth/me` | 当前登录用户信息（含角色+权限列表） |
| GET | `/api/auth/permissions` | 获取当前用户的所有权限标识 |

### 5.3 请求/响应示例

#### GET /api/users

```json
// Query Params: ?page=1&size=20&role=&status=&keyword=

// Response
{
  "code": 0,
  "data": {
    "total": 15,
    "items": [
      {
        "username": "admin",
        "nickname": "系统管理员",
        "avatar": "/static/avatar/admin.png",
        "role": "super_admin",
        "role_name": "超级管理员",
        "is_active": true,
        "email": "admin@example.com",
        "created_at": "2026-01-01 10:00:00",
        "last_login_at": "2026-06-04 09:30:00",
        "login_count": 128,
        "remark": "初始管理员"
      }
    ]
  }
}
```

#### PUT /api/users/{username}/role

```json
// Request
{ "role": "super_admin" }

// Response (Success)
{ "code": 0, "message": "角色已更新" }

// Response (Error - 最后一个管理员)
{ "code": 40003, "message": "不能移除最后一个超级管理员" }
```

---

## 6. 数据库设计

### 6.1 新增表结构

#### 6.1.1 roles 表（角色定义）

```sql
CREATE TABLE IF NOT EXISTS roles (
    id          VARCHAR(32)  PRIMARY KEY,      -- 角色标识: super_admin / user
    name        VARCHAR(50)  NOT NULL UNIQUE,   -- 角色显示名称
    description TEXT                            -- 角色描述
);

-- 预设数据
INSERT INTO roles VALUES ('super_admin', '超级管理员', '拥有所有权限');
INSERT INTO roles VALUES ('user', '普通用户', '平台基础功能使用者');
```

#### 6.1.2 permissions 表（权限定义）

```sql
CREATE TABLE IF NOT EXISTS permissions (
    id          VARCHAR(64)  PRIMARY KEY,       -- 权限标识: user:list, source:manage ...
    name        VARCHAR(100) NOT NULL,           -- 权限名称
    category    VARCHAR(32)  NOT NULL,            -- 分类: user_manage / system_config / content_access
    description TEXT                             -- 权限描述
);
```

#### 6.1.3 role_permissions 表（角色-权限关联）

```sql
CREATE TABLE IF NOT EXISTS role_permissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id       VARCHAR(32)  NOT NULL REFERENCES roles(id),
    permission_id VARCHAR(64)  NOT NULL REFERENCES permissions(id),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role_id, permission_id)
);
```

#### 6.1.4 user_roles 表（用户-角色关联）

```sql
CREATE TABLE IF NOT EXISTS user_roles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      VARCHAR(255) NOT NULL,          -- 关联 we-mp-rss users.username
    role_id       VARCHAR(32)  NOT NULL REFERENCES roles(id),
    assigned_by   VARCHAR(255),                   -- 分配者
    assigned_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(username)
);
```

#### 6.1.5 user_operation_logs 表（操作日志）

```sql
CREATE TABLE IF NOT EXISTS user_operation_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operator        VARCHAR(255) NOT NULL,         -- 操作人
    action          VARCHAR(32)  NOT NULL,         -- 操作类型: update_role / disable / enable / batch_update
    target_user     VARCHAR(255) NOT NULL,         -- 目标用户
    detail          TEXT,                          -- 变更详情 JSON
    ip_address      VARCHAR(45),                   -- 操作 IP
    user_agent      TEXT,                          -- 浏览器 UA
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_logs_operator ON user_operation_logs(operator);
CREATE INDEX idx_logs_action ON user_operation_logs(action);
CREATE INDEX idx_logs_created ON user_operation_logs(created_at);
```

#### 6.1.6 user_stats 表（用户统计——可选，也可从 we-mp-rss 同步）

```sql
CREATE TABLE IF NOT EXISTS user_stats (
    username      VARCHAR(255) PRIMARY KEY,
    login_count   INTEGER DEFAULT 0,
    last_login_at DATETIME,
    last_login_ip VARCHAR(45),
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 6.2 ER 关系图

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│   roles     │──────<│ role_permissions │>──────│    permissions      │
│             │  1:N  │                  │  N:1  │                     │
└─────────────┘       └──────────────────┘       └─────────────────────┘
        ▲
        │ 1
        │
        │ N
┌─────────────┐
│ user_roles  │─────────────────────────────────┐
│             │                                 │
└─────────────┘                                 │
                                                │
┌─────────────────────┐    ┌────────────────────┴───────────┐
│ user_operation_logs │    │  user_stats                        │
│                     │    │                                    │
└─────────────────────┘    └────────────────────────────────────┘
                                  (via username ── we-mp-rss.users)
```

---

## 7. 技术实现方案

### 7.1 技术选型

| 层面 | 选型 | 说明 |
|------|------|------|
| 数据库 | SQLite（现有） + SQLAlchemy ORM | 新增表复用现有连接池 |
| 缓存 | 内存字典（现有 SSO 方案） | Token 中携带角色信息，避免频繁查库 |
| 后端框架 | FastAPI（现有） | 新增 Router + Middleware |
| 前端框架 | React（web/frontend/） | 新增页面组件 + 路由 |
| 权限模型 | RBAC（固定角色） | 不支持动态创建角色 |

### 7.2 与现有 SSO 集成方案

```
用户登录（SSO）
     ↓
we-mp-rss 认证成功，返回 Token
     ↓
SSO Service 缓存 Token 时，同时查询该用户的 role
     ↓
Token Payload 增加 role 字段: { access_token, role: "super_admin", ... }
     ↓
后续请求 → 权限中间件从 Token 读取 role → 查 role_permissions 表 → 放行/拒绝
```

**关键改动点**：
1. `sso_service.py`：Token 缓存增加 `role` 字段
2. 新建 `permission_middleware.py`：FastAPI 依赖注入，校验权限
3. 各 API 路由添加 `Depends(require_permission("user:list"))` 装饰器

### 7.3 目录结构规划

```
app/
├── api/
│   └── users.py                  # 新增：用户管理 API 路由
├── core/
│   ├── database.py               # 已有：新增表自动创建
│   └── permission.py             # 新增：权限校验中间件
├── models.py                     # 修改：新增 Role/Permission 等模型
├── services/
│   ├── sso_service.py            # 修改：Token 携带角色
│   └── user_service.py           # 新增：用户管理业务逻辑
└── schemas/
    └── user_schemas.py           # 新增：请求/响应 Pydantic 模型

web/frontend/src/
├── pages/
│   └── UserManagement.jsx        # 新增：用户管理页面
├── components/
│   ├── UserTable.jsx             # 新增：用户列表表格
│   ├── UserEditModal.jsx         # 新增：编辑弹窗
│   └── OperationLog.jsx          # 新增：操作日志
├── router/
│   └── index.jsx                 # 修改：新增路由
└── services/
    └── api.js                    # 修改：新增用户 API 调用
```

---

## 8. 开发任务拆解（全栈并行）

### Phase 1：后端基础（优先）

| # | 任务 | 文件 | 预估复杂度 |
|---|------|------|-----------|
| 1 | 数据库模型：Role / Permission / UserRole / OperationLog / UserStats | [app/models.py](app/models.py) | 中 |
| 2 | 权限服务：初始化预设角色和权限数据 | [app/services/user_service.py](app/services/user_service.py) | 低 |
| 3 | SSO 扩展：Token 携带角色信息 | [app/services/sso_service.py](app/services/sso_service.py) | 低 |
| 4 | 权限中间件：require_permission() 依赖注入 | [app/core/permission.py](app/core/permission.py) | 中 |
| 5 | 用户管理 API：CRUD + 批量操作 | [app/api/users.py](app/api/users.py) | 高 |
| 6 | Pydantic Schema 定义 | [app/schemas/user_schemas.py](app/schemas/user_schemas.py) | 低 |

### Phase 2：前端界面（并行）

| # | 任务 | 文件 | 预估复杂度 |
|---|------|------|-----------|
| 7 | API 封装：用户管理相关接口调用 | [web/frontend/src/services/api.js](web/frontend/src/services/api.js) | 低 |
| 8 | 用户列表页：表格 + 搜索 + 筛选 + 分页 | [web/frontend/src/pages/UserManagement.jsx](web/frontend/src/pages/UserManagement.jsx) | 高 |
| 9 | 编辑用户弹窗：表单 + 校验 | [web/frontend/src/components/UserEditModal.jsx](web/frontend/src/components/UserEditModal.jsx) | 中 |
| 10 | 批量操作：多选 + 确认弹窗 | [web/frontend/src/components/UserTable.jsx](web/frontend/src/components/UserTable.jsx) | 中 |
| 11 | 操作日志 Tab 页 | [web/frontend/src/components/OperationLog.jsx](web/frontend/src/components/OperationLog.jsx) | 中 |
| 12 | 路由配置 + 侧边栏菜单（仅超管可见） | [web/frontend/src/router/index.jsx](web/frontend/src/router/index.jsx) | 低 |

### Phase 3：联调与收尾

| # | 任务 | 说明 |
|---|------|------|
| 13 | 前后端联调 | 接口对接 + 权限校验验证 |
| 14 | 边界场景测试 | 最后一个管理员保护、自我禁用拦截等 |
| 15 | 初始种子数据 | 创建首个超级管理员账号 |

---

## 9. 非功能性需求

### 9.1 安全性

- 所有用户管理接口必须通过权限校验（`user:*` 系列）
- 密码相关操作不在此模块处理（由 we-mp-rss 的 auth 模块负责）
- 操作日志不可删除、不可修改（append-only）
- 敏感操作（角色变更、禁用）需二次确认

### 9.2 性能

- 权限列表缓存：用户登录后权限列表缓存在 Token 中，API 请求无需每次查库
- 用户列表分页：强制分页，禁止一次拉取全量数据
- 操作日志异步写入（可选优化）

### 9.3 兼容性

- 与 we-mp-rss 用户表通过 `username` 字段关联，不迁移用户数据
- 现有 SSO 登录流程保持兼容，仅扩展 Token 信息量
- 前端页面风格与现有 TrendRadar 保持一致

---

## 10. 验收标准

### 10.1 功能验收

- [ ] 超级管理员可在用户列表查看所有用户
- [ ] 超级管理员可编辑用户角色（普通用户 ↔ 超级管理员）
- [ ] 超级管理员可禁用/启用用户账号
- [ ] 超级管理员可批量修改角色和状态
- [ ] 操作日志正确记录所有管理行为
- [ ] 普通用户无法访问用户管理页面（403 或隐藏入口）
- [ ] 普通用户无法调用用户管理 API（403）
- [ ] 最后一个超级管理员不可被降级或禁用
- [ ] 用户不可禁用自身账号

### 10.2 技术验收

- [ ] 新增数据库表自动创建（无需手动 migration）
- [ ] 权限中间件在所有受保护接口生效
- [ ] Token 正确携带角色信息
- [ ] 前端页面无控制台报错
- [ ] API 响应时间 < 500ms（列表接口）

---

## 附录 A：权限预设数据清单

### permissions 表初始数据

```python
INITIAL_PERMISSIONS = [
    # 用户管理
    ("user:list", "查看用户列表", "user_manage", "查看用户列表及详情"),
    ("user:edit", "编辑用户信息", "user_manage", "修改用户昵称、邮箱等"),
    ("user:disable", "禁用/启用账号", "user_manage", "更改用户账号启用状态"),
    ("user:batch", "批量操作", "user_manage", "批量修改角色或状态"),

    # 系统配置
    ("source:manage", "管理信息源", "system_config", "管理热榜源/网站源/公众号"),
    ("config:crawler", "配置爬虫规则", "system_config", "设置爬取参数和过滤规则"),
    ("config:schedule", "设置定时任务", "system_config", "配置调度策略"),
    ("config:notification", "管理通知渠道", "system_config", "配置订阅和推送"),

    # 内容/数据访问
    ("hotspot:view", "查看热点数据", "content_access", "浏览热榜和热点信息"),
    ("hotspot:export", "导出热点数据", "content_access", "导出热点数据为文件"),
    ("ai:analysis", "使用 AI 分析", "content_access", "发起 AI 分析任务"),
    ("ai:template_manage", "管理 AI 模板", "content_access", "创建/编辑/删除分析模板"),
    ("wechat:view", "查看公众号内容", "content_access", "浏览公众号文章"),
    ("media:view", "查看媒体文件", "content_access", "浏览图片和视频"),
]
```

### role_permissions 初始映射

```python
# 超级管理员：拥有全部权限
# 普通用户：仅 content_access 下的非管理权限
USER_PERMISSIONS = [
    "hotspot:view",
    "ai:analysis",
    "wechat:view",
    "media:view",
]
```

---

*文档结束。以上需求经产品经理与需求方逐条确认后生成。*
