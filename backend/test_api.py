import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_finance_overview():
    response = client.get("/api/finance/overview")
    assert response.status_code == 200
    data = response.json()
    assert "net_worth" in data
    assert "total_income_this_month" in data
    assert "financial_health_score" in data
    assert "category_breakdown" in data
    assert "cashflow_history" in data
    assert len(data["category_breakdown"]) > 0

def test_forecast():
    response = client.get("/api/finance/forecast")
    assert response.status_code == 200
    data = response.json()
    assert "daily_burn_rate" in data
    assert "projected_total_month_expense" in data
    assert "forecast_points" in data

def test_accounts():
    response = client.get("/api/accounts")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) >= 4

def test_normal_transaction_creation():
    response = client.post("/api/transactions", json={
        "account_id": 1,
        "type": "expense",
        "category": "Groceries",
        "merchant": "Whole Foods Market",
        "amount": 65.50,
        "description": "Weekly grocery run",
        "location_city": "New York, USA",
        "location_lat": 40.7128,
        "location_lng": -74.0060
    })
    assert response.status_code == 200
    tx = response.json()
    assert tx["risk_level"] == "SAFE"
    assert tx["risk_score"] < 30.0
    assert tx["is_flagged"] is False

def test_fraud_attack_simulation_geo_hop():
    response = client.post("/api/simulator/trigger-attack?attack_type=geo_hop")
    assert response.status_code == 200
    tx = response.json()
    assert tx["risk_level"] in ["HIGH_RISK", "SUSPICIOUS"]
    assert tx["risk_score"] >= 60.0
    assert tx["is_flagged"] is True
    assert len(tx["risk_reasons"]) > 0

def test_fraud_alerts_and_resolution():
    # Get active alerts
    alerts_res = client.get("/api/fraud/alerts?status_filter=active")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) > 0

    target_alert_id = alerts[0]["id"]
    resolve_res = client.post(f"/api/fraud/alerts/{target_alert_id}/resolve", json={
        "action": "confirm_fraud",
        "notes": "Test confirmed fraudulent charge"
    })
    assert resolve_res.status_code == 200
    assert resolve_res.json()["action"] == "confirmed_fraud"

def test_budgets_and_subscriptions():
    b_res = client.get("/api/budgets")
    assert b_res.status_code == 200
    assert len(b_res.json()) > 0

    s_res = client.get("/api/subscriptions")
    assert s_res.status_code == 200
    assert len(s_res.json()) > 0

def test_what_if_calculator():
    res = client.post("/api/advisor/what-if", json={
        "dining_reduction_pct": 25.0,
        "subscriptions_to_cancel_ids": [1],
        "custom_monthly_savings": 100.0,
        "investment_return_rate": 0.07
    })
    assert res.status_code == 200
    data = res.json()
    assert data["monthly_savings"] > 0
    assert data["five_year_savings_compounded"] > data["annual_savings"] * 5

def test_ai_advisor_chat():
    res = client.post("/api/advisor/chat", json={
        "query": "Where did I spend the most money this month?"
    })
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert len(data["answer"]) > 10

if __name__ == "__main__":
    test_health()
    test_finance_overview()
    test_forecast()
    test_accounts()
    test_normal_transaction_creation()
    test_fraud_attack_simulation_geo_hop()
    test_fraud_alerts_and_resolution()
    test_budgets_and_subscriptions()
    test_what_if_calculator()
    test_ai_advisor_chat()
    print("[SUCCESS] All 10 API & Fraud Engine Unit Tests Passed Flawlessly!")
