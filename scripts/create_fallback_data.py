#!/usr/bin/env python3
"""Create fallback data when GDELT is unavailable"""
import json
from datetime import datetime, timedelta
from pathlib import Path

output_dir = Path("news")
output_dir.mkdir(exist_ok=True)

# Create trending.json with realistic mock data
trending = {
    'timestamp': datetime.now().isoformat(),
    'trends': [
        {'date': (datetime.now() - timedelta(hours=i)).strftime('%Y%m%d%H'), 
         'value': 1000 - (i * 50)}
        for i in range(15)
    ],
    'note': 'Fallback data - GDELT API temporarily unavailable'
}

with open(output_dir / 'trending.json', 'w') as f:
    json.dump(trending, f, indent=2)

# Create latest.json with cached or mock articles
latest = {
    'timestamp': datetime.now().isoformat(),
    'total': 5,
    'articles': [
        {
            'title': 'Sample News Article ' + str(i),
            'url': '#',
            'source': 'News Source',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'country': 'US',
            'summary': 'This is a sample article while GDELT API is recovering...',
            'themes': ['sample', 'news']
        }
        for i in range(5)
    ]
}

with open(output_dir / 'latest.json', 'w') as f:
    json.dump(latest, f, indent=2)

print("Created fallback data files")
