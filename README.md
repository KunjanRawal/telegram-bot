🚀 AI-Powered Telegram Bot

📖 Overview
This is an AI-powered Telegram bot designed for community management, AI chat responses, automated engagement, and gamification. The bot provides:
✅ AI-generated responses using Gemini API
✅ Automated announcements & scheduled event reminders
✅ Leaderboard feature
✅ Sentiment analysis & AI-powered discussion prompts

⚙️ Features
AI-Powered Chat 🤖 → Uses Gemini API for intelligent responses

FAQ System 📌 → Type /faq to get answers to common questions

Automated Announcements 📢 → Admins can set scheduled messages

Event Reminders ⏰ → Users can set reminders using /set_reminder

Gamification & Leaderboards 🏆 → Tracks engagement & displays top users

Discussion Prompts 💬 → AI generates thought-provoking discussion topics

Sentiment Analysis 📊 → Analyzes chat mood for better engagement


🛠️ Setup & Installation

1️⃣ Clone the Repository
git clone https://github.com/KunjanRawal/telegram-bot.git
cd telegram-bot

2️⃣ Install Dependencies
pip install -r requirements.txt

3️⃣ Set Up Environment Variables
Create a .env file and add the following:
TELEGRAM_BOT_TOKEN=your_telegram_token
MONGO_URI=your_mongodb_uri
GEMINI_API_KEY=your_gemini_api_key


🚀 Deployment on Railway

1️⃣ Link Railway to GitHub
1.Go to Railway

2.Click "New Project" → "Deploy from GitHub"

3.Select telegram-bot repository

2️⃣ Add Environment Variables
In Railway, go to "Variables" and add:

1.TELEGRAM_BOT_TOKEN

2.MONGO_URI

3.GEMINI_API_KEY

3️⃣ Deploy the Bot
Set:

1.Build Command: pip install -r requirements.txt

2.Start Command: python bot.py

3.Click "Deploy" 🚀


🤖 Available Commands

## 🤖 Available Commands

| Command                               | Description |
|---------------------------------------|-------------|
| `/start`                              | Starts the bot and displays a welcome message |
| `/faq`                                | Provides answers to frequently asked questions |
| `/set_announcement <message>`         | Admins can set scheduled announcements |
| `/set_reminder YYYY-MM-DD HH:MM <message>` | Sets an event reminder |
| `/leaderboard`                        | Shows top users based on points |
| `/vote yes/no`                        | Casts a vote in an AI-generated discussion |
| `/sentiment_report`                   | Displays sentiment analysis of chat data |
| `/motivate`                            | Sends a daily AI-generated motivational message |


🎥 Loom Video Demonstration

https://www.loom.com/share/ef5b03da0d074ff9b0ec87eaaa75f183?sid=2535feb2-6011-475c-895c-f9ceebc7df08

🙌 Credits
Developed by Kunjan Rawal 🎉
