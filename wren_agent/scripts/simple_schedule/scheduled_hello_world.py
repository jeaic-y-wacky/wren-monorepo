import wren


# Schedule to print hello world at 9 AM every day
@wren.on_schedule("0 9 * * *")
def scheduled_hello_world():
    print("Hello, world!")
