#!/usr/bin/env python3
"""
Telegram Bot for GDELT News - With Caching and Multiple Endpoints
Responds to user commands with news from GDELT
"""

import os
import json
import requests
import time
import random
import hashlib
from datetime import datetime, timedelta
import urllib.parse
import logging
from pathlib import Path

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
    from telegram.error import TelegramError, RetryAfter
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
        
        # Log token preview
        token_preview = self.token[:5] + "..." + self.token[-5:]
        logger.info(f"Initializing bot with token: {token_preview}")
        
        # GitHub Pages base URL
        self.site_url = "https://yusdesign.github.io/newstiger"
        
        # Multiple GDELT endpoints for redundancy
        self.gdelt_endpoints = [
            "https://api.gdeltproject.org/api/v2/doc/doc",
            "https://api.gdeltproject.org/api/v2/doc/doc",  # Same endpoint but we'll try different params
            "https://api.gdeltproject.org/api/v2/summary/summary"  # Alternative endpoint
        ]
        
        # Translation API (multiple fallbacks)
        self.translate_apis = [
            {
                'name': 'libretranslate',
                'url': 'https://libretranslate.de/translate',
                'enabled': True
            },
            {
                'name': 'mymemory',
                'url': 'https://api.mymemory.translated.net/get',
                'enabled': True
            }
        ]
        
        # Cache system
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = 3600  # 1 hour default
        self.memory_cache = {}  # In-memory cache for fast access
        self.memory_cache_timeout = 300  # 5 minutes
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # Minimum 2 seconds between requests
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'errors': 0,
            'last_reset': datetime.now().isoformat()
        }
    
    def _rate_limit(self):
        """Ensure we don't hit APIs too fast"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _get_cache_key(self, query, country=None, endpoint_type='news'):
        """Generate cache key from parameters"""
        key_string = f"{endpoint_type}_{query}_{country}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key, max_age=None):
        """Get data from cache (memory first, then disk)"""
        # Check memory cache first
        if cache_key in self.memory_cache:
            cached_time, cached_data = self.memory_cache[cache_key]
            if time.time() - cached_time < self.memory_cache_timeout:
                logger.debug(f"Memory cache hit for {cache_key}")
                self.stats['cache_hits'] += 1
                return cached_data
        
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                cache_time = datetime.fromisoformat(cached['cached_at'])
                age = (datetime.now() - cache_time).total_seconds()
                
                if age < (max_age or self.cache_duration):
                    logger.debug(f"Disk cache hit for {cache_key} (age: {age:.0f}s)")
                    # Also store in memory cache
                    self.memory_cache[cache_key] = (time.time(), cached['data'])
                    self.stats['cache_hits'] += 1
                    return cached['data']
                else:
                    logger.debug(f"Cache expired for {cache_key} (age: {age:.0f}s)")
                    cache_file.unlink()  # Remove expired cache
            except Exception as e:
                logger.error(f"Error reading cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key, data, cache_duration=None):
        """Save data to cache (both memory and disk)"""
        # Memory cache
        self.memory_cache[cache_key] = (time.time(), data)
        
        # Disk cache
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'expires_in': cache_duration or self.cache_duration,
                'data': data
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.debug(f"Saved to cache: {cache_key}")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
    
    def fetch_news(self, query, country=None, max_records=5, retry=3):
        """Fetch news from GDELT with multiple endpoints and retry logic"""
        
        # Check cache first
        cache_key = self._get_cache_key(query, country, 'news')
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Returning cached news for: {query}")
            return cached
        
        # Prepare query with country
        full_query = query
        if country:
            full_query = f"{query} sourcecountry:{country}"
        
        # Try different endpoints and parameters
        endpoint_configs = [
            {
                'url': self.gdelt_endpoints[0],
                'params': {
                    'query': full_query,
                    'mode': 'artlist',
                    'format': 'json',
                    'maxrecords': max_records,
                    'sort': 'date',
                    'timespan': '24h'  # Last 24 hours
                }
            },
            {
                'url': self.gdelt_endpoints[0],
                'params': {
                    'query': full_query,
                    'mode': 'artlist',
                    'format': 'json',
                    'maxrecords': max_records,
                    'sort': 'relevance',  # Try relevance instead of date
                }
            },
            {
                'url': self.gdelt_endpoints[2],  # Summary endpoint
                'params': {
                    'query': full_query,
                    'mode': 'summary',
                    'format': 'json',
                }
            }
        ]
        
        # Add random delay to avoid rate limiting
        self._rate_limit()
        
        for attempt in range(retry):
            for config in endpoint_configs:
                try:
                    logger.info(f"Fetching news (attempt {attempt+1}) with endpoint: {config['url']}")
                    
                    response = requests.get(
                        config['url'], 
                        params=config['params'], 
                        timeout=15,
                        headers={'User-Agent': 'NewsTigerBot/1.0'}
                    )
                    
                    self.stats['api_calls'] += 1
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Format based on endpoint type
                        if 'summary' in config['url']:
                            formatted = self._format_summary(data, query, country)
                        else:
                            formatted = self._format_articles(data, query, country)
                        
                        if formatted and formatted.get('articles'):
                            # Save to cache
                            self._save_to_cache(cache_key, formatted)
                            logger.info(f"Successfully fetched {len(formatted['articles'])} articles")
                            return formatted
                    
                    elif response.status_code == 429:
                        wait_time = (2 ** attempt) * 5 + random.uniform(1, 5)
                        logger.warning(f"Rate limited (429). Waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    
                    else:
                        logger.warning(f"Endpoint returned {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout on attempt {attempt+1}")
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Connection error on attempt {attempt+1}")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                
                # Small delay between endpoint attempts
                time.sleep(random.uniform(1, 3))
            
            # Exponential backoff between retry attempts
            if attempt < retry - 1:
                wait_time = (2 ** attempt) * 10 + random.uniform(5, 10)
                logger.info(f"All endpoints failed, waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
        
        # If all attempts fail, try to get from GitHub Pages cache
        logger.warning("All API attempts failed, trying GitHub Pages cache")
        github_cache = self._fetch_from_github_pages(query, country)
        if github_cache:
            return github_cache
        
        # Return None if everything fails
        self.stats['errors'] += 1
        return None
    
    def _fetch_from_github_pages(self, query, country=None):
        """Try to fetch cached news from GitHub Pages"""
        try:
            # Create filename like in your GitHub Action
            safe_query = query.lower().replace(' ', '_')
            safe_query = ''.join(c for c in safe_query if c.isalnum() or c == '_')[:50]
            
            if country:
                filename = f"{safe_query}_{country.lower()}.json"
            else:
                filename = f"{safe_query}.json"
            
            url = f"{self.site_url}/news/search/{filename}"
            logger.info(f"Trying GitHub Pages cache: {url}")
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Found in GitHub Pages cache: {len(data.get('articles', []))} articles")
                return data
        except Exception as e:
            logger.error(f"GitHub Pages cache error: {e}")
        
        return None
    
    def fetch_trending(self, hours=24):
        """Fetch trending topics with caching"""
        cache_key = self._get_cache_key('trending', str(hours), 'trending')
        cached = self._get_from_cache(cache_key, max_age=1800)  # 30 minutes for trending
        if cached:
            return cached
        
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        params = {
            'query': '*',
            'mode': 'timelinevol',
            'format': 'json',
            'startdatetime': start_date.strftime('%Y%m%d%H%M%S'),
            'enddatetime': end_date.strftime('%Y%m%d%H%M%S'),
            'maxrecords': 30
        }
        
        self._rate_limit()
        
        try:
            logger.info("Fetching trending topics")
            response = requests.get(self.gdelt_endpoints[0], params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                formatted = self._format_trending(data)
                self._save_to_cache(cache_key, formatted, max_age=1800)
                return formatted
            else:
                logger.error(f"Trending API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching trending: {e}")
        
        return self._generate_mock_trending()
    
    def translate_text(self, text, target_lang='ru'):
        """Translate text using multiple translation APIs with caching"""
        if not text or len(text) < 3 or target_lang == 'none':
            return text
        
        # Check translation cache
        cache_key = self._get_cache_key(text, target_lang, 'translation')
        cached = self._get_from_cache(cache_key, max_age=86400)  # 24 hours for translations
        if cached:
            return cached
        
        # Try different translation APIs
        for api in self.translate_apis:
            if not api['enabled']:
                continue
            
            try:
                self._rate_limit()
                
                if api['name'] == 'libretranslate':
                    response = requests.post(api['url'], json={
                        'q': text,
                        'source': 'auto',
                        'target': target_lang,
                        'format': 'text'
                    }, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        translated = data.get('translatedText', text)
                        self._save_to_cache(cache_key, translated, max_age=86400)
                        return translated
                
                elif api['name'] == 'mymemory':
                    response = requests.get(api['url'], params={
                        'q': text,
                        'langpair': f'auto|{target_lang}'
                    }, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        translated = data.get('responseData', {}).get('translatedText', text)
                        if translated and translated != text:
                            self._save_to_cache(cache_key, translated, max_age=86400)
                            return translated
                
            except Exception as e:
                logger.warning(f"Translation API {api['name']} failed: {e}")
                continue
        
        return text
    
    def _format_articles(self, raw_data, query, country=None):
        """Format articles for response"""
        articles = []
        
        for article in raw_data.get('articles', [])[:10]:
            articles.append({
                'title': article.get('title', 'No title'),
                'url': article.get('url', '#'),
                'source': article.get('domain', 'Unknown'),
                'date': self._format_date(article.get('seendate', '')),
                'country': article.get('sourcecountry', 'Unknown'),
                'language': article.get('language', 'Unknown'),
                'summary': article.get('content', '')[:200] + '...' if article.get('content') else '',
                'themes': article.get('themes', [])[:3]
            })
        
        return {
            'query': query,
            'country': country,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles),
            'articles': articles,
            'source': 'GDELT API'
        }
    
    def _format_summary(self, raw_data, query, country=None):
        """Format summary endpoint response"""
        # Convert summary format to articles
        articles = []
        
        # This is a simplified conversion - adjust based on actual summary format
        if 'summary' in raw_data:
            articles.append({
                'title': f"Summary for: {query}",
                'url': self.site_url,
                'source': 'GDELT Summary',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'country': country or 'Global',
                'summary': raw_data.get('summary', 'No summary available'),
                'themes': []
            })
        
        return {
            'query': query,
            'country': country,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles),
            'articles': articles,
            'source': 'GDELT Summary'
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
            'timestamp': datetime.now().isoformat(),
            'trends': trends,
            'source': 'GDELT API'
        }
    
    def _generate_mock_trending(self):
        """Generate mock trending data as fallback"""
        trends = []
        now = datetime.now()
        
        for i in range(10):
            date = now - timedelta(hours=i)
            trends.append({
                'date': date.strftime('%Y%m%d%H'),
                'value': 1000 - (i * 80) + random.randint(-20, 20)
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trends': trends,
            'source': 'Mock Data (API Unavailable)'
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
    
    def get_stats(self):
        """Get bot statistics"""
        self.stats['cache_size'] = len(self.memory_cache)
        self.stats['disk_cache_files'] = len(list(self.cache_dir.glob('*.json')))
        return self.stats
    
    # ==================== TELEGRAM COMMAND HANDLERS ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        logger.info(f"Start command from user: {user.username or user.id}")
        
        welcome = (
            f"👋 *Welcome to NewsTiger Bot!*\n\n"
            f"Get latest news from thousands of global sources.\n\n"
            f"*Commands:*\n"
            f"• `/news <query>` - Search news\n"
            f"• `/trending` - Trending topics\n"
            f"• `/russia` - News about Russia (in Russian)\n"
            f"• `/world` - World headlines\n"
            f"• `/help` - Show help\n"
            f"• `/stats` - Bot statistics\n\n"
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
            "📚 *NewsTiger Bot Help*\n\n"
            "*Search Commands:*\n"
            "• `/news technology` - Search for technology news\n"
            "• `/news \"climate change\"` - Use quotes for exact phrase\n"
            "• `/news AI country:RU` - Filter by country (RU, US, GB, etc.)\n\n"
            "*Quick Commands:*\n"
            "• `/trending` - What's trending now\n"
            "• `/russia` - News about Russia (in Russian)\n"
            "• `/world` - World headlines\n"
            "• `/stats` - Bot statistics\n\n"
            "*Tips:*\n"
            "• Results are cached for 1 hour to be efficient\n"
            "• If API is busy, try again in a few minutes\n"
            "• Web version has more features and translation\n\n"
            f"🌐 Web App: {self.site_url}"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        stats = self.get_stats()
        message = (
            f"📊 *Bot Statistics*\n\n"
            f"API Calls: {stats['api_calls']}\n"
            f"Cache Hits: {stats['cache_hits']}\n"
            f"Errors: {stats['errors']}\n"
            f"Memory Cache: {stats['cache_size']} items\n"
            f"Disk Cache: {stats['disk_cache_files']} files\n"
            f"Last Reset: {stats['last_reset'][:19]}\n\n"
            f"Cache Duration: {self.cache_duration//3600}h\n"
            f"Request Interval: {self.min_request_interval}s"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /news command"""
        if not context.args:
            await update.message.reply_text(
                "Please provide a search query.\n"
                "Example: `/news technology`\n"
                "Example: `/news climate change country:RU`",
                parse_mode='Markdown'
            )
            return
        
        query = ' '.join(context.args)
        logger.info(f"News search: {query} from user {update.effective_user.username}")
        
        await update.message.reply_text(f"🔍 Searching for: *{query}*", parse_mode='Markdown')
        
        # Parse country filter
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
        
        # Fetch news
        results = self.fetch_news(query, country)
        
        if results and results.get('articles'):
            articles = results['articles']
            
            # Prepare message
            source_info = f" (from {results.get('source', 'GDELT')})"
            message = f"📰 *News for: {query}*{source_info}\n\n"
            
            for i, article in enumerate(articles[:5], 1):
                # Escape special characters for Markdown
                title = article['title'].replace('*', '\\*').replace('_', '\\_').replace('[', '\\[')
                message += f"*{i}. {title}*\n"
                message += f"📰 Source: {article['source']}\n"
                message += f"🌍 Country: {article['country']}\n"
                message += f"📅 {article['date']}\n"
                message += f"🔗 [Read more]({article['url']})\n\n"
            
            message += f"\n🔍 More at: {self.site_url}?q={urllib.parse.quote(query)}"
            if country:
                message += f"&country={country}"
            
            # Split long messages
            if len(message) > 4000:
                parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for part in parts:
                    await update.message.reply_text(part, parse_mode='Markdown', disable_web_page_preview=True)
            else:
                await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            # Friendly error message
            error_msg = (
                f"😔 *No news found for '{query}'*\n\n"
                f"This could be because:\n"
                f"• The GDELT API is temporarily busy\n"
                f"• No recent articles match your query\n"
                f"• The country filter is too specific\n\n"
                f"Try:\n"
                f"• Using a simpler query\n"
                f"• Removing the country filter\n"
                f"• Checking the [web version]({self.site_url})\n"
                f"• Trying again in a few minutes"
            )
            await update.message.reply_text(error_msg, parse_mode='Markdown')
    
    async def trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trending command"""
        logger.info(f"Trending command from user: {update.effective_user.username}")
        
        await update.message.reply_text("📈 Fetching trending topics...")
        
        results = self.fetch_trending()
        if results and results.get('trends'):
            trends = results['trends']
            source_info = f" (from {results.get('source', 'GDELT')})"
            message = f"📈 *Trending Topics (Last 24h)*{source_info}\n\n"
            
            for i, trend in enumerate(trends[:10], 1):
                message += f"{i}. {trend['date']} - Volume: {trend['value']:,}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "😔 *No trending data available*\n\n"
                "The API might be busy. Try again in a few minutes.",
                parse_mode='Markdown'
            )
    
    async def russia_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /russia command - news about Russia in Russian"""
        logger.info(f"Russia command from user: {update.effective_user.username}")
        
        await update.message.reply_text("🇷🇺 Поиск новостей о России...")
        
        results = self.fetch_news("Russia", "RU", max_records=5)
        
        if results and results.get('articles'):
            articles = results['articles']
            source_info = f" (from {results.get('source', 'GDELT')})"
            message = f"🇷🇺 *Новости о России*{source_info}\n\n"
            
            for i, article in enumerate(articles[:5], 1):
                # Translate title to Russian
                title_ru = self.translate_text(article['title'], 'ru')
                title_ru = title_ru.replace('*', '\\*').replace('_', '\\_')
                message += f"*{i}. {title_ru}*\n"
                message += f"📰 {article['source']}\n"
                message += f"🔗 [Читать]({article['url']})\n\n"
            
            message += f"\n🔍 Больше на сайте: {self.site_url}?q=Russia&country=RU"
            
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            error_msg = (
                "😔 *Временно недоступно*\n\n"
                "Новости временно не загружаются из-за технических причин.\n\n"
                "Попробуйте:\n"
                "• повторить через 5-10 минут\n"
                "• посмотреть новости на [нашем сайте]({self.site_url}?q=Russia&country=RU)\n\n"
                "Мы уже работаем над восстановлением сервиса!"
            )
            await update.message.reply_text(error_msg, parse_mode='Markdown')
    
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
            await update.message.reply_text(
                "😔 *No world news available*\n\n"
                "The API might be busy. Try again in a few minutes.",
                parse_mode='Markdown'
            )
    
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
        
        logger.info("=" * 50)
        logger.info("Starting NewsTiger Bot in POLLING mode")
        logger.info(f"Cache directory: {self.cache_dir.absolute()}")
        logger.info("=" * 50)
        
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
            application.add_handler(CommandHandler("stats", self.stats_command))
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
            # Check if we can reach GDELT
            response = requests.get(
                self.gdelt_endpoints[0],
                params={'query': 'test', 'mode': 'artlist', 'format': 'json', 'maxrecords': 1},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("✅ GDELT API is reachable")
                
                # Check GitHub Pages cache
                pages_response = requests.get(f"{self.site_url}/news/latest.json", timeout=5)
                if pages_response.status_code == 200:
                    data = pages_response.json()
                    logger.info(f"✅ GitHub Pages cache: {data.get('timestamp')}")
                    return True
            else:
                logger.warning(f"⚠️ GDELT API returned {response.status_code}")
                
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
            bot.run_polling()
        else:
            # Check mode for GitHub Actions
            bot.check_updates()
            
            # Print stats
            stats = bot.get_stats()
            logger.info(f"Stats: {stats}")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
