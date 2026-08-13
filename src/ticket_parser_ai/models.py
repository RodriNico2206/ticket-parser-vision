from typing import List, Optional
from pydantic import BaseModel, Field


class TicketItem(BaseModel):
    product_name: str = Field(description="Name or description of the product")
    quantity: float = Field(description="Quantity purchased")
    unit_price: float = Field(description="Price per unit")
    total_price: float = Field(description="Total price for this item")


class TicketData(BaseModel):
    store_name: Optional[str] = Field(default=None, description="Name of the store or business")
    date: Optional[str] = Field(default=None, description="Date of purchase if available")
    items: List[TicketItem] = Field(default_factory=list, description="List of items in the ticket")
    total_amount: Optional[float] = Field(default=None, description="Total ticket amount")