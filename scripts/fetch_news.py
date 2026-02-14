#!/usr/bin/env python3
"""
GDELT News Fetcher - Runs via GitHub Actions
Fetches latest news and saves as JSON for static site
"""

import requests
import json
import os
from datetime import datetime
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
            response = requests.get(self.api_url, params=params, timeout=30)
            if response.status_code == 200:
                return self._format_articles(response.json(), query)
            else:
                print(f"Error fetching {query}: {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception fetching {query}: {e}")
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
            response = requests.get(self.api_url, params=params, timeout=30)
            if response.status_code == 200:
                return self._format_trending(response.json())
            return None
        except Exception as e:
            print(f"Error fetching trending: {e}")
            return None
    
    def _format_articles(self, raw_data, query):
        """Format articles for JSON storage"""
        articles = []
        
        for article in raw_data.get('articles', []):
            articles.append({
                'title': article.get('title', 'No title'),
                'url': article.get('url', '#'),
                'source': article.get('domain', 'Unknown'),
                'date': self._format_date(article.get('seendate', '')),
                'country': article.get('sourcecountry', 'Unknown'),
                'language': article.get('language', 'Unknown'),
                'summary': article.get('content', '')[:300] if article.get('content') else '',
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
        
        for item in raw_data.get('timeline', []):
            trends.append({
                'date': item.get('date', ''),
                'value': item.get('value', 0)
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'trends': trends[:30]  # Top 30
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
        print(f"Saved {filepath}")
    
    def save_search(self, data, query, country=None):
        """Save search results with safe filename"""
        # Create safe filename
        safe_query = query.lower().replace(' ', '_')
        safe_query = ''.join(c for c in safe_query if c.isalnum() or c == '_')
        safe_query = safe_query[:50]  # Limit length
        
        if country:
            filename = f"{safe_query}_{country}.json"
        else:
            filename = f"{safe_query}.json"
        
        filepath = self.search_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved search: {filepath}")
    
    def run(self):
        """Main fetch routine"""
        print(f"Starting GDELT fetch at {datetime.now()}")
        
        # 1. Fetch latest technology news (default)
        print("\n1. Fetching latest technology news...")
        tech_news = self.fetch_news("technology", max_records=30)
        if tech_news:
            self.save_json(tech_news, "latest.json")
            self.save_search(tech_news, "technology")
        
        # 2. Fetch trending topics
        print("\n2. Fetching trending topics...")
        trending = self.fetch_trending()
        if trending:
            self.save_json(trending, "trending.json")
        
        # 3. Fetch popular searches
        popular_searches = [
            ("climate change", None),
            ("artificial intelligence", None),
            ("business", None),
            ("health", "US"),
            ("sports", None),
            ("election", "US"),
            ("technology", "US"),
            ("technology", "GB"),
            ("technology", "IN")
        ]
        
        print("\n3. Fetching popular searches...")
        for query, country in popular_searches:
            print(f"   - {query} {f'({country})' if country else ''}")
            news = self.fetch_news(query, max_records=15, country=country)
            if news:
                self.save_search(news, query, country)
            time.sleep(1)  # Be nice to the API
        
        # 4. Create index file
        index = {
            'last_update': datetime.now().isoformat(),
            'searches': len(popular_searches) + 1,
            'files': {
                'latest': 'latest.json',
                'trending': 'trending.json',
                'searches': [f"search/{self._get_filename(q, c)}" for q, c in popular_searches]
            }
        }
        self.save_json(index, "index.json")
        
        print(f"\n✅ Fetch complete at {datetime.now()}")
    
    def _get_filename(self, query, country):
        """Get filename for a query"""
        safe = query.lower().replace(' ', '_')
        safe = ''.join(c for c in safe if c.isalnum() or c == '_')[:50]
        if country:
            return f"{safe}_{country}.json"
        return f"{safe}.json"

from datetime import timedelta

if __name__ == "__main__":
    fetcher = GDELTFetcher()
    fetcher.run()
