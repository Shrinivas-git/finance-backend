from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.schemas.dashboard import (
    AnalystInsights,
    CategoryTotal,
    DashboardSummary,
    MonthlyTrend,
    RecentTransaction,
    TopCategory,
    WeeklyTrend,
)


def get_dashboard_summary(db: Session) -> DashboardSummary:
    active_txs = db.query(Transaction).filter(Transaction.is_deleted == False)  # noqa: E712

    # ── Totals ────────────────────────────────────────────────────────────────
    income_row = (
        active_txs.filter(Transaction.type == TransactionType.income)
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0.0))
        .scalar()
    )
    expense_row = (
        active_txs.filter(Transaction.type == TransactionType.expense)
        .with_entities(func.coalesce(func.sum(Transaction.amount), 0.0))
        .scalar()
    )
    total_income = float(income_row)
    total_expense = float(expense_row)

    # ── Category-wise totals ───────────────────────────────────────────────────
    cat_rows = (
        active_txs.with_entities(
            Transaction.category,
            func.sum(Transaction.amount),
            func.count(Transaction.id),
        )
        .group_by(Transaction.category)
        .all()
    )
    category_totals = [
        CategoryTotal(category=row[0], total=float(row[1]), count=row[2]) for row in cat_rows
    ]

    # ── Monthly trends ────────────────────────────────────────────────────────
    # Pull all active transactions and aggregate in Python to stay DB-agnostic
    all_txs = active_txs.with_entities(
        Transaction.date, Transaction.type, Transaction.amount
    ).all()

    monthly: dict[tuple[int, int], dict] = defaultdict(
        lambda: {"income": 0.0, "expense": 0.0}
    )
    for tx_date, tx_type, amount in all_txs:
        key = (tx_date.year, tx_date.month)
        monthly[key][tx_type.value] += float(amount)

    monthly_trends = [
        MonthlyTrend(
            year=year,
            month=month,
            income=vals["income"],
            expense=vals["expense"],
            net=vals["income"] - vals["expense"],
        )
        for (year, month), vals in sorted(monthly.items())
    ]

    # ── Recent activity (last 10 records) ────────────────────────────────────
    recent_rows = (
        active_txs.order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(10)
        .all()
    )
    recent_transactions = [
        RecentTransaction(
            id=tx.id,
            amount=tx.amount,
            type=tx.type.value,
            category=tx.category,
            date=str(tx.date),
            notes=tx.notes,
        )
        for tx in recent_rows
    ]

    return DashboardSummary(
        total_income=total_income,
        total_expense=total_expense,
        net_balance=total_income - total_expense,
        total_transactions=active_txs.count(),
        category_totals=category_totals,
        monthly_trends=monthly_trends,
        recent_transactions=recent_transactions,
    )


def get_analyst_insights(db: Session) -> AnalystInsights:
    active_txs = db.query(Transaction).filter(Transaction.is_deleted == False)  # noqa: E712

    all_txs = active_txs.with_entities(
        Transaction.date, Transaction.type, Transaction.amount, Transaction.category
    ).all()

    if not all_txs:
        return AnalystInsights(
            avg_transaction_amount=0.0,
            avg_monthly_income=0.0,
            avg_monthly_expense=0.0,
            top_income_categories=[],
            top_expense_categories=[],
            weekly_trends=[],
            highest_single_expense=None,
            highest_single_income=None,
        )

    total_amount = sum(float(r.amount) for r in all_txs)
    avg_tx = total_amount / len(all_txs)

    # ── Monthly averages ──────────────────────────────────────────────────────
    monthly: dict[tuple[int, int], dict] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for r in all_txs:
        key = (r.date.year, r.date.month)
        monthly[key][r.type.value] += float(r.amount)

    months = list(monthly.values())
    avg_monthly_income = sum(m["income"] for m in months) / len(months) if months else 0.0
    avg_monthly_expense = sum(m["expense"] for m in months) / len(months) if months else 0.0

    # ── Top categories ────────────────────────────────────────────────────────
    income_cats: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    expense_cats: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    highest_income: float | None = None
    highest_expense: float | None = None

    for r in all_txs:
        amt = float(r.amount)
        if r.type == TransactionType.income:
            income_cats[r.category]["total"] += amt
            income_cats[r.category]["count"] += 1
            highest_income = max(highest_income, amt) if highest_income is not None else amt
        else:
            expense_cats[r.category]["total"] += amt
            expense_cats[r.category]["count"] += 1
            highest_expense = max(highest_expense, amt) if highest_expense is not None else amt

    total_income_sum = sum(v["total"] for v in income_cats.values()) or 1.0
    total_expense_sum = sum(v["total"] for v in expense_cats.values()) or 1.0

    top_income = sorted(income_cats.items(), key=lambda x: x[1]["total"], reverse=True)[:5]
    top_expense = sorted(expense_cats.items(), key=lambda x: x[1]["total"], reverse=True)[:5]

    top_income_categories = [
        TopCategory(
            category=cat,
            total=round(v["total"], 2),
            count=v["count"],
            percentage=round(v["total"] / total_income_sum * 100, 2),
        )
        for cat, v in top_income
    ]
    top_expense_categories = [
        TopCategory(
            category=cat,
            total=round(v["total"], 2),
            count=v["count"],
            percentage=round(v["total"] / total_expense_sum * 100, 2),
        )
        for cat, v in top_expense
    ]

    # ── Weekly trends (ISO week) ──────────────────────────────────────────────
    weekly: dict[tuple[int, int], dict] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for r in all_txs:
        iso = r.date.isocalendar()
        key = (iso.year, iso.week)
        weekly[key][r.type.value] += float(r.amount)

    weekly_trends = [
        WeeklyTrend(
            year=year,
            week=week,
            income=round(vals["income"], 2),
            expense=round(vals["expense"], 2),
            net=round(vals["income"] - vals["expense"], 2),
        )
        for (year, week), vals in sorted(weekly.items())
    ]

    return AnalystInsights(
        avg_transaction_amount=round(avg_tx, 2),
        avg_monthly_income=round(avg_monthly_income, 2),
        avg_monthly_expense=round(avg_monthly_expense, 2),
        top_income_categories=top_income_categories,
        top_expense_categories=top_expense_categories,
        weekly_trends=weekly_trends,
        highest_single_expense=highest_expense,
        highest_single_income=highest_income,
    )
