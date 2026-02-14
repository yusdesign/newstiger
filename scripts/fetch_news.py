#!/usr/bin/env python3
"""
GDELT News Fetcher - With random delays to avoid rate limiting
"""

import requests
import json
import os
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

class GDELTFetcher:
    def __init__(self):
        self.api_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.output_dir = Path("news")
        self.search_dir = self.output_dir / "search"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.search_dir.mkdir(exist_ok=True)
        
        # Track last request time for rate limiting
        self.last_request_time = 0
        self.min_request_interval = 3  # Minimum 3 seconds between requests
        
        # Statistics
        self.stats = {
            'requests_made': 0,
            'rate_limited': 0,
            'successful': 0
        }
    
    def _rate_limit(self):
        """Ensure we don't hit API too fast"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            # Add random jitter
            sleep_time += random.uniform(1, 5)
            print(f"  Rate limiting: sleeping {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _random_delay(self, min_seconds=2, max_seconds=8):
        """Add random delay between operations"""
        delay = random.uniform(min_seconds, max_seconds)
        print(f"  Adding random delay: {delay:.1f}s...")
        time.sleep(delay)
    
    def fetch_news(self, query, max_records=25, country=None, retry=3):
        """Fetch news from GDELT with retry logic and delays"""
        
        params = {
            'query': query,
            'mode': 'artlist',
            'format': 'json',
            'maxrecords': max_records,
            'sort': 'date'
        }
        
        if country:
            params['sourcecountry'] = country
        
        # Apply rate limiting
        self._rate_limit()
        
        for attempt in range(retry):
            try:
                print(f"  Fetching: {query} ({country if country else 'all'}) - attempt {attempt+1}")
                
                # Add jitter before request
                time.sleep(random.uniform(0.5, 2))
                
                response = requests.get(self.api_url, params=params, timeout=30)
                self.stats['requests_made'] += 1
                
                if response.status_code == 200:
                    self.stats['successful'] += 1
                    print(f"  ✅ Success: {response.status_code}")
                    return self._format_articles(response.json(), query, country)
                    
                elif response.status_code == 429:
                    self.stats['rate_limited'] += 1
                    wait_time = (2 ** attempt) * 15 + random.uniform(5, 20)
                    print(f"  ⚠️ Rate limited (429). Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                    
                else:
                    print(f"  ⚠️ API error: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"  ⚠️ Timeout on attempt {attempt+1}")
            except requests.exceptions.ConnectionError:
                print(f"  ⚠️ Connection error on attempt {attempt+1}")
            except Exception as e:
                print(f"  ⚠️ Exception: {e}")
            
            # Exponential backoff between retries
            if attempt < retry - 1:
                wait_time = (2 ** attempt) * 10 + random.uniform(5, 15)
                print(f"  Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)
        
        print(f"  ❌ All attempts failed for {query}")
        return None
    
    def fetch_trending(self, hours=24):
        """Fetch trending topics with delays"""
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
        
        # Apply rate limiting
        self._rate_limit()
        
        try:
            print("📈 Fetching trending topics...")
            response = requests.get(self.api_url, params=params, timeout=30)
            
            if response.status_code == 200:
                return self._format_trending(response.json())
            elif response.status_code == 429:
                print("  ⚠️ Rate limited on trending, waiting 60s...")
                time.sleep(60)
                # Try one more time
                response = requests.get(self.api_url, params=params, timeout=30)
                if response.status_code == 200:
                    return self._format_trending(response.json())
            
        except Exception as e:
            print(f"  ⚠️ Trending error: {e}")
        
        return self._generate_mock_trending()
    
    def _format_articles(self, raw_data, query, country=None):
        """Format articles for JSON storage"""
        articles = []
        
        for article in raw_data.get('articles', [])[:25]:
            articles.append({
                'title': article.get('title', 'No title'),
                'url': article.get('url', '#'),
                'source': article.get('domain', 'Unknown'),
                'date': self._format_date(article.get('seendate', '')),
                'country': article.get('sourcecountry', 'Unknown'),
                'language': article.get('language', 'Unknown'),
                'summary': (article.get('content', '')[:300] + '...') if article.get('content') else '',
                'themes': article.get('themes', [])[:5]
            })
        
        return {
            'query': query,
            'country': country,
            'timestamp': datetime.now().isoformat(),
            'total': len(articles),
            'articles': articles
        }
    
    def _format_trending(self, raw_data):
        """Format trending data"""
        trends = []
        
        for item in raw_data.get('timeline', [])[:30]:
            trends.append({
                'date': item.get('date', ''),
                'value': item.get('value', 0)
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trends': trends
        }
    
    def _generate_mock_trending(self):
        """Generate mock trending data as fallback"""
        trends = []
        now = datetime.now()
        
        for i in range(15):
            date = now - timedelta(hours=i)
            trends.append({
                'date': date.strftime('%Y%m%d%H'),
                'value': 1000 - (i * 50) + random.randint(-20, 20)
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trends': trends,
            'note': 'Mock data - API temporarily unavailable'
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
    
    def save_json(self, data, filename):
        """Save data as JSON"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  💾 Saved: {filename}")
    
    def save_search(self, data, query, country=None):
        """Save search results with safe filename"""
        # Create safe filename
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
        """Main fetch routine with strategic delays"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting GDELT fetch at {datetime.now()}")
        print(f"{'='*60}\n")
        
        # Initial random delay to spread out actions
        initial_delay = random.uniform(10, 30)
        print(f"Initial random delay: {initial_delay:.1f}s")
        time.sleep(initial_delay)
        
        # 1. Fetch trending topics
        print("\n📈 Phase 1: Trending Topics")
        trending = self.fetch_trending()
        if trending:
            self.save_json(trending, "trending.json")
        
        # Longer delay after trending
        self._random_delay(5, 15)
        
        # 2. Fetch latest technology news
        print("\n📰 Phase 2: Technology News")
        tech_news = self.fetch_news("technology", max_records=30)
        if tech_news:
            self.save_json(tech_news, "latest.json")
            self.save_search(tech_news, "technology")
        
        self._random_delay(8, 20)
        
        # 3. Fetch country-specific news
        print("\n🌍 Phase 3: Country-Specific News")
        country_searches = [
            ("Russia", "RU"),
            ("Ukraine", "UA"),
            ("USA", "US"),
            ("UK", "GB"),
            ("Germany", "DE"),
            ("France", "FR"),
            ("China", "CN"),
            ("Japan", "JP"),
            ("India", "IN"),
            ("Brazil", "BR"),
        ]
        
        for idx, (query, country) in enumerate(country_searches):
            print(f"\n  {idx+1}/{len(country_searches)}: {query} ({country})")
            
            # Add delay between each country request
            if idx > 0:
                delay = random.uniform(5, 15)
                print(f"  Waiting {delay:.1f}s before next country...")
                time.sleep(delay)
            
            news = self.fetch_news(query, max_records=20, country=country)
            if news:
                self.save_search(news, query, country)
        
        self._random_delay(10, 25)
        
        # 4. Fetch popular searches
        print("\n🔍 Phase 4: Popular Searches")
        popular_searches = [
            ("climate change", None),
            ("artificial intelligence", None),
            ("business", None),
            ("sports", None),
            ("health", None),
            ("election", None),
            ("technology", "US"),
            ("technology", "GB"),
            ("technology", "DE"),
            ("war", None),
            ("peace", None),
            ("economy", None),
        ]
        
        for idx, (query, country) in enumerate(popular_searches):
            print(f"\n  {idx+1}/{len(popular_searches)}: {query} {f'({country})' if country else ''}")
            
            # Add delay between searches
            if idx > 0:
                delay = random.uniform(4, 12)
                print(f"  Waiting {delay:.1f}s before next search...")
                time.sleep(delay)
            
            news = self.fetch_news(query, max_records=15, country=country)
            if news:
                self.save_search(news, query, country)
        
        # 5. Create index file
        print("\n📋 Phase 5: Creating Index")
        index = {
            'last_update': datetime.now().isoformat(),
            'trending': 'trending.json',
            'latest': 'latest.json',
            'countries': [c for _, c in country_searches],
            'searches': len(popular_searches) + len(country_searches) + 1,
            'stats': self.stats
        }
        self.save_json(index, "index.json")
        
        print(f"\n{'='*60}")
        print(f"✅ Fetch complete at {datetime.now()}")
        print(f"📊 Stats: {self.stats}")
        print(f"{'='*60}")

if __name__ == "__main__":
    fetcher = GDELTFetcher()
    fetcher.run()
