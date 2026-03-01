"""
Factor Analyzer Module
因子分析器模块

提供因子分析的核心功能:
- 因子数据标准化
- 因子相关性分析
- 因子有效性检验 (IC 值)
- 因子合成方法
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from scipy import stats
from scipy.stats import pearsonr, spearmanr
import warnings

warnings.filterwarnings('ignore')


class FactorAnalyzer:
    """因子分析器"""
    
    def __init__(self, factors_df: pd.DataFrame, returns: pd.Series = None):
        """
        初始化因子分析器
        
        Args:
            factors_df: 因子数据 DataFrame，每列为一个因子
            returns: 收益率序列 (用于 IC 计算)
        """
        self.factors_df = factors_df.copy()
        self.returns = returns.copy() if returns is not None else None
        self.factor_names = list(factors_df.columns)
        self.ic_results = {}
        self._corr_matrix = None
    
    # ==================== 因子标准化 ====================
    
    def standardize(self, method: str = 'zscore') -> pd.DataFrame:
        """
        因子标准化处理
        
        Args:
            method: 标准化方法
                - 'zscore': Z-Score 标准化 (均值 0，标准差 1)
                - 'rank': 秩标准化 (转换为百分位排名)
                - 'minmax': Min-Max 标准化 (缩放到 [0, 1])
                
        Returns:
            标准化后的因子数据
        """
        standardized = pd.DataFrame(index=self.factors_df.index)
        
        for col in self.factors_df.columns:
            factor = self.factors_df[col].dropna()
            
            if method == 'zscore':
                # Z-Score 标准化
                mean = factor.mean()
                std = factor.std()
                if std > 0:
                    standardized[col] = (factor - mean) / std
                else:
                    standardized[col] = 0
                    
            elif method == 'rank':
                # 秩标准化
                standardized[col] = factor.rank(pct=True)
                
            elif method == 'minmax':
                # Min-Max 标准化
                min_val = factor.min()
                max_val = factor.max()
                if max_val > min_val:
                    standardized[col] = (factor - min_val) / (max_val - min_val)
                else:
                    standardized[col] = 0.5
            
            else:
                raise ValueError(f"不支持的标准化方法：{method}")
        
        return standardized
    
    def winsorize(self, limits: Tuple[float, float] = (0.01, 0.99)) -> pd.DataFrame:
        """
        因子去极值 (Winsorization)
        
        Args:
            limits: 上下限分位数
            
        Returns:
            去极值后的因子数据
        """
        winsorized = self.factors_df.copy()
        
        for col in winsorized.columns:
            lower = winsorized[col].quantile(limits[0])
            upper = winsorized[col].quantile(limits[1])
            winsorized[col] = winsorized[col].clip(lower=lower, upper=upper)
        
        return winsorized
    
    def neutralize(self, benchmark: pd.Series = None) -> pd.DataFrame:
        """
        因子中性化处理 (去除市场影响)
        
        Args:
            benchmark: 基准收益率序列 (如市场指数收益率)
            
        Returns:
            中性化后的因子数据
        """
        neutralized = pd.DataFrame(index=self.factors_df.index)
        
        for col in self.factors_df.columns:
            factor = self.factors_df[col].dropna()
            
            if benchmark is not None:
                # 对基准做回归，取残差作为中性化因子
                common_idx = factor.index.intersection(benchmark.dropna().index)
                if len(common_idx) > 10:
                    f = factor.loc[common_idx]
                    b = benchmark.loc[common_idx]
                    
                    # 简单线性回归
                    slope, intercept, _, _, _ = stats.linregress(b, f)
                    residual = f - (intercept + slope * b)
                    neutralized[col] = residual
                else:
                    neutralized[col] = factor
            else:
                # 无基准时，对时间序列去均值
                neutralized[col] = factor - factor.mean()
        
        return neutralized
    
    # ==================== 因子相关性分析 ====================
    
    def correlation_matrix(self, method: str = 'pearson') -> pd.DataFrame:
        """
        计算因子相关性矩阵
        
        Args:
            method: 相关性计算方法
                - 'pearson': Pearson 相关系数
                - 'spearman': Spearman 秩相关
                - 'kendall': Kendall 秩相关
                
        Returns:
            相关性矩阵
        """
        if method == 'pearson':
            corr = self.factors_df.corr(method='pearson')
        elif method == 'spearman':
            corr = self.factors_df.corr(method='spearman')
        elif method == 'kendall':
            corr = self.factors_df.corr(method='kendall')
        else:
            raise ValueError(f"不支持的相关性方法：{method}")
        
        self._corr_matrix = corr
        return corr
    
    def high_correlation_pairs(self, threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        找出高相关性因子对
        
        Args:
            threshold: 相关性阈值
            
        Returns:
            高相关性因子对列表 [(因子 1, 因子 2, 相关系数)]
        """
        corr = self._corr_matrix if self._corr_matrix is not None else self.correlation_matrix()
        high_corr_pairs = []
        
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                factor1 = corr.columns[i]
                factor2 = corr.columns[j]
                corr_value = corr.iloc[i, j]
                
                if abs(corr_value) >= threshold:
                    high_corr_pairs.append((factor1, factor2, corr_value))
        
        # 按相关性绝对值排序
        high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        
        return high_corr_pairs
    
    def pca_analysis(self, n_components: int = None) -> Dict:
        """
        主成分分析 (PCA)
        
        Args:
            n_components: 保留的主成分数量
            
        Returns:
            包含特征值、解释方差比、主成分的字典
        """
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        
        # 标准化
        scaler = StandardScaler()
        factors_scaled = scaler.fit_transform(self.factors_df.dropna())
        
        # PCA
        if n_components is None:
            n_components = min(len(self.factors_df.columns), factors_scaled.shape[0] - 1)
        
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(factors_scaled)
        
        return {
            'explained_variance_ratio': pca.explained_variance_ratio_,
            'cumulative_variance_ratio': np.cumsum(pca.explained_variance_ratio_),
            'components': pca.components_,
            'n_components': n_components
        }
    
    # ==================== 因子有效性检验 (IC 分析) ====================
    
    def calculate_ic(self, factor_name: str, forward_returns: pd.Series = None, 
                     method: str = 'pearson') -> pd.Series:
        """
        计算单个因子的 IC 值 (Information Coefficient)
        
        Args:
            factor_name: 因子名称
            forward_returns: 远期收益率序列 (如未提供则使用 self.returns)
            method: IC 计算方法 ('pearson' 或 'spearman')
            
        Returns:
            IC 时间序列
        """
        if forward_returns is None:
            if self.returns is None:
                raise ValueError("需要提供收益率序列")
            forward_returns = self.returns
        
        factor = self.factors_df[factor_name].dropna()
        returns = forward_returns.dropna()
        
        # 对齐时间索引
        common_idx = factor.index.intersection(returns.index)
        factor = factor.loc[common_idx]
        returns = returns.loc[common_idx]
        
        # 计算滚动 IC
        ic_series = pd.Series(index=common_idx)
        window = 252  # 约 1 年交易日
        
        for i in range(window, len(common_idx)):
            idx = common_idx[:i]
            f = factor.loc[idx]
            r = returns.loc[idx]
            
            if method == 'pearson':
                ic, _ = pearsonr(f, r)
            elif method == 'spearman':
                ic, _ = spearmanr(f, r)
            else:
                raise ValueError(f"不支持的 IC 计算方法：{method}")
            
            ic_series.loc[common_idx[i]] = ic
        
        self.ic_results[factor_name] = ic_series
        return ic_series
    
    def calculate_all_ic(self, forward_returns: pd.Series = None, 
                         method: str = 'pearson') -> pd.DataFrame:
        """
        计算所有因子的 IC 值
        
        Args:
            forward_returns: 远期收益率序列
            method: IC 计算方法
            
        Returns:
            所有因子的 IC 时间序列
        """
        ic_df = pd.DataFrame(index=self.factors_df.index)
        
        for factor_name in self.factors_df.columns:
            try:
                ic_series = self.calculate_ic(factor_name, forward_returns, method)
                ic_df[factor_name] = ic_series
            except Exception as e:
                print(f"计算因子 {factor_name} 的 IC 失败：{e}")
        
        return ic_df
    
    def ic_statistics(self, ic_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        IC 统计指标
        
        Args:
            ic_df: IC 时间序列 DataFrame (如未提供则使用已计算的结果)
            
        Returns:
            IC 统计指标 DataFrame
        """
        if ic_df is None:
            if not self.ic_results:
                raise ValueError("请先计算 IC 值")
            ic_df = pd.DataFrame(self.ic_results)
        
        stats_dict = {}
        
        for col in ic_df.columns:
            ic_series = ic_df[col].dropna()
            
            if len(ic_series) > 0:
                stats_dict[col] = {
                    'ic_mean': ic_series.mean(),
                    'ic_std': ic_series.std(),
                    'ic_ir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0,  # IR 比率
                    'ic_tstat': ic_series.mean() / (ic_series.std() / np.sqrt(len(ic_series))) if len(ic_series) > 0 else 0,
                    'ic_positive_ratio': (ic_series > 0).sum() / len(ic_series),  # 正 IC 比例
                    'ic_median': ic_series.median(),
                    'ic_skew': ic_series.skew(),
                    'ic_kurtosis': ic_series.kurtosis()
                }
        
        return pd.DataFrame(stats_dict).T
    
    def ic_decay(self, factor_name: str, forward_returns_list: List[pd.Series], 
                 lags: List[int] = None) -> pd.Series:
        """
        计算 IC 衰减 (不同滞后期的 IC)
        
        Args:
            factor_name: 因子名称
            forward_returns_list: 不同滞后期的收益率列表
            lags: 滞后期列表
            
        Returns:
            IC 衰减序列
        """
        if lags is None:
            lags = list(range(1, len(forward_returns_list) + 1))
        
        ic_decay = pd.Series(index=lags)
        
        for i, lag in enumerate(lags):
            if i < len(forward_returns_list):
                try:
                    ic = self.calculate_ic(factor_name, forward_returns_list[i])
                    ic_decay[lag] = ic.mean()
                except:
                    ic_decay[lag] = np.nan
        
        return ic_decay
    
    # ==================== 因子合成 ====================
    
    def equal_weight_synthesis(self, factor_names: List[str] = None) -> pd.Series:
        """
        等权合成因子
        
        Args:
            factor_names: 要合成的因子列表 (如为 None 则使用所有因子)
            
        Returns:
            合成因子序列
        """
        if factor_names is None:
            factor_names = self.factors_df.columns
        
        # 标准化
        standardized = self.standardize(method='zscore')
        
        # 等权平均
        synthetic_factor = standardized[factor_names].mean(axis=1)
        
        return synthetic_factor
    
    def ic_weight_synthesis(self, factor_names: List[str] = None, 
                            ic_df: pd.DataFrame = None) -> pd.Series:
        """
        IC 加权合成因子 (根据 IC 值分配权重)
        
        Args:
            factor_names: 要合成的因子列表
            ic_df: IC 时间序列 DataFrame
            
        Returns:
            合成因子序列
        """
        if factor_names is None:
            factor_names = self.factors_df.columns
        
        if ic_df is None:
            ic_stats = self.ic_statistics()
        else:
            ic_stats = self.ic_statistics(ic_df)
        
        # 使用 IC_IR 作为权重
        weights = {}
        for factor in factor_names:
            if factor in ic_stats.index:
                ic_ir = ic_stats.loc[factor, 'ic_ir']
                weights[factor] = max(ic_ir, 0)  # 只取正权重
            else:
                weights[factor] = 1.0
        
        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # 标准化因子
        standardized = self.standardize(method='zscore')
        
        # 加权合成
        synthetic_factor = sum(standardized[factor] * weight for factor, weight in weights.items())
        
        return synthetic_factor
    
    def pca_synthesis(self, n_components: int = 1) -> pd.Series:
        """
        PCA 合成因子 (使用第一主成分)
        
        Args:
            n_components: 使用的主成分数量
            
        Returns:
            合成因子序列
        """
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        
        # 标准化
        scaler = StandardScaler()
        factors_scaled = scaler.fit_transform(self.factors_df.dropna())
        
        # PCA
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(factors_scaled)
        
        # 转换回 DataFrame
        synthetic_factor = pd.Series(pca_result[:, 0], 
                          index=self.factors_df.dropna().index,
                          name='pca_synthetic_factor')
        
        return synthetic_factor
    
    # ==================== 因子筛选 ====================
    
    def select_factors_by_ic(self, min_ic: float = 0.02, 
                             min_ir: float = 0.5) -> List[str]:
        """
        根据 IC 指标筛选有效因子
        
        Args:
            min_ic: 最小 IC 均值
            min_ir: 最小 IR 比率
            
        Returns:
            有效因子列表
        """
        ic_stats = self.ic_statistics()
        
        valid_factors = []
        for factor in ic_stats.index:
            if (ic_stats.loc[factor, 'ic_mean'] >= min_ic and 
                ic_stats.loc[factor, 'ic_ir'] >= min_ir):
                valid_factors.append(factor)
        
        return valid_factors
    
    def select_factors_by_low_correlation(self, threshold: float = 0.5) -> List[str]:
        """
        选择低相关性的因子 (避免多重共线性)
        
        Args:
            threshold: 相关性阈值
            
        Returns:
            低相关性因子列表
        """
        corr = self.correlation_matrix()
        selected = []
        
        for factor in corr.columns:
            is_independent = True
            for selected_factor in selected:
                if abs(corr.loc[factor, selected_factor]) > threshold:
                    is_independent = False
                    break
            
            if is_independent:
                selected.append(factor)
        
        return selected
    
    def factor_rank(self, date: pd.Timestamp = None) -> pd.DataFrame:
        """
        因子排名 (某日各因子的分位数排名)
        
        Args:
            date: 特定日期 (如为 None 则返回最新日期)
            
        Returns:
            因子排名 DataFrame
        """
        if date is None:
            date = self.factors_df.index[-1]
        
        row = self.factors_df.loc[date].dropna()
        rank = row.rank(pct=True)
        
        return pd.DataFrame({
            'value': row,
            'rank': rank,
            'percentile': rank * 100
        })
    
    # ==================== 报告生成 ====================
    
    def generate_factor_report(self) -> str:
        """
        生成因子分析报告
        
        Returns:
            报告文本
        """
        report = []
        report.append("=" * 60)
        report.append("因子分析报告")
        report.append("=" * 60)
        report.append(f"\n因子数量：{len(self.factors_df.columns)}")
        report.append(f"时间范围：{self.factors_df.index[0]} 至 {self.factors_df.index[-1]}")
        report.append(f"样本数量：{len(self.factors_df)}")
        
        # 描述性统计
        report.append("\n" + "=" * 60)
        report.append("因子描述性统计")
        report.append("=" * 60)
        desc = self.factors_df.describe()
        report.append(desc.to_string())
        
        # 相关性分析
        report.append("\n" + "=" * 60)
        report.append("高相关性因子对 (|corr| > 0.7)")
        report.append("=" * 60)
        high_corr = self.high_correlation_pairs(0.7)
        if high_corr:
            for f1, f2, corr in high_corr[:10]:
                report.append(f"{f1} <-> {f2}: {corr:.3f}")
        else:
            report.append("无高相关性因子对")
        
        # IC 分析
        if self.ic_results:
            report.append("\n" + "=" * 60)
            report.append("因子 IC 统计")
            report.append("=" * 60)
            ic_stats = self.ic_statistics()
            report.append(ic_stats.to_string())
        
        return "\n".join(report)


# 使用示例
if __name__ == "__main__":
    # 创建示例数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=252, freq='B')
    
    # 生成因子数据
    factors = pd.DataFrame({
        'momentum': np.cumsum(np.random.randn(252)),
        'value': np.random.randn(252),
        'quality': np.random.randn(252) * 0.5 + np.sin(np.arange(252) / 20),
        'volatility': np.abs(np.random.randn(252))
    }, index=dates)
    
    # 生成收益率
    returns = pd.Series(np.random.randn(252) * 0.02, index=dates)
    
    # 创建分析器
    analyzer = FactorAnalyzer(factors, returns)
    
    # 标准化
    standardized = analyzer.standardize('zscore')
    print("标准化后因子 (前 5 行):")
    print(standardized.head())
    
    # 相关性分析
    corr = analyzer.correlation_matrix()
    print("\n因子相关性矩阵:")
    print(corr)
    
    # IC 分析
    ic_df = analyzer.calculate_all_ic(method='spearman')
    ic_stats = analyzer.ic_statistics(ic_df)
    print("\n因子 IC 统计:")
    print(ic_stats)
    
    # 因子合成
    synthetic = analyzer.equal_weight_synthesis()
    print("\n等权合成因子 (最后 5 个值):")
    print(synthetic.tail())
    
    # 生成报告
    report = analyzer.generate_factor_report()
    print("\n" + report)
