#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财报跟踪模块 - Earnings Tracker
负责季报/年报跟踪、业绩预告、分红送股、股权激励
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json


class ReportType(Enum):
    """财报类型"""
    ANNUAL = 'annual'  # 年报
    Q1 = 'q1'  # 一季报
    Q2 = 'q2'  # 中报
    Q3 = 'q3'  # 三季报
    PRELIMINARY = 'preliminary'  # 业绩预告


class DividendType(Enum):
    """分红类型"""
    CASH = 'cash'  # 现金分红
    STOCK = 'stock'  # 送股
    RIGHTS = 'rights'  # 配股


@dataclass
class EarningsReport:
    """财报数据"""
    symbol: str
    report_date: datetime
    report_type: ReportType
    fiscal_year: int
    fiscal_period: str
    
    # 核心数据
    revenue: float
    revenue_yoy: float  # 同比增长
    net_income: float
    net_income_yoy: float
    eps: float
    eps_yoy: float
    
    # 预期对比
    estimated_revenue: float = 0.0
    estimated_eps: float = 0.0
    revenue_surprise: float = 0.0  # 超预期百分比
    eps_surprise: float = 0.0
    
    # 其他指标
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    operating_cash_flow: float = 0.0
    free_cash_flow: float = 0.0
    
    # 指引
    next_quarter_guidance_revenue: float = 0.0
    next_quarter_guidance_eps: float = 0.0
    full_year_guidance_revenue: float = 0.0
    full_year_guidance_eps: float = 0.0
    
    # 会议信息
    conference_call_date: datetime = None
    conference_call_time: str = ''
    
    def __post_init__(self):
        # 计算超预期
        if self.estimated_revenue > 0:
            self.revenue_surprise = (self.revenue - self.estimated_revenue) / self.estimated_revenue * 100
        if self.estimated_eps > 0:
            self.eps_surprise = (self.eps - self.estimated_eps) / self.estimated_eps * 100


@dataclass
class EarningsPreview:
    """业绩预告"""
    symbol: str
    announce_date: datetime
    report_type: ReportType
    fiscal_period: str
    
    # 预告类型
    preview_type: str  # 'pre_announcement', 'warning', 'update'
    
    # 预告数据
    estimated_revenue_min: float = 0.0
    estimated_revenue_max: float = 0.0
    estimated_net_income_min: float = 0.0
    estimated_net_income_max: float = 0.0
    estimated_eps_min: float = 0.0
    estimated_eps_max: float = 0.0
    
    # 同比变化
    yoy_change_min: float = 0.0
    yoy_change_max: float = 0.0
    
    # 预告说明
    description: str = ''
    
    def get_midpoint(self) -> Dict[str, float]:
        """获取预告中值"""
        return {
            'revenue': (self.estimated_revenue_min + self.estimated_revenue_max) / 2,
            'net_income': (self.estimated_net_income_min + self.estimated_net_income_max) / 2,
            'eps': (self.estimated_eps_min + self.estimated_eps_max) / 2,
            'yoy_change': (self.yoy_change_min + self.yoy_change_max) / 2
        }


@dataclass
class DividendInfo:
    """分红送股信息"""
    symbol: str
    announce_date: datetime
    dividend_type: DividendType
    
    # 分红方案
    cash_dividend_per_share: float = 0.0  # 每股现金分红
    stock_dividend_ratio: float = 0.0  # 送股比例 (10 送 X)
    rights_ratio: float = 0.0  # 配股比例
    rights_price: float = 0.0  # 配股价
    
    # 关键日期
    record_date: datetime = None  # 股权登记日
    ex_dividend_date: datetime = None  # 除权除息日
    payment_date: datetime = None  # 派息日
    
    # 分红总额
    total_dividend: float = 0.0
    payout_ratio: float = 0.0  # 分红率
    
    # 股息率
    dividend_yield: float = 0.0
    
    def get_dividend_description(self) -> str:
        """获取分红方案描述"""
        parts = []
        if self.cash_dividend_per_share > 0:
            parts.append(f"每 10 股派{self.cash_dividend_per_share * 10:.2f}元")
        if self.stock_dividend_ratio > 0:
            parts.append(f"每 10 股送{self.stock_dividend_ratio * 10:.1f}股")
        if self.rights_ratio > 0:
            parts.append(f"每 10 股配{self.rights_ratio * 10:.1f}股 (配股价{self.rights_price:.2f}元)")
        return ' '.join(parts) if parts else '无分红'


@dataclass
class StockIncentive:
    """股权激励计划"""
    symbol: str
    announce_date: datetime
    plan_type: str  # 'restricted_stock', 'stock_option', 'espp'
    
    # 激励对象
    target_employees: int = 0  # 激励人数
    key_executives: List[str] = field(default_factory=list)
    
    # 激励规模
    total_shares: float = 0.0  # 总股数
    total_value: float = 0.0  # 总价值
    percent_of_capital: float = 0.0  # 占总股本比例
    
    # 授予价格
    grant_price: float = 0.0
    current_price: float = 0.0
    discount: float = 0.0  # 折扣率
    
    # 解锁/行权条件
    vesting_period: int = 0  # 锁定期 (年)
    performance_targets: List[Dict] = field(default_factory=list)
    
    # 状态
    status: str = 'proposed'  # proposed, approved, implemented
    
    def get_incentive_description(self) -> str:
        """获取激励计划描述"""
        return f"{self.plan_type}: {self.total_shares:.1f}万股，占总股本{self.percent_of_capital:.2f}%"


class EarningsTracker:
    """财报跟踪器"""
    
    def __init__(self):
        self.earnings_reports: List[EarningsReport] = []
        self.previews: List[EarningsPreview] = []
        self.dividends: List[DividendInfo] = []
        self.incentives: List[StockIncentive] = []
        self.watchlist: List[str] = []  # 跟踪的股票列表
    
    def add_to_watchlist(self, symbols: List[str]):
        """添加到跟踪列表"""
        self.watchlist.extend(symbols)
        self.watchlist = list(set(self.watchlist))
    
    def add_earnings_report(self, report: EarningsReport):
        """添加财报"""
        self.earnings_reports.append(report)
        self.earnings_reports.sort(key=lambda x: x.report_date, reverse=True)
    
    def add_preview(self, preview: EarningsPreview):
        """添加业绩预告"""
        self.previews.append(preview)
    
    def add_dividend(self, dividend: DividendInfo):
        """添加分红信息"""
        self.dividends.append(dividend)
    
    def add_incentive(self, incentive: StockIncentive):
        """添加股权激励"""
        self.incentives.append(incentive)
    
    # ==================== 财报日历 ====================
    
    def get_earnings_calendar(self, start_date: datetime = None, 
                               end_date: datetime = None,
                               symbols: List[str] = None) -> List[Dict[str, any]]:
        """
        获取财报日历
        """
        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        calendar = []
        
        # 筛选日期范围和股票
        for report in self.earnings_reports:
            if start_date <= report.report_date <= end_date:
                if symbols is None or report.symbol in symbols:
                    calendar.append({
                        'symbol': report.symbol,
                        'report_date': report.report_date.isoformat(),
                        'report_type': report.report_type.value,
                        'fiscal_period': report.fiscal_period,
                        'estimated_eps': report.estimated_eps,
                        'estimated_revenue': report.estimated_revenue,
                        'conference_call': report.conference_call_time if report.conference_call_date else None
                    })
        
        calendar.sort(key=lambda x: x['report_date'])
        return calendar
    
    def get_upcoming_earnings(self, days: int = 7, symbols: List[str] = None) -> List[Dict[str, any]]:
        """获取未来 N 天的财报"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        return self.get_earnings_calendar(start_date, end_date, symbols)
    
    # ==================== 财报分析 ====================
    
    def analyze_earnings_surprise(self, symbol: str, periods: int = 4) -> Dict[str, any]:
        """
        分析财报超预期情况
        """
        reports = [r for r in self.earnings_reports if r.symbol == symbol]
        reports = reports[:periods] if len(reports) > periods else reports
        
        if not reports:
            return {'error': 'No earnings data found'}
        
        surprises = []
        beat_count = 0
        
        for report in reports:
            surprise_data = {
                'report_date': report.report_date.isoformat(),
                'fiscal_period': report.fiscal_period,
                'eps_actual': report.eps,
                'eps_estimated': report.estimated_eps,
                'eps_surprise': report.eps_surprise,
                'revenue_actual': report.revenue,
                'revenue_estimated': report.estimated_revenue,
                'revenue_surprise': report.revenue_surprise,
                'beat_eps': report.eps_surprise > 0,
                'beat_revenue': report.revenue_surprise > 0
            }
            surprises.append(surprise_data)
            
            if report.eps_surprise > 0:
                beat_count += 1
        
        return {
            'symbol': symbol,
            'periods_analyzed': len(reports),
            'eps_beat_rate': round(beat_count / len(reports) * 100, 1) if reports else 0,
            'avg_eps_surprise': round(np.mean([r.eps_surprise for r in reports]), 2) if reports else 0,
            'avg_revenue_surprise': round(np.mean([r.revenue_surprise for r in reports]), 2) if reports else 0,
            'surprises': surprises
        }
    
    def analyze_earnings_trend(self, symbol: str) -> Dict[str, any]:
        """
        分析财报趋势
        """
        reports = [r for r in self.earnings_reports if r.symbol == symbol]
        reports.sort(key=lambda x: x.report_date)
        
        if len(reports) < 2:
            return {'error': 'Insufficient data'}
        
        # 计算趋势
        revenue_trend = [r.revenue for r in reports]
        eps_trend = [r.eps for r in reports]
        
        # 计算增长率
        revenue_growth = [(revenue_trend[i] - revenue_trend[i-1]) / revenue_trend[i-1] * 100 
                         for i in range(1, len(revenue_trend))]
        eps_growth = [(eps_trend[i] - eps_trend[i-1]) / eps_trend[i-1] * 100 
                     for i in range(1, len(eps_trend))]
        
        return {
            'symbol': symbol,
            'periods': len(reports),
            'revenue_trend': {
                'latest': revenue_trend[-1],
                'avg_growth': round(np.mean(revenue_growth), 2) if revenue_growth else 0,
                'direction': 'up' if revenue_growth and revenue_growth[-1] > 0 else 'down'
            },
            'eps_trend': {
                'latest': eps_trend[-1],
                'avg_growth': round(np.mean(eps_growth), 2) if eps_growth else 0,
                'direction': 'up' if eps_growth and eps_growth[-1] > 0 else 'down'
            },
            'margin_trend': {
                'latest_gross_margin': reports[-1].gross_margin,
                'latest_operating_margin': reports[-1].operating_margin
            }
        }
    
    # ==================== 业绩预告分析 ====================
    
    def get_latest_preview(self, symbol: str) -> Optional[EarningsPreview]:
        """获取最新业绩预告"""
        previews = [p for p in self.previews if p.symbol == symbol]
        if not previews:
            return None
        previews.sort(key=lambda x: x.announce_date, reverse=True)
        return previews[0]
    
    def analyze_preview_accuracy(self, symbol: str) -> Dict[str, any]:
        """
        分析业绩预告准确性
        """
        previews = [p for p in self.previews if p.symbol == symbol]
        
        accuracy_data = []
        for preview in previews:
            # 查找对应的实际财报
            actual = next((r for r in self.earnings_reports 
                          if r.symbol == symbol and r.fiscal_period == preview.fiscal_period), None)
            
            if actual:
                preview_mid = preview.get_midpoint()
                accuracy_data.append({
                    'fiscal_period': preview.fiscal_period,
                    'preview_eps_mid': preview_mid['eps'],
                    'actual_eps': actual.eps,
                    'accuracy': 100 - abs(actual.eps - preview_mid['eps']) / preview_mid['eps'] * 100 if preview_mid['eps'] > 0 else 0,
                    'preview_revenue_mid': preview_mid['revenue'],
                    'actual_revenue': actual.revenue
                })
        
        if not accuracy_data:
            return {'error': 'No matching data found'}
        
        avg_accuracy = np.mean([d['accuracy'] for d in accuracy_data])
        
        return {
            'symbol': symbol,
            'previews_analyzed': len(accuracy_data),
            'avg_accuracy': round(avg_accuracy, 2),
            'accuracy_rating': 'High' if avg_accuracy >= 90 else 'Medium' if avg_accuracy >= 80 else 'Low',
            'details': accuracy_data
        }
    
    # ==================== 分红分析 ====================
    
    def get_dividend_history(self, symbol: str, years: int = 5) -> List[DividendInfo]:
        """获取分红历史"""
        cutoff_date = datetime.now() - timedelta(days=years*365)
        dividends = [d for d in self.dividends 
                    if d.symbol == symbol and d.announce_date >= cutoff_date]
        dividends.sort(key=lambda x: x.announce_date, reverse=True)
        return dividends
    
    def analyze_dividend_policy(self, symbol: str) -> Dict[str, any]:
        """
        分析分红政策
        """
        dividends = self.get_dividend_history(symbol)
        
        if not dividends:
            return {'error': 'No dividend data found'}
        
        cash_dividends = [d for d in dividends if d.dividend_type == DividendType.CASH]
        
        if not cash_dividends:
            return {'error': 'No cash dividend data found'}
        
        # 计算分红指标
        total_dividends = sum(d.cash_dividend_per_share for d in cash_dividends)
        avg_yield = np.mean([d.dividend_yield for d in cash_dividends if d.dividend_yield > 0])
        avg_payout = np.mean([d.payout_ratio for d in cash_dividends if d.payout_ratio > 0])
        
        # 分红增长
        if len(cash_dividends) >= 2:
            recent = cash_dividends[0].cash_dividend_per_share
            older = cash_dividends[-1].cash_dividend_per_share
            growth_rate = (recent - older) / older * 100 if older > 0 else 0
        else:
            growth_rate = 0
        
        # 分红连续性
        years_with_dividend = len(set(d.announce_date.year for d in cash_dividends))
        
        return {
            'symbol': symbol,
            'years_analyzed': years_with_dividend,
            'total_dividends': round(total_dividends, 2),
            'avg_dividend_yield': round(avg_yield, 2),
            'avg_payout_ratio': round(avg_payout, 2),
            'dividend_growth_rate': round(growth_rate, 2),
            'consecutive_years': years_with_dividend,
            'dividend_aristocrat': years_with_dividend >= 5 and growth_rate > 0,
            'recent_dividends': [
                {
                    'announce_date': d.announce_date.isoformat(),
                    'cash_per_share': d.cash_dividend_per_share,
                    'yield': d.dividend_yield,
                    'description': d.get_dividend_description()
                }
                for d in cash_dividends[:5]
            ]
        }
    
    # ==================== 股权激励分析 ====================
    
    def get_incentive_plans(self, symbol: str) -> List[StockIncentive]:
        """获取股权激励计划"""
        return [i for i in self.incentives if i.symbol == symbol]
    
    def analyze_incentive_impact(self, symbol: str) -> Dict[str, any]:
        """
        分析股权激励影响
        """
        incentives = self.get_incentive_plans(symbol)
        
        if not incentives:
            return {'error': 'No incentive plan found'}
        
        latest = incentives[-1]  # 最新计划
        
        # 稀释影响
        dilution = latest.percent_of_capital
        
        # 激励力度评估
        if latest.percent_of_capital >= 3:
            intensity = 'High'
        elif latest.percent_of_capital >= 1:
            intensity = 'Medium'
        else:
            intensity = 'Low'
        
        # 解锁条件分析
        performance_conditions = []
        for target in latest.performance_targets:
            performance_conditions.append({
                'metric': target.get('metric'),
                'target': target.get('target'),
                'period': target.get('period')
            })
        
        return {
            'symbol': symbol,
            'plan_type': latest.plan_type,
            'total_shares': latest.total_shares,
            'percent_of_capital': latest.percent_of_capital,
            'grant_price': latest.grant_price,
            'current_price': latest.current_price,
            'upside_potential': round((latest.current_price - latest.grant_price) / latest.grant_price * 100, 2) if latest.grant_price > 0 else 0,
            'vesting_period': latest.vesting_period,
            'dilution_impact': round(dilution, 2),
            'incentive_intensity': intensity,
            'performance_conditions': performance_conditions,
            'status': latest.status
        }
    
    # ==================== 综合财报评分 ====================
    
    def earnings_quality_score(self, symbol: str) -> Dict[str, any]:
        """
        财报质量综合评分
        """
        score = 0
        factors = {}
        
        # 1. 超预期记录 (30 分)
        surprise_analysis = self.analyze_earnings_surprise(symbol)
        if 'error' not in surprise_analysis:
            beat_rate = surprise_analysis['eps_beat_rate']
            if beat_rate >= 75:
                factors['surprise'] = 30
            elif beat_rate >= 50:
                factors['surprise'] = 20
            else:
                factors['surprise'] = 10
            score += factors['surprise']
        
        # 2. 增长趋势 (25 分)
        trend_analysis = self.analyze_earnings_trend(symbol)
        if 'error' not in trend_analysis:
            if trend_analysis['revenue_trend']['direction'] == 'up' and \
               trend_analysis['eps_trend']['direction'] == 'up':
                factors['trend'] = 25
            elif trend_analysis['revenue_trend']['direction'] == 'up':
                factors['trend'] = 15
            else:
                factors['trend'] = 5
            score += factors['trend']
        
        # 3. 分红记录 (20 分)
        dividend_analysis = self.analyze_dividend_policy(symbol)
        if 'error' not in dividend_analysis:
            if dividend_analysis.get('dividend_aristocrat'):
                factors['dividend'] = 20
            elif dividend_analysis['consecutive_years'] >= 3:
                factors['dividend'] = 15
            elif dividend_analysis['consecutive_years'] >= 1:
                factors['dividend'] = 10
            else:
                factors['dividend'] = 0
            score += factors['dividend']
        
        # 4. 业绩预告准确性 (15 分)
        preview_accuracy = self.analyze_preview_accuracy(symbol)
        if 'error' not in preview_accuracy:
            if preview_accuracy['accuracy_rating'] == 'High':
                factors['preview'] = 15
            elif preview_accuracy['accuracy_rating'] == 'Medium':
                factors['preview'] = 10
            else:
                factors['preview'] = 5
            score += factors['preview']
        
        # 5. 股权激励 (10 分)
        incentive_analysis = self.analyze_incentive_impact(symbol)
        if 'error' not in incentive_analysis:
            if incentive_analysis['incentive_intensity'] == 'Medium':
                factors['incentive'] = 10
            elif incentive_analysis['incentive_intensity'] == 'Low':
                factors['incentive'] = 5
            else:
                factors['incentive'] = 3  # 过高可能有稀释风险
            score += factors['incentive']
        
        # 评级
        if score >= 85:
            rating = 'A+'
        elif score >= 75:
            rating = 'A'
        elif score >= 65:
            rating = 'B+'
        elif score >= 55:
            rating = 'B'
        elif score >= 45:
            rating = 'C'
        else:
            rating = 'D'
        
        return {
            'symbol': symbol,
            'total_score': score,
            'rating': rating,
            'factors': factors,
            'report_date': datetime.now().isoformat()
        }
    
    # ==================== 财报事件提醒 ====================
    
    def get_earnings_alerts(self, symbols: List[str] = None) -> List[Dict[str, any]]:
        """获取财报事件提醒"""
        alerts = []
        
        target_symbols = symbols if symbols else self.watchlist
        
        for symbol in target_symbols:
            # 即将发布的财报
            upcoming = self.get_upcoming_earnings(7, [symbol])
            for report in upcoming:
                alerts.append({
                    'type': 'earnings_release',
                    'symbol': symbol,
                    'message': f"{symbol} 将于 {report['report_date']} 发布 {report['report_type']} 财报",
                    'date': report['report_date'],
                    'priority': 'high'
                })
            
            # 分红除息日
            dividends = [d for d in self.dividends if d.symbol == symbol]
            for div in dividends:
                if div.ex_dividend_date:
                    days_to_ex = (div.ex_dividend_date - datetime.now()).days
                    if 0 <= days_to_ex <= 7:
                        alerts.append({
                            'type': 'ex_dividend',
                            'symbol': symbol,
                            'message': f"{symbol} 将于 {div.ex_dividend_date.strftime('%Y-%m-%d')} 除息，每股{div.cash_dividend_per_share:.2f}元",
                            'date': div.ex_dividend_date.isoformat(),
                            'priority': 'medium'
                        })
        
        alerts.sort(key=lambda x: x['date'])
        return alerts
    
    # ==================== 生成财报报告 ====================
    
    def generate_earnings_report(self, symbol: str) -> Dict[str, any]:
        """生成完整的财报跟踪报告"""
        return {
            'symbol': symbol,
            'report_date': datetime.now().isoformat(),
            'latest_earnings': self.analyze_earnings_surprise(symbol),
            'earnings_trend': self.analyze_earnings_trend(symbol),
            'dividend_analysis': self.analyze_dividend_policy(symbol),
            'incentive_analysis': self.analyze_incentive_impact(symbol),
            'quality_score': self.earnings_quality_score(symbol),
            'upcoming_events': self.get_upcoming_earnings(30, [symbol]),
            'alerts': self.get_earnings_alerts([symbol])
        }


# 导入 numpy (在文件顶部)
import numpy as np


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 示例用法
    tracker = EarningsTracker()
    
    # 添加示例财报
    report = EarningsReport(
        symbol='AAPL',
        report_date=datetime(2024, 12, 31),
        report_type=ReportType.Q1,
        fiscal_year=2024,
        fiscal_period='Q1 2024',
        revenue=120000000000,
        revenue_yoy=0.08,
        net_income=35000000000,
        net_income_yoy=0.10,
        eps=2.15,
        eps_yoy=0.12,
        estimated_revenue=118000000000,
        estimated_eps=2.10,
        gross_margin=44.0,
        operating_margin=30.0
    )
    
    tracker.add_earnings_report(report)
    
    # 生成报告
    report = tracker.generate_earnings_report('AAPL')
    print(f"财报质量评分：{report['quality_score']['total_score']}")
    print(f"评级：{report['quality_score']['rating']}")
