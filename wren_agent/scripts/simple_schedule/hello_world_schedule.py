import wren


# Schedule a task to print 'Hello, World!' at 9 AM daily
@wren.on_schedule("0 9 * * *")
def print_hello_world():
    print("Hello, World!")
