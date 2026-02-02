import wren
from pydantic import BaseModel

# Initialize integrations
email_client = wren.integrations.gmail.init()

# Define Pydantic model for structured extraction
class InvoiceData(BaseModel):
    amount: str
    sender: str

@wren.on_email(subject_contains="Invoice")
def handle_invoice_email(email):
    # Extract invoice details
    invoice_data: InvoiceData = wren.ai.extract(email.body)

    # Log the extracted data
    print(f"Invoice amount: {invoice_data.amount}")
    print(f"Sender: {invoice_data.sender}")
