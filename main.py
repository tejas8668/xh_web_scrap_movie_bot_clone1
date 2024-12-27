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
            "👋 **ℍ𝕖𝕝𝕝𝕠 𝔻𝕖𝕒𝕣!**\n\n"
            "SEND ME ANY TERABOX LINK, I WILL SEND YOU DIRECT STREAM LINK WITHOUT TERABOX LOGIN OR ANY ADS​\n\n"
            "**𝐈𝐦𝐩𝐨𝐫𝐭𝐚𝐧𝐭​​**\n\n"
            "𝗨𝘀𝗲 𝗖𝗵𝗿𝗼𝗺𝗲 𝗙𝗼𝗿 𝗔𝗰𝗰𝗲𝘀𝘀 𝗠𝘆 𝗔𝗹𝗹 𝗳𝗲𝗮𝘁𝘂𝗿𝗲𝘀"
        ),
        parse_mode='Markdown'
    )

# Define the link handler
async def handle_link(update: Update, context: CallbackContext) -> None:
    logger.info("Received message: %s", update.message.text)
    original_link = update.message.text
    parsed_link = urllib.parse.quote(original_link, safe='')
    modified_link = f"https://streamterabox.blogspot.com/?q={parsed_link}&m=0"

    # Create a button with the modified link
    button = [
        [InlineKeyboardButton("Stream Link", url=modified_link)]
    ]
    reply_markup = InlineKeyboardMarkup(button)

    # Send the message with the link, copyable link, and button
    await update.message.reply_text(
        f"👇👇 𝐓𝐚𝐩 𝐀𝐧𝐝 𝐂𝐨𝐩𝐲 𝐓𝐡𝐢𝐬 𝐔𝐫𝐥 𝐀𝐧𝐝 𝐏𝐚𝐬𝐭𝐞 𝐈𝐧 𝐂𝐡𝐫𝐨𝐦𝐞 𝐅𝐨𝐫 𝐔𝐬𝐞 𝐌𝐲 𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 👇👇\n\n♥ Your Stream Link ♥\n\n`{modified_link}`\n\n"
        "𝐔𝐬𝐞 𝐆𝐨𝐨𝐠𝐥𝐞 𝐂𝐡𝐫𝐨𝐦𝐞 𝐅𝐨𝐫 𝐏𝐥𝐚𝐲 𝐕𝐢𝐝𝐞𝐨 𝐈𝐧 𝐅𝐮𝐥𝐥 𝐒𝐜𝐫𝐞𝐞𝐧",
        reply_markup=reply_markup,
        parse_mode='Markdown'
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
