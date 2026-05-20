# AI智慧盘 · AiWisePlate

> **AI驱动的智能股票分析与量化研究平台**  
> 融合实时行情监控、K线分析、断板策略跟踪与 AI 智能分析于一体

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=flat&logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

---

## 📖 项目说明

本项目基于以下开源项目二次开发，在此致谢：

| 原项目 | 作者 | 许可证 | 贡献内容 |
|--------|------|--------|----------|
| **[Vibe-Trading](https://github.com/HKUDS/Vibe-Trading)** | HKUDS | MIT | AI Agent 核心、量化回测引擎、74个金融技能、多智能体 Swarm |
| **StockMiniProgramSystem** | 原作者 | - | 断板策略逻辑、新浪财经数据客户端、K线展示方案 |

**本项目新增内容：**
- 股票监控仪表盘（`agent/static/stock.html`）
- 多用户权限系统（`agent/src/stock/`）
- AI 智能分析面板（嵌入股票监控页）
- 统一登录认证（JWT，用户数据隔离）
- 实时数据缓存服务（新浪财经接口）
- 中英文双语界面

---

## ✨ 核心功能

### 🔍 股票监控（StockWatch）
- **K线图表**：5日历史 + 实时分时，MA5、买点线，断板/买点标注
- **断板识别**：自动识别断板，3日监控窗口，K线图高亮
- **买卖点监控**：MA5×1.025 买点 + 4条卖点规则（盘中30秒轮询）
- **候选池**：每日涨幅≥15%自动入候选池
- **持仓管理**：真实持仓录入、实时盈亏、卖点提醒
- **市场分类**：沪主板 / 深主板 / 创业板 / 科创板 / 北交所

### 🤖 AI 智能分析
- 内嵌 AI 对话面板，自动用工具拉取真实数据再分析
- 多模型自动 Fallback（主力→备用，用户无感）
- 每用户独立会话（30天保留）

### 📊 量化研究（继承 Vibe-Trading）
- 74个专业金融 Skills，29个 Swarm 多智能体预设
- 跨市场回测引擎（A股/港股/美股/加密/期货）
- Shadow Account：复盘交易行为

---

## 🚀 快速部署

### 环境要求
- Python 3.11+，Ubuntu 20.04+（推荐）
- 2核 4GB 内存，4M 带宽
- 至少一个 LLM API Key（国内推荐千问/DeepSeek）

### 安装

```bash
git clone https://github.com/xiaojie-mge/AiWisePlate.git
cd AiWisePlate

# 安装依赖
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 下载 ECharts 本地文件（避免 CDN 问题）
curl -o agent/static/echarts.min.js \
  https://cdn.bootcdn.net/ajax/libs/echarts/5.4.3/echarts.min.js

# 配置
cp agent/.env.example agent/.env
# 编辑 agent/.env，填入 LLM API Key

# 启动
vibe-trading serve --host 0.0.0.0 --port 8899
```

访问 `http://服务器IP:8899`，默认账号：`admin / Admin@123`（**首次登录请立即修改密码**）

### Docker 部署

```bash
cp agent/.env.example agent/.env
docker compose up --build -d
```

---

## ⚙️ 大模型配置

编辑 `agent/.env`：

```env
# 主力（推荐千问/DeepSeek，国内直连）
LANGCHAIN_PROVIDER=deepseek
LANGCHAIN_MODEL_NAME=deepseek-chat
DEEPSEEK_API_KEY=your-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 备用（千问）
FALLBACK_1_PROVIDER=dashscope
FALLBACK_1_MODEL=qwen3.5-flash
FALLBACK_1_API_KEY=your-key
FALLBACK_1_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 访问密码
API_AUTH_KEY=your-secret
```

---

## 📁 项目结构

```
AiWisePlate/
├── agent/                    # 后端（Python + FastAPI）
│   ├── api_server.py
│   ├── static/
│   │   ├── login.html        # 登录页
│   │   └── stock.html        # 股票监控主页
│   └── src/
│       ├── agent/            # Vibe-Trading ReAct Agent
│       └── stock/            # AiWisePlate 股票监控（新增）
│           ├── user_db.py
│           ├── stock_db.py
│           └── services/
│               ├── sina_client.py
│               ├── break_board.py
│               ├── buy_signal.py
│               ├── sell_signal.py
│               └── scheduler.py
├── frontend/                 # 量化研究前端（React，来自 Vibe-Trading）
├── doc/                      # 开发文档
│   ├── BUG_TRACKER.md        # ⚠️ 开发前必读
│   └── ...
└── README.md
```

---

## 🗺 路线图

- [x] 统一登录 + 多用户权限
- [x] K线图表 + 断板/买点标注
- [x] AI 智能分析面板
- [x] 断板识别 + 买卖点监控
- [x] 候选池 + 持仓管理
- [x] 用户数据隔离
- [ ] 微信/钉钉信号推送
- [ ] 移动端适配

---

## 📄 开源声明

本项目遵循 MIT 许可证。

原始项目 **Vibe-Trading** 版权归 [HKUDS](https://github.com/HKUDS) 所有，本项目在其基础上进行二次开发。使用时请遵循原项目许可证要求。

---

*AI智慧盘 · AiWisePlate © 2026 | Based on [Vibe-Trading](https://github.com/HKUDS/Vibe-Trading)*
