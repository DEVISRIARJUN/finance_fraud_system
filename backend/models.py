import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # checking, savings, credit_card, investment
    balance = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    account_number_mask = Column(String(20), default="**** 1234")
    is_frozen = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    type = Column(String(20), nullable=False)  # income, expense
    category = Column(String(50), nullable=False)  # Groceries, Dining, Utilities, Subscriptions, Tech, Travel, Salary, Investment, etc.
    merchant = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(255), default="")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Geographic metadata for fraud analysis
    location_city = Column(String(100), default="New York, USA")
    location_lat = Column(Float, default=40.7128)
    location_lng = Column(Float, default=-74.0060)

    # Fraud & Anomaly Metadata
    risk_score = Column(Float, default=0.0)  # 0 to 100
    risk_level = Column(String(20), default="SAFE")  # SAFE, SUSPICIOUS, HIGH_RISK
    risk_reasons = Column(Text, default="[]")  # JSON encoded list of explanations
    is_flagged = Column(Boolean, default=False)
    status = Column(String(30), default="cleared")  # cleared, pending, disputed, blocked, confirmed_fraud
    
    # Recurring metadata
    is_recurring = Column(Boolean, default=False)

    account = relationship("Account", back_populates="transactions")
    fraud_alert = relationship("FraudAlert", back_populates="transaction", uselist=False, cascade="all, delete-orphan")

    def get_risk_reasons_list(self):
        try:
            return json.loads(self.risk_reasons) if self.risk_reasons else []
        except Exception:
            return []

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, unique=True)
    monthly_limit = Column(Float, nullable=False)
    color = Column(String(20), default="#10b981")
    icon = Column(String(50), default="tag")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    merchant = Column(String(100), nullable=False)
    category = Column(String(50), default="Subscriptions")
    amount = Column(Float, nullable=False)
    billing_cycle = Column(String(20), default="monthly")  # monthly, yearly
    next_billing_date = Column(String(30), nullable=False)
    is_active = Column(Boolean, default=True)
    cancellation_url = Column(String(255), default="")

class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_factors = Column(Text, default="[]")
    status = Column(String(30), default="active")  # active, resolved_valid, resolved_fraud
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(255), default="")

    transaction = relationship("Transaction", back_populates="fraud_alert")

class MerchantBlocklist(Base):
    __tablename__ = "merchant_blocklist"

    id = Column(Integer, primary_key=True, index=True)
    merchant_name = Column(String(100), unique=True, nullable=False)
    reason = Column(String(255), default="Flagged as fraudulent by user")
    created_at = Column(DateTime, default=datetime.utcnow)
