// Visaire Frontend Application
class VisaireApp {
    constructor() {
        this.apiBaseUrl = '';
        this.animationHistory = JSON.parse(localStorage.getItem('animationHistory') || '[]');
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkApiStatus();
        this.renderHistory();
    }

    setupEventListeners() {
        // Form submission
        const form = document.getElementById('animation-form');
        form.addEventListener('submit', (e) => this.handleFormSubmit(e));

        // Example prompts
        const examplePrompts = document.querySelectorAll('.example-prompt');
        examplePrompts.forEach(prompt => {
            prompt.addEventListener('click', (e) => this.handleExampleClick(e));
        });

        // Clear error when typing
        const promptTextarea = document.getElementById('prompt');
        promptTextarea.addEventListener('input', () => this.hideError());
    }

    async checkApiStatus() {
        const statusElement = document.getElementById('api-status');
        const statusBadge = document.getElementById('status-badge');
        const pulseDot = statusBadge.querySelector('.pulse-dot');
        
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            if (data.status === 'healthy') {
                statusElement.textContent = 'Online & Ready';
                pulseDot.style.color = '#10b981'; // Green
            } else {
                statusElement.textContent = 'Issues Detected';
                pulseDot.style.color = '#f59e0b'; // Amber
            }
        } catch (error) {
            statusElement.textContent = 'Offline';
            pulseDot.style.color = '#ef4444'; // Red
        }
    }

    handleExampleClick(e) {
        const prompt = e.target.getAttribute('data-prompt');
        document.getElementById('prompt').value = prompt;
        this.hideError();
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        const prompt = document.getElementById('prompt').value.trim();
        if (!prompt) {
            this.showError('Please enter a prompt for your animation');
            return;
        }

        this.showLoading();
        this.hideError();

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_prompt: prompt })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to generate animation');
            }

            this.showVideo(data.video_url, prompt);
            this.addToHistory(prompt, data.video_url);
            
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }

    showLoading() {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('generate-btn').disabled = true;
        document.getElementById('generate-btn').innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            Generating...
        `;
    }

    hideLoading() {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('generate-btn').disabled = false;
        document.getElementById('generate-btn').innerHTML = `
            <i class="fas fa-wand-magic-sparkles me-2"></i>
            Generate Animation
        `;
    }

    showError(message) {
        const errorAlert = document.getElementById('error-alert');
        const errorMessage = document.getElementById('error-message');
        
        errorMessage.textContent = message;
        errorAlert.style.display = 'block';
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    hideError() {
        document.getElementById('error-alert').style.display = 'none';
    }

    showVideo(videoUrl, prompt) {
        const videoContainer = document.getElementById('video-container');
        
        videoContainer.innerHTML = `
            <div class="fade-in">
                <video controls autoplay class="w-100 mb-3">
                    <source src="${videoUrl}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">Prompt: "${prompt}"</small>
                    <div>
                        <a href="${videoUrl}" download class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-download me-1"></i>
                            Download
                        </a>
                    </div>
                </div>
            </div>
        `;

        videoContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    addToHistory(prompt, videoUrl) {
        const historyItem = {
            id: Date.now(),
            prompt: prompt.substring(0, 100) + (prompt.length > 100 ? '...' : ''),
            videoUrl,
            timestamp: new Date().toISOString(),
            date: new Date().toLocaleDateString()
        };

        this.animationHistory.unshift(historyItem);
        
        // Keep only last 10 items
        if (this.animationHistory.length > 10) {
            this.animationHistory = this.animationHistory.slice(0, 10);
        }

        localStorage.setItem('animationHistory', JSON.stringify(this.animationHistory));
        this.renderHistory();
    }

    renderHistory() {
        const historyContainer = document.getElementById('history-container');
        
        if (this.animationHistory.length === 0) {
            historyContainer.innerHTML = '<p class="text-muted text-center">No animations created yet</p>';
            return;
        }

        const historyHtml = this.animationHistory.map(item => `
            <div class="history-item" onclick="app.loadHistoryItem('${item.videoUrl}', '${item.prompt}')">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <small class="text-primary fw-bold">${item.date}</small>
                        <p class="mb-1 small">${item.prompt}</p>
                    </div>
                    <button class="btn btn-sm btn-outline-danger ms-2" onclick="event.stopPropagation(); app.deleteHistoryItem(${item.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

        historyContainer.innerHTML = historyHtml;
    }

    loadHistoryItem(videoUrl, prompt) {
        this.showVideo(videoUrl, prompt);
        document.getElementById('prompt').value = prompt;
    }

    deleteHistoryItem(id) {
        this.animationHistory = this.animationHistory.filter(item => item.id !== id);
        localStorage.setItem('animationHistory', JSON.stringify(this.animationHistory));
        this.renderHistory();
    }

    clearHistory() {
        if (confirm('Are you sure you want to clear all animation history?')) {
            this.animationHistory = [];
            localStorage.removeItem('animationHistory');
            this.renderHistory();
        }
    }
}

// Initialize the app when the page loads
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new VisaireApp();
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to generate
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('animation-form').dispatchEvent(new Event('submit'));
    }
});
