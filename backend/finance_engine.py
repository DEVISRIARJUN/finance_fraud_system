import calendar
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models import Account, Transaction, Budget, Subscription, FraudAlert

CATEGORY_COLORS = {
    "Groceries": "#10b981",
    "Dining": "#f59e0b",
    "Subscriptions": "#8b5cf6",
    "Utilities": "#3b82f6",
    "Tech & Electronics": "#06b6d4",
    "Travel": "#ec4899",
    "Health & Fitness": "#14b8a6",
    "Entertainment": "#a855f7",
    "Luxury & Jewelry": "#f43f5e",
    "Crypto & Transfers": "#e11d48",
    "General Merchandise": "#64748b",
    "Salary & Income": "#22c55e"
}

class FinanceAnalyticsEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, year: int = None, month: int = None) -> Dict[str, Any]:
        now = datetime.utcnow()
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        # 1. Accounts & Net Worth
        accounts = self.db.query(Account).all()
        net_worth = 0.0
        for acc in accounts:
            if acc.type == "credit_card":
                net_worth -= acc.balance  # credit balance is liability
            else:
                net_worth += acc.balance

        # 2. Monthly Income & Expense
        month_txs = (
            self.db.query(Transaction)
            .filter(
                extract("year", Transaction.timestamp) == year,
                extract("month", Transaction.timestamp) == month,
                Transaction.status != "confirmed_fraud"  # exclude reversed fraud from true spend
            )
            .all()
        )

        total_income = sum(t.amount for t in month_txs if t.type == "income")
        total_expense = sum(t.amount for t in month_txs if t.type == "expense")
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100.0) if total_income > 0 else 0.0

        # 3. Category Breakdown
        category_map: Dict[str, Dict[str, Any]] = {}
        for t in month_txs:
            if t.type == "expense":
                cat = t.category
                if cat not in category_map:
                    category_map[cat] = {
                        "category": cat,
                        "amount": 0.0,
                        "count": 0,
                        "color": CATEGORY_COLORS.get(cat, "#64748b")
                    }
                category_map[cat]["amount"] += t.amount
                category_map[cat]["count"] += 1

        category_breakdown = []
        for cat, data in sorted(category_map.items(), key=lambda x: x[1]["amount"], reverse=True):
            pct = (data["amount"] / total_expense * 100.0) if total_expense > 0 else 0.0
            category_breakdown.append({
                "category": cat,
                "amount": round(data["amount"], 2),
                "percentage": round(pct, 1),
                "transaction_count": data["count"],
                "color": data["color"]
            })

        # 4. Cashflow History (Past 6 Months)
        cashflow_history = self._get_cashflow_history(now)

        # 5. Financial Health Score
        health_score, health_grade = self._compute_health_score(savings_rate, total_income, total_expense)

        # 6. Active Fraud Alerts
        active_alerts_count = self.db.query(FraudAlert).filter(FraudAlert.status == "active").count()

        # 7. Subscriptions Summary
        subs = self.db.query(Subscription).filter(Subscription.is_active == True).all()
        monthly_subs = sum(s.amount if s.billing_cycle == "monthly" else (s.amount / 12.0) for s in subs)
        annual_subs = monthly_subs * 12.0

        # 8. Forecasted Expense for End of Month
        forecast_data = self.get_forecast(year, month)

        return {
            "net_worth": round(net_worth, 2),
            "total_income_this_month": round(total_income, 2),
            "total_expense_this_month": round(total_expense, 2),
            "net_savings_this_month": round(net_savings, 2),
            "savings_rate_this_month": round(savings_rate, 1),
            "financial_health_score": health_score,
            "health_grade": health_grade,
            "active_fraud_alerts_count": active_alerts_count,
            "total_subscriptions_monthly": round(monthly_subs, 2),
            "total_subscriptions_annual": round(annual_subs, 2),
            "category_breakdown": category_breakdown,
            "cashflow_history": cashflow_history,
            "predicted_monthly_expense": forecast_data["projected_total_month_expense"]
        }

    def _get_cashflow_history(self, current_dt: datetime) -> List[Dict[str, Any]]:
        history = []
        # Go back 5 months + current month
        for i in range(5, -1, -1):
            target_date = current_dt - timedelta(days=i * 30)
            y = target_date.year
            m = target_date.month
            m_label = target_date.strftime("%b %Y")

            txs = (
                self.db.query(Transaction)
                .filter(
                    extract("year", Transaction.timestamp) == y,
                    extract("month", Transaction.timestamp) == m,
                    Transaction.status != "confirmed_fraud"
                )
                .all()
            )
            inc = sum(t.amount for t in txs if t.type == "income")
            exp = sum(t.amount for t in txs if t.type == "expense")
            sav = inc - exp
            rate = (sav / inc * 100.0) if inc > 0 else 0.0

            history.append({
                "month": m_label,
                "income": round(inc, 2),
                "expenses": round(exp, 2),
                "net_savings": round(sav, 2),
                "savings_rate": round(rate, 1)
            })
        return history

    def _compute_health_score(self, savings_rate: float, income: float, expense: float) -> Tuple[int, str]:
        score = 50.0

        # Savings rate component (+/- 30 points)
        if savings_rate >= 30.0:
            score += 30.0
        elif savings_rate >= 20.0:
            score += 20.0
        elif savings_rate >= 10.0:
            score += 10.0
        elif savings_rate < 0.0:
            score -= 25.0  # Deficit

        # Budget adherence component
        budgets = self.db.query(Budget).all()
        if budgets:
            over_budget_count = 0
            for b in budgets:
                spent = (
                    self.db.query(func.sum(Transaction.amount))
                    .filter(
                        Transaction.category == b.category,
                        Transaction.type == "expense"
                    )
                    .scalar() or 0.0
                )
                if spent > b.monthly_limit:
                    over_budget_count += 1
            if over_budget_count == 0:
                score += 15.0
            else:
                score -= min(20.0, over_budget_count * 8.0)

        # Unresolved fraud factor
        active_alerts = self.db.query(FraudAlert).filter(FraudAlert.status == "active").count()
        score -= min(25.0, active_alerts * 10.0)

        final_score = int(max(10, min(99, score)))

        if final_score >= 80:
            grade = "Excellent"
        elif final_score >= 65:
            grade = "Good"
        elif final_score >= 45:
            grade = "Fair"
        else:
            grade = "Needs Attention"

        return final_score, grade

    def get_forecast(self, year: int, month: int) -> Dict[str, Any]:
        now = datetime.utcnow()
        days_in_month = calendar.monthrange(year, month)[1]
        
        # If current month, use today's day; if past month, use all days
        if year == now.year and month == now.month:
            days_elapsed = max(1, now.day)
        elif datetime(year, month, 1) < datetime(now.year, now.month, 1):
            days_elapsed = days_in_month
        else:
            days_elapsed = 1

        days_remaining = max(0, days_in_month - days_elapsed)

        current_spent = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                extract("year", Transaction.timestamp) == year,
                extract("month", Transaction.timestamp) == month,
                Transaction.type == "expense",
                Transaction.status != "confirmed_fraud"
            )
            .scalar() or 0.0
        )

        daily_burn_rate = current_spent / days_elapsed

        # Factor in committed subscriptions remaining in month
        committed_remaining_subs = 0.0
        active_subs = self.db.query(Subscription).filter(Subscription.is_active == True).all()
        for s in active_subs:
            # If day of billing is ahead in month
            try:
                sub_day = int(s.next_billing_date.split("-")[-1]) if "-" in s.next_billing_date else 15
                if sub_day > days_elapsed:
                    committed_remaining_subs += s.amount
            except Exception:
                pass

        projected_total = current_spent + (daily_burn_rate * days_remaining) + committed_remaining_subs

        # Total monthly budget cap
        total_budget = self.db.query(func.sum(Budget.monthly_limit)).scalar() or 0.0
        budget_diff = projected_total - total_budget if total_budget > 0 else 0.0

        if total_budget > 0:
            if projected_total > total_budget * 1.05:
                status = "over_budget"
            elif projected_total > total_budget * 0.90:
                status = "warning"
            else:
                status = "on_track"
        else:
            status = "on_track"

        # Generate day-by-day trajectory points for chart
        forecast_points = []
        running_spent = 0.0
        step_spend = daily_burn_rate
        for d in range(1, days_in_month + 1):
            if d <= days_elapsed:
                # Real/interpolated
                running_spent = (current_spent / days_elapsed) * d
                forecast_points.append({"day": f"Day {d}", "actual": round(running_spent, 2), "projected": None})
            else:
                running_spent += step_spend
                forecast_points.append({"day": f"Day {d}", "actual": None, "projected": round(running_spent, 2)})

        return {
            "current_spent": round(current_spent, 2),
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "daily_burn_rate": round(daily_burn_rate, 2),
            "projected_total_month_expense": round(projected_total, 2),
            "total_budget": round(total_budget, 2),
            "budget_comparison": round(budget_diff, 2),
            "status": status,
            "forecast_points": forecast_points
        }

    def get_budgets_status(self) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        budgets = self.db.query(Budget).all()
        results = []

        for b in budgets:
            spent = (
                self.db.query(func.sum(Transaction.amount))
                .filter(
                    extract("year", Transaction.timestamp) == now.year,
                    extract("month", Transaction.timestamp) == now.month,
                    Transaction.category == b.category,
                    Transaction.type == "expense",
                    Transaction.status != "confirmed_fraud"
                )
                .scalar() or 0.0
            )
            pct = (spent / b.monthly_limit * 100.0) if b.monthly_limit > 0 else 0.0
            rem = b.monthly_limit - spent

            if pct >= 100.0:
                st = "exceeded"
            elif pct >= 80.0:
                st = "warning"
            else:
                st = "healthy"

            results.append({
                "id": b.id,
                "category": b.category,
                "monthly_limit": b.monthly_limit,
                "current_spent": round(spent, 2),
                "remaining": round(rem, 2),
                "percentage": round(pct, 1),
                "status": st,
                "color": b.color or CATEGORY_COLORS.get(b.category, "#10b981"),
                "icon": b.icon or "tag"
            })
        return results
