from pydantic import BaseModel, Field
from typing import Optional, List, Generic, TypeVar

T = TypeVar('T')

class BoundingBox(BaseModel):
    """Represents a bounding box with coordinates."""
    x1: int = Field(description="The top-left x-coordinate.")
    y1: int = Field(description="The top-left y-coordinate.")
    x2: int = Field(description="The bottom-right x-coordinate.")
    y2: int = Field(description="The bottom-right y-coordinate.")

class WithValue(BaseModel, Generic[T]):
    """A value with an associated bounding box."""
    value: T
    bbox: Optional[BoundingBox] = None

class AreasOfInterest(BaseModel):
    """Defines the key areas of interest to be located in the invoice."""
    header_area: Optional[BoundingBox] = Field(description="The area containing vendor name, invoice number, and dates.")
    line_items_area: Optional[BoundingBox] = Field(description="The area containing the table of line items.")
    summary_area: Optional[BoundingBox] = Field(description="The area containing the subtotal, tax, and total amount.")

class ExtractedHeader(BaseModel):
    """Represents the extracted header information."""
    invoice_number: Optional[WithValue[str]] = None
    vendor_name: Optional[WithValue[str]] = None
    client_name: Optional[WithValue[str]] = None
    invoice_date: Optional[WithValue[str]] = None
    due_date: Optional[WithValue[str]] = None

class LineItem(BaseModel):
    """Represents a single line item in the invoice."""
    description: Optional[WithValue[str]] = None
    quantity: Optional[WithValue[float]] = None
    unit_price: Optional[WithValue[float]] = None
    total_price: Optional[WithValue[float]] = None
    bbox: Optional[BoundingBox] = None

class ExtractedLineItems(BaseModel):
    """Represents a list of extracted line items."""
    line_items: List[LineItem] = Field(description="A list of all line items extracted from the invoice.")

class ExtractedSummary(BaseModel):
    """Represents the extracted summary information."""
    total_amount: Optional[WithValue[float]] = None
    tax_amount: Optional[WithValue[float]] = None

class CompleteInvoice(BaseModel):
    """The final structured data for an invoice, including all extracted fields."""
    invoice_number: Optional[WithValue[str]] = Field(None, title="Invoice Number")
    vendor_name: Optional[WithValue[str]] = Field(None, title="Vendor Name")
    client_name: Optional[WithValue[str]] = Field(None, title="Client Name")
    invoice_date: Optional[WithValue[str]] = Field(None, title="Invoice Date")
    due_date: Optional[WithValue[str]] = Field(None, title="Due Date")
    total_amount: Optional[WithValue[float]] = Field(None, title="Total Amount")
    tax_amount: Optional[WithValue[float]] = Field(None, title="Tax Amount")
    line_items: List[LineItem] = Field(default_factory=list, title="Line Items")