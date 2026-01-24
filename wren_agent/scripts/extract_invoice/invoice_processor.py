import wren
from pydantic import BaseModel

# Define a Pydantic model for structured data extraction
class Invoice(BaseModel):
    amount: str
    sender: str

# Initialize the Gmail integration at module level
gmail = wren.integrations.gmail.init()

# Trigger function for emails with subject containing 'Invoice'
@wren.on_email(subject="Invoice")
def process_invoice(email):
    # Extract the amount and sender from the email
    invoice: Invoice = wren.ai.extract(email.body, Invoice)
    
    # Print or further process the extracted information
    print(f"Invoice from {invoice.sender} for amount {invoice.amount}")
    # More processing logic can be added here
