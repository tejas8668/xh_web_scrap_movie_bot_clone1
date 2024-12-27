import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    await update.message.reply_photo(
        photo='https://ik.imagekit.io/dvnhxw9vq/unnamed.png?updatedAt=1735280750258',  # Replace with your image URL
        caption=(
            "👋 **Welcome!**\n\n"
            "We're thrilled to have you here! 😊\n\n"
            "**How can I assist you today?**\n\n"
            "Feel free to ask me anything or send me a link, and I'll be happy to help!"
        ),
        parse_mode='MarkdownV2'
    )

# Define the link handler
async def handle_link(update: Update, context: CallbackContext) -> None:
    logger.info("Received message: %s", update.message.text)
    original_link = update.message.text
    parsed_link = urllib.parse.quote(original_link, safe='')
    modified_link = f"https://streamterabox.blogspot.com/?q={parsed_link}&m=0"

    # Create a button with the modified link
    button = [
        [InlineKeyboardButton("Open Link", url=modified_link)]
    ]
    reply_markup = InlineKeyboardMarkup(button)

    # Send the message with the link, copyable link, and button
    await update.message.reply_text(
        f"Here is your link:\n{modified_link}\n\n"
        "For the best experience, please open this link in Google Chrome.",
        reply_markup=reply_markup
    )

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
