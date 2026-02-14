#!/usr/bin/env python3
"""
Guardian Live API - Прямой доступ к Guardian API
Не требует сохранения файлов, работает в реальном времени
"""

import requests
import json
import os
from datetime import datetime

class GuardianLive:
    def __init__(self):
        self.api_key = os.environ.get('GUARDIAN_API_KEY')
        if not self.api_key:
            raise ValueError("GUARDIAN_API_KEY not found")
        self.base_url = "https://content.guardianapis.com"
    
    def search(self, query, page_size=15, section=None):
        """Поиск новостей по запросу"""
        params = {
            'q': query,
            'page-size': page_size,
            'show-fields': 'headline,trailText,thumbnail,bodyText',
            'show-tags': 'contributor',
            'order-by': 'relevance',
            'api-key': self.api_key
        }
        
        if section:
            params['section'] = section
        
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            if response.status_code == 200:
                data = response.json()
                return self._format_results(data, query)
            else:
                return {'error': f'API Error: {response.status_code}', 'articles': []}
        except Exception as e:
            return {'error': str(e), 'articles': []}
    
    def latest(self, page_size=20):
        """Последние новости"""
        params = {
            'page-size': page_size,
            'show-fields': 'headline,trailText,thumbnail',
            'order-by': 'newest',
            'api-key': self.api_key
        }
        
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            if response.status_code == 200:
                data = response.json()
                return self._format_results(data, 'latest')
        except:
            pass
        return {'articles': []}
    
    def section(self, section, page_size=20):
        """Новости по разделу"""
        params = {
            'section': section,
            'page-size': page_size,
            'show-fields': 'headline,trailText,thumbnail',
            'order-by': 'newest',
            'api-key': self.api_key
        }
        
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            if response.status_code == 200:
                data = response.json()
                return self._format_results(data, section)
        except:
            pass
        return {'articles': []}
    
    def _format_results(self, data, source):
        """Форматирование результатов"""
        articles = []
        response = data.get('response', {})
        
        for result in response.get('results', []):
            fields = result.get('fields', {})
            articles.append({
                'title': fields.get('headline', result.get('webTitle', 'No title')),
                'url': result.get('webUrl', '#'),
                'source': 'The Guardian',
                'date': result.get('webPublicationDate', ''),
                'country': self._section_to_country(result.get('sectionId', '')),
                'section': result.get('sectionName', 'News'),
                'summary': fields.get('trailText', '').replace('<p>', '').replace('</p>', ''),
                'image': fields.get('thumbnail', ''),
                'id': result.get('id', '')
            })
        
        return {
            'source': source,
            'total': len(articles),
            'articles': articles,
            'timestamp': datetime.now().isoformat()
        }
    
    def _section_to_country(self, section):
        countries = {
            'us-news': 'US', 'uk-news': 'GB', 'australia-news': 'AU',
            'world/russia': 'RU', 'world/ukraine': 'UA', 'world/germany': 'DE',
            'world/france': 'FR', 'world/japan': 'JP', 'world/india': 'IN',
            'world/china': 'CN', 'world/europe-news': 'EU'
        }
        return countries.get(section, 'Global')

# Для тестирования
if __name__ == "__main__":
    api = GuardianLive()
    
    print("🔍 Тест поиска 'russia':")
    result = api.search('russia', 5)
    for a in result['articles']:
        print(f"  - {a['title'][:50]}...")
    
    print("\n📰 Тест последних новостей:")
    latest = api.latest(5)
    for a in latest['articles']:
        print(f"  - {a['title'][:50]}...")
