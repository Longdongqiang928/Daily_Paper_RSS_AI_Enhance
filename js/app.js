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
    language: localStorage.getItem('preferredLanguage') || 'Chinese'
};

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

// Initialize app
async function initApp() {
    console.log('Initializing app...');
    
    // Load favorites and metadata first (these are fast)
    await Promise.all([
        loadUpdateInfo(),
        loadFavoritesFromServer(),
        loadFavoritesFoldersFromServer()
    ]);
    
    // Then load only the initial papers (today's date + favorites)
    await loadInitialPapers();
    
    // Set up event listeners
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
    
    // Display home page by default
    displayUpdateInfo();
    
    console.log('App initialized successfully');
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
