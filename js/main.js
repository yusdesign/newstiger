// ============================================
// NEWSTIGER - Прямой доступ к Guardian API
// ============================================

const API_ENDPOINT = 'https://script.google.com/macros/s/AKfycbzWJQgx0LxgZqg9Bqzj9vZjXQxKk0nKk0nKk0n/exec'; // Мы создадим прокси

let currentQuery = '';
let currentCountry = '';

// DOM элементы
const searchInput = document.getElementById('search-input');
const countrySelect = document.getElementById('country-select');
const searchBtn = document.getElementById('search-btn');
const loading = document.getElementById('loading');
const latestNews = document.getElementById('latest-news');
const trendingTopics = document.getElementById('trending-topics');

// Инициализация
async function init() {
    console.log('🚀 NewsTiger starting...');
    await loadLatest();
    setupEventListeners();
}

// Загрузка последних новостей
async function loadLatest() {
    showLoading();
    try {
        const response = await fetch('https://content.guardianapis.com/search?page-size=20&show-fields=headline,trailText,thumbnail&api-key=1f962fc0-b843-4a63-acb9-770f4c24a86e');
        const data = await response.json();
        
        const articles = data.response.results.map(formatArticle);
        displayArticles(articles, 'Latest News');
    } catch (error) {
        console.error('Error loading latest:', error);
        showError('Failed to load news');
    } finally {
        hideLoading();
    }
}

// Поиск новостей
async function searchNews() {
    const query = searchInput.value.trim();
    if (!query) {
        await loadLatest();
        return;
    }
    
    showLoading();
    
    try {
        const url = `https://content.guardianapis.com/search?q=${encodeURIComponent(query)}&page-size=20&show-fields=headline,trailText,thumbnail&api-key=1f962fc0-b843-4a63-acb9-770f4c24a86e`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.response && data.response.results) {
            const articles = data.response.results.map(formatArticle);
            displayArticles(articles, `Search: ${query}`);
        } else {
            showError('No results found');
        }
    } catch (error) {
        console.error('Search error:', error);
        showError('Search failed');
    } finally {
        hideLoading();
    }
}

// Форматирование статьи из Guardian API
function formatArticle(result) {
    const fields = result.fields || {};
    return {
        title: fields.headline || result.webTitle || 'No title',
        url: result.webUrl || '#',
        source: 'The Guardian',
        date: formatDate(result.webPublicationDate),
        country: sectionToCountry(result.sectionId),
        section: result.sectionName || 'News',
        summary: (fields.trailText || '').replace(/<[^>]*>/g, '').substring(0, 200) + '...',
        image: fields.thumbnail || ''
    };
}

// Отображение статей
function displayArticles(articles, title) {
    if (!articles || articles.length === 0) {
        latestNews.innerHTML = '<div class="no-results">No articles found</div>';
        return;
    }
    
    let html = `<div class="results-header">
        <h2>📰 ${escapeHtml(title)}</h2>
        <p class="results-count">${articles.length} articles from The Guardian</p>
    </div>`;
    
    articles.forEach(article => {
        html += `
            <div class="news-card">
                ${article.image ? `<img src="${escapeHtml(article.image)}" class="news-thumbnail" onerror="this.style.display='none'">` : ''}
                <div class="news-content">
                    <h3><a href="${escapeHtml(article.url)}" target="_blank">${escapeHtml(article.title)}</a></h3>
                    <div class="news-meta">
                        <span class="source">📰 ${escapeHtml(article.source)}</span>
                        <span class="country">🌍 ${escapeHtml(article.country)}</span>
                        <span class="date">📅 ${escapeHtml(article.date)}</span>
                    </div>
                    <p class="summary">${escapeHtml(article.summary)}</p>
                    <a href="${escapeHtml(article.url)}" target="_blank" class="read-more-btn">Read on Guardian</a>
                </div>
            </div>
        `;
    });
    
    latestNews.innerHTML = html;
}

// Вспомогательные функции
function sectionToCountry(section) {
    const map = {
        'us-news': 'US', 'uk-news': 'GB', 'australia-news': 'AU',
        'world/russia': 'RU', 'world/ukraine': 'UA', 'world/germany': 'DE',
        'world/france': 'FR', 'world/japan': 'JP', 'world/india': 'IN',
        'world/china': 'CN'
    };
    return map[section] || 'Global';
}

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
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

function showLoading() {
    if (loading) loading.style.display = 'flex';
}

function hideLoading() {
    if (loading) loading.style.display = 'none';
}

function showError(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast error';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function setupEventListeners() {
    searchBtn?.addEventListener('click', searchNews);
    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchNews();
    });
}

// Запуск
document.addEventListener('DOMContentLoaded', init);
