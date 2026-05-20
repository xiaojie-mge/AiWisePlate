import { Bot, TrendingUp, Bitcoin, Globe, Sparkles, Users, UserCircle2, NotebookPen } from "lucide-react";
import { useI18n } from "@/lib/i18n";

interface Example { title: string; desc: string; prompt: string; }
interface Category { label: string; icon: React.ReactNode; color: string; examples: Example[]; }

const CATEGORIES_EN: Omit<Category, "icon">[] = [
  {
    label: "Multi-Market Backtest",
    color: "text-red-400 border-red-500/30 hover:border-red-500/60 hover:bg-red-500/5",
    examples: [
      { title: "Cross-Market Portfolio", desc: "A-shares + crypto + US equities with risk-parity optimizer", prompt: "Backtest a risk-parity portfolio of 000001.SZ, BTC-USDT, and AAPL for full-year 2024, compare against equal-weight baseline" },
      { title: "BTC 5-Min MACD Strategy", desc: "Minute-level crypto backtest with real-time OKX data", prompt: "Backtest BTC-USDT 5-minute MACD strategy, fast=12 slow=26 signal=9, last 30 days" },
      { title: "US Tech Max Diversification", desc: "Portfolio optimizer across FAANG+ via yfinance", prompt: "Backtest AAPL, MSFT, GOOGL, AMZN, NVDA with max_diversification portfolio optimizer, full-year 2024" },
    ],
  },
  {
    label: "Research & Analysis",
    color: "text-amber-400 border-amber-500/30 hover:border-amber-500/60 hover:bg-amber-500/5",
    examples: [
      { title: "Multi-Factor Alpha Model", desc: "IC-weighted factor synthesis across 300 stocks", prompt: "Build a multi-factor alpha model using momentum, reversal, volatility, and turnover on CSI 300 constituents with IC-weighted factor synthesis, backtest 2023-2024" },
      { title: "Options Greeks Analysis", desc: "Black-Scholes pricing with Delta/Gamma/Theta/Vega", prompt: "Calculate option Greeks using Black-Scholes: spot=100, strike=105, risk-free rate=3%, vol=25%, expiry=90 days, analyze Delta/Gamma/Theta/Vega" },
    ],
  },
  {
    label: "Swarm Teams",
    color: "text-violet-400 border-violet-500/30 hover:border-violet-500/60 hover:bg-violet-500/5",
    examples: [
      { title: "Investment Committee Review", desc: "Multi-agent debate: long vs short, risk review, PM decision", prompt: "[Swarm Team Mode] Use the investment_committee preset to evaluate whether to go long or short on NVDA given current market conditions" },
      { title: "Quant Strategy Desk", desc: "Screening → factor research → backtest → risk audit pipeline", prompt: "[Swarm Team Mode] Use the quant_strategy_desk preset to find and backtest the best momentum strategy on CSI 300 constituents" },
    ],
  },
  {
    label: "Document & Web Research",
    color: "text-blue-400 border-blue-500/30 hover:border-blue-500/60 hover:bg-blue-500/5",
    examples: [
      { title: "Analyze an Earnings Report PDF", desc: "Upload a PDF and ask questions about the financials", prompt: "Summarize the key financial metrics, risks, and outlook from the uploaded earnings report" },
      { title: "Web Research: Macro Outlook", desc: "Read live web sources for macro analysis", prompt: "Read the latest Fed meeting minutes and summarize the key takeaways for equity and crypto markets" },
    ],
  },
  {
    label: "Trade Journal",
    color: "text-orange-400 border-orange-500/30 hover:border-orange-500/60 hover:bg-orange-500/5",
    examples: [
      { title: "Analyze My Broker Export", desc: "Parse 同花顺/东财/富途/generic CSV — holding days, win rate, PnL ratio, hourly distribution", prompt: "Analyze the trade journal I just uploaded — full profile with holding stats, win rate, top symbols, and hourly distribution" },
      { title: "Diagnose My Behavior Biases", desc: "Disposition effect, overtrading, chasing momentum, anchoring — severity + numeric evidence", prompt: "Run the 4 behavior diagnostics on my trade journal (disposition, overtrading, chasing, anchoring) and tell me which bias hurts my PnL most" },
    ],
  },
  {
    label: "Shadow Account",
    color: "text-emerald-400 border-emerald-500/30 hover:border-emerald-500/60 hover:bg-emerald-500/5",
    examples: [
      { title: "Train My Shadow from Journal", desc: "Extract your strategy rules from a broker CSV and persist a Shadow profile", prompt: "Train my shadow account from the trading journal I just uploaded — show the extracted rules and confirm they look like my behavior" },
      { title: "How Much Am I Leaving on the Table?", desc: "Backtest your shadow strategy and attribute delta vs. your actual PnL", prompt: "Run a shadow backtest for the last 90 days on the US market and break down where my PnL diverged from the shadow (rule violations, early exits, missed signals)" },
      { title: "Generate Shadow Report", desc: "8-section HTML/PDF — equity curve, per-market Sharpe, attribution waterfall", prompt: "Render the shadow report and give me the URL — lead with the you-vs-shadow delta" },
    ],
  },
];

const CATEGORIES_ZH: Omit<Category, "icon">[] = [
  {
    label: "跨市场回测",
    color: "text-red-400 border-red-500/30 hover:border-red-500/60 hover:bg-red-500/5",
    examples: [
      { title: "跨市场组合回测", desc: "A股 + 加密 + 美股，风险平价优化", prompt: "用风险平价策略回测 000001.SZ、BTC-USDT、AAPL 组合，2024全年，与等权基准对比" },
      { title: "BTC 5分钟 MACD 策略", desc: "分钟级加密回测，使用 OKX 实时数据", prompt: "回测 BTC-USDT 5分钟 MACD 策略，fast=12 slow=26 signal=9，最近30天" },
      { title: "美股科技最大分散化", desc: "通过 yfinance 对 FAANG+ 进行组合优化", prompt: "回测 AAPL、MSFT、GOOGL、AMZN、NVDA，使用最大分散化组合优化器，2024全年" },
    ],
  },
  {
    label: "研究与分析",
    color: "text-amber-400 border-amber-500/30 hover:border-amber-500/60 hover:bg-amber-500/5",
    examples: [
      { title: "多因子 Alpha 模型", desc: "沪深300成分股 IC 加权因子合成", prompt: "在沪深300成分股上构建多因子 Alpha 模型，使用动量、反转、波动率和换手率因子做IC加权合成，回测2023-2024年" },
      { title: "期权 Greeks 分析", desc: "Black-Scholes 定价，分析 Delta/Gamma/Theta/Vega", prompt: "用Black-Scholes计算期权Greeks：现价=100，行权价=105，无风险利率=3%，波动率=25%，到期=90天，分析 Delta/Gamma/Theta/Vega" },
    ],
  },
  {
    label: "多智能体团队",
    color: "text-violet-400 border-violet-500/30 hover:border-violet-500/60 hover:bg-violet-500/5",
    examples: [
      { title: "投资委员会评审", desc: "多智能体辩论：多空对决、风险审查、PM最终决策", prompt: "[Swarm Team Mode] 用 investment_committee preset 评估当前市场环境下是否应该做多 NVDA" },
      { title: "量化策略团队", desc: "筛选 → 因子研究 → 回测 → 风险审计", prompt: "[Swarm Team Mode] 用 quant_strategy_desk preset 在沪深300成分股中寻找并回测最优动量策略" },
    ],
  },
  {
    label: "文档与网络研究",
    color: "text-blue-400 border-blue-500/30 hover:border-blue-500/60 hover:bg-blue-500/5",
    examples: [
      { title: "分析财报 PDF", desc: "上传 PDF，智能体解读财务数据", prompt: "总结上传财报中的核心财务指标、风险点和业绩展望" },
      { title: "网络研究：宏观展望", desc: "实时读取网页进行宏观分析", prompt: "读取最新美联储会议纪要，总结对股票和加密市场的关键影响" },
    ],
  },
  {
    label: "交易日志",
    color: "text-orange-400 border-orange-500/30 hover:border-orange-500/60 hover:bg-orange-500/5",
    examples: [
      { title: "分析我的券商导出", desc: "解析同花顺/东财/富途/CSV，统计持仓天数、胜率、盈亏比", prompt: "分析我刚上传的交易日志，给出完整画像，包括持仓统计、胜率、高频品种和交易时段分布" },
      { title: "诊断我的行为偏差", desc: "处置效应、过度交易、追涨、锚定 — 严重程度和数据证据", prompt: "对我的交易日志做4类行为诊断（处置效应、过度交易、追涨、锚定），告诉我哪个偏差对收益损伤最大" },
    ],
  },
  {
    label: "Shadow Account",
    color: "text-emerald-400 border-emerald-500/30 hover:border-emerald-500/60 hover:bg-emerald-500/5",
    examples: [
      { title: "从日志训练我的 Shadow", desc: "从券商 CSV 中提取策略规则并持久化 Shadow 画像", prompt: "从我上传的交易日志中训练 Shadow Account，展示提取的规则，确认是否符合我的实际行为" },
      { title: "我错过了多少收益？", desc: "回测 Shadow 策略，归因与实际 PnL 的差距", prompt: "回测最近90天美股的 Shadow 策略，拆解我的 PnL 与 Shadow 的差距（规则违背、过早离场、错过信号）" },
      { title: "生成 Shadow 报告", desc: "8节 HTML/PDF — 净值曲线、分市场夏普、归因瀑布图", prompt: "生成 Shadow 报告并给我 URL，重点展示实际与 Shadow 的 PnL 差距" },
    ],
  },
];

const CHIPS_EN = ["70 Finance Skills","29 Swarm Presets","32 Agent Tools","3 Markets: A-Share · Crypto · HK/US","Minute to Daily Timeframes","4 Portfolio Optimizers","15+ Risk Metrics","Options & Derivatives","PDF & Web Research","Factor Analysis & ML","Trade Journal Analyzer","Shadow Account Backtest","Persistent Memory","Session Search"];
const CHIPS_ZH = ["74个金融技能","29个Swarm预设","32个智能体工具","三大市场：A股·加密·港美股","分钟到日线周期","4种组合优化器","15+风险指标","期权与衍生品","PDF与网络研究","因子分析与机器学习","交易日志分析","Shadow账户回测","持久化记忆","会话搜索"];

const ICONS = [
  <TrendingUp className="h-4 w-4" />,
  <Sparkles className="h-4 w-4" />,
  <Users className="h-4 w-4" />,
  <Globe className="h-4 w-4" />,
  <NotebookPen className="h-4 w-4" />,
  <UserCircle2 className="h-4 w-4" />,
];

interface Props { onExample: (s: string) => void; }

export function WelcomeScreen({ onExample }: Props) {
  const { t, lang } = useI18n();
  const categories = (lang === "zh" ? CATEGORIES_ZH : CATEGORIES_EN).map((c, i) => ({ ...c, icon: ICONS[i] }));
  const chips = lang === "zh" ? CHIPS_ZH : CHIPS_EN;

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 text-center">
      <div className="space-y-3">
        <div className="h-16 w-16 mx-auto rounded-2xl bg-gradient-to-br from-primary/80 to-info/80 flex items-center justify-center shadow-lg">
          <Bot className="h-8 w-8 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Vibe-Trading</h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto leading-relaxed">
            {lang === "zh" ? "你的专业金融智能体团队" : "vibe trading with your professional financial agent team"}
          </p>
          <p className="text-sm text-muted-foreground mt-2 max-w-md leading-relaxed mx-auto">
            {t.describeStrategy}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap justify-center gap-2 max-w-lg">
        {chips.map((chip) => (
          <span key={chip} className="px-2.5 py-1 text-xs rounded-full border border-border/60 text-muted-foreground bg-muted/30">
            {chip}
          </span>
        ))}
      </div>

      <div className="w-full max-w-2xl text-left space-y-4">
        <p className="text-xs text-muted-foreground px-1">{t.examples}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {categories.map((cat) => (
            <div key={cat.label} className="space-y-2">
              <div className={`flex items-center gap-1.5 text-xs font-medium px-1 ${cat.color.split(" ").filter(c => c.startsWith("text-")).join(" ")}`}>
                {cat.icon}
                <span>{cat.label}</span>
              </div>
              <div className="space-y-1.5">
                {cat.examples.map((ex) => (
                  <button
                    key={ex.title}
                    onClick={() => onExample(ex.prompt)}
                    className={`block w-full text-left px-3 py-2.5 rounded-xl border transition-colors ${cat.color}`}
                  >
                    <span className="text-sm font-medium text-foreground leading-snug">{ex.title}</span>
                    <span className="block text-xs text-muted-foreground mt-0.5 leading-snug">{ex.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
