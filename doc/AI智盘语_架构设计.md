# AI智慧盘 架构设计文档

> 版本：v0.2（融合后）  
> 日期：2026-05-20

---

## 用户流程图

```
用户访问任意页面
      ↓
检查 localStorage.vt_token
      ↓
   有 token？
  /         \
 是           否
 ↓            ↓
进入系统    /login 登录页
            输入账号/密码
                ↓
          POST /api/stock/auth/login
                ↓
          返回 JWT token（8小时）
                ↓
          跳转 /（主页）

主页导航：
  左侧边栏下方 → 📈 股票监控 → /stock
  顶部导航     → 🤖 AI 智能体 → /agent
  登出按钮     → 清除 token → /login
```

---

## API 路由设计

### 认证相关
```
POST /api/stock/auth/login     → 登录，返回 JWT
GET  /api/stock/auth/me        → 当前用户信息
```

### 用户管理（管理员）
```
GET    /api/stock/admin/users          → 用户列表
POST   /api/stock/admin/users          → 创建用户
DELETE /api/stock/admin/users/{name}   → 删除用户
```

### 股票数据
```
GET  /api/stock/pool                   → 我的策略池
POST /api/stock/pool/add               → 添加股票到策略池
GET  /api/stock/candidates             → 候选池
POST /api/stock/candidates/{id}/select → 候选股加入策略池
GET  /api/stock/signals                → 买点信号列表
GET  /api/stock/positions              → 持仓记录
GET  /api/stock/chart/{code}           → K线历史数据
GET  /api/stock/intraday/{code}        → 分时数据
GET  /api/stock/realtime/{code}        → 实时价格
```

### 静态页面
```
GET /login   → login.html（登录页）
GET /stock   → stock.html（股票监控仪表盘）
GET /        → React SPA（AI 智能体主界面）
```

---

## 数据库设计

### stock_users.db

```sql
CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    pwd_hash TEXT NOT NULL,          -- SHA256 hash
    role     TEXT DEFAULT 'user',    -- 'admin' or 'user'
    display  TEXT,                   -- 显示名
    created  INTEGER                 -- Unix timestamp
);
```

### stock_data.db

```sql
-- 策略池（按用户隔离）
CREATE TABLE stock_pool (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL,   -- 关联 users.id
    code         TEXT NOT NULL,      -- 如 000001.SZ
    name         TEXT,
    add_type     TEXT,               -- 'auto' or 'manual'
    trade_status TEXT,               -- 'pending/triggered/abandoned'
    theme        TEXT,               -- 题材概念
    add_date     TEXT,
    status       TEXT DEFAULT 'in'   -- 'in' or 'out'
);

-- 候选池
CREATE TABLE candidate_pool (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL,
    code         TEXT,
    name         TEXT,
    add_date     TEXT,
    change_ratio REAL,
    close_price  REAL,
    pool_status  TEXT DEFAULT 'pending'  -- 'pending/selected/rejected'
);

-- 买点信号
CREATE TABLE buy_signal (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL,
    code          TEXT,
    signal_date   TEXT,
    trigger_price REAL,   -- MA5 × 1.025
    ma5           REAL,
    is_notified   INTEGER DEFAULT 0
);

-- 持仓记录
CREATE TABLE position (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    code        TEXT,
    name        TEXT,
    buy_date    TEXT,
    buy_price   REAL,
    shares      INTEGER,
    status      TEXT DEFAULT 'open',  -- 'open' or 'closed'
    close_date  TEXT,
    close_price REAL,
    pnl         REAL,
    pnl_pct     REAL
);
```

---

## 断板策略逻辑（Step 2 实现）

### 断板识别
```
条件：前日涨停（涨幅≥19%）且今日不涨停
过滤：
  - 断板日最高价 < 前日收盘价 → 移出股票池
  - 断板日收盘 < (前开+前收)/2 → 移出股票池
  - 通过过滤 → 写入断板记录，监控3个交易日
```

### 买点条件（同时满足）
```
条件1：开盘涨跌幅 ≥ -3%（开盘有效）
条件2：当日最低价 ≤ MA5 × 1.025（回踩5日线）
触发：写入 buy_signal，推送提醒
```

### 卖点条件（任一触发）
```
规则1：接近涨停（≥前收×1.195）→ 卖半仓
规则2：跌破 MA5 → 清仓
规则3：浮盈 ≥ 25% → 清仓
规则4：浮亏 ≥ 6% → 清仓
```

### 定时任务
```
收盘后 16:30（周一至周五）：
  - 刷新股票池（检查剔除规则）
  - 断板识别

盘中每30秒（9:25-11:31, 13:00-15:05）：
  - 买点监控
  - 卖点提醒
  - 模拟自动买卖
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端（AI智能体） | React 19 + Vite + TypeScript + ECharts |
| 前端（股票监控） | 原生 HTML + ECharts 5 |
| 后端框架 | FastAPI + Uvicorn |
| AI 调用 | LangChain + LangGraph（ReAct Agent） |
| 大模型 | 千问 qwen3.5-flash（主）/ DeepSeek / open1.codes |
| 市场数据 | AKShare（免费）/ Tushare（可选）|
| 数据库 | SQLite（用户+股票数据）|
| 认证 | HMAC-SHA256 JWT（8小时有效期）|
| 部署 | Ubuntu 24.04 + nohup 后台 |
