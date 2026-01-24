import wren

# Initialize Slack integration at module level
slack = wren.integrations.slack.init(default_channel="#urgent-notifications")

@wren.on_email()
def classify_and_notify(email):
    # Classify the email as either urgent or normal
    category = wren.ai.classify(email.body, ["urgent", "normal"])
    
    # If the email is classified as urgent, post to Slack
    if category == "urgent":
        slack.post(f"Urgent email received: {email.subject}")