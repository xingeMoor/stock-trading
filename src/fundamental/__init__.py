#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Q 脑基本面分析模块

提供完整的财务分析、估值建模、行业对比和财报跟踪能力。
"""

from .financial_analyzer import FinancialAnalyzer, FinancialStatement
from .valuation_models import ValuationModels, ValuationInput
from .industry_compare import IndustryComparator, CompanyMetrics, IndustryMetrics
from .earnings_tracker import (
    EarningsTracker,
    EarningsReport,
    EarningsPreview,
    DividendInfo,
    StockIncentive,
    ReportType,
    DividendType
)

__version__ = '1.0.0'
__author__ = 'Q 脑开发团队'

__all__ = [
    # 财务分析
    'FinancialAnalyzer',
    'FinancialStatement',
    
    # 估值模型
    'ValuationModels',
    'ValuationInput',
    
    # 行业对比
    'IndustryComparator',
    'CompanyMetrics',
    'IndustryMetrics',
    
    # 财报跟踪
    'EarningsTracker',
    'EarningsReport',
    'EarningsPreview',
    'DividendInfo',
    'StockIncentive',
    'ReportType',
    'DividendType',
]
