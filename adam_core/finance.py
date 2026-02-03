from dataclasses import dataclass

@dataclass
class FinanceInputs:
    breached_accounts: int
    avg_contract_value: float
    sla_penalty_per_account: float
    churn_probability: float
    overtime_hours: float
    overtime_rate: float

@dataclass
class FinanceOutputs:
    revenue_at_risk: float
    penalty_cost: float
    churn_cost: float
    overtime_cost: float
    total_impact: float

def estimate_impact(inp: FinanceInputs) -> FinanceOutputs:
    revenue_at_risk = inp.breached_accounts * inp.avg_contract_value
    penalty_cost = inp.breached_accounts * inp.sla_penalty_per_account
    churn_cost = inp.breached_accounts * inp.churn_probability * inp.avg_contract_value
    overtime_cost = inp.overtime_hours * inp.overtime_rate
    total_impact = penalty_cost + churn_cost + overtime_cost

    return FinanceOutputs(
        revenue_at_risk=revenue_at_risk,
        penalty_cost=penalty_cost,
        churn_cost=churn_cost,
        overtime_cost=overtime_cost,
        total_impact=total_impact,
    )
