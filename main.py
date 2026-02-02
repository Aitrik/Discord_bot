import discord
from discord.ext import commands, tasks
import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re
from io import BytesIO

load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
EXCEL_FILE_PATH = os.getenv('EXCEL_FILE_PATH')
CHECK_INTERVAL = int(os.getenv('EXCEL_CHECK_INTERVAL', 30))

# Store the channel ID dynamically (will be set when commands are used)
ANNOUNCEMENT_CHANNEL_ID = None

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Track announced events to avoid duplicates
announced_events = set()

def download_google_sheet(url):
    """Download Google Sheets as Excel file"""
    try:
        # Convert Google Sheets URL to export URL
        if 'docs.google.com/spreadsheets' in url:
            sheet_id = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
            if sheet_id:
                export_url = f'https://docs.google.com/spreadsheets/d/{sheet_id.group(1)}/export?format=xlsx'
                response = requests.get(export_url, timeout=30)
                response.raise_for_status()
                return BytesIO(response.content)
        return None
    except Exception as e:
        print(f"Error downloading sheet: {e}")
        return None

def parse_event_data(df):
    """Parse event data from the spreadsheet"""
    events = []
    
    # Get column names or use positional indexing
    print(f"DataFrame columns: {df.columns.tolist()}")
    print(f"DataFrame shape: {df.shape}")
    print(f"First few rows:\n{df.head()}")
    
    for idx, row in df.iterrows():
        try:
            # Skip if this looks like a header row
            if idx == 0:
                first_col = row.iloc[0] if len(row) > 0 else None
                if first_col == 'Date' or str(first_col).lower() == 'date':
                    print(f"Skipping header row at index {idx}")
                    continue
            
            # Try to get data by column name first, then by position
            if 'Date' in df.columns and 'content' in df.columns:
                date_value = row['Date']
                content = row['content']
            elif 'Date' in df.columns:
                date_value = row['Date']
                content = row.iloc[1] if len(row) > 1 else ''
            else:
                # Use first two columns
                date_value = row.iloc[0] if len(row) > 0 else None
                content = row.iloc[1] if len(row) > 1 else ''
            
            # Convert content to string
            content = str(content) if not pd.isna(content) else ''
            
            # Skip empty rows
            if pd.isna(date_value):
                print(f"Skipping row {idx}: date is NaN")
                continue
            
            if content == '' or content == 'nan':
                print(f"Skipping row {idx}: content is empty")
                continue
            
            # Skip header-like content
            if content.lower() == 'content':
                print(f"Skipping row {idx}: looks like header")
                continue
            
            print(f"Processing row {idx}: date_value type={type(date_value)}, date_value='{date_value}', content length={len(content)}")
            
            # Handle different date formats
            event_date = None
            
            # Case 1: Already a datetime object (from Google Sheets)
            if isinstance(date_value, datetime):
                event_date = date_value
                print(f"  ✓ Date is datetime object: {event_date}")
            
            # Case 2: pandas Timestamp
            elif isinstance(date_value, pd.Timestamp):
                event_date = date_value.to_pydatetime()
                print(f"  ✓ Date is pandas Timestamp: {event_date}")
            
            # Case 3: String format DD/MM/YY or other string dates
            else:
                date_str = str(date_value)
                
                # Try parsing DD/MM/YY format
                if '/' in date_str:
                    date_parts = date_str.split('/')
                    if len(date_parts) == 3:
                        day, month, year = date_parts
                        if len(year) == 2:
                            year = '20' + year
                        event_date = datetime(int(year), int(month), int(day))
                        print(f"  ✓ Parsed string date DD/MM/YY: {event_date}")
                
                # Try parsing YYYY-MM-DD format
                elif '-' in date_str and 'T' not in date_str:
                    try:
                        event_date = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
                        print(f"  ✓ Parsed string date YYYY-MM-DD: {event_date}")
                    except:
                        pass
            
            # If we successfully parsed a date, add the event
            if event_date:
                event_info = {
                    'date': event_date,
                    'content': content,
                    'unique_id': f"{event_date.strftime('%Y%m%d')}_{hash(content)}"
                }
                events.append(event_info)
                print(f"✅ Added event for {event_date.strftime('%Y-%m-%d')}")
            else:
                print(f"⚠️ Could not parse date from: {date_value} (type: {type(date_value)})")
                
        except Exception as e:
            print(f"❌ Error parsing row {idx}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n📊 Total events parsed: {len(events)}")
    return events

def format_event_message(event):
    """Format event announcement message"""
    content = event['content']
    date = event['date']
    
    # Extract key information
    lines = content.split('\n')
    title = lines[0] if lines else "Event Reminder"
    
    # Create embed message
    embed = discord.Embed(
        title="🎉 Event Reminder - Tomorrow!",
        description=f"**{title}**",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📅 Date",
        value=date.strftime("%A, %B %d, %Y"),
        inline=False
    )
    
    # Extract location if present
    location_match = re.search(r'Jakarta, Indonesia', content)
    if location_match:
        embed.add_field(
            name="📍 Location",
            value="Jakarta, Indonesia",
            inline=True
        )
    
    # Extract time if present
    time_match = re.search(r'(\d{1,2}:\d{2}-\d{1,2}:\d{2}\s*[AP]M)', content)
    if time_match:
        embed.add_field(
            name="⏰ Time",
            value=time_match.group(1),
            inline=True
        )
    
    # Add event details
    details = []
    for line in lines[1:]:
        if line.strip() and not line.startswith('-'):
            details.append(line.strip())
    
    if details:
        embed.add_field(
            name="ℹ️ Details",
            value='\n'.join(details[:5]),  # Limit to 5 lines
            inline=False
        )
    
    embed.set_footer(text="Don't miss this event!")
    
    return embed

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_events():
    """Check for events happening tomorrow and announce them"""
    if ANNOUNCEMENT_CHANNEL_ID is None:
        return
    
    channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not channel:
        print(f"Channel {ANNOUNCEMENT_CHANNEL_ID} not found")
        return
    
    try:
        # Download and read the spreadsheet
        excel_data = download_google_sheet(EXCEL_FILE_PATH)
        if not excel_data:
            print("Failed to download spreadsheet")
            return
        
        # Read Excel file - let pandas auto-detect headers
        df = pd.read_excel(excel_data, header=0)
        print(f"Excel loaded. Shape: {df.shape}, Columns: {df.columns.tolist()}")
        
        # Parse events
        events = parse_event_data(df)
        
        # Get tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        print(f"Checking for events on: {tomorrow}")
        
        # Check for events tomorrow
        for event in events:
            event_date = event['date'].date()
            print(f"Event date: {event_date}, Tomorrow: {tomorrow}, Match: {event_date == tomorrow}")
            
            if event_date == tomorrow:
                event_id = event['unique_id']
                
                # Only announce if not already announced
                if event_id not in announced_events:
                    embed = format_event_message(event)
                    await channel.send(embed=embed)
                    announced_events.add(event_id)
                    print(f"✅ Announced event for {event_date}")
                else:
                    print(f"⏭️ Event already announced: {event_date}")
        
    except Exception as e:
        print(f"Error checking events: {e}")
        import traceback
        traceback.print_exc()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Monitoring spreadsheet every {CHECK_INTERVAL} seconds')
    if ANNOUNCEMENT_CHANNEL_ID is not None:
        print(f'Announcements will be sent to channel ID: {ANNOUNCEMENT_CHANNEL_ID}')
    else:
        print('⚠️ No announcement channel set yet. Use !excel start in the desired channel.')

@bot.command(name='excel')
async def excel_command(ctx, action=None):
    """Manage Excel monitoring settings"""
    global ANNOUNCEMENT_CHANNEL_ID
    
    if action == 'start':
        # Automatically use the current channel
        ANNOUNCEMENT_CHANNEL_ID = ctx.channel.id
        
        await ctx.send(f'✅ Announcement channel set to {ctx.channel.mention}')
        
        # Start the task if not running
        if not check_events.is_running():
            check_events.start()
            await ctx.send('🟢 Event monitoring started!')
        else:
            await ctx.send('ℹ️ Event monitoring was already running, now using this channel.')
    
    elif action == 'stop':
        if check_events.is_running():
            check_events.stop()
            ANNOUNCEMENT_CHANNEL_ID = None
            await ctx.send('🔴 Event monitoring stopped!')
        else:
            await ctx.send('ℹ️ Event monitoring is not currently running.')
    
    elif action == 'status':
        channel_mention = f'<#{ANNOUNCEMENT_CHANNEL_ID}>' if ANNOUNCEMENT_CHANNEL_ID else 'Not set'
        status_msg = f"""
📊 **Excel Monitor Status**
Channel: {channel_mention}
Check Interval: {CHECK_INTERVAL} seconds
Task Running: {'Yes' if check_events.is_running() else 'No'}
Events Announced: {len(announced_events)}
        """
        await ctx.send(status_msg)
    
    elif action == 'check':
        if ANNOUNCEMENT_CHANNEL_ID is None:
            await ctx.send('❌ Please start monitoring first using `!excel start`')
            return
        await ctx.send('🔄 Manually checking for events...')
        await check_events()
        await ctx.send('✅ Check complete!')
    
    elif action == 'debug':
        # Debug command to see what's in the spreadsheet
        await ctx.send('🔍 Fetching spreadsheet data...')
        try:
            excel_data = download_google_sheet(EXCEL_FILE_PATH)
            if not excel_data:
                await ctx.send('❌ Failed to download spreadsheet')
                return
            
            df = pd.read_excel(excel_data, header=0)
            print(f"Debug - Excel loaded. Shape: {df.shape}, Columns: {df.columns.tolist()}")
            events = parse_event_data(df)
            
            tomorrow = (datetime.now() + timedelta(days=1)).date()
            
            if not events:
                await ctx.send('⚠️ No events found in spreadsheet!')
                return
            
            # Show all events
            debug_msg = f"**Found {len(events)} events:**\n\n"
            for event in events[:5]:  # Show first 5
                event_date = event['date'].date()
                is_tomorrow = "✅ TOMORROW!" if event_date == tomorrow else ""
                days_diff = (event_date - datetime.now().date()).days
                debug_msg += f"• {event_date} ({days_diff} days from now) {is_tomorrow}\n"
            
            if len(events) > 5:
                debug_msg += f"\n...and {len(events) - 5} more events"
            
            await ctx.send(debug_msg)
            
        except Exception as e:
            await ctx.send(f'❌ Error: {str(e)}')
    
    else:
        help_msg = """
📋 **Excel Monitor Commands**
`!excel start` - Start monitoring in this channel
`!excel stop` - Stop event monitoring
`!excel status` - Show current status
`!excel check` - Manually check for events now
`!excel debug` - Show all events in spreadsheet
        """
        await ctx.send(help_msg)

@bot.command(name='test')
async def test_notification(ctx):
    """Send a test notification"""
    embed = discord.Embed(
        title="🧪 Test Notification",
        description="This is a test event reminder",
        color=discord.Color.blue()
    )
    embed.add_field(name="Status", value="✅ Bot is working correctly!")
    embed.add_field(name="Channel", value=f"Using {ctx.channel.mention}")
    await ctx.send(embed=embed)

# Run the bot
if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in .env file!")
    else:
        bot.run(DISCORD_TOKEN)