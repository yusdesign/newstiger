#!/usr/bin/env python3
"""
Guardian News Fetcher - Actually fetches real data
"""

import requests
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Your working API key
API_KEY = "1f962fc0-b843-4a63-acb9-770f4c24a86e"
BASE_URL = "https://content.guardianapis.com"

class GuardianFetcher:
    def __init__(self):
        self.api_key = API_KEY
        self.output_dir = Path("news")
        self.search_dir = self.output_dir / "search"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.search_dir.mkdir(exist_ok=True)
    
    def fetch_section(self, section, page_size=20):
        """Fetch articles from a specific section"""
        url = f"{BASE_URL}/search"
        params = {
            'section': section,
            'page-size': page_size,
            'show-fields': 'headline,trailText,thumbnail,bodyText',
            'show-tags': 'contributor',
            'order-by': 'newest',
            'api-key': self.api_key
        }
        
        print(f"  📰 Fetching section: {section}")
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._format_articles(data, section)
            else:
                print(f"  ⚠️ Error {response.status_code}")
                return None
        except Exception as e:
            print(f"  ⚠️ Exception: {e}")
            return None
    
    def fetch_search(self, query, page_size=20):
        """Search for articles by query"""
        url = f"{BASE_URL}/search"
        params = {
            'q': query,
            'page-size': page_size,
            'show-fields': 'headline,trailText,thumbnail,bodyText',
            'show-tags': 'contributor',
            'order-by': 'relevance',
            'api-key': self.api_key
        }
        
        print(f"  🔍 Searching: {query}")
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._format_articles(data, query)
            else:
                return None
        except Exception as e:
            print(f"  ⚠️ Exception: {e}")
            return None
    
    def _format_articles(self, data, source):
        """Format Guardian articles"""
        articles = []
        response = data.get('response', {})
        results = response.get('results', [])
        
        print(f"     Found {len(results)} articles")
        
        for result in results:
            fields = result.get('fields', {})
            
            # Get body text preview
            body = fields.get('bodyText', '')
            summary = body[:300] + '...' if body else fields.get('trailText', '')
            
            article = {
                'title': fields.get('headline', result.get('webTitle', 'No title')),
                'url': result.get('webUrl', '#'),
                'source': 'The Guardian',
                'date': result.get('webPublicationDate', ''),
                'country': self._section_to_country(result.get('sectionId', '')),
                'section': result.get('sectionName', 'News'),
                'section_id': result.get('sectionId', ''),
                'summary': summary.replace('<p>', '').replace('</p>', '').strip(),
                'image': fields.get('thumbnail', ''),
                'api': 'guardian',
                'id': result.get('id', '')
            }
            
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
        """Map section to country code"""
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
            'world/europe-news': 'EU',
            'world/middleeast': 'ME'
        }
        return country_map.get(section_id, 'Global')
    
    def save_json(self, data, filename):
        """Save data as JSON"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved: {filename}")
    
    def save_search(self, data, name):
        """Save search results"""
        safe_name = name.lower().replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')[:40]
        filename = f"{safe_name}.json"
        
        filepath = self.search_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved search: {filename}")
    
    def run(self):
        """Main fetch routine"""
        print(f"\n{'='*60}")
        print(f"🚀 Fetching Guardian News at {datetime.now()}")
        print(f"{'='*60}\n")
        
        # 1. RUSSIA NEWS
        print("\n🇷🇺 Russia News")
        russia = self.fetch_section('world/russia', 25)
        if russia:
            self.save_search(russia, 'russia')
        
        time.sleep(1)
        
        # 2. UKRAINE NEWS
        print("\n🇺🇦 Ukraine News")
        ukraine = self.fetch_section('world/ukraine', 25)
        if ukraine:
            self.save_search(ukraine, 'ukraine')
        
        time.sleep(1)
        
        # 3. US NEWS
        print("\n🇺🇸 US News")
        us = self.fetch_section('us-news', 25)
        if us:
            self.save_search(us, 'us')
        
        time.sleep(1)
        
        # 4. UK NEWS
        print("\n🇬🇧 UK News")
        uk = self.fetch_section('uk-news', 25)
        if uk:
            self.save_search(uk, 'gb')
        
        time.sleep(1)
        
        # 5. TECHNOLOGY
        print("\n💻 Technology")
        tech = self.fetch_section('technology', 25)
        if tech:
            self.save_search(tech, 'technology')
        
        time.sleep(1)
        
        # 6. WORLD NEWS (latest)
        print("\n🌍 World News")
        world = self.fetch_section('world', 30)
        if world:
            self.save_json(world, 'latest.json')
        
        time.sleep(1)
        
        # 7. TRENDING (based on most recent)
        print("\n📈 Trending")
        if world and world.get('articles'):
            trends = []
            for i, article in enumerate(world['articles'][:15]):
                trends.append({
                    'rank': i + 1,
                    'title': article['title'][:60],
                    'section': article['section'],
                    'date': article['date'][:10]
                })
            
            trending_data = {
                'timestamp': datetime.now().isoformat(),
                'trends': trends,
                'source': 'Guardian'
            }
            self.save_json(trending_data, 'trending.json')
        
        # 8. POPULAR SEARCHES
        print("\n🔍 Popular Searches")
        searches = [
            'climate change',
            'artificial intelligence',
            'business',
            'sports',
            'health',
            'politics'
        ]
        
        for query in searches:
            print(f"\n  {query}")
            results = self.fetch_search(query, 15)
            if results:
                self.save_search(results, query.replace(' ', '_'))
            time.sleep(1)
        
        # 9. INDEX
        print("\n📋 Creating Index")
        index = {
            'last_update': datetime.now().isoformat(),
            'message': 'Fresh Guardian news',
            'total_articles': sum(
                len(russia.get('articles', [])) if russia else 0,
                len(ukraine.get('articles', [])) if ukraine else 0,
                len(us.get('articles', [])) if us else 0,
                len(uk.get('articles', [])) if uk else 0,
                len(tech.get('articles', [])) if tech else 0,
                len(world.get('articles', [])) if world else 0
            )
        }
        self.save_json(index, 'index.json')
        
        print(f"\n{'='*60}")
        print(f"✅ Done at {datetime.now()}")
        print(f"{'='*60}")

if __name__ == "__main__":
    fetcher = GuardianFetcher()
    fetcher.run()
