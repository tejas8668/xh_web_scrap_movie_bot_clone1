import os
import logging
import asyncio
import re
from urllib.parse import urljoin
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
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
users = {}
search_results = {}

# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    user = update.effective_user

    # Initialize user data
    users[user.id] = {
        'search_results': [],
        'current_page': 0
    }

    message = (
        f"New user started the bot:\n"
        f"Name: {user.full_name}\n"
        f"Username: @{user.username}\n"
        f"User  ID: {user.id}"
    )
    await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
    await update.message.reply_photo(
        photo='https://ik.imagekit.io/dvnhxw9vq/movie_bot.png?updatedAt=1741412177209',  # Replace with your image URL
        caption=(
            "👋 **ℍ𝕖𝕝𝕝𝕠 𝔻𝕖𝕒𝕣!**\n\n"
            "I am an advanced movie search bot. Just send me any movie name and I will give you a direct download link of any movie.​\n\n"
            "**𝐈𝐦𝐩𝐨𝐫𝐭𝐚𝐧𝐭​​**\n\n"
            "Please search with the correct spelling for better results."
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

async def send_search_results(update: Update, context: CallbackContext):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    if user_id not in users or 'search_results' not in users[user_id]:
        await update.message.reply_text("No search results available.")
        return
    buttons = users[user_id]['search_results']
    current_page = users[user_id]['current_page']
    
    # Paginate the results
    start = current_page * 5
    end = start + 5
    page_buttons = buttons[start:end]
    
    # Send the video links with thumbnails
    for index, (video_url, image_url) in enumerate(page_buttons):
        # Truncate the video_url *only* for the callback data
        truncated_video_url = video_url[:50]
        callback_data = f"watch_{truncated_video_url}"
        if len(callback_data) > 64:
            callback_data = callback_data[:64]  # Truncate to fit the allowed length

        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_url,
                caption=f"Video {start + index + 1}: [Watch Video]", # Removed callback data from caption
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Watch", callback_data=callback_data)]
                ])
            )
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            if update.message:
                await update.message.reply_text(f"Failed to send video {start + index + 1}.")
            elif update.callback_query:
                await update.callback_query.message.reply_text(f"Failed to send video {start + index + 1}.")
    
    # Add a "Next" button if there are more results
    if end < len(buttons):
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Next", callback_data="next_page")]
        ])
        if update.message:
            del_msg = await update.message.reply_text("More results available:", reply_markup=reply_markup)
        elif update.callback_query:
            try:
                del_msg = await update.callback_query.message.reply_text("More results available:", reply_markup=reply_markup)
            except AttributeError as e:
                logger.error(f"Error sending 'More results' message: {e}")
                return # Exit the function if the message cannot be sent
        
        # Schedule the deletion of the message after 120 seconds without blocking
        asyncio.create_task(delete_message_after_delay(del_msg))


async def handle_button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Ensure the user is initialized
    if user_id not in users:
        users[user_id] = {
            'search_results': [],
            'current_page': 0
        }
    
    if query.data == "next_page":
        users[user_id]['current_page'] += 1
        await send_search_results(update, context)
    elif query.data.startswith("watch_"):
        video_url = query.data[len("watch_"):]
        try:
            await xh_scrape_m3u8_links(video_url, update, context)
        except Exception as e:
            logger.error(f"Error in xh_scrape_m3u8_links: {e}")
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(f"Failed to process video link.")
            else:
                logger.error("Callback query or message is None in handle_button_click")
    else:
        url = context.user_data.get(query.data)
        if url:
            await filmyfly_download_linkmake_view(url, update)


async def delete_message_after_delay(message):
    await asyncio.sleep(120)
    await message.delete()

async def Xhamster_scrap_get_link_thumb(url, update, context, searching_message_id):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        if update.message:
            await update.message.reply_text(f"Failed to retrieve the page: {e}")
        elif update.callback_query:
            await update.callback_query.message.reply_text(f"Failed to retrieve the page: {e}")
        return
    
    soup = BeautifulSoup(response.content, 'html.parser')
    video_thumbs = soup.find_all('div', class_='video-thumb-info')
    
    user_id = update.effective_user.id
    
    # Ensure the user is initialized
    if user_id not in users:
        users[user_id] = {
            'search_results': [],
            'current_page': 0
        }

    users[user_id]['search_results'] = []

    for video in video_thumbs:
        link_tag = video.find('a')
        if link_tag and 'href' in link_tag.attrs:
            video_url = link_tag['href']
            parent_div = video.find_parent('div', class_='thumb-list__item video-thumb video-thumb--type-video')
            if parent_div:
                img_tag = parent_div.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    image_url = img_tag['src']
                    users[user_id]['search_results'].append((video_url, image_url))

    if update.message:
        await update.message.reply_text("Links fetched successfully!")
    elif update.callback_query:
        await update.callback_query.message.reply_text("Links fetched successfully!")
    await send_search_results(update, context)


async def xh_scrape_m3u8_links(url, update: Update, context: CallbackContext):
    try:
        # Fetch webpage content
        response = requests.get(url)
        response.raise_for_status()
        
        # Create BeautifulSoup object
        soup = BeautifulSoup(response.text, 'html.parser')
        base_url = response.url  # Get base URL for joining relative links
        
        # List to store all found m3u8 links
        m3u8_links = []
        
        # Find links in href attributes
        for tag in soup.find_all(href=re.compile(r'\.m3u8$')):
            href = tag.get('href')
            full_url = urljoin(base_url, href)
            m3u8_links.append(full_url)
        
        # Find links in src attributes
        for tag in soup.find_all(src=re.compile(r'\.m3u8$')):
            src = tag.get('src')
            full_url = urljoin(base_url, src)
            m3u8_links.append(full_url)
        
        # Additional search using regex for any m3u8 patterns in page text
        text_links = re.findall(r'https?://[^\s"\']+\.m3u8', response.text)
        m3u8_links.extend([urljoin(base_url, link) for link in text_links])
        
        # Remove duplicates
        unique_links = list(set(m3u8_links))
        
        # Send results as Telegram buttons
        if unique_links:
            buttons = []
            for link in unique_links:
                stream_gen_link_xh_to_hsl = f"https://www.hlsplayer.org/play?url={link}"
                buttons.append([InlineKeyboardButton("Watch Stream", url=stream_gen_link_xh_to_hsl)])
            
            reply_markup = InlineKeyboardMarkup(buttons)
            if update.message:
                await update.message.reply_text("Found m3u8 links:", reply_markup=reply_markup)
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("Found m3u8 links:", reply_markup=reply_markup)
            else:
                logger.error("No message or callback_query.message in xh_scrape_m3u8_links")
        else:
            if update.message:
                await update.message.reply_text("No .m3u8 links found on the page")
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("No .m3u8 links found on the page")
            else:
                logger.error("No message or callback_query.message in xh_scrape_m3u8_links")
    except requests.exceptions.RequestException as e:
        if update.message:
            await update.message.reply_text(f"Error fetching the page: {e}")
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(f"Error fetching the page: {e}")
        else:
            logger.error("No message or callback_query.message in xh_scrape_m3u8_links")
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"An error occurred: {e}")
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(f"An error occurred: {e}")
        else:
            logger.error("No message or callback_query.message in xh_scrape_m3u8_links")

async def xh_scrap_video_home_demo_code(update: Update, context: CallbackContext):
    searching_message = await update.message.reply_text("Searching...")
    
    xh_home_scrap_query = update.message.text
    if not xh_home_scrap_query:
        await update.message.reply_text("Send Message ''Get Video'' for Get Videos")
        return

    xh_home_crap_domain = "https://xhamster43.desi/"
    await Xhamster_scrap_get_link_thumb(xh_home_crap_domain, update, context, searching_message.message_id)

async def xh_scrap_video_home(update: Update, context: CallbackContext):
    # Send a "Searching..." message
    searching_message = await update.message.reply_text("Searching...")
    
    # Fetch download links
    xh_user_query = update.message.text
    if not xh_user_query:
        await update.message.reply_text("Search Query To Get Video")
        return

    #filmyfly_domain = redirection_domain_get("https://xhamster43.desi/")
    #filmyfly_final = f"{filmyfly_domain}site-1.html?to-search={xh_home_scrap_query}"
    xh_search_query = f"https://xhamster43.desi/search/{xh_user_query}"
    await Xhamster_scrap_get_link_thumb(xh_search_query, update, context, searching_message.message_id)

async def video_command(update: Update, context: CallbackContext):
    searching_message = await update.message.reply_text("Searching...")
    
    xh_home_scrap_query = update.message.text
    if not xh_home_scrap_query:
        await update.message.reply_text("Send Message ''Get Video'' for Get Videos")
        return

    xh_home_crap_domain = "https://xhamster43.desi/"
    await Xhamster_scrap_get_link_thumb(xh_home_crap_domain, update, context, searching_message.message_id)

def main() -> None:
    port = int(os.environ.get('PORT', 8080))
    webhook_url = f"https://delicate-jyoti-toxicc-188b9b28.koyeb.app/{TOKEN}"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("video", video_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, xh_scrap_video_home))
    app.add_handler(CallbackQueryHandler(handle_button_click))

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=webhook_url
    )

if __name__ == '__main__':
    main()
