import wren

# Initialize Discord integration with our test channel
discord = wren.integrations.discord.init(default_channel_id="1276278355590643714")

@wren.on_schedule("*/2 * * * *")  # Every 2 minutes for testing
def send_weather_update():
    """Send a weather update to Discord."""
    forecast = wren.ai("Give a brief, fun weather forecast for Dublin, Ireland. One sentence.")
    discord.post(f"🌤️ Weather Update: {forecast}")
