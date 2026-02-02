import wren

# Initialize Discord integration at module level
# Replace 'CHANNEL_ID' with your actual Discord channel ID

discord = wren.integrations.discord.init(channel_id='CHANNEL_ID')

@wren.on_schedule("0 9 * * *")  # Schedule for daily at 9 AM
def daily_weather_notification():
    # Assuming there's a fictional AI model to get weather called 'get_weather_forecast'
    weather_forecast: str = wren.ai('Get today\'s weather forecast', '')
    
    # Send weather forecast message to Discord
    discord.post(f"Today's weather forecast: {weather_forecast}")