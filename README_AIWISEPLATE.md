# AI智慧盘 · AiWisePlate

> **AI驱动的智能股票分析与量化研究平台**  
> 融合实时行情监控、K线分析、断板策略跟踪与 AI 智能分析于一体

---

## 产品定位

| 维度 | 说明 |
|------|------|
| **中文名** | AI智慧盘 |
| **英文名** | AiWisePlate |
| **命名含义** | Wise（智慧）+ Plate（盘面/交易盘），寓意智慧看盘 |
| **目标用户** | 个人投资者、量化研究员、私募团队 |
| **核心价值** | 实时盯盘 + AI 分析 + 量化回测，三位一体 |

---

## 核心功能

### 🔍 股票监控（StockWatch）
- 策略池管理：添加关注股票，分市场分类（沪主板/深主板/创业板/科创板/北交所）
- K线图表：5日历史 + 实时分时，MA5、买点线标注
- 断板识别：自动识别前日涨停今日断板，标注K线图，3日监控窗口
- 买点监控：MA5×1.025 回踩触发买点信号（盘中30秒轮询）
- 卖点监控：浮盈25%/浮亏6%/跌破MA5/接近涨停，实时提醒
- 候选池：每日涨幅≥15%股票自动入候选池
- 持仓管理：真实持仓录入、实时盈亏、卖点高亮

### 🤖 AI 智能分析（AiAnalyst）
- 内嵌 AI 对话面板，直接分析当前股票
- 自动调用工具拉取真实市场数据，不靠训练记忆
- 预设问题：技术分析 / 买点判断 / 风险评估 / 快速回测
- 多模型自动切换（主力→备用，用户无感）

### 📊 量化研究（QuantLab）
- 74个专业金融 Skills（A股/港股/美股/加密/期货）
- 29个 Swarm 多智能体预设团队
- 跨市场回测引擎，支持多数据源自动 Fallback
- Shadow Account：复盘自己的交易行为，提取策略规则

---

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│              浏览器 http://域名:8899                  │
├──────────────────────────────────────────────────────┤
│  /login       登录页（JWT 多用户认证）               │
│  /stock       股票监控主页面（HTML + ECharts）        │
│  /agent       量化研究（React 19 + TypeScript）       │
├──────────────────────────────────────────────────────┤
│              FastAPI 后端（Python 3.12）              │
├─────────────────────┬────────────────────────────────┤
│  股票监控服务        │  AI Agent 服务                 │
│  ├ 实时数据（新浪）  │  ├ ReAct Agent Loop            │
│  ├ 断板识别          │  ├ 74个金融 Skills             │
│  ├ 买卖点监控        │  ├ 32个工具                    │
│  ├ 定时任务          │  └ 跨市场回测引擎              │
│  └ SQLite 数据库     │                                │
└─────────────────────┴────────────────────────────────┘
```

### 技术栈

| 层 | 技术 |
|----|------|
| 股票监控前端 | 原生 HTML5 + ECharts 5（本地化）|
| 量化研究前端 | React 19 + Vite + TypeScript + TailwindCSS |
| 后端框架 | FastAPI + Uvicorn（Python 3.12）|
| AI 调度 | LangChain + LangGraph（ReAct Agent）|
| 数据源 | 新浪财经（主）/ AKShare / Tushare |
| 数据库 | SQLite（用户+股票数据，单机零配置）|
| 认证 | HMAC-SHA256 JWT（8小时，多用户隔离）|
| 大模型 | open1.codes GPT → 千问 → DeepSeek（自动Fallback）|

---

## 快速部署

### 环境要求

| 项目 | 要求 |
|------|------|
| 服务器 | 2核 4GB+ 内存，Ubuntu 20.04+ |
| Python | 3.11 或 3.12 |
| 带宽 | 4M 以上（流量极低）|
| 大模型 | 任意 OpenAI 兼容 API（国内可用千问/DeepSeek）|

### 一键启动

```bash
# 1. 克隆项目
git clone https://github.com/yourrepo/AiWisePlate.git
cd AiWisePlate

# 2. 安装依赖
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows
pip install -e .

# 3. 配置大模型
cp agent/.env.example agent/.env
# 编辑 agent/.env，填入 API Key

# 4. 启动服务
vibe-trading serve --host 0.0.0.0 --port 8899
```

访问 `http://服务器IP:8899`，默认账号：`admin / Admin@123`

### Docker 部署

```bash
cp agent/.env.example agent/.env
# 编辑 agent/.env 填入 API Key
docker compose up --build -d
```

---

## 大模型配置

编辑 `agent/.env`，推荐配置（国内可用）：

```env
# 主力（open1.codes - 顶级模型）
LANGCHAIN_PROVIDER=openai
LANGCHAIN_MODEL_NAME=gpt-5.4
OPENAI_API_KEY=你的Key
OPENAI_BASE_URL=https://www.open1.codes/v1

# 备用1（千问，国内免费额度）
FALLBACK_1_PROVIDER=dashscope
FALLBACK_1_MODEL=qwen3.5-flash
FALLBACK_1_API_KEY=你的Key
FALLBACK_1_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 备用2（DeepSeek，国内直连）
FALLBACK_2_PROVIDER=deepseek
FALLBACK_2_MODEL=deepseek-chat
FALLBACK_2_API_KEY=你的Key
FALLBACK_2_BASE_URL=https://api.deepseek.com/v1

# 系统
API_AUTH_KEY=你的访问密码
```

---

## 用户权限体系

| 角色 | 权限 |
|------|------|
| **admin** | 全功能 + 用户管理，不可删除 |
| **user** | 股票监控 + AI分析，数据与其他用户完全隔离 |

每个用户独立：
- 策略池、持仓、断板记录
- AI 对话历史（保留30天）
- AI 记忆（`~/.vibe-trading/memory/user_{id}/`）

---

## 项目结构

```
AiWisePlate/
├── agent/                    # 后端（Python）
│   ├── api_server.py         # FastAPI 主入口
│   ├── static/
│   │   ├── login.html        # 登录页
│   │   ├── stock.html        # 股票监控主页
│   │   └── echarts.min.js    # ECharts（本地化，避免CDN问题）
│   └── src/
│       ├── agent/            # ReAct Agent 核心
│       ├── stock/            # 股票监控服务
│       │   ├── user_db.py    # 多用户管理
│       │   ├── stock_db.py   # 股票数据（按用户隔离）
│       │   └── services/
│       │       ├── sina_client.py      # 新浪财经数据（稳定）
│       │       ├── break_board.py      # 断板识别
│       │       ├── buy_signal.py       # 买点监控
│       │       ├── sell_signal.py      # 卖点监控
│       │       ├── candidate_pool.py   # 候选池扫描
│       │       ├── realtime_service.py # 实时数据缓存
│       │       └── scheduler.py        # APScheduler 定时任务
│       └── skills/           # 74个金融技能
├── frontend/                 # 量化研究前端（React）
├── doc/                      # 开发文档
│   ├── BUG_TRACKER.md        # Bug 追踪记录（每次开发前必看）
│   ├── AI智慧盘_融合开发记录.md
│   ├── AI智慧盘_架构设计.md
│   └── AI智慧盘_功能设计方案.md
└── README_AIWISEPLATE.md     # 本文件
```

---

## 定时任务调度

| 时间 | 任务 |
|------|------|
| 每天 06:00 | 清空实时数据缓存 |
| 每天 08:30 | 开始拉取入池股票实时行情（30秒/次）|
| 每天 15:05 | 停止实时数据拉取 |
| 每天 16:35（周一至周五）| 刷新策略池 + 断板识别 + 候选池扫描 |
| 盘中每30秒 | 买点监控 + 卖点监控 |
| 每天 02:00 | 清理超过30天的旧会话 |

---

## 开发规范

详见 [doc/BUG_TRACKER.md](doc/BUG_TRACKER.md)，每次开发前必读。

### 关键规则

1. **文件上传路径**
   - `stock.html` / `login.html` → `/opt/AiWisePlate/agent/static/`
   - `api_server.py` → `/opt/AiWisePlate/agent/`

2. **重启命令**
   ```bash
   kill $(lsof -ti:8899); cd /opt/AiWisePlate && nohup .venv/bin/vibe-trading serve --host 0.0.0.0 --port 8899 > /var/log/aiwiseplate.log 2>&1 &
   ```

3. **ECharts 使用本地文件**，不要改回 CDN（国内访问慢）

4. **JS 中不能在对象字面量 `{}` 内写 `const`**（会导致 SyntaxError）

---

## 路线图

| 阶段 | 功能 | 状态 |
|------|------|:----:|
| **已完成** | 股票监控主界面、K线图、多用户、AI分析 | ✅ |
| **Phase 2** | 断板/买卖点监控、候选池、定时任务 | ✅ |
| **Phase 3** | 用户数据隔离、AI会话隔离 | ✅ |
| **Phase 4** | 实时数据临时库、市场分类 | ✅ |
| **待开发** | 微信/钉钉推送 | 🔜 |
| **待开发** | 移动端适配 | 🔜 |
| **待开发** | 多品种扩展（港股/美股实时）| 🔜 |

---

## 许可证

内部使用，未经授权不得对外分发。

---

*AI智慧盘 · AiWisePlate © 2026*
