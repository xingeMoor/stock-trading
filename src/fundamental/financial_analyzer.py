#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务分析模块 - Financial Analyzer
负责三大报表解析、财务比率计算、杜邦分析、趋势分析
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class FinancialStatement:
    """财务报表数据结构"""
    symbol: str
    report_date: datetime
    report_type: str  # 'annual', 'quarterly'
    currency: str = 'CNY'
    
    # 资产负债表项目
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    total_equity: float = 0.0
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    cash_and_equivalents: float = 0.0
    accounts_receivable: float = 0.0
    inventory: float = 0.0
    fixed_assets: float = 0.0
    long_term_debt: float = 0.0
    
    # 利润表项目
    revenue: float = 0.0
    gross_profit: float = 0.0
    operating_profit: float = 0.0
    net_income: float = 0.0
    ebitda: float = 0.0
    operating_expenses: float = 0.0
    
    # 现金流量表项目
    operating_cash_flow: float = 0.0
    investing_cash_flow: float = 0.0
    financing_cash_flow: float = 0.0
    free_cash_flow: float = 0.0
    capex: float = 0.0


class FinancialAnalyzer:
    """财务分析器"""
    
    def __init__(self):
        self.statements: List[FinancialStatement] = []
    
    def add_statement(self, statement: FinancialStatement):
        """添加财务报表"""
        self.statements.append(statement)
        self.statements.sort(key=lambda x: x.report_date)
    
    # ==================== 财务比率计算 ====================
    
    def calculate_liquidity_ratios(self, statement: FinancialStatement) -> Dict[str, float]:
        """计算流动性比率"""
        if statement.current_liabilities == 0:
            return {'current_ratio': 0.0, 'quick_ratio': 0.0, 'cash_ratio': 0.0}
        
        current_ratio = statement.current_assets / statement.current_liabilities
        quick_ratio = (statement.current_assets - statement.inventory) / statement.current_liabilities
        cash_ratio = statement.cash_and_equivalents / statement.current_liabilities
        
        return {
            'current_ratio': round(current_ratio, 3),
            'quick_ratio': round(quick_ratio, 3),
            'cash_ratio': round(cash_ratio, 3)
        }
    
    def calculate_profitability_ratios(self, statement: FinancialStatement) -> Dict[str, float]:
        """计算盈利能力比率"""
        if statement.revenue == 0:
            return {'gross_margin': 0.0, 'operating_margin': 0.0, 'net_margin': 0.0, 'roe': 0.0, 'roa': 0.0}
        
        gross_margin = (statement.gross_profit / statement.revenue) * 100
        operating_margin = (statement.operating_profit / statement.revenue) * 100
        net_margin = (statement.net_income / statement.revenue) * 100
        roe = (statement.net_income / statement.total_equity) * 100 if statement.total_equity > 0 else 0
        roa = (statement.net_income / statement.total_assets) * 100 if statement.total_assets > 0 else 0
        
        return {
            'gross_margin': round(gross_margin, 2),
            'operating_margin': round(operating_margin, 2),
            'net_margin': round(net_margin, 2),
            'roe': round(roe, 2),
            'roa': round(roa, 2)
        }
    
    def calculate_leverage_ratios(self, statement: FinancialStatement) -> Dict[str, float]:
        """计算杠杆比率"""
        if statement.total_assets == 0:
            return {'debt_to_asset': 0.0, 'debt_to_equity': 0.0, 'equity_multiplier': 0.0}
        
        total_debt = statement.long_term_debt + statement.current_liabilities
        debt_to_asset = (total_debt / statement.total_assets) * 100
        debt_to_equity = (total_debt / statement.total_equity) * 100 if statement.total_equity > 0 else 0
        equity_multiplier = statement.total_assets / statement.total_equity if statement.total_equity > 0 else 0
        
        return {
            'debt_to_asset': round(debt_to_asset, 2),
            'debt_to_equity': round(debt_to_equity, 2),
            'equity_multiplier': round(equity_multiplier, 3)
        }
    
    def calculate_efficiency_ratios(self, statement: FinancialStatement) -> Dict[str, float]:
        """计算效率比率"""
        if statement.revenue == 0:
            return {'asset_turnover': 0.0, 'inventory_turnover': 0.0, 'receivables_turnover': 0.0}
        
        asset_turnover = statement.revenue / statement.total_assets if statement.total_assets > 0 else 0
        inventory_turnover = statement.revenue / statement.inventory if statement.inventory > 0 else 0
        receivables_turnover = statement.revenue / statement.accounts_receivable if statement.accounts_receivable > 0 else 0
        
        return {
            'asset_turnover': round(asset_turnover, 3),
            'inventory_turnover': round(inventory_turnover, 3),
            'receivables_turnover': round(receivables_turnover, 3)
        }
    
    def calculate_cash_flow_ratios(self, statement: FinancialStatement) -> Dict[str, float]:
        """计算现金流量比率"""
        if statement.current_liabilities == 0:
            return {'operating_cash_flow_ratio': 0.0, 'free_cash_flow_yield': 0.0}
        
        operating_cash_flow_ratio = statement.operating_cash_flow / statement.current_liabilities
        fcf_yield = (statement.free_cash_flow / statement.revenue) * 100 if statement.revenue > 0 else 0
        
        return {
            'operating_cash_flow_ratio': round(operating_cash_flow_ratio, 3),
            'free_cash_flow_yield': round(fcf_yield, 2)
        }
    
    def get_all_ratios(self, statement: FinancialStatement) -> Dict[str, Dict[str, float]]:
        """获取所有财务比率"""
        return {
            'liquidity': self.calculate_liquidity_ratios(statement),
            'profitability': self.calculate_profitability_ratios(statement),
            'leverage': self.calculate_leverage_ratios(statement),
            'efficiency': self.calculate_efficiency_ratios(statement),
            'cash_flow': self.calculate_cash_flow_ratios(statement)
        }
    
    # ==================== 杜邦分析 ====================
    
    def dupont_analysis(self, statement: FinancialStatement) -> Dict[str, float]:
        """
        杜邦分析 - 分解 ROE
        ROE = 净利润率 × 总资产周转率 × 权益乘数
        """
        if statement.revenue == 0 or statement.total_assets == 0 or statement.total_equity == 0:
            return {'roe': 0.0, 'net_margin': 0.0, 'asset_turnover': 0.0, 'equity_multiplier': 0.0}
        
        net_margin = statement.net_income / statement.revenue
        asset_turnover = statement.revenue / statement.total_assets
        equity_multiplier = statement.total_assets / statement.total_equity
        roe = net_margin * asset_turnover * equity_multiplier
        
        return {
            'roe': round(roe * 100, 2),
            'net_margin': round(net_margin * 100, 2),
            'asset_turnover': round(asset_turnover, 3),
            'equity_multiplier': round(equity_multiplier, 3)
        }
    
    def extended_dupont_analysis(self, statement: FinancialStatement) -> Dict[str, float]:
        """
        扩展杜邦分析 - 5 因素模型
        ROE = 税负 × 利息负担 × 营业利润率 × 资产周转率 × 权益乘数
        """
        # 简化版本，实际需要根据更详细的利润表数据
        base = self.dupont_analysis(statement)
        
        # 计算营业利润率和利息负担 (简化)
        operating_margin = statement.operating_profit / statement.revenue if statement.revenue > 0 else 0
        tax_burden = statement.net_income / statement.operating_profit if statement.operating_profit > 0 else 1
        
        return {
            **base,
            'operating_margin': round(operating_margin * 100, 2),
            'tax_burden': round(tax_burden, 3)
        }
    
    # ==================== 趋势分析 ====================
    
    def trend_analysis(self, metric: str, periods: int = 5) -> Dict[str, float]:
        """
        趋势分析 - 计算指定指标的增长趋势
        """
        if len(self.statements) < 2:
            return {'cagr': 0.0, 'avg_growth': 0.0, 'trend': 'stable'}
        
        recent = self.statements[-periods:] if len(self.statements) >= periods else self.statements
        
        values = [getattr(s, metric, 0) for s in recent]
        if not values or values[0] == 0:
            return {'cagr': 0.0, 'avg_growth': 0.0, 'trend': 'stable'}
        
        # 计算复合年增长率 (CAGR)
        n = len(values) - 1
        if n > 0 and values[0] > 0:
            cagr = ((values[-1] / values[0]) ** (1/n) - 1) * 100
        else:
            cagr = 0.0
        
        # 计算平均增长率
        growth_rates = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                growth_rates.append((values[i] - values[i-1]) / values[i-1] * 100)
        
        avg_growth = np.mean(growth_rates) if growth_rates else 0.0
        
        # 判断趋势
        if cagr > 15:
            trend = 'high_growth'
        elif cagr > 5:
            trend = 'growth'
        elif cagr > 0:
            trend = 'slow_growth'
        elif cagr > -10:
            trend = 'decline'
        else:
            trend = 'sharp_decline'
        
        return {
            'cagr': round(cagr, 2),
            'avg_growth': round(avg_growth, 2),
            'trend': trend,
            'periods': n
        }
    
    def financial_health_score(self, statement: FinancialStatement) -> Dict[str, any]:
        """
        财务健康度评分 (0-100)
        基于多个维度综合评估
        """
        ratios = self.get_all_ratios(statement)
        score = 0
        factors = {}
        
        # 流动性 (20 分)
        current_ratio = ratios['liquidity']['current_ratio']
        if current_ratio >= 2:
            factors['liquidity'] = 20
        elif current_ratio >= 1.5:
            factors['liquidity'] = 15
        elif current_ratio >= 1:
            factors['liquidity'] = 10
        else:
            factors['liquidity'] = max(0, current_ratio * 10)
        
        # 盈利能力 (30 分)
        roe = ratios['profitability']['roe']
        if roe >= 20:
            factors['profitability'] = 30
        elif roe >= 15:
            factors['profitability'] = 25
        elif roe >= 10:
            factors['profitability'] = 20
        elif roe >= 5:
            factors['profitability'] = 15
        else:
            factors['profitability'] = max(0, roe * 2)
        
        # 杠杆水平 (20 分)
        debt_to_equity = ratios['leverage']['debt_to_equity']
        if debt_to_equity <= 50:
            factors['leverage'] = 20
        elif debt_to_equity <= 100:
            factors['leverage'] = 15
        elif debt_to_equity <= 150:
            factors['leverage'] = 10
        else:
            factors['leverage'] = max(0, 20 - debt_to_equity / 20)
        
        # 现金流 (20 分)
        ocf_ratio = ratios['cash_flow']['operating_cash_flow_ratio']
        if ocf_ratio >= 1:
            factors['cash_flow'] = 20
        elif ocf_ratio >= 0.7:
            factors['cash_flow'] = 15
        elif ocf_ratio >= 0.4:
            factors['cash_flow'] = 10
        else:
            factors['cash_flow'] = max(0, ocf_ratio * 20)
        
        # 运营效率 (10 分)
        asset_turnover = ratios['efficiency']['asset_turnover']
        if asset_turnover >= 1:
            factors['efficiency'] = 10
        elif asset_turnover >= 0.7:
            factors['efficiency'] = 7
        elif asset_turnover >= 0.4:
            factors['efficiency'] = 5
        else:
            factors['efficiency'] = max(0, asset_turnover * 10)
        
        score = sum(factors.values())
        
        # 评级
        if score >= 85:
            rating = 'AAA'
        elif score >= 75:
            rating = 'AA'
        elif score >= 65:
            rating = 'A'
        elif score >= 55:
            rating = 'BBB'
        elif score >= 45:
            rating = 'BB'
        elif score >= 35:
            rating = 'B'
        else:
            rating = 'C'
        
        return {
            'total_score': round(score, 1),
            'rating': rating,
            'factors': factors,
            'report_date': statement.report_date.isoformat()
        }
    
    def generate_financial_report(self, statement: FinancialStatement) -> Dict[str, any]:
        """生成完整的财务分析报告"""
        return {
            'symbol': statement.symbol,
            'report_date': statement.report_date.isoformat(),
            'report_type': statement.report_type,
            'ratios': self.get_all_ratios(statement),
            'dupont': self.dupont_analysis(statement),
            'health_score': self.financial_health_score(statement),
            'trends': {
                'revenue': self.trend_analysis('revenue'),
                'net_income': self.trend_analysis('net_income'),
                'operating_cash_flow': self.trend_analysis('operating_cash_flow')
            }
        }


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 示例用法
    analyzer = FinancialAnalyzer()
    
    # 创建示例财报数据
    statement = FinancialStatement(
        symbol='AAPL',
        report_date=datetime(2024, 12, 31),
        report_type='annual',
        total_assets=350000000000,
        total_liabilities=290000000000,
        total_equity=60000000000,
        current_assets=140000000000,
        current_liabilities=130000000000,
        cash_and_equivalents=50000000000,
        revenue=385000000000,
        gross_profit=170000000000,
        operating_profit=115000000000,
        net_income=97000000000,
        operating_cash_flow=110000000000,
        free_cash_flow=100000000000
    )
    
    analyzer.add_statement(statement)
    
    # 生成报告
    report = analyzer.generate_financial_report(statement)
    print(f"财务健康评分：{report['health_score']['total_score']}")
    print(f"评级：{report['health_score']['rating']}")
    print(f"ROE: {report['ratios']['profitability']['roe']}%")
