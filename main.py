import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, JobQueue
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
search_results = {}

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

def delete_message(context: CallbackContext) -> None:
    job = context.job
    try:
        context.bot.delete_message(chat_id=job.data['chat_id'], message_id=job.data['message_id'])
    except Exception as e:
        logger.error(f"Failed to delete message: {e}")

async def filmyfly_movie_search(url, domain, update: Update, context: CallbackContext, searching_message_id: int):
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
        for i, link in enumerate(download_links):
            href = link.get('href')
            if href and href not in unique_links:
                unique_links.add(href)
                callback_data = f'link_{i}'
                context.user_data[callback_data] = f'{domain}{href}'
                # Extract the last part of the URL for the button title
                button_title = href.split('/')[-1]
                buttons.append([InlineKeyboardButton(button_title, callback_data=callback_data)])
        
        # Store the search results in the context
        context.user_data['search_results'] = buttons
        context.user_data['current_page'] = 0
        
        # Delete the "Searching..." message
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=searching_message_id)
        
        # Send the first page of results
        await send_search_results(update, context)
    else:
        await update.message.reply_text(f"Failed to retrieve the webpage. Status code: {response.status_code}")

async def send_search_results(update: Update, context: CallbackContext):
    buttons = context.user_data['search_results']
    current_page = context.user_data['current_page']
    
    # Paginate the results
    start = current_page * 8
    end = start + 8
    page_buttons = buttons[start:end]
    
    # Add a "Next" button if there are more results
    if end < len(buttons):
        page_buttons.append([InlineKeyboardButton("Next", callback_data="next_page")])
    
    reply_markup = InlineKeyboardMarkup(page_buttons)
    if update.message:
        sent_message = await update.message.reply_text("Download Links:", reply_markup=reply_markup)
    elif update.callback_query:
        sent_message = await update.callback_query.message.reply_text("Download Links:", reply_markup=reply_markup)
    
    # Schedule the deletion of the message after 10 minutes (600 seconds)
    context.job_queue.run_once(delete_message, 600, data={'chat_id': sent_message.chat_id, 'message_id': sent_message.message_id})

async def handle_button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == "next_page":
        context.user_data['current_page'] += 1
        await send_search_results(query, context)
    else:
        url = context.user_data.get(query.data)
        if url:
            await filmyfly_download_linkmake_view(url, update, context)

async def filmyfly_download_linkmake_view(url, update: Update, context: CallbackContext):
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
        sent_message = await update.callback_query.message.reply_text("Linkmake Links:", reply_markup=reply_markup)
        
        # Schedule the deletion of the message after 10 minutes (600 seconds)
        context.job_queue.run_once(delete_message, 600, data={'chat_id': sent_message.chat_id, 'message_id': sent_message.message_id})
    else:
        await update.callback_query.message.reply_text(f"Failed to retrieve the webpage. Status code: {response.status_code}")

async def filmyfly_scraping(update: Update, context: CallbackContext):
    # Send a "Searching..." message
    searching_message = await update.message.reply_text("Searching...")
    
    # Fetch download links
    filmyflyurl = update.message.text
    if not filmyflyurl:
        await update.message.reply_text("Search Any Movie With Correct Spelling To Download")
        return

    filmyfly_domain = redirection_domain_get("https://filmyfly.esq")
    filmyfly_final = f"{filmyfly_domain}site-1.html?to-search={filmyflyurl}"
    await filmyfly_movie_search(filmyfly_final, filmyfly_domain, update, context, searching_message.message_id)

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

    # Register the button click handler
    app.add_handler(CallbackQueryHandler(handle_button_click))

    # Run the bot using a webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
