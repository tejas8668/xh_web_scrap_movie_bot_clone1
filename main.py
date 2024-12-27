import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
import urllib.parse

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the bot token from environment variables
TOKEN = os.getenv('BOT_TOKEN')

# Define the allowed domains
ALLOWED_DOMAINS = [
    "www.mirrobox.com", "www.nephobox.com", "freeterabox.com", "www.freeterabox.com",
    "1024tera.com", "4funbox.co", "www.4funbox.com", "mirrobox.com", "nephobox.com",
    "terabox.app", "terabox.com", "www.terabox.app", "terabox.fun", "www.terabox.com",
    "www.1024tera.com", "www.momerybox.com", "teraboxapp.com", "momerybox.com",
    "tibibox.com", "www.tibibox.com", "www.teraboxapp.com"
]

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    await update.message.reply_text('Welcome! How can I assist you today?')

# Define the link handler
async def handle_link(update: Update, context: CallbackContext) -> None:
    logger.info("Received message: %s", update.message.text)
    original_link = update.message.text
    domain = urllib.parse.urlparse(original_link).netloc
    if domain in ALLOWED_DOMAINS:
        parsed_link = urllib.parse.quote(original_link, safe='')
        modified_link = f"{parsed_link}&m=0"
        await update.message.reply_text(modified_link)
    else:
        await update.message.reply_text("This domain is not supported.")

def main() -> None:
    # Get the port from the environment variable or use default
    port = int(os.environ.get('PORT', 8080))  # Default to port 8080
    webhook_url = f"https://total-jessalyn-toxiccdeveloperr-36046375.koyeb.app/{TOKEN}"  # Replace with your server URL

    # Create the Application and pass it your bot's token
    app = ApplicationBuilder().token(TOKEN).build()

    # Register the /start command handler
    app.add_handler(CommandHandler("start", start))

    # Register the link handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    # Run the bot using a webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
