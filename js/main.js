// ============================================
// NEWSTIGER - Прямые JSONP запросы к Guardian API
// ============================================

// Конфигурация
const GUARDIAN_API = {
    key: '1f962fc0-b843-4a63-acb9-770f4c24a86e',
    url: 'https://content.guardianapis.com/search'
};

// Состояние
let currentQuery = '';
let currentCallbackId = 0;

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
    setupEventListeners();
    loadLatestNews();
}

// Загрузка последних новостей через JSONP
function loadLatestNews() {
    showLoading();
    guardianJSONP({
        'page-size': 20,
        'show-fields': 'headline,trailText,thumbnail',
        'order-by': 'newest'
    }, (data) => {
        if (data.response && data.response.status === 'ok') {
            const articles = data.response.results.map(formatArticle);
            displayArticles(articles, 'Latest News');
        } else {
            showError('Failed to load news');
        }
        hideLoading();
    });
}

// Поиск новостей
function searchNews() {
    const query = searchInput.value.trim();
    if (!query) {
        loadLatestNews();
        return;
    }
    
    showLoading();
    
    guardianJSONP({
        'q': query,
        'page-size': 20,
        'show-fields': 'headline,trailText,thumbnail'
    }, (data) => {
        if (data.response && data.response.status === 'ok') {
            const articles = data.response.results.map(formatArticle);
            displayArticles(articles, `Search: ${query}`);
        } else {
            showError('No results found');
            loadLatestNews(); // Загружаем последние новости как fallback
        }
        hideLoading();
    });
}

// Универсальная функция JSONP запроса к Guardian
function guardianJSONP(params, callback) {
    // Увеличиваем счетчик для уникального имени callback
    currentCallbackId++;
    const callbackName = `guardianCallback${currentCallbackId}`;
    
    // Создаем глобальную функцию callback
    window[callbackName] = function(data) {
        // Удаляем скрипт и глобальную функцию после вызова
        document.head.removeChild(script);
        delete window[callbackName];
        callback(data);
    };
    
    // Формируем параметры запроса
    const queryParams = {
        ...params,
        'api-key': GUARDIAN_API.key,
        'format': 'json',
        'callback': callbackName
    };
    
    // Строим URL
    const url = GUARDIAN_API.url + '?' + new URLSearchParams(queryParams).toString();
    
    // Создаем и добавляем script тег
    const script = document.createElement('script');
    script.src = url;
    script.onerror = function() {
        // Если ошибка загрузки скрипта
        document.head.removeChild(script);
        delete window[callbackName];
        callback({ response: { status: 'error', message: 'Network error' } });
        hideLoading();
    };
    document.head.appendChild(script);
}

// Форматирование статьи из ответа Guardian
function formatArticle(result) {
    const fields = result.fields || {};
    const section = result.sectionId || '';
    
    return {
        title: fields.headline || result.webTitle || 'No title',
        url: result.webUrl || '#',
        source: 'The Guardian',
        date: formatDate(result.webPublicationDate),
        country: sectionToCountry(section),
        section: result.sectionName || 'News',
        summary: (fields.trailText || '').replace(/<[^>]*>/g, '').substring(0, 200) + '...',
        image: fields.thumbnail || ''
    };
}

// Определение страны по разделу
function sectionToCountry(section) {
    const countryMap = {
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
        'world/europe-news': 'EU'
    };
    return countryMap[section] || 'Global';
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
                ${article.image ? `<img src="${escapeHtml(article.image)}" alt="${escapeHtml(article.title)}" class="news-thumbnail" onerror="this.style.display='none'">` : ''}
                <div class="news-content">
                    <h3><a href="${escapeHtml(article.url)}" target="_blank" rel="noopener">${escapeHtml(article.title)}</a></h3>
                    <div class="news-meta">
                        <span class="source">📰 ${escapeHtml(article.source)}</span>
                        <span class="country">🌍 ${escapeHtml(article.country)}</span>
                        <span class="date">📅 ${escapeHtml(article.date)}</span>
                    </div>
                    <p class="summary">${escapeHtml(article.summary)}</p>
                    <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener" class="read-more-btn">📖 Read on Guardian</a>
                </div>
            </div>
        `;
    });
    
    latestNews.innerHTML = html;
}

// Форматирование даты
function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString() + ' ' + 
               date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return dateStr;
    }
}

// Экранирование HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Управление загрузкой
function showLoading() {
    if (loading) loading.style.display = 'flex';
}

function hideLoading() {
    if (loading) loading.style.display = 'none';
}

// Показ ошибок
function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'toast error';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Настройка обработчиков событий
function setupEventListeners() {
    searchBtn?.addEventListener('click', searchNews);
    
    searchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchNews();
    });
    
    // Кнопки пресетов
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            const country = btn.dataset.country;
            
            searchInput.value = query || '';
            if (country) countrySelect.value = country;
            
            searchNews();
        });
    });
}

// Запуск
document.addEventListener('DOMContentLoaded', init);
