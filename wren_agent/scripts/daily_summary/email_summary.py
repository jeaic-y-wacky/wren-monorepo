import wren

# Initialize Slack integration at module level
slack = wren.integrations.slack.init(default_channel="#daily-summaries")

def summarize_emails():
    """Summarize all emails received today and post to Slack"""
    # fetch all today's emails
    emails = wren.integrations.gmail.get_emails(from_date="today")
    summaries = []
    for email in emails:
        summary: str = wren.ai.summarize(email.body, max_length=200)
        summaries.append(f"From: {email.from_addr}\nSubject: {email.subject}\nSummary: {summary}")
    full_summary = "\n\n".join(summaries)
    slack.post(f"Daily Email Summary:\n{full_summary}")

# Schedule the task to run every day at 6 PM
@wren.on_schedule("0 18 * * *")
def daily_email_summary_task():
    summarize_emails()
