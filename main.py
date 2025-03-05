import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the bot token and channel ID from environment variables
TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# In-memory storage for user tracking
users = set()

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    user = update.effective_user

    # Add user to the set
    users.add(user.id)

    message = (
        f"New user started the bot:\n"
        f"Name: {user.full_name}\n"
        f"Username: @{user.username}\n"
        f"User ID: {user.id}"
    )
    await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
    await update.message.reply_photo(
        photo='https://ik.imagekit.io/dvnhxw9vq/unnamed.png?updatedAt=1735280750258',  # Replace with your image URL
        caption=(
            "👋 **ℍ𝕖𝕝𝕝𝕠 𝔻𝕖𝕒𝕣!**\n\n"
            "SEND ME ANY TERABOX LINK, I WILL SEND YOU DIRECT STREAM LINK WITHOUT TERABOX LOGIN OR ANY ADS​\n\n"
            "**𝐈𝐦𝐩𝐨𝐫𝐭𝐚𝐧𝐭​​**\n\n"
            "𝗨𝘀𝗲 𝗖𝗵𝗿𝗼𝗺𝗲 𝗙𝗼𝗿 𝗔𝗰𝗰𝗲𝘀𝘀 𝗠𝘆 𝗔𝗹𝗹 𝗳𝗲𝗮𝘁𝘂𝗿𝗲𝘀"
        ),
        parse_mode='Markdown'
    )

def redirection_domain_get(old_url):
    try:
        # Send a GET request to the old URL and allow redirects
        response = requests.get(old_url, allow_redirects=True)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Extract the final URL after redirection
            new_url = response.url
            return new_url
        else:
            return old_url
    except requests.RequestException as e:
        return old_url

async def filmyfly_movie_search(url, domain, update: Update):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all <a> tags with href containing '/page-download/'
        download_links = soup.find_all('a', href=lambda href: href and '/page-download/' in href)
        
        # Use a set to store unique links
        unique_links = set()
        buttons = []
        
        # Extract and print the href attributes
        for link in download_links:
            href = link.get('href')
            if href and href not in unique_links:
                unique_links.add(href)
                buttons.append([InlineKeyboardButton(f'Link: {domain}{href}', url=f'{domain}{href}')])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("Download Links:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"Failed to retrieve the webpage. Status code: {response.status_code}")

async def filmyfly_download_linkmake_view(url, update: Update):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all <a> tags with href containing 'https://linkmake.in/view'
        linkmake_links = soup.find_all('a', href=lambda href: href and 'https://linkmake.in/view' in href)
        
        # Use a set to store unique links
        unique_links = set()
        buttons = []
        
        # Extract and print the href attributes
        for link in linkmake_links:
            href = link.get('href')
            if href and href not in unique_links:
                unique_links.add(href)
                buttons.append([InlineKeyboardButton(f'Link: {href}', url=href)])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("Linkmake Links:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"Failed to retrieve the webpage. Status code: {response.status_code}")

async def filmyfly_scraping(update: Update, context: CallbackContext):
    # Fetch download links
    filmyflyurl = context.args[0] if context.args else ''
    if not filmyflyurl:
        await update.message.reply_text("Please provide a URL to fetch download links.")
        return

    filmyfly_domain = redirection_domain_get("https://filmyfly.esq")
    filmyfly_final = f"{filmyfly_domain}site-1.html?to-search={filmyflyurl}"
    await filmyfly_movie_search(filmyfly_final, filmyfly_domain, update)
    
    # Fetch linkmake links
    filmyfly_link = context.args[1] if len(context.args) > 1 else ''
    if filmyfly_link:
        await filmyfly_download_linkmake_view(filmyfly_link, update)

def main() -> None:
    # Get the port from the environment variable or use default
    port = int(os.environ.get('PORT', 8080))  # Default to port 8080
    webhook_url = f"https://painful-eustacia-chavan-013550df.koyeb.app/{TOKEN}"  # Replace with your server URL

    # Create the Application and pass it your bot's token
    app = ApplicationBuilder().token(TOKEN).build()

    # Register the /start command handler
    app.add_handler(CommandHandler("start", start))

    # Register the link handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filmyfly_scraping))

    # Run the bot using a webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
