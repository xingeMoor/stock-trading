"""
Quant Agent - 大模型量化交易Agent
核心决策流程：数据收集 → LLM分析 → 决策执行 → 复盘反馈
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import yaml

# 导入各模块
from data_provider import DataProvider
from stock_selector import StockSelector
from llm_strategy_engine import LLMStrategyEngine
from auto_trader import AutoTrader
from polymarket_sentiment import PolymarketSentiment

@dataclass
class DailyReport:
    """每日投资报告"""
    date: str
    market_summary: str
    positions_review: List[Dict]
    trading_signals: List[Dict]
    risk_assessment: str
    tomorrow_outlook: str


class QuantAgent:
    """
    量化交易Agent - 核心控制器
    
    工作流程:
    Phase 1: 盘前准备 (9:00-9:25)
    Phase 2: 开盘交易 (9:30-15:00)
    Phase 3: 盘后复盘 (15:05-16:00)
    """
    
    def __init__(self, account_id: str = "main", mode: str = "paper"):
        self.account_id = account_id
        self.mode = mode
        
        # 初始化各组件
        self.data = DataProvider()
        self.selector = StockSelector()
        self.llm_engine = LLMStrategyEngine()
        self.trader = AutoTrader(account_id, mode)
        self.sentiment = PolymarketSentiment()
        
        # 加载配置
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'strategy_config.yaml')
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
    
    # ==================== Phase 1: 盘前准备 ====================
    
    def pre_market_analysis(self) -> Dict[str, Any]:
        """
        盘前分析 (9:00-9:25执行)
        
        收集所有信息，为开盘做准备
        """
        print("\n" + "="*60)
        print("🌅 Phase 1: 盘前准备")
        print("="*60)
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "market_context": {},
            "stock_pool": [],
            "sentiment": {},
            "portfolio_status": {}
        }
        
        # 1. 市场环境扫描
        print("\n📊 1. 市场环境扫描...")
        try:
            # 获取主要指数
            indices = {
                "上证指数": self.data.get_realtime("000001", "A股"),
                "深证成指": self.data.get_realtime("399001", "A股"),
                "创业板指": self.data.get_realtime("399006", "A股"),
            }
            
            analysis["market_context"]["indices"] = indices
            print(f"   ✅ 指数数据获取完成")
        except Exception as e:
            print(f"   ⚠️  {e}")
        
        # 2. 板块强度分析
        print("\n📈 2. 板块强度分析...")
        try:
            sectors = self.selector.get_sector_strength()
            top_sectors = sectors.head(10).to_dict('records') if not sectors.empty else []
            analysis["market_context"]["top_sectors"] = top_sectors
            print(f"   ✅ TOP10板块: {[s.get('板块名称') for s in top_sectors[:5]]}")
        except Exception as e:
            print(f"   ⚠️  {e}")
        
        # 3. 选股池筛选
        print("\n🎯 3. 选股池筛选...")
        try:
            selected = self.selector.select_stocks(
                max_stocks=20,
                min_score=60
            )
            analysis["stock_pool"] = [
                {
                    "symbol": s.symbol,
                    "name": s.name,
                    "sector": s.sector,
                    "score": s.total_score,
                    "signals": s.metrics.get('details', {})
                }
                for s in selected
            ]
            print(f"   ✅ 选出 {len(selected)} 只股票")
        except Exception as e:
            print(f"   ⚠️  {e}")
        
        # 4. 市场情绪
        print("\n💭 4. 市场情绪监测...")
        try:
            sentiment = self.sentiment.get_economy_sentiment()
            analysis["sentiment"] = sentiment
            print(f"   ✅ 情绪评分: {sentiment.get('sentiment_score', 'N/A')}")
        except Exception as e:
            print(f"   ⚠️  {e}")
        
        # 5. 当前持仓
        print("\n💼 5. 当前持仓状态...")
        positions = self.trader.positions
        cash = self.trader.cash
        total_value = self.trader._get_total_value()
        
        analysis["portfolio_status"] = {
            "total_value": total_value,
            "cash": cash,
            "cash_ratio": cash / total_value if total_value > 0 else 0,
            "positions_count": len(positions),
            "positions": [
                {
                    "symbol": sym,
                    "shares": pos['shares'],
                    "avg_cost": pos['average_cost'],
                    "current_price": pos['current_price'],
                    "pnl_pct": (pos['current_price'] - pos['average_cost']) / pos['average_cost'] * 100
                }
                for sym, pos in positions.items()
            ]
        }
        print(f"   ✅ 总资产: ¥{total_value:,.2f}, 现金比例: {cash/total_value*100:.1f}%")
        
        return analysis
    
    # ==================== Phase 2: LLM决策生成 ====================
    
    def generate_llm_prompt(self, analysis: Dict) -> str:
        """
        生成给大模型的完整决策prompt
        """
        
        prompt = f"""
你是一位资深的量化投资经理，拥有10年A股投资经验。请基于以下信息做出今日投资决策。

## 📅 日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 一、市场环境概览

### 主要指数
"""
        
        # 添加指数信息
        for name, data in analysis.get('market_context', {}).get('indices', {}).items():
            if 'error' not in data:
                prompt += f"- {name}: {data.get('price')} ({data.get('change_pct', 0):+.2f}%)\n"
        
        # 添加板块信息
        prompt += f"\n### 强势板块\n"
        for sector in analysis.get('market_context', {}).get('top_sectors', [])[:5]:
            prompt += f"- {sector.get('板块名称')}: +{sector.get('涨跌幅', 0)}%\n"
        
        # 添加情绪
        sentiment = analysis.get('sentiment', {})
        prompt += f"\n### 市场情绪\n"
        prompt += f"- Polymarket情绪评分: {sentiment.get('sentiment_score', 'N/A')}\n"
        prompt += f"- 解读: {sentiment.get('interpretation', 'N/A')}\n"
        
        # 添加持仓
        portfolio = analysis.get('portfolio_status', {})
        prompt += f"\n## 二、当前持仓状况\n"
        prompt += f"- 总资产: ¥{portfolio.get('total_value', 0):,.2f}\n"
        prompt += f"- 现金: ¥{portfolio.get('cash', 0):,.2f} ({portfolio.get('cash_ratio', 0)*100:.1f}%)\n"
        prompt += f"- 持仓股票数: {portfolio.get('positions_count', 0)}\n"
        
        if portfolio.get('positions'):
            prompt += "\n持仓明细:\n"
            for pos in portfolio['positions'][:5]:
                emoji = "🟢" if pos.get('pnl_pct', 0) > 0 else "🔴"
                prompt += f"- {pos['symbol']}: {pos['shares']}股, 成本¥{pos['avg_cost']:.2f}, 盈亏{pos['pnl_pct']:+.2f}% {emoji}\n"
        
        # 添加候选股票
        prompt += f"\n## 三、今日候选股票池 (已初步筛选)\n"
        for stock in analysis.get('stock_pool', [])[:10]:
            prompt += f"\n{stock['symbol']} {stock['name']} ({stock['sector']})\n"
            prompt += f"- 综合评分: {stock['score']:.0f}/100\n"
            signals = stock.get('signals', {})
            for k, v in signals.items():
                prompt += f"- {k}: {v}\n"
        
        # 决策指令
        prompt += f"""

---

## 四、决策任务

请作为投资经理，做出以下决策:

### 1. 市场整体判断
- 当前市场处于什么状态？（牛市/震荡/熊市）
- 今日风险偏好如何？（高/中/低）
- 建议整体仓位水平？

### 2. 持仓股票操作 (对每只持仓)
分析是否继续持有、加仓还是减仓，并说明理由。

### 3. 新买入标的 (从候选池中选择)
- 选择哪些股票买入？
- 每只买入多少仓位？
- 目标价和止损价设置？

### 4. 风险控制
- 需要设置哪些止损？
- 有什么风险需要警惕？

---

## 五、输出格式

请以JSON格式返回你的决策:

```json
{{
  "market_assessment": {{
    "state": "牛市/震荡/熊市",
    "confidence": 0.8,
    "risk_appetite": "高/中/低",
    "suggested_position": 0.7,
    "reasoning": "简要分析..."
  }},
  "position_adjustments": [
    {{
      "symbol": "现有持仓代码",
      "action": "hold/add/reduce/sell",
      "target_weight": 0.15,
      "reasoning": "分析理由..."
    }}
  ],
  "new_positions": [
    {{
      "symbol": "新买入代码",
      "weight": 0.10,
      "target_price": 15.5,
      "stop_loss": 13.2,
      "reasoning": "买入逻辑..."
    }}
  ],
  "risk_management": {{
    "stop_losses": ["symbol: price"],
    "alerts": ["风险提示1", "风险提示2"],
    "hedge_suggestions": ["对冲建议"]
  }},
  "trading_plan": {{
    "morning": "早盘计划",
    "intraday": "盘中调整策略",
    "closing": "尾盘操作"
  }}
}}
```

请确保你的分析专业、全面，并考虑到风险控制。
"""
        
        return prompt
    
    def call_llm_for_decision(self, prompt: str) -> Dict[str, Any]:
        """
        调用大模型获取决策
        
        这里接入实际的LLM API
        """
        print("\n🤖 正在请求大模型决策...")
        print(f"   Prompt长度: {len(prompt)} 字符")
        
        # TODO: 接入实际的大模型API
        # 目前返回模拟决策用于测试
        
        mock_decision = {
            "market_assessment": {
                "state": "震荡市",
                "confidence": 0.75,
                "risk_appetite": "中等",
                "suggested_position": 0.65,
                "reasoning": "指数处于震荡区间，板块轮动明显，建议控制仓位精选个股"
            },
            "position_adjustments": [],
            "new_positions": [
                {
                    "symbol": "512760",
                    "weight": 0.12,
                    "target_price": 1.95,
                    "stop_loss": 1.70,
                    "reasoning": "芯片ETF技术形态良好，政策利好半导体行业，RSI处于合理区间"
                }
            ],
            "risk_management": {
                "stop_losses": [],
                "alerts": ["关注美联储议息会议", "注意成交量变化"],
                "hedge_suggestions": []
            },
            "trading_plan": {
                "morning": "观察开盘后资金流向",
                "intraday": "逢低分批建仓",
                "closing": "评估当日表现"
            }
        }
        
        print("   ✅ 收到大模型决策")
        return mock_decision
    
    # ==================== Phase 3: 执行与复盘 ====================
    
    def execute_decision(self, decision: Dict) -> List[Dict]:
        """执行交易决策"""
        print("\n" + "="*60)
        print("⚡ Phase 3: 执行交易决策")
        print("="*60)
        
        results = self.trader.process_llm_decision(decision)
        
        print(f"\n✅ 执行完成: {len(results)} 笔交易")
        return results
    
    def generate_daily_report(self, analysis: Dict, decision: Dict, executions: List) -> DailyReport:
        """生成每日投资报告"""
        
        report = DailyReport(
            date=datetime.now().strftime('%Y-%m-%d'),
            market_summary=f"市场状态: {decision.get('market_assessment', {}).get('state', '未知')}",
            positions_review=[],
            trading_signals=decision.get('new_positions', []),
            risk_assessment=decision.get('risk_management', {}).get('alerts', ['无特殊风险'])[0],
            tomorrow_outlook="继续跟踪市场动向"
        )
        
        return report
    
    # ==================== 主流程 ====================
    
    def run_daily_workflow(self):
        """运行完整日常工作流"""
        print("\n" + "🚀"*30)
        print("   Quant Agent - 每日投资决策系统")
        print("🚀"*30)
        
        # Phase 1: 盘前分析
        analysis = self.pre_market_analysis()
        
        # Phase 2: LLM决策
        prompt = self.generate_llm_prompt(analysis)
        decision = self.call_llm_for_decision(prompt)
        
        # Phase 3: 执行交易
        executions = self.execute_decision(decision)
        
        # 生成报告
        report = self.generate_daily_report(analysis, decision, executions)
        
        print("\n" + "="*60)
        print("📋 今日投资简报")
        print("="*60)
        print(f"日期: {report.date}")
        print(f"市场: {report.market_summary}")
        print(f"交易: {len(report.trading_signals)} 个新信号")
        print(f"风险: {report.risk_assessment}")
        print(f"展望: {report.tomorrow_outlook}")
        print("="*60)
        
        return {
            "analysis": analysis,
            "decision": decision,
            "executions": executions,
            "report": report
        }


def test_quant_agent():
    """测试Quant Agent"""
    print("🧪 测试 Quant Agent 完整流程\n")
    
    agent = QuantAgent(account_id="test", mode="paper")
    
    # 运行完整工作流
    result = agent.run_daily_workflow()
    
    print("\n✅ 完整流程测试成功！")
    print(f"\n📊 结果摘要:")
    print(f"   - 分析了 {len(result['analysis'].get('stock_pool', []))} 只候选股票")
    print(f"   - 生成了 {len(result['decision'].get('new_positions', []))} 个交易信号")
    print(f"   - 执行了 {len(result['executions'])} 笔交易")


if __name__ == "__main__":
    test_quant_agent()
