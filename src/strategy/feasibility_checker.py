#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可行性检查器 (Feasibility Checker)
评估策略的技术可行性、开发工作量和潜在风险
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import json
from datetime import datetime


class FeasibilityLevel(Enum):
    """可行性等级"""
    HIGHLY_FEASIBLE = "highly_feasible"  # 高度可行
    FEASIBLE = "feasible"  # 可行
    CONDITIONALLY_FEASIBLE = "conditionally_feasible"  # 有条件可行
    CHALLENGING = "challenging"  # 有挑战
    NOT_FEASIBLE = "not_feasible"  # 不可行


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中等风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 严重风险


@dataclass
class TechnicalRequirement:
    """技术需求"""
    requirement_id: str
    category: str  # data/compute/execution/risk
    description: str
    priority: str  # must_have/should_have/nice_to_have
    estimated_effort_hours: int
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class FeasibilityAssessment:
    """可行性评估结果"""
    strategy_id: str
    strategy_name: str
    assessment_date: str
    feasibility_level: FeasibilityLevel
    feasibility_score: float  # 0-100
    risk_level: RiskLevel
    risk_score: float  # 0-100
    total_effort_hours: int
    total_effort_days: int
    team_size_recommended: int
    timeline_weeks: int
    technical_constraints: List[str]
    resource_requirements: Dict[str, Any]
    go_no_go_recommendation: str
    key_milestones: List[Dict[str, Any]]
    mitigation_strategies: List[Dict[str, str]]


class FeasibilityChecker:
    """可行性检查器核心类"""
    
    def __init__(self):
        # 技术能力矩阵 (当前系统能力)
        self.current_capabilities = {
            "data_sources": {
                "us_stock_daily": True,
                "us_stock_intraday": True,
                "us_stock_tick": False,
                "a_share_daily": True,
                "a_share_intraday": False,
                "crypto": True,
                "futures": False,
            },
            "compute": {
                "backtest_engine": True,
                "optimization": True,
                "ml_training": True,
                "realtime_calculation": True,
                "distributed_compute": False,
            },
            "execution": {
                "us_stock_api": True,
                "a_stock_api": False,
                "crypto_api": True,
                "low_latency": False,
                "smart_routing": False,
            },
            "risk_management": {
                "position_monitoring": True,
                "realtime_risk": True,
                "auto_liquidation": False,
                "portfolio_optimization": True,
            }
        }
        
        # 资源成本估算 (人天)
        self.effort_estimates = {
            "data_integration": {
                "existing_source": 0.5,
                "new_api": 3,
                "realtime_stream": 5,
                "historical_backfill": 2,
            },
            "strategy_development": {
                "simple_indicator": 2,
                "complex_indicator": 5,
                "ml_model": 10,
                "multi_factor": 8,
            },
            "backtest_setup": {
                "basic": 2,
                "advanced": 5,
                "walk_forward": 3,
                "monte_carlo": 4,
            },
            "execution_integration": {
                "paper_trading": 3,
                "live_trading": 5,
                "low_latency": 10,
            },
            "risk_system": {
                "basic_monitoring": 2,
                "realtime_alerts": 3,
                "auto_controls": 5,
            },
            "testing_qa": {
                "unit_tests": 2,
                "integration_tests": 3,
                "performance_tests": 3,
            }
        }
    
    def assess_feasibility(
        self,
        strategy_id: str,
        strategy_name: str,
        technical_spec: Dict[str, Any],
        business_constraints: Optional[Dict[str, Any]] = None
    ) -> FeasibilityAssessment:
        """
        评估策略可行性
        
        Args:
            strategy_id: 策略 ID
            strategy_name: 策略名称
            technical_spec: 技术规格 (来自 RequirementTranslator)
            business_constraints: 业务约束 (时间、预算等)
            
        Returns:
            FeasibilityAssessment: 可行性评估结果
        """
        # 1. 技术可行性分析
        tech_feasibility = self._analyze_technical_feasibility(technical_spec)
        
        # 2. 资源需求估算
        resource_requirements = self._estimate_resources(technical_spec)
        
        # 3. 工作量估算
        effort_hours = self._estimate_effort(technical_spec)
        
        # 4. 风险评估
        risk_assessment = self._assess_risks(technical_spec)
        
        # 5. 时间线规划
        timeline = self._plan_timeline(effort_hours, resource_requirements)
        
        # 6. 综合评分
        feasibility_score = self._calculate_feasibility_score(
            tech_feasibility, risk_assessment
        )
        
        # 7. 确定可行性等级
        feasibility_level = self._determine_feasibility_level(feasibility_score)
        
        # 8. 生成建议
        recommendation = self._generate_recommendation(
            feasibility_level, risk_assessment, business_constraints
        )
        
        # 9. 制定缓解策略
        mitigation_strategies = self._create_mitigation_strategies(
            tech_feasibility, risk_assessment
        )
        
        # 10. 关键里程碑
        milestones = self._define_milestones(timeline)
        
        return FeasibilityAssessment(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            assessment_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            feasibility_level=feasibility_level,
            feasibility_score=feasibility_score,
            risk_level=risk_assessment["level"],
            risk_score=risk_assessment["score"],
            total_effort_hours=effort_hours,
            total_effort_days=effort_hours // 8,
            team_size_recommended=resource_requirements["team_size"],
            timeline_weeks=timeline["weeks"],
            technical_constraints=tech_feasibility["constraints"],
            resource_requirements=resource_requirements,
            go_no_go_recommendation=recommendation,
            key_milestones=milestones,
            mitigation_strategies=mitigation_strategies
        )
    
    def _analyze_technical_feasibility(
        self,
        technical_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析技术可行性"""
        result = {
            "score": 100,
            "constraints": [],
            "gaps": [],
            "ready_areas": []
        }
        
        # 检查数据源可行性
        data_reqs = technical_spec.get("data_requirements", {})
        data_sources = data_reqs.get("data_sources", [])
        
        for source in data_sources:
            if source in ["polygon", "alpaca", "yfinance"]:
                if self.current_capabilities["data_sources"]["us_stock_daily"]:
                    result["ready_areas"].append(f"美股数据源：{source}")
                else:
                    result["score"] -= 15
                    result["gaps"].append(f"美股数据源未接入：{source}")
            
            elif source in ["tushare", "baostock", "wind"]:
                if self.current_capabilities["data_sources"]["a_share_daily"]:
                    result["ready_areas"].append(f"A 股数据源：{source}")
                else:
                    result["score"] -= 20
                    result["gaps"].append(f"A 股数据源未接入：{source}")
                    result["constraints"].append("A 股实时数据不可用")
        
        # 检查频率要求
        freq_type = technical_spec.get("frequency_type", "daily")
        if freq_type == "high_frequency":
            if not self.current_capabilities["data_sources"]["us_stock_tick"]:
                result["score"] -= 25
                result["gaps"].append("Tick 级数据不可用")
                result["constraints"].append("无法支持高频策略")
            
            if not self.current_capabilities["execution"]["low_latency"]:
                result["score"] -= 20
                result["gaps"].append("低延迟执行系统未就绪")
                result["constraints"].append("执行延迟可能影响策略表现")
        
        # 检查执行要求
        market_type = technical_spec.get("market_type", "us_stock")
        if market_type == "a_share":
            if not self.current_capabilities["execution"]["a_stock_api"]:
                result["score"] -= 30
                result["gaps"].append("A 股交易接口未接入")
                result["constraints"].append("A 股实盘交易暂不支持")
        
        # 检查计算需求
        if technical_spec.get("strategy_type") == "factor_investing":
            if not self.current_capabilities["compute"]["distributed_compute"]:
                result["score"] -= 10
                result["constraints"].append("因子计算可能需要优化性能")
        
        result["score"] = max(0, result["score"])
        return result
    
    def _estimate_resources(
        self,
        technical_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """估算资源需求"""
        resources = {
            "developers": 1,
            "data_engineers": 0,
            "qa_engineers": 0.5,
            "devops": 0.2,
            "team_size": 2,
            "infrastructure": [],
            "external_services": [],
            "budget_estimate_usd": 0
        }
        
        # 根据复杂度调整团队规模
        complexity = technical_spec.get("estimated_complexity", "medium")
        if complexity == "high":
            resources["developers"] = 2
            resources["qa_engineers"] = 1
            resources["team_size"] = 4
        elif complexity == "low":
            resources["developers"] = 1
            resources["team_size"] = 1
        
        # 高频策略需要更多资源
        if technical_spec.get("frequency_type") == "high_frequency":
            resources["devops"] = 1
            resources["team_size"] += 1
            resources["infrastructure"].append("低延迟服务器")
            resources["infrastructure"].append("专线网络")
        
        # 数据需求
        data_reqs = technical_spec.get("data_requirements", {})
        if data_reqs.get("update_frequency") == "real-time":
            resources["data_engineers"] = 1
            resources["external_services"].append("实时数据订阅")
            resources["budget_estimate_usd"] += 500  # 月度数据成本
        
        # A 股策略需要额外资源
        if technical_spec.get("market_type") == "a_share":
            resources["external_services"].append("A 股数据服务")
            resources["budget_estimate_usd"] += 300
        
        return resources
    
    def _estimate_effort(self, technical_spec: Dict[str, Any]) -> int:
        """估算工作量 (小时)"""
        total_hours = 0
        
        # 1. 数据集成
        data_reqs = technical_spec.get("data_requirements", {})
        if data_reqs.get("update_frequency") == "real-time":
            total_hours += self.effort_estimates["data_integration"]["realtime_stream"]
        else:
            total_hours += self.effort_estimates["data_integration"]["existing_source"]
        
        # 历史数据回补
        if data_reqs.get("historical_depth") != "1 year":
            total_hours += self.effort_estimates["data_integration"]["historical_backfill"]
        
        # 2. 策略开发
        strategy_type = technical_spec.get("strategy_type", "other")
        indicator_count = len(technical_spec.get("indicator_requirements", []))
        
        if strategy_type == "factor_investing":
            total_hours += self.effort_estimates["strategy_development"]["ml_model"]
        elif indicator_count > 5:
            total_hours += self.effort_estimates["strategy_development"]["multi_factor"]
        elif indicator_count > 2:
            total_hours += self.effort_estimates["strategy_development"]["complex_indicator"]
        else:
            total_hours += self.effort_estimates["strategy_development"]["simple_indicator"]
        
        # 3. 回测设置
        freq_type = technical_spec.get("frequency_type", "daily")
        if freq_type == "high_frequency":
            total_hours += self.effort_estimates["backtest_setup"]["advanced"]
        else:
            total_hours += self.effort_estimates["backtest_setup"]["basic"]
        
        # 4. 执行集成
        market_type = technical_spec.get("market_type", "us_stock")
        if freq_type == "high_frequency":
            total_hours += self.effort_estimates["execution_integration"]["low_latency"]
        else:
            total_hours += self.effort_estimates["execution_integration"]["paper_trading"]
        
        # 5. 风控系统
        risk_controls = technical_spec.get("risk_controls", [])
        if len(risk_controls) > 5:
            total_hours += self.effort_estimates["risk_system"]["auto_controls"]
        elif len(risk_controls) > 3:
            total_hours += self.effort_estimates["risk_system"]["realtime_alerts"]
        else:
            total_hours += self.effort_estimates["risk_system"]["basic_monitoring"]
        
        # 6. 测试 QA
        complexity = technical_spec.get("estimated_complexity", "medium")
        total_hours += self.effort_estimates["testing_qa"]["unit_tests"]
        if complexity in ["medium", "high"]:
            total_hours += self.effort_estimates["testing_qa"]["integration_tests"]
        if complexity == "high":
            total_hours += self.effort_estimates["testing_qa"]["performance_tests"]
        
        # 缓冲时间 (20%)
        total_hours = int(total_hours * 1.2)
        
        return total_hours
    
    def _assess_risks(self, technical_spec: Dict[str, Any]) -> Dict[str, Any]:
        """评估风险"""
        risk_score = 0
        risk_factors = []
        
        # 技术风险
        tech_risks = technical_spec.get("technical_risks", [])
        for risk in tech_risks:
            if "延迟" in risk or "latency" in risk.lower():
                risk_score += 15
                risk_factors.append({"type": "technical", "description": risk, "impact": "high"})
            elif "过拟合" in risk or "overfitting" in risk.lower():
                risk_score += 20
                risk_factors.append({"type": "model", "description": risk, "impact": "high"})
            else:
                risk_score += 10
                risk_factors.append({"type": "technical", "description": risk, "impact": "medium"})
        
        # 市场风险
        market_type = technical_spec.get("market_type", "us_stock")
        if market_type == "a_share":
            risk_score += 15
            risk_factors.append({
                "type": "regulatory",
                "description": "A 股交易规则复杂且可能变化",
                "impact": "medium"
            })
        
        # 频率风险
        freq_type = technical_spec.get("frequency_type", "daily")
        if freq_type == "high_frequency":
            risk_score += 25
            risk_factors.append({
                "type": "operational",
                "description": "高频交易对系统稳定性要求极高",
                "impact": "critical"
            })
        
        # 数据风险
        data_reqs = technical_spec.get("data_requirements", {})
        if data_reqs.get("update_frequency") == "real-time":
            risk_score += 15
            risk_factors.append({
                "type": "data",
                "description": "实时数据流可能中断或延迟",
                "impact": "high"
            })
        
        # 确定风险等级
        if risk_score >= 60:
            level = RiskLevel.CRITICAL
        elif risk_score >= 40:
            level = RiskLevel.HIGH
        elif risk_score >= 20:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        return {
            "score": min(100, risk_score),
            "level": level,
            "factors": risk_factors
        }
    
    def _plan_timeline(
        self,
        effort_hours: int,
        resources: Dict[str, Any]
    ) -> Dict[str, Any]:
        """规划时间线"""
        team_size = resources["team_size"]
        
        # 考虑并行工作，实际时间会缩短
        parallel_factor = 0.7 if team_size > 1 else 1.0
        
        # 每周有效工作时间 (考虑会议、沟通等)
        hours_per_week = 30  # 40 小时 * 0.75 效率
        
        # 计算周数
        total_weeks = (effort_hours * parallel_factor) / (hours_per_week * team_size)
        total_weeks = max(1, round(total_weeks))
        
        # 添加缓冲 (20%)
        total_weeks = int(total_weeks * 1.2)
        
        return {
            "weeks": total_weeks,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "estimated_end_date": "",  # 由调用方计算
            "phases": [
                {"name": "需求分析", "duration_days": 3},
                {"name": "技术设计", "duration_days": 5},
                {"name": "开发实现", "duration_days": total_weeks * 7 * 0.5},
                {"name": "测试验证", "duration_days": total_weeks * 7 * 0.2},
                {"name": "部署上线", "duration_days": 3},
            ]
        }
    
    def _calculate_feasibility_score(
        self,
        tech_feasibility: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> float:
        """计算综合可行性评分"""
        # 技术可行性权重 60%
        tech_score = tech_feasibility["score"]
        
        # 风险评分反向权重 40% (风险越低，可行性越高)
        risk_score = 100 - risk_assessment["score"]
        
        # 加权平均
        feasibility_score = (tech_score * 0.6) + (risk_score * 0.4)
        
        return round(feasibility_score, 1)
    
    def _determine_feasibility_level(self, score: float) -> FeasibilityLevel:
        """根据评分确定可行性等级"""
        if score >= 80:
            return FeasibilityLevel.HIGHLY_FEASIBLE
        elif score >= 60:
            return FeasibilityLevel.FEASIBLE
        elif score >= 40:
            return FeasibilityLevel.CONDITIONALLY_FEASIBLE
        elif score >= 20:
            return FeasibilityLevel.CHALLENGING
        else:
            return FeasibilityLevel.NOT_FEASIBLE
    
    def _generate_recommendation(
        self,
        feasibility_level: FeasibilityLevel,
        risk_assessment: Dict[str, Any],
        business_constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成建议"""
        if feasibility_level == FeasibilityLevel.HIGHLY_FEASIBLE:
            return "✅ 建议立即启动 - 技术成熟，风险可控"
        
        elif feasibility_level == FeasibilityLevel.FEASIBLE:
            return "✅ 建议启动 - 整体可行，注意监控已识别风险"
        
        elif feasibility_level == FeasibilityLevel.CONDITIONALLY_FEASIBLE:
            constraints = business_constraints or {}
            if constraints.get("timeline_flexible", True):
                return "⚠️ 有条件启动 - 需要解决关键技术约束，建议延长开发周期"
            else:
                return "⚠️ 谨慎启动 - 时间约束下风险较高，建议先解决核心问题"
        
        elif feasibility_level == FeasibilityLevel.CHALLENGING:
            return "❌ 暂缓启动 - 技术挑战较大，建议重新设计或分阶段实施"
        
        else:
            return "❌ 不建议启动 - 当前技术条件不支持，需要重大技术投入"
    
    def _create_mitigation_strategies(
        self,
        tech_feasibility: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """制定风险缓解策略"""
        strategies = []
        
        # 针对技术约束
        for constraint in tech_feasibility.get("constraints", []):
            if "A 股" in constraint:
                strategies.append({
                    "risk": constraint,
                    "strategy": "优先开发美股版本，A 股版本延后",
                    "timeline": "Phase 2"
                })
            elif "延迟" in constraint or "latency" in constraint:
                strategies.append({
                    "risk": constraint,
                    "strategy": "优化网络架构，考虑托管服务器",
                    "timeline": "Phase 1"
                })
            elif "高频" in constraint:
                strategies.append({
                    "risk": constraint,
                    "strategy": "降低频率至日内级别，验证策略逻辑后再升级",
                    "timeline": "Phase 1"
                })
        
        # 针对风险因素
        for risk_factor in risk_assessment.get("factors", []):
            if risk_factor["type"] == "model":
                strategies.append({
                    "risk": risk_factor["description"],
                    "strategy": "实施严格的样本外测试和交叉验证",
                    "timeline": "开发阶段"
                })
            elif risk_factor["type"] == "data":
                strategies.append({
                    "risk": risk_factor["description"],
                    "strategy": "建立数据质量监控和备份机制",
                    "timeline": "Phase 1"
                })
            elif risk_factor["type"] == "operational":
                strategies.append({
                    "risk": risk_factor["description"],
                    "strategy": "实施灰度发布和熔断机制",
                    "timeline": "上线前"
                })
        
        return strategies
    
    def _define_milestones(
        self,
        timeline: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """定义关键里程碑"""
        weeks = timeline["weeks"]
        milestones = [
            {
                "name": "需求确认",
                "week": 1,
                "deliverables": ["需求文档", "技术规格"],
                "gate": "技术评审通过"
            },
            {
                "name": "数据就绪",
                "week": 2,
                "deliverables": ["数据管道", "历史数据"],
                "gate": "数据质量验证"
            },
            {
                "name": "策略原型",
                "week": weeks * 0.4,
                "deliverables": ["策略代码", "单元测试"],
                "gate": "代码审查通过"
            },
            {
                "name": "回测完成",
                "week": weeks * 0.6,
                "deliverables": ["回测报告", "性能分析"],
                "gate": "策略表现达标"
            },
            {
                "name": "模拟交易",
                "week": weeks * 0.8,
                "deliverables": ["模拟交易报告", "风控验证"],
                "gate": "模拟交易稳定"
            },
            {
                "name": "正式上线",
                "week": weeks,
                "deliverables": ["生产部署", "监控告警"],
                "gate": "上线评审通过"
            }
        ]
        
        return milestones
    
    def generate_assessment_report(
        self,
        assessment: FeasibilityAssessment
    ) -> str:
        """生成可行性评估报告"""
        report = f"""# 策略可行性评估报告

## 基本信息
- **策略名称**: {assessment.strategy_name}
- **策略 ID**: {assessment.strategy_id}
- **评估日期**: {assessment.assessment_date}

## 评估结论

### 可行性等级
**{assessment.feasibility_level.value.upper()}** (评分：{assessment.feasibility_score}/100)

### 风险等级
**{assessment.risk_level.value.upper()}** (评分：{assessment.risk_score}/100)

### 建议
**{assessment.go_no_go_recommendation}**

## 资源估算

### 工作量
- **总工时**: {assessment.total_effort_hours} 小时
- **总人天**: {assessment.total_effort_days} 天
- **预计周期**: {assessment.timeline_weeks} 周

### 团队配置
- **推荐团队规模**: {assessment.team_size_recommended} 人
- **开发人员**: {assessment.resource_requirements.get('developers', 0)} 人
- **数据工程师**: {assessment.resource_requirements.get('data_engineers', 0)} 人
- **测试工程师**: {assessment.resource_requirements.get('qa_engineers', 0)} 人

### 基础设施需求
{chr(10).join(['- ' + item for item in assessment.resource_requirements.get('infrastructure', ['无特殊需求'])])}

### 外部服务
{chr(10).join(['- ' + item for item in assessment.resource_requirements.get('external_services', ['无'])])}

### 预算估算
**${assessment.resource_requirements.get('budget_estimate_usd', 0)}/月** (数据和服务费用)

## 技术约束
{chr(10).join(['- ⚠️ ' + c for c in assessment.technical_constraints]) if assessment.technical_constraints else '- 无重大技术约束'}

## 关键里程碑
| 里程碑 | 时间 | 交付物 | 准出条件 |
|--------|------|--------|----------|
{chr(10).join([f"| {m['name']} | 第{int(m['week'])}周 | {', '.join(m['deliverables'])} | {m['gate']} |" for m in assessment.key_milestones])}

## 风险缓解策略
{chr(10).join([f"- **{s['risk']}**: {s['strategy']} ({s['timeline']})" for s in assessment.mitigation_strategies]) if assessment.mitigation_strategies else '- 标准风险管理流程'}

## 下一步行动
1. [ ] 评审可行性报告
2. [ ] 确认资源分配
3. [ ] 启动项目 (如 Go)
4. [ ] 或重新设计策略 (如 No-Go)

---
*报告由 FeasibilityChecker 自动生成*
"""
        return report


# 使用示例
if __name__ == "__main__":
    # 示例技术规格
    tech_spec = {
        "strategy_id": "STRAT_20260301_ABC123",
        "strategy_type": "trend_following",
        "market_type": "us_stock",
        "frequency_type": "daily",
        "estimated_complexity": "medium",
        "data_requirements": {
            "data_sources": ["polygon", "yfinance"],
            "update_frequency": "daily",
            "historical_depth": "5 years"
        },
        "indicator_requirements": ["MA", "MACD", "RSI"],
        "risk_controls": ["止损", "止盈", "仓位限制"],
        "technical_risks": ["过拟合风险", "市场制度变化风险"]
    }
    
    # 评估可行性
    checker = FeasibilityChecker()
    assessment = checker.assess_feasibility(
        strategy_id="STRAT_20260301_ABC123",
        strategy_name="双均线趋势策略",
        technical_spec=tech_spec
    )
    
    # 生成报告
    report = checker.generate_assessment_report(assessment)
    print(report)
    
    # 保存报告
    with open(f"feasibility_{assessment.strategy_id}.md", "w", encoding="utf-8") as f:
        f.write(report)
