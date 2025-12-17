from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

class Price(BaseModel):
    market: str
    timestamp: datetime
    price: Decimal

class Spread(BaseModel):
    market_pair: str
    timestamp: datetime
    spread: Decimal
    net_opportunity: Decimal
    low_market: str
    high_market: str
    low_price: Decimal
    high_price: Decimal

class Alert(BaseModel):
    market_pair: str
    spread: Decimal
    net_opportunity: Decimal
    priority: str
    message: str | None = None
    acknowledged: bool = False
