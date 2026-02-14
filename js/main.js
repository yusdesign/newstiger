// ============================================
// NEWSTIGER - Guardian News Only
// Complete rewrite - no GDELT references
// ============================================

// State
let currentQuery = 'news';
let currentCountry = '';
let allArticles = [];

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

// ============================================
// INITIALIZATION
// ============================================

async function init() {
    console.log('🚀 NewsTiger starting...');
    
    // Load saved preferences
    loadPreferences();
    
    // Check URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const urlQuery = urlParams.get('q');
    const urlCountry = urlParams.get('country');
    
    if (urlQuery) {
        searchInput.value = urlQuery;
        if (urlCountry) {
            countrySelect.value = urlCountry;
            currentCountry = urlCountry;
        }
        await searchNews();
    } else {
        // Load default news
        await loadLatestNews();
    }
    
    // Load trending data
    await loadTrending();
    
    // Setup event listeners
    setupEventListeners();
    
    // Update timestamp
    updateTimestamp();
    
    console.log('✅ NewsTiger ready');
}

// ============================================
// NEWS LOADING FUNCTIONS
// ============================================

async function loadLatestNews() {
    showLoading();
    
    try {
        // Try to load from latest.json
        const response = await fetch('news/latest.json?t=' + Date.now());
        
        if (!response.ok) {
            throw new Error('Latest news not found');
        }
        
        const data = await response.json();
        
        if (data.articles && data.articles.length > 0) {
            allArticles = data.articles;
            displayArticles(allArticles, 'Latest News');
        } else {
            // No articles, load fallback
            loadFallbackNews();
        }
    } catch (error) {
        console.log('Latest news error:', error);
        loadFallbackNews();
    } finally {
        hideLoading();
    }
}

async function searchNews() {
    showLoading();
    
    const query = searchInput.value.trim() || 'news';
    const country = countrySelect.value;
    
    currentQuery = query;
    currentCountry = country;
    
    updateURL(query, country);
    
    try {
        // Map queries to actual filenames that exist
        let filename;
        const lowerQuery = query.toLowerCase();
        
        if (lowerQuery.includes('russia') || country === 'RU') {
            filename = 'news/search/russia.json';
        } else if (lowerQuery.includes('ukraine') || country === 'UA') {
            filename = 'news/search/ukraine.json';
        } else if (lowerQuery.includes('us') || country === 'US') {
            filename = 'news/search/us.json';
        } else if (lowerQuery.includes('uk') || country === 'GB') {
            filename = 'news/search/gb.json';
        } else if (lowerQuery.includes('technology')) {
            filename = 'news/search/technology.json';
        } else if (lowerQuery.includes('climate')) {
            filename = 'news/search/climate_change.json';
        } else if (lowerQuery.includes('business')) {
            filename = 'news/search/business.json';
        } else if (lowerQuery.includes('sports')) {
            filename = 'news/search/sports.json';
        } else if (lowerQuery.includes('politics')) {
            filename = 'news/search/politics.json';
        } else {
            // Default to latest.json
            filename = 'news/latest.json';
        }
        
        console.log('📁 Loading:', filename);
        const response = await fetch(filename + '?t=' + Date.now());
        
        if (response.ok) {
            const data = await response.json();
            if (data.articles && data.articles.length > 0) {
                displayArticles(data.articles, query);
            } else {
                loadFallbackNews(query);
            }
        } else {
            // If specific file fails, try latest.json
            const latestResponse = await fetch('news/latest.json?t=' + Date.now());
            if (latestResponse.ok) {
                const latestData = await latestResponse.json();
                displayArticles(latestData.articles.slice(0, 10), query);
            } else {
                loadFallbackNews(query);
            }
        }
    } catch (error) {
        console.error('Search error:', error);
        loadFallbackNews(query);
    } finally {
        hideLoading();
    }
}

async function loadTrending() {
    try {
        const response = await fetch('news/trending.json?t=' + Date.now());
        
        if (response.ok) {
            const data = await response.json();
            displayTrending(data.trends || []);
        }
    } catch (error) {
        console.log('Trending error:', error);
    }
}

// ============================================
// DISPLAY FUNCTIONS
// ============================================

function displayArticles(articles, title) {
    if (!articles || articles.length === 0) {
        latestNews.innerHTML = '<div class="no-results">No articles found</div>';
        return;
    }
    
    let html = `<div class="results-header">
        <h2>📰 ${escapeHtml(title)}</h2>
        <p class="results-count">${articles.length} articles from The Guardian</p>
    </div>`;
    
    articles.slice(0, 15).forEach(article => {
        const articleTitle = article.title || 'No title';
        const articleUrl = article.url || '#';
        const articleSource = article.source || 'The Guardian';
        const articleDate = formatDate(article.date || '');
        const articleCountry = article.country || 'Global';
        const articleSummary = (article.summary || '').substring(0, 200);
        const articleImage = article.image || '';
        const articleSection = article.section || 'News';
        
        html += `
            <div class="news-card">
                ${articleImage ? `
                    <img src="${escapeHtml(articleImage)}" 
                         alt="${escapeHtml(articleTitle)}" 
                         class="news-thumbnail"
                         onerror="this.style.display='none'">
                ` : ''}
                <div class="news-content">
                    <h3>
                        <a href="${escapeHtml(articleUrl)}" target="_blank" rel="noopener">
                            ${escapeHtml(articleTitle)}
                        </a>
                    </h3>
                    <div class="news-meta">
                        <span class="source">📰 ${escapeHtml(articleSource)}</span>
                        <span class="country">🌍 ${escapeHtml(articleCountry)}</span>
                        <span class="date">📅 ${escapeHtml(articleDate)}</span>
                        <span class="section">🏷️ ${escapeHtml(articleSection)}</span>
                    </div>
                    <p class="summary">${escapeHtml(articleSummary)}...</p>
                    <div class="news-actions">
                        <a href="${escapeHtml(articleUrl)}" 
                           target="_blank" 
                           rel="noopener"
                           class="read-more-btn">
                            📖 Read on Guardian
                        </a>
                    </div>
                </div>
            </div>
        `;
    });
    
    latestNews.innerHTML = html;
}

function displayTrending(trends) {
    if (!trends || trends.length === 0) {
        if (trendingTopics) {
            trendingTopics.innerHTML = '<div class="no-results">No trending topics</div>';
        }
        return;
    }
    
    let html = '<div class="trending-list">';
    trends.slice(0, 10).forEach((trend, index) => {
        const title = trend.title || `Topic ${index + 1}`;
        const section = trend.section || 'News';
        const date = trend.date || '';
        
        html += `
            <div class="trend-item" onclick="searchTrend('${escapeHtml(title)}')">
                <span class="trend-rank">#${index + 1}</span>
                <span class="trend-title">${escapeHtml(title)}</span>
                <span class="trend-section">${escapeHtml(section)}</span>
                <span class="trend-date">${escapeHtml(date)}</span>
            </div>
        `;
    });
    html += '</div>';
    
    if (trendingTopics) {
        trendingTopics.innerHTML = html;
    }
}

// ============================================
// FALLBACK FUNCTIONS
// ============================================

function loadFallbackNews(query = 'news') {
    const fallbackArticles = [
        {
            title: `Latest news about ${query}`,
            url: 'https://www.theguardian.com',
            source: 'The Guardian',
            date: new Date().toLocaleDateString(),
            country: 'Global',
            summary: `Stay informed with the latest developments in ${query}. Our news updates are coming soon.`,
            image: '',
            section: 'News'
        },
        {
            title: `${query} - Today's headlines`,
            url: 'https://www.theguardian.com',
            source: 'The Guardian',
            date: new Date().toLocaleDateString(),
            country: 'Global',
            summary: `Breaking news and analysis about ${query} from around the world.`,
            image: '',
            section: 'World'
        },
        {
            title: `What's new in ${query}`,
            url: 'https://www.theguardian.com',
            source: 'The Guardian',
            date: new Date().toLocaleDateString(),
            country: 'Global',
            summary: `The latest updates and stories about ${query} from The Guardian.`,
            image: '',
            section: 'Updates'
        }
    ];
    
    displayArticles(fallbackArticles, query);
    showMessage('Showing sample data - fresh news loading soon', 'info');
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    
    try {
        // Handle ISO format
        if (dateStr.includes('T')) {
            const date = new Date(dateStr);
            return date.toLocaleDateString() + ' ' + 
                   date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        }
        return dateStr;
    } catch {
        return dateStr;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateURL(query, country) {
    const url = new URL(window.location);
    url.searchParams.set('q', query);
    if (country) {
        url.searchParams.set('country', country);
    } else {
        url.searchParams.delete('country');
    }
    window.history.pushState({}, '', url);
}

function loadPreferences() {
    const savedLang = localStorage.getItem('preferred_language');
    if (savedLang) {
        document.querySelectorAll('.translation-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.lang === savedLang);
        });
    }
}

function showLoading() {
    if (loading) {
        loading.style.display = 'flex';
    }
}

function hideLoading() {
    if (loading) {
        loading.style.display = 'none';
    }
}

function showMessage(text, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = text;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function updateTimestamp() {
    if (lastUpdate) {
        const now = new Date();
        lastUpdate.textContent = now.toLocaleString();
    }
}

// Global function for trend clicks
window.searchTrend = function(title) {
    searchInput.value = title;
    searchNews();
};

// ============================================
// EVENT LISTENERS
// ============================================

function setupEventListeners() {
    // Search button
    if (searchBtn) {
        searchBtn.addEventListener('click', searchNews);
    }
    
    // Enter key
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchNews();
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
        });
    });
    
    // Country select
    if (countrySelect) {
        countrySelect.addEventListener('change', () => {
            if (searchInput.value.trim()) {
                searchNews();
            }
        });
    }
    
    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            const country = btn.dataset.country;
            if (query) {
                searchInput.value = query;
                if (country) {
                    countrySelect.value = country;
                }
                searchNews();
            }
        });
    });
    
    // Translation buttons
    document.querySelectorAll('.translation-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.translation-btn').forEach(b => 
                b.classList.remove('active')
            );
            btn.classList.add('active');
            localStorage.setItem('preferred_language', btn.dataset.lang);
            showMessage(`Language: ${btn.textContent.trim()}`);
        });
    });
}

// ============================================
// START THE APP
// ============================================

document.addEventListener('DOMContentLoaded', init);
