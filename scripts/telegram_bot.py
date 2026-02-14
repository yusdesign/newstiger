#!/usr/bin/env python3
"""
Telegram Bot for GDELT News - Responds to user commands
"""

import os
import json
import requests
import time
import logging
import asyncio
from datetime import datetime, timedelta
import urllib.parse

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Try to import telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    TELEGRAM_AVAILABLE = False
    logger.error(f"Failed to import telegram: {e}")
    logger.error("Install with: pip install python-telegram-bot==20.7")

class GDELTNewsBot:
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        logger.info(f"Initializing bot with token: {self.token[:5]}...")
        
        # GitHub Pages base URL
        self.site_url = "https://yusdesign.github.io/newstiger"
        
        # GDELT API
        self.gdelt_api = "https://api.gdeltproject.org/api/v2/doc/doc"
        
        # Translation API
        self.translate_api = "https://libretranslate.de/translate"
        
    def fetch_news(self, query, country=None, max_records=5, retry=3):
        """Fetch news from GDELT with retry logic"""
        params = {
            'query': query,
            'mode': 'artlist',
            'format': 'json',
            'maxrecords': max_records,
            'sort': 'date'
        }
        
        if country:
            params['sourcecountry'] = country
        
        logger.info(f"Fetching news for: {query} (country: {country})")
        
        for attempt in range(retry):
            try:
                response = requests.get(self.gdelt_api, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._format_articles(data, query)
                elif response.status_code == 429:
                    wait_time = (2 ** attempt) * 5  # 5, 10, 20 seconds
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"GDELT API error: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error fetching news (attempt {attempt+1}): {e}")
                if attempt < retry - 1:
                    time.sleep(2 ** attempt * 2)
                else:
                    return None
        
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
        
        logger.info("Fetching trending topics")
        
        try:
            response = requests.get(self.gdelt_api, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._format_trending(data)
            return None
        except Exception as e:
            logger.error(f"Error fetching trending: {e}")
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
            logger.error(f"Translation error: {e}")
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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        logger.info(f"Start command from user: {update.effective_user.username}")
        
        welcome = (
            "👋 *Welcome to GDELT News Bot!*\n\n"
            "Get latest news from thousands of global sources.\n\n"
            "*Commands:*\n"
            "• `/news <query>` - Search news\n"
            "• `/trending` - Trending topics\n"
            "• `/russia` - News about Russia (in Russian)\n"
            "• `/world` - World headlines\n"
            "• `/help` - Show help\n\n"
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
        logger.info(f"Help command from user: {update.effective_user.username}")
        
        help_text = (
            "📚 *GDELT Bot Help*\n\n"
            "*Search Commands:*\n"
            "• `/news technology` - Search for technology news\n"
            "• `/news \"climate change\"` - Use quotes for exact phrase\n"
            "• `/news AI country:US` - Filter by country\n\n"
            "*Quick Commands:*\n"
            "• `/trending` - What's trending now\n"
            "• `/russia` - News about Russia (in Russian)\n"
            "• `/world` - World headlines\n\n"
            "*Tips:*\n"
            "• Combine terms: `climate AND policy`\n"
            "• Exclude terms: `apple -fruit`\n\n"
            f"🌐 Web App: {self.site_url}"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide a search query.\n"
                "Example: `/news technology`\n"
                "Example: `/news climate change country:US`",
                parse_mode='Markdown'
            )
            return
        
        query = ' '.join(context.args)
        logger.info(f"News search: {query} from user {update.effective_user.username}")
        
        await update.message.reply_text(f"🔍 Searching for: *{query}*", parse_mode='Markdown')
        
        # Check for country filter
        country = None
        if 'country:' in query:
            parts = query.split()
            filtered_parts = []
            for part in parts:
                if part.startswith('country:'):
                    country = part.split(':')[1].upper()
                else:
                    filtered_parts.append(part)
            query = ' '.join(filtered_parts)
        
        # Fetch fresh news
        results = self.fetch_news(query, country)
        
        if results and results.get('articles'):
            articles = results['articles']
            message = f"📰 *News for: {query}*\n\n"
            
            for i, article in enumerate(articles[:5], 1):
                # Escape special characters for Markdown
                title = article['title'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[')
                message += f"*{i}. {title}*\n"
                message += f"📰 Source: {article['source']}\n"
                message += f"🌍 Country: {article['country']}\n"
                message += f"📅 {article['date']}\n"
                message += f"🔗 [Read more]({article['url']})\n\n"
            
            message += f"\n🔍 More at: {self.site_url}?q={urllib.parse.quote(query)}"
            
            # Split long messages
            if len(message) > 4000:
                parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for part in parts:
                    await update.message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text(f"❌ No results found for '{query}'")
    
    async def trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trending command"""
        logger.info(f"Trending command from user: {update.effective_user.username}")
        
        await update.message.reply_text("📈 Fetching trending topics...")
        
        results = self.fetch_trending()
        if results and results.get('trends'):
            trends = results['trends']
            message = "📈 *Trending Topics (Last 24h)*\n\n"
            
            for i, trend in enumerate(trends[:10], 1):
                message += f"{i}. {trend['date']} - Volume: {trend['value']:,}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ No trending data available")
    
    async def russia_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /russia command - news about Russia in Russian"""
        logger.info(f"Russia command from user: {update.effective_user.username}")
        
        await update.message.reply_text("🇷🇺 Поиск новостей о России...")
        
        results = self.fetch_news("Russia", "RU", 5)
        if results and results.get('articles'):
            message = "🇷🇺 *Новости о России*\n\n"
            for i, article in enumerate(results['articles'][:5], 1):
                # Try to translate title to Russian
                title_ru = self.translate_text(article['title'], 'ru')
                title_ru = title_ru.replace('*', '\\*').replace('_', '\\_')
                message += f"*{i}. {title_ru}*\n"
                message += f"📰 {article['source']}\n"
                message += f"🔗 [Читать]({article['url']})\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ Новостей не найдено")
    
    async def world_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /world command - world headlines"""
        logger.info(f"World command from user: {update.effective_user.username}")
        
        await update.message.reply_text("🌍 Fetching world headlines...")
        
        results = self.fetch_news("world news", max_records=5)
        if results and results.get('articles'):
            articles = results['articles']
            message = "🌍 *World Headlines*\n\n"
            
            for i, article in enumerate(articles[:5], 1):
                title = article['title'].replace('*', '\\*').replace('_', '\\_')
                message += f"*{i}. {title}*\n"
                message += f"📰 {article['source']} | 🌍 {article['country']}\n"
                message += f"🔗 [Read more]({article['url']})\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text("❌ No world news available")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        query = update.message.text
        logger.info(f"Message from {update.effective_user.username}: {query[:50]}...")
        
        if len(query) < 3:
            await update.message.reply_text("Please type a longer query (min 3 characters)")
            return
        
        # Treat as news search
        context.args = query.split()
        await self.news_command(update, context)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        logger.info(f"Button callback: {query.data} from {update.effective_user.username}")
        
        if query.data == "trending":
            await self.trending_command(update, context)
        elif query.data == "russia":
            await self.russia_command(update, context)
    
    def run_polling(self):
        """Run bot in polling mode"""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot not available")
            return
        
        logger.info("Starting bot in POLLING mode...")
        
        try:
            # Build application
            application = Application.builder().token(self.token).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("help", self.help_command))
            application.add_handler(CommandHandler("news", self.news_command))
            application.add_handler(CommandHandler("trending", self.trending_command))
            application.add_handler(CommandHandler("russia", self.russia_command))
            application.add_handler(CommandHandler("world", self.world_command))
            application.add_handler(CallbackQueryHandler(self.button_callback))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Start polling
            logger.info("Bot is polling for updates...")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
    
    def check_updates(self):
        """Just check for new articles (GitHub Action mode)"""
        logger.info("Running in check mode")
        try:
            response = requests.get(f"{self.site_url}/news/latest.json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Latest news timestamp: {data.get('timestamp')}")
                logger.info(f"Total articles: {len(data.get('articles', []))}")
                return True
        except Exception as e:
            logger.error(f"Check failed: {e}")
        return False

def main():
    """Main function"""
    mode = os.environ.get('BOT_MODE', 'check')
    logger.info(f"Starting bot in {mode} mode")
    
    try:
        bot = GDELTNewsBot()
        
        if mode == 'polling':
            # Run in polling mode (for long-running processes)
            logger.info("=" * 50)
            logger.info("BOT IS RUNNING - Send commands to @YourBotName")
            logger.info("=" * 50)
            bot.run_polling()
        else:
            # Run in check mode (for GitHub Actions)
            bot.check_updates()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
