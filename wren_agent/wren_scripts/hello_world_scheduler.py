import wren


# Schedule the function to run daily at 9 AM
@wren.on_schedule("0 9 * * *")
def print_hello_world():
    print("Hello, World!")
