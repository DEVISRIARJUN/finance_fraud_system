from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Account Schemas ---
class AccountBase(BaseModel):
    name: str
    type: str  # checking, savings, credit_card, investment
    balance: float
    currency: str = "USD"
    account_number_mask: str = "**** 1234"

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    is_frozen: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Transaction Schemas ---
class TransactionCreate(BaseModel):
    account_id: int
    type: str = "expense"  # income, expense
    category: Optional[str] = None  # if empty, auto-categorizer determines it
    merchant: str
    amount: float
    description: Optional[str] = ""
    timestamp: Optional[datetime] = None
    location_city: Optional[str] = "New York, USA"
    location_lat: Optional[float] = 40.7128
    location_lng: Optional[float] = -74.0060
    is_recurring: bool = False

class RiskExplanation(BaseModel):
    factor: str
    description: str
    severity: str  # low, medium, high, critical
    score_impact: float

class TransactionResponse(BaseModel):
    id: int
    account_id: int
    account_name: Optional[str] = ""
    type: str
    category: str
    merchant: str
    amount: float
    description: str
    timestamp: datetime
    location_city: str
    location_lat: float
    location_lng: float
    risk_score: float
    risk_level: str
    risk_reasons: List[RiskExplanation] = []
    is_flagged: bool
    status: str
    is_recurring: bool

    class Config:
        from_attributes = True

# --- Budget Schemas ---
class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float
    color: Optional[str] = "#10b981"
    icon: Optional[str] = "tag"

class BudgetResponse(BaseModel):
    id: int
    category: str
    monthly_limit: float
    current_spent: float = 0.0
    remaining: float = 0.0
    percentage: float = 0.0
    status: str = "healthy"  # healthy, warning, exceeded
    color: str
    icon: str

# --- Subscription Schemas ---
class SubscriptionCreate(BaseModel):
    name: str
    merchant: str
    category: str = "Subscriptions"
    amount: float
    billing_cycle: str = "monthly"
    next_billing_date: str
    cancellation_url: Optional[str] = ""

class SubscriptionResponse(BaseModel):
    id: int
    name: str
    merchant: str
    category: str
    amount: float
    billing_cycle: str
    annual_cost: float
    next_billing_date: str
    is_active: bool
    cancellation_url: str

    class Config:
        from_attributes = True

# --- Fraud Alert & Dispute Schemas ---
class FraudAlertResponse(BaseModel):
    id: int
    transaction_id: int
    merchant: str
    amount: float
    location_city: str
    timestamp: datetime
    risk_score: float
    risk_factors: List[RiskExplanation] = []
    status: str
    created_at: datetime
    notes: str

class DisputeActionRequest(BaseModel):
    action: str  # "confirm_fraud", "mark_valid", "freeze_account", "unfreeze_account"
    notes: Optional[str] = ""

# --- Finance Overview & Analytics Schemas ---
class CategorySpending(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int
    color: str

class MonthlyCashflowPoint(BaseModel):
    month: str  # "Jan 2026", "Feb 2026"
    income: float
    expenses: float
    net_savings: float
    savings_rate: float

class FinanceOverviewResponse(BaseModel):
    net_worth: float
    total_income_this_month: float
    total_expense_this_month: float
    net_savings_this_month: float
    savings_rate_this_month: float
    financial_health_score: int  # 0 to 100
    health_grade: str  # "Excellent", "Good", "Fair", "Needs Attention"
    active_fraud_alerts_count: int
    total_subscriptions_monthly: float
    total_subscriptions_annual: float
    category_breakdown: List[CategorySpending]
    cashflow_history: List[MonthlyCashflowPoint]
    predicted_monthly_expense: float

# --- Forecast & What-If Schemas ---
class FutureExpenseForecast(BaseModel):
    current_spent: float
    days_elapsed: int
    days_remaining: int
    daily_burn_rate: float
    projected_total_month_expense: float
    budget_comparison: float  # + or - vs total monthly budget
    status: str  # "on_track", "warning", "over_budget"
    forecast_points: List[Dict[str, Any]]  # day-by-day trajectory

class WhatIfRequest(BaseModel):
    dining_reduction_pct: float = 0.0
    subscriptions_to_cancel_ids: List[int] = []
    custom_monthly_savings: float = 0.0
    investment_return_rate: float = 0.07  # 7% standard market return

class WhatIfResponse(BaseModel):
    monthly_savings: float
    annual_savings: float
    five_year_savings_compounded: float
    ten_year_savings_compounded: float
    new_projected_savings_rate: float
    breakdown_details: List[str]

# --- AI Chat / Query Schemas ---
class AIChatRequest(BaseModel):
    query: str

class AIChatResponse(BaseModel):
    answer: str
    suggested_actions: List[Dict[str, str]] = []
    related_metrics: Optional[Dict[str, Any]] = None
