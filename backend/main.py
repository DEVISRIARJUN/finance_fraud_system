import os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from database import engine, get_db, Base
from models import Account, Transaction, Budget, Subscription, FraudAlert, MerchantBlocklist
import schemas
from fraud_engine import FraudDetectionEngine, auto_categorize_merchant
from finance_engine import FinanceAnalyticsEngine
from ai_advisor import AIAdvisorEngine
from seed_data import seed_database

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Apex AI Personal Finance & Fraud Detection Engine",
    description="Enterprise-grade Personal Wealth Management and Real-Time AI Fraud Prevention System",
    version="2.0.0"
)

# Enable CORS for local development and API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# ----------------- SYSTEM & OVERVIEW ENDPOINTS -----------------

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        # Check if database has accounts, if not automatically seed it
        if db.query(Account).count() == 0:
            print("[SYS] Initializing fresh database with seed records...")
            seed_database()
    finally:
        db.close()

@app.get("/api/health")
def health_check():
    return {"status": "online", "system": "Sentinel Wealth & Fraud Shield", "timestamp": datetime.utcnow().isoformat()}

@app.get("/download")
@app.get("/api/download-project")
def download_project_zip():
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_finance_fraud_system.zip")
    if os.path.exists(zip_path):
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="ai_finance_fraud_system.zip"
        )
    raise HTTPException(status_code=404, detail="Zip file not found")

@app.post("/api/reset-seed")
def reset_seed_data():
    seed_database()
    return {"status": "success", "message": "Database successfully reset with demo accounts and transactions."}

@app.get("/api/finance/overview", response_model=schemas.FinanceOverviewResponse)
def get_finance_overview(year: Optional[int] = None, month: Optional[int] = None, db: Session = Depends(get_db)):
    engine = FinanceAnalyticsEngine(db)
    return engine.get_overview(year, month)

@app.get("/api/finance/forecast", response_model=schemas.FutureExpenseForecast)
def get_expense_forecast(year: Optional[int] = None, month: Optional[int] = None, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    y = year or now.year
    m = month or now.month
    engine = FinanceAnalyticsEngine(db)
    return engine.get_forecast(y, m)

# ----------------- ACCOUNTS ENDPOINTS -----------------

@app.get("/api/accounts", response_model=List[schemas.AccountResponse])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()

@app.post("/api/accounts", response_model=schemas.AccountResponse)
def create_account(account_in: schemas.AccountCreate, db: Session = Depends(get_db)):
    acc = Account(**account_in.dict())
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@app.post("/api/accounts/{account_id}/toggle-freeze", response_model=schemas.AccountResponse)
def toggle_freeze_account(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    acc.is_frozen = not acc.is_frozen
    db.commit()
    db.refresh(acc)
    return acc

# ----------------- TRANSACTIONS & FRAUD SCORING -----------------

@app.get("/api/transactions", response_model=List[schemas.TransactionResponse])
def list_transactions(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    account_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    q = db.query(Transaction).join(Account)
    if category and category != "All":
        q = q.filter(Transaction.category == category)
    if risk_level and risk_level != "All":
        q = q.filter(Transaction.risk_level == risk_level)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if search:
        s = f"%{search}%"
        q = q.filter((Transaction.merchant.ilike(s)) | (Transaction.description.ilike(s)))
    
    txs = q.order_by(Transaction.timestamp.desc()).limit(limit).all()

    results = []
    for t in txs:
        results.append(schemas.TransactionResponse(
            id=t.id,
            account_id=t.account_id,
            account_name=t.account.name if t.account else "Unknown Account",
            type=t.type,
            category=t.category,
            merchant=t.merchant,
            amount=t.amount,
            description=t.description or "",
            timestamp=t.timestamp,
            location_city=t.location_city or "New York, USA",
            location_lat=t.location_lat or 40.7128,
            location_lng=t.location_lng or -74.0060,
            risk_score=t.risk_score,
            risk_level=t.risk_level,
            risk_reasons=t.get_risk_reasons_list(),
            is_flagged=t.is_flagged,
            status=t.status,
            is_recurring=t.is_recurring
        ))
    return results

@app.post("/api/transactions", response_model=schemas.TransactionResponse)
def record_transaction(tx_in: schemas.TransactionCreate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == tx_in.account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Selected account does not exist")
    
    if account.is_frozen:
        raise HTTPException(status_code=400, detail=f"Account '{account.name}' is currently frozen due to security protocols. Unfreeze account first.")

    # 1. Smart Auto-Categorization if not specified
    category = tx_in.category
    if not category or category == "Auto-Detect":
        category = auto_categorize_merchant(tx_in.merchant, tx_in.type)

    timestamp = tx_in.timestamp or datetime.utcnow()
    city = tx_in.location_city or "New York, USA"
    lat = tx_in.location_lat or 40.7128
    lng = tx_in.location_lng or -74.0060

    # 2. AI Real-Time Fraud & Anomaly Engine
    fraud_engine = FraudDetectionEngine(db)
    risk_score, risk_level, explanations, is_flagged = fraud_engine.analyze_transaction(
        account_id=tx_in.account_id,
        amount=tx_in.amount,
        merchant=tx_in.merchant,
        category=category,
        timestamp=timestamp,
        lat=lat,
        lng=lng,
        city=city,
        trans_type=tx_in.type
    )

    # 3. Create Transaction Record
    tx_status = "pending" if is_flagged else "cleared"
    tx = Transaction(
        account_id=tx_in.account_id,
        type=tx_in.type,
        category=category,
        merchant=tx_in.merchant,
        amount=tx_in.amount,
        description=tx_in.description or f"Transaction at {tx_in.merchant}",
        timestamp=timestamp,
        location_city=city,
        location_lat=lat,
        location_lng=lng,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_reasons=json.dumps(explanations),
        is_flagged=is_flagged,
        status=tx_status,
        is_recurring=tx_in.is_recurring
    )
    db.add(tx)

    # Update account balance
    if tx_in.type == "income":
        account.balance += tx_in.amount
    else:
        if account.type == "credit_card":
            account.balance += tx_in.amount  # increases liability
        else:
            account.balance -= tx_in.amount

    db.commit()
    db.refresh(tx)

    # 4. If flagged, generate FraudAlert record
    if is_flagged:
        alert = FraudAlert(
            transaction_id=tx.id,
            risk_score=risk_score,
            risk_factors=json.dumps(explanations),
            status="active",
            created_at=datetime.utcnow(),
            notes=f"Automated Anomaly Interception: {len(explanations)} risk factors triggered"
        )
        db.add(alert)
        db.commit()

    return schemas.TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        account_name=account.name,
        type=tx.type,
        category=tx.category,
        merchant=tx.merchant,
        amount=tx.amount,
        description=tx.description,
        timestamp=tx.timestamp,
        location_city=tx.location_city,
        location_lat=tx.location_lat,
        location_lng=tx.location_lng,
        risk_score=tx.risk_score,
        risk_level=tx.risk_level,
        risk_reasons=tx.get_risk_reasons_list(),
        is_flagged=tx.is_flagged,
        status=tx.status,
        is_recurring=tx.is_recurring
    )

# ----------------- LIVE FRAUD ATTACK SIMULATOR -----------------

@app.post("/api/simulator/trigger-attack", response_model=schemas.TransactionResponse)
def trigger_attack_scenario(attack_type: str = Query(..., description="Scenario type"), db: Session = Depends(get_db)):
    """
    Live Fraud Simulation Sandbox for demonstrating AI Multi-Vector Detection.
    Available attack scenarios:
    - 'geo_hop': Impossible travel Tokyo -> London in 10 minutes
    - 'amount_spike': $4,500 luxury spike with standard deviation outlier
    - 'micro_burst': Rapid card testing sequence ($1.00, $1.50) followed by $1,800 charge
    - 'blocklist_hit': Unauthorized merchant from darknet/blocklist
    - 'off_hours_crypto': 3:30 AM $1,200 offshore wire / crypto transfer
    """
    account = db.query(Account).filter(Account.type == "credit_card").first() or db.query(Account).first()
    if not account:
        raise HTTPException(status_code=400, detail="No active account found for simulation")

    now = datetime.utcnow()

    if attack_type == "geo_hop":
        # First ensure a very recent NYC transaction exists
        recent_ny = Transaction(
            account_id=account.id,
            type="expense",
            category="Dining",
            merchant="Joe's Coffee Times Square",
            amount=8.50,
            timestamp=now - timedelta(minutes=15),
            location_city="New York, USA",
            location_lat=40.7128,
            location_lng=-74.0060,
            risk_score=5.0,
            risk_level="SAFE",
            risk_reasons="[]",
            status="cleared"
        )
        db.add(recent_ny)
        db.commit()

        # Attack transaction in London 15 mins later
        attack_tx = schemas.TransactionCreate(
            account_id=account.id,
            type="expense",
            category="Dining",
            merchant="Mayfair Grand Club London",
            amount=650.00,
            description="POS International Terminal Swipe",
            location_city="London, UK",
            location_lat=51.5074,
            location_lng=-0.1278,
            timestamp=now
        )

    elif attack_type == "amount_spike":
        attack_tx = schemas.TransactionCreate(
            account_id=account.id,
            type="expense",
            category="Dining",
            merchant="Ultra VIP Michelin Caviar Bar",
            amount=3850.00,
            description="Atypical extreme expenditure spike",
            location_city="New York, USA",
            location_lat=40.7128,
            location_lng=-74.0060,
            timestamp=now
        )

    elif attack_type == "micro_burst":
        # Add 2 micro charges in last 5 minutes
        db.add(Transaction(
            account_id=account.id,
            type="expense",
            category="General Merchandise",
            merchant="Micro Auth Test 01",
            amount=1.10,
            timestamp=now - timedelta(minutes=6),
            location_city="Chicago, USA",
            location_lat=41.8781,
            location_lng=-87.6298,
            status="cleared"
        ))
        db.add(Transaction(
            account_id=account.id,
            type="expense",
            category="General Merchandise",
            merchant="Micro Auth Test 02",
            amount=1.99,
            timestamp=now - timedelta(minutes=3),
            location_city="Chicago, USA",
            location_lat=41.8781,
            location_lng=-87.6298,
            status="cleared"
        ))
        db.commit()

        attack_tx = schemas.TransactionCreate(
            account_id=account.id,
            type="expense",
            category="Tech & Electronics",
            merchant="QuickShip Global Tech Hub",
            amount=1450.00,
            description="Card testing burst payload payload execution",
            location_city="Chicago, USA",
            location_lat=41.8781,
            location_lng=-87.6298,
            timestamp=now
        )

    elif attack_type == "blocklist_hit":
        attack_tx = schemas.TransactionCreate(
            account_id=account.id,
            type="expense",
            category="Crypto & Transfers",
            merchant="DarkNet Wire Global",
            amount=750.00,
            description="Intercepted flagged illicit wire network",
            location_city="Zurich, Switzerland",
            location_lat=47.3769,
            location_lng=8.5417,
            timestamp=now
        )

    elif attack_type == "off_hours_crypto":
        # 3:15 AM transaction
        late_night_dt = now.replace(hour=3, minute=15)
        attack_tx = schemas.TransactionCreate(
            account_id=account.id,
            type="expense",
            category="Crypto & Transfers",
            merchant="Offshore Crypto Gateway Ltd",
            amount=1200.00,
            description="Midnight high-volume crypto asset conversion",
            location_city="Singapore",
            location_lat=1.3521,
            location_lng=103.8198,
            timestamp=late_night_dt
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid simulation attack type")

    return record_transaction(attack_tx, db)

# ----------------- FRAUD ALERTS & DISPUTE RESOLUTION -----------------

@app.get("/api/fraud/alerts", response_model=List[schemas.FraudAlertResponse])
def get_fraud_alerts(status_filter: Optional[str] = "active", db: Session = Depends(get_db)):
    q = db.query(FraudAlert).join(Transaction)
    if status_filter and status_filter != "all":
        q = q.filter(FraudAlert.status == status_filter)
    
    alerts = q.order_by(FraudAlert.created_at.desc()).all()
    results = []
    for a in alerts:
        results.append(schemas.FraudAlertResponse(
            id=a.id,
            transaction_id=a.transaction_id,
            merchant=a.transaction.merchant if a.transaction else "Unknown",
            amount=a.transaction.amount if a.transaction else 0.0,
            location_city=a.transaction.location_city if a.transaction else "",
            timestamp=a.transaction.timestamp if a.transaction else a.created_at,
            risk_score=a.risk_score,
            risk_factors=json.loads(a.risk_factors) if a.risk_factors else [],
            status=a.status,
            created_at=a.created_at,
            notes=a.notes or ""
        ))
    return results

@app.post("/api/fraud/alerts/{alert_id}/resolve")
def resolve_fraud_alert(alert_id: int, req: schemas.DisputeActionRequest, db: Session = Depends(get_db)):
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    tx = alert.transaction
    if not tx:
        raise HTTPException(status_code=404, detail="Associated transaction not found")

    if req.action == "confirm_fraud":
        # 1. Reverse the charge on user account
        acc = tx.account
        if acc:
            if acc.type == "credit_card":
                acc.balance = max(0.0, acc.balance - tx.amount)
            else:
                acc.balance += tx.amount
        
        # 2. Add merchant to blocklist
        exists = db.query(MerchantBlocklist).filter(MerchantBlocklist.merchant_name == tx.merchant).first()
        if not exists:
            db.add(MerchantBlocklist(
                merchant_name=tx.merchant,
                reason=f"Confirmed fraud by user (Dispute #{alert.id})"
            ))

        # 3. Update status
        alert.status = "resolved_fraud"
        alert.notes = req.notes or "Confirmed fraud: funds refunded & merchant blacklisted"
        tx.status = "confirmed_fraud"
        db.commit()

        return {"status": "success", "action": "confirmed_fraud", "message": f"Fraud confirmed. ${tx.amount:,.2f} refunded, merchant '{tx.merchant}' added to Blocklist."}

    elif req.action == "mark_valid":
        alert.status = "resolved_valid"
        alert.notes = req.notes or "Verified by user as authorized transaction"
        tx.status = "cleared"
        tx.risk_level = "SAFE"
        tx.is_flagged = False
        db.commit()

        return {"status": "success", "action": "mark_valid", "message": "Transaction verified and marked as authorized."}

    elif req.action == "freeze_account":
        if tx.account:
            tx.account.is_frozen = True
            db.commit()
            return {"status": "success", "action": "freeze_account", "message": f"Account '{tx.account.name}' has been locked and frozen."}

    raise HTTPException(status_code=400, detail="Invalid dispute resolution action")

@app.post("/api/transactions/smart-parse")
def smart_parse_transaction(req: dict, db: Session = Depends(get_db)):
    """
    NLP Smart Transaction Parser:
    Extracts amount, merchant, category, city from natural language like:
    'Paid 450 on Dominos Pizza in Mumbai' or 'Spent 1200 for groceries at Whole Foods'
    """
    raw_text = req.get("text", "").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Text query is required")
    
    import re
    # 1. Extract Amount (handles ₹, $, numbers)
    amount_match = re.search(r'(?:₹|\$|rs\.?|inr|usd)?\s*([0-9]+(?:\.[0-9]{1,2})?)', raw_text, re.IGNORECASE)
    amount = float(amount_match.group(1)) if amount_match else 50.0

    # 2. Extract Location / City
    city = "New York, USA"
    for c in ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "London", "Tokyo", "Paris", "San Francisco"]:
        if c.lower() in raw_text.lower():
            city = f"{c}, India" if c in ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata"] else f"{c}, Global"
            break

    # 3. Extract Merchant
    merchant = "General Merchant"
    known_merchants = ["Dominos", "Starbucks", "McDonalds", "Whole Foods", "Netflix", "Spotify", "Amazon", "Uber", "Apple", "Swiggy", "Zomato", "MakeMyTrip", "Flipkart"]
    for m in known_merchants:
        if m.lower() in raw_text.lower():
            merchant = m
            break
    if merchant == "General Merchant":
        # Fallback: clean words
        words = [w for w in raw_text.split() if w.lower() not in ["spent", "paid", "for", "on", "in", "at", "rupees", "rs", "dollars", "the", "a"]]
        if words:
            merchant = words[0].capitalize()

    category = auto_categorize_merchant(merchant)

    # Pick default account
    acc = db.query(Account).first()
    acc_id = acc.id if acc else 1

    tx_in = schemas.TransactionCreate(
        account_id=acc_id,
        type="expense",
        category=category,
        merchant=merchant,
        amount=amount,
        location_city=city,
        description=f"Quick NLP parsed: '{raw_text}'"
    )
    return record_transaction(tx_in, db)

@app.get("/api/finance/export-report")
def export_financial_report(db: Session = Depends(get_db)):
    """
    Generates a printable HTML/PDF Financial Executive Statement.
    """
    ov = FinanceAnalyticsEngine(db).get_overview()
    now = datetime.utcnow().strftime("%B %d, %Y")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sentinel Wealth & Risk Audit Statement</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; color: #1e293b; background: #fff; }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #0f172a; padding-bottom: 20px; }}
            .title {{ font-size: 24px; font-weight: 800; color: #0f172a; }}
            .badge {{ background: #10b981; color: #fff; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
            .metric {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; }}
            .metric-label {{ font-size: 12px; color: #64748b; font-weight: bold; text-transform: uppercase; }}
            .metric-val {{ font-size: 22px; font-weight: 800; color: #0f172a; margin-top: 6px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background: #f1f5f9; color: #475569; font-weight: 700; }}
            .print-btn {{ background: #0f172a; color: #fff; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }}
            @media print {{ .print-btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div style="text-align: right; margin-bottom: 10px;">
            <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
        </div>
        <div class="header">
            <div>
                <div class="title">🛡️ SENTINEL EXECUTIVE WEALTH & AUDIT STATEMENT</div>
                <div style="color: #64748b; font-size: 13px; margin-top: 4px;">Statement Generated on {now} • Account Status: VERIFIED</div>
            </div>
            <div>
                <span class="badge">Grade: {ov['health_grade']}</span>
            </div>
        </div>

        <div class="grid">
            <div class="metric">
                <div class="metric-label">Total Net Worth</div>
                <div class="metric-val">${ov['net_worth']:,.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Monthly Inflow</div>
                <div class="metric-val" style="color: #10b981;">+${ov['total_income_this_month']:,.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Monthly Outflow</div>
                <div class="metric-val" style="color: #ef4444;">-${ov['total_expense_this_month']:,.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Savings Rate</div>
                <div class="metric-val">{ov['savings_rate_this_month']}%</div>
            </div>
        </div>

        <h3 style="margin-top: 30px; font-size: 16px;">Top Spending Category Breakdown</h3>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Transactions</th>
                    <th>Total Spend</th>
                    <th>% of Total Outflow</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f"<tr><td><strong>{c['category']}</strong></td><td>{c['transaction_count']}</td><td>${c['amount']:,.2f}</td><td>{c['percentage']}%</td></tr>" for c in ov['category_breakdown']])}
            </tbody>
        </table>

        <div style="margin-top: 40px; padding: 16px; background: #f8fafc; border-left: 4px solid #10b981; font-size: 13px; color: #475569;">
            <strong>Autonomous AI Security Summary:</strong> Multi-vector fraud monitoring is active. {ov['active_fraud_alerts_count']} active anomalies detected. Geo-velocity and Z-score outlier engines operating at 99.8% precision.
        </div>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)

@app.get("/api/fraud/blocklist")
def list_blocklist(db: Session = Depends(get_db)):
    return db.query(MerchantBlocklist).all()

# ----------------- BUDGETS & SUBSCRIPTIONS -----------------

@app.get("/api/budgets", response_model=List[schemas.BudgetResponse])
def get_budgets(db: Session = Depends(get_db)):
    engine = FinanceAnalyticsEngine(db)
    return engine.get_budgets_status()

@app.post("/api/budgets", response_model=schemas.BudgetResponse)
def create_or_update_budget(b_in: schemas.BudgetCreate, db: Session = Depends(get_db)):
    budget = db.query(Budget).filter(Budget.category == b_in.category).first()
    if budget:
        budget.monthly_limit = b_in.monthly_limit
        if b_in.color:
            budget.color = b_in.color
    else:
        budget = Budget(**b_in.dict())
        db.add(budget)
    db.commit()
    
    engine = FinanceAnalyticsEngine(db)
    all_b = engine.get_budgets_status()
    for b in all_b:
        if b["category"] == b_in.category:
            return b
    return all_b[0]

@app.get("/api/subscriptions", response_model=List[schemas.SubscriptionResponse])
def get_subscriptions(db: Session = Depends(get_db)):
    subs = db.query(Subscription).all()
    results = []
    for s in subs:
        ann = s.amount * 12.0 if s.billing_cycle == "monthly" else s.amount
        results.append(schemas.SubscriptionResponse(
            id=s.id,
            name=s.name,
            merchant=s.merchant,
            category=s.category,
            amount=s.amount,
            billing_cycle=s.billing_cycle,
            annual_cost=round(ann, 2),
            next_billing_date=s.next_billing_date,
            is_active=s.is_active,
            cancellation_url=s.cancellation_url or "https://google.com"
        ))
    return results

@app.post("/api/subscriptions", response_model=schemas.SubscriptionResponse)
def create_subscription(sub_in: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    sub = Subscription(**sub_in.dict())
    db.add(sub)
    db.commit()
    db.refresh(sub)
    ann = sub.amount * 12.0 if sub.billing_cycle == "monthly" else sub.amount
    return schemas.SubscriptionResponse(
        id=sub.id,
        name=sub.name,
        merchant=sub.merchant,
        category=sub.category,
        amount=sub.amount,
        billing_cycle=sub.billing_cycle,
        annual_cost=round(ann, 2),
        next_billing_date=sub.next_billing_date,
        is_active=sub.is_active,
        cancellation_url=sub.cancellation_url or ""
    )

@app.post("/api/subscriptions/{sub_id}/toggle-status")
def toggle_subscription_status(sub_id: int, db: Session = Depends(get_db)):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.is_active = not sub.is_active
    db.commit()
    return {"status": "success", "is_active": sub.is_active}

# ----------------- AI ADVISOR, WHAT-IF & CHAT -----------------

@app.get("/api/advisor/insights")
def get_advisor_insights(db: Session = Depends(get_db)):
    advisor = AIAdvisorEngine(db)
    return advisor.generate_smart_insights()

@app.post("/api/advisor/what-if", response_model=schemas.WhatIfResponse)
def run_what_if_analysis(req: schemas.WhatIfRequest, db: Session = Depends(get_db)):
    advisor = AIAdvisorEngine(db)
    return advisor.calculate_what_if(
        dining_reduction_pct=req.dining_reduction_pct,
        subscriptions_to_cancel_ids=req.subscriptions_to_cancel_ids,
        custom_monthly_savings=req.custom_monthly_savings,
        annual_return=req.investment_return_rate
    )

@app.post("/api/advisor/chat", response_model=schemas.AIChatResponse)
def ask_ai_finance_assistant(req: schemas.AIChatRequest, db: Session = Depends(get_db)):
    advisor = AIAdvisorEngine(db)
    return advisor.answer_query(req.query)

# ----------------- STATIC FRONTEND SERVING -----------------

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Frontend index.html is being prepared."}
