/**
 * PDF Email Extractor - Frontend Application
 * Handles file uploads, API communication, and results display
 */

// API Configuration
const API_BASE_URL = window.location.origin;

// State
let selectedFiles = [];
let currentJobId = null;
let currentResults = null;
let currentPage = 1;
let itemsPerPage = 20;
let dupCurrentPage = 1;
let dupItemsPerPage = 10;
let currentDuplicates = [];
let filteredDuplicates = [];
let dupSearchTerm = '';

// Sort state
let sortColumn = null;
let sortDirection = 'asc'; // 'asc' or 'desc'

// Selection state - persists across pagination
let selectedEmailsSet = new Set();

// Chart instances
let emailDistributionChart = null;
let validityChart = null;
let confidenceChart = null;

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const selectedFilesSection = document.getElementById('selectedFiles');
const fileList = document.getElementById('fileList');
const clearFilesBtn = document.getElementById('clearFilesBtn');
const uploadBtn = document.getElementById('uploadBtn');
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const resultsSection = document.getElementById('resultsSection');
const resultsBody = document.getElementById('resultsBody');
const searchInput = document.getElementById('searchInput');
const filterSelect = document.getElementById('filterSelect');
const errorModal = document.getElementById('errorModal');
const errorMessage = document.getElementById('errorMessage');
const closeModal = document.getElementById('closeModal');
const errorOkBtn = document.getElementById('errorOkBtn');
const newExtractionBtn = document.getElementById('newExtractionBtn');

// ==================== Event Listeners ====================

// File input change
fileInput.addEventListener('change', handleFileSelect);

// Browse button
browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

// Drop zone click
dropZone.addEventListener('click', () => fileInput.click());

// Drag and drop events
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
    addFiles(files);
});

// Clear files
clearFilesBtn.addEventListener('click', clearFiles);

// Upload button
uploadBtn.addEventListener('click', uploadFiles);

// Search input
searchInput.addEventListener('input', debounce(filterResults, 300));

// Duplicate search input
document.getElementById('dupSearchInput').addEventListener('input', debounce(filterDuplicates, 300));

// Filter select
filterSelect.addEventListener('change', filterResults);

// Sortable column headers
document.querySelectorAll('.results-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const column = th.dataset.sort;
        if (column) {
            handleSort(column);
        }
    });
});

// Copy all emails header
document.getElementById('copyAllHeader').addEventListener('click', copyAllEmails);

// Export buttons
document.getElementById('exportCsv').addEventListener('click', () => exportResults('csv'));
document.getElementById('exportTxt').addEventListener('click', () => exportResults('txt'));
document.getElementById('exportXlsx').addEventListener('click', () => exportResults('xlsx'));

// Pagination
document.getElementById('firstPage').addEventListener('click', () => goToPage(1));
document.getElementById('prevPage').addEventListener('click', () => changePage(-1));
document.getElementById('nextPage').addEventListener('click', () => changePage(1));
document.getElementById('lastPage').addEventListener('click', () => goToPage('last'));

// Page size selector
document.getElementById('pageSizeSelect').addEventListener('change', (e) => {
    itemsPerPage = parseInt(e.target.value);
    currentPage = 1; // Reset to first page when changing page size
    filterResults();
});

// Duplicates pagination
document.getElementById('dupFirstPage').addEventListener('click', () => goToDupPage(1));
document.getElementById('dupPrevPage').addEventListener('click', () => changeDupPage(-1));
document.getElementById('dupNextPage').addEventListener('click', () => changeDupPage(1));
document.getElementById('dupLastPage').addEventListener('click', () => goToDupPage('last'));

// Duplicates page size selector
document.getElementById('dupPageSizeSelect').addEventListener('change', (e) => {
    dupItemsPerPage = parseInt(e.target.value);
    dupCurrentPage = 1;
    renderDuplicatesTable();
});

// Duplicates export buttons
document.getElementById('exportDupCsv').addEventListener('click', () => exportDuplicates('csv'));
document.getElementById('exportDupTxt').addEventListener('click', () => exportDuplicates('txt'));

// Scroll buttons
document.getElementById('scrollToTop').addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

document.getElementById('scrollToBottom').addEventListener('click', () => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
});

// Modal close
closeModal.addEventListener('click', hideError);
errorOkBtn.addEventListener('click', hideError);
errorModal.addEventListener('click', (e) => {
    if (e.target === errorModal) hideError();
});

// New extraction
newExtractionBtn.addEventListener('click', resetApp);

// Select all checkbox - toggles all emails (not just current page)
document.getElementById('selectAll').addEventListener('change', (e) => {
    if (e.target.checked) {
        // Select all emails from current results
        if (currentResults && currentResults.emails) {
            currentResults.emails.forEach(email => selectedEmailsSet.add(email.email));
        }
    } else {
        // Deselect all
        selectedEmailsSet.clear();
    }
    // Update checkboxes on current page
    const checkboxes = resultsBody.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = e.target.checked);
    updateSelectionCount();
});

// Delegate checkbox changes in results table
resultsBody.addEventListener('change', (e) => {
    if (e.target.type === 'checkbox') {
        const email = e.target.dataset.email;
        if (email) {
            if (e.target.checked) {
                selectedEmailsSet.add(email);
            } else {
                selectedEmailsSet.delete(email);
            }
            updateSelectAllCheckbox();
            updateSelectionCount();
        }
    }
});

// ==================== File Handling ====================

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFiles(files);
}

function addFiles(files) {
    const pdfFiles = files.filter(f => f.type === 'application/pdf' || f.name.endsWith('.pdf'));
    
    if (pdfFiles.length === 0) {
        showError('Please select valid PDF files.');
        return;
    }

    // Check file sizes
    const maxSize = 20 * 1024 * 1024; // 20 MB
    const validFiles = pdfFiles.filter(f => {
        if (f.size > maxSize) {
            showError(`File "${f.name}" exceeds the 20 MB limit.`);
            return false;
        }
        return true;
    });

    // Add to selected files (avoid duplicates)
    validFiles.forEach(file => {
        if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            selectedFiles.push(file);
        }
    });

    updateFileList();
}

function updateFileList() {
    if (selectedFiles.length === 0) {
        selectedFilesSection.style.display = 'none';
        return;
    }

    selectedFilesSection.style.display = 'block';
    fileList.innerHTML = selectedFiles.map((file, index) => `
        <li>
            <span class="file-name">
                <i class="fas fa-file-pdf"></i>
                ${escapeHtml(file.name)}
            </span>
            <span class="file-size">${formatFileSize(file.size)}</span>
            <button class="remove-file" onclick="removeFile(${index})" title="Remove">
                <i class="fas fa-times"></i>
            </button>
        </li>
    `).join('');
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
}

function clearFiles() {
    selectedFiles = [];
    fileInput.value = '';
    updateFileList();
}

// ==================== Upload & Processing ====================

async function uploadFiles() {
    if (selectedFiles.length === 0) {
        showError('Please select at least one PDF file.');
        return;
    }

    // Show progress
    selectedFilesSection.style.display = 'none';
    progressSection.style.display = 'block';
    progressBar.style.width = '10%';
    progressText.textContent = 'Uploading files...';

    try {
        let jobId;

        if (selectedFiles.length === 1) {
            // Single file upload
            const formData = new FormData();
            formData.append('file', selectedFiles[0]);

            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();
            jobId = result.id;
        } else {
            // Multiple files upload
            const formData = new FormData();
            selectedFiles.forEach(file => formData.append('files', file));

            const response = await fetch(`${API_BASE_URL}/upload-multiple`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();
            // Now the backend returns a single combined job ID
            jobId = result.id;
        }

        currentJobId = jobId;
        progressBar.style.width = '30%';
        progressText.textContent = selectedFiles.length > 1 
            ? `Processing ${selectedFiles.length} PDFs...` 
            : 'Processing PDF...';

        // Poll for results
        await pollForResults(jobId);

    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message || 'Failed to upload files. Please try again.');
        resetToUpload();
    }
}

async function pollForResults(jobId) {
    const maxAttempts = 120; // 120 attempts x 2 seconds = 4 minutes max for OCR
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`${API_BASE_URL}/results/${jobId}`);
            
            if (!response.ok) {
                throw new Error('Failed to fetch results');
            }

            const result = await response.json();

            if (result.status === 'completed') {
                progressBar.style.width = '100%';
                progressText.textContent = 'Processing complete!';
                
                setTimeout(() => {
                    displayResults(result);
                }, 500);
                return;
            }

            if (result.status === 'failed') {
                throw new Error(result.error || 'Processing failed');
            }

            // Update progress
            const progress = Math.min(90, 30 + (attempts * 2));
            progressBar.style.width = `${progress}%`;
            
            if (result.status === 'processing') {
                // Show detailed page progress if available
                if (result.progress_text) {
                    progressText.textContent = result.progress_text;
                } else if (result.current_page && result.total_pages) {
                    progressText.textContent = `Processing page ${result.current_page} of ${result.total_pages}...`;
                } else if (result.file_progress) {
                    progressText.textContent = result.file_progress;
                } else if (result.current_file) {
                    progressText.textContent = `Processing: ${result.current_file}...`;
                } else {
                    progressText.textContent = 'Extracting emails from PDF...';
                }
            }

            await sleep(2000);
            attempts++;

        } catch (error) {
            console.error('Polling error:', error);
            showError(error.message || 'Error processing file');
            resetToUpload();
            return;
        }
    }

    showError('Processing timed out. Please try again with a smaller file.');
    resetToUpload();
}

// ==================== Results Display ====================

function displayResults(result) {
    currentResults = result;
    currentPage = 1;
    selectedEmailsSet.clear(); // Clear selections for new results

    // Hide progress, show results
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';

    // Update summary cards
    document.getElementById('totalCount').textContent = result.total_emails;
    document.getElementById('validCount').textContent = result.valid_emails;
    document.getElementById('invalidCount').textContent = result.invalid_emails;
    document.getElementById('duplicatesCardCount').textContent = (result.duplicates || []).length;
    document.getElementById('processingTime').textContent = `${result.processing_time.toFixed(1)}s`;

    // Display emails in table
    filterResults();
    
    // Display duplicates if any
    displayDuplicates(result.duplicates || []);
    
    // Render statistics charts
    renderStatistics(result);
}

function displayDuplicates(duplicates) {
    const duplicatesSection = document.getElementById('duplicatesSection');
    const duplicatesCount = document.getElementById('duplicatesCount');
    
    if (!duplicates || duplicates.length === 0) {
        duplicatesSection.style.display = 'none';
        currentDuplicates = [];
        return;
    }
    
    currentDuplicates = duplicates;
    filteredDuplicates = duplicates;
    dupSearchTerm = '';
    document.getElementById('dupSearchInput').value = '';
    dupCurrentPage = 1;
    duplicatesSection.style.display = 'block';
    duplicatesCount.textContent = `${duplicates.length} duplicate${duplicates.length > 1 ? 's' : ''}`;
    
    renderDuplicatesTable();
}

function renderDuplicatesTable() {
    const duplicatesBody = document.getElementById('duplicatesBody');
    
    // Pagination using filtered duplicates
    const totalPages = Math.ceil(filteredDuplicates.length / dupItemsPerPage);
    const startIndex = (dupCurrentPage - 1) * dupItemsPerPage;
    const endIndex = startIndex + dupItemsPerPage;
    const pageDuplicates = filteredDuplicates.slice(startIndex, endIndex);
    
    // Render rows with serial numbers and copy button
    duplicatesBody.innerHTML = pageDuplicates.map((dup, index) => {
        const serialNumber = startIndex + index + 1;
        return `
            <tr>
                <td class="serial-number">${serialNumber}</td>
                <td class="email">${escapeHtml(dup.email)}</td>
                <td><span class="duplicate-count-badge">${dup.count}x</span></td>
                <td>${escapeHtml(dup.domain)}</td>
                <td>
                    <button class="copy-btn" onclick="copyEmail('${escapeHtml(dup.email)}')" title="Copy email">
                        <i class="fas fa-copy"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // Update pagination controls
    const totalPagesDisplay = totalPages || 1;
    document.getElementById('dupPageInfo').textContent = `Page ${dupCurrentPage} of ${totalPagesDisplay}`;
    document.getElementById('dupFirstPage').disabled = dupCurrentPage <= 1;
    document.getElementById('dupPrevPage').disabled = dupCurrentPage <= 1;
    document.getElementById('dupNextPage').disabled = dupCurrentPage >= totalPages;
    document.getElementById('dupLastPage').disabled = dupCurrentPage >= totalPages;
    
    // Store total pages for navigation
    window.dupTotalPages = totalPages;
}

function filterDuplicates() {
    dupSearchTerm = document.getElementById('dupSearchInput').value.toLowerCase().trim();
    
    if (!dupSearchTerm) {
        filteredDuplicates = currentDuplicates;
    } else {
        filteredDuplicates = currentDuplicates.filter(dup => 
            dup.email.toLowerCase().includes(dupSearchTerm) ||
            dup.domain.toLowerCase().includes(dupSearchTerm)
        );
    }
    
    // Update count display
    const duplicatesCount = document.getElementById('duplicatesCount');
    if (dupSearchTerm) {
        duplicatesCount.textContent = `${filteredDuplicates.length} of ${currentDuplicates.length} duplicates`;
    } else {
        duplicatesCount.textContent = `${currentDuplicates.length} duplicate${currentDuplicates.length > 1 ? 's' : ''}`;
    }
    
    // Reset to first page and render
    dupCurrentPage = 1;
    renderDuplicatesTable();
}

function changeDupPage(delta) {
    dupCurrentPage += delta;
    renderDuplicatesTable();
}

function goToDupPage(page) {
    if (page === 'last') {
        dupCurrentPage = window.dupTotalPages || 1;
    } else {
        dupCurrentPage = page;
    }
    renderDuplicatesTable();
}

function exportDuplicates(format) {
    // Export filtered duplicates if search is active, otherwise all
    const duplicatesToExport = dupSearchTerm ? filteredDuplicates : currentDuplicates;
    
    if (!duplicatesToExport || duplicatesToExport.length === 0) {
        showError('No duplicates to export.');
        return;
    }
    
    let content = '';
    let filename = dupSearchTerm ? `filtered_duplicate_emails.${format}` : `duplicate_emails.${format}`;
    let mimeType = '';
    
    if (format === 'csv') {
        content = 'Email,Count,Domain\n';
        content += duplicatesToExport.map(dup => 
            `"${dup.email}",${dup.count},"${dup.domain}"`
        ).join('\n');
        mimeType = 'text/csv';
    } else if (format === 'txt') {
        content = duplicatesToExport.map(dup => 
            `${dup.email} (${dup.count}x)`
        ).join('\n');
        mimeType = 'text/plain';
    }
    
    // Download file
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showCopyToast(`Exported ${currentDuplicates.length} duplicates to ${format.toUpperCase()}`);
}

// ==================== Statistics & Charts ====================

function renderStatistics(result) {
    const duplicatesCount = (result.duplicates || []).length;
    const totalExtracted = result.total_emails + duplicatesCount;
    
    // Calculate average confidence
    let avgConfidence = 0;
    if (result.emails && result.emails.length > 0) {
        const totalConfidence = result.emails.reduce((sum, email) => sum + email.confidence, 0);
        avgConfidence = totalConfidence / result.emails.length;
    }
    
    // Update statistics summary
    document.getElementById('statTotal').textContent = totalExtracted;
    document.getElementById('statUnique').textContent = result.total_emails;
    document.getElementById('statValid').textContent = result.valid_emails;
    document.getElementById('statInvalid').textContent = result.invalid_emails;
    document.getElementById('statDuplicates').textContent = duplicatesCount;
    document.getElementById('statAvgConfidence').textContent = `${avgConfidence.toFixed(1)}%`;
    
    // Render charts
    renderEmailDistributionChart(result.total_emails, duplicatesCount);
    renderValidityChart(result.valid_emails, result.invalid_emails);
    renderConfidenceChart(result.emails || []);
}

function renderEmailDistributionChart(uniqueCount, duplicatesCount) {
    const ctx = document.getElementById('emailDistributionChart').getContext('2d');
    
    // Destroy existing chart if any
    if (emailDistributionChart) {
        emailDistributionChart.destroy();
    }
    
    const data = {
        labels: ['Unique Emails', 'Duplicates'],
        datasets: [{
            data: [uniqueCount, duplicatesCount],
            backgroundColor: ['#4f46e5', '#f59e0b'],
            borderColor: ['#4338ca', '#d97706'],
            borderWidth: 2
        }]
    };
    
    emailDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            cutout: '60%'
        }
    });
    
    // Update custom legend
    const legend = document.getElementById('distributionLegend');
    legend.innerHTML = `
        <div class="legend-item">
            <span class="legend-color" style="background-color: #4f46e5;"></span>
            <span>Unique: ${uniqueCount}</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #f59e0b;"></span>
            <span>Duplicates: ${duplicatesCount}</span>
        </div>
    `;
}

function renderValidityChart(validCount, invalidCount) {
    const ctx = document.getElementById('validityChart').getContext('2d');
    
    // Destroy existing chart if any
    if (validityChart) {
        validityChart.destroy();
    }
    
    const data = {
        labels: ['Valid', 'Invalid'],
        datasets: [{
            data: [validCount, invalidCount],
            backgroundColor: ['#10b981', '#ef4444'],
            borderColor: ['#059669', '#dc2626'],
            borderWidth: 2
        }]
    };
    
    validityChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            cutout: '60%'
        }
    });
    
    // Update custom legend
    const legend = document.getElementById('validityLegend');
    const total = validCount + invalidCount;
    const validPercent = total > 0 ? ((validCount / total) * 100).toFixed(1) : 0;
    const invalidPercent = total > 0 ? ((invalidCount / total) * 100).toFixed(1) : 0;
    
    legend.innerHTML = `
        <div class="legend-item">
            <span class="legend-color" style="background-color: #10b981;"></span>
            <span>Valid: ${validCount} (${validPercent}%)</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #ef4444;"></span>
            <span>Invalid: ${invalidCount} (${invalidPercent}%)</span>
        </div>
    `;
}

function renderConfidenceChart(emails) {
    const ctx = document.getElementById('confidenceChart').getContext('2d');
    
    // Destroy existing chart if any
    if (confidenceChart) {
        confidenceChart.destroy();
    }
    
    // Group emails by confidence ranges
    const ranges = {
        'Low (0-49%)': 0,
        'Medium (50-74%)': 0,
        'High (75-100%)': 0
    };
    
    emails.forEach(email => {
        if (email.confidence < 50) {
            ranges['Low (0-49%)']++;
        } else if (email.confidence < 75) {
            ranges['Medium (50-74%)']++;
        } else {
            ranges['High (75-100%)']++;
        }
    });
    
    const data = {
        labels: Object.keys(ranges),
        datasets: [{
            label: 'Emails',
            data: Object.values(ranges),
            backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
            borderColor: ['#dc2626', '#d97706', '#059669'],
            borderWidth: 2,
            borderRadius: 6,
            barThickness: 40
        }]
    };
    
    confidenceChart = new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
    
    // Update custom legend
    const legend = document.getElementById('confidenceLegend');
    legend.innerHTML = `
        <div class="legend-item">
            <span class="legend-color" style="background-color: #ef4444;"></span>
            <span>Low: ${ranges['Low (0-49%)']}</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #f59e0b;"></span>
            <span>Medium: ${ranges['Medium (50-74%)']}</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #10b981;"></span>
            <span>High: ${ranges['High (75-100%)']}</span>
        </div>
    `;
}

function filterResults() {
    if (!currentResults) return;

    const searchTerm = searchInput.value.toLowerCase();
    const filterValue = filterSelect.value;

    let filtered = currentResults.emails.filter(email => {
        // Search filter
        if (searchTerm && !email.email.toLowerCase().includes(searchTerm)) {
            return false;
        }

        // Status filter
        switch (filterValue) {
            case 'valid':
                return email.is_valid;
            case 'invalid':
                return !email.is_valid;
            case 'high':
                return email.confidence >= 75;
            default:
                return true;
        }
    });

    // Apply sorting if a column is selected
    if (sortColumn) {
        filtered = sortEmails(filtered, sortColumn, sortDirection);
    }

    renderTable(filtered);
}

function sortEmails(emails, column, direction) {
    const sorted = [...emails].sort((a, b) => {
        let valueA, valueB;
        
        switch (column) {
            case 'email':
                valueA = a.email.toLowerCase();
                valueB = b.email.toLowerCase();
                break;
            case 'confidence':
                valueA = a.confidence;
                valueB = b.confidence;
                break;
            case 'status':
                valueA = a.is_valid ? 1 : 0;
                valueB = b.is_valid ? 1 : 0;
                break;
            case 'domain':
                valueA = a.domain.toLowerCase();
                valueB = b.domain.toLowerCase();
                break;
            default:
                return 0;
        }
        
        if (valueA < valueB) return direction === 'asc' ? -1 : 1;
        if (valueA > valueB) return direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    return sorted;
}

function handleSort(column) {
    // Toggle direction if same column, otherwise reset to ascending
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    
    // Update sort icons
    updateSortIcons();
    
    // Re-render with sorting
    currentPage = 1; // Reset to first page when sorting
    filterResults();
}

function updateSortIcons() {
    // Reset all sort icons
    document.querySelectorAll('.results-table th.sortable').forEach(th => {
        const icon = th.querySelector('i');
        th.classList.remove('sort-asc', 'sort-desc');
        if (icon) {
            icon.className = 'fas fa-sort';
        }
    });
    
    // Set active sort icon
    if (sortColumn) {
        const activeTh = document.querySelector(`.results-table th[data-sort="${sortColumn}"]`);
        if (activeTh) {
            const icon = activeTh.querySelector('i');
            if (sortDirection === 'asc') {
                activeTh.classList.add('sort-asc');
                if (icon) icon.className = 'fas fa-sort-up';
            } else {
                activeTh.classList.add('sort-desc');
                if (icon) icon.className = 'fas fa-sort-down';
            }
        }
    }
}

function renderTable(emails) {
    // Pagination
    const totalPages = Math.ceil(emails.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageEmails = emails.slice(startIndex, endIndex);

    // Render rows with serial numbers and copy button
    resultsBody.innerHTML = pageEmails.map((email, index) => {
        const serialNumber = startIndex + index + 1;
        return `
            <tr>
                <td><input type="checkbox" data-email="${escapeHtml(email.email)}" ${selectedEmailsSet.has(email.email) ? 'checked' : ''}></td>
                <td class="serial-number">${serialNumber}</td>
                <td class="email">${escapeHtml(email.email)}</td>
                <td>
                    <span class="confidence-badge ${getConfidenceClass(email.confidence)}">
                        ${email.confidence.toFixed(0)}%
                    </span>
                </td>
                <td>
                    <span class="status-badge ${email.is_valid ? 'valid' : 'invalid'}">
                        <i class="fas ${email.is_valid ? 'fa-check' : 'fa-times'}"></i>
                        ${email.is_valid ? 'Valid' : 'Invalid'}
                    </span>
                </td>
                <td>${escapeHtml(email.domain)}</td>
                <td>
                    <button class="copy-btn" onclick="copyEmail('${escapeHtml(email.email)}')" title="Copy email">
                        <i class="fas fa-copy"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Update pagination
    const totalPagesDisplay = totalPages || 1;
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPagesDisplay}`;
    document.getElementById('firstPage').disabled = currentPage <= 1;
    document.getElementById('prevPage').disabled = currentPage <= 1;
    document.getElementById('nextPage').disabled = currentPage >= totalPages;
    document.getElementById('lastPage').disabled = currentPage >= totalPages;
    
    // Store total pages for goToPage function
    window.currentTotalPages = totalPages;

    // Update select all checkbox state
    updateSelectAllCheckbox();
    updateSelectionCount();
}

// Update select all checkbox based on current selections
function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('selectAll');
    if (!currentResults || !currentResults.emails || currentResults.emails.length === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
        return;
    }
    
    const totalEmails = currentResults.emails.length;
    const selectedCount = selectedEmailsSet.size;
    
    if (selectedCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
    } else if (selectedCount === totalEmails) {
        selectAllCheckbox.checked = true;
        selectAllCheckbox.indeterminate = false;
    } else {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = true;
    }
}

// Update selection count display
function updateSelectionCount() {
    const countDisplay = document.getElementById('selectionCount');
    if (countDisplay) {
        if (selectedEmailsSet.size > 0) {
            countDisplay.textContent = `${selectedEmailsSet.size} selected`;
            countDisplay.style.display = 'inline-block';
        } else {
            countDisplay.style.display = 'none';
        }
    }
}

function getConfidenceClass(confidence) {
    if (confidence >= 75) return 'high';
    if (confidence >= 50) return 'medium';
    return 'low';
}

function changePage(delta) {
    currentPage += delta;
    filterResults();
}

function goToPage(page) {
    if (page === 'last') {
        currentPage = window.currentTotalPages || 1;
    } else {
        currentPage = page;
    }
    filterResults();
}

// ==================== Export ====================

// Get selected emails from the persistent Set
function getSelectedEmails() {
    return Array.from(selectedEmailsSet);
}

async function exportResults(format) {
    if (!currentResults || !currentResults.emails || currentResults.emails.length === 0) {
        showError('No results to export.');
        return;
    }

    const selectedEmails = getSelectedEmails();
    const hasSelection = selectedEmails.length > 0 && selectedEmails.length < currentResults.emails.length;
    
    // Determine which emails to export
    let emailsToExport;
    let filename;
    let toastMessage;
    
    if (hasSelection) {
        // Export only selected emails
        emailsToExport = currentResults.emails.filter(e => selectedEmails.includes(e.email));
        filename = `selected_emails_${selectedEmails.length}`;
        toastMessage = `Exported ${selectedEmails.length} selected emails`;
    } else {
        // Export all emails
        emailsToExport = currentResults.emails;
        filename = `all_emails_${currentResults.emails.length}`;
        toastMessage = `Exported ${currentResults.emails.length} emails`;
    }
    
    try {
        let content = '';
        let mimeType = '';
        
        if (format === 'csv') {
            content = 'Email,Confidence,Valid,Domain\n';
            content += emailsToExport.map(e => 
                `"${e.email}",${e.confidence.toFixed(1)},${e.is_valid ? 'Yes' : 'No'},"${e.domain}"`
            ).join('\n');
            mimeType = 'text/csv';
        } else if (format === 'txt') {
            content = emailsToExport.map(e => e.email).join('\n');
            mimeType = 'text/plain';
        } else if (format === 'xlsx') {
            // For xlsx, we need to use the backend if no selection, or create simple CSV fallback
            if (!hasSelection && currentJobId) {
                // Use backend for full export
                const response = await fetch(`${API_BASE_URL}/export/${currentJobId}?format=${format}`);
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Export failed');
                }
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${filename}.${format}`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                showCopyToast(toastMessage + ' to XLSX');
                return;
            } else {
                // Fall back to CSV for selected emails
                content = 'Email,Confidence,Valid,Domain\n';
                content += emailsToExport.map(e => 
                    `"${e.email}",${e.confidence.toFixed(1)},${e.is_valid ? 'Yes' : 'No'},"${e.domain}"`
                ).join('\n');
                mimeType = 'text/csv';
                format = 'csv';
                showCopyToast(toastMessage + ' to CSV (XLSX requires full export)');
            }
        }
        
        // Download file
        const blob = new Blob([content], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        if (format !== 'xlsx') {
            showCopyToast(toastMessage + ` to ${format.toUpperCase()}`);
        }

    } catch (error) {
        console.error('Export error:', error);
        showError(error.message || 'Failed to export results.');
    }
}

// ==================== Utility Functions ====================

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function showError(message) {
    errorMessage.textContent = message;
    errorModal.style.display = 'flex';
}

function hideError() {
    errorModal.style.display = 'none';
}

function resetToUpload() {
    progressSection.style.display = 'none';
    selectedFilesSection.style.display = selectedFiles.length > 0 ? 'block' : 'none';
}

function resetApp() {
    // Reset state
    selectedFiles = [];
    currentJobId = null;
    currentResults = null;
    currentPage = 1;
    itemsPerPage = 20;
    dupCurrentPage = 1;
    dupItemsPerPage = 10;
    currentDuplicates = [];
    filteredDuplicates = [];
    dupSearchTerm = '';
    sortColumn = null;
    sortDirection = 'asc';
    selectedEmailsSet.clear();

    // Destroy charts
    if (emailDistributionChart) {
        emailDistributionChart.destroy();
        emailDistributionChart = null;
    }
    if (validityChart) {
        validityChart.destroy();
        validityChart = null;
    }
    if (confidenceChart) {
        confidenceChart.destroy();
        confidenceChart = null;
    }

    // Reset UI
    fileInput.value = '';
    searchInput.value = '';
    filterSelect.value = 'all';
    document.getElementById('pageSizeSelect').value = '20';
    document.getElementById('dupPageSizeSelect').value = '10';
    document.getElementById('dupSearchInput').value = '';
    resultsSection.style.display = 'none';
    progressSection.style.display = 'none';
    selectedFilesSection.style.display = 'none';
    document.getElementById('duplicatesSection').style.display = 'none';
    
    // Reset sort icons
    updateSortIcons();
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Copy email to clipboard
function copyEmail(email) {
    navigator.clipboard.writeText(email).then(() => {
        showCopyToast(`Copied: ${email}`);
    }).catch(err => {
        console.error('Failed to copy:', err);
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = email;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showCopyToast(`Copied: ${email}`);
    });
}

// Copy all emails to clipboard (or selected if any are checked)
function copyAllEmails() {
    if (!currentResults || !currentResults.emails || currentResults.emails.length === 0) {
        showCopyToast('No emails to copy');
        return;
    }
    
    const selectedEmails = getSelectedEmails();
    const hasSelection = selectedEmails.length > 0 && selectedEmails.length < currentResults.emails.length;
    
    let emailsToCopy;
    let toastMessage;
    
    if (hasSelection) {
        emailsToCopy = selectedEmails.join('\n');
        toastMessage = `Copied ${selectedEmails.length} selected emails to clipboard`;
    } else {
        emailsToCopy = currentResults.emails.map(e => e.email).join('\n');
        toastMessage = `Copied ${currentResults.emails.length} emails to clipboard`;
    }
    
    const header = document.getElementById('copyAllHeader');
    
    navigator.clipboard.writeText(emailsToCopy).then(() => {
        // Show feedback
        header.innerHTML = '<i class="fas fa-check"></i> Copied!';
        header.classList.add('copied');
        showCopyToast(toastMessage);
        
        // Reset after 2 seconds
        setTimeout(() => {
            header.innerHTML = '<i class="fas fa-copy"></i> Copy';
            header.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        // Fallback
        const textArea = document.createElement('textarea');
        textArea.value = emailsToCopy;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        header.innerHTML = '<i class="fas fa-check"></i> Copied!';
        header.classList.add('copied');
        showCopyToast(toastMessage);
        
        setTimeout(() => {
            header.innerHTML = '<i class="fas fa-copy"></i> Copy';
            header.classList.remove('copied');
        }, 2000);
    });
}

// Show copy toast notification
function showCopyToast(message) {
    // Remove existing toast if any
    const existingToast = document.querySelector('.copy-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create and show new toast
    const toast = document.createElement('div');
    toast.className = 'copy-toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Hide and remove after 2 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// Make functions accessible globally
window.removeFile = removeFile;
window.copyEmail = copyEmail;

// ==================== Initialize ====================

console.log('PDF Email Extractor initialized');
