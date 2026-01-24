import wren
from pydantic import BaseModel

# Define a Pydantic model for invoice data
class InvoiceData(BaseModel):
    amount: str
    sender: str

# Use Wren's email trigger for emails with 'Invoice' in the subject
@wren.on_email(subject_contains="Invoice")
def extract_invoice_details(email):
    # Extract the amount and sender information from the email
    invoice_data: InvoiceData = wren.ai.extract(email.body)

    # For now, just print the extracted data (could be replaced with further processing)
    print(f"Invoice from {invoice_data.sender} for amount {invoice_data.amount}")
