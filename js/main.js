// State
let currentQuery = 'technology';
let newsData = {};
let trendingData = [];

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
}

// Load latest news from JSON file
async function loadLatestNews() {
    showLoading();
    try {
        const response = await fetch('news/latest.json?t=' + Date.now());
        if (!response.ok) throw new Error('Failed to load');
        const data = await response.json();
        newsData.latest = data;
        displayLatestNews(data.articles || []);
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

// Load search results for a query
async function loadSearch(query, country = '') {
    showLoading();
    
    // Create filename from query (safe for filesystem)
    const filename = query.toLowerCase().replace(/[^a-z0-9]+/g, '_').substring(0, 50);
    const countrySuffix = country ? `_${country}` : '';
    const filePath = `news/search/${filename}${countrySuffix}.json?t=${Date.now()}`;
    
    try {
        const response = await fetch(filePath);
        if (!response.ok) {
            // If no cached file, show message
            if (response.status === 404) {
                latestNews.innerHTML = '<div class="no-results">This search hasn\'t been cached yet. Try a popular search or check back later.</div>';
            } else {
                throw new Error('Failed to load');
            }
            return;
        }
        
        const data = await response.json();
        
        // Display in appropriate tab
        if (document.querySelector('.tab-btn.active').dataset.tab === 'saved') {
            displaySavedResults(data.articles || []);
        } else {
            displayLatestNews(data.articles || []);
        }
        
    } catch (error) {
        console.error('Error loading search:', error);
        latestNews.innerHTML = '<div class="error">Failed to load search results.</div>';
    } finally {
        hideLoading();
    }
}

// Display latest news
function displayLatestNews(articles) {
    if (!articles || articles.length === 0) {
        latestNews.innerHTML = '<div class="no-results">No articles found</div>';
        return;
    }
    
    let html = '';
    articles.slice(0, 20).forEach(article => {
        html += `
            <div class="news-card">
                <h3><a href="${article.url}" target="_blank">${escapeHtml(article.title)}</a></h3>
                <div class="news-meta">
                    <span class="source">📰 ${escapeHtml(article.source)}</span>
                    <span class="country">🌍 ${escapeHtml(article.country)}</span>
                    <span class="date">📅 ${escapeHtml(article.date)}</span>
                </div>
                <p class="summary">${escapeHtml(article.summary || '')}</p>
                ${article.themes ? `<div class="themes">🏷️ ${article.themes.join(' · ')}</div>` : ''}
            </div>
        `;
    });
    
    latestNews.innerHTML = html;
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
    
    // Add click handlers to trend items
    document.querySelectorAll('.trend-item').forEach(item => {
        item.addEventListener('click', () => {
            const date = item.dataset.date;
            searchInput.value = `date:${date}`;
            performSearch();
        });
    });
}

// Display saved search results
function displaySavedResults(articles) {
    if (!articles || articles.length === 0) {
        savedResults.innerHTML = '<div class="no-results">No results for this search</div>';
        return;
    }
    
    let html = '';
    articles.slice(0, 10).forEach(article => {
        html += `
            <div class="news-card">
                <h3><a href="${article.url}" target="_blank">${escapeHtml(article.title)}</a></h3>
                <div class="news-meta">
                    <span class="source">📰 ${escapeHtml(article.source)}</span>
                    <span class="date">📅 ${escapeHtml(article.date)}</span>
                </div>
            </div>
        `;
    });
    
    savedResults.innerHTML = html;
}

// Perform search
async function performSearch() {
    const query = searchInput.value.trim() || 'technology';
    const country = countrySelect.value;
    
    currentQuery = query;
    
    // Switch to latest tab
    tabBtns.forEach(b => b.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    document.querySelector('[data-tab="latest"]').classList.add('active');
    document.getElementById('latest-tab').classList.add('active');
    
    await loadSearch(query, country);
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
        return `${year}-${month}-${day}`;
    }
    return dateStr;
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
            
            // Load appropriate content
            if (btn.dataset.tab === 'latest') {
                displayLatestNews(newsData.latest?.articles || []);
            } else if (btn.dataset.tab === 'trending') {
                displayTrending(trendingData);
            }
        });
    });
    
    // Saved search buttons
    document.querySelectorAll('.saved-search').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            searchInput.value = query;
            
            // Switch to saved tab
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            document.querySelector('[data-tab="saved"]').classList.add('active');
            document.getElementById('saved-tab').classList.add('active');
            
            loadSearch(query);
        });
    });
}

// Start the app
document.addEventListener('DOMContentLoaded', init);
