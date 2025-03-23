import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os
import re
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from textblob import TextBlob

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")  # MongoDB connection string

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Connect to MongoDB
client = MongoClient(MONGO_URI)

db = client["telegram_bot"]  # Database

chat_collection = db["chat_logs"]  # Collection for chat logs
announcement_collection = db["announcements"]  # Collection for announcements
reminders_collection = db["reminders"]  # Collection for event reminders
leaderboard_collection = db["leaderboard"]  # Collection for tracking user points
discussions_collection = db["discussions"]  # Collection for AI-generated discussion topics
votes_collection = db["votes"]  # Collection to track user votes
sentiment_collection = db["sentiment_logs"]  # Collection for sentiment tracking


FAQS = {
    "What is this bot?": "This is an AI-powered community bot that provides AI-generated responses.",
    "How do I ask a question?": "Type your question, and the bot will generate an response.",
    "How do I set announcements?": "Admins can use `/set_announcement` to schedule an announcement."
}


# Function for /start command
async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    welcome_message = (
        f"👋 Hello, {user_name}! Welcome to our AI-powered bot.\n\n"
        "✨ You can:\n"
        "🔹 Ask questions (just type your message)\n"
        "🔹 Use `/faq` to see common questions\n"
        "🔹 Get announcements from admins\n\n"
        "Let's get started! 🚀"
    )
    await update.message.reply_text(welcome_message)

 
# Function To Set /faq    
async def faq(update: Update, context: CallbackContext):
    faq_message = "📌 *Frequently Asked Questions:*\n\n"
    for question, answer in FAQS.items():
        faq_message += f"❓ *{question}*\n➡ {answer}\n\n"
    
    await update.message.reply_text(faq_message, parse_mode="Markdown")

#Function To Welcome New Members
async def welcome_new_member(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        welcome_text = f"👋 Welcome, {member.first_name}! Feel free to ask questions. Type `/faq` to see common questions."
        await update.message.reply_text(welcome_text)


# Function for Gemini AI Replies & Storing Chat Logs
async def gemini_reply(update: Update, context: CallbackContext):
    user_message = update.message.text  
    user_id = update.message.from_user.id
    user_name = update.message.from_user.username or "Unknown"

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(user_message)
        reply_text = response.text if response and response.text else "I'm not sure how to respond to that."

        # Analyze sentiment
        sentiment = analyze_sentiment(user_message)

        # Store chat log in MongoDB
        chat_log = {
            "user_id": user_id,
            "username": user_name,
            "message": user_message,
            "bot_reply": reply_text,
            "sentiment": sentiment,
            "timestamp": datetime.datetime.utcnow()
        }
        chat_collection.insert_one(chat_log)  

        # Store sentiment log separately
        sentiment_collection.insert_one({"user_id": user_id, "sentiment": sentiment, "timestamp": datetime.datetime.utcnow()})

        await update.message.reply_text(reply_text)

    except Exception as e:
        await update.message.reply_text("Sorry, I couldn't process your request.")
        print("Error:", e)  
 


#Function to build LeaderBoard
async def leaderboard(update: Update, context: CallbackContext):
    """Displays the top users based on points."""
    user_count = leaderboard_collection.count_documents({})
    
    if user_count == 0:
        await update.message.reply_text("No leaderboard data yet. Start chatting to earn points!")
        return

    top_users = list(leaderboard_collection.find().sort("points", -1).limit(5))  # Convert cursor to list

    leaderboard_text = "🏆 *Leaderboard - Top Users* 🏆\n\n"
    rank = 1
    for user in top_users:
        username = user.get("username", "Unknown")  # Ensure username exists
        safe_username = re.sub(r'[_*[\]()~`>#+-=|{}.!]', '', username)  # Escape special characters
        leaderboard_text += f"{rank}. @{safe_username} - {user['points']} points\n"
        rank += 1

    await update.message.reply_text(leaderboard_text, parse_mode="Markdown")

#function to generate discussion topics
async def generate_discussion():
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content("Give me a thought-provoking discussion topic.")
        return response.text if response and response.text else "Is technology making us smarter or lazier?"
    except Exception as e:
        print("Error generating discussion:", e)
        return "Is technology making us smarter or lazier?"

#function to send discussion prompt 
async def send_discussion_prompt(context: CallbackContext):
    discussion = await generate_discussion()
    chat_id = context.job.context

    # Store discussion in MongoDB
    discussion_entry = {
        "topic": discussion,
        "timestamp": datetime.datetime.utcnow(),
        "yes_votes": 0,
        "no_votes": 0
    }
    discussion_id = discussions_collection.insert_one(discussion_entry).inserted_id

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💬 *Discussion Topic of the Day*\n\n{discussion}\n\nVote using:\n✅ `/vote yes`\n❌ `/vote no`",
        parse_mode="Markdown"
    )

#function to handle voting
async def vote(update: Update, context: CallbackContext):
    """Handles voting for the latest discussion topic."""
    user_id = update.message.from_user.id

    # Extract the vote argument manually
    if not context.args:
        await update.message.reply_text("Usage: `/vote yes` or `/vote no`", parse_mode="Markdown")
        return

    vote_option = context.args[0].lower()
    if vote_option not in ["yes", "no"]:
        await update.message.reply_text("❌ Invalid vote! Use `/vote yes` or `/vote no`.", parse_mode="Markdown")
        return

    # Get the latest discussion
    latest_discussion = discussions_collection.find_one({}, sort=[("_id", -1)])
    if not latest_discussion:
        await update.message.reply_text("No active discussion topics to vote on.")
        return

    # Check if the user has already voted
    existing_vote = votes_collection.find_one({"user_id": user_id, "discussion_id": latest_discussion["_id"]})
    if existing_vote:
        await update.message.reply_text("❌ You have already voted on this topic!")
        return

    # Store vote in MongoDB
    votes_collection.insert_one({"user_id": user_id, "discussion_id": latest_discussion["_id"], "vote": vote_option})

    # Update discussion vote count
    update_field = "yes_votes" if vote_option == "yes" else "no_votes"
    discussions_collection.update_one({"_id": latest_discussion["_id"]}, {"$inc": {update_field: 1}})

    await update.message.reply_text(f"✅ Vote recorded: {vote_option.upper()}!")


#Function to set reminders
async def set_reminder(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if len(context.args) < 3:
        await update.message.reply_text("Usage: /set_reminder YYYY-MM-DD HH:MM Event description")
        return

    date_str = context.args[0]
    time_str = context.args[1]
    message = " ".join(context.args[2:])

    try:
        reminder_time = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        # Store reminder in MongoDB
        reminder = {
            "user_id": user_id,
            "message": message,
            "time": reminder_time,
            "notified": False  # Track whether the reminder has been sent
        }
        reminder_id = reminders_collection.insert_one(reminder).inserted_id

        # Schedule the reminder
        scheduler.add_job(
            send_reminder,
            CronTrigger(year=reminder_time.year, month=reminder_time.month, day=reminder_time.day,
                        hour=reminder_time.hour, minute=reminder_time.minute),
            args=[reminder_id],
            id=str(reminder_id),
            replace_existing=True
        )

        await update.message.reply_text(f"✅ Reminder set for {date_str} at {time_str}!")

    except ValueError:
        await update.message.reply_text("❌ Invalid date/time format! Use YYYY-MM-DD HH:MM.")

#function to send reminder message
async def send_reminder(reminder_id):
    reminder = reminders_collection.find_one({"_id": reminder_id})

    if reminder and not reminder["notified"]:
        chat_id = reminder["user_id"]
        message = f"⏰ *Reminder!*\n\n{reminder['message']}\n\n📅 {reminder['time'].strftime('%Y-%m-%d %H:%M')}"
        
        # Send the message
        await app.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        
        # Mark reminder as sent
        reminders_collection.update_one({"_id": reminder_id}, {"$set": {"notified": True}})


# Function to set announcements
async def set_announcement(update: Update, context: CallbackContext):
    """Allows admin to set a new announcement"""
    user_id = update.message.from_user.id

    # Restrict access to admins
    ADMIN_IDS = [1186503158] 
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to set announcements.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /set_announcement Your announcement message")
        return

    message = " ".join(context.args)
    timestamp = datetime.datetime.utcnow()

    # Store announcement in MongoDB
    announcement_collection.insert_one({"message": message, "timestamp": timestamp})
    
    await update.message.reply_text("✅ Announcement updated successfully!")


# Function to send scheduled announcements
async def send_scheduled_announcement(context: CallbackContext):
    announcement = announcement_collection.find_one({}, sort=[("_id", -1)])
    if announcement:
        message = f"📢 *Scheduled Announcement*\n\n{announcement['message']}\n\n🕒 {announcement['timestamp']}"
        chat_id = context.job.context  # Group/User ID
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")


#Function for motivational messages
async def generate_motivation():
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content("Give me a short motivational quote.")
        return response.text if response and response.text else "🌟 Keep pushing forward!"
    except Exception as e:
        print("Error generating motivation:", e)
        return "🌟 Keep pushing forward!"
        
async def send_motivational_message(context: CallbackContext):
    motivation = await generate_motivation()
    chat_id = context.job.context
    await context.bot.send_message(chat_id=chat_id, text=f"💡 *Daily Motivation*\n\n{motivation}", parse_mode="Markdown")

async def motivate(update: Update, context: CallbackContext):
    motivation = await generate_motivation()
    await update.message.reply_text(f"💡 *Here's a motivation for you!*\n\n{motivation}", parse_mode="Markdown")


#function to analyze sentiments 
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # Sentiment score between -1 and 1

    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"


#function for sentiment report
async def sentiment_report(update: Update, context: CallbackContext):
    total_messages = sentiment_collection.count_documents({})
    if total_messages == 0:
        await update.message.reply_text("No sentiment data available yet. Start chatting!")
        return

    positive_count = sentiment_collection.count_documents({"sentiment": "Positive"})
    neutral_count = sentiment_collection.count_documents({"sentiment": "Neutral"})
    negative_count = sentiment_collection.count_documents({"sentiment": "Negative"})

    report = (
        "📊 *Community Sentiment Report* 📊\n\n"
        f"😊 Positive: {positive_count} messages\n"
        f"😐 Neutral: {neutral_count} messages\n"
        f"😡 Negative: {negative_count} messages\n\n"
        f"📌 Total messages analyzed: {total_messages}"
    )

    await update.message.reply_text(report, parse_mode="Markdown")

        
# Setting up the bot
app = Application.builder().token(TOKEN).build()

# Adding handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("set_announcement", set_announcement))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gemini_reply))
app.add_handler(CommandHandler("faq", faq))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
app.add_handler(CommandHandler("set_reminder", set_reminder))
app.add_handler(CommandHandler("motivate", motivate))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("vote", vote))
app.add_handler(CommandHandler("sentiment_report", sentiment_report))


# Scheduler for daily tasks
scheduler = BackgroundScheduler()


# Daily motivational messages at 9:00 AM
scheduler.add_job(
    send_motivational_message,
    CronTrigger(hour=9, minute=0),
    args=[None], 
    id="daily_motivation",
    replace_existing=True
)

# Daily discussion prompt at 10:00 AM
scheduler.add_job(
    send_discussion_prompt,
    CronTrigger(hour=10, minute=0),
    args=[None],  # Placeholder for chat_id
    id="daily_discussion",
    replace_existing=True
)

# Daily announcements at 12:00 PM
scheduler.add_job(
    send_scheduled_announcement,
    CronTrigger(hour=12, minute=0),
    args=[None], 
    id="daily_announcement",
    replace_existing=True
)

scheduler.start()


print("Bot is running...")
app.run_polling()
