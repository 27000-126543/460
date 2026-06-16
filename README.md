# 共享办公空间智能调度系统 API

基于 FastAPI + SQLAlchemy 开发的共享办公空间智能调度与运营管理后端服务。

## 功能特性

### 会员管理
- 会员注册、登录、个人信息管理
- 会员等级体系（普通/银/金/铂金）
- 信用额度与余额管理
- 违约记录与预订限制

### 资源管理
- 工位、会议室等资源管理
- 资源状态（可用/占用/维护）
- 分层、分区、容量、费率配置

### 预订管理
- 智能推荐可用资源
- 时段冲突自动检测
- 资源锁定机制
- 签到/签退与实际时长计费

### 审批流程
- 高等级会员（金/铂金）自动通过
- 普通会员需管理员审批
- 超时2小时自动升级至上级
- 审批意见与拒绝原因

### 费用结算
- 按时长自动计费
- 余额自动扣款
- 充值与支付记录
- 余额不足预警与预订限制

### 消息通知
- 预订确认/审批结果实时推送
- 费用结算通知
- 余额不足提醒
- 管理员审批催办

## 技术栈

- **框架**: FastAPI 0.115
- **ORM**: SQLAlchemy 2.0
- **数据库**: SQLite（开发）/ MySQL（生产）
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt
- **任务调度**: APScheduler

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制 `.env.example` 为 `.env`，根据需要修改配置：

```bash
cp .env.example .env
```

默认使用 SQLite 数据库，无需额外配置。

### 3. 初始化数据库

```bash
PYTHONPATH=. python3 scripts/init_db.py
```

初始化后将创建以下测试账号：

**会员账号:**
- 普通会员: `test@example.com` / `test123`
- 黄金会员: `gold@example.com` / `gold123` (免审批)

**管理员账号:**
- 一级管理员: `admin` / `admin123`
- 二级管理员: `superadmin` / `super123`

### 4. 启动服务

```bash
PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问:
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 5. 运行测试

```bash
python3 scripts/test_api.py
```

## API 接口说明

### 会员模块 (`/api/v1/members`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/register` | 会员注册 | 公开 |
| POST | `/login` | 会员登录 | 公开 |
| GET | `/me` | 获取个人信息 | 会员 |
| PUT | `/me` | 更新个人信息 | 会员 |
| GET | `/notifications` | 我的通知 | 会员 |
| POST | `/notifications/{id}/read` | 标记已读 | 会员 |

### 资源模块 (`/api/v1/resources`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/` | 资源列表 | 公开 |
| GET | `/{id}` | 资源详情 | 公开 |
| POST | `/` | 创建资源 | 管理员 |
| PUT | `/{id}` | 更新资源 | 管理员 |
| DELETE | `/{id}` | 删除资源 | 管理员 |
| GET | `/{id}/availability` | 检查可用性 | 公开 |

### 预订模块 (`/api/v1/bookings`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/` | 创建预订 | 会员 |
| GET | `/` | 我的预订 | 会员 |
| GET | `/{id}` | 预订详情 | 会员 |
| POST | `/{id}/cancel` | 取消预订 | 会员 |
| POST | `/{id}/check-in` | 签到 | 会员 |
| POST | `/{id}/check-out` | 签退结算 | 会员 |
| POST | `/recommend` | 推荐资源 | 公开 |

### 支付模块 (`/api/v1/payments`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/recharge` | 账户充值 | 会员 |
| GET | `/` | 支付记录 | 会员 |
| GET | `/{id}` | 支付详情 | 会员 |

### 审批模块 (`/api/v1/approvals`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/` | 审批列表 | 管理员 |
| GET | `/{id}` | 审批详情 | 管理员 |
| POST | `/{id}/approve` | 通过审批 | 管理员 |
| POST | `/{id}/reject` | 拒绝审批 | 管理员 |

### 管理员模块 (`/api/v1/admin`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/login` | 管理员登录 | 公开 |
| GET | `/members` | 会员列表 | 管理员 |
| GET | `/members/{id}` | 会员详情 | 管理员 |
| PUT | `/members/{id}` | 更新会员 | 管理员 |
| GET | `/bookings` | 所有预订 | 管理员 |

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── database.py            # 数据库连接
│   ├── deps.py                # 依赖注入（认证等）
│   ├── main.py                # 应用入口
│   ├── scheduler.py           # 定时任务
│   ├── models/                # 数据模型
│   │   └── __init__.py
│   ├── schemas/               # Pydantic 模式
│   │   └── __init__.py
│   ├── services/              # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── member_service.py
│   │   ├── resource_service.py
│   │   ├── booking_service.py
│   │   ├── approval_service.py
│   │   ├── payment_service.py
│   │   └── notification_service.py
│   ├── routers/               # API 路由
│   │   ├── __init__.py
│   │   ├── members.py
│   │   ├── resources.py
│   │   ├── bookings.py
│   │   ├── approvals.py
│   │   ├── payments.py
│   │   └── admin.py
│   └── utils/                 # 工具函数
│       └── __init__.py
├── scripts/
│   ├── init_db.py             # 数据库初始化
│   └── test_api.py            # API 功能测试
├── .env                       # 环境配置
├── .env.example               # 环境配置示例
├── requirements.txt           # 依赖列表
└── run.sh                     # 启动脚本
```

## 业务规则

### 会员等级与权益
- **普通会员 (BASIC)**: 信用额度 ¥1000，预订需审批
- **银卡会员 (SILVER)**: 信用额度 ¥3000，预订需审批
- **金卡会员 (GOLD)**: 信用额度 ¥8000，预订免审批
- **铂金会员 (PLATINUM)**: 信用额度 ¥20000，预订免审批

### 预订规则
1. 同一资源同一时段只能有一个有效预订
2. 可用额度 = 账户余额 + 信用额度
3. 预订金额超过可用额度则拒绝
4. 违约次数 ≥ 3 次限制预订

### 审批规则
1. 金卡/铂金会员预订自动通过
2. 其他会员预订需一级管理员审批
3. 2小时未处理自动升级至二级管理员
4. 最高级超时自动通过

### 费用结算
1. 签退时按实际使用时长计费
2. 实际费用不超过预定时长费用
3. 余额充足自动扣款
4. 余额不足推送提醒并限制后续预订

## 切换到 MySQL 生产环境

修改 `.env` 文件中的数据库连接：

```env
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/coworking_db?charset=utf8mb4
```

确保已创建数据库：

```sql
CREATE DATABASE coworking_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## License

MIT
