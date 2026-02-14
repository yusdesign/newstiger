#!/usr/bin/env python3
"""Create fallback data when GDELT API is unavailable"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import time

print(f"\n{'='*50}")
print(f"Creating fallback data at {datetime.now()}")
print(f"{'='*50}\n")

output_dir = Path("news")
output_dir.mkdir(exist_ok=True)
search_dir = output_dir / "search"
search_dir.mkdir(exist_ok=True)

timestamp = datetime.now().isoformat()

# Create trending.json with mock data
print("📈 Creating trending.json...")
trending = {
    'timestamp': timestamp,
    'trends': [
        {
            'date': (datetime.now() - timedelta(hours=i)).strftime('%Y%m%d%H'),
            'value': 1000 - (i * 50) + random.randint(-20, 20)
        }
        for i in range(15)
    ],
    'note': 'Fallback data - GDELT API temporarily unavailable'
}

with open(output_dir / 'trending.json', 'w') as f:
    json.dump(trending, f, indent=2)
print("  ✅ trending.json created")

# Create latest.json with sample articles
print("📰 Creating latest.json...")
latest = {
    'timestamp': timestamp,
    'total': 5,
    'articles': [
        {
            'title': f'Global News Update {i}',
            'url': 'https://example.com',
            'source': 'News Service',
            'date': (datetime.now() - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M'),
            'country': random.choice(['US', 'GB', 'RU', 'DE', 'FR']),
            'summary': 'This is a sample article while the GDELT API is recovering...',
            'themes': ['sample', 'news']
        }
        for i in range(5)
    ]
}

with open(output_dir / 'latest.json', 'w') as f:
    json.dump(latest, f, indent=2)
print("  ✅ latest.json created")

# Create essential country files
print("🌍 Creating country files...")
countries = ['RU', 'UA', 'US', 'GB', 'DE', 'FR', 'CN', 'JP', 'IN', 'BR']
for country in countries:
    filename = f"russia_{country.lower()}.json" if country == 'RU' else f"{country.lower()}.json"
    
    data = {
        'timestamp': timestamp,
        'total': 3,
        'articles': [
            {
                'title': f'News from {country} - Update {i}',
                'url': 'https://example.com',
                'source': f'{country} News',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'country': country,
                'summary': f'Sample news from {country} while API is unavailable',
                'themes': ['regional', 'news']
            }
            for i in range(3)
        ]
    }
    
    with open(search_dir / filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  ✅ {filename}")

print("\n🎉 All fallback data created successfully!")
