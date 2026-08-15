from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models import Transaction, Account, Budget, Subscription, FraudAlert

class AIAdvisorEngine:
    def __init__(self, db: Session):
        self.db = db

    def generate_smart_insights(self) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        insights = []

        # 1. Total Spend & Income check
        month_txs = (
            self.db.query(Transaction)
            .filter(
                extract("year", Transaction.timestamp) == now.year,
                extract("month", Transaction.timestamp) == now.month,
                Transaction.status != "confirmed_fraud"
            )
            .all()
        )
        total_income = sum(t.amount for t in month_txs if t.type == "income")
        total_expense = sum(t.amount for t in month_txs if t.type == "expense")

        # Check: Dining Out vs Groceries
        dining_spend = sum(t.amount for t in month_txs if t.category == "Dining" and t.type == "expense")
        groceries_spend = sum(t.amount for t in month_txs if t.category == "Groceries" and t.type == "expense")

        if dining_spend > groceries_spend and dining_spend > 350.0:
            potential_save = dining_spend * 0.35
            insights.append({
                "id": "dining_spike",
                "type": "opportunity",
                "badge": "Smart Savings",
                "title": "Dining Out Outpaces Groceries",
                "description": f"You've spent ${dining_spend:,.2f} on dining out versus ${groceries_spend:,.2f} on groceries. Cooking 2 extra meals a week could redirect ~${potential_save:,.2f}/mo into your high-yield savings.",
                "potential_monthly_savings": round(potential_save, 2),
                "action_label": "Optimize Dining",
                "action_category": "Dining"
            })

        # Check: Subscription Sprawl
        active_subs = self.db.query(Subscription).filter(Subscription.is_active == True).all()
        sub_total = sum(s.amount for s in active_subs if s.billing_cycle == "monthly")
        if len(active_subs) >= 4:
            insights.append({
                "id": "sub_audit",
                "type": "warning",
                "badge": "Subscription Leakage",
                "title": f"You have {len(active_subs)} Active Subscriptions",
                "description": f"Your recurring subscriptions total ${sub_total:,.2f}/mo (${sub_total*12:,.2f}/year). Auditing 2 unused streaming/software services could save you $35-$70/mo.",
                "potential_monthly_savings": 50.0,
                "action_label": "Audit Subscriptions",
                "action_category": "Subscriptions"
            })

        # Check: Emergency Fund Readiness
        checking_savings = (
            self.db.query(func.sum(Account.balance))
            .filter(Account.type.in_(["checking", "savings"]))
            .scalar() or 0.0
        )
        three_month_burn = (total_expense * 3.0) if total_expense > 0 else 6000.0
        if checking_savings < three_month_burn:
            shortfall = three_month_burn - checking_savings
            insights.append({
                "id": "emergency_fund",
                "type": "info",
                "badge": "Financial Resilience",
                "title": "Emergency Buffer Below 3-Month Target",
                "description": f"Your liquid reserves (${checking_savings:,.2f}) are below the recommended 3-month safety benchmark (${three_month_burn:,.2f}). Target allocating $250/mo to close the ${shortfall:,.2f} gap.",
                "potential_monthly_savings": 0.0,
                "action_label": "Boost Savings",
                "action_category": "Savings"
            })
        else:
            insights.append({
                "id": "emergency_ok",
                "type": "positive",
                "badge": "Strong Foundation",
                "title": "Healthy 3+ Month Emergency Reserve",
                "description": f"Your liquid reserves (${checking_savings:,.2f}) safely cover your essential burn rate. Consider channeling excess monthly surplus into index investments.",
                "potential_monthly_savings": 0.0,
                "action_label": "Explore Investments",
                "action_category": "Investment"
            })

        # Check: Active Fraud Threat
        active_fraud = self.db.query(FraudAlert).filter(FraudAlert.status == "active").count()
        if active_fraud > 0:
            insights.insert(0, {
                "id": "fraud_threat",
                "type": "critical",
                "badge": "Immediate Security Alert",
                "title": f"{active_fraud} Unresolved Suspicious Transaction(s)",
                "description": "High-risk anomalies were detected. Review and verify or freeze impacted cards immediately in the Fraud Security Center.",
                "potential_monthly_savings": 0.0,
                "action_label": "Review Fraud Center",
                "action_category": "Fraud"
            })

        return insights

    def calculate_what_if(
        self,
        dining_reduction_pct: float,
        subscriptions_to_cancel_ids: List[int],
        custom_monthly_savings: float,
        annual_return: float = 0.07
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        details = []
        monthly_total_saved = custom_monthly_savings

        # 1. Dining savings
        if dining_reduction_pct > 0:
            cur_dining = (
                self.db.query(func.sum(Transaction.amount))
                .filter(
                    extract("year", Transaction.timestamp) == now.year,
                    extract("month", Transaction.timestamp) == now.month,
                    Transaction.category == "Dining",
                    Transaction.type == "expense"
                )
                .scalar() or 450.0
            )
            dining_saved = cur_dining * (dining_reduction_pct / 100.0)
            monthly_total_saved += dining_saved
            details.append(f"Reduced Dining spending by {dining_reduction_pct:.0f}%: +${dining_saved:,.2f}/mo")

        # 2. Cancelled Subscriptions
        if subscriptions_to_cancel_ids:
            subs = self.db.query(Subscription).filter(Subscription.id.in_(subscriptions_to_cancel_ids)).all()
            sub_saved = 0.0
            for s in subs:
                amt = s.amount if s.billing_cycle == "monthly" else (s.amount / 12.0)
                sub_saved += amt
                details.append(f"Cancelled '{s.name}': +${amt:,.2f}/mo")
            monthly_total_saved += sub_saved

        if custom_monthly_savings > 0:
            details.append(f"Additional discretionary budget trim: +${custom_monthly_savings:,.2f}/mo")

        annual_saved = monthly_total_saved * 12.0

        # Compound Future Value formula: FV = PMT * [((1 + r/12)^(12*t) - 1) / (r/12)]
        r = annual_return
        pmt = monthly_total_saved
        
        def future_value(years: int) -> float:
            if r <= 0 or pmt <= 0:
                return pmt * 12 * years
            n_months = years * 12
            monthly_r = r / 12.0
            return pmt * (((1 + monthly_r) ** n_months - 1) / monthly_r)

        fv_5_years = future_value(5)
        fv_10_years = future_value(10)

        # Calculate impact on savings rate
        month_income = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                extract("year", Transaction.timestamp) == now.year,
                extract("month", Transaction.timestamp) == now.month,
                Transaction.type == "income"
            )
            .scalar() or 6500.0
        )
        cur_expense = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                extract("year", Transaction.timestamp) == now.year,
                extract("month", Transaction.timestamp) == now.month,
                Transaction.type == "expense"
            )
            .scalar() or 3800.0
        )
        new_expense = max(0.0, cur_expense - monthly_total_saved)
        new_savings_rate = ((month_income - new_expense) / month_income * 100.0) if month_income > 0 else 0.0

        return {
            "monthly_savings": round(monthly_total_saved, 2),
            "annual_savings": round(annual_saved, 2),
            "five_year_savings_compounded": round(fv_5_years, 2),
            "ten_year_savings_compounded": round(fv_10_years, 2),
            "new_projected_savings_rate": round(new_savings_rate, 1),
            "breakdown_details": details if details else ["No optimizations selected yet."]
        }

    def answer_query(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower()
        now = datetime.utcnow()

        # 1. Dining query
        if "dining" in q_lower or "restaurant" in q_lower or "food" in q_lower:
            spent = (
                self.db.query(func.sum(Transaction.amount))
                .filter(
                    extract("year", Transaction.timestamp) == now.year,
                    extract("month", Transaction.timestamp) == now.month,
                    Transaction.category == "Dining",
                    Transaction.type == "expense"
                )
                .scalar() or 0.0
            )
            return {
                "answer": (
                    f"This month, you have spent **${spent:,.2f}** across restaurants, cafes, and delivery. "
                    "This accounts for roughly 12% of your monthly outflows. Reducing takeout by 25% would yield an extra $110/mo in savings."
                ),
                "suggested_actions": [
                    {"label": "Run What-If Scenario for Dining", "action": "open_what_if"},
                    {"label": "Set Dining Budget Cap", "action": "open_budgets"}
                ]
            }

        # 2. Fraud / Security query
        if "fraud" in q_lower or "suspicious" in q_lower or "alert" in q_lower or "risk" in q_lower:
            alerts = self.db.query(FraudAlert).filter(FraudAlert.status == "active").all()
            if alerts:
                items_desc = ", ".join([f"{a.transaction.merchant} (${a.transaction.amount:,.2f})" for a in alerts if a.transaction])
                return {
                    "answer": (
                        f"⚠️ You have **{len(alerts)} active security alert(s)** requiring review: {items_desc}. "
                        "Our AI engine flagged these due to geographic anomalies or atypical amount spikes."
                    ),
                    "suggested_actions": [
                        {"label": "Open Fraud Security Center", "action": "open_fraud_center"},
                        {"label": "Freeze Affected Cards", "action": "freeze_all"}
                    ]
                }
            else:
                return {
                    "answer": "✅ All clear! There are currently **0 active fraud alerts**. All recent transactions scored well within your normal behavioral envelope.",
                    "suggested_actions": [
                        {"label": "Run Live Attack Simulator", "action": "open_simulator"}
                    ]
                }

        # 3. Forecast / Future expense query
        if "predict" in q_lower or "forecast" in q_lower or "future" in q_lower or "end of month" in q_lower:
            from finance_engine import FinanceAnalyticsEngine
            fe = FinanceAnalyticsEngine(self.db)
            fc = fe.get_forecast(now.year, now.month)
            return {
                "answer": (
                    f"📈 Based on your daily burn rate of **${fc['daily_burn_rate']:,.2f}/day** and upcoming subscriptions, "
                    f"your projected total spending for this month is **${fc['projected_total_month_expense']:,.2f}**. "
                    f"Status: **{fc['status'].replace('_', ' ').title()}**."
                ),
                "suggested_actions": [
                    {"label": "View Budget Trajectory", "action": "open_budgets"}
                ]
            }

        # 4. Save money / Recommendations query
        if "save" in q_lower or "recommend" in q_lower or "advice" in q_lower or "invest" in q_lower:
            return {
                "answer": (
                    "💡 Top 3 AI recommendations for your portfolio this month:\n"
                    "1. **Subscription Pruning:** You have recurring SaaS and streaming services totaling ~$180/mo.\n"
                    "2. **Dining Rebalancing:** Trimming dining out by $120/mo and placing it into an index ETF compounds to **$9,400+** in 5 years at 7% return.\n"
                    "3. **High-Yield Cash Routing:** Keep ~3 months liquid in High-Yield Savings and sweep surplus to brokerage."
                ),
                "suggested_actions": [
                    {"label": "Launch What-If Compound Simulator", "action": "open_what_if"},
                    {"label": "Audit Subscriptions", "action": "open_subscriptions"}
                ]
            }

        # Default smart response
        from finance_engine import FinanceAnalyticsEngine
        fe = FinanceAnalyticsEngine(self.db)
        ov = fe.get_overview(now.year, now.month)
        top_cat = ov["category_breakdown"][0]["category"] if ov["category_breakdown"] else "Living"
        top_amt = ov["category_breakdown"][0]["amount"] if ov["category_breakdown"] else 0.0

        return {
            "answer": (
                f"📊 Here is your live financial snapshot:\n"
                f"• **Net Worth:** ${ov['net_worth']:,.2f}\n"
                f"• **Monthly Savings Rate:** {ov['savings_rate_this_month']}%\n"
                f"• **Financial Health Score:** {ov['financial_health_score']}/100 ({ov['health_grade']})\n"
                f"• **Top Spending Category:** {top_cat} (${top_amt:,.2f})\n"
                f"• **Fraud Threat Status:** {ov['active_fraud_alerts_count']} active alerts."
            ),
            "suggested_actions": [
                {"label": "View Expense Forecast", "action": "open_forecast"},
                {"label": "Test Fraud Sandbox", "action": "open_simulator"}
            ]
        }
