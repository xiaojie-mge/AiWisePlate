# AI智慧盘 Bug 追踪记录

> 每次开发前先查此文档，避免重复踩坑  
> 更新日期：2026-05-20

---

## ✅ 已修复

### BUG-001：ECharts 从 CDN 加载导致白屏/加载失败
- **现象**：K线图区域卡在"加载中..."，侧边栏股票池不显示
- **根因**：`cdn.jsdelivr.net` 从中国服务器加载慢（3秒+）甚至被墙
- **修复**：ECharts 本地化到 `/static/echarts.min.js`，改用 `/static/echarts.min.js` 引用
- **注意**：升级 ECharts 版本时需重新下载到 `/opt/Vibe-Trading/agent/static/`

### BUG-002：K线图请求 `?days=5` 参数校验失败返回空数据
- **现象**：切换"5日历史"后图表空白
- **根因**：API 校验 `days >= 10`，前端请求了 `?days=5`
- **修复**：前端请求 `?days=30`，用 dataZoom 的 `start` 参数只展示最近5日

### BUG-003：`/app` 路由 404
- **现象**：量化研究页面无法访问
- **根因**：`serve_main()` 有条件判断 `if not any(route.path=="/" for route...)` 防止重复挂载 SPA，但我加了 `@app.get("/")` 导致条件为 False，SPA 完全没挂载
- **修复**：移除该判断条件，改为 `app.mount("/", SPAStaticFiles(...))` 无条件挂载；同时将 `/` 重定向改为客户端 JS 处理

### BUG-004：React 智能体"消息发送失败"
- **现象**：`/agent` 页面发消息报错
- **根因**：`require_auth` 只接受 `API_AUTH_KEY`，React 前端未设置该 Key
- **修复**：
  1. `_validate_api_auth` 同时接受股票系统 `vt_token` 作为有效凭证
  2. `apiAuth.ts` 的 `getApiAuthKey()` 自动 fallback 到 `vt_token`

### BUG-005：股票删除按钮不工作
- **现象**：点击策略池的 × 删除按钮无响应
- **根因**：股票代码含 `.`（如 `600900.SH`），FastAPI 路径参数 `DELETE /pool/{code}` 对含点的路径匹配异常
- **修复**：改用 `POST /pool/remove?code=xxx` query 参数方式

### BUG-006：千问免费额度用完导致 AI 不可用
- **现象**：AI 分析报 `AllocationQuota.FreeTierOnly` 错误
- **根因**：千问 qwen3.5-flash 免费额度耗尽
- **修复**：切换主力为 DeepSeek，千问作备用。每次额度耗尽及时充值或切换

### BUG-007：SPA 挂载顺序与显式路由冲突
- **现象**：`@app.get("/")` 和 `app.mount("/", SPA)` 冲突
- **根因**：FastAPI 中显式路由优先于 mount，但 `mount("/")` 会覆盖所有未匹配子路径
- **规则**：永远用 `app.mount("/", SPA)` 不加条件判断，根路径重定向在 `index.html` 客户端做

### BUG-008：`api_server.py` 上传路径错误
- **现象**：文件改了但服务器没生效
- **根因**：`scp` 命令把 `stock.html` 传到了 `/agent/` 而不是 `/agent/static/`
- **规则**：`stock.html`/`login.html` 必须传到 `/opt/Vibe-Trading/agent/static/`，`api_server.py` 传到 `/opt/Vibe-Trading/agent/`

---

## 🔧 开发规则（每次必看）

### 文件上传路径
```
stock.html / login.html  → /opt/Vibe-Trading/agent/static/
api_server.py            → /opt/Vibe-Trading/agent/
src/stock/**             → /opt/Vibe-Trading/agent/src/stock/
frontend/dist/           → /opt/Vibe-Trading/frontend/dist/
```

### 重启服务器
```bash
kill $(lsof -ti:8899) 2>/dev/null; sleep 1
cd /opt/Vibe-Trading && nohup .venv/bin/vibe-trading serve --host 0.0.0.0 --port 8899 > /var/log/vibe-trading.log 2>&1 &
```

### 验证上传是否成功
```bash
grep -c '关键词' /opt/Vibe-Trading/agent/static/stock.html
```

### 大模型配置
- 主力：DeepSeek（`/opt/Vibe-Trading/agent/.env`）
- 备用：千问 → open1.codes（按顺序自动 fallback）
- 千问额度用完时：登录阿里云百炼控制台补充额度或切主力

### API 认证
- 股票系统：JWT（`vt_token`），8小时有效
- 量化研究（React）：`vt_token` 自动作为 Bearer token，登录即可用
- API_AUTH_KEY：`vibe2026`（浏览器 Settings 备用）

---

### BUG-012：`const` 声明放在对象字面量内导致 SyntaxError
- **现象**：K线图和侧边栏全部不显示，F12 报 `Uncaught SyntaxError: Unexpected identifier 'zoomStart'`
- **根因**：`const zoomStart = ...` 被错误放在 `chart.setOption({...})` 的对象 `{}` 内，JS 对象内不能有变量声明
- **修复**：将 `const zoomStart` 移到 `chart.setOption({` 调用之前（函数体内、对象外）
- **规则**：凡是要在 ECharts setOption 参数对象内用到的变量，必须在 setOption 调用语句之前声明

---

## ⏳ 待修复

| ID | 问题 | 优先级 |
|----|------|:------:|
| BUG-009 | 分时图（实时模式）非交易时段拉取超时，需要显示提示而不是白转圈 | 中 |
| BUG-010 | AKShare 实时行情偶发 `Connection aborted` 错误 | 中 |
| BUG-011 | 20 用户 AI 会话完全隔离（Memory 目录隔离已做，Session 过滤已做） | 低 |
