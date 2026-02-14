#!/usr/bin/env python3
"""
News Fetcher using The Guardian API - Completely free, no daily limits!
Plus NewsAPI as backup
"""

import requests
import json
import os
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

class NewsFetcher:
    def __init__(self):
        # Guardian API (primary - unlimited)
        self.guardian_key = os.environ.get('GUARDIAN_API_KEY', '')  # Optional but recommended
        self.guardian_url = "https://content.guardianapis.com/search"
        
        # NewsAPI (backup - 100/day)
        self.newsapi_key = os.environ.get('NEWS_API_TOKEN', '')
        self.newsapi_url = "https://newsapi.org/v2/everything"
        self.newsapi_headlines = "https://newsapi.org/v2/top-headlines"
        
        self.output_dir = Path("news")
        self.search_dir = self.output_dir / "search"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.search_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            'guardian_calls': 0,
            'newsapi_calls': 0,
            'cache_hits': 0,
            'errors': 0
        }
        
        # Country to section mapping for Guardian
        self.country_sections = {
            'RU': 'world/russia',
            'UA': 'world/ukraine',
            'US': 'us-news',
            'GB': 'uk-news',
            'DE': 'world/germany',
            'FR': 'world/france',
            'JP': 'world/japan',
            'IN': 'world/india',
            'CN': 'world/china',
            'BR': 'world/brazil'
        }
    
    def fetch_guardian(self, query=None, section=None, page_size=10, pages=1):
        """Fetch from Guardian API (unlimited, primary source)"""
        
        params = {
            'page-size': page_size,
            'page': pages,
            'show-fields': 'headline,trailText,thumbnail,short-url',
            'show-tags': 'contributor',
            'show-elements': 'image',
            'format': 'json'
        }
        
        if query:
            params['q'] = query
        if section:
            params['section'] = section
        if self.guardian_key:
            params['api-key'] = self.guardian_key
        
        try:
            print(f"  📰 Fetching from Guardian: {query or section}")
            response = requests.get(self.guardian_url, params=params, timeout=15)
            self.stats['guardian_calls'] += 1
            
            if response.status_code == 200:
                data = response.json()
                return self._format_guardian_articles(data, query or section)
            else:
                print(f"  ⚠️ Guardian error: {response.status_code}")
                self.stats['errors'] += 1
                return None
                
        except Exception as e:
            print(f"  ⚠️ Guardian exception: {e}")
            self.stats['errors'] += 1
            return None
    
    def fetch_newsapi(self, query, country=None, page_size=10):
        """Fetch from NewsAPI (backup, rate-limited)"""
        
        params = {
            'apiKey': self.newsapi_key,
            'pageSize': page_size,
            'language': 'en',
            'sortBy': 'publishedAt'
        }
        
        if query:
            params['q'] = query
        if country:
            params['country'] = country.lower()
        
        try:
            print(f"  🔄 Fetching from NewsAPI: {query}")
            response = requests.get(self.newsapi_url, params=params, timeout=15)
            self.stats['newsapi_calls'] += 1
            
            if response.status_code == 200:
                data = response.json()
                return self._format_newsapi_articles(data, query)
            else:
                print(f"  ⚠️ NewsAPI error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  ⚠️ NewsAPI exception: {e}")
            return None
    
    def _format_guardian_articles(self, data, source):
        """Format Guardian articles for JSON storage"""
        articles = []
        
        for result in data.get('response', {}).get('results', []):
            fields = result.get('fields', {})
            
            articles.append({
                'title': fields.get('headline', result.get('webTitle', 'No title')),
                'url': result.get('webUrl', '#'),
                'source': 'The Guardian',
                'date': self._format_date(result.get('webPublicationDate', '')),
                'country': self._extract_country(result),
                'section': result.get('sectionName', 'General'),
                'summary': fields.get('trailText', '').replace('<p>', '').replace('</p>', '')[:300] + '...',
                'image': fields.get('thumbnail', ''),
                'api': 'guardian'
            })
        
        return {
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles),
            'articles': articles,
            'api': 'Guardian'
        }
    
    def _format_newsapi_articles(self, data, query):
        """Format NewsAPI articles for JSON storage"""
        articles = []
        
        for article in data.get('articles', [])[:15]:
            if article.get('title') and article.get('title') != '[Removed]':
                articles.append({
                    'title': article.get('title', 'No title'),
                    'url': article.get('url', '#'),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'date': self._format_date(article.get('publishedAt', '')),
                    'country': 'Global',
                    'summary': (article.get('description', '')[:300] + '...') if article.get('description') else '',
                    'image': article.get('urlToImage', ''),
                    'api': 'newsapi'
                })
        
        return {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles),
            'articles': articles,
            'api': 'NewsAPI'
        }
    
    def _extract_country(self, article):
        """Extract country from Guardian article tags/section"""
        section = article.get('sectionId', '')
        
        # Map Guardian sections to countries
        country_map = {
            'us-news': 'US',
            'uk-news': 'GB',
            'australia-news': 'AU',
            'world/russia': 'RU',
            'world/ukraine': 'UA',
            'world/germany': 'DE',
            'world/france': 'FR',
            'world/japan': 'JP',
            'world/india': 'IN',
            'world/china': 'CN',
            'world/brazil': 'BR'
        }
        
        return country_map.get(section, 'Global')
    
    def _format_date(self, date_str):
        """Format ISO date"""
        if not date_str:
            return 'Unknown'
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return date_str
    
    def save_json(self, data, filename):
        """Save data as JSON"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 Saved: {filename}")
    
    def save_search(self, data, query, country=None):
        """Save search results with safe filename"""
        safe_query = query.lower().replace(' ', '_')
        safe_query = ''.join(c for c in safe_query if c.isalnum() or c == '_')[:50]
        
        if country:
            filename = f"{safe_query}_{country.lower()}.json"
        else:
            filename = f"{safe_query}.json"
        
        filepath = self.search_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 Saved search: {filename}")
    
    def run(self):
        """Main fetch routine"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting News Fetch at {datetime.now()}")
        print(f"📊 Guardian API: Unlimited • NewsAPI: {self.stats['newsapi_calls']}/day")
        print(f"{'='*60}\n")
        
        # 1. Fetch Russia news (primary for your bot)
        print("\n🇷🇺 Phase 1: Russia News")
        russia_news = self.fetch_guardian(section='world/russia', page_size=20)
        if russia_news:
            self.save_search(russia_news, "russia", "RU")
        else:
            # Fallback to NewsAPI
            russia_news = self.fetch_newsapi("Russia", country="ru", page_size=15)
            if russia_news:
                self.save_search(russia_news, "russia", "RU")
        
        time.sleep(random.uniform(2, 4))
        
        # 2. Fetch top headlines by country
        print("\n🌍 Phase 2: Country News")
        for country_code, section in list(self.country_sections.items())[:8]:  # First 8 countries
            print(f"\n  📍 {country_code}")
            
            # Try Guardian first
            news = self.fetch_guardian(section=section, page_size=12)
            if news:
                self.save_search(news, country_code.lower(), country_code)
            else:
                # Fallback to NewsAPI
                news = self.fetch_newsapi(country_code, country=country_code.lower(), page_size=10)
                if news:
                    self.save_search(news, country_code.lower(), country_code)
            
            time.sleep(random.uniform(3, 6))
        
        # 3. Fetch popular searches
        print("\n🔍 Phase 3: Popular Searches")
        searches = [
            "technology",
            "artificial intelligence",
            "climate change",
            "business",
            "sports",
            "health",
            "science"
        ]
        
        for query in searches:
            print(f"\n  🔎 {query}")
            
            # Try Guardian first
            news = self.fetch_guardian(query=query, page_size=15)
            if news:
                self.save_search(news, query)
            else:
                # Fallback to NewsAPI
                news = self.fetch_newsapi(query, page_size=12)
                if news:
                    self.save_search(news, query)
            
            time.sleep(random.uniform(2, 5))
        
        # 4. Create trending data (from Guardian)
        print("\n📈 Phase 4: Trending Topics")
        trending = self.fetch_guardian(query="", page_size=30)  # Get latest articles
        if trending:
            # Convert to trending format
            trends = []
            for i, article in enumerate(trending['articles'][:15]):
                trends.append({
                    'date': article['date'][:10],
                    'value': 1000 - (i * 50),
                    'title': article['title'][:50]
                })
            
            trending_data = {
                'timestamp': datetime.now().isoformat(),
                'trends': trends,
                'source': 'Guardian'
            }
            self.save_json(trending_data, "trending.json")
        
        # 5. Create latest.json
        print("\n📰 Phase 5: Latest News")
        latest = self.fetch_guardian(page_size=25)
        if latest:
            self.save_json(latest, "latest.json")
        
        # 6. Create index file
        print("\n📋 Phase 6: Creating Index")
        index = {
            'last_update': datetime.now().isoformat(),
            'stats': self.stats,
            'countries': list(self.country_sections.keys()),
            'searches': searches
        }
        self.save_json(index, "index.json")
        
        print(f"\n{'='*60}")
        print(f"✅ Fetch complete at {datetime.now()}")
        print(f"📊 Stats: {self.stats}")
        print(f"{'='*60}")

if __name__ == "__main__":
    fetcher = NewsFetcher()
    fetcher.run()
