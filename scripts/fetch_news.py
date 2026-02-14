#!/usr/bin/env python3
"""
Guardian News Fetcher - Gets ALL news sections properly
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
        
        print(f"📁 Output directory: {self.output_dir.absolute()}")
    
    def fetch_section(self, section, page_size=30):
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
        
        print(f"  📰 Fetching section: {section} (max {page_size} articles)")
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._format_articles(data, section)
            else:
                print(f"  ⚠️ Error {response.status_code}: {response.text[:100]}")
                return None
        except Exception as e:
            print(f"  ⚠️ Exception: {e}")
            return None
    
    def fetch_search(self, query, page_size=25):
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
        
        print(f"  🔍 Searching: '{query}'")
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._format_articles(data, query)
            else:
                print(f"  ⚠️ Error {response.status_code}")
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
            
            # Clean HTML from summary
            summary = summary.replace('<p>', '').replace('</p>', '').replace('<strong>', '').replace('</strong>', '').strip()
            
            article = {
                'title': fields.get('headline', result.get('webTitle', 'No title')),
                'url': result.get('webUrl', '#'),
                'source': 'The Guardian',
                'date': result.get('webPublicationDate', ''),
                'country': self._section_to_country(result.get('sectionId', '')),
                'section': result.get('sectionName', 'News'),
                'section_id': result.get('sectionId', ''),
                'summary': summary,
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
            'world/middleeast': 'ME',
            'world/africa': 'AF',
            'world/americas': 'AM',
            'world/asia': 'AS'
        }
        return country_map.get(section_id, 'Global')
    
    def save_json(self, data, filename):
        """Save data as JSON"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved: {filename} ({data['total']} articles)")
    
    def save_search(self, data, name):
        """Save search results"""
        safe_name = name.lower().replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')[:40]
        filename = f"{safe_name}.json"
        
        filepath = self.search_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved search: {filename} ({data['total']} articles)")
    
    def run(self):
        """Main fetch routine"""
        print(f"\n{'='*70}")
        print(f"🚀 Fetching Guardian News at {datetime.now()}")
        print(f"🔑 API Key: {self.api_key[:5]}...{self.api_key[-5:]}")
        print(f"{'='*70}\n")
        
        all_results = {}
        
        # 1. COUNTRY SECTIONS
        print("\n🌍 PHASE 1: COUNTRY SECTIONS")
        country_sections = [
            ('world/russia', 'russia'),
            ('world/ukraine', 'ukraine'),
            ('us-news', 'us'),
            ('uk-news', 'gb'),
            ('world/germany', 'germany'),
            ('world/france', 'france'),
            ('world/japan', 'japan'),
            ('world/india', 'india'),
            ('world/china', 'china'),
            ('australia-news', 'australia'),
        ]
        
        for section, name in country_sections:
            print(f"\n  📍 {name.upper()}")
            result = self.fetch_section(section, 25)
            if result and result['articles']:
                self.save_search(result, name)
                all_results[name] = result
            time.sleep(1)  # Be nice to API
        
        # 2. TOPIC SECTIONS
        print("\n📰 PHASE 2: TOPIC SECTIONS")
        topic_sections = [
            'technology',
            'business',
            'sport',
            'science',
            'environment',
            'politics',
            'culture',
            'lifeandstyle'
        ]
        
        for section in topic_sections:
            print(f"\n  📌 {section}")
            result = self.fetch_section(section, 25)
            if result and result['articles']:
                self.save_search(result, section)
                all_results[section] = result
            time.sleep(1)
        
        # 3. POPULAR SEARCHES
        print("\n🔍 PHASE 3: POPULAR SEARCHES")
        searches = [
            'climate change',
            'artificial intelligence',
            'covid',
            'election',
            'economy',
            'health',
            'education'
        ]
        
        for query in searches:
            print(f"\n  🔎 {query}")
            result = self.fetch_search(query, 20)
            if result and result['articles']:
                name = query.replace(' ', '_')
                self.save_search(result, name)
                all_results[name] = result
            time.sleep(1)
        
        # 4. LATEST NEWS (world section for latest)
        print("\n📰 PHASE 4: LATEST NEWS")
        latest = self.fetch_section('world', 40)
        if latest and latest['articles']:
            self.save_json(latest, 'latest.json')
            all_results['latest'] = latest
        
        time.sleep(1)
        
        # 5. TRENDING (based on latest)
        print("\n📈 PHASE 5: TRENDING")
        if latest and latest.get('articles'):
            trends = []
            for i, article in enumerate(latest['articles'][:20]):
                trends.append({
                    'rank': i + 1,
                    'title': article['title'][:70],
                    'section': article['section'],
                    'date': article['date'][:10] if article['date'] else '',
                    'url': article['url']
                })
            
            trending_data = {
                'timestamp': datetime.now().isoformat(),
                'total': len(trends),
                'trends': trends,
                'source': 'Guardian'
            }
            self.save_json(trending_data, 'trending.json')
        
        # 6. INDEX
        print("\n📋 PHASE 6: INDEX")
        
        # Calculate totals safely
        total_articles = 0
        sections_summary = {}
        
        for name, result in all_results.items():
            try:
                if result and isinstance(result, dict):
                    articles = result.get('articles', [])
                    if articles and isinstance(articles, list):
                        count = len(articles)
                        total_articles += count
                        sections_summary[name] = count
                        print(f"  📊 {name}: {count} articles")
                    else:
                        sections_summary[name] = 0
                        print(f"  ⚠️ {name}: no articles")
            except Exception as e:
                print(f"  ⚠️ Error processing {name}: {e}")
                sections_summary[name] = 0
        
        # Create index with ALL required fields
        index = {
            'last_update': datetime.now().isoformat(),
            'total_articles': total_articles,
            'total': total_articles,  # Add this line to fix the error
            'sections': sections_summary,
            'files_created': len(all_results),
            'message': 'Fresh Guardian news',
            'latest_file': 'latest.json',
            'trending_file': 'trending.json',
            'status': 'success'
        }
        
        try:
            # Save to both locations to be safe
            with open(self.output_dir / 'index.json', 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            print(f"  ✅ Index saved with {total_articles} total articles")
            
            # Also save a copy in search directory
            with open(self.search_dir / 'index.json', 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"  ⚠️ Error saving index: {e}")
            # Save minimal version as fallback
            minimal = {
                'last_update': datetime.now().isoformat(),
                'total_articles': total_articles,
                'total': total_articles,
                'message': 'Minimal index'
            }
            with open(self.output_dir / 'index.json', 'w', encoding='utf-8') as f:
                json.dump(minimal, f, indent=2)
            print(f"  ✅ Minimal index saved")
        
        print(f"\n{'='*70}")
        print(f"✅ COMPLETE!")
        print(f"📊 Total articles: {total_articles}")
        print(f"📁 Files created: {len(all_results)}")
        print(f"{'='*70}")

if __name__ == "__main__":
    fetcher = GuardianFetcher()
    fetcher.run()
