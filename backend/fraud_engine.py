import math
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from models import Transaction, Account, MerchantBlocklist

# Category mapping dictionary for smart auto-categorization
MERCHANT_CATEGORY_RULES = {
    "groceries": ["whole foods", "trader joe", "safeway", "kroger", "walmart", "target", "costco", "aldi", "sprouts", "supermarket"],
    "dining": ["starbucks", "mcdonald", "chipotle", "uber eats", "doordash", "grubhub", "restaurant", "bistro", "cafe", "pizza", "sushi", "shake shack", "sweetgreen"],
    "subscriptions": ["netflix", "spotify", "apple music", "amazon prime", "hulu", "disney", "youtube", "chatgpt", "openai", "github", "dropbox", "icloud", "nyt", "audible"],
    "utilities": ["conedison", "pge", "verizon", "at&t", "t-mobile", "water dept", "electric", "internet", "comcast", "spectrum"],
    "travel": ["uber", "lyft", "delta", "american airlines", "united airlines", "airbnb", "hotel", "expedia", "booking.com", "hertz", "amtrak"],
    "tech": ["best buy", "apple store", "micro center", "newegg", "b&h photo", "dell", "lenovo"],
    "health": ["cvs", "walgreens", "pharmacy", "gym", "equinox", "planet fitness", "clinic", "hospital", "dentist"],
    "entertainment": ["amc theatres", "ticketmaster", "steam", "playstation", "nintendo", "cinema", "bowling", "concert"],
    "crypto_wire": ["binance", "coinbase", "kraken", "wire transfer", "crypto.com", "western union", "remitly", "offshore"],
    "luxury": ["gucci", "louis vuitton", "rolex", "tiffany", "cartier", "prada"],
    "salary": ["payroll", "employer", "direct deposit", "stripe payout", "upwork", "freelance payment"]
}

def auto_categorize_merchant(merchant_name: str, transaction_type: str = "expense") -> str:
    """Smartly categorizes merchant names using heuristic pattern matching."""
    name_lower = merchant_name.lower().strip()
    if transaction_type == "income":
        return "Salary & Income"

    for category_key, keywords in MERCHANT_CATEGORY_RULES.items():
        for kw in keywords:
            if kw in name_lower:
                if category_key == "crypto_wire":
                    return "Crypto & Transfers"
                elif category_key == "tech":
                    return "Tech & Electronics"
                elif category_key == "health":
                    return "Health & Fitness"
                elif category_key == "luxury":
                    return "Luxury & Jewelry"
                return category_key.capitalize()
                
    return "General Merchandise"

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in km."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class FraudDetectionEngine:
    """
    Multi-vector AI & Statistical Anomaly Detection Engine for Financial Transactions.
    Evaluates:
    1. Impossible Geographic Velocity (Haversine distance vs elapsed time)
    2. Statistical Category Amount Outliers (Z-score & standard deviations)
    3. Card Testing & Micro-Burst Patterns (Rapid tiny charges preceding high amounts)
    4. High-Risk Merchant & Blocklist Interception
    5. Off-Hours High-Value Purchases (Unusual circadian behavior)
    """

    def __init__(self, db: Session):
        self.db = db

    def analyze_transaction(
        self,
        account_id: int,
        amount: float,
        merchant: str,
        category: str,
        timestamp: datetime,
        lat: float,
        lng: float,
        city: str,
        trans_type: str = "expense"
    ) -> Tuple[float, str, List[Dict], bool]:
        """
        Runs all fraud analysis modules and returns:
        (risk_score, risk_level, risk_explanations, is_flagged)
        """
        # Income is generally non-fraudulent from user's perspective unless negative
        if trans_type == "income":
            return 0.0, "SAFE", [], False

        explanations: List[Dict] = []
        raw_score = 0.0

        # Check 0: Blocklist Check
        blocklist_hit = self._check_blocklist(merchant)
        if blocklist_hit:
            raw_score += 85.0
            explanations.append({
                "factor": "Merchant Blocklist Match",
                "description": f"Merchant '{merchant}' is explicitly listed on your security blocklist ({blocklist_hit}).",
                "severity": "critical",
                "score_impact": 85.0
            })

        # Fetch recent user transactions for baseline
        recent_txs = (
            self.db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(Transaction.timestamp.desc())
            .limit(50)
            .all()
        )

        # Check 1: Impossible Velocity / Geo Anomaly
        geo_impact, geo_exp = self._check_geo_velocity(recent_txs, timestamp, lat, lng, city)
        if geo_impact > 0:
            raw_score += geo_impact
            explanations.append(geo_exp)

        # Check 2: Statistical Amount Spike / Z-Score Anomaly
        spike_impact, spike_exp = self._check_amount_spike(account_id, category, amount)
        if spike_impact > 0:
            raw_score += spike_impact
            explanations.append(spike_exp)

        # Check 3: Card Testing / Rapid Micro-Charge Burst
        burst_impact, burst_exp = self._check_micro_charge_burst(recent_txs, timestamp, amount)
        if burst_impact > 0:
            raw_score += burst_impact
            explanations.append(burst_exp)

        # Check 4: High-Risk Category & Dark Patterns
        category_impact, cat_exp = self._check_high_risk_category(category, merchant, amount)
        if category_impact > 0:
            raw_score += category_impact
            explanations.append(cat_exp)

        # Check 5: Off-Hours High-Value Anomaly (e.g. 2:00 AM - 4:45 AM)
        time_impact, time_exp = self._check_off_hours(timestamp, amount)
        if time_impact > 0:
            raw_score += time_impact
            explanations.append(time_exp)

        # Cap total score between 0 and 100 with bounded scaling
        final_score = min(100.0, round(raw_score, 1))

        if final_score >= 70.0:
            risk_level = "HIGH_RISK"
            is_flagged = True
        elif final_score >= 30.0:
            risk_level = "SUSPICIOUS"
            is_flagged = True
        else:
            risk_level = "SAFE"
            is_flagged = False

        return final_score, risk_level, explanations, is_flagged

    def _check_blocklist(self, merchant: str) -> Optional[str]:
        m_lower = merchant.lower().strip()
        blocked = self.db.query(MerchantBlocklist).all()
        for b in blocked:
            if b.merchant_name.lower() in m_lower or m_lower in b.merchant_name.lower():
                return b.reason
        return None

    def _check_geo_velocity(
        self,
        recent_txs: List[Transaction],
        current_time: datetime,
        lat: float,
        lng: float,
        city: str
    ) -> Tuple[float, Optional[Dict]]:
        if not recent_txs:
            return 0.0, None

        # Compare with the most recent transaction
        last_tx = recent_txs[0]
        time_diff_hours = abs((current_time - last_tx.timestamp).total_seconds()) / 3600.0

        # Avoid zero division
        if time_diff_hours < 0.01:
            time_diff_hours = 0.01

        distance_km = haversine_distance_km(last_tx.location_lat, last_tx.location_lng, lat, lng)

        # If physically different cities/locations
        if distance_km > 300:
            required_speed_kmh = distance_km / time_diff_hours
            # Commercial flights cruise at ~850-900 km/h
            if required_speed_kmh > 800:
                score = 80.0 if required_speed_kmh > 1500 else 60.0
                return score, {
                    "factor": "Impossible Geographic Velocity",
                    "description": (
                        f"Transaction occurred in {city} {round(time_diff_hours*60, 1)} minutes after a "
                        f"transaction in {last_tx.location_city} ({round(distance_km, 1)} km away). "
                        f"Required travel speed of {int(required_speed_kmh)} km/h exceeds physical possibilities."
                    ),
                    "severity": "critical" if required_speed_kmh > 1500 else "high",
                    "score_impact": score
                }

        return 0.0, None

    def _check_amount_spike(self, account_id: int, category: str, amount: float) -> Tuple[float, Optional[Dict]]:
        category_txs = (
            self.db.query(Transaction.amount)
            .filter(
                Transaction.account_id == account_id,
                Transaction.category == category,
                Transaction.type == "expense"
            )
            .all()
        )
        amounts = [t[0] for t in category_txs if t[0] > 0]
        if len(amounts) < 3:
            # Check against global baseline if new category
            if amount > 1500.0:
                return 40.0, {
                    "factor": "High First-Time Ticket Amount",
                    "description": f"First time high-value purchase (${amount:,.2f}) with no prior baseline in '{category}'.",
                    "severity": "medium",
                    "score_impact": 40.0
                }
            return 0.0, None

        mean = sum(amounts) / len(amounts)
        variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
        std_dev = math.sqrt(variance) if variance > 0 else (mean * 0.2)

        if std_dev == 0:
            std_dev = 1.0

        z_score = (amount - mean) / std_dev
        ratio = amount / mean if mean > 0 else 1.0

        if z_score > 3.5 or ratio > 4.5:
            score = 65.0 if ratio > 6.0 else 45.0
            return score, {
                "factor": "Statistical Spending Outlier",
                "description": (
                    f"Charge of ${amount:,.2f} is {ratio:.1f}x higher than your average of ${mean:,.2f} "
                    f"for '{category}' (Z-Score: +{z_score:.2f} standard deviations)."
                ),
                "severity": "high",
                "score_impact": score
            }

        return 0.0, None

    def _check_micro_charge_burst(
        self,
        recent_txs: List[Transaction],
        current_time: datetime,
        current_amount: float
    ) -> Tuple[float, Optional[Dict]]:
        if not recent_txs:
            return 0.0, None

        # Check last 15 minutes for micro-transactions ($0.50 to $3.50)
        micro_charges = []
        for tx in recent_txs:
            time_delta = abs((current_time - tx.timestamp).total_seconds())
            if time_delta <= 900:  # 15 minutes
                if 0.20 <= tx.amount <= 4.00:
                    micro_charges.append(tx)

        if len(micro_charges) >= 2 and current_amount > 50.0:
            return 70.0, {
                "factor": "Card-Testing Attack Pattern",
                "description": (
                    f"Detected {len(micro_charges)} rapid micro-charges ($0.99 - $3.00) in the last 15 minutes "
                    f"immediately followed by this larger charge (${current_amount:,.2f}). Classic credential stuffing signature."
                ),
                "severity": "critical",
                "score_impact": 70.0
            }
        return 0.0, None

    def _check_high_risk_category(self, category: str, merchant: str, amount: float) -> Tuple[float, Optional[Dict]]:
        m_lower = merchant.lower()
        if category in ["Crypto & Transfers", "Luxury & Jewelry"] or "crypto" in m_lower or "casino" in m_lower or "wire" in m_lower:
            if amount > 800.0:
                score = 55.0
                return score, {
                    "factor": "High-Risk Merchant Sector",
                    "description": f"High-ticket purchase (${amount:,.2f}) in high-risk volatility category '{category}' at '{merchant}'.",
                    "severity": "high",
                    "score_impact": score
                }
        return 0.0, None

    def _check_off_hours(self, timestamp: datetime, amount: float) -> Tuple[float, Optional[Dict]]:
        hour = timestamp.hour
        # 1:00 AM to 4:59 AM
        if 1 <= hour <= 4 and amount > 400.0:
            return 30.0, {
                "factor": "Unusual Off-Hours Activity",
                "description": f"High-value transaction (${amount:,.2f}) processed at {timestamp.strftime('%I:%M %p')}, outside regular activity hours.",
                "severity": "medium",
                "score_impact": 30.0
            }
        return 0.0, None
