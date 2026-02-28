"""
大模型策略决策引擎
核心：让大模型基于多因子分析做出交易决策
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import yaml
import json

# 加载配置
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'strategy_config.yaml')

@dataclass
class FactorAnalysis:
    """因子分析结果"""
    factor_name: str
    score: float  # 0-100
    weight: float
    reasoning: str
    key_metrics: Dict[str, Any]

@dataclass
class StockAnalysis:
    """个股综合分析"""
    symbol: str
    name: str
    sector: str
    
    # 各维度评分
    technical_score: float
    fundamental_score: float
    sentiment_score: float
    
    # 大模型综合判断
    overall_score: float
    confidence: float  # 置信度
    recommendation: str  # strong_buy / buy / hold / sell / strong_sell
    reasoning: str  # 详细推理过程
    
    # 风险提示
    risk_factors: List[str]
    opportunity_factors: List[str]


class LLMStrategyEngine:
    """
    大模型策略决策引擎
    
    工作流程:
    1. 收集多维度数据（技术面、基本面、情绪面）
    2. 构建prompt，提供给大模型
    3. 解析大模型输出，生成结构化决策
    4. 执行决策并记录
    """
    
    def __init__(self, config_path: str = CONFIG_PATH):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.strategy = self.config['strategy']
        
    def prepare_market_context(self) -> str:
        """
        准备市场环境上下文
        """
        context = f"""
【市场环境分析】日期: {datetime.now().strftime('%Y-%m-%d')}

请基于以下信息判断当前市场状态:

1. 指数走势:
   - 上证指数近期趋势
   - 创业板指表现
   - 成交量变化

2. 板块轮动:
   - 当前强势板块
   - 资金流向
   - 政策热点

3. 情绪指标:
   - Polymarket预测市场情绪
   - 北向资金流向
   - 融资融券余额变化

请给出判断:
- 当前市场处于什么状态？(牛市/震荡/熊市)
- 风险偏好如何？(高/中/低)
- 建议仓位水平？(满仓/重仓/半仓/轻仓/空仓)
- 主要风险点是什么？
"""
        return context
    
    def prepare_factor_analysis_prompt(self, stock_data: Dict) -> str:
        """
        准备因子分析prompt
        """
        prompt = f"""
【股票深度分析】{stock_data.get('name')} ({stock_data.get('symbol')})

=== 技术面分析 ===
价格走势:
- 最新价: {stock_data.get('price')}
- 20日均线: {stock_data.get('ma20')}
- 60日均线: {stock_data.get('ma60')}
- 趋势: {'向上' if stock_data.get('price', 0) > stock_data.get('ma20', 0) else '向下'}

动量指标:
- RSI(14): {stock_data.get('rsi')}
- MACD: {stock_data.get('macd_signal')}
- 成交量: {stock_data.get('volume_trend')}

技术形态:
- 是否突破关键阻力位?
- 是否有金叉/死叉信号?
- 量价配合如何?

=== 基本面分析 ===
估值水平:
- PE: {stock_data.get('pe')}
- PB: {stock_data.get('pb')}
- 行业排名: {stock_data.get('valuation_percentile')}

成长性:
- 营收增长率: {stock_data.get('revenue_growth')}
- 净利润增长率: {stock_data.get('profit_growth')}

财务质量:
- ROE: {stock_data.get('roe')}
- 负债率: {stock_data.get('debt_ratio')}
- 现金流: {stock_data.get('cash_flow')}

=== 情绪与资金 ===
- 近期新闻情绪: {stock_data.get('news_sentiment')}
- 机构持仓变化: {stock_data.get('institutional_change')}
- 散户关注度: {stock_data.get('retail_attention')}

请给出专业分析:
1. 技术面评分 (0-100): ___ 理由:
2. 基本面评分 (0-100): ___ 理由:
3. 情绪面评分 (0-100): ___ 理由:
4. 综合推荐: [强烈买入/买入/持有/卖出/强烈卖出]
5. 目标价位: ___ 止损位: ___
6. 主要风险:
7. 投资逻辑:
"""
        return prompt
    
    def generate_trading_decision(self, 
                                 market_context: str,
                                 portfolio_status: Dict,
                                 candidate_stocks: List[Dict]) -> Dict:
        """
        生成交易决策
        
        这是核心函数，构建完整prompt给大模型
        """
        
        decision_prompt = f"""
你是一个专业的量化投资经理，拥有丰富的A股投资经验。

{market_context}

=== 当前持仓 ===
总仓位: {portfolio_status.get('total_position', 0)}%
现金: {portfolio_status.get('cash', 0)}元
持仓股票:
{json.dumps(portfolio_status.get('holdings', []), indent=2, ensure_ascii=False)}

=== 候选股票池 ===
经过初步筛选的候选股票:
{json.dumps(candidate_stocks[:10], indent=2, ensure_ascii=False)}

=== 决策任务 ===
基于以上信息，请做出投资决策:

1. 市场判断:
   - 当前市场状态评估
   - 建议整体仓位调整（加仓/减仓/维持）
   - 行业配置建议

2. 个股决策（对每只候选股票）:
   - 是否买入？买多少仓位？
   - 是否卖出已有持仓？
   - 持有不动？

3. 风险控制:
   - 需要设置哪些止损止盈？
   - 是否需要对冲操作？

请以JSON格式返回决策:
{{
    "market_assessment": {{
        "state": "牛市/震荡/熊市",
        "confidence": 0.8,
        "suggested_position": 0.7,
        "reasoning": "..."
    }},
    "trading_decisions": [
        {{
            "symbol": "000001",
            "action": "buy/add/hold/sell",
            "position_delta": 0.05,
            "target_price": 15.5,
            "stop_loss": 13.2,
            "reasoning": "..."
        }}
    ],
    "risk_management": {{
        "hedge_needed": false,
        "alerts": ["..."]
    }}
}}
"""
        
        return {
            "prompt": decision_prompt,
            "timestamp": datetime.now().isoformat(),
            "model": self.strategy['llm_config']['primary_model']
        }
    
    def parse_llm_response(self, response: str) -> Dict:
        """
        解析大模型的决策响应
        """
        try:
            # 尝试提取JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                decision = json.loads(json_str)
                return {
                    "status": "success",
                    "decision": decision,
                    "raw_response": response
                }
            else:
                return {
                    "status": "error",
                    "message": "无法从响应中提取JSON",
                    "raw_response": response
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "raw_response": response
            }
    
    def execute_decision(self, decision: Dict) -> Dict:
        """
        执行交易决策
        """
        results = []
        
        for trade in decision.get('trading_decisions', []):
            result = {
                "symbol": trade['symbol'],
                "action": trade['action'],
                "status": "pending",
                "timestamp": datetime.now().isoformat()
            }
            
            # 这里调用实际的交易执行接口
            # 模拟盘或实盘API
            
            results.append(result)
        
        return {
            "execution_time": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total_trades": len(results),
                "buy_count": sum(1 for r in results if r['action'] == 'buy'),
                "sell_count": sum(1 for r in results if r['action'] == 'sell')
            }
        }


def test_llm_engine():
    """测试大模型决策引擎"""
    print("🧪 测试大模型策略决策引擎\n")
    
    engine = LLMStrategyEngine()
    
    # 测试1: 加载配置
    print("1️⃣  加载策略配置...")
    print(f"   ✅ 策略名称: {engine.strategy['name']}")
    print(f"   ✅ 决策模式: {engine.strategy['decision_mode']}")
    print(f"   ✅ 主模型: {engine.strategy['llm_config']['primary_model']}")
    
    # 测试2: 生成市场环境上下文
    print("\n2️⃣  生成市场环境prompt...")
    context = engine.prepare_market_context()
    print(f"   ✅ Prompt长度: {len(context)} 字符")
    
    # 测试3: 生成交易决策框架
    print("\n3️⃣  生成交易决策框架...")
    
    mock_portfolio = {
        "total_position": 0.45,
        "cash": 55000,
        "holdings": [
            {"symbol": "000001", "name": "平安银行", "weight": 0.15}
        ]
    }
    
    mock_candidates = [
        {"symbol": "512760", "name": "芯片ETF", "sector": "科技"},
        {"symbol": "510300", "name": "沪深300ETF", "sector": "宽基"}
    ]
    
    decision_framework = engine.generate_trading_decision(
        market_context=context,
        portfolio_status=mock_portfolio,
        candidate_stocks=mock_candidates
    )
    
    print(f"   ✅ 决策框架已生成")
    print(f"   📋 建议使用模型: {decision_framework['model']}")
    
    print("\n✅ 测试完成！")
    print("\n💡 使用说明:")
    print("   1. 将生成的prompt发送给大模型")
    print("   2. 获取大模型的JSON格式回复")
    print("   3. 使用parse_llm_response解析")
    print("   4. 使用execute_decision执行")


if __name__ == "__main__":
    test_llm_engine()
