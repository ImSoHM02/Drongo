// Global functions for HTML onclick handlers (defined early)
function showDashboardSection() {
    const dash = document.getElementById('dashboard-view');
    const config = document.getElementById('config-view');
    const stats = document.getElementById('stats-view');
    if (!dash || !config) {
        console.warn('showDashboardSection(): required elements missing');
    }
    if (dash) dash.style.display = 'block';
    if (config) config.style.display = 'none';
    if (stats) stats.style.display = 'none';
    console.debug('showDashboardSection(): activated');
}

function showConfigSection() {
    const dash = document.getElementById('dashboard-view');
    const config = document.getElementById('config-view');
    const stats = document.getElementById('stats-view');
    if (!dash || !config) {
        console.warn('showConfigSection(): required elements missing');
    }
    if (dash) dash.style.display = 'none';
    if (config) config.style.display = 'block';
    if (stats) stats.style.display = 'none';
    
    // Load commands when config section is shown
    if (window.dashboard) {
        window.dashboard.loadCommands();
    }
    console.debug('showConfigSection(): activated');
}

function showStatsSection() {
    const dash = document.getElementById('dashboard-view');
    const config = document.getElementById('config-view');
    const stats = document.getElementById('stats-view');
    if (!stats) {
        console.warn('showStatsSection(): stats-view not found');
    }
    if (dash) dash.style.display = 'none';
    if (config) config.style.display = 'none';
    if (stats) stats.style.display = 'block';
    
    // Resize charts after becoming visible so Chart.js recalculates layout
    setTimeout(() => {
        if (window.dashboard && window.dashboard.charts && window.dashboard.charts.activity) {
            try {
                window.dashboard.charts.activity.resize();
            } catch (e) {
                // Ignore resize errors
            }
        }
    }, 50);
    console.debug('showStatsSection(): activated');
}

class DashboardManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        
        this.charts = {};
        this.stats = {
            messages_processed: 0,
            commands_executed: 0,
            active_users: 0,
            uptime_seconds: 0
        };
        
        this.messageHistory = [];
        this.eventHistory = [];
        
        this.init();
    }
    
    init() {
        this.setupWebSocket();
        this.setupCharts();
        this.setupEventListeners();
        this.startPeriodicUpdates();
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
                this.updateStats(data.data);
                this.updateDatabaseHealth(data.data.database_health || {});
                this.updateRecentActivity(data.data);
                break;
            case 'message_activity':
                this.updateMessageActivity(data.data);
                break;
            case 'database_health':
                this.updateDatabaseHealth(data.data);
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
    
    updateStats(stats) {
        Object.assign(this.stats, stats);
        
        this.updateElement('messages-processed', this.formatNumber(stats.messages_processed || 0));
        this.updateElement('commands-executed', this.formatNumber(stats.commands_executed || 0));
        this.updateElement('active-users', this.formatNumber(stats.active_users || 0));
        this.updateElement('uptime', stats.uptime || '00:00:00');
        
        if (stats.message_rate !== undefined) {
            this.updateElement('message-rate', `${stats.message_rate}/min`);
        }
        if (stats.command_rate !== undefined) {
            this.updateElement('command-rate', `${stats.command_rate}/min`);
        }
    }
    
    updateMessageActivity(data) {
        if (this.charts.activity && data.timestamps && data.message_counts) {
            const chart = this.charts.activity;
            
            chart.data.labels = data.timestamps.map(ts => new Date(ts).toLocaleTimeString());
            chart.data.datasets[0].data = data.message_counts;
            
            if (chart.data.labels.length > 20) {
                chart.data.labels = chart.data.labels.slice(-20);
                chart.data.datasets[0].data = chart.data.datasets[0].data.slice(-20);
            }
            
            chart.update('none');
        }
    }
    
    updateDatabaseHealth(health) {
        if (health.database_size_mb !== undefined) {
            this.updateElement('db-size', `${health.database_size_mb.toFixed(1)} MB`);
            const percentage = Math.min((health.database_size_mb / 100) * 100, 100);
            const progressBar = document.getElementById('db-size-bar');
            if (progressBar) {
                progressBar.style.width = `${percentage}%`;
            }
        }
        
        if (health.table_count !== undefined) {
            this.updateElement('db-tables', health.table_count);
        }
        
        if (health.index_count !== undefined) {
            this.updateElement('db-indexes', health.index_count);
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
    
    setupCharts() {
        this.setupActivityChart();
    }
    
    setupActivityChart() {
        const ctx = document.getElementById('activity-chart');
        if (!ctx) return;
        
        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Messages per Minute',
                    data: [],
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: '#334155'
                        },
                        ticks: {
                            color: '#cbd5e1',
                            maxTicksLimit: 6
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        grid: {
                            color: '#334155'
                        },
                        ticks: {
                            color: '#cbd5e1'
                        }
                    }
                },
                elements: {
                    point: {
                        backgroundColor: '#6366f1'
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
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
        
        // Set up command management event listeners
        this.setupCommandEventListeners();
    }
    
    setupCommandEventListeners() {
        // Register commands button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'register-commands-btn') {
                this.registerCommands();
            } else if (e.target.id === 'delete-commands-btn') {
                this.deleteCommands();
            } else if (e.target.id === 'restart-bot-btn') {
                this.restartBot();
            } else if (e.target.id === 'shutdown-bot-btn') {
                this.shutdownBot();
            }
        });
    }
    
    async registerCommands() {
        const button = document.getElementById('register-commands-btn');
        const statusDiv = document.getElementById('command-status');
        
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
        
        try {
            const response = await fetch('/api/commands/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showCommandStatus('Commands registered successfully!', 'success');
                this.loadCommands(); // Refresh the commands list
            } else {
                this.showCommandStatus(`Error: ${result.error || 'Failed to register commands'}`, 'error');
            }
        } catch (error) {
            this.showCommandStatus('Network error occurred while registering commands', 'error');
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-plus"></i> Register Commands';
        }
    }
    
    async deleteCommands() {
        if (!confirm('Are you sure you want to delete ALL Discord commands? This action cannot be undone.')) {
            return;
        }
        
        const button = document.getElementById('delete-commands-btn');
        const statusDiv = document.getElementById('command-status');
        
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
        
        try {
            const response = await fetch('/api/commands/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showCommandStatus('Commands deleted successfully!', 'success');
                this.loadCommands(); // Refresh the commands list
            } else {
                this.showCommandStatus(`Error: ${result.error || 'Failed to delete commands'}`, 'error');
            }
        } catch (error) {
            this.showCommandStatus('Network error occurred while deleting commands', 'error');
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-trash"></i> Delete All Commands';
        }
    }
    
    showCommandStatus(message, type) {
        const statusDiv = document.getElementById('command-status');
        statusDiv.style.display = 'block';
        statusDiv.textContent = message;
        
        // Set background color based on type
        if (type === 'success') {
            statusDiv.style.background = 'rgba(16, 185, 129, 0.1)';
            statusDiv.style.color = 'var(--success)';
            statusDiv.style.border = '1px solid rgba(16, 185, 129, 0.2)';
        } else if (type === 'error') {
            statusDiv.style.background = 'rgba(239, 68, 68, 0.1)';
            statusDiv.style.color = 'var(--danger)';
            statusDiv.style.border = '1px solid rgba(239, 68, 68, 0.2)';
        }
        
        // Hide after 5 seconds
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
    
    async loadCommands() {
        try {
            const response = await fetch('/api/commands/list');
            const commands = await response.json();
            
            const commandsList = document.getElementById('commands-list');
            if (commandsList) {
                if (commands.length === 0) {
                    commandsList.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">No commands registered</div>';
                } else {
                    commandsList.innerHTML = commands.map(cmd =>
                        `<div style="margin-bottom: 0.5rem; padding: 0.5rem; background: var(--bg-primary); border-radius: 0.25rem;">
                            <strong>/${cmd.name}</strong><br>
                            <span style="color: var(--text-muted); font-size: 0.8rem;">${cmd.description}</span>
                        </div>`
                    ).join('');
                }
            }
        } catch (error) {
            const commandsList = document.getElementById('commands-list');
            if (commandsList) {
                commandsList.innerHTML = '<div style="color: var(--danger);">Error loading commands</div>';
            }
        }
    }
    
    async restartBot() {
        if (!confirm('Are you sure you want to restart the bot? This will temporarily disconnect all services.')) {
            return;
        }
        
        const button = document.getElementById('restart-bot-btn');
        button.disabled = true;
        button.innerHTML = 'Restarting...';
        
        try {
            const response = await fetch('/api/bot/restart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Just indicate completion without visual changes
                // Connection will be lost when bot restarts
                setTimeout(() => {
                    this.updateConnectionStatus(false);
                }, 2000);
            } else {
                // Reset button on failure
                setTimeout(() => {
                    button.disabled = false;
                }, 3000);
            }
        } catch (error) {
            // Reset button on error
            setTimeout(() => {
                button.disabled = false;
            }, 3000);
        }
    }
    
    async shutdownBot() {
        if (!confirm('Are you sure you want to shutdown the bot? This will stop all bot services until manually restarted.')) {
            return;
        }
        
        const button = document.getElementById('shutdown-bot-btn');
        button.disabled = true;
        button.innerHTML = 'Shutting Down...';
        
        try {
            const response = await fetch('/api/bot/shutdown', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Just indicate completion without visual changes
                // Connection will be lost when bot shuts down
                setTimeout(() => {
                    this.updateConnectionStatus(false);
                    this.updateBotStatus('offline');
                }, 2000);
            } else {
                // Reset button on failure
                setTimeout(() => {
                    button.disabled = false;
                }, 3000);
            }
        } catch (error) {
            // Reset button on error
            setTimeout(() => {
                button.disabled = false;
            }, 3000);
        }
    }
    
    startPeriodicUpdates() {
        setInterval(() => {
            if (this.stats.uptime_seconds !== undefined) {
                this.stats.uptime_seconds++;
                this.updateElement('uptime', this.formatUptime(this.stats.uptime_seconds));
            }
        }, 1000);
        
        setInterval(() => {
            document.querySelectorAll('.activity-time').forEach(el => {
                const timestamp = el.dataset.timestamp;
                if (timestamp) {
                    el.textContent = this.formatRelativeTime(new Date(timestamp));
                }
            });
        }, 30000);
    }
    
    startHeartbeat() {
        // Send ping every 30 seconds to keep connection alive
        setInterval(() => {
            if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
                this.socket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    formatUptime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatRelativeTime(date) {
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) {
            return `${days}d ago`;
        } else if (hours > 0) {
            return `${hours}h ago`;
        } else if (minutes > 0) {
            return `${minutes}m ago`;
        } else {
            return 'Just now';
        }
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
            } else {
                showDashboardSection();
            }
        });
    });
});

window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.disconnect();
    }
});
