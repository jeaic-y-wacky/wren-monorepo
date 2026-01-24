import wren
from pydantic import BaseModel

# Slack integration initialized at module level
slack = wren.integrations.slack.init(default_channel="#daily-summary")

gmail = wren.integrations.gmail.init()

class EmailSummary(BaseModel):
    subject: str
    sender: str
    summary: str

# Function to summarize and post emails
@wren.on_schedule("0 18 * * *")  # Daily at 6 PM
def summarize_daily_emails():
    all_emails = gmail.fetch_emails(received_today=True)
    summaries = []
    for email in all_emails:
        summary: str = wren.ai.summarize(email.body, max_length=50)
        summaries.append(EmailSummary(subject=email.subject, sender=email.from_addr, summary=summary))
    # Format and send the summary to Slack
    summary_text = "\n".join([f"From: {email.sender}\nSubject: {email.subject}\nSummary: {email.summary}\n" for email in summaries])
    slack.post(summary_text)