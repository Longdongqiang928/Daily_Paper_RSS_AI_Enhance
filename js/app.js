// Global state management
const AppState = {
    papers: [],
    filteredPapers: [],
    currentPage: 'home',
    selectedDates: new Set(),
    availableDates: [],
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
    favorites: JSON.parse(localStorage.getItem('favorites')) || {},
    favoritesFolders: JSON.parse(localStorage.getItem('favoritesFolders')) || ['Default'],
    updateInfo: null
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

async function loadPapers() {
    const papers = [];
    const availableDates = [];
    
    try {
        const updateResponse = await fetch('data/cache/update.json');
        const updateInfo = await updateResponse.json();
        
        for (const source of updateInfo.message) {
            if (source.total_papers > 0) {
                const outputFile = source.output_file.replace(/\\/g, '/');
                
                // Extract date from filename (e.g., "data/2025-11-03_nature.jsonl" -> "2025-11-03")
                const dateMatch = outputFile.match(/(\d{4}-\d{2}-\d{2})/);
                const fileDate = dateMatch ? dateMatch[1] : null;
                
                if (fileDate && !availableDates.includes(fileDate)) {
                    availableDates.push(fileDate);
                }
                
                // Try to load AI enhanced version first
                const basePath = outputFile.replace('.jsonl', '');
                const enhancedPath = `${basePath}_AI_enhanced_Chinese.jsonl`;
                
                try {
                    const response = await fetch(enhancedPath);
                    if (response.ok) {
                        const text = await response.text();
                        const lines = text.trim().split('\n');
                        for (const line of lines) {
                            if (line.trim()) {
                                const paper = JSON.parse(line);
                                // Add file date to paper object
                                paper.fileDate = fileDate;
                                papers.push(paper);
                            }
                        }
                        console.log(`Loaded ${lines.length} papers from ${enhancedPath} (date: ${fileDate})`);
                    } else {
                        // Fallback to original file
                        const origResponse = await fetch(outputFile);
                        const text = await origResponse.text();
                        const lines = text.trim().split('\n');
                        for (const line of lines) {
                            if (line.trim()) {
                                const paper = JSON.parse(line);
                                paper.fileDate = fileDate;
                                papers.push(paper);
                            }
                        }
                        console.log(`Loaded ${lines.length} papers from ${outputFile} (date: ${fileDate})`);
                    }
                } catch (error) {
                    console.error(`Failed to load papers from ${enhancedPath}:`, error);
                }
            }
        }
        
        // Sort dates descending
        availableDates.sort((a, b) => b.localeCompare(a));
        
        AppState.papers = papers;
        AppState.filteredPapers = papers;
        AppState.availableDates = availableDates;
        console.log(`Total papers loaded: ${papers.length}`);
        console.log(`Available dates: ${availableDates.join(', ')}`);
        
        // Initialize filters
        extractFilterOptions();
        
    } catch (error) {
        console.error('Failed to load papers:', error);
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
    
    // Sort papers by score.max in descending order
    const sortedPapers = [...AppState.filteredPapers].sort((a, b) => {
        const scoreA = a.score && a.score.max ? a.score.max : 0;
        const scoreB = b.score && b.score.max ? b.score.max : 0;
        return scoreB - scoreA;
    });
    
    // Group papers by file date
    const papersByDate = {};
    sortedPapers.forEach(paper => {
        const date = paper.fileDate || 'Unknown';
        if (!papersByDate[date]) {
            papersByDate[date] = [];
        }
        papersByDate[date].push(paper);
    });
    
    // Sort dates descending
    const sortedDates = Object.keys(papersByDate).sort((a, b) => b.localeCompare(a));
    
    let html = '';
    sortedDates.forEach(date => {
        const papers = papersByDate[date];
        html += `
            <div class="date-section">
                <div class="date-header">
                    <i class="fa-solid fa-calendar-day"></i>
                    <h3>${date}</h3>
                    <span class="paper-count">${papers.length} papers</span>
                </div>
                <div class="cards-container">
        `;
        
        papers.forEach(paper => {
            const collection = paper.collection && paper.collection.length > 0 ? paper.collection[0] : 'Uncategorized';
            const authors = paper.authors ? paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ', et al.' : '') : 'Unknown';
            const tldr = paper.AI && paper.AI.tldr && paper.AI.tldr !== 'Error' && paper.AI.tldr !== 'Skip' ? paper.AI.tldr : 'No summary available';
            const isFavorite = isInFavorites(paper.id);
            const score = paper.score && paper.score.max ? paper.score.max.toFixed(2) : 'N/A';
            
            html += `
                <div class="card" data-paper-id="${paper.id}">
                    <div class="favorite-icon ${isFavorite ? 'favorited' : ''}" onclick="toggleFavorite(event, '${paper.id}')">
                        <i class="fa-${isFavorite ? 'solid' : 'regular'} fa-star"></i>
                    </div>
                    <div class="card-content">
                        <div class="card-tag">${collection}</div>
                        <div class="card-score">Score: ${score}</div>
                        <h2>${paper.title}</h2>
                        <p class="paper-authors">${authors}</p>
                        <p class="paper-summary">${tldr}</p>
                        <div class="card-footer">
                            <button class="card-button" onclick="showPaperDetails('${paper.id}')">See More</button>
                            <div class="card-icon">→</div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html || '<div class="no-papers">No papers found matching your filters.</div>';
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
    applyFilters();
}

function clearAllDates() {
    AppState.selectedDates.clear();
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
    applyFilters();
}

function applyFilters() {
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
    displaySearchBar();
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
            
            <div class="paper-links">
                ${paper.abs ? `<a href="${paper.abs}" target="_blank" class="paper-link">
                    <i class="fa-solid fa-file-alt"></i> Abstract
                </a>` : ''}
                ${paper.pdf ? `<a href="${paper.pdf}" target="_blank" class="paper-link">
                    <i class="fa-solid fa-file-pdf"></i> PDF
                </a>` : ''}
            </div>
            
            ${hasAI ? `
                <div class="ai-summary">
                    <h3><i class="fa-solid fa-brain"></i> AI-Generated Summary</h3>
                    
                    <div class="summary-section">
                        <h4>TL;DR</h4>
                        <p>${paper.AI.tldr}</p>
                    </div>
                    
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
            ` : ''}
            
            <div class="paper-abstract">
                <h3><i class="fa-solid fa-align-left"></i> Original Abstract</h3>
                <p>${paper.summary || 'No abstract available'}</p>
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
        localStorage.setItem('favoritesFolders', JSON.stringify(AppState.favoritesFolders));
    }
    
    addToFavoritesFolder(paperId, folderName);
}

function saveFavorites() {
    localStorage.setItem('favorites', JSON.stringify(AppState.favorites));
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
                    
                    html += `
                        <div class="card" data-paper-id="${paper.id}">
                            <div class="favorite-icon favorited" onclick="toggleFavorite(event, '${paper.id}')">
                                <i class="fa-solid fa-star"></i>
                            </div>
                            <div class="card-content">
                                <div class="card-tag">${collection}</div>
                                <h2>${paper.title}</h2>
                                <p class="paper-authors">${authors}</p>
                                <p class="paper-summary">${tldr}</p>
                                <div class="card-footer">
                                    <button class="card-button" onclick="showPaperDetails('${paper.id}')">See More</button>
                                    <div class="card-icon">→</div>
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
        localStorage.setItem('favoritesFolders', JSON.stringify(AppState.favoritesFolders));
        displayFavorites();
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
            displayPapers();
        } else if (page === 'favorites') {
            displayFavorites();
        }
    }
}

// Initialize app
async function initApp() {
    console.log('Initializing app...');
    
    // Load data
    await Promise.all([
        loadUpdateInfo(),
        loadPapers()
    ]);
    
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
