#!/usr/bin/env python3
"""
GDELT News Fetcher - Creates JSON files for static site
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import time

class GDELTFetcher:
    def __init__(self):
        self.api_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.output_dir = Path("news")
        self.search_dir = self.output_dir / "search"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.search_dir.mkdir(exist_ok=True)
    
    def fetch_news(self, query, max_records=25, country=None):
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
            print(f"Fetching: {query} ({country if country else 'all'})")
            response = requests.get(self.api_url, params=params, timeout=30)
            if response.status_code == 200:
                return self._format_articles(response.json(), query)
            else:
                print(f"  Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"  Exception: {e}")
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
            print("Fetching trending topics...")
            response = requests.get(self.api_url, params=params, timeout=30)
            if response.status_code == 200:
                return self._format_trending(response.json())
            else:
                print(f"  Trending error: {response.status_code}")
                return self._generate_mock_trending()
        except Exception as e:
            print(f"  Trending exception: {e}")
            return self._generate_mock_trending()
    
    def _format_articles(self, raw_data, query):
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
                'value': 1000 - (i * 50)  # Decreasing trend
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trends': trends,
            'note': 'Mock data - API unavailable'
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
        print(f"  Saved: {filename}")
    
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
        print(f"  Saved search: {filename}")
    
    def run(self):
        """Main fetch routine"""
        print(f"\n{'='*50}")
        print(f"Starting GDELT fetch at {datetime.now()}")
        print(f"{'='*50}\n")
        
        # 1. Fetch trending topics (always do this first)
        print("📈 Fetching trending topics...")
        trending = self.fetch_trending()
        if trending:
            self.save_json(trending, "trending.json")
        else:
            # Create default trending file
            default_trending = {
                'timestamp': datetime.now().isoformat(),
                'trends': [],
                'note': 'No data available'
            }
            self.save_json(default_trending, "trending.json")
        
        # 2. Fetch latest technology news (default)
        print("\n📰 Fetching latest technology news...")
        tech_news = self.fetch_news("technology", max_records=30)
        if tech_news:
            self.save_json(tech_news, "latest.json")
            self.save_search(tech_news, "technology")
        
        # 3. Fetch country-specific news
        print("\n🌍 Fetching country-specific news...")
        country_searches = [
            ("Russia", "RU"),
            ("Ukraine", "UA"),
            ("USA", "US"),
            ("UK", "GB"),
            ("Germany", "DE"),
            ("France", "FR"),
            ("China", "CN"),
        ]
        
        for query, country in country_searches:
            print(f"  - {query} ({country})")
            news = self.fetch_news(query, max_records=20, country=country)
            if news:
                self.save_search(news, query, country)
            time.sleep(1)  # Be nice to the API
        
        # 4. Fetch popular searches
        print("\n🔍 Fetching popular searches...")
        popular_searches = [
            ("climate change", None),
            ("artificial intelligence", None),
            ("business", None),
            ("sports", None),
            ("health", None),
            ("election", None),
        ]
        
        for query, country in popular_searches:
            print(f"  - {query}")
            news = self.fetch_news(query, max_records=15, country=country)
            if news:
                self.save_search(news, query, country)
            time.sleep(1)
        
        # 5. Create index file
        print("\n📋 Creating index file...")
        index = {
            'last_update': datetime.now().isoformat(),
            'trending': 'trending.json',
            'latest': 'latest.json',
            'countries': [c for _, c in country_searches],
            'searches': len(popular_searches) + len(country_searches) + 1
        }
        self.save_json(index, "index.json")
        
        print(f"\n{'='*50}")
        print(f"✅ Fetch complete at {datetime.now()}")
        print(f"{'='*50}")

if __name__ == "__main__":
    fetcher = GDELTFetcher()
    fetcher.run()
