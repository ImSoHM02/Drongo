// Global functions for HTML onclick handlers (defined early)

// Modal management functions
function closeModal(modalId) {
    if (window.levelingDashboard) {
        window.levelingDashboard.closeModal(modalId);
    }
}

function saveRank() {
    if (window.levelingDashboard) {
        window.levelingDashboard.saveRank();
    }
}

function saveTemplate() {
    if (window.levelingDashboard) {
        window.levelingDashboard.saveTemplate();
    }
}

function editRank(rankId) {
    if (window.levelingDashboard) {
        window.levelingDashboard.showRankModal(rankId);
    }
}

function deleteRank(rankId) {
    if (window.levelingDashboard) {
        window.levelingDashboard.deleteRank(rankId);
    }
}

function editTemplate(templateId) {
    if (window.levelingDashboard) {
        window.levelingDashboard.showTemplateModal(templateId);
    }
}

function deleteTemplate(templateId) {
    if (window.levelingDashboard) {
        window.levelingDashboard.deleteTemplate(templateId);
    }
}

function previewTemplateById(templateId) {
    if (window.levelingDashboard) {
        window.levelingDashboard.previewTemplateById(templateId);
    }
}

function previewTemplate() {
    if (window.levelingDashboard) {
        window.levelingDashboard.previewTemplate();
    }
}

function showVariableReference() {
    if (window.levelingDashboard) {
        window.levelingDashboard.showVariableReference();
    }
}

function confirmAction() {
    // This will be implemented when needed for confirmation dialogs
    console.log('Confirm action called');
}

function showMainSection() {
    const main = document.getElementById('dashboard-view');
    const config = document.getElementById('config-view');
    const stats = document.getElementById('stats-view');
    const leveling = document.getElementById('leveling-view');
    if (!main || !config) {
        console.warn('showMainSection(): required elements missing');
    }
    if (main) main.style.display = 'block';
    if (config) config.style.display = 'none';
    if (stats) stats.style.display = 'none';
    if (leveling) leveling.style.display = 'none';
    console.debug('showMainSection(): activated');
}

function showConfigSection() {
    const main = document.getElementById('dashboard-view');
    const config = document.getElementById('config-view');
    const stats = document.getElementById('stats-view');
    const leveling = document.getElementById('leveling-view');
    if (!main || !config) {
        console.warn('showConfigSection(): required elements missing');
    }
    if (main) main.style.display = 'none';
    if (config) config.style.display = 'block';
    if (stats) stats.style.display = 'none';
    if (leveling) leveling.style.display = 'none';
    
    // Load commands when config section is shown
    if (window.commandsManager) {
        window.commandsManager.loadCommands();
    }
    console.debug('showConfigSection(): activated');
}

function showStatsSection() {
    const main = document.getElementById('dashboard-view');
    const config = document.getElementById('config-view');
    const stats = document.getElementById('stats-view');
    const leveling = document.getElementById('leveling-view');
    if (!stats) {
        console.warn('showStatsSection(): stats-view not found');
    }
    if (main) main.style.display = 'none';
    if (config) config.style.display = 'none';
    if (stats) stats.style.display = 'block';
    if (leveling) leveling.style.display = 'none';
    
    // Resize charts after becoming visible so Chart.js recalculates layout
    if (window.statsManager) {
        window.statsManager.resizeCharts();
    }
    console.debug('showStatsSection(): activated');
}

function showLevelingSection() {
    const main = document.getElementById('dashboard-view');
    const config = document.getElementById('config-view');
    const stats = document.getElementById('stats-view');
    const leveling = document.getElementById('leveling-view');
    if (!leveling) {
        console.warn('showLevelingSection(): leveling-view not found');
    }
    if (main) main.style.display = 'none';
    if (config) config.style.display = 'none';
    if (stats) stats.style.display = 'none';
    if (leveling) leveling.style.display = 'block';
    
    // Initialize leveling dashboard if not already done
    if (leveling && leveling.style.display === 'block' && window.LevelingDashboard && !window.levelingDashboard) {
        window.levelingDashboard = new LevelingDashboard();
    }
    
    console.debug('showLevelingSection(): activated');
}

class DashboardManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        
        this.messageHistory = [];
        this.eventHistory = [];
        
        this.init();
    }
    
    init() {
        this.setupWebSocket();
        this.setupEventListeners();
        this.startHeartbeat();
    }
    
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                this.onConnectionOpen();
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    // Silently handle WebSocket message parsing errors
                }
            };
            
            this.socket.onclose = () => {
                this.onConnectionClose();
            };
            
            this.socket.onerror = (error) => {
                this.onConnectionError();
            };
            
        } catch (error) {
            this.onConnectionError();
        }
    }
    
    onConnectionOpen() {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.updateConnectionStatus(true);
        this.updateBotStatus('connected');
    }
    
    onConnectionClose() {
        this.isConnected = false;
        this.updateConnectionStatus(false);
        this.updateBotStatus('disconnected');
        this.attemptReconnect();
    }
    
    onConnectionError() {
        this.isConnected = false;
        this.updateConnectionStatus(false);
        this.updateBotStatus('error');
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                this.setupWebSocket();
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            // Max reconnection attempts reached
        }
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'stats_update':
                if (window.statsManager) {
                    window.statsManager.updateStats(data.data);
                    window.statsManager.updateDatabaseHealth(data.data.database_health || {});
                }
                this.updateRecentActivity(data.data);
                break;
            case 'message_activity':
                if (window.statsManager) {
                    window.statsManager.updateMessageActivity(data.data);
                }
                break;
            case 'database_health':
                if (window.statsManager) {
                    window.statsManager.updateDatabaseHealth(data.data);
                }
                break;
            case 'bot_status':
                this.updateBotStatus(data.status);
                break;
            case 'recent_activity':
                this.updateRecentActivity(data.data);
                break;
            case 'pong':
                // Handle pong response
                break;
            case 'error':
                // Server error
                break;
            default:
                // Unknown message type
        }
    }
    
    updateRecentActivity(activity) {
        if (activity.recent_messages) {
            this.updateActivityList('recent-messages', activity.recent_messages, 'message');
        }
        
        if (activity.recent_events) {
            this.updateActivityList('recent-events', activity.recent_events, 'event');
        }
    }
    
    updateActivityList(containerId, items, type) {
        const container = document.getElementById(containerId);
        if (!container) {
            return;
        }
        
        container.innerHTML = '';
        
        items.slice(0, 10).forEach((item, index) => {
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';
            
            const avatar = document.createElement('div');
            avatar.className = 'activity-avatar';
            avatar.textContent = type === 'message' ?
                (item.author ? item.author[0].toUpperCase() : 'U') :
                'E';
            
            const content = document.createElement('div');
            content.className = 'activity-content';
            
            const text = document.createElement('div');
            text.className = 'activity-text';
            text.textContent = type === 'message' ?
                `${item.author || 'User'} in #${item.channel || 'unknown'}` :
                item.event || 'Event occurred';
            
            const meta = document.createElement('div');
            meta.className = 'activity-meta';
            meta.textContent = type === 'message' ?
                `${item.guild || 'Server'}` :
                item.type || 'system';
            
            const time = document.createElement('div');
            time.className = 'activity-time';
            time.textContent = item.timestamp || 'Now';
            
            content.appendChild(text);
            content.appendChild(meta);
            
            activityItem.appendChild(avatar);
            activityItem.appendChild(content);
            activityItem.appendChild(time);
            
            container.appendChild(activityItem);
        });
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }
    
    updateBotStatus(status) {
        // Bot status element was removed from the template
        // This method is kept for compatibility but does nothing
    }
    
    setupEventListeners() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page hidden
            } else {
                // Page visible
                if (!this.isConnected) {
                    this.setupWebSocket();
                }
            }
        });
    }
    
    startHeartbeat() {
        // Send ping every 30 seconds to keep connection alive
        setInterval(() => {
            if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }
    
    requestUpdate() {
        if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type: 'request_update' }));
        }
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardManager();

    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            const href = link.getAttribute('href');
            if (href === '#commands') {
                showConfigSection();
            } else if (href === '#stats') {
                showStatsSection();
            } else if (href === '#leveling') {
                showLevelingSection();
            } else {
                showMainSection();
            }
        });
    });
});

window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.disconnect();
    }
});

// Export for global access
window.DashboardManager = DashboardManager;
