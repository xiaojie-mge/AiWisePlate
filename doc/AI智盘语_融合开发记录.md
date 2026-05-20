# AI智慧盘 融合开发记录

> 项目：Vibe-Trading + StockMiniProgramSystem → AI智慧盘  
> 服务器：1.15.170.236:8899  
> 更新日期：2026-05-20

---

## 一、整合目标

将两个项目融合为一个统一平台：

| 来源项目 | 贡献内容 |
|---------|---------|
| **Vibe-Trading** | AI 智能体、量化回测、多市场数据、技能库 |
| **StockMiniProgramSystem** | K线图表、断板策略监控、买卖点信号、模拟交易 |

**融合后叫做：AI智慧盘**  
一个地址统一入口，登录后可同时使用股票监控和AI智能体。

---

## 二、整体架构

```
http://1.15.170.236:8899
        ↓
   /login（统一登录页）
        ↓
   ┌────────────────────────────┐
   │                            │
  /stock（股票监控仪表盘）      /（AI 智能体）
  ECharts K线 + 买卖点          React 前端
  断板监控 + 模拟交易            回测 + 研究
   │                            │
   └──────────┬─────────────────┘
              ↓
         统一后端 FastAPI（8899）
    ┌──────────────────────────────┐
    │                              │
 /api/stock/*               /api/*（原有）
 股票监控服务                AI Agent 服务
 多用户隔离                  回测/研究/分析
    │
  SQLite（stock_users.db + stock_data.db）
```

---

## 三、当前完成进度

### ✅ 已完成（Step 1）

| 功能 | 文件 | 说明 |
|------|------|------|
| **统一登录页** | `agent/static/login.html` | JWT 认证，访问任意页面未登录自动跳转 |
| **多用户管理** | `agent/src/stock/user_db.py` | SQLite 存储，admin/user 角色区分 |
| **股票监控仪表盘** | `agent/static/stock.html` | ECharts K线、实时/5日切换、三栏布局 |
| **K线图** | `api/stock/chart/{code}` | AKShare 获取历史数据，MA5+买点线标注 |
| **分时图** | `api/stock/intraday/{code}` | 1分钟K线，昨收参考线 |
| **实时行情** | `api/stock/realtime/{code}` | AKShare 实时价格/涨跌幅 |
| **股票池管理** | `agent/src/stock/stock_db.py` | 按 user_id 隔离，支持手动添加 |
| **AI分析面板** | stock.html 右侧面板 | 一键问AI，预设提问，流式输出 |
| **用户管理界面** | stock.html 管理员弹窗 | 管理员可增删用户 |
| **侧边栏入口** | `frontend/src/components/layout/Layout.tsx` | React 导航加"股票监控"链接+退出按钮 |
| **统一登录流程** | `frontend/index.html` | 未登录自动跳转 /login |
| **千问大模型** | `agent/.env` | 主力 qwen3.5-flash，禁用思考模式 |
| **Fallback链** | `agent/src/providers/llm.py` | 千问→DeepSeek→open1.codes 自动切换 |
| **中文界面** | `frontend/src/lib/i18n.tsx` | 全量中英文切换，localStorage 持久化 |
| **系统命名** | 全局 | 统一改名为"AI智慧盘" |

---

### ❌ 待完成（Step 2）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 🔴 高 | **断板识别服务** | 前日涨停→今日未涨停，自动写入断板记录 |
| 🔴 高 | **买点监控** | 开盘≥-3% 且最低≤MA5×1.025，触发买点信号 |
| 🔴 高 | **卖点监控** | 浮盈25%/浮亏6%/跌破MA5/接近涨停，触发卖点提醒 |
| 🔴 高 | **定时任务** | APScheduler：16:30 收盘扫描 + 盘中30秒轮询 |
| 🟡 中 | **候选池自动扫描** | 每日涨幅≥15%的创业板股票自动入候选池 |
| 🟡 中 | **模拟交易引擎** | 根据买卖点信号自动模拟买卖，追踪盈亏 |
| 🟡 中 | **K线断板标注** | 在K线图上标注断板日（橙色图钉）和买点（红色箭头） |
| 🟡 中 | **持仓记录** | 用户可手动录入实际持仓，追踪浮盈/卖点提醒 |
| 🟢 低 | **AI对话用户隔离** | 不同用户有独立的 Session 和 Memory |
| 🟢 低 | **回测记录用户隔离** | 不同用户只看自己的回测结果 |
| 🟢 低 | **实时价格侧边栏** | 策略池股票列表显示实时涨跌（30秒自动刷新） |
| 🟢 低 | **断板3日监控窗口** | K线上橙色区间高亮断板后3个交易日 |
| 🟢 低 | **连板计数标注** | K线上自动标注 N板，4板以上用紫色 |

---

## 四、关键文件清单

### 新增文件

```
agent/
├── static/
│   ├── login.html          # 统一登录页
│   └── stock.html          # 股票监控仪表盘
└── src/stock/
    ├── __init__.py
    ├── user_db.py          # 多用户管理 + JWT
    └── stock_db.py         # 股票池/信号/持仓数据（按用户隔离）

doc/
├── AI智慧盘_融合开发记录.md   # 本文件
└── AI智慧盘_架构设计.md
```

### 修改文件

```
agent/
├── api_server.py           # 新增 /login /stock /api/stock/* 路由
├── src/providers/llm.py    # FallbackLLM + 千问禁用思考模式
└── src/agent/context.py    # 添加简洁输出要求

frontend/
├── index.html              # 添加未登录跳转
├── src/lib/i18n.tsx        # 中英文双语
└── src/components/layout/Layout.tsx  # 股票监控入口+退出按钮
```

### 数据库文件（服务器上）

```
/opt/Vibe-Trading/agent/
├── stock_users.db   # 用户表（id/username/pwd_hash/role/display）
└── stock_data.db    # 股票数据（stock_pool/candidate_pool/buy_signal/position）
```

---

## 五、服务器部署信息

| 项目 | 内容 |
|------|------|
| 服务器 IP | 1.15.170.236 |
| 端口 | 8899 |
| 系统 | Ubuntu 24.04 LTS |
| Python | 3.12（.venv 虚拟环境） |
| 进程管理 | nohup 后台运行，日志 /var/log/vibe-trading.log |
| 主力大模型 | 千问 qwen3.5-flash（DashScope） |
| 备用大模型 | DeepSeek deepseek-chat → open1.codes gpt-5.4 |
| 默认管理员 | admin / Admin@123 |
| AI API Key | vibe2026（浏览器 Settings 页面填入） |

### 启动命令

```bash
cd /opt/Vibe-Trading
.venv/bin/vibe-trading serve --host 0.0.0.0 --port 8899
```

---

## 六、Step 2 开发计划

### Phase 2A：核心监控服务（优先）

1. `agent/src/stock/scheduler.py` — APScheduler 定时任务
2. `agent/src/stock/break_board.py` — 断板识别逻辑
3. `agent/src/stock/buy_signal.py` — 买点监控（MA5×1.025）
4. `agent/src/stock/sell_signal.py` — 卖点监控（4条规则）
5. 在 `api_server.py` 启动时初始化 scheduler

### Phase 2B：前端数据打通

1. 股票池侧边栏实时刷新价格
2. K线图添加断板/买点标注
3. 信号 Tab 真实数据展示
4. 持仓 Tab + 手动录入表单

### Phase 2C：用户数据隔离

1. AI Session 绑定 user_id（按用户分目录）
2. 回测 Runs 绑定 user_id
3. AI Memory 按用户分目录存储

---

*文档由 Claude Code 自动生成，记录截止 2026-05-20*
