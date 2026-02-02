import wren

# Initialize integration at module level
# Assume wren.integrations.discord.init() is available and could be:
# wren.integrations.discord.init(default_channel="#weather")
discord = wren.integrations.discord.init(default_channel="#weather")

# Schedule trigger for 9 AM daily
@wren.on_schedule("0 9 * * *")
def daily_weather_notification():
    weather_forecast: str = wren.ai("What is the weather forecast for today?")
    discord.post(weather_forecast)
