// State
let currentQuery = 'technology';
let newsData = {};
let trendingData = [];
let searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');

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

// Initialize
async function init() {
    await loadLatestNews();
    await loadTrending();
    setupEventListeners();
    updateTimestamp();
    addFetchButton();
    displaySearchHistory();
}

// Add Fetch Fresh button
function addFetchButton() {
    const searchBox = document.querySelector('.search-box');
    const fetchBtn = document.createElement('button');
    fetchBtn.id = 'fetch-fresh-btn';
    fetchBtn.innerHTML = '🔄 Fetch Fresh News';
    fetchBtn.className = 'fetch-btn';
    fetchBtn.addEventListener('click', () => {
        const query = searchInput.value.trim() || 'technology';
        const country = countrySelect.value;
        fetchFreshNews(query, country);
    });
    searchBox.appendChild(fetchBtn);
}

// Fetch fresh news using proxy
async function fetchFreshNews(query, country = '') {
    showLoading();
    
    // Try multiple proxies
    const proxyUrls = [
        `https://api.allorigins.win/get?url=${encodeURIComponent(buildGDELTUrl(query, country))}`,
        `https://corsproxy.io/?${encodeURIComponent(buildGDELTUrl(query, country))}`,
        `https://cors-anywhere.herokuapp.com/${buildGDELTUrl(query, country)}`
    ];
    
    for (const proxyUrl of proxyUrls) {
        try {
            let data;
            const response = await fetch(proxyUrl);
            
            if (proxyUrl.includes('allorigins')) {
                const wrapped = await response.json();
                data = JSON.parse(wrapped.contents);
            } else {
                data = await response.json();
            }
            
            // Format and display
            const formatted = formatArticles(data, query);
            displaySearchResults(formatted.articles);
            
            // Save to cache
            saveToCache(query, country, formatted);
            
            // Add to search history
            addToSearchHistory(query, country);
            
            hideLoading();
            showSuccess(`Found ${formatted.articles.length} fresh articles`);
            return;
            
        } catch (error) {
            console.log('Proxy failed:', proxyUrl);
            continue;
        }
    }
    
    // If all proxies fail, try cached
    const cached = await loadCachedSearch(query, country);
    if (cached) {
        displaySearchResults(cached.articles);
        showWarning('Using cached version (proxy unavailable)');
    } else {
        showError('Unable to fetch news. Please try again later.');
    }
    
    hideLoading();
}

// Build GDELT URL
function buildGDELTUrl(query, country) {
    let url = `https://api.gdeltproject.org/api/v2/doc/doc?query=${encodeURIComponent(query)}&mode=artlist&format=json&maxrecords=25&sort=date`;
    if (country) {
        url += `&sourcecountry=${country}`;
    }
    return url;
}

// Format articles
function formatArticles(rawData, query) {
    const articles = [];
    
    for (const article of rawData.articles || []) {
        articles.push({
            title: article.title || 'No title',
            url: article.url || '#',
            source: article.domain || 'Unknown',
            date: formatDate(article.seendate),
            country: article.sourcecountry || 'Unknown',
            summary: (article.content || '').substring(0, 300) + '...',
            themes: (article.themes || []).slice(0, 5)
        });
    }
    
    return {
        query: query,
        timestamp: new Date().toISOString(),
        total: articles.length,
        articles: articles
    };
}

// Display search results
function displaySearchResults(articles) {
    if (!articles || articles.length === 0) {
        latestNews.innerHTML = '<div class="no-results">No articles found</div>';
        return;
    }
    
    let html = '';
    articles.forEach(article => {
        html += `
            <div class="news-card">
                <h3><a href="${escapeHtml(article.url)}" target="_blank">${escapeHtml(article.title)}</a></h3>
                <div class="news-meta">
                    <span class="source">📰 ${escapeHtml(article.source)}</span>
                    <span class="country">🌍 ${escapeHtml(article.country)}</span>
                    <span class="date">📅 ${escapeHtml(article.date)}</span>
                </div>
                <p class="summary">${escapeHtml(article.summary)}</p>
                ${article.themes ? `<div class="themes">🏷️ ${article.themes.join(' · ')}</div>` : ''}
            </div>
        `;
    });
    
    latestNews.innerHTML = html;
}

// Save to cache
function saveToCache(query, country, data) {
    const key = `gdelt_${query}_${country}`;
    const cacheItem = {
        timestamp: Date.now(),
        data: data
    };
    localStorage.setItem(key, JSON.stringify(cacheItem));
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
    
    // Try file cache
    try {
        const filename = query.toLowerCase().replace(/[^a-z0-9]+/g, '_').substring(0, 50);
        const countrySuffix = country ? `_${country}` : '';
        const response = await fetch(`news/search/${filename}${countrySuffix}.json?t=${Date.now()}`);
        if (response.ok) {
            return await response.json();
        }
    } catch (e) {
        // No file cache
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
        !(s.query === query && s.country === country)
    )].slice(0, 10);
    
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
    displaySearchHistory();
}

// Display search history
function displaySearchHistory() {
    const historyContainer = document.getElementById('search-history');
    if (!historyContainer) return;
    
    if (searchHistory.length === 0) {
        historyContainer.innerHTML = '<p>No search history yet</p>';
        return;
    }
    
    let html = '<h3>Recent Searches:</h3><div class="history-list">';
    searchHistory.forEach(search => {
        html += `
            <button class="history-item" onclick="replaySearch('${search.query}', '${search.country}')">
                🔍 ${escapeHtml(search.query)} ${search.country !== 'all' ? `(${search.country})` : ''}
            </button>
        `;
    });
    html += '</div>';
    
    historyContainer.innerHTML = html;
}

// Replay a search
window.replaySearch = function(query, country) {
    searchInput.value = query;
    if (country !== 'all') {
        countrySelect.value = country;
    }
    fetchFreshNews(query, country);
};

// Show success message
function showSuccess(message) {
    const toast = document.createElement('div');
    toast.className = 'toast success';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Show warning message
function showWarning(message) {
    const toast = document.createElement('div');
    toast.className = 'toast warning';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Show error message
function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'toast error';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Load latest news from JSON file
async function loadLatestNews() {
    showLoading();
    try {
        const response = await fetch('news/latest.json?t=' + Date.now());
        if (!response.ok) throw new Error('Failed to load');
        const data = await response.json();
        newsData.latest = data;
        displaySearchResults(data.articles || []);
    } catch (error) {
        console.error('Error loading latest news:', error);
        latestNews.innerHTML = '<div class="error">Failed to load news. Will retry soon.</div>';
    } finally {
        hideLoading();
    }
}

// Load trending data
async function loadTrending() {
    try {
        const response = await fetch('news/trending.json?t=' + Date.now());
        if (!response.ok) throw new Error('Failed to load');
        const data = await response.json();
        trendingData = data.trends || [];
        displayTrending(trendingData);
    } catch (error) {
        console.error('Error loading trending:', error);
    }
}

// Display trending topics
function displayTrending(trends) {
    if (!trends || trends.length === 0) {
        trendingTopics.innerHTML = '<div class="no-results">No trending data available</div>';
        return;
    }
    
    let html = '';
    trends.slice(0, 15).forEach((trend, index) => {
        html += `
            <div class="trend-item" data-date="${trend.date}">
                <span class="trend-rank">#${index + 1}</span>
                <span class="trend-date">${formatDate(trend.date)}</span>
                <span class="trend-value">Volume: ${trend.value.toLocaleString()}</span>
            </div>
        `;
    });
    
    trendingTopics.innerHTML = html;
}

// Update last update timestamp
function updateTimestamp() {
    const now = new Date();
    lastUpdate.textContent = now.toLocaleString();
}

// Helper: Show loading
function showLoading() {
    loading.style.display = 'block';
}

// Helper: Hide loading
function hideLoading() {
    loading.style.display = 'none';
}

// Helper: Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper: Format date
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

// Perform search (cached version)
async function performSearch() {
    const query = searchInput.value.trim() || 'technology';
    const country = countrySelect.value;
    
    currentQuery = query;
    
    const cached = await loadCachedSearch(query, country);
    if (cached) {
        displaySearchResults(cached.articles);
        showSuccess('Loaded from cache');
    } else {
        fetchFreshNews(query, country);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Search button
    searchBtn.addEventListener('click', performSearch);
    
    // Enter key in search input
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    
    // Tab switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(`${btn.dataset.tab}-tab`).classList.add('active');
        });
    });
    
    // Saved search buttons
    document.querySelectorAll('.saved-search').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            searchInput.value = query;
            performSearch();
        });
    });
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
