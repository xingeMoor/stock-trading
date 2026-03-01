#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
估值模型模块 - Valuation Models
负责 DCF 模型、PE/PB/PS 估值、EV/EBITDA、相对估值
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np


@dataclass
class ValuationInput:
    """估值输入参数"""
    symbol: str
    current_price: float
    shares_outstanding: float
    market_cap: float
    
    # 财务数据
    free_cash_flow: float
    revenue: float
    net_income: float
    ebitda: float
    total_equity: float
    total_debt: float
    cash_and_equivalents: float
    
    # 增长假设
    revenue_growth_rate: float = 0.0
    fcf_growth_rate: float = 0.0
    terminal_growth_rate: float = 0.02
    
    # 风险参数
    beta: float = 1.0
    risk_free_rate: float = 0.04
    equity_risk_premium: float = 0.06
    cost_of_debt: float = 0.05
    tax_rate: float = 0.25


class ValuationModels:
    """估值模型集合"""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
    
    # ==================== DCF 模型 ====================
    
    def calculate_wacc(self, input_data: ValuationInput) -> float:
        """
        计算加权平均资本成本 (WACC)
        WACC = (E/V) × Re + (D/V) × Rd × (1-T)
        """
        equity_value = input_data.market_cap
        debt_value = input_data.total_debt
        total_value = equity_value + debt_value
        
        if total_value == 0:
            return 0.10  # 默认 10%
        
        # 股权成本 (CAPM)
        cost_of_equity = input_data.risk_free_rate + input_data.beta * input_data.equity_risk_premium
        
        # WACC
        wacc = (equity_value / total_value) * cost_of_equity + \
               (debt_value / total_value) * input_data.cost_of_debt * (1 - input_data.tax_rate)
        
        return round(wacc, 4)
    
    def dcf_model(self, input_data: ValuationInput, forecast_years: int = 5) -> Dict[str, float]:
        """
        自由现金流折现模型 (DCF)
        计算企业价值和股权价值
        """
        wacc = self.calculate_wacc(input_data)
        
        if wacc <= input_data.terminal_growth_rate:
            return {'error': 'WACC must be greater than terminal growth rate'}
        
        # 预测期 FCF
        fcf_projections = []
        current_fcf = input_data.free_cash_flow
        
        for year in range(1, forecast_years + 1):
            projected_fcf = current_fcf * (1 + input_data.fcf_growth_rate) ** year
            fcf_projections.append(projected_fcf)
        
        # 终值 (Gordon Growth Model)
        terminal_fcf = fcf_projections[-1] * (1 + input_data.terminal_growth_rate)
        terminal_value = terminal_fcf / (wacc - input_data.terminal_growth_rate)
        
        # 折现
        pv_fcf = sum([fcf / (1 + wacc) ** (i + 1) for i, fcf in enumerate(fcf_projections)])
        pv_terminal = terminal_value / (1 + wacc) ** forecast_years
        
        # 企业价值
        enterprise_value = pv_fcf + pv_terminal
        
        # 股权价值
        equity_value = enterprise_value - input_data.total_debt + input_data.cash_and_equivalents
        
        # 每股价值
        intrinsic_value_per_share = equity_value / input_data.shares_outstanding
        
        # 安全边际
        margin_of_safety = (intrinsic_value_per_share - input_data.current_price) / input_data.current_price
        
        return {
            'wacc': round(wacc * 100, 2),
            'enterprise_value': round(enterprise_value, 2),
            'equity_value': round(equity_value, 2),
            'intrinsic_value_per_share': round(intrinsic_value_per_share, 2),
            'current_price': input_data.current_price,
            'margin_of_safety': round(margin_of_safety * 100, 2),
            'recommendation': self._get_recommendation(margin_of_safety),
            'pv_fcf': round(pv_fcf, 2),
            'pv_terminal': round(pv_terminal, 2),
            'terminal_value': round(terminal_value, 2)
        }
    
    def dcf_sensitivity_analysis(self, input_data: ValuationInput, 
                                  wacc_range: List[float] = None,
                                  growth_range: List[float] = None) -> Dict[str, any]:
        """
        DCF 敏感性分析
        分析 WACC 和永续增长率变化对估值的影响
        """
        if wacc_range is None:
            wacc_range = [0.06, 0.08, 0.10, 0.12, 0.14]
        if growth_range is None:
            growth_range = [0.01, 0.02, 0.03, 0.04]
        
        sensitivity_matrix = []
        
        for wacc in wacc_range:
            row = {'wacc': wacc}
            for growth in growth_range:
                input_data.terminal_growth_rate = growth
                # 临时修改 WACC 计算
                original_risk_free = input_data.risk_free_rate
                input_data.risk_free_rate = wacc  # 简化处理
                result = self.dcf_model(input_data)
                row[f'g_{int(growth*100)}'] = result.get('intrinsic_value_per_share', 0)
                input_data.risk_free_rate = original_risk_free
            sensitivity_matrix.append(row)
        
        return {
            'sensitivity_matrix': sensitivity_matrix,
            'wacc_range': [w * 100 for w in wacc_range],
            'growth_range': [g * 100 for g in growth_range]
        }
    
    # ==================== 相对估值法 ====================
    
    def pe_valuation(self, input_data: ValuationInput, 
                     industry_pe: float = None,
                     historical_pe_avg: float = None) -> Dict[str, float]:
        """
        PE 估值法
        基于行业 PE 和历史 PE 进行估值
        """
        current_pe = input_data.market_cap / input_data.net_income if input_data.net_income > 0 else 0
        
        valuations = {}
        
        # 基于行业 PE
        if industry_pe and industry_pe > 0:
            industry_value = input_data.net_income * industry_pe
            valuations['industry_based'] = {
                'pe_used': industry_pe,
                'implied_value': round(industry_value, 2),
                'implied_price': round(industry_value / input_data.shares_outstanding, 2)
            }
        
        # 基于历史 PE
        if historical_pe_avg and historical_pe_avg > 0:
            historical_value = input_data.net_income * historical_pe_avg
            valuations['historical_based'] = {
                'pe_used': historical_pe_avg,
                'implied_value': round(historical_value, 2),
                'implied_price': round(historical_value / input_data.shares_outstanding, 2)
            }
        
        # 当前估值
        valuations['current'] = {
            'pe': round(current_pe, 2),
            'market_cap': round(input_data.market_cap, 2)
        }
        
        return valuations
    
    def pb_valuation(self, input_data: ValuationInput,
                     industry_pb: float = None) -> Dict[str, float]:
        """
        PB 估值法 (市净率)
        适用于重资产行业
        """
        current_pb = input_data.market_cap / input_data.total_equity if input_data.total_equity > 0 else 0
        
        valuations = {}
        
        if industry_pb and industry_pb > 0:
            industry_value = input_data.total_equity * industry_pb
            valuations['industry_based'] = {
                'pb_used': industry_pb,
                'implied_value': round(industry_value, 2),
                'implied_price': round(industry_value / input_data.shares_outstanding, 2)
            }
        
        valuations['current'] = {
            'pb': round(current_pb, 2),
            'book_value_per_share': round(input_data.total_equity / input_data.shares_outstanding, 2)
        }
        
        return valuations
    
    def ps_valuation(self, input_data: ValuationInput,
                     industry_ps: float = None) -> Dict[str, float]:
        """
        PS 估值法 (市销率)
        适用于高增长未盈利公司
        """
        current_ps = input_data.market_cap / input_data.revenue if input_data.revenue > 0 else 0
        
        valuations = {}
        
        if industry_ps and industry_ps > 0:
            industry_value = input_data.revenue * industry_ps
            valuations['industry_based'] = {
                'ps_used': industry_ps,
                'implied_value': round(industry_value, 2),
                'implied_price': round(industry_value / input_data.shares_outstanding, 2)
            }
        
        valuations['current'] = {
            'ps': round(current_ps, 2),
            'revenue_per_share': round(input_data.revenue / input_data.shares_outstanding, 2)
        }
        
        return valuations
    
    def ev_ebitda_valuation(self, input_data: ValuationInput,
                            industry_ev_ebitda: float = None) -> Dict[str, float]:
        """
        EV/EBITDA 估值法
        适用于资本密集型行业
        """
        enterprise_value = input_data.market_cap + input_data.total_debt - input_data.cash_and_equivalents
        current_ev_ebitda = enterprise_value / input_data.ebitda if input_data.ebitda > 0 else 0
        
        valuations = {}
        
        if industry_ev_ebitda and industry_ev_ebitda > 0:
            implied_ev = input_data.ebitda * industry_ev_ebitda
            implied_equity = implied_ev - input_data.total_debt + input_data.cash_and_equivalents
            valuations['industry_based'] = {
                'ev_ebitda_used': industry_ev_ebitda,
                'implied_ev': round(implied_ev, 2),
                'implied_equity_value': round(implied_equity, 2),
                'implied_price': round(implied_equity / input_data.shares_outstanding, 2)
            }
        
        valuations['current'] = {
            'ev': round(enterprise_value, 2),
            'ev_ebitda': round(current_ev_ebitda, 2),
            'ebitda': round(input_data.ebitda, 2)
        }
        
        return valuations
    
    # ==================== PEG 估值 ====================
    
    def peg_valuation(self, input_data: ValuationInput,
                      expected_growth_rate: float = None) -> Dict[str, float]:
        """
        PEG 估值法
        PE 与增长率的比值，适用于成长股
        """
        current_pe = input_data.market_cap / input_data.net_income if input_data.net_income > 0 else 0
        growth_rate = expected_growth_rate if expected_growth_rate else input_data.fcf_growth_rate
        
        if growth_rate <= 0:
            return {'error': 'Growth rate must be positive for PEG calculation'}
        
        peg = current_pe / (growth_rate * 100)
        
        # PEG 解读
        if peg < 1:
            interpretation = 'undervalued'
        elif peg < 1.5:
            interpretation = 'fairly_valued'
        else:
            interpretation = 'overvalued'
        
        return {
            'pe': round(current_pe, 2),
            'growth_rate': round(growth_rate * 100, 2),
            'peg': round(peg, 2),
            'interpretation': interpretation
        }
    
    # ==================== 综合估值 ====================
    
    def comprehensive_valuation(self, input_data: ValuationInput,
                                industry_comparables: Dict[str, float] = None) -> Dict[str, any]:
        """
        综合估值 - 整合多种估值方法
        """
        results = {}
        
        # DCF 估值
        results['dcf'] = self.dcf_model(input_data)
        
        # 相对估值
        if industry_comparables:
            results['pe_valuation'] = self.pe_valuation(
                input_data, 
                industry_pe=industry_comparables.get('pe')
            )
            results['pb_valuation'] = self.pb_valuation(
                input_data,
                industry_pb=industry_comparables.get('pb')
            )
            results['ps_valuation'] = self.ps_valuation(
                input_data,
                industry_ps=industry_comparables.get('ps')
            )
            results['ev_ebitda'] = self.ev_ebitda_valuation(
                input_data,
                industry_ev_ebitda=industry_comparables.get('ev_ebitda')
            )
        
        # PEG
        results['peg'] = self.peg_valuation(input_data)
        
        # 综合目标价
        target_prices = []
        if 'dcf' in results and 'intrinsic_value_per_share' in results['dcf']:
            target_prices.append(results['dcf']['intrinsic_value_per_share'])
        
        if 'pe_valuation' in results and 'industry_based' in results['pe_valuation']:
            target_prices.append(results['pe_valuation']['industry_based']['implied_price'])
        
        if 'ev_ebitda' in results and 'industry_based' in results['ev_ebitda']:
            target_prices.append(results['ev_ebitda']['industry_based']['implied_price'])
        
        if target_prices:
            avg_target = np.mean(target_prices)
            results['consensus'] = {
                'target_price': round(avg_target, 2),
                'upside': round((avg_target - input_data.current_price) / input_data.current_price * 100, 2),
                'methodologies_used': len(target_prices)
            }
        
        return results
    
    def _get_recommendation(self, margin_of_safety: float) -> str:
        """基于安全边际给出投资建议"""
        if margin_of_safety >= 0.3:
            return 'STRONG_BUY'
        elif margin_of_safety >= 0.15:
            return 'BUY'
        elif margin_of_safety >= 0:
            return 'HOLD'
        elif margin_of_safety >= -0.15:
            return 'REDUCE'
        else:
            return 'SELL'
    
    # ==================== 估值报告生成 ====================
    
    def generate_valuation_report(self, input_data: ValuationInput,
                                  industry_comparables: Dict[str, float] = None) -> Dict[str, any]:
        """生成完整的估值报告"""
        return {
            'symbol': input_data.symbol,
            'report_date': datetime.now().isoformat(),
            'current_price': input_data.current_price,
            'market_cap': round(input_data.market_cap, 2),
            'comprehensive_valuation': self.comprehensive_valuation(input_data, industry_comparables),
            'key_metrics': {
                'pe': round(input_data.market_cap / input_data.net_income, 2) if input_data.net_income > 0 else None,
                'pb': round(input_data.market_cap / input_data.total_equity, 2) if input_data.total_equity > 0 else None,
                'ps': round(input_data.market_cap / input_data.revenue, 2) if input_data.revenue > 0 else None,
                'ev_ebitda': round((input_data.market_cap + input_data.total_debt - input_data.cash_and_equivalents) / input_data.ebitda, 2) if input_data.ebitda > 0 else None
            },
            'assumptions': {
                'fcf_growth_rate': input_data.fcf_growth_rate * 100,
                'terminal_growth_rate': input_data.terminal_growth_rate * 100,
                'beta': input_data.beta,
                'risk_free_rate': input_data.risk_free_rate * 100
            }
        }


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 示例用法
    valuator = ValuationModels()
    
    # 创建估值输入
    input_data = ValuationInput(
        symbol='AAPL',
        current_price=175.0,
        shares_outstanding=15500000000,
        market_cap=2712500000000,
        free_cash_flow=100000000000,
        revenue=385000000000,
        net_income=97000000000,
        ebitda=125000000000,
        total_equity=60000000000,
        total_debt=110000000000,
        cash_and_equivalents=50000000000,
        fcf_growth_rate=0.08,
        beta=1.2
    )
    
    # 行业对比数据
    industry_comps = {
        'pe': 28.0,
        'pb': 45.0,
        'ps': 7.0,
        'ev_ebitda': 22.0
    }
    
    # 生成估值报告
    report = valuator.generate_valuation_report(input_data, industry_comps)
    print(f"综合目标价：${report['comprehensive_valuation']['consensus']['target_price']}")
    print(f"上涨空间：{report['comprehensive_valuation']['consensus']['upside']}%")
