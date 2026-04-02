from pydantic import BaseModel


class CategoryTotal(BaseModel):
    category: str
    total: float
    count: int


class MonthlyTrend(BaseModel):
    year: int
    month: int
    income: float
    expense: float
    net: float


class RecentTransaction(BaseModel):
    id: int
    amount: float
    type: str
    category: str
    date: str
    notes: str | None


class DashboardSummary(BaseModel):
    total_income: float
    total_expense: float
    net_balance: float
    total_transactions: int
    category_totals: list[CategoryTotal]
    monthly_trends: list[MonthlyTrend]
    recent_transactions: list[RecentTransaction]


# ── Analyst-only insight schemas ──────────────────────────────────────────────

class TopCategory(BaseModel):
    category: str
    total: float
    count: int
    percentage: float  # share of total spend/income for that type


class WeeklyTrend(BaseModel):
    year: int
    week: int          # ISO week number
    income: float
    expense: float
    net: float


class AnalystInsights(BaseModel):
    avg_transaction_amount: float
    avg_monthly_income: float
    avg_monthly_expense: float
    top_income_categories: list[TopCategory]
    top_expense_categories: list[TopCategory]
    weekly_trends: list[WeeklyTrend]
    highest_single_expense: float | None
    highest_single_income: float | None
