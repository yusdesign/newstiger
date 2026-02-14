# In your bot, update the fetch_news method to use Guardian
def fetch_news(self, query, country=None, max_records=5):
    """Fetch news from Guardian via GitHub Pages cache"""
    
    # Try to get from GitHub Pages cache first
    cached = self._fetch_from_github_pages(query, country)
    if cached:
        return cached
    
    # If not in cache, return mock data with explanation
    return {
        'articles': [{
            'title': f'News about {query}',
            'url': self.site_url,
            'source': 'The Guardian',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'country': country or 'Global',
            'summary': 'Please check our website for the latest news. We update every 2 hours.',
            'api': 'Guardian'
        }],
        'total': 1,
        'query': query
    }
