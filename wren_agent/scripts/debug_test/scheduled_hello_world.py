import wren


@wren.on_schedule("0 9 * * *")  # Daily at 9 AM
def print_hello_world():
    print("Hello, World!")
