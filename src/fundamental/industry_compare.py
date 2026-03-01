#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业对比模块 - Industry Comparison
负责行业均值对比、竞争对手分析、行业排名、护城河评估
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd


@dataclass
class CompanyMetrics:
    """公司指标数据"""
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap: float
    
    # 估值指标
    pe_ratio: float
    pb_ratio: float
    ps_ratio: float
    ev_ebitda: float
    peg_ratio: float
    
    # 盈利能力
    roe: float
    roa: float
    gross_margin: float
    operating_margin: float
    net_margin: float
    
    # 增长指标
    revenue_growth: float
    earnings_growth: float
    fcf_growth: float
    
    # 财务健康
    debt_to_equity: float
    current_ratio: float
    interest_coverage: float
    
    # 护城河指标
    moat_score: float = 0.0
    competitive_advantage: str = ''


@dataclass
class IndustryMetrics:
    """行业指标汇总"""
    industry_name: str
    sector: str
    company_count: int
    
    # 行业均值
    avg_pe: float
    avg_pb: float
    avg_ps: float
    avg_ev_ebitda: float
    avg_roe: float
    avg_roa: float
    avg_gross_margin: float
    avg_net_margin: float
    avg_debt_to_equity: float
    
    # 行业中位数
    median_pe: float
    median_roe: float
    median_revenue_growth: float
    
    # 行业分位数
    pe_25th: float
    pe_75th: float
    roe_25th: float
    roe_75th: float


class IndustryComparator:
    """行业对比分析器"""
    
    def __init__(self):
        self.companies: List[CompanyMetrics] = []
        self.industry_data: Dict[str, IndustryMetrics] = {}
    
    def add_company(self, company: CompanyMetrics):
        """添加公司数据"""
        self.companies.append(company)
    
    def set_industry_data(self, industry: IndustryMetrics):
        """设置行业数据"""
        self.industry_data[industry.industry_name] = industry
    
    # ==================== 行业均值对比 ====================
    
    def calculate_industry_averages(self, industry_name: str = None) -> IndustryMetrics:
        """
        计算行业平均值和中位数
        """
        if industry_name:
            filtered = [c for c in self.companies if c.industry == industry_name]
        else:
            filtered = self.companies
        
        if not filtered:
            return None
        
        # 提取各项指标
        pe_values = [c.pe_ratio for c in filtered if c.pe_ratio > 0]
        pb_values = [c.pb_ratio for c in filtered if c.pb_ratio > 0]
        ps_values = [c.ps_ratio for c in filtered if c.ps_ratio > 0]
        ev_ebitda_values = [c.ev_ebitda for c in filtered if c.ev_ebitda > 0]
        roe_values = [c.roe for c in filtered]
        roa_values = [c.roa for c in filtered]
        gross_margin_values = [c.gross_margin for c in filtered]
        net_margin_values = [c.net_margin for c in filtered]
        dte_values = [c.debt_to_equity for c in filtered]
        revenue_growth_values = [c.revenue_growth for c in filtered]
        
        def safe_mean(values):
            return np.mean(values) if values else 0.0
        
        def safe_median(values):
            return np.median(values) if values else 0.0
        
        def percentile(values, p):
            return np.percentile(values, p) if values else 0.0
        
        return IndustryMetrics(
            industry_name=industry_name or 'All',
            sector=filtered[0].sector if filtered else '',
            company_count=len(filtered),
            avg_pe=safe_mean(pe_values),
            avg_pb=safe_mean(pb_values),
            avg_ps=safe_mean(ps_values),
            avg_ev_ebitda=safe_mean(ev_ebitda_values),
            avg_roe=safe_mean(roe_values),
            avg_roa=safe_mean(roa_values),
            avg_gross_margin=safe_mean(gross_margin_values),
            avg_net_margin=safe_mean(net_margin_values),
            avg_debt_to_equity=safe_mean(dte_values),
            median_pe=safe_median(pe_values),
            median_roe=safe_median(roe_values),
            median_revenue_growth=safe_median(revenue_growth_values),
            pe_25th=percentile(pe_values, 25),
            pe_75th=percentile(pe_values, 75),
            roe_25th=percentile(roe_values, 25),
            roe_75th=percentile(roe_values, 75)
        )
    
    def compare_to_industry(self, symbol: str) -> Dict[str, any]:
        """
        将公司与行业均值对比
        """
        company = next((c for c in self.companies if c.symbol == symbol), None)
        if not company:
            return {'error': 'Company not found'}
        
        industry = self.industry_data.get(company.industry)
        if not industry:
            industry = self.calculate_industry_averages(company.industry)
        
        if not industry:
            return {'error': 'Industry data not available'}
        
        comparison = {
            'symbol': symbol,
            'company_name': company.name,
            'industry': company.industry,
            'metrics': {}
        }
        
        # 估值对比
        comparison['metrics']['valuation'] = {
            'pe': {
                'company': company.pe_ratio,
                'industry_avg': industry.avg_pe,
                'vs_industry': round((company.pe_ratio - industry.avg_pe) / industry.avg_pe * 100, 2) if industry.avg_pe > 0 else 0,
                'percentile': self._calculate_percentile(company.pe_ratio, [c.pe_ratio for c in self.companies if c.industry == company.industry and c.pe_ratio > 0])
            },
            'pb': {
                'company': company.pb_ratio,
                'industry_avg': industry.avg_pb,
                'vs_industry': round((company.pb_ratio - industry.avg_pb) / industry.avg_pb * 100, 2) if industry.avg_pb > 0 else 0
            },
            'ps': {
                'company': company.ps_ratio,
                'industry_avg': industry.avg_ps,
                'vs_industry': round((company.ps_ratio - industry.avg_ps) / industry.avg_ps * 100, 2) if industry.avg_ps > 0 else 0
            }
        }
        
        # 盈利能力对比
        comparison['metrics']['profitability'] = {
            'roe': {
                'company': company.roe,
                'industry_avg': industry.avg_roe,
                'vs_industry': round(company.roe - industry.avg_roe, 2),
                'percentile': self._calculate_percentile(company.roe, [c.roe for c in self.companies if c.industry == company.industry])
            },
            'roa': {
                'company': company.roa,
                'industry_avg': industry.avg_roa,
                'vs_industry': round(company.roa - industry.avg_roa, 2)
            },
            'net_margin': {
                'company': company.net_margin,
                'industry_avg': industry.avg_net_margin,
                'vs_industry': round(company.net_margin - industry.avg_net_margin, 2)
            }
        }
        
        # 财务健康对比
        comparison['metrics']['financial_health'] = {
            'debt_to_equity': {
                'company': company.debt_to_equity,
                'industry_avg': industry.avg_debt_to_equity,
                'vs_industry': round(company.debt_to_equity - industry.avg_debt_to_equity, 2)
            },
            'current_ratio': {
                'company': company.current_ratio,
                'industry_avg': 'N/A'  # 需要添加行业数据
            }
        }
        
        return comparison
    
    def _calculate_percentile(self, value: float, values: List[float]) -> float:
        """计算百分位"""
        if not values:
            return 0.0
        rank = sum(1 for v in values if v < value)
        return round(rank / len(values) * 100, 1)
    
    # ==================== 竞争对手分析 ====================
    
    def find_competitors(self, symbol: str, top_n: int = 5) -> List[Dict[str, any]]:
        """
        找出最接近的竞争对手
        基于市值和业务范围相似度
        """
        target = next((c for c in self.companies if c.symbol == symbol), None)
        if not target:
            return []
        
        # 同行业其他公司
        peers = [c for c in self.companies if c.symbol != symbol and c.industry == target.industry]
        
        if not peers:
            # 如果没有同行业公司，找同板块的
            peers = [c for c in self.companies if c.symbol != symbol and c.sector == target.sector]
        
        # 按市值差异排序
        for peer in peers:
            peer.market_cap_diff = abs(peer.market_cap - target.market_cap)
        
        peers.sort(key=lambda x: x.market_cap_diff)
        
        competitors = []
        for peer in peers[:top_n]:
            competitors.append({
                'symbol': peer.symbol,
                'name': peer.name,
                'market_cap': peer.market_cap,
                'market_cap_ratio': round(peer.market_cap / target.market_cap, 2),
                'pe_ratio': peer.pe_ratio,
                'roe': peer.roe,
                'revenue_growth': peer.revenue_growth
            })
        
        return competitors
    
    def competitive_positioning(self, symbol: str) -> Dict[str, any]:
        """
        竞争定位分析
        """
        company = next((c for c in self.companies if c.symbol == symbol), None)
        if not company:
            return {'error': 'Company not found'}
        
        competitors = self.find_competitors(symbol)
        
        # 构建对比矩阵
        metrics_to_compare = ['pe_ratio', 'roe', 'revenue_growth', 'net_margin', 'debt_to_equity']
        
        positioning = {
            'symbol': symbol,
            'company_name': company.name,
            'competitors': competitors,
            'comparison_matrix': []
        }
        
        for metric in metrics_to_compare:
            company_value = getattr(company, metric)
            competitor_values = [getattr(c, metric) for c in competitors]
            
            positioning['comparison_matrix'].append({
                'metric': metric,
                'company': company_value,
                'competitor_avg': round(np.mean(competitor_values), 2) if competitor_values else 0,
                'competitor_max': round(max(competitor_values), 2) if competitor_values else 0,
                'competitor_min': round(min(competitor_values), 2) if competitor_values else 0,
                'company_rank': sum(1 for v in competitor_values if v < company_value) + 1
            })
        
        return positioning
    
    # ==================== 行业排名 ====================
    
    def industry_ranking(self, industry_name: str = None, 
                         metric: str = 'roe',
                         top_n: int = 10) -> List[Dict[str, any]]:
        """
        行业排名
        """
        if industry_name:
            filtered = [c for c in self.companies if c.industry == industry_name]
        else:
            filtered = self.companies
        
        # 按指定指标排序
        filtered.sort(key=lambda x: getattr(x, metric, 0), reverse=True)
        
        rankings = []
        for i, company in enumerate(filtered[:top_n]):
            rankings.append({
                'rank': i + 1,
                'symbol': company.symbol,
                'name': company.name,
                'market_cap': company.market_cap,
                metric: getattr(company, metric),
                'pe_ratio': company.pe_ratio,
                'revenue_growth': company.revenue_growth
            })
        
        return rankings
    
    def multi_metric_ranking(self, industry_name: str = None) -> Dict[str, List[Dict]]:
        """
        多指标综合排名
        """
        metrics = ['roe', 'revenue_growth', 'net_margin', 'pe_ratio']
        
        rankings = {}
        for metric in metrics:
            # PE 越低越好，其他越高越好
            reverse = metric != 'pe_ratio'
            rankings[metric] = self.industry_ranking(industry_name, metric, top_n=20)
        
        # 综合评分
        company_scores = {}
        for metric, ranking in rankings.items():
            for i, item in enumerate(ranking):
                symbol = item['symbol']
                if symbol not in company_scores:
                    company_scores[symbol] = {'total_score': 0, 'name': item['name']}
                
                # 排名得分 (排名越靠前得分越高)
                score = 20 - i
                company_scores[symbol]['total_score'] += score
        
        # 综合排名
        comprehensive = sorted(
            [{'symbol': k, 'name': v['name'], 'composite_score': v['total_score']} 
             for k, v in company_scores.items()],
            key=lambda x: x['composite_score'],
            reverse=True
        )
        
        rankings['comprehensive'] = comprehensive[:20]
        
        return rankings
    
    # ==================== 护城河评估 ====================
    
    def evaluate_moat(self, symbol: str) -> Dict[str, any]:
        """
        护城河评估
        基于多个维度评估公司的竞争优势
        """
        company = next((c for c in self.companies if c.symbol == symbol), None)
        if not company:
            return {'error': 'Company not found'}
        
        moat_analysis = {
            'symbol': symbol,
            'company_name': company.name,
            'dimensions': {},
            'total_score': 0,
            'moat_rating': 'None'
        }
        
        # 1. 盈利能力护城河 (高 ROE 持续性)
        if company.roe >= 20:
            moat_analysis['dimensions']['profitability'] = {'score': 25, 'reason': 'ROE >= 20%, 卓越盈利能力'}
        elif company.roe >= 15:
            moat_analysis['dimensions']['profitability'] = {'score': 20, 'reason': 'ROE >= 15%, 强劲盈利能力'}
        elif company.roe >= 10:
            moat_analysis['dimensions']['profitability'] = {'score': 15, 'reason': 'ROE >= 10%, 良好盈利能力'}
        else:
            moat_analysis['dimensions']['profitability'] = {'score': 5, 'reason': 'ROE < 10%, 盈利能力一般'}
        
        # 2. 利润率护城河 (高毛利率)
        if company.gross_margin >= 50:
            moat_analysis['dimensions']['margin'] = {'score': 20, 'reason': '毛利率 >= 50%, 强定价权'}
        elif company.gross_margin >= 30:
            moat_analysis['dimensions']['margin'] = {'score': 15, 'reason': '毛利率 >= 30%, 一定定价权'}
        else:
            moat_analysis['dimensions']['margin'] = {'score': 5, 'reason': '毛利率 < 30%, 竞争激烈'}
        
        # 3. 增长护城河 (持续增长)
        if company.revenue_growth >= 20 and company.earnings_growth >= 20:
            moat_analysis['dimensions']['growth'] = {'score': 20, 'reason': '营收和利润双增长 >= 20%'}
        elif company.revenue_growth >= 10:
            moat_analysis['dimensions']['growth'] = {'score': 15, 'reason': '营收增长 >= 10%'}
        else:
            moat_analysis['dimensions']['growth'] = {'score': 5, 'reason': '增长放缓'}
        
        # 4. 财务健康护城河 (低负债)
        if company.debt_to_equity <= 0.5 and company.current_ratio >= 2:
            moat_analysis['dimensions']['financial'] = {'score': 15, 'reason': '财务结构稳健'}
        elif company.debt_to_equity <= 1:
            moat_analysis['dimensions']['financial'] = {'score': 10, 'reason': '财务结构合理'}
        else:
            moat_analysis['dimensions']['financial'] = {'score': 5, 'reason': '负债较高'}
        
        # 5. 估值护城河 (合理估值)
        if company.pe_ratio <= 15 and company.peg_ratio <= 1:
            moat_analysis['dimensions']['valuation'] = {'score': 20, 'reason': '估值低估，安全边际高'}
        elif company.pe_ratio <= 25:
            moat_analysis['dimensions']['valuation'] = {'score': 10, 'reason': '估值合理'}
        else:
            moat_analysis['dimensions']['valuation'] = {'score': 5, 'reason': '估值偏高'}
        
        # 计算总分
        total_score = sum(d['score'] for d in moat_analysis['dimensions'].values())
        moat_analysis['total_score'] = total_score
        
        # 护城河评级
        if total_score >= 80:
            moat_analysis['moat_rating'] = 'Wide'
            moat_analysis['description'] = '宽护城河，竞争优势显著'
        elif total_score >= 60:
            moat_analysis['moat_rating'] = 'Narrow'
            moat_analysis['description'] = '窄护城河，有一定竞争优势'
        elif total_score >= 40:
            moat_analysis['moat_rating'] = 'None'
            moat_analysis['description'] = '无明显护城河'
        else:
            moat_analysis['moat_rating'] = 'Weak'
            moat_analysis['description'] = '竞争地位薄弱'
        
        return moat_analysis
    
    def screen_by_moat(self, min_score: int = 60) -> List[Dict[str, any]]:
        """
        筛选具有护城河的公司
        """
        moat_companies = []
        
        for company in self.companies:
            moat = self.evaluate_moat(company.symbol)
            if moat['total_score'] >= min_score:
                moat_companies.append({
                    'symbol': company.symbol,
                    'name': company.name,
                    'moat_score': moat['total_score'],
                    'moat_rating': moat['moat_rating'],
                    'roe': company.roe,
                    'market_cap': company.market_cap
                })
        
        moat_companies.sort(key=lambda x: x['moat_score'], reverse=True)
        return moat_companies
    
    # ==================== 行业分析报告 ====================
    
    def generate_industry_report(self, industry_name: str = None) -> Dict[str, any]:
        """生成行业分析报告"""
        industry = self.calculate_industry_averages(industry_name)
        if not industry:
            return {'error': 'No data available'}
        
        # 行业排名
        rankings = self.multi_metric_ranking(industry_name)
        
        # 护城河公司
        moat_companies = self.screen_by_moat(60)
        
        return {
            'industry_name': industry.industry_name,
            'report_date': datetime.now().isoformat(),
            'overview': {
                'company_count': industry.company_count,
                'sector': industry.sector
            },
            'valuation_metrics': {
                'avg_pe': round(industry.avg_pe, 2),
                'avg_pb': round(industry.avg_pb, 2),
                'avg_ps': round(industry.avg_ps, 2),
                'pe_median': round(industry.median_pe, 2),
                'pe_25th': round(industry.pe_25th, 2),
                'pe_75th': round(industry.pe_75th, 2)
            },
            'profitability_metrics': {
                'avg_roe': round(industry.avg_roe, 2),
                'avg_roa': round(industry.avg_roa, 2),
                'avg_gross_margin': round(industry.avg_gross_margin, 2),
                'avg_net_margin': round(industry.avg_net_margin, 2)
            },
            'top_companies': {
                'by_roe': rankings.get('roe', [])[:5],
                'by_growth': rankings.get('revenue_growth', [])[:5],
                'comprehensive': rankings.get('comprehensive', [])[:5]
            },
            'moat_companies': moat_companies[:10]
        }


# ==================== 使用示例 ====================

if __name__ == '__main__':
    # 示例用法
    comparator = IndustryComparator()
    
    # 添加示例公司数据
    companies = [
        CompanyMetrics(
            symbol='AAPL', name='Apple', sector='Technology', industry='Consumer Electronics',
            market_cap=2800000000000, pe_ratio=28, pb_ratio=45, ps_ratio=7.5,
            ev_ebitda=22, peg_ratio=2.1, roe=150, roa=28, gross_margin=44,
            operating_margin=30, net_margin=25, revenue_growth=0.08,
            earnings_growth=0.10, fcf_growth=0.09, debt_to_equity=1.8,
            current_ratio=1.0, interest_coverage=35
        ),
        CompanyMetrics(
            symbol='MSFT', name='Microsoft', sector='Technology', industry='Software',
            market_cap=2900000000000, pe_ratio=35, pb_ratio=12, ps_ratio=12,
            ev_ebitda=25, peg_ratio=2.3, roe=42, roa=18, gross_margin=69,
            operating_margin=42, net_margin=34, revenue_growth=0.12,
            earnings_growth=0.15, fcf_growth=0.14, debt_to_equity=0.5,
            current_ratio=1.8, interest_coverage=50
        )
    ]
    
    for company in companies:
        comparator.add_company(company)
    
    # 生成行业报告
    report = comparator.generate_industry_report('Technology')
    print(f"行业平均 PE: {report['valuation_metrics']['avg_pe']}")
    print(f"护城河公司：{len(report['moat_companies'])} 家")
