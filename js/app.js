// Global state management
const AppState = {
    papers: [],
    filteredPapers: [],
    currentPage: 'home',
    selectedDates: new Set(),
    availableDates: [],
    loadedDates: new Set(), // Track which dates have been loaded
    dateFileMapping: {}, // Map dates to their file names
    calendarMode: 'single', // 'single' or 'range'
    calendarRangeStart: null,
    calendarRangeEnd: null,
    currentCalendarMonth: new Date().getMonth(),
    currentCalendarYear: new Date().getFullYear(),
    filters: {
        journals: new Set(),
        collections: new Set(),
        searchQuery: ''
    },
    favorites: {},
    favoritesFolders: ['Default'],
    updateInfo: null,
    language: localStorage.getItem('preferredLanguage') || 'Chinese',
    isAuthenticated: false,
    username: '',
    hideEmptyAbstracts: true // Default: hide papers without abstracts
};

// ============================================
// Authentication Functions
// ============================================

async function checkAuth() {
    /**
     * Check if the user is authenticated.
     * Returns true if authenticated, false otherwise.
     */
    try {
        const response = await fetch('/api/auth/check', {
            credentials: 'include'
        });
        if (response.ok) {
            const data = await response.json();
            AppState.isAuthenticated = data.authenticated;
            AppState.username = data.username || '';
            return data.authenticated;
        }
    } catch (error) {
        console.error('Failed to check authentication:', error);
    }
    AppState.isAuthenticated = false;
    return false;
}

function showLoginScreen() {
    /**
     * Show the login screen and hide the app.
     */
    const loginScreen = document.getElementById('login-screen');
    const appContainer = document.getElementById('app-container');
    
    if (loginScreen) loginScreen.style.display = 'flex';
    if (appContainer) appContainer.style.display = 'none';
}

function showAppScreen() {
    /**
     * Show the app and hide the login screen.
     */
    const loginScreen = document.getElementById('login-screen');
    const appContainer = document.getElementById('app-container');
    
    if (loginScreen) loginScreen.style.display = 'none';
    if (appContainer) appContainer.style.display = 'flex';
}

async function handleLogin(event) {
    /**
     * Handle the login form submission.
     */
    event.preventDefault();
    
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const errorDiv = document.getElementById('login-error');
    const loginBtn = document.getElementById('login-btn');
    
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    
    // Clear previous error
    if (errorDiv) errorDiv.textContent = '';
    
    // Disable button and show loading state
    if (loginBtn) {
        loginBtn.disabled = true;
        loginBtn.innerHTML = '<span class="btn-text">Signing in...</span><i class="fa-solid fa-spinner fa-spin"></i>';
    }
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === 'success') {
            // Login successful
            AppState.isAuthenticated = true;
            AppState.username = data.username;
            
            // Clear form
            usernameInput.value = '';
            passwordInput.value = '';
            
            // Show app
            showAppScreen();
            
            // Initialize the app
            await initMainApp();
        } else {
            // Login failed
            if (errorDiv) {
                errorDiv.textContent = data.message || 'Login failed. Please try again.';
            }
        }
    } catch (error) {
        console.error('Login error:', error);
        if (errorDiv) {
            errorDiv.textContent = 'Connection error. Please try again.';
        }
    } finally {
        // Re-enable button
        if (loginBtn) {
            loginBtn.disabled = false;
            loginBtn.innerHTML = '<span class="btn-text">Sign In</span><i class="fa-solid fa-arrow-right"></i>';
        }
    }
}

async function handleLogout() {
    /**
     * Handle the logout action.
     */
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            // Clear app state
            AppState.isAuthenticated = false;
            AppState.username = '';
            AppState.papers = [];
            AppState.filteredPapers = [];
            AppState.favorites = {};
            AppState.favoritesFolders = ['Default'];
            AppState.loadedDates.clear();
            AppState.selectedDates.clear();
            
            // Show login screen
            showLoginScreen();
        } else {
            console.error('Logout failed');
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Data loading functions
async function loadUpdateInfo() {
    try {
        const response = await fetch('data/cache/update.json');
        AppState.updateInfo = await response.json();
        displayUpdateInfo();
    } catch (error) {
        console.error('Failed to load update info:', error);
    }
}

async function loadFavoritesFromServer() {
    try {
        const response = await fetch('/api/favorites');
        if (response.ok) {
            AppState.favorites = await response.json();
            console.log('Favorites loaded from server:', AppState.favorites);
        } else {
            console.warn('Failed to load favorites from server, using default');
            AppState.favorites = {};
        }
    } catch (error) {
        console.error('Failed to load favorites:', error);
        AppState.favorites = {};
    }
}

async function loadFavoritesFoldersFromServer() {
    try {
        const response = await fetch('/api/favorites/folders');
        if (response.ok) {
            AppState.favoritesFolders = await response.json();
            console.log('Folders loaded from server:', AppState.favoritesFolders);
        } else {
            console.warn('Failed to load folders from server, using default');
            AppState.favoritesFolders = ['Default'];
        }
    } catch (error) {
        console.error('Failed to load folders:', error);
        AppState.favoritesFolders = ['Default'];
    }
}

async function loadFileList() {
    /**
     * Load file list and build date-to-file mapping without loading actual papers.
     * This is fast and allows us to know what dates are available.
     */
    try {
        const fileListResponse = await fetch('data/cache/file-list.txt');
        const fileListText = await fileListResponse.text();
        
        // Parse file list (one file per line)
        const files = fileListText.trim().split('\n')
            .map(line => line.trim())
            .filter(line => line && line.endsWith('.jsonl'));
        
        const availableDates = [];
        const dateFileMapping = {};
        
        for (const fileName of files) {
            // Extract date from filename (e.g., "2025-11-03_nature.jsonl" -> "2025-11-03")
            const dateMatch = fileName.match(/(\d{4}-\d{2}-\d{2})/);
            const fileDate = dateMatch ? dateMatch[1] : null;
            
            if (fileDate) {
                if (!availableDates.includes(fileDate)) {
                    availableDates.push(fileDate);
                    dateFileMapping[fileDate] = [];
                }
                dateFileMapping[fileDate].push(fileName);
            }
        }
        
        // Sort dates descending
        availableDates.sort((a, b) => b.localeCompare(a));
        
        AppState.availableDates = availableDates;
        AppState.dateFileMapping = dateFileMapping;
        
        console.log(`Available dates: ${availableDates.join(', ')}`);
        console.log('Date-file mapping built');
        
    } catch (error) {
        console.error('Failed to load file list:', error);
    }
}

async function loadPapersForDate(date) {
    /**
     * Load papers for a specific date.
     * Returns the loaded papers.
     */
    if (AppState.loadedDates.has(date)) {
        console.log(`Papers for ${date} already loaded, skipping`);
        return [];
    }
    
    const files = AppState.dateFileMapping[date] || [];
    const papers = [];
    
    for (const fileName of files) {
        // Extract date and source from filename
        const dateMatch = fileName.match(/(\d{4}-\d{2}-\d{2})/);
        const fileDate = dateMatch ? dateMatch[1] : null;
        
        const sourceMatch = fileName.match(/\d{4}-\d{2}-\d{2}_([^.]+)\.jsonl/);
        const source = sourceMatch ? sourceMatch[1] : 'unknown';
        
        // Try to load AI enhanced version first
        const baseName = fileName.replace('.jsonl', '');
        const enhancedPath = `data/${baseName}_AI_enhanced_${AppState.language}.jsonl`;
        const originalPath = `data/${fileName}`;
        
        try {
            let response = await fetch(enhancedPath);
            let loadedFrom = enhancedPath;
            
            if (!response.ok) {
                // Fallback to original file
                response = await fetch(originalPath);
                loadedFrom = originalPath;
            }
            
            if (response.ok) {
                const text = await response.text();
                const lines = text.trim().split('\n');
                for (const line of lines) {
                    if (line.trim()) {
                        const paper = JSON.parse(line);
                        // Add file date and source to paper object
                        paper.fileDate = fileDate;
                        paper.source = source;
                        papers.push(paper);
                    }
                }
                console.log(`Loaded ${lines.length} papers from ${loadedFrom} (date: ${fileDate})`);
            }
        } catch (error) {
            console.error(`Failed to load papers from ${fileName}:`, error);
        }
    }
    
    AppState.loadedDates.add(date);
    return papers;
}

async function loadPapersForDates(dates) {
    /**
     * Load papers for multiple dates.
     * Only loads dates that haven't been loaded yet.
     */
    const newPapers = [];
    
    for (const date of dates) {
        const papers = await loadPapersForDate(date);
        newPapers.push(...papers);
    }
    
    // Add to global papers list
    AppState.papers.push(...newPapers);
    
    console.log(`Loaded ${newPapers.length} new papers, total: ${AppState.papers.length}`);
    
    // Update filter options
    extractFilterOptions();
    
    return newPapers;
}

async function loadInitialPapers() {
    /**
     * Load only the initial set of papers:
     * 1. Today's date (or most recent date)
     * 2. Papers that are in favorites (to ensure they can be displayed)
     */
    try {
        // First load the file list to know what's available
        await loadFileList();
        
        if (AppState.availableDates.length === 0) {
            console.log('No dates available');
            return;
        }
        
        // Determine the default date (today or most recent)
        const today = new Date().toISOString().split('T')[0]; // Format: YYYY-MM-DD
        const defaultDate = AppState.availableDates.includes(today) ? today : AppState.availableDates[0];
        
        console.log(`Loading initial papers for date: ${defaultDate}`);
        
        // Load papers for the default date
        await loadPapersForDates([defaultDate]);
        
        // Automatically select the default date
        AppState.selectedDates.add(defaultDate);
        console.log(`Default date selected: ${defaultDate}`);
        
        // Now check if there are favorite papers from other dates that need to be loaded
        await loadFavoritePapers();
        
    } catch (error) {
        console.error('Failed to load initial papers:', error);
    }
}

async function loadFavoritePapers() {
    /**
     * Load favorited papers from the centralized cache.
     * This is much faster than searching through individual date files.
     */
    try {
        const response = await fetch('/api/favorites/papers');
        if (response.ok) {
            const favoritePapers = await response.json();
            
            if (favoritePapers.length === 0) {
                console.log('No favorite papers in cache');
                return;
            }
            
            console.log(`Loading ${favoritePapers.length} favorite papers from cache`);
            
            // Add favorite papers to the global papers list if not already present
            const loadedPaperIds = new Set(AppState.papers.map(p => p.id));
            const newFavoritePapers = favoritePapers.filter(paper => !loadedPaperIds.has(paper.id));
            
            if (newFavoritePapers.length > 0) {
                AppState.papers.push(...newFavoritePapers);
                console.log(`Added ${newFavoritePapers.length} favorite papers from cache`);
                
                // Update filter options
                extractFilterOptions();
            } else {
                console.log('All favorite papers already loaded');
            }
        } else {
            console.warn('Failed to load favorite papers from cache');
        }
    } catch (error) {
        console.error('Failed to load favorite papers:', error);
    }
}

function extractFilterOptions() {
    const journals = new Set();
    const collections = new Set();
    
    AppState.papers.forEach(paper => {
        if (paper.journal) journals.add(paper.journal);
        if (paper.collection && Array.isArray(paper.collection)) {
            paper.collection.forEach(c => collections.add(c));
        }
    });
    
    return { journals: Array.from(journals), collections: Array.from(collections) };
}

// Display functions
function displayUpdateInfo() {
    if (!AppState.updateInfo) return;
    
    const container = document.getElementById('update-info');
    if (!container) return;
    
    const lastUpdated = new Date(AppState.updateInfo.last_updated).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    let html = `
        <div class="update-card">
            <div class="update-header">
                <i class="fa-solid fa-bell"></i>
                <h3>Latest Update</h3>
            </div>
            <div class="update-time">Last updated: ${lastUpdated}</div>
            <div class="update-sources">
    `;
    
    AppState.updateInfo.message.forEach(source => {
        html += `
            <div class="update-source">
                <div class="source-name">${source.source.toUpperCase()}</div>
                <div class="source-stats">
                    <span class="stat-item"><i class="fa-solid fa-file"></i> Total: ${source.total_papers}</span>
                    <span class="stat-item"><i class="fa-solid fa-plus"></i> New: ${source.new_papers}</span>
                    <span class="stat-item"><i class="fa-solid fa-check"></i> With Abstract: ${source.new_papers_with_abs}</span>
                </div>
            </div>
        `;
    });
    
    html += `
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function displayPapers() {
    const container = document.getElementById('papers-container');
    if (!container) return;
    
    // Sort all papers by score.max in descending order
    const sortedPapers = [...AppState.filteredPapers].sort((a, b) => {
        const scoreA = a.score && a.score.max ? a.score.max : 0;
        const scoreB = b.score && b.score.max ? b.score.max : 0;
        return scoreB - scoreA;
    });
    
    // Check if there are no papers to display
    if (sortedPapers.length === 0) {
        container.innerHTML = `
            <div class="no-papers-container">
                <div class="no-papers-icon">
                    <i class="fa-solid fa-mug-hot"></i>
                </div>
                <h2 class="no-papers-title">No Paper Today. Take a Rest!</h2>
                <p class="no-papers-subtitle">There are no papers matching your current filters.</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="cards-container">';
    
    sortedPapers.forEach(paper => {
        const collection = paper.collection && paper.collection.length > 0 ? paper.collection[0] : 'Uncategorized';
        const authors = paper.authors ? paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ', et al.' : '') : 'Unknown';
        const tldr = paper.AI && paper.AI.tldr && paper.AI.tldr !== 'Error' && paper.AI.tldr !== 'Skip' ? paper.AI.tldr : 'No summary available';
        const isFavorite = isInFavorites(paper.id);
        const score = paper.score && paper.score.max ? paper.score.max.toFixed(2) : 'N/A';
        const fileDate = paper.fileDate || 'Unknown';
        const source = paper.source || 'unknown';
        const logoPath = `assets/${source}.png`;
        
        html += `
            <div class="card" data-paper-id="${paper.id}">
                <div class="favorite-icon ${isFavorite ? 'favorited' : ''}" onclick="toggleFavorite(event, '${paper.id}')">
                    <i class="fa-${isFavorite ? 'solid' : 'regular'} fa-star"></i>
                </div>
                <div class="card-content">
                    <div class="card-date">${fileDate}</div>
                    <div class="card-tag">${collection}</div>
                    <div class="card-score">Score: ${score}</div>
                    <h2>${paper.title}</h2>
                    <p class="paper-authors">${authors}</p>
                    <p class="paper-summary">${tldr}</p>
                    <div class="card-footer">
                        <button class="card-button" onclick="showPaperDetails('${paper.id}')">See More</button>
                        <img src="${logoPath}" alt="${source}" class="card-logo" onerror="this.style.display='none'">
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    container.innerHTML = html;
}

function displayFilters() {
    const filterContainer = document.getElementById('filters-container');
    if (!filterContainer) return;
    
    const { journals, collections } = extractFilterOptions();
    
    let html = `
        <div class="filters-section">
            <div class="filter-group">
                <label><i class="fa-solid fa-book"></i> Journal</label>
                <div class="filter-options">
                    <button class="filter-tag ${AppState.filters.journals.size === 0 ? 'active' : ''}" 
                            onclick="clearFilter('journals')">All</button>
    `;
    
    journals.forEach(journal => {
        const isActive = AppState.filters.journals.has(journal);
        html += `
            <button class="filter-tag ${isActive ? 'active' : ''}" 
                    onclick="toggleFilter('journals', '${journal}')">
                ${journal}
            </button>
        `;
    });
    
    html += `
                </div>
            </div>
            <div class="filter-group">
                <label><i class="fa-solid fa-folder"></i> Collection</label>
                <div class="filter-options">
                    <button class="filter-tag ${AppState.filters.collections.size === 0 ? 'active' : ''}" 
                            onclick="clearFilter('collections')">All</button>
    `;
    
    collections.forEach(collection => {
        const isActive = AppState.filters.collections.has(collection);
        html += `
            <button class="filter-tag ${isActive ? 'active' : ''}" 
                    onclick="toggleFilter('collections', '${collection}')">
                ${collection}
            </button>
        `;
    });
    
    html += `
                </div>
            </div>
        </div>
    `;
    
    filterContainer.innerHTML = html;
}

function displaySearchBar() {
    const searchContainer = document.getElementById('search-container');
    if (!searchContainer) return;
    
    // Display selected dates summary
    let selectedText = 'All Dates';
    if (AppState.selectedDates.size > 0) {
        const dates = Array.from(AppState.selectedDates).sort();
        if (AppState.calendarMode === 'range' && dates.length > 1) {
            selectedText = `${dates[0]} to ${dates[dates.length - 1]}`;
        } else if (dates.length === 1) {
            selectedText = dates[0];
        } else {
            selectedText = `${dates.length} dates selected`;
        }
    }
    
    searchContainer.innerHTML = `
        <div class="search-and-date-container">
            <div class="search-box">
                <i class="fa-solid fa-search"></i>
                <input type="text" id="search-input" placeholder="Search papers by title, authors, or keywords..." 
                       value="${AppState.filters.searchQuery}" oninput="handleSearch(this.value)">
                ${AppState.filters.searchQuery ? '<i class="fa-solid fa-times clear-search" onclick="clearSearch()"></i>' : ''}
            </div>
            <div class="abstract-toggle-container">
                <label class="abstract-toggle-label">
                    <span class="toggle-text">Show No-Abstract</span>
                    <input type="checkbox" ${!AppState.hideEmptyAbstracts ? 'checked' : ''} 
                           onchange="toggleEmptyAbstracts(this.checked)">
                    <span class="abstract-toggle-slider"></span>
                </label>
            </div>
            <div class="date-picker-button-container">
                <button class="calendar-trigger-btn" onclick="openCalendarModal()">
                    <i class="fa-solid fa-calendar-days"></i>
                    <span>${selectedText}</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </button>
                ${AppState.selectedDates.size > 0 ? `
                    <button class="clear-dates-btn" onclick="clearAllDates()">
                        <i class="fa-solid fa-times"></i>
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

function displayDatePicker() {
    // Date picker is now part of the search bar
    // This function is kept for compatibility but does nothing
}

function openCalendarModal() {
    const modal = document.getElementById('calendar-modal');
    const modalContent = document.getElementById('calendar-modal-content');
    
    // Initialize calendar to current month if no dates selected
    if (AppState.selectedDates.size > 0) {
        const firstDate = Array.from(AppState.selectedDates).sort()[0];
        const dateObj = new Date(firstDate);
        AppState.currentCalendarMonth = dateObj.getMonth();
        AppState.currentCalendarYear = dateObj.getFullYear();
    }
    
    renderCalendar();
    modal.classList.add('active');
}

function closeCalendarModal() {
    const modal = document.getElementById('calendar-modal');
    modal.classList.remove('active');
}

function renderCalendar() {
    const modalContent = document.getElementById('calendar-modal-content');
    
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
    
    const firstDay = new Date(AppState.currentCalendarYear, AppState.currentCalendarMonth, 1);
    const lastDay = new Date(AppState.currentCalendarYear, AppState.currentCalendarMonth + 1, 0);
    const prevLastDay = new Date(AppState.currentCalendarYear, AppState.currentCalendarMonth, 0);
    
    const firstDayOfWeek = firstDay.getDay();
    const lastDate = lastDay.getDate();
    const prevLastDate = prevLastDay.getDate();
    
    let html = `
        <div class="calendar-modal-header">
            <h2>Select Date</h2>
            <button class="modal-close" onclick="closeCalendarModal()">
                <i class="fa-solid fa-times"></i>
            </button>
        </div>
        <div class="calendar-controls">
            <button class="calendar-nav-btn" onclick="previousMonth()">
                <i class="fa-solid fa-chevron-left"></i>
            </button>
            <div class="calendar-month-year">
                <select class="month-select" onchange="changeMonth(this.value)">
    `;
    
    monthNames.forEach((month, index) => {
        html += `<option value="${index}" ${index === AppState.currentCalendarMonth ? 'selected' : ''}>${month}</option>`;
    });
    
    html += `
                </select>
                <input type="number" class="year-input" value="${AppState.currentCalendarYear}" 
                       onchange="changeYear(this.value)" min="2020" max="2030">
            </div>
            <button class="calendar-nav-btn" onclick="nextMonth()">
                <i class="fa-solid fa-chevron-right"></i>
            </button>
        </div>
        <div class="calendar-weekdays">
            <div class="weekday">Sun</div>
            <div class="weekday">Mon</div>
            <div class="weekday">Tue</div>
            <div class="weekday">Wed</div>
            <div class="weekday">Thu</div>
            <div class="weekday">Fri</div>
            <div class="weekday">Sat</div>
        </div>
        <div class="calendar-days">
    `;
    
    // Previous month's days
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
        const day = prevLastDate - i;
        html += `<div class="calendar-day prev-month">${day}</div>`;
    }
    
    // Current month's days
    for (let day = 1; day <= lastDate; day++) {
        const dateStr = `${AppState.currentCalendarYear}-${String(AppState.currentCalendarMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const isAvailable = AppState.availableDates.includes(dateStr);
        const isSelected = AppState.selectedDates.has(dateStr);
        const isInRange = isDateInRange(dateStr);
        
        let classes = 'calendar-day';
        if (!isAvailable) classes += ' disabled';
        if (isSelected) classes += ' selected';
        if (isInRange) classes += ' in-range';
        
        html += `
            <div class="${classes}" onclick="${isAvailable ? `selectDate('${dateStr}')` : ''}">
                ${day}
                ${isAvailable ? '<div class="day-dot"></div>' : ''}
            </div>
        `;
    }
    
    // Next month's days
    const remainingDays = 42 - (firstDayOfWeek + lastDate);
    for (let day = 1; day <= remainingDays; day++) {
        html += `<div class="calendar-day next-month">${day}</div>`;
    }
    
    html += `
        </div>
        <div class="calendar-footer">
            <div class="calendar-mode-toggle">
                <label class="toggle-label">
                    <span>Range</span>
                    <input type="checkbox" ${AppState.calendarMode === 'range' ? 'checked' : ''} 
                           onchange="toggleCalendarMode(this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            <button class="calendar-apply-btn" onclick="applyCalendarSelection()">
                Apply
            </button>
        </div>
    `;
    
    modalContent.innerHTML = html;
}

function isDateInRange(dateStr) {
    if (AppState.calendarMode !== 'range' || AppState.selectedDates.size < 2) return false;
    
    const dates = Array.from(AppState.selectedDates).sort();
    return dateStr >= dates[0] && dateStr <= dates[dates.length - 1];
}

function selectDate(dateStr) {
    if (AppState.calendarMode === 'single') {
        AppState.selectedDates.clear();
        AppState.selectedDates.add(dateStr);
    } else {
        // Range mode
        if (AppState.selectedDates.size === 0) {
            AppState.selectedDates.add(dateStr);
        } else if (AppState.selectedDates.size === 1) {
            const firstDate = Array.from(AppState.selectedDates)[0];
            if (dateStr === firstDate) {
                AppState.selectedDates.delete(dateStr);
            } else {
                // Add all dates in range
                const start = dateStr < firstDate ? dateStr : firstDate;
                const end = dateStr < firstDate ? firstDate : dateStr;
                
                AppState.selectedDates.clear();
                AppState.availableDates.forEach(date => {
                    if (date >= start && date <= end) {
                        AppState.selectedDates.add(date);
                    }
                });
            }
        } else {
            // Reset and start new selection
            AppState.selectedDates.clear();
            AppState.selectedDates.add(dateStr);
        }
    }
    renderCalendar();
}

function toggleCalendarMode(isRange) {
    AppState.calendarMode = isRange ? 'range' : 'single';
    if (!isRange && AppState.selectedDates.size > 1) {
        const firstDate = Array.from(AppState.selectedDates).sort()[0];
        AppState.selectedDates.clear();
        AppState.selectedDates.add(firstDate);
    }
    renderCalendar();
}

function previousMonth() {
    AppState.currentCalendarMonth--;
    if (AppState.currentCalendarMonth < 0) {
        AppState.currentCalendarMonth = 11;
        AppState.currentCalendarYear--;
    }
    renderCalendar();
}

function nextMonth() {
    AppState.currentCalendarMonth++;
    if (AppState.currentCalendarMonth > 11) {
        AppState.currentCalendarMonth = 0;
        AppState.currentCalendarYear++;
    }
    renderCalendar();
}

function changeMonth(month) {
    AppState.currentCalendarMonth = parseInt(month);
    renderCalendar();
}

function changeYear(year) {
    AppState.currentCalendarYear = parseInt(year);
    renderCalendar();
}

function applyCalendarSelection() {
    closeCalendarModal();
    displaySearchBar(); // Update date display in the button
    applyFilters();
}

function clearAllDates() {
    AppState.selectedDates.clear();
    displaySearchBar(); // Update date display in the button
    applyFilters();
}

function toggleEmptyAbstracts(showEmpty) {
    AppState.hideEmptyAbstracts = !showEmpty;
    applyFilters();
}

// Filter functions
function toggleFilter(type, value) {
    if (AppState.filters[type].has(value)) {
        AppState.filters[type].delete(value);
    } else {
        AppState.filters[type].add(value);
    }
    applyFilters();
}

function clearFilter(type) {
    AppState.filters[type].clear();
    applyFilters();
}

function handleSearch(query) {
    AppState.filters.searchQuery = query;
    applyFilters();
}

function clearSearch() {
    AppState.filters.searchQuery = '';
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    displaySearchBar(); // Re-render to remove the clear button
    applyFilters();
}

async function applyFilters() {
    // Load papers for selected dates if not already loaded
    if (AppState.selectedDates.size > 0) {
        const datesToLoad = [...AppState.selectedDates].filter(date => !AppState.loadedDates.has(date));
        if (datesToLoad.length > 0) {
            console.log(`Loading papers for newly selected dates: ${datesToLoad.join(', ')}`);
            await loadPapersForDates(datesToLoad);
        }
    }
    
    let filtered = AppState.papers;
    
    // Apply date filter (only if dates are explicitly selected)
    if (AppState.selectedDates.size > 0) {
        filtered = filtered.filter(paper => 
            AppState.selectedDates.has(paper.fileDate)
        );
    }
    
    // Apply journal filter
    if (AppState.filters.journals.size > 0) {
        filtered = filtered.filter(paper => 
            AppState.filters.journals.has(paper.journal)
        );
    }
    
    // Apply collection filter
    if (AppState.filters.collections.size > 0) {
        filtered = filtered.filter(paper => 
            paper.collection && paper.collection.some(c => AppState.filters.collections.has(c))
        );
    }
    
    // Apply search filter
    if (AppState.filters.searchQuery) {
        const query = AppState.filters.searchQuery.toLowerCase();
        filtered = filtered.filter(paper => {
            const title = (paper.title || '').toLowerCase();
            const authors = (paper.authors || []).join(' ').toLowerCase();
            const summary = (paper.summary || '').toLowerCase();
            const tldr = (paper.AI && paper.AI.tldr ? paper.AI.tldr : '').toLowerCase();
            
            return title.includes(query) || authors.includes(query) || 
                   summary.includes(query) || tldr.includes(query);
        });
    }
    
    // Apply empty abstract filter
    if (AppState.hideEmptyAbstracts) {
        filtered = filtered.filter(paper => {
            const summary = paper.summary || '';
            return summary.trim() !== '';
        });
    }
    
    AppState.filteredPapers = filtered;
    displayPapers();
    displayFilters();
    // Don't re-render search bar during search to maintain input focus
    // displaySearchBar();
    displayDatePicker();
}

// Date picker functions
function toggleDate(date) {
    if (AppState.selectedDates.has(date)) {
        AppState.selectedDates.delete(date);
    } else {
        AppState.selectedDates.add(date);
    }
    applyFilters();
}

function selectAllDates() {
    if (AppState.selectedDates.size === AppState.availableDates.length) {
        // Deselect all
        AppState.selectedDates.clear();
    } else {
        // Select all
        AppState.selectedDates.clear();
        AppState.availableDates.forEach(date => AppState.selectedDates.add(date));
    }
    applyFilters();
}

// Paper details modal
function showPaperDetails(paperId) {
    const paper = AppState.papers.find(p => p.id === paperId);
    if (!paper) return;
    
    const modal = document.getElementById('paper-modal');
    const modalContent = document.getElementById('modal-content');
    
    const authors = paper.authors ? paper.authors.join(', ') : 'Unknown';
    
    // Build collections with scores
    let collectionsWithScores = 'None';
    if (paper.collection && paper.collection.length > 0) {
        const collectionItems = paper.collection.map(collection => {
            const score = paper.score && paper.score[collection] !== undefined 
                ? paper.score[collection].toFixed(3) 
                : 'N/A';
            return `${collection}: ${score}`;
        });
        collectionsWithScores = collectionItems.join(', ');
    }
    
    const hasAI = paper.AI && typeof paper.AI === 'object' && paper.AI.tldr !== 'Error' && paper.AI.tldr !== 'Skip';
    
    let html = `
        <div class="modal-header">
            <h2>${paper.title}</h2>
            <button class="modal-close" onclick="closePaperDetails()">
                <i class="fa-solid fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            <div class="paper-meta">
                <div class="meta-item">
                    <i class="fa-solid fa-book"></i>
                    <span><strong>Journal:</strong> ${paper.journal || 'Unknown'}</span>
                </div>
                <div class="meta-item">
                    <i class="fa-solid fa-calendar"></i>
                    <span><strong>Published:</strong> ${paper.published || 'Unknown'}</span>
                </div>
                <div class="meta-item">
                    <i class="fa-solid fa-folder"></i>
                    <span><strong>Collections:</strong> ${collectionsWithScores}</span>
                </div>
                <div class="meta-item">
                    <i class="fa-solid fa-tag"></i>
                    <span><strong>Category:</strong> ${paper.category || 'Unknown'}</span>
                </div>
            </div>
            
            <div class="paper-authors-full">
                <h3><i class="fa-solid fa-users"></i> Authors</h3>
                <p>${authors}</p>
            </div>
            
            ${hasAI ? `
                <div class="ai-summary">
                    <h3><i class="fa-solid fa-brain"></i> AI-Generated Summary</h3>
                    
                    <div class="summary-section tldr-section">
                        <h4>TL;DR</h4>
                        <p>${paper.AI.tldr}</p>
                    </div>
                    
                    <div class="summary-grid">
                        <div class="summary-section">
                            <h4>Motivation</h4>
                            <p>${paper.AI.motivation}</p>
                        </div>
                        
                        <div class="summary-section">
                            <h4>Method</h4>
                            <p>${paper.AI.method}</p>
                        </div>
                        
                        <div class="summary-section">
                            <h4>Result</h4>
                            <p>${paper.AI.result}</p>
                        </div>
                        
                        <div class="summary-section">
                            <h4>Conclusion</h4>
                            <p>${paper.AI.conclusion}</p>
                        </div>
                    </div>
                </div>
            ` : ''}
            
            <div class="paper-abstract">
                <h3><i class="fa-solid fa-align-left"></i> Original Abstract</h3>
                <p>${paper.summary || 'No abstract available'}</p>
            </div>
            
            ${paper.AI && paper.AI.summary_translated ? `
            <div class="paper-abstract translated-abstract">
                <h3><i class="fa-solid fa-language"></i> Translated Abstract</h3>
                <p>${paper.AI.summary_translated}</p>
            </div>
            ` : ''}
        </div>
        <div class="modal-footer">
            <div class="footer-info">
                <i class="fa-solid fa-info-circle"></i>
                <span>Paper Details</span>
            </div>
            <div class="footer-links">
                ${paper.abs ? `<a href="${paper.abs}" target="_blank" class="footer-link">
                    <i class="fa-solid fa-file-alt"></i>
                    <span>Abstract</span>
                </a>` : ''}
                ${paper.pdf ? `<a href="${paper.pdf}" target="_blank" class="footer-link">
                    <i class="fa-solid fa-file-pdf"></i>
                    <span>PDF</span>
                </a>` : ''}
            </div>
        </div>
    `;
    
    modalContent.innerHTML = html;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closePaperDetails() {
    const modal = document.getElementById('paper-modal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

// Favorites system
function isInFavorites(paperId) {
    for (const folder in AppState.favorites) {
        if (AppState.favorites[folder].includes(paperId)) {
            return true;
        }
    }
    return false;
}

function toggleFavorite(event, paperId) {
    event.stopPropagation();
    
    if (isInFavorites(paperId)) {
        // Remove from favorites
        for (const folder in AppState.favorites) {
            AppState.favorites[folder] = AppState.favorites[folder].filter(id => id !== paperId);
            if (AppState.favorites[folder].length === 0 && folder !== 'Default') {
                delete AppState.favorites[folder];
            }
        }
        saveFavorites();
        
        if (AppState.currentPage === 'papers') {
            displayPapers();
        } else if (AppState.currentPage === 'favorites') {
            displayFavorites();
        }
    } else {
        // Add to favorites - show folder selection modal
        showFolderSelectionModal(paperId);
    }
}

function showFolderSelectionModal(paperId) {
    const modal = document.getElementById('folder-modal');
    const modalContent = document.getElementById('folder-modal-content');
    
    let html = `
        <div class="modal-header">
            <h2>Add to Favorites</h2>
            <button class="modal-close" onclick="closeFolderModal()">
                <i class="fa-solid fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            <p>Select a folder to add this paper:</p>
            <div class="folder-list">
    `;
    
    AppState.favoritesFolders.forEach(folder => {
        html += `
            <button class="folder-option" onclick="addToFavoritesFolder('${paperId}', '${folder}')">
                <i class="fa-solid fa-folder"></i> ${folder}
            </button>
        `;
    });
    
    html += `
            </div>
            <div class="create-folder">
                <input type="text" id="new-folder-name" placeholder="New folder name...">
                <button onclick="createAndAddToFolder('${paperId}')">
                    <i class="fa-solid fa-plus"></i> Create & Add
                </button>
            </div>
        </div>
    `;
    
    modalContent.innerHTML = html;
    modal.classList.add('active');
}

function closeFolderModal() {
    const modal = document.getElementById('folder-modal');
    modal.classList.remove('active');
}

function addToFavoritesFolder(paperId, folder) {
    if (!AppState.favorites[folder]) {
        AppState.favorites[folder] = [];
    }
    if (!AppState.favorites[folder].includes(paperId)) {
        AppState.favorites[folder].push(paperId);
    }
    saveFavorites();
    closeFolderModal();
    
    if (AppState.currentPage === 'papers') {
        displayPapers();
    } else if (AppState.currentPage === 'favorites') {
        displayFavorites();
    }
}

function createAndAddToFolder(paperId) {
    const input = document.getElementById('new-folder-name');
    const folderName = input.value.trim();
    
    if (!folderName) {
        alert('Please enter a folder name');
        return;
    }
    
    if (!AppState.favoritesFolders.includes(folderName)) {
        AppState.favoritesFolders.push(folderName);
        saveFavoritesFolders();
    }
    
    addToFavoritesFolder(paperId, folderName);
}

async function saveFavorites() {
    try {
        const response = await fetch('/api/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(AppState.favorites)
        });
        
        if (response.ok) {
            console.log('Favorites saved to server');
        } else {
            console.error('Failed to save favorites to server');
        }
    } catch (error) {
        console.error('Error saving favorites:', error);
    }
}

function displayFavorites() {
    const container = document.getElementById('favorites-container');
    if (!container) return;
    
    let html = '';
    
    if (Object.keys(AppState.favorites).length === 0 || 
        Object.values(AppState.favorites).every(arr => arr.length === 0)) {
        html = `
            <div class="empty-favorites">
                <i class="fa-solid fa-star"></i>
                <h3>No favorites yet</h3>
                <p>Start adding papers to your favorites from the Papers page!</p>
            </div>
        `;
    } else {
        for (const folder in AppState.favorites) {
            if (AppState.favorites[folder].length > 0) {
                const papers = AppState.favorites[folder].map(id => 
                    AppState.papers.find(p => p.id === id)
                ).filter(p => p);
                
                html += `
                    <div class="favorites-folder">
                        <div class="folder-header">
                            <h3><i class="fa-solid fa-folder"></i> ${folder}</h3>
                            <span class="paper-count">${papers.length} papers</span>
                            ${folder !== 'Default' ? `<button class="delete-folder" onclick="deleteFolder('${folder}')">
                                <i class="fa-solid fa-trash"></i>
                            </button>` : ''}
                        </div>
                        <div class="cards-container">
                `;
                
                papers.forEach(paper => {
                    const collection = paper.collection && paper.collection.length > 0 ? paper.collection[0] : 'Uncategorized';
                    const authors = paper.authors ? paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ', et al.' : '') : 'Unknown';
                    const tldr = paper.AI && paper.AI.tldr && paper.AI.tldr !== 'Error' && paper.AI.tldr !== 'Skip' ? paper.AI.tldr : 'No summary available';
                    const score = paper.score && paper.score.max ? paper.score.max.toFixed(2) : 'N/A';
                    const fileDate = paper.fileDate || 'Unknown';
                    const source = paper.source || 'unknown';
                    const logoPath = `assets/${source}.png`;
                    
                    html += `
                        <div class="card" data-paper-id="${paper.id}">
                            <div class="favorite-icon favorited" onclick="toggleFavorite(event, '${paper.id}')">
                                <i class="fa-solid fa-star"></i>
                            </div>
                            <div class="card-content">
                                <div class="card-date">${fileDate}</div>
                                <div class="card-tag">${collection}</div>
                                <div class="card-score">Score: ${score}</div>
                                <h2>${paper.title}</h2>
                                <p class="paper-authors">${authors}</p>
                                <p class="paper-summary">${tldr}</p>
                                <div class="card-footer">
                                    <button class="card-button" onclick="showPaperDetails('${paper.id}')">See More</button>
                                    <img src="${logoPath}" alt="${source}" class="card-logo" onerror="this.style.display='none'">
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
            }
        }
    }
    
    container.innerHTML = html;
}

function deleteFolder(folderName) {
    if (confirm(`Are you sure you want to delete the folder "${folderName}"?`)) {
        delete AppState.favorites[folderName];
        AppState.favoritesFolders = AppState.favoritesFolders.filter(f => f !== folderName);
        saveFavorites();
        saveFavoritesFolders();
        displayFavorites();
    }
}

async function saveFavoritesFolders() {
    try {
        const response = await fetch('/api/favorites/folders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(AppState.favoritesFolders)
        });
        
        if (response.ok) {
            console.log('Folders saved to server');
        } else {
            console.error('Failed to save folders to server');
        }
    } catch (error) {
        console.error('Error saving folders:', error);
    }
}

// Page navigation
function navigateTo(page) {
    // Update nav items
    document.querySelectorAll('.nav-list li').forEach(li => {
        li.classList.remove('active');
    });
    
    event.currentTarget.classList.add('active');
    
    // Hide all pages
    document.querySelectorAll('.page-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Show selected page
    const pageElement = document.getElementById(`${page}-page`);
    if (pageElement) {
        pageElement.classList.add('active');
        AppState.currentPage = page;
        
        // Load page-specific content
        if (page === 'papers') {
            displayDatePicker();
            displayFilters();
            displaySearchBar();
            applyFilters(); // Apply filters to show default date selection
        } else if (page === 'favorites') {
            displayFavorites();
        } else if (page === 'settings') {
            loadSettingsPage();
        } else if (page === 'analytics') {
            displayAnalytics();
        }
    }
}

// Settings page functions
function loadSettingsPage() {
    const currentLanguage = AppState.language;
    const radioButtons = document.querySelectorAll('input[name="language"]');
    radioButtons.forEach(radio => {
        radio.checked = radio.value === currentLanguage;
    });
}

function saveLanguagePreference() {
    const selectedLanguage = document.querySelector('input[name="language"]:checked').value;
    
    if (selectedLanguage !== AppState.language) {
        AppState.language = selectedLanguage;
        localStorage.setItem('preferredLanguage', selectedLanguage);
        
        // Show success message
        alert(`Language preference saved: ${selectedLanguage}\n\nThe page will reload to apply changes.`);
        
        // Reload papers with new language
        location.reload();
    } else {
        alert('Language preference saved!');
    }
}

// Back to top functionality
function toggleBackToTopButton() {
    const backToTopButton = document.getElementById('back-to-top');
    if (window.scrollY > 300) {
        backToTopButton.classList.add('visible');
    } else {
        backToTopButton.classList.remove('visible');
    }
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// ============================================
// Analytics Functions
// ============================================

function getAnalyticsPapers() {
    /**
     * Get papers for analytics based on current date selection from papers page.
     * Uses the same date filter as the papers page for consistency.
     */
    let papers = AppState.papers;
    
    // Apply the same date filter as the papers page
    if (AppState.selectedDates.size > 0) {
        papers = papers.filter(paper => 
            AppState.selectedDates.has(paper.fileDate)
        );
    }
    
    return papers;
}

function computeAnalyticsData(papers) {
    /**
     * Compute all analytics metrics from the given papers.
     */
    const analytics = {
        overview: {
            totalPapers: papers.length,
            uniqueJournals: new Set(papers.map(p => p.journal).filter(Boolean)).size,
            uniqueCollections: new Set(papers.flatMap(p => p.collection || [])).size,
            avgScore: 0,
            highScorePapers: 0
        },
        categories: {},
        collections: {},
        sources: {},
        journals: {},
        authors: {},
        scores: [],
        ai: {
            success: 0,
            skip: 0,
            error: 0,
            translated: 0,
            fields: {
                tldr: { filled: 0, empty: 0 },
                motivation: { filled: 0, empty: 0 },
                method: { filled: 0, empty: 0 },
                result: { filled: 0, empty: 0 },
                conclusion: { filled: 0, empty: 0 },
                summary_translated: { filled: 0, empty: 0 }
            },
            bySource: {}
        },
        topPapers: []
    };
    
    let totalScore = 0;
    let scoredPapers = 0;
    
    papers.forEach(paper => {
        // Categories (from arXiv category field)
        if (paper.category && Array.isArray(paper.category)) {
            paper.category.forEach(cat => {
                analytics.categories[cat] = (analytics.categories[cat] || 0) + 1;
            });
        }
        
        // Collections (from Zotero matching)
        if (paper.collection && Array.isArray(paper.collection)) {
            paper.collection.forEach(col => {
                analytics.collections[col] = (analytics.collections[col] || 0) + 1;
            });
        }
        
        // Sources
        const source = paper.source || 'unknown';
        analytics.sources[source] = (analytics.sources[source] || 0) + 1;
        
        // Journals
        if (paper.journal) {
            analytics.journals[paper.journal] = (analytics.journals[paper.journal] || 0) + 1;
        }
        
        // Authors
        if (paper.authors && Array.isArray(paper.authors)) {
            paper.authors.forEach(author => {
                if (author && author.trim()) {
                    analytics.authors[author] = (analytics.authors[author] || 0) + 1;
                }
            });
        }
        
        // Scores
        if (paper.score && paper.score.max !== undefined) {
            analytics.scores.push(paper.score.max);
            totalScore += paper.score.max;
            scoredPapers++;
            if (paper.score.max >= 5.0) {
                analytics.overview.highScorePapers++;
            }
        }
        
        // AI metrics
        const aiStatus = getAIStatus(paper);
        analytics.ai[aiStatus]++;
        
        // Track by source
        if (!analytics.ai.bySource[source]) {
            analytics.ai.bySource[source] = { success: 0, skip: 0, error: 0, total: 0 };
        }
        analytics.ai.bySource[source][aiStatus]++;
        analytics.ai.bySource[source].total++;
        
        // AI field completion
        if (paper.AI) {
            ['tldr', 'motivation', 'method', 'result', 'conclusion', 'summary_translated'].forEach(field => {
                if (paper.AI[field] && paper.AI[field] !== 'Error' && paper.AI[field] !== 'Skip' && paper.AI[field].trim()) {
                    analytics.ai.fields[field].filled++;
                } else {
                    analytics.ai.fields[field].empty++;
                }
            });
            
            if (paper.AI.summary_translated && paper.AI.summary_translated.trim()) {
                analytics.ai.translated++;
            }
        } else {
            Object.keys(analytics.ai.fields).forEach(field => {
                analytics.ai.fields[field].empty++;
            });
        }
    });
    
    // Calculate average score
    analytics.overview.avgScore = scoredPapers > 0 ? (totalScore / scoredPapers).toFixed(2) : 0;
    
    // Get top 10 papers by score
    analytics.topPapers = [...papers]
        .filter(p => p.score && p.score.max !== undefined)
        .sort((a, b) => b.score.max - a.score.max)
        .slice(0, 10);
    
    return analytics;
}

function getAIStatus(paper) {
    if (!paper.AI) return 'skip';
    if (paper.AI.tldr === 'Error') return 'error';
    if (paper.AI.tldr === 'Skip') return 'skip';
    if (paper.AI.tldr && paper.AI.tldr.trim()) return 'success';
    return 'skip';
}

function displayAnalytics() {
    const papers = getAnalyticsPapers();
    const analytics = computeAnalyticsData(papers);
    
    // Display date info
    displayAnalyticsDateInfo();
    
    // Display all sections
    displayAnalyticsOverview(analytics);
    displayTrendingCategories(analytics);
    displayCollectionsRadar(analytics);
    displayKeywordCloud(papers);
    displayTopPapers(analytics);
    displayScoreDistribution(analytics);
    displayScoreThreshold(analytics);
    displayPapersBySource(analytics);
    displaySourceScoreComparison(analytics, papers);
    displayTopAuthors(analytics);
    displayAISuccessRate(analytics);
    displayAIFieldCompletion(analytics);
    displayAIBySource(analytics);
}

function displayAnalyticsDateInfo() {
    const container = document.getElementById('analytics-date-info');
    if (!container) return;
    
    let dateText = 'All available data';
    if (AppState.selectedDates.size > 0) {
        const dates = Array.from(AppState.selectedDates).sort();
        if (dates.length === 1) {
            dateText = `Data for ${dates[0]}`;
        } else {
            dateText = `Data from ${dates[0]} to ${dates[dates.length - 1]} (${dates.length} days)`;
        }
    }
    
    container.innerHTML = `
        <div class="date-info-banner">
            <i class="fa-solid fa-calendar-days"></i>
            <span>${dateText}</span>
            <span class="date-hint">(Synced with Papers page date selection)</span>
        </div>
    `;
}

function displayAnalyticsOverview(analytics) {
    const container = document.getElementById('analytics-overview');
    if (!container) return;
    
    const successRate = analytics.overview.totalPapers > 0 
        ? ((analytics.ai.success / analytics.overview.totalPapers) * 100).toFixed(1) 
        : 0;
    
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-icon"><i class="fa-solid fa-file-lines"></i></div>
            <div class="stat-content">
                <div class="stat-value">${analytics.overview.totalPapers}</div>
                <div class="stat-label">Total Papers</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fa-solid fa-chart-line"></i></div>
            <div class="stat-content">
                <div class="stat-value">${analytics.overview.avgScore}</div>
                <div class="stat-label">Avg. Score</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fa-solid fa-star"></i></div>
            <div class="stat-content">
                <div class="stat-value">${analytics.overview.highScorePapers}</div>
                <div class="stat-label">High Score (≥5.0)</div>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon"><i class="fa-solid fa-robot"></i></div>
            <div class="stat-content">
                <div class="stat-value">${successRate}%</div>
                <div class="stat-label">AI Success Rate</div>
            </div>
        </div>
    `;
}

function displayTrendingCategories(analytics) {
    const container = document.getElementById('trending-categories');
    if (!container) return;
    
    // Combine categories and collections for trending
    const allTopics = { ...analytics.categories };
    Object.entries(analytics.collections).forEach(([col, count]) => {
        allTopics[col] = (allTopics[col] || 0) + count;
    });
    
    const sorted = Object.entries(allTopics)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    const maxCount = sorted.length > 0 ? sorted[0][1] : 1;
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-fire"></i>
            <h4>Trending Topics</h4>
        </div>
        <div class="trending-list">
    `;
    
    sorted.forEach(([topic, count], index) => {
        const percentage = (count / maxCount) * 100;
        html += `
            <div class="trending-item">
                <span class="trending-rank">${index + 1}</span>
                <span class="trending-name">${topic}</span>
                <div class="trending-bar-container">
                    <div class="trending-bar" style="width: ${percentage}%"></div>
                </div>
                <span class="trending-count">${count}</span>
            </div>
        `;
    });
    
    if (sorted.length === 0) {
        html += '<div class="no-data">No category data available</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function displayCollectionsRadar(analytics) {
    const container = document.getElementById('collections-radar');
    if (!container) return;
    
    const sorted = Object.entries(analytics.collections)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8);
    
    const total = sorted.reduce((sum, [, count]) => sum + count, 0);
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-layer-group"></i>
            <h4>Collection Distribution</h4>
        </div>
        <div class="collection-list">
    `;
    
    sorted.forEach(([collection, count]) => {
        const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
        html += `
            <div class="collection-item">
                <div class="collection-info">
                    <span class="collection-name">${collection}</span>
                    <span class="collection-stats">${count} papers (${percentage}%)</span>
                </div>
                <div class="collection-bar-container">
                    <div class="collection-bar" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    });
    
    if (sorted.length === 0) {
        html += '<div class="no-data">No collection data available</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function extractKeywords(papers) {
    /**
     * Extract keywords from paper titles, abstracts (summary), and AI-generated TL;DRs.
     * Filters out common stop words and returns word frequency map.
     */
    const stopWords = new Set([
        // English stop words
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'it', 'its', 'this', 'that', 'these', 'those', 'i', 'we', 'you',
        'he', 'she', 'they', 'what', 'which', 'who', 'whom', 'when', 'where',
        'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
        'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there',
        'into', 'over', 'after', 'before', 'between', 'under', 'again',
        'further', 'then', 'once', 'during', 'while', 'about', 'against',
        'above', 'below', 'up', 'down', 'out', 'off', 'through', 'any',
        'our', 'their', 'your', 'his', 'her', 'if', 'because', 'until',
        'being', 'having', 'doing', 'using', 'based', 'via', 'per', 'however',
        'show', 'shows', 'shown', 'showing', 'use', 'uses', 'used', 'using',
        'new', 'paper', 'papers', 'study', 'studies', 'work', 'works',
        'propose', 'proposed', 'proposes', 'present', 'presents', 'presented',
        'approach', 'method', 'methods', 'result', 'results', 'demonstrate',
        'demonstrates', 'demonstrated', 'provide', 'provides', 'provided',
        'develop', 'develops', 'developed', 'achieve', 'achieves', 'achieved',
        'improve', 'improves', 'improved', 'compared', 'existing', 'different',
        'first', 'two', 'three', 'one', 'well', 'high', 'low', 'large', 'small',
        'can', 'et', 'al', 'etc', 'e.g', 'i.e', 'arxiv', 'abstract',
        'here', 'find', 'found', 'report', 'reports', 'reported', 'discuss',
        'discusses', 'discussed', 'consider', 'considers', 'considered',
        'investigate', 'investigates', 'investigated', 'analysis', 'analyze',
        'analyzes', 'analyzed', 'introduce', 'introduces', 'introduced',
        'show', 'shows', 'showed', 'establish', 'establishes', 'established',
        'describe', 'describes', 'described', 'determine', 'determines',
        'determined', 'suggest', 'suggests', 'suggested', 'reveal', 'reveals',
        'revealed', 'indicate', 'indicates', 'indicated', 'explore', 'explores',
        'explored', 'obtain', 'obtains', 'obtained', 'allow', 'allows', 'allowed',
        'enable', 'enables', 'enabled', 'require', 'requires', 'required'
    ]);
    
    const wordFreq = {};
    
    papers.forEach(paper => {
        // Extract from title
        const title = paper.title || '';
        
        // Extract from abstract/summary if available
        const summary = (paper.summary && 
                        paper.summary !== 'No Summary Available' &&
                        paper.summary.trim()) ? paper.summary : '';
        
        // Extract from TL;DR if available
        const tldr = (paper.AI && paper.AI.tldr && 
                     paper.AI.tldr !== 'Error' && 
                     paper.AI.tldr !== 'Skip') ? paper.AI.tldr : '';
        
        // Combine text sources (title, abstract, and TL;DR)
        const text = `${title} ${summary} ${tldr}`.toLowerCase();
        
        // Extract words (alphanumeric, allowing hyphens for compound terms)
        const words = text.match(/[a-z][a-z0-9-]*[a-z0-9]/g) || [];
        
        words.forEach(word => {
            // Skip stop words and very short words
            if (word.length < 3 || stopWords.has(word)) return;
            // Skip words that are just numbers
            if (/^\d+$/.test(word)) return;
            
            wordFreq[word] = (wordFreq[word] || 0) + 1;
        });
    });
    
    // Sort by frequency and take top words
    const sorted = Object.entries(wordFreq)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 60);
    
    return sorted;
}

function displayKeywordCloud(papers) {
    const container = document.getElementById('keyword-cloud');
    if (!container) return;
    
    const keywords = extractKeywords(papers);
    
    if (keywords.length === 0) {
        container.innerHTML = `
            <div class="card-header">
                <i class="fa-solid fa-cloud"></i>
                <h4>Research Keywords</h4>
            </div>
            <div class="no-data">No keyword data available</div>
        `;
        return;
    }
    
    const maxFreq = keywords[0][1];
    const minFreq = keywords[keywords.length - 1][1];
    
    // Shuffle keywords for more natural cloud appearance
    const shuffled = [...keywords].sort(() => Math.random() - 0.5);
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-cloud"></i>
            <h4>Research Keywords</h4>
            <span class="keyword-count">${keywords.length} keywords from ${papers.length} papers</span>
        </div>
        <div class="word-cloud">
    `;
    
    shuffled.forEach(([word, count]) => {
        // Calculate font size based on frequency (scale from 0.7 to 2.2)
        const normalized = maxFreq === minFreq ? 0.5 : 
            (count - minFreq) / (maxFreq - minFreq);
        const fontSize = 0.75 + (normalized * 1.5);
        
        // Calculate opacity based on frequency
        const opacity = 0.6 + (normalized * 0.4);
        
        // Assign color class based on frequency tier
        let colorClass = 'keyword-low';
        if (normalized > 0.7) colorClass = 'keyword-high';
        else if (normalized > 0.4) colorClass = 'keyword-medium';
        
        html += `
            <span class="cloud-word ${colorClass}" 
                  style="font-size: ${fontSize}rem; opacity: ${opacity}"
                  title="${word}: ${count} occurrences">
                ${word}
            </span>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displayTopPapers(analytics) {
    const container = document.getElementById('top-papers');
    if (!container) return;
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-trophy"></i>
            <h4>Top Scoring Papers</h4>
        </div>
        <div class="top-papers-table">
            <div class="table-header">
                <span class="col-score">Score</span>
                <span class="col-title">Title</span>
                <span class="col-collection">Collection</span>
                <span class="col-source">Source</span>
            </div>
    `;
    
    analytics.topPapers.forEach(paper => {
        const score = paper.score.max.toFixed(2);
        const collection = paper.collection && paper.collection[0] ? paper.collection[0] : 'N/A';
        const source = paper.source || 'unknown';
        const truncatedTitle = paper.title.length > 80 ? paper.title.substring(0, 80) + '...' : paper.title;
        
        html += `
            <div class="table-row" onclick="showPaperDetails('${paper.id}')">
                <span class="col-score score-badge">${score}</span>
                <span class="col-title" title="${paper.title}">${truncatedTitle}</span>
                <span class="col-collection">${collection}</span>
                <span class="col-source">${source}</span>
            </div>
        `;
    });
    
    if (analytics.topPapers.length === 0) {
        html += '<div class="no-data">No scored papers available</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function displayScoreDistribution(analytics) {
    const container = document.getElementById('score-distribution');
    if (!container) return;
    
    // Create histogram buckets
    const buckets = {
        '0-2': 0,
        '2-3': 0,
        '3-4': 0,
        '4-5': 0,
        '5-6': 0,
        '6-7': 0,
        '7+': 0
    };
    
    analytics.scores.forEach(score => {
        if (score < 2) buckets['0-2']++;
        else if (score < 3) buckets['2-3']++;
        else if (score < 4) buckets['3-4']++;
        else if (score < 5) buckets['4-5']++;
        else if (score < 6) buckets['5-6']++;
        else if (score < 7) buckets['6-7']++;
        else buckets['7+']++;
    });
    
    const maxCount = Math.max(...Object.values(buckets), 1);
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-chart-bar"></i>
            <h4>Score Distribution</h4>
        </div>
        <div class="histogram">
    `;
    
    Object.entries(buckets).forEach(([range, count]) => {
        const height = (count / maxCount) * 100;
        html += `
            <div class="histogram-bar-container">
                <div class="histogram-bar" style="height: ${height}%">
                    <span class="histogram-count">${count}</span>
                </div>
                <span class="histogram-label">${range}</span>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displayScoreThreshold(analytics) {
    const container = document.getElementById('score-threshold');
    if (!container) return;
    
    const total = analytics.scores.length || 1;
    const thresholds = [
        { label: 'Score ≥ 7.0', count: analytics.scores.filter(s => s >= 7).length },
        { label: 'Score ≥ 6.0', count: analytics.scores.filter(s => s >= 6).length },
        { label: 'Score ≥ 5.0', count: analytics.scores.filter(s => s >= 5).length },
        { label: 'Score ≥ 4.0', count: analytics.scores.filter(s => s >= 4).length },
        { label: 'Score ≥ 3.0', count: analytics.scores.filter(s => s >= 3).length }
    ];
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-filter"></i>
            <h4>Score Threshold Analysis</h4>
        </div>
        <div class="threshold-list">
    `;
    
    thresholds.forEach(({ label, count }) => {
        const percentage = ((count / total) * 100).toFixed(1);
        html += `
            <div class="threshold-item">
                <span class="threshold-label">${label}</span>
                <div class="threshold-bar-container">
                    <div class="threshold-bar" style="width: ${percentage}%"></div>
                </div>
                <span class="threshold-value">${count} (${percentage}%)</span>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displayPapersBySource(analytics) {
    const container = document.getElementById('papers-by-source');
    if (!container) return;
    
    const sorted = Object.entries(analytics.sources)
        .sort((a, b) => b[1] - a[1]);
    
    const total = sorted.reduce((sum, [, count]) => sum + count, 0);
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-database"></i>
            <h4>Papers by Source</h4>
        </div>
        <div class="source-list">
    `;
    
    sorted.forEach(([source, count]) => {
        const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
        html += `
            <div class="source-item">
                <div class="source-info">
                    <img src="assets/${source}.png" alt="${source}" class="source-logo" onerror="this.style.display='none'">
                    <span class="source-name">${source.toUpperCase()}</span>
                </div>
                <div class="source-bar-container">
                    <div class="source-bar" style="width: ${percentage}%"></div>
                </div>
                <span class="source-count">${count}</span>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displaySourceScoreComparison(analytics, papers) {
    const container = document.getElementById('source-score-comparison');
    if (!container) return;
    
    // Calculate average score per source
    const sourceScores = {};
    papers.forEach(paper => {
        const source = paper.source || 'unknown';
        if (paper.score && paper.score.max !== undefined) {
            if (!sourceScores[source]) {
                sourceScores[source] = { total: 0, count: 0 };
            }
            sourceScores[source].total += paper.score.max;
            sourceScores[source].count++;
        }
    });
    
    const avgScores = Object.entries(sourceScores)
        .map(([source, data]) => ({
            source,
            avg: data.count > 0 ? (data.total / data.count).toFixed(2) : 0,
            count: data.count
        }))
        .sort((a, b) => b.avg - a.avg);
    
    const maxAvg = avgScores.length > 0 ? Math.max(...avgScores.map(s => s.avg)) : 1;
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-scale-balanced"></i>
            <h4>Avg. Score by Source</h4>
        </div>
        <div class="score-comparison-list">
    `;
    
    avgScores.forEach(({ source, avg, count }) => {
        const width = (avg / maxAvg) * 100;
        html += `
            <div class="score-comparison-item">
                <span class="comparison-source">${source.toUpperCase()}</span>
                <div class="comparison-bar-container">
                    <div class="comparison-bar" style="width: ${width}%"></div>
                </div>
                <span class="comparison-score">${avg}</span>
            </div>
        `;
    });
    
    if (avgScores.length === 0) {
        html += '<div class="no-data">No score data available</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function displayTopAuthors(analytics) {
    const container = document.getElementById('top-authors');
    if (!container) return;
    
    const sorted = Object.entries(analytics.authors)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-user-graduate"></i>
            <h4>Most Active Authors</h4>
        </div>
        <div class="authors-grid">
    `;
    
    sorted.forEach(([author, count], index) => {
        html += `
            <div class="author-chip">
                <span class="author-rank">${index + 1}</span>
                <span class="author-name">${author}</span>
                <span class="author-count">${count} papers</span>
            </div>
        `;
    });
    
    if (sorted.length === 0) {
        html += '<div class="no-data">No author data available</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function displayAISuccessRate(analytics) {
    const container = document.getElementById('ai-success-rate');
    if (!container) return;
    
    const total = analytics.ai.success + analytics.ai.skip + analytics.ai.error;
    const successRate = total > 0 ? ((analytics.ai.success / total) * 100).toFixed(1) : 0;
    const skipRate = total > 0 ? ((analytics.ai.skip / total) * 100).toFixed(1) : 0;
    const errorRate = total > 0 ? ((analytics.ai.error / total) * 100).toFixed(1) : 0;
    const translationRate = total > 0 ? ((analytics.ai.translated / total) * 100).toFixed(1) : 0;
    
    container.innerHTML = `
        <div class="card-header">
            <i class="fa-solid fa-circle-check"></i>
            <h4>AI Processing Status</h4>
        </div>
        <div class="ai-status-grid">
            <div class="ai-status-item success">
                <i class="fa-solid fa-check"></i>
                <span class="status-value">${analytics.ai.success}</span>
                <span class="status-label">Success (${successRate}%)</span>
            </div>
            <div class="ai-status-item skip">
                <i class="fa-solid fa-forward"></i>
                <span class="status-value">${analytics.ai.skip}</span>
                <span class="status-label">Skipped (${skipRate}%)</span>
            </div>
            <div class="ai-status-item error">
                <i class="fa-solid fa-xmark"></i>
                <span class="status-value">${analytics.ai.error}</span>
                <span class="status-label">Errors (${errorRate}%)</span>
            </div>
            <div class="ai-status-item translated">
                <i class="fa-solid fa-language"></i>
                <span class="status-value">${analytics.ai.translated}</span>
                <span class="status-label">Translated (${translationRate}%)</span>
            </div>
        </div>
        <div class="ai-progress-bar">
            <div class="progress-success" style="width: ${successRate}%"></div>
            <div class="progress-skip" style="width: ${skipRate}%"></div>
            <div class="progress-error" style="width: ${errorRate}%"></div>
        </div>
    `;
}

function displayAIFieldCompletion(analytics) {
    const container = document.getElementById('ai-field-completion');
    if (!container) return;
    
    const fields = [
        { key: 'tldr', label: 'TL;DR' },
        { key: 'motivation', label: 'Motivation' },
        { key: 'method', label: 'Method' },
        { key: 'result', label: 'Result' },
        { key: 'conclusion', label: 'Conclusion' },
        { key: 'summary_translated', label: 'Translation' }
    ];
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-list-check"></i>
            <h4>AI Field Completion</h4>
        </div>
        <div class="field-completion-list">
    `;
    
    fields.forEach(({ key, label }) => {
        const data = analytics.ai.fields[key];
        const total = data.filled + data.empty;
        const rate = total > 0 ? ((data.filled / total) * 100).toFixed(1) : 0;
        
        html += `
            <div class="field-completion-item">
                <span class="field-label">${label}</span>
                <div class="field-bar-container">
                    <div class="field-bar" style="width: ${rate}%"></div>
                </div>
                <span class="field-rate">${rate}%</span>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displayAIBySource(analytics) {
    const container = document.getElementById('ai-by-source');
    if (!container) return;
    
    let html = `
        <div class="card-header">
            <i class="fa-solid fa-table"></i>
            <h4>AI Success Rate by Source</h4>
        </div>
        <div class="ai-source-table">
            <div class="table-header">
                <span class="col-source">Source</span>
                <span class="col-total">Total</span>
                <span class="col-success">Success</span>
                <span class="col-skip">Skip</span>
                <span class="col-error">Error</span>
                <span class="col-rate">Success Rate</span>
            </div>
    `;
    
    Object.entries(analytics.ai.bySource)
        .sort((a, b) => b[1].total - a[1].total)
        .forEach(([source, data]) => {
            const successRate = data.total > 0 ? ((data.success / data.total) * 100).toFixed(1) : 0;
            html += `
                <div class="table-row">
                    <span class="col-source">${source.toUpperCase()}</span>
                    <span class="col-total">${data.total}</span>
                    <span class="col-success">${data.success}</span>
                    <span class="col-skip">${data.skip}</span>
                    <span class="col-error">${data.error}</span>
                    <span class="col-rate">
                        <div class="mini-bar-container">
                            <div class="mini-bar" style="width: ${successRate}%"></div>
                        </div>
                        <span>${successRate}%</span>
                    </span>
                </div>
            `;
        });
    
    if (Object.keys(analytics.ai.bySource).length === 0) {
        html += '<div class="no-data">No AI data by source available</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// Initialize main app content (after authentication)
async function initMainApp() {
    console.log('Initializing main app content...');
    
    // Load favorites and metadata first (these are fast)
    await Promise.all([
        loadUpdateInfo(),
        loadFavoritesFromServer(),
        loadFavoritesFoldersFromServer()
    ]);
    
    // Then load only the initial papers (today's date + favorites)
    await loadInitialPapers();
    
    // Display home page by default
    displayUpdateInfo();
    
    console.log('Main app initialized successfully');
}

// Initialize app
async function initApp() {
    console.log('Initializing app...');
    
    // Set up event listeners (these should always be available)
    document.addEventListener('click', (e) => {
        if (e.target.id === 'paper-modal') {
            closePaperDetails();
        }
        if (e.target.id === 'folder-modal') {
            closeFolderModal();
        }
        if (e.target.id === 'calendar-modal') {
            closeCalendarModal();
        }
    });
    
    // Add card hover effect for spotlight
    document.addEventListener('mousemove', (e) => {
        if (e.target.closest('.card')) {
            const card = e.target.closest('.card');
            const rect = card.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;
            card.style.setProperty('--x', `${x}%`);
            card.style.setProperty('--y', `${y}%`);
        }
    });
    
    // Back to top button visibility
    window.addEventListener('scroll', toggleBackToTopButton);
    
    // Check authentication status
    const isAuthenticated = await checkAuth();
    
    if (isAuthenticated) {
        // User is already authenticated, show app and load content
        showAppScreen();
        await initMainApp();
    } else {
        // User is not authenticated, show login screen
        showLoginScreen();
    }
    
    console.log('App initialized successfully');
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
