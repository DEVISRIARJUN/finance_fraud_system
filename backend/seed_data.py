import os
import json
from datetime import datetime, timedelta
from database import engine, SessionLocal, Base
from models import Account, Transaction, Budget, Subscription, FraudAlert, MerchantBlocklist
from fraud_engine import haversine_distance_km

def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("[SEED] Seeding Accounts...")
        acc_checking = Account(
            name="Primary Checking",
            type="checking",
            balance=5420.50,
            currency="USD",
            account_number_mask="**** 8492",
            is_frozen=False
        )
        acc_savings = Account(
            name="High-Yield Vault",
            type="savings",
            balance=24800.00,
            currency="USD",
            account_number_mask="**** 3109",
            is_frozen=False
        )
        acc_credit = Account(
            name="Platinum Elite Rewards Card",
            type="credit_card",
            balance=1420.30,
            currency="USD",
            account_number_mask="**** 5921",
            is_frozen=False
        )
        acc_invest = Account(
            name="Apex Wealth Brokerage & Index",
            type="investment",
            balance=48650.00,
            currency="USD",
            account_number_mask="**** 7740",
            is_frozen=False
        )
        db.add_all([acc_checking, acc_savings, acc_credit, acc_invest])
        db.commit()

        print("[SEED] Seeding Budgets...")
        budgets_data = [
            {"category": "Groceries", "limit": 650.0, "color": "#10b981", "icon": "shopping-cart"},
            {"category": "Dining", "limit": 450.0, "color": "#f59e0b", "icon": "utensils"},
            {"category": "Utilities", "limit": 280.0, "color": "#3b82f6", "icon": "zap"},
            {"category": "Subscriptions", "limit": 160.0, "color": "#8b5cf6", "icon": "repeat"},
            {"category": "Tech & Electronics", "limit": 300.0, "color": "#06b6d4", "icon": "laptop"},
            {"category": "Travel", "limit": 400.0, "color": "#ec4899", "icon": "plane"},
            {"category": "Health & Fitness", "limit": 200.0, "color": "#14b8a6", "icon": "activity"},
            {"category": "Entertainment", "limit": 220.0, "color": "#a855f7", "icon": "film"}
        ]
        for b in budgets_data:
            db.add(Budget(category=b["category"], monthly_limit=b["limit"], color=b["color"], icon=b["icon"]))
        db.commit()

        print("[SEED] Seeding Subscriptions...")
        subs_data = [
            {"name": "Netflix Premium 4K", "merchant": "Netflix", "category": "Subscriptions", "amount": 22.99, "cycle": "monthly", "date": "2026-08-25"},
            {"name": "Spotify Family", "merchant": "Spotify", "category": "Subscriptions", "amount": 16.99, "cycle": "monthly", "date": "2026-08-22"},
            {"name": "ChatGPT Plus Subscription", "merchant": "OpenAI", "category": "Subscriptions", "amount": 20.00, "cycle": "monthly", "date": "2026-08-18"},
            {"name": "GitHub Copilot Enterprise", "merchant": "GitHub", "category": "Subscriptions", "amount": 19.00, "cycle": "monthly", "date": "2026-08-19"},
            {"name": "AWS Cloud Hosting Tier", "merchant": "Amazon Web Services", "category": "Tech & Electronics", "amount": 48.50, "cycle": "monthly", "date": "2026-08-28"},
            {"name": "Equinox All-Access Gym", "merchant": "Equinox", "category": "Health & Fitness", "amount": 85.00, "cycle": "monthly", "date": "2026-08-30"}
        ]
        for s in subs_data:
            db.add(Subscription(
                name=s["name"],
                merchant=s["merchant"],
                category=s["category"],
                amount=s["amount"],
                billing_cycle=s["cycle"],
                next_billing_date=s["date"],
                is_active=True,
                cancellation_url="https://example.com/cancel"
            ))
        db.commit()

        print("[SEED] Seeding Merchant Blocklist...")
        blocklist_entries = [
            MerchantBlocklist(merchant_name="DarkNet Wire Global", reason="Known unauthorized wire relay", created_at=datetime.utcnow() - timedelta(days=12)),
            MerchantBlocklist(merchant_name="FastCash Payday Offshore", reason="Predatory unauthorized lender recurring charge", created_at=datetime.utcnow() - timedelta(days=20))
        ]
        db.add_all(blocklist_entries)
        db.commit()

        print("[SEED] Seeding Historical & Current Transactions...")
        now = datetime.utcnow()
        transactions = []

        # Monthly Salaries across past 3 months
        for i in range(3, -1, -1):
            salary_date = now - timedelta(days=i * 30 + 10)
            transactions.append(Transaction(
                account_id=acc_checking.id,
                type="income",
                category="Salary & Income",
                merchant="Apex Fintech Corp Direct Deposit",
                amount=4600.00,
                description="Bi-weekly executive payroll",
                timestamp=salary_date,
                location_city="New York, USA",
                location_lat=40.7128,
                location_lng=-74.0060,
                risk_score=0.0,
                risk_level="SAFE",
                risk_reasons="[]",
                is_flagged=False,
                status="cleared"
            ))

        # Regular Expense Seed List
        historical_expenses = [
            # Recent Days
            {"days_ago": 1, "m": "Whole Foods Market", "cat": "Groceries", "amt": 142.60, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 2, "m": "Starbucks Reserve Roastery", "cat": "Dining", "amt": 14.50, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 3, "m": "ConEdison Power & Gas", "cat": "Utilities", "amt": 165.20, "acc": acc_checking.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 4, "m": "Sweetgreen Manhattan", "cat": "Dining", "amt": 22.40, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 5, "m": "Trader Joe's Chelsea", "cat": "Groceries", "amt": 88.90, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 6, "m": "Uber Premier", "cat": "Travel", "amt": 45.80, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 7, "m": "Apple Store 5th Ave", "cat": "Tech & Electronics", "amt": 129.00, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 8, "m": "Nobu Downtown Sushi", "cat": "Dining", "amt": 185.00, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 10, "m": "AMC Empire 25 IMAX", "cat": "Entertainment", "amt": 38.00, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 12, "m": "CVS Pharmacy Manhattan", "cat": "Health & Fitness", "amt": 34.50, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 14, "m": "Costco Wholesale", "cat": "Groceries", "amt": 245.30, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            # Last Month
            {"days_ago": 28, "m": "Delta Air Lines JFK-SFO", "cat": "Travel", "amt": 380.00, "acc": acc_credit.id, "city": "San Francisco, USA", "lat": 37.7749, "lng": -122.4194},
            {"days_ago": 32, "m": "Verizon Fios Gigabit", "cat": "Utilities", "amt": 89.99, "acc": acc_checking.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 35, "m": "Best Buy Electronics", "cat": "Tech & Electronics", "amt": 249.99, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 40, "m": "Whole Foods Market", "cat": "Groceries", "amt": 160.00, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 45, "m": "Chipotle Mexican Grill", "cat": "Dining", "amt": 16.25, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
            {"days_ago": 50, "m": "Equinox All-Access", "cat": "Health & Fitness", "amt": 85.00, "acc": acc_credit.id, "city": "New York, USA", "lat": 40.7128, "lng": -74.0060},
        ]

        for item in historical_expenses:
            tx_time = now - timedelta(days=item["days_ago"], hours=item.get("hours", 3))
            t = Transaction(
                account_id=item["acc"],
                type="expense",
                category=item["cat"],
                merchant=item["m"],
                amount=item["amt"],
                description=f"Standard purchase at {item['m']}",
                timestamp=tx_time,
                location_city=item["city"],
                location_lat=item["lat"],
                location_lng=item["lng"],
                risk_score=5.0,
                risk_level="SAFE",
                risk_reasons="[]",
                is_flagged=False,
                status="cleared"
            )
            transactions.append(t)

        db.add_all(transactions)
        db.commit()

        # Seed 1 Active Pre-staged High-Risk Fraud Alert
        # Scenario: User was in New York 45 minutes ago buying groceries, suddenly $2,850 charged in Tokyo, Japan!
        print("[SEED] Seeding Active Pre-staged Fraud Case...")
        fraud_time = now - timedelta(minutes=45)
        fraud_reasons = [
            {
                "factor": "Impossible Geographic Velocity",
                "description": "Transaction occurred in Tokyo, Japan 45 minutes after New York purchase (10,850 km away). Required velocity is 14,466 km/h.",
                "severity": "critical",
                "score_impact": 80.0
            },
            {
                "factor": "Statistical Spending Outlier",
                "description": "Charge of $2,850.00 is 18.5x higher than your average for 'Luxury & Jewelry' (Z-Score: +6.4 standard deviations).",
                "severity": "high",
                "score_impact": 55.0
            }
        ]

        fraud_tx = Transaction(
            account_id=acc_credit.id,
            type="expense",
            category="Luxury & Jewelry",
            merchant="Ginza Diamond Emporium Tokyo",
            amount=2850.00,
            description="High-value international jewelry POS authorization",
            timestamp=fraud_time,
            location_city="Tokyo, Japan",
            location_lat=35.6762,
            location_lng=139.6503,
            risk_score=94.5,
            risk_level="HIGH_RISK",
            risk_reasons=json.dumps(fraud_reasons),
            is_flagged=True,
            status="pending"
        )
        db.add(fraud_tx)
        db.commit()

        fraud_alert = FraudAlert(
            transaction_id=fraud_tx.id,
            risk_score=94.5,
            risk_factors=json.dumps(fraud_reasons),
            status="active",
            created_at=fraud_time,
            notes="Automated Real-Time AI Interception: Geo-velocity violation + amount spike"
        )
        db.add(fraud_alert)
        db.commit()

        print("[SUCCESS] Database seeding successfully completed with rich financial & fraud records!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
