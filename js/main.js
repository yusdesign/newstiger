// State
let currentQuery = 'technology';
let currentCountry = '';
let newsData = {};
let trendingData = [];
let searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
let currentArticles = [];

// DOM Elements
const searchInput = document.getElementById('search-input');
const countrySelect = document.getElementById('country-select');
const searchBtn = document.getElementById('search-btn');
const loading = document.getElementById('loading');
const lastUpdate = document.getElementById('last-update');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const latestNews = document.getElementById('latest-news');
const trendingTopics = document.getElementById('trending-topics');
const savedResults = document.getElementById('saved-results');
const filterDisplay = document.getElementById('filter-display');

// Initialize
async function init() {
    console.log('Initializing NewsTiger...');
    
    // Check URL parameters first
    const urlParams = new URLSearchParams(window.location.search);
    const urlQuery = urlParams.get('q');
    const urlCountry = urlParams.get('country');
    
    if (urlQuery) {
        searchInput.value = urlQuery;
        currentQuery = urlQuery;
        if (urlCountry) {
            countrySelect.value = urlCountry;
            currentCountry = urlCountry;
        }
        // Perform search with URL params
        await performSearch();
    } else {
        // Default load - technology news
        searchInput.value = 'technology';
        await performSearch();
    }
    
    await loadTrending();
    setupEventListeners();
    updateTimestamp();
    addFetchButton();
    displaySearchHistory();
    setupTranslationButtons();
    setupPresetButtons();
    updateFilterDisplay();
    
    console.log('NewsTiger initialized');
}

// Setup preset buttons for quick access
function setupPresetButtons() {
    // Check if preset buttons already exist
    if (document.querySelector('.preset-buttons')) return;
    
    const searchSection = document.querySelector('.search-section');
    const presetDiv = document.createElement('div');
    presetDiv.className = 'preset-buttons';
    presetDiv.innerHTML = `
        <button class="preset-btn" data-query="Russia" data-country="RU">🇷🇺 Russia News</button>
        <button class="preset-btn" data-query="Ukraine" data-country="UA">🇺🇦 Ukraine News</button>
        <button class="preset-btn" data-query="USA" data-country="US">🇺🇸 US News</button>
        <button class="preset-btn" data-query="UK" data-country="GB">🇬🇧 UK News</button>
        <button class="preset-btn" data-query="Germany" data-country="DE">🇩🇪 Germany News</button>
        <button class="preset-btn" data-query="France" data-country="FR">🇫🇷 France News</button>
        <button class="preset-btn" data-query="technology" data-country="">💻 Technology</button>
        <button class="preset-btn" data-query="climate change" data-country="">🌍 Climate</button>
    `;
    
    searchSection.appendChild(presetDiv);
    
    // Add event listeners
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            const country = btn.dataset.country;
            searchInput.value = query;
            if (country) {
                countrySelect.value = country;
            } else {
                countrySelect.value = '';
            }
            performSearch();
            
            // Update URL without reloading
            const url = new URL(window.location);
            url.searchParams.set('q', query);
            if (country) {
                url.searchParams.set('country', country);
            } else {
                url.searchParams.delete('country');
            }
            window.history.pushState({}, '', url);
            updateFilterDisplay();
        });
    });
}

// Add Fetch Fresh button
function addFetchButton() {
    // Check if button already exists
    if (document.getElementById('fetch-fresh-btn')) return;
    
    const actionButtons = document.querySelector('.action-buttons');
    if (!actionButtons) {
        // Create action buttons container if it doesn't exist
        const searchBox = document.querySelector('.search-box');
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'action-buttons';
        searchBox.appendChild(actionsDiv);
    }
    
    const fetchBtn = document.createElement('button');
    fetchBtn.id = 'fetch-fresh-btn';
    fetchBtn.innerHTML = '🔄 Fetch Fresh News';
    fetchBtn.className = 'fetch-btn';
    fetchBtn.addEventListener('click', () => {
        const query = searchInput.value.trim() || 'technology';
        const country = countrySelect.value;
        fetchFreshNews(query, country);
    });
    
    document.querySelector('.action-buttons').appendChild(fetchBtn);
}

// Setup translation buttons
function setupTranslationButtons() {
    document.querySelectorAll('.translation-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const lang = btn.dataset.lang;
            if (window.Translator) {
                window.Translator.setLanguage(lang);
            } else {
                // Fallback if Translator not loaded
                document.querySelectorAll('.translation-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                localStorage.setItem('preferred_language', lang);
            }
            
            // Show toast
            if (lang === 'none') {
                showSuccess('Translation disabled');
            } else if (lang === 'en') {
                showSuccess('Translating to English');
            } else if (lang === 'ru') {
                showSuccess('Перевод на русский');
            }
            
            // Retranslate visible content if modal is open
            if (window.modal && window.modal.currentArticle) {
                window.modal.translate(lang);
            }
        });
    });
}

// Update filter display
function updateFilterDisplay() {
    if (!filterDisplay) return;
    
    const country = countrySelect.value;
    const query = searchInput.value || 'technology';
    
    if (country) {
        const countryName = countrySelect.options[countrySelect.selectedIndex]?.text || country;
        filterDisplay.textContent = `"${query}" in ${countryName}`;
    } else {
        filterDisplay.textContent = `"${query}" Worldwide`;
    }
}

// Perform search (cached version first)
async function performSearch() {
    const query = searchInput.value.trim() || 'technology';
    const country = countrySelect.value;
    
    currentQuery = query;
    currentCountry = country;
    
    updateFilterDisplay();
    showLoading();
    
    // Try cache first
    const cached = await loadCachedSearch(query, country);
    if (cached && cached.articles && cached.articles.length > 0) {
        displaySearchResults(cached.articles);
        showSuccess(`Loaded from cache (${country || 'All Countries'})`);
        hideLoading();
    } else {
        // Fetch fresh
        await fetchFreshNews(query, country);
    }
}

// Fetch fresh news using proxy
async function fetchFreshNews(query, country = '') {
    showLoading();
    
    // Try to get from our GitHub Pages cache first
    try {
        // Create filename from query
        const safeQuery = query.toLowerCase().replace(/[^a-z0-9]+/g, '_').substring(0, 50);
        const cacheFile = country ? 
            `news/search/${safeQuery}_${country.toLowerCase()}.json` : 
            `news/search/${safeQuery}.json`;
        
        console.log('📁 Trying cache:', cacheFile);
        
        const cacheResponse = await fetch(cacheFile + '?t=' + Date.now());
        if (cacheResponse.ok) {
            const data = await cacheResponse.json();
            if (data.articles && data.articles.length > 0) {
                displaySearchResults(data.articles);
                showSuccess(`Loaded from cache (${data.api || 'Guardian'})`);
                hideLoading();
                return;
            }
        }
    } catch (e) {
        console.log('Cache miss:', e);
    }
    
    // If no cache, try to get from latest.json
    try {
        const latestResponse = await fetch('news/latest.json?t=' + Date.now());
        if (latestResponse.ok) {
            const latest = await latestResponse.json();
            if (latest.articles && latest.articles.length > 0) {
                // Filter articles by query if needed
                const filtered = latest.articles.filter(a => 
                    a.title.toLowerCase().includes(query.toLowerCase()) ||
                    (a.summary && a.summary.toLowerCase().includes(query.toLowerCase()))
                );
                
                if (filtered.length > 0) {
                    displaySearchResults(filtered);
                    showSuccess(`Filtered from latest news`);
                } else {
                    displaySearchResults(latest.articles.slice(0, 10));
                    showSuccess(`Showing latest news`);
                }
                hideLoading();
                return;
            }
        }
    } catch (e) {
        console.log('Latest fetch failed:', e);
    }
    
    // Final fallback - show sample data
    const sampleArticles = [
        {
            title: `News about: ${query}`,
            url: 'https://theguardian.com',
            source: 'The Guardian',
            date: new Date().toLocaleDateString(),
            country: country || 'Global',
            summary: `Latest news and updates about ${query}. Please check back soon for fresh articles.`,
            image: '',
            section: 'News'
        },
        {
            title: `Developments in ${query}`,
            url: 'https://theguardian.com',
            source: 'The Guardian',
            date: new Date().toLocaleDateString(),
            country: country || 'Global',
            summary: `Stay informed with the latest developments in ${query}.`,
            image: '',
            section: 'Updates'
        }
    ];
    
    displaySearchResults(sampleArticles);
    showWarning('Showing sample data - real news will appear soon');
    hideLoading();
}

// Format articles from GDELT response
function formatArticles(rawData, query) {
    const articles = [];
    
    for (const article of rawData.articles || []) {
        articles.push({
            title: article.title || 'No title',
            url: article.url || '#',
            source: article.domain || 'Unknown',
            date: formatDate(article.seendate),
            country: article.sourcecountry || 'Unknown',
            language: article.language || 'Unknown',
            summary: (article.content || article.summary || '').substring(0, 300) + '...',
            themes: (article.themes || []).slice(0, 5),
            image: article.socialimage || ''
        });
    }
    
    return {
        query: query,
        timestamp: new Date().toISOString(),
        total: articles.length,
        articles: articles
    };
}

// Display search results handled by Guardian data
function displaySearchResults(articles) {
    if (!articles || articles.length === 0) {
        latestNews.innerHTML = '<div class="no-results">No articles found</div>';
        return;
    }
    
    const country = countrySelect.value;
    const query = searchInput.value;
    
    let html = `<div class="results-header">
        <h2>📰 News from The Guardian</h2>
        <p class="results-count">Found ${articles.length} articles</p>
    </div>`;
    
    articles.forEach(article => {
        // Handle both old and new data formats
        const title = article.title || article.webTitle || 'No title';
        const url = article.url || article.webUrl || '#';
        const source = article.source || 'The Guardian';
        const date = article.date || article.webPublicationDate || '';
        const country_code = article.country || 'Global';
        const summary = article.summary || article.fields?.trailText || '';
        const image = article.image || article.fields?.thumbnail || '';
        const section = article.section || article.sectionName || 'News';
        
        html += `
            <div class="news-card">
                ${image ? `<img src="${image}" alt="${escapeHtml(title)}" class="news-thumbnail" onerror="this.style.display='none'">` : ''}
                <div class="news-content">
                    <h3><a href="${escapeHtml(url)}" target="_blank">${escapeHtml(title)}</a></h3>
                    <div class="news-meta">
                        <span class="source">📰 ${escapeHtml(source)}</span>
                        <span class="country">🌍 ${escapeHtml(country_code)}</span>
                        <span class="date">📅 ${escapeHtml(formatDate(date))}</span>
                        <span class="section">🏷️ ${escapeHtml(section)}</span>
                    </div>
                    <p class="summary">${escapeHtml(summary.substring(0, 200))}...</p>
                    <div class="news-actions">
                        <a href="${escapeHtml(url)}" target="_blank" class="read-more-btn">📖 Read on Guardian</a>
                    </div>
                </div>
            </div>
        `;
    });
    
    latestNews.innerHTML = html;
}

// Open article in modal
window.openArticle = function(index) {
    if (window.modal && window.currentArticles && window.currentArticles[index]) {
        window.modal.open(window.currentArticles[index]);
    } else {
        console.error('Modal or article not available');
    }
};

// Get country name from code
function getCountryName(code) {
    const countries = {
        'RU': 'Russia', 'UA': 'Ukraine', 'US': 'United States', 
        'GB': 'United Kingdom', 'DE': 'Germany', 'FR': 'France',
        'CA': 'Canada', 'AU': 'Australia', 'IN': 'India',
        'CN': 'China', 'JP': 'Japan', 'BR': 'Brazil'
    };
    return countries[code] || code;
}

// Load trending data with fallback
async function loadTrending() {
    try {
        // Try to fetch from GitHub Pages first
        const response = await fetch('news/trending.json?t=' + Date.now());
        
        if (!response.ok) {
            // If 404, use mock data or fetch live
            console.log('Trending file not found, using live data or fallback');
            const liveTrends = await fetchLiveTrending();
            displayTrending(liveTrends);
            return;
        }
        
        const data = await response.json();
        trendingData = data.trends || [];
        displayTrending(trendingData);
    } catch (error) {
        console.error('Error loading trending:', error);
        // Fallback to live fetch
        const liveTrends = await fetchLiveTrending();
        displayTrending(liveTrends);
    }
}

// Fetch live trending data from GDELT
async function fetchLiveTrending() {
    try {
        // Use proxy to fetch live trending from GDELT
        const proxyUrl = 'https://api.allorigins.win/get?url=' + encodeURIComponent(
            'https://api.gdeltproject.org/api/v2/doc/doc?query=*&mode=timelinevol&format=json&maxrecords=15'
        );
        
        const response = await fetch(proxyUrl);
        const data = await response.json();
        const parsed = JSON.parse(data.contents);
        
        // Format the data
        const trends = (parsed.timeline || []).map(item => ({
            date: item.date || '',
            value: item.value || 0
        }));
        
        return trends;
    } catch (e) {
        console.log('Live trending failed, using mock data');
        // Return mock data as last resort
        return generateMockTrending();
    }
}

// Generate mock trending data for fallback
function generateMockTrending() {
    const trends = [];
    const now = new Date();
    
    for (let i = 0; i < 10; i++) {
        const date = new Date(now);
        date.setHours(now.getHours() - i);
        
        trends.push({
            date: date.toISOString().split('T')[0].replace(/-/g, ''),
            value: Math.floor(Math.random() * 1000) + 500
        });
    }
    
    return trends;
}

// Display trending topics
function displayTrending(trends) {
    if (!trends || trends.length === 0) {
        if (trendingTopics) {
            trendingTopics.innerHTML = '<div class="no-results">No trending data available</div>';
        }
        return;
    }
    
    let html = '<div class="trending-list">';
    trends.slice(0, 15).forEach((trend, index) => {
        html += `
            <div class="trend-item" data-date="${trend.date}">
                <span class="trend-rank">#${index + 1}</span>
                <span class="trend-date">${formatDate(trend.date)}</span>
                <span class="trend-value">📊 ${trend.value.toLocaleString()}</span>
            </div>
        `;
    });
    html += '</div>';
    
    if (trendingTopics) {
        trendingTopics.innerHTML = html;
    }
    
    // Add click handlers to trend items
    document.querySelectorAll('.trend-item').forEach(item => {
        item.addEventListener('click', () => {
            const date = item.dataset.date;
            searchInput.value = `date:${date}`;
            performSearch();
        });
    });
}

// Save to localStorage cache
function saveToCache(query, country, data) {
    const key = `gdelt_${query}_${country}`;
    const cacheItem = {
        timestamp: Date.now(),
        data: data
    };
    localStorage.setItem(key, JSON.stringify(cacheItem));
    
    // Clean old cache (keep only last 20 items)
    try {
        const keys = Object.keys(localStorage).filter(k => k.startsWith('gdelt_'));
        if (keys.length > 20) {
            const oldest = keys
                .map(k => ({ key: k, time: JSON.parse(localStorage.getItem(k)).timestamp }))
                .sort((a, b) => a.time - b.time)[0];
            if (oldest) localStorage.removeItem(oldest.key);
        }
    } catch (e) {
        console.log('Cache cleanup error:', e);
    }
}

// Load cached search
async function loadCachedSearch(query, country) {
    const key = `gdelt_${query}_${country}`;
    const cached = localStorage.getItem(key);
    
    if (cached) {
        const item = JSON.parse(cached);
        // Cache valid for 1 hour
        if (Date.now() - item.timestamp < 3600000) {
            return item.data;
        }
    }
    return null;
}

// Add to search history
function addToSearchHistory(query, country) {
    const search = {
        query: query,
        country: country || 'all',
        timestamp: Date.now()
    };
    
    searchHistory = [search, ...searchHistory.filter(s => 
        !(s.query === query && s.country === (country || 'all'))
    )].slice(0, 10);
    
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
    displaySearchHistory();
}

// Display search history
function displaySearchHistory() {
    const historyContainer = document.getElementById('search-history');
    if (!historyContainer) return;
    
    if (searchHistory.length === 0) {
        historyContainer.innerHTML = '<p class="empty-state">No search history yet</p>';
        return;
    }
    
    let html = '<h3>🕒 Recent Searches:</h3><div class="history-list">';
    searchHistory.forEach(search => {
        const countryName = search.country !== 'all' ? getCountryName(search.country) : 'Worldwide';
        html += `
            <button class="history-item" onclick="window.replaySearch('${search.query}', '${search.country === 'all' ? '' : search.country}')">
                🔍 ${escapeHtml(search.query)} <span class="country-badge">${countryName}</span>
            </button>
        `;
    });
    html += '</div>';
    
    historyContainer.innerHTML = html;
}

// Replay a search
window.replaySearch = function(query, country) {
    searchInput.value = query;
    if (country) {
        countrySelect.value = country;
    } else {
        countrySelect.value = '';
    }
    performSearch();
    
    // Update URL
    const url = new URL(window.location);
    url.searchParams.set('q', query);
    if (country) {
        url.searchParams.set('country', country);
    } else {
        url.searchParams.delete('country');
    }
    window.history.pushState({}, '', url);
    updateFilterDisplay();
};

// Update last update timestamp
function updateTimestamp() {
    if (lastUpdate) {
        const now = new Date();
        lastUpdate.textContent = now.toLocaleString();
    }
}

// Show loading
function showLoading() {
    if (loading) {
        loading.style.display = 'block';
    }
}

// Hide loading
function hideLoading() {
    if (loading) {
        loading.style.display = 'none';
    }
}

// Show success message
function showSuccess(message) {
    showToast(message, 'success');
}

// Show warning message
function showWarning(message) {
    showToast(message, 'warning');
}

// Show error message
function showError(message) {
    showToast(message, 'error');
}

// Toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    if (dateStr.length >= 8) {
        const year = dateStr.substring(0, 4);
        const month = dateStr.substring(4, 6);
        const day = dateStr.substring(6, 8);
        let formatted = `${year}-${month}-${day}`;
        
        if (dateStr.length >= 12) {
            const hour = dateStr.substring(8, 10);
            const minute = dateStr.substring(10, 12);
            formatted += ` ${hour}:${minute}`;
        }
        return formatted;
    }
    return dateStr;
}

// Setup event listeners
function setupEventListeners() {
    // Search button
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
    
    // Enter key in search input
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }
    
    // Country select change
    if (countrySelect) {
        countrySelect.addEventListener('change', () => {
            updateFilterDisplay();
        });
    }
    
    // Tab switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            const tabElement = document.getElementById(`${tabId}-tab`);
            if (tabElement) {
                tabElement.classList.add('active');
            }
            
            // Load tab content if needed
            if (tabId === 'trending' && trendingTopics && trendingTopics.children.length === 0) {
                displayTrending(trendingData);
            }
        });
    });
    
    // Handle browser back/forward
    window.addEventListener('popstate', () => {
        const urlParams = new URLSearchParams(window.location.search);
        const urlQuery = urlParams.get('q');
        const urlCountry = urlParams.get('country');
        
        if (urlQuery) {
            searchInput.value = urlQuery;
            if (urlCountry) {
                countrySelect.value = urlCountry;
            }
            performSearch();
        }
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);

// Export for debugging
window.debug = {
    state: () => ({
        currentQuery,
        currentCountry,
        searchHistory,
        currentArticles: currentArticles.length
    }),
    clearCache: () => {
        Object.keys(localStorage).forEach(k => {
            if (k.startsWith('gdelt_')) localStorage.removeItem(k);
        });
        console.log('Cache cleared');
        showSuccess('Cache cleared');
    }
};
