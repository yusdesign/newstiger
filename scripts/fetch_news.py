#!/usr/bin/env python3
"""
News Fetcher using The Guardian API - Completely free, no limits!
This replaces the old GDELT fetcher entirely.
"""

import requests
import json
import os
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

class GuardianFetcher:
    def __init__(self):
        # Guardian API
        self.api_key = os.environ.get('GUARDIAN_API_KEY', '')
        self.base_url = "https://content.guardianapis.com"
        self.search_url = f"{self.base_url}/search"
        
        # Output directories
        self.output_dir = Path("news")
        self.search_dir = self.output_dir / "search"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.search_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'articles_fetched': 0,
            'errors': 0
        }
        
        # Country to section mapping
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
            'BR': 'world/brazil',
            'AU': 'australia-news',
            'CA': 'world/canada'
        }
        
        # Category to section mapping
        self.category_sections = {
            'technology': 'technology',
            'business': 'business',
            'sports': 'sport',
            'science': 'science',
            'health': 'wellness',
            'climate': 'environment',
            'politics': 'politics',
            'culture': 'culture'
        }
    
    def fetch_guardian(self, query=None, section=None, page_size=20, pages=1, tag=None):
        """
        Fetch from Guardian API
        This is our primary and only news source now
        """
        params = {
            'page-size': min(page_size, 50),  # Guardian max is 50
            'page': pages,
            'show-fields': 'headline,trailText,thumbnail,short-url,bodyText',
            'show-tags': 'contributor,publication',
            'show-elements': 'image',
            'show-refinements': 'all',
            'order-by': 'newest',
            'format': 'json'
        }
        
        if query:
            params['q'] = query
        if section:
            params['section'] = section
        if tag:
            params['tag'] = tag
        if self.api_key:
            params['api-key'] = self.api_key
        
        try:
            print(f"  📰 Fetching: {query or section}")
            response = requests.get(self.search_url, params=params, timeout=15)
            self.stats['api_calls'] += 1
            
            if response.status_code == 200:
                data = response.json()
                articles = self._format_articles(data, query or section)
                self.stats['articles_fetched'] += len(articles)
                return articles
            else:
                print(f"  ⚠️ Guardian error: {response.status_code} - {response.text}")
                self.stats['errors'] += 1
                return self._generate_fallback(query or section)
                
        except Exception as e:
            print(f"  ⚠️ Guardian exception: {e}")
            self.stats['errors'] += 1
            return self._generate_fallback(query or section)
    
    def _format_articles(self, data, source):
        """Format Guardian articles for JSON storage"""
        articles = []
        response = data.get('response', {})
        
        for result in response.get('results', []):
            fields = result.get('fields', {})
            
            # Get publication date
            web_date = result.get('webPublicationDate', '')
            
            # Extract country from section
            section_id = result.get('sectionId', '')
            country = self._section_to_country(section_id)
            
            # Get body text preview
            body = fields.get('bodyText', '')
            summary = body[:300] + '...' if body else fields.get('trailText', '')
            
            article = {
                'title': fields.get('headline', result.get('webTitle', 'No title')),
                'url': result.get('webUrl', '#'),
                'source': 'The Guardian',
                'date': self._format_date(web_date),
                'country': country,
                'section': result.get('sectionName', 'General'),
                'section_id': section_id,
                'summary': summary.replace('<p>', '').replace('</p>', '').strip(),
                'image': fields.get('thumbnail', ''),
                'api': 'guardian',
                'id': result.get('id', '')
            }
            
            # Only add if it has a title
            if article['title'] and article['title'] != 'No title':
                articles.append(article)
        
        return {
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles),
            'articles': articles,
            'api': 'Guardian'
        }
    
    def _section_to_country(self, section_id):
        """Map Guardian section to country code"""
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
            'world/brazil': 'BR',
            'world/canada': 'CA',
            'world/europe-news': 'EU',
            'world/middleeast': 'ME'
        }
        return country_map.get(section_id, 'Global')
    
    def _generate_fallback(self, query):
        """Generate fallback data when API fails"""
        print(f"  📦 Generating fallback for: {query}")
        
        articles = []
        topics = ['technology', 'business', 'politics', 'sports', 'science']
        
        for i in range(5):
            articles.append({
                'title': f"{query.title()} - Latest News Update",
                'url': 'https://theguardian.com',
                'source': 'The Guardian',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'country': self._extract_country_from_query(query),
                'section': 'General',
                'summary': f"Latest developments in {query}. Please check back soon for fresh articles.",
                'image': '',
                'api': 'guardian_fallback',
                'id': f'fallback-{i}'
            })
        
        return {
            'source': query,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles),
            'articles': articles,
            'api': 'Guardian (Fallback)'
        }
    
    def _extract_country_from_query(self, query):
        """Extract country code from query"""
        query_lower = query.lower()
        for code in ['RU', 'UA', 'US', 'GB', 'DE', 'FR']:
            if code.lower() in query_lower or query_lower.startswith(code.lower()):
                return code
        return 'Global'
    
    def _format_date(self, date_str):
        """Format ISO date to readable"""
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
    
    def save_search(self, data, name):
        """Save search results with safe filename"""
        safe_name = name.lower().replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')[:50]
        filename = f"{safe_name}.json"
        
        filepath = self.search_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 Saved search: {filename}")
    
    def run(self):
        """Main fetch routine - Guardian only"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting Guardian News Fetch at {datetime.now()}")
        print(f"📊 Guardian API: Unlimited • No rate limits")
        print(f"{'='*60}\n")
        
        # 1. RUSSIA NEWS - Most important for your bot
        print("\n🇷🇺 PHASE 1: RUSSIA NEWS")
        russia_news = self.fetch_guardian(section='world/russia', page_size=30)
        if russia_news:
            self.save_search(russia_news, 'russia')
            # Also save as country-specific
            self.save_search(russia_news, 'ru')
        
        time.sleep(2)
        
        # 2. UKRAINE NEWS
        print("\n🇺🇦 PHASE 2: UKRAINE NEWS")
        ukraine_news = self.fetch_guardian(section='world/ukraine', page_size=25)
        if ukraine_news:
            self.save_search(ukraine_news, 'ukraine')
            self.save_search(ukraine_news, 'ua')
        
        time.sleep(2)
        
        # 3. ALL COUNTRY SECTIONS
        print("\n🌍 PHASE 3: COUNTRY NEWS")
        for country_code, section in self.country_sections.items():
            print(f"\n  📍 {country_code} - {section}")
            news = self.fetch_guardian(section=section, page_size=20)
            if news:
                self.save_search(news, country_code.lower())
            time.sleep(random.uniform(1, 3))
        
        # 4. CATEGORY NEWS
        print("\n📰 PHASE 4: CATEGORY NEWS")
        for category, section in self.category_sections.items():
            print(f"\n  📌 {category}")
            news = self.fetch_guardian(section=section, page_size=25)
            if news:
                self.save_search(news, category)
                # Also save as JSON file for direct access
                self.save_json(news, f"{category}.json")
            time.sleep(random.uniform(1, 3))
        
        # 5. POPULAR SEARCHES
        print("\n🔍 PHASE 5: POPULAR SEARCHES")
        searches = [
            "artificial intelligence",
            "climate crisis",
            "technology",
            "business",
            "sports",
            "science",
            "health",
            "politics",
            "culture",
            "economy"
        ]
        
        for query in searches:
            print(f"\n  🔎 {query}")
            news = self.fetch_guardian(query=query, page_size=20)
            if news:
                self.save_search(news, query.replace(' ', '_'))
            time.sleep(random.uniform(1, 3))
        
        # 6. LATEST NEWS (for homepage)
        print("\n📰 PHASE 6: LATEST NEWS")
        latest = self.fetch_guardian(page_size=50)  # Get latest 50 articles
        if latest:
            self.save_json(latest, "latest.json")
        
        # 7. TRENDING (based on most recent)
        print("\n📈 PHASE 7: TRENDING TOPICS")
        if latest and latest.get('articles'):
            trends = []
            for i, article in enumerate(latest['articles'][:20]):
                trends.append({
                    'rank': i + 1,
                    'title': article['title'][:60],
                    'section': article['section'],
                    'date': article['date'][:10],
                    'url': article['url']
                })
            
            trending_data = {
                'timestamp': datetime.now().isoformat(),
                'total': len(trends),
                'trends': trends,
                'source': 'Guardian'
            }
            self.save_json(trending_data, "trending.json")
        
        # 8. INDEX FILE
        print("\n📋 PHASE 8: CREATING INDEX")
        index = {
            'last_update': datetime.now().isoformat(),
            'stats': self.stats,
            'countries': list(self.country_sections.keys()),
            'categories': list(self.category_sections.keys()),
            'searches': searches,
            'message': 'Powered by The Guardian API'
        }
        self.save_json(index, "index.json")
        
        print(f"\n{'='*60}")
        print(f"✅ Fetch complete at {datetime.now()}")
        print(f"📊 Stats: {self.stats}")
        print(f"{'='*60}")

if __name__ == "__main__":
    fetcher = GuardianFetcher()
    fetcher.run()
