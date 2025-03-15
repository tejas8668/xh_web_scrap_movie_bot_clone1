import os
import logging
import asyncio
import re
import uuid
from urllib.parse import urljoin
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import requests
from bs4 import BeautifulSoup
import urllib.parse
from pymongo import MongoClient
from datetime import datetime, timedelta
from telegram import CallbackQuery


# Add this at the top of the file
VERIFICATION_REQUIRED = os.getenv('VERIFICATION_REQUIRED', 'true').lower() == 'true'

# Get the bot token and channel ID from environment variables
TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# In-memory storage for user tracking
users = {}
search_results = {}
temp_url_ids = {}  # Dictionary to store temporary URL IDs and their URLs
message_deletion_tasks = {}  # Dictionary to store message deletion tasks

admin_ids = [6025969005, 6018060368]

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI')  # Get MongoDB URI from environment variables
client = MongoClient(MONGO_URI)
db = client['xh_bot']  # Updated database name
users_collection = db['users']

# Referral points reward
REFERRAL_POINTS = 25
PREMIUM_POINTS = 50

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Function to generate a unique referral code
def generate_referral_code(user_id):
    return f"{user_id}_{uuid.uuid4().hex[:6]}"

# Function to award premium access (skip verification)
# Function to award premium access (skip verification)
async def award_premium_access(user_id, query: CallbackQuery, context: CallbackContext):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"verified_until": datetime.now() + timedelta(days=1)}},
        upsert=True
    )
    await query.message.reply_text(
        "🎉 **Premium Access Unlocked!**\n\n"
        "You have earned premium access and can use the bot without verification for the next 24 hours.",
        parse_mode='Markdown'
    )


# Define the /start command handler
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    user = update.effective_user
    user_id = user.id

    # Check if the user exists in the database
    existing_user = users_collection.find_one({"user_id": user_id})

    # If the user is new, create a new entry
    if not existing_user:
        # Create a new user entry
        new_user_data = {
            "user_id": user_id,
            "username": user.username,
            "full_name": user.full_name,
            "referral_code": generate_referral_code(user_id),
            "referred_by": None,
            "referral_points": 0,
            "verified_until": datetime.min
        }
        users_collection.insert_one(new_user_data)

        # Check if the start command includes a referral code
        if context.args:
            referral_code = context.args[0]
            referrer = users_collection.find_one({"referral_code": referral_code})

            if referrer:
                referrer_id = referrer['user_id']
                # Update the referred user's document with the referrer's ID
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"referred_by": referrer_id}}
                )

                # Increment the referrer's referral points
                users_collection.update_one(
                    {"user_id": referrer_id},
                    {"$inc": {"referral_points": REFERRAL_POINTS}}
                )

                # Send a message to the referrer
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            "🎉 You successfully completed 1 referral and earned "
                            f"{REFERRAL_POINTS} points! Check your points using /points command."
                        )
                    )
                except Exception as e:
                    logger.error(f"Error sending referral notification to user {referrer_id}: {e}")
            else:
                await update.message.reply_text("Invalid referral code.")
                return

        # Send the welcome message and store user ID in MongoDB
        message = (
            f"New user started the bot:\n"
            f"Name: {user.full_name}\n"
            f"Username: @{user.username}\n"
            f"User     ID: {user.id}"
        )
        await context.bot.send_message(chat_id=CHANNEL_ID, text=message)

    else:
        # Ensure referral_code exists for existing users (migration)
        if "referral_code" not in existing_user:
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"referral_code": generate_referral_code(user_id)}}
            )

    # Update user information in the database
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"username": user.username, "full_name": user.full_name}},
        upsert=True
    )

    # Send the welcome message
    start_message = await update.message.reply_photo(
        photo='https://ik.imagekit.io/dvnhxw9vq/bot_pic.jpeg?updatedAt=1741960637889',  # Replace with your image URL
        caption=(
            "🔥 Welcome My Friend 🔥\n\n"
            "🔞 Your ultimate destination for exclusive adult content!\n\n💦 What You Get Here:\n✅ HD Exclusive Videos\n✅ Daily Hot Updates 🔥\n✅ Private & Premium Content 💎\n✅ Exclusive Requests 📝\n\n"
            "🚀 Start Exploring Now!\n\n"
            "👉 Send /start to Start\n👉 Use /video for Get Video\n👉 You Can Also Search Video To Sending A Message To Bot\n\n🔥 Popular Search 🔥\n👉 `Russian`\n👉 `Hot Girls`\n👉 `DBSM`\n👉 `Sex Videos`\n\n"
            "📌 Reffer The Bot Link Unlock All Bot Primium Feature\n"
            "📌 Use /reffer Command To Know More\n\n"
        ),
    )
    # Do not schedule deletion for the /start message

"""async def referral_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id

    existing_user = users_collection.find_one({"user_id": user_id})

    if not existing_user:
        await update.message.reply_text("You need to start the bot first using /start.")
        return

    referral_link = f"https://t.me/{context.bot.username}?start={existing_user['referral_code']}"
    await update.message.reply_text(
        f"Your referral link: {referral_link}\n\n"
        "Share this link with your friends to earn rewards!"
    )"""

async def referral_command(update: Update, context: CallbackContext) -> None:
    # Check if the call is from a callback query or a command
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Acknowledge the callback query
        user = query.from_user  # Get user from the callback query
    else:
        user = update.effective_user  # Get user from the command

    user_id = user.id

    existing_user = users_collection.find_one({"user_id": user_id})

    if not existing_user:
        message_text = "You need to start the bot first using /start."
        if update.callback_query:
            await query.message.reply_text(message_text)
        else:
            await update.message.reply_text(message_text)
        return

    referral_link = f"https://t.me/{context.bot.username}?start={existing_user['referral_code']}"

    message_text = (
        f"Your referral link:\n{referral_link}\n\n"
        "Share this link with your friends to earn rewards!\n\nGet 25 Points Per Complete reffer\nYou Need 50 Points To Unlock (Skip) One Verification\n\nShare And Use All Bot Primium Feature Without Ads Or Verify"
    )

    if update.callback_query:
        await query.message.reply_text(message_text)
    else:
        await update.message.reply_text(message_text)

async def check_verification(user_id: int) -> bool:
    user = users_collection.find_one({"user_id": user_id})
    if user and user.get("verified_until", datetime.min) > datetime.now():
        return True
    return False

async def get_token(user_id: int, bot_username: str) -> str:
    # Generate a random token
    token = os.urandom(16).hex()
    # Update user's verification status in database
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"token": token, "verified_until": datetime.min}},  # Reset verified_until to min
        upsert=True
    )
    # Create verification link
    verification_link = f"https://telegram.me/{bot_username}?start={token}"
    # Shorten verification link using shorten_url_link function
    shortened_link = shorten_url_link(verification_link)
    return shortened_link

def shorten_url_link(url):
    api_url = 'https://arolinks.com/api'
    api_key = '90bcb2590cca0a2b438a66e178f5e90fea2dc8b4'
    params = {
        'api': api_key,
        'url': url
    }
    response = requests.get(api_url, params=params, verify=False)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success':
            logger.info(f"Adrinolinks shortened URL: {data['shortenedUrl']}")
            return data['shortenedUrl']
    logger.error(f"Failed to shorten URL with Adrinolinks: {url}")
    return url

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
        # Create a unique ID for the URL
        url_id = str(uuid.uuid4())

        # Store the video URL in context.user_data
        context.user_data[url_id] = video_url

        callback_data = f"watch_{url_id}" # Callback data is now the unique ID
        
        try:
            sent_message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_url,
                caption=f"Video {start + index + 1}: [Click On Watch]", # Removed callback data from caption
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Watch", callback_data=callback_data)]
                ])
            )
            asyncio.create_task(delete_message_after_delay(sent_message))
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            if update.message:
                error_message = await update.message.reply_text(f"Failed to send video {start + index + 1}.")
                asyncio.create_task(delete_message_after_delay(error_message))
            elif update.callback_query:
                error_message = await update.callback_query.message.reply_text(f"Failed to send video {start + index + 1}.")
                asyncio.create_task(delete_message_after_delay(error_message))
    
    # Add a "Next" button if there are more results
    if end < len(buttons):
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Next", callback_data="next_page")]
        ])
        if update.message:
            del_msg = await update.message.reply_text("More results available:", reply_markup=reply_markup)
            asyncio.create_task(delete_message_after_delay(del_msg))
        elif update.callback_query:
            try:
                del_msg = await update.callback_query.message.reply_text("More results available:", reply_markup=reply_markup)
                asyncio.create_task(delete_message_after_delay(del_msg))
            except AttributeError as e:
                logger.error(f"Error sending 'More results' message: {e}")
                return # Exit the function if the message cannot be sent

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
        url_id = query.data[len("watch_"):]
        video_url = context.user_data.get(url_id)
        if video_url:
            try:
                await xh_scrape_m3u8_links(video_url, update, context)
            except Exception as e:
                logger.error(f"Error in xh_scrape_m3u8_links: {e}")
                if update.callback_query and update.callback_query.message:
                    error_message = await update.callback_query.message.reply_text(f"Failed to process video link.")
                    asyncio.create_task(delete_message_after_delay(error_message))
                else:
                    logger.error("Callback query or message is None in handle_button_click")
        else:
            logger.warning(f"No video URL found for ID: {url_id}")
            if update.callback_query and update.callback_query.message:
                error_message = await update.callback_query.message.reply_text("This video link has expired.")
                asyncio.create_task(delete_message_after_delay(error_message))
            else:
                logger.error("Callback query or message is None in handle_button_click")
    else:
        url = context.user_data.get(query.data)
        if url:
            await filmyfly_download_linkmake_view(url, update)

async def delete_message_after_delay(message):
    await asyncio.sleep(300)  # 5 minutes = 300 seconds
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")

async def Xhamster_scrap_get_link_thumb(url, update, context, searching_message_id):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        effective_message = update.effective_message # Use effective_message
        if effective_message:
            error_message = await effective_message.reply_text(f"Failed to retrieve the page: {e}")
            asyncio.create_task(delete_message_after_delay(error_message))
        else:
            logger.error("No effective message available in Xhamster_scrap_get_link_thumb")
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

    effective_message = update.effective_message # Use effective_message
    if effective_message:
        success_message = await effective_message.reply_text("Links fetched successfully!")
        asyncio.create_task(delete_message_after_delay(success_message))
    else:
        logger.error("No effective message available after fetching links.")
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
                # Decode the URL before passing it to the HLS player
                decoded_link = urllib.parse.unquote(link)
                stream_gen_link_xh_to_hsl = f"https://www.hlsplayer.org/play?url={decoded_link}"
                buttons.append([InlineKeyboardButton("Watch Stream", url=stream_gen_link_xh_to_hsl)])
            
            reply_markup = InlineKeyboardMarkup(buttons)
            effective_message = update.effective_message
            if effective_message:
                stream_message = await effective_message.reply_text("Your Stream Link", reply_markup=reply_markup)
                asyncio.create_task(delete_message_after_delay(stream_message))
            else:
                logger.error("No message or callback_query.message in xh_scrape_m3u8_links")
        else:
            effective_message = update.effective_message
            if effective_message:
                no_links_message = await effective_message.reply_text("No .m3u8 links found on the page")
                asyncio.create_task(delete_message_after_delay(no_links_message))
            else:
                logger.error("No message or callback_query.message in xh_scrape_m3u8_links")
    except requests.exceptions.RequestException as e:
        effective_message = update.effective_message
        if effective_message:
            error_message = await effective_message.reply_text(f"Error fetching the page: {e}")
            asyncio.create_task(delete_message_after_delay(error_message))
        else:
            logger.error("No message or callback_query.message in xh_scrape_m3u8_links")
    except Exception as e:
        effective_message = update.effective_message
        if effective_message:
            error_message = await effective_message.reply_text(f"An error occurred: {e}")
            asyncio.create_task(delete_message_after_delay(error_message))
        else:
            logger.error("No message or callback_query.message in xh_scrape_m3u8_links")

async def xh_scrap_video_home(update: Update, context: CallbackContext):
    user = update.effective_user

    if user.id in admin_ids:
        # Admin ko verify karne ki zaroorat na ho
        pass
    else:
        # User ko verify karne ki zaroorat hai
        if VERIFICATION_REQUIRED and not await check_verification(user.id):
            # User ko verify karne ki zaroorat hai
            btn = [
                [InlineKeyboardButton("Verify", url=await get_token(user.id, context.bot.username))],
                [InlineKeyboardButton("How To Open Link & Verify", url="https://t.me/how_to_download_0011")],
                [InlineKeyboardButton("Reffer To Skip Verify", callback_data="reffer")]  # Corrected Referral Button
            ]
            await update.message.reply_text(
                text="🚨 <b>Token Expired!</b>\n\n"
                     "<b>Timeout: 24 hours</b>\n\n"
                     "Your access token has expired. Verify it to continue using the bot!\n\n"
                     "<b>🔑 Why Tokens?</b>\n\n"
                     "Tokens unlock premium features with a quick ad process. Enjoy 24 hours of uninterrupted access! 🌟\n\n"
                     "<b>👉 Tap below to verify your token.</b>\n\n"
                     "/reffer Bot Link To skip The Verification And Unlock Bot Primium Without Watching Ads\nCheck More About It Send /reffer Command\n\n"
                     "Thank you for your support! ❤️",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return
    # Send a "Searching..." message
    searching_message = await update.message.reply_text("Searching...")
    asyncio.create_task(delete_message_after_delay(searching_message))
    
    # Fetch download links
    xh_user_query = update.message.text
    if not xh_user_query:
        no_query_message = await update.message.reply_text("Search Query To Get Video")
        asyncio.create_task(delete_message_after_delay(no_query_message))
        return

    xh_search_query = f"https://xhamster43.desi/search/{xh_user_query}"
    await Xhamster_scrap_get_link_thumb(xh_search_query, update, context, searching_message.message_id)

async def video_command(update: Update, context: CallbackContext):
    user = update.effective_user

    if user.id in admin_ids:
        # Admin ko verify karne ki zaroorat na ho
        pass
    else:
        # User ko verify karne ki zaroorat hai
        if VERIFICATION_REQUIRED and not await check_verification(user.id):
            # User ko verify karne ki zaroorat hai
            btn = [
                [InlineKeyboardButton("Verify", url=await get_token(user.id, context.bot.username))],
                [InlineKeyboardButton("How To Open Link & Verify", url="https://t.me/how_to_download_0011")],
                [InlineKeyboardButton("Reffer To Skip Verify", callback_data="reffer")]  # Corrected Referral Button
            ]
            await update.message.reply_text(
                text="🚨 <b>Token Expired!</b>\n\n"
                     "<b>Timeout: 24 hours</b>\n\n"
                     "Your access token has expired. Verify it to continue using the bot!\n\n"
                     "<b>🔑 Why Tokens?</b>\n\n"
                     "Tokens unlock premium features with a quick ad process. Enjoy 24 hours of uninterrupted access! 🌟\n\n"
                     "<b>👉 Tap below to verify your token.</b>\n\n"
                     "/reffer Bot Link To skip The Verification And Unlock Bot Primium Without Watching Ads\nCheck More About It Send /reffer Command\n\n"
                     "Thank you for your support! ❤️",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return
    searching_message = await update.message.reply_text("Searching...")
    asyncio.create_task(delete_message_after_delay(searching_message))
    
    xh_home_scrap_query = update.message.text
    if not xh_home_scrap_query:
        no_query_message = await update.message.reply_text("Send Message ''Get Video'' for Get Videos")
        asyncio.create_task(delete_message_after_delay(no_query_message))
        return

    xh_home_crap_domain = "https://xhamster43.desi/"
    await Xhamster_scrap_get_link_thumb(xh_home_crap_domain, update, context, searching_message.message_id)

async def points_command(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_id = user.id

    existing_user = users_collection.find_one({"user_id": user_id})

    if not existing_user:
        await update.message.reply_text("You need to start the bot first using /start.")
        return

    referral_points = existing_user.get("referral_points", 0)

    # Add unlock button if user has enough points
    if referral_points >= PREMIUM_POINTS:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Unlock Premium", callback_data="unlock_premium")]])
        await update.message.reply_text(f"Your referral points: {referral_points}\nYou have enough points to unlock premium access! Click the button below to unlock.", reply_markup=keyboard)
    else:
        await update.message.reply_text(f"Your referral points: {referral_points}\n\nGet 25 Points Per Complete reffer\nYou Need 50 Points To Unlock (Skip) One Verification\n\nShare More And Earn More Points To Unlock bot Primium Without Verify")

async def unlock_premium(update: Update, context: CallbackContext) -> None:
    # Check if the call is from a callback query or a command
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Acknowledge the callback query
        user = query.from_user  # Get user from the callback query
    else:
        user = update.effective_user  # Get user from the command

    user_id = user.id

    existing_user = users_collection.find_one({"user_id": user_id})

    if not existing_user:
        if update.callback_query:
            await query.message.reply_text("You need to start the bot first using /start.")
        else:
            await update.message.reply_text("You need to start the bot first using /start.")
        return

    referral_points = existing_user.get("referral_points", 0)

    if referral_points >= PREMIUM_POINTS:
        await award_premium_access(user_id, query if update.callback_query else None, context)  # Award premium access
        # Reset referral points after awarding premium access
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"referral_points": 0}}
        )
        if update.callback_query:
            await query.message.reply_text("Premium access unlocked! Your referral points have been reset.")
        else:
            await update.message.reply_text("Premium access unlocked! Your referral points have been reset.")
    else:
        if update.callback_query:
            await query.message.reply_text("You don't have enough referral points to unlock premium access.\nCheck Your Points Using /points")
        else:
            await update.message.reply_text("You don't have enough referral points to unlock premium access.\nCheck Your Points Using /points")
        
def main() -> None:
    port = int(os.environ.get('PORT', 8080))
    webhook_url = f"https://perfect-bria-tej-fded6488.koyeb.app/{TOKEN}"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reffer", referral_command))  # Add the new handler
    app.add_handler(CallbackQueryHandler(referral_command, pattern="^reffer$"))  # Handle callback query for unlocking premium
    app.add_handler(CommandHandler("video", video_command))
    app.add_handler(CommandHandler("points", points_command))  # Add the new handler
    #app.add_handler(CommandHandler("unlock", unlock_premium))  # Command handler for /unlock
    #app.add_handler(CallbackQueryHandler(unlock_premium, pattern="^unlock_premium$"))  # Handle callback query for unlocking premium
    app.add_handler(CommandHandler("unlock", unlock_premium))  # Command handler for /unlock
    app.add_handler(CallbackQueryHandler(unlock_premium, pattern="^unlock_premium$"))  # Handle callback query for unlocking premium
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
