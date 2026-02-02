import wren

# Initialize integrations at module level
# Assuming Discord integration exists and initialized correctly here
discord = wren.integrations.discord.init(channel_id='your_channel_id')

@wren.on_schedule("0 9 * * *")  # Daily at 9 AM
def send_weather_forecast():
    weather_forecast: str = wren.ai("What is the weather forecast for today?")
    discord.post(f"Today's weather forecast: {weather_forecast}")