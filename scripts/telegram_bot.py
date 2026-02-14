#!/usr/bin/env python3
"""
Telegram Bot for GDELT News - Runs as GitHub Action
Responds to user queries with news from GDELT
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
import html
import urllib.parse

# Try to import telegram, but handle if not available
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Warning: python-telegram-bot not installed. Install with: pip install python-telegram-bot")

class GDELTNewsBot:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        # GitHub Pages base URL
        self.site_url = "https://yusdesign.github.io/newstiger"
        
        # GDELT API
        self.gdelt_api = "https://api.gdeltproject.org/api/v2/doc/doc"
        
        # Translation API (using LibreTranslate)
        self.translate_api = "https://libretranslate.de/translate"
        
        # Store last update time
        self.last_update_file = "last_bot_update.txt"
        
    def fetch_news(self, query, country=None, max_records=5):
        """Fetch news from GDELT"""
        params = {
            'query': query,
            'mode': 'artlist',
            'format': 'json',
            'maxrecords': max_records,
            'sort': 'date'
        }
        
        if country:
            params['sourcecountry'] = country
        
        try:
            response = requests.get(self.gdelt_api, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._format_articles(data, query)
            else:
                print(f"GDELT API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching news: {e}")
            return None
    
    def fetch_trending(self, hours=24):
        """Fetch trending topics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        params = {
            'query': '*',
            'mode': 'timelinevol',
            'format': 'json',
            'startdatetime': start_date.strftime('%Y%m%d%H%M%S'),
            'enddatetime': end_date.strftime('%Y%m%d%H%M%S')
        }
        
        try:
            response = requests.get(self.gdelt_api, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._format_trending(data)
            return None
        except Exception as e:
            print(f"Error fetching trending: {e}")
            return None
    
    def translate_text(self, text, target_lang='ru'):
        """Translate text using LibreTranslate"""
        if not text or len(text) < 3:
            return text
        
        try:
            response = requests.post(self.translate_api, json={
                'q': text,
                'source': 'auto',
                'target': target_lang,
                'format': 'text'
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('translatedText', text)
            return text
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    def _format_articles(self, raw_data, query):
        """Format articles for response"""
        articles = []
        
        for article in raw_data.get('articles', [])[:10]:
            articles.append({
                'title': article.get('title', 'No title'),
                'url': article.get('url', '#'),
                'source': article.get('domain', 'Unknown'),
                'date': self._format_date(article.get('seendate', '')),
                'country': article.get('sourcecountry', 'Unknown'),
                'summary': article.get('content', '')[:200] + '...' if article.get('content') else '',
                'themes': article.get('themes', [])[:3]
            })
        
        return {
            'query': query,
            'total': len(articles),
            'articles': articles
        }
    
    def _format_trending(self, raw_data):
        """Format trending data"""
        trends = []
        
        for item in raw_data.get('timeline', [])[:15]:
            trends.append({
                'date': self._format_date(item.get('date', '')),
                'value': item.get('value', 0)
            })
        
        return {
            'trends': trends,
            'total': len(trends)
        }
    
    def _format_date(self, date_str):
        """Format GDELT date"""
        if not date_str or len(date_str) < 8:
            return 'Unknown'
        
        try:
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            
            if len(date_str) >= 12:
                hour = date_str[8:10]
                minute = date_str[10:12]
                return f"{year}-{month}-{day} {hour}:{minute}"
            return f"{year}-{month}-{day}"
        except:
            return date_str
    
    def get_cached_news(self, query):
        """Try to get news from GitHub Pages cache"""
        safe_query = query.lower().replace(' ', '_')
        safe_query = ''.join(c for c in safe_query if c.isalnum() or c == '_')[:50]
        url = f"{self.site_url}/news/search/{safe_query}.json"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def create_news_message(self, articles, query, translate=False):
        """Create formatted message from articles"""
        if not articles:
            return f"No news found for '{query}'"
        
        message = f"📰 *News for: {query}*\n\n"
        
        for i, article in enumerate(articles[:5], 1):
            title = article['title']
            if translate:
                title = self.translate_text(title, 'ru')
            
            message += f"*{i}. {title}*\n"
            message += f"📰 Source: {article['source']}\n"
            message += f"🌍 Country: {article['country']}\n"
            message += f"📅 {article['date']}\n"
            message += f"🔗 [Read more]({article['url']})\n\n"
        
        message += f"\n🔍 More at: {self.site_url}?q={urllib.parse.quote(query)}"
        return message
    
    def create_trending_message(self, trends):
        """Create formatted trending message"""
        if not trends:
            return "No trending data available"
        
        message = "📈 *Trending Topics (Last 24h)*\n\n"
        
        for i, trend in enumerate(trends[:10], 1):
            message += f"{i}. {trend['date']} - Volume: {trend['value']:,}\n"
        
        return message
    
    def check_for_updates(self):
        """Check if there are new articles since last run"""
        try:
            # Get latest news from GitHub Pages
            response = requests.get(f"{self.site_url}/news/latest.json", timeout=5)
            if response.status_code == 200:
                latest = response.json()
                
                # Read last update timestamp
                try:
                    with open(self.last_update_file, 'r') as f:
                        last_timestamp = f.read().strip()
                except:
                    last_timestamp = None
                
                current_timestamp = latest.get('timestamp', '')
                
                if last_timestamp != current_timestamp and last_timestamp:
                    # New articles available
                    return True, latest
                
                # Save current timestamp
                with open(self.last_update_file, 'w') as f:
                    f.write(current_timestamp)
        
        except Exception as e:
            print(f"Error checking updates: {e}")
        
        return False, None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome = (
            "👋 *Welcome to GDELT News Bot!*\n\n"
            "Get latest news from thousands of global sources.\n\n"
            "*Commands:*\n"
            "• /news <query> - Search news\n"
            "• /trending - Trending topics\n"
            "• /russia - News about Russia\n"
            "• /world - World news\n"
            "• /help - Show help\n\n"
            f"🌐 Web version: {self.site_url}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 Search News", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("📈 Trending", callback_data="trending"),
             InlineKeyboardButton("🇷🇺 Russia", callback_data="russia")],
            [InlineKeyboardButton("🌐 Open Web App", url=self.site_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "📚 *GDELT Bot Help*\n\n"
            "*Search Commands:*\n"
            "• `/news technology` - Search for technology news\n"
            "• `/news climate change` - Search with spaces\n"
            "• `/news AI country:US` - Filter by country\n\n"
            "*Quick Commands:*\n"
            "• `/trending` - What's trending now\n"
            "• `/russia` - News about Russia\n"
            "• `/world` - World headlines\n"
            "• `/translate ru <text>` - Translate to Russian\n\n"
            "*Tips:*\n"
            "• Use quotes: `/news \"artificial intelligence\"`\n"
            "• Combine terms: `climate AND policy`\n"
            "• Exclude terms: `apple -fruit`\n\n"
            f"🌐 Web App: {self.site_url}"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command"""
        if not context.args:
            await update.message.reply_text("Please provide a search query. Example: /news technology")
            return
        
        query = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching for: *{query}*", parse_mode='Markdown')
        
        # Check for country filter
        country = None
        if 'country:' in query:
            parts = query.split()
            for part in parts:
                if part.startswith('country:'):
                    country = part.split(':')[1].upper()
                    query = query.replace(part, '').strip()
        
        # Try cache first
        cached = self.get_cached_news(query)
        if cached and cached.get('articles'):
            message = self.create_news_message(cached['articles'], query)
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
            return
        
        # Fetch fresh news
        results = self.fetch_news(query, country)
        if results and results.get('articles'):
            message = self.create_news_message(results['articles'], query)
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text(f"❌ No results found for '{query}'")
    
    async def trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trending command"""
        await update.message.reply_text("📈 Fetching trending topics...")
        
        results = self.fetch_trending()
        if results and results.get('trends'):
            message = self.create_trending_message(results['trends'])
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ No trending data available")
    
    async def russia_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /russia command - news about Russia in Russian"""
        await update.message.reply_text("🇷🇺 Поиск новостей о России...")
        
        results = self.fetch_news("Russia", "RU", 5)
        if results and results.get('articles'):
            # Translate titles to Russian
            message = "🇷🇺 *Новости о России*\n\n"
            for i, article in enumerate(results['articles'][:5], 1):
                title_ru = self.translate_text(article['title'], 'ru')
                message += f"*{i}. {title_ru}*\n"
                message += f"📰 {article['source']}\n"
                message += f"🔗 [Читать]({article['url']})\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ Новостей не найдено")
    
    async def world_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /world command - world headlines"""
        await update.message.reply_text("🌍 Fetching world headlines...")
        
        results = self.fetch_news("world news", max_records=5)
        if results and results.get('articles'):
            message = self.create_news_message(results['articles'], "World News")
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ No world news available")
    
    async def translate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /translate command"""
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /translate ru Hello world")
            return
        
        target_lang = context.args[0].lower()
        text = ' '.join(context.args[1:])
        
        await update.message.reply_text(f"🔄 Translating to {target_lang}...")
        
        translated = self.translate_text(text, target_lang)
        await update.message.reply_text(f"*Translation:*\n{translated}", parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        query = update.message.text
        
        if len(query) < 3:
            await update.message.reply_text("Please type a longer query (min 3 characters)")
            return
        
        # Treat as news search
        await self.news_command(update, context)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "trending":
            await self.trending_command(update, context)
        elif query.data == "russia":
            await self.russia_command(update, context)
    
    async def broadcast_update(self, application, new_articles):
        """Broadcast news update to all active chats"""
        # This would need chat IDs storage
        # For GitHub Actions, we'd need a database
        pass
    
    def run(self):
        """Run the bot (for polling mode)"""
        if not TELEGRAM_AVAILABLE:
            print("Error: python-telegram-bot not available")
            return
        
        application = Application.builder().token(self.token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("news", self.news_command))
        application.add_handler(CommandHandler("trending", self.trending_command))
        application.add_handler(CommandHandler("russia", self.russia_command))
        application.add_handler(CommandHandler("world", self.world_command))
        application.add_handler(CommandHandler("translate", self.translate_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("Starting Telegram bot...")
        application.run_polling()

def main():
    """Main function for GitHub Action"""
    print(f"GDELT News Bot - Running at {datetime.now()}")
    
    bot = GDELTNewsBot()
    
    # Check for mode
    if os.environ.get('BOT_MODE') == 'polling':
        # Run in polling mode (for long-running processes)
        bot.run()
    else:
        # Run in GitHub Action mode - just check updates
        has_updates, latest = bot.check_for_updates()
        
        if has_updates:
            print("📰 New articles available!")
            print(f"Latest timestamp: {latest.get('timestamp')}")
            print(f"Total articles: {latest.get('total', 0)}")
            
            # Here you could send notifications to Telegram
            # For now, just log
        else:
            print("No new articles since last check")

if __name__ == "__main__":
    main()
