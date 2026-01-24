import wren

# Initialize Gmail integration at the module level
gmail = wren.integrations.gmail.init()

# Define a function to handle incoming emails
@wren.on_email()
def notify_on_email(email):
    # Send a notification
    gmail.send("New Email Notification", "You have received a new email!")
