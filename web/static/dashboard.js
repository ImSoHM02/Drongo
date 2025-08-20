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
    if (window.dashboard) {
        window.dashboard.loadCommands();
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
        if (!confirm('Are you sure you want to register the commands?')) {
            return;
        }

        const button = document.getElementById('register-commands-btn');
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';

        try {
            const response = await fetch('/api/commands/register', {
                method: 'POST'
            });
            const result = await response.json();
            if (response.ok) {
                this.showCommandStatus('Commands registered successfully!', 'success');
                this.loadCommands();
            } else {
                this.showCommandStatus(`Error: ${result.error || 'Failed to register'}`, 'error');
            }
        } catch (error) {
            this.showCommandStatus('Network error occurred', 'error');
        } finally {
            setTimeout(() => {
                button.disabled = false;
                button.innerHTML = originalText;
            }, 2000);
        }
    }
    
    async deleteCommands() {
        if (!confirm('Are you sure you want to delete ALL commands?')) {
            return;
        }

        const button = document.getElementById('delete-commands-btn');
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';

        try {
            const response = await fetch('/api/commands/delete', {
                method: 'POST'
            });
            const result = await response.json();
            if (response.ok) {
                this.showCommandStatus('Commands deleted successfully!', 'success');
                this.loadCommands();
            } else {
                this.showCommandStatus(`Error: ${result.error || 'Failed to delete'}`, 'error');
            }
        } catch (error) {
            this.showCommandStatus('Network error occurred', 'error');
        } finally {
            setTimeout(() => {
                button.disabled = false;
                button.innerHTML = originalText;
            }, 2000);
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
        if (!confirm('Are you sure you want to restart the bot?')) {
            return;
        }

        const button = document.getElementById('restart-bot-btn');
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Restarting...';

        try {
            await fetch('/api/bot/restart', {
                method: 'POST'
            });
            this.showCommandStatus('Bot is restarting...', 'success');
        } catch (error) {
            this.showCommandStatus('Failed to send restart command', 'error');
        } finally {
            setTimeout(() => {
                button.disabled = false;
                button.innerHTML = originalText;
            }, 5000);
        }
    }
    
    async shutdownBot() {
        if (!confirm('Are you sure you want to shut down the bot?')) {
            return;
        }

        const button = document.getElementById('shutdown-bot-btn');
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Shutting down...';

        try {
            await fetch('/api/bot/shutdown', {
                method: 'POST'
            });
            this.showCommandStatus('Bot is shutting down...', 'success');
        } catch (error) {
            this.showCommandStatus('Failed to send shutdown command', 'error');
        } finally {
            setTimeout(() => {
                button.disabled = false;
                button.innerHTML = originalText;
            }, 5000);
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

// =========================================================================
// LEVELING DASHBOARD FUNCTIONALITY
// =========================================================================

class LevelingDashboard {
    constructor() {
        this.currentGuild = null;
        this.feedPaused = false;
        this.feedUpdateInterval = null;
        this.leaderboardUpdateInterval = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadGuilds();
        this.startPeriodicUpdates();
    }
    
    setupEventListeners() {
        // Guild selection
        const guildSelect = document.getElementById('guild-select');
        if (guildSelect) {
            guildSelect.addEventListener('change', (e) => {
                this.currentGuild = e.target.value;
                if (this.currentGuild) {
                    this.loadGuildData();
                }
            });
        }
        
        // Feed toggle
        const toggleFeed = document.getElementById('toggle-feed');
        if (toggleFeed) {
            toggleFeed.addEventListener('click', () => {
                this.toggleFeed();
            });
        }
        
        // Leaderboard limit
        const leaderboardLimit = document.getElementById('leaderboard-limit');
        if (leaderboardLimit) {
            leaderboardLimit.addEventListener('change', () => {
                this.loadLeaderboard();
            });
        }
        
        // Configuration save
        const saveConfig = document.getElementById('save-config');
        if (saveConfig) {
            saveConfig.addEventListener('click', () => {
                this.saveConfiguration();
            });
        }
        
        // Manual adjustment
        const applyAdjustment = document.getElementById('apply-adjustment');
        if (applyAdjustment) {
            applyAdjustment.addEventListener('click', () => {
                this.applyManualAdjustment();
            });
        }
        
        // User lookup
        const lookupBtn = document.getElementById('lookup-btn');
        if (lookupBtn) {
            lookupBtn.addEventListener('click', () => {
                this.lookupUser();
            });
        }
        
        // Enter key for user lookup
        const lookupInput = document.getElementById('lookup-user');
        if (lookupInput) {
            lookupInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.lookupUser();
                }
            });
        }

        // Rank management event listeners
        const addRankBtn = document.getElementById('add-rank-btn');
        if (addRankBtn) {
            addRankBtn.addEventListener('click', () => {
                this.showRankModal();
            });
        }

        // Template management event listeners
        const addTemplateBtn = document.getElementById('add-template-btn');
        if (addTemplateBtn) {
            addTemplateBtn.addEventListener('click', () => {
                this.showTemplateModal();
            });
        }

        // Template type tabs
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('tab-btn')) {
                this.switchTemplateTab(e.target.dataset.type);
            }
        });
    }
    
    async loadGuilds() {
        try {
            const response = await fetch('/api/leveling/guilds');
            const guilds = await response.json();
            
            const guildSelect = document.getElementById('guild-select');
            if (guildSelect && response.ok) {
                // Clear existing options except the first placeholder
                while (guildSelect.children.length > 1) {
                    guildSelect.removeChild(guildSelect.lastChild);
                }
                
                guilds.forEach(guild => {
                    const option = document.createElement('option');
                    option.value = guild.id;
                    option.textContent = `${guild.name} (${guild.user_count} users)`;
                    guildSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading guilds:', error);
            this.showStatus('Error loading guilds', 'error');
        }
    }
    
    async loadGuildData() {
        if (!this.currentGuild) return;
        
        // Show loading state
        this.showLoadingState(true);
        
        try {
            await Promise.all([
                this.loadStats(),
                this.loadConfiguration(),
                this.loadLeaderboard(),
                this.loadLiveFeed(),
                this.loadRanks(),
                this.loadTemplates()
            ]);
            this.showStatus('Guild data loaded successfully', 'success');
        } catch (error) {
            console.error('Error loading guild data:', error);
            this.showStatus('Error loading guild data', 'error');
        } finally {
            this.showLoadingState(false);
        }
    }
    
    async loadStats() {
        try {
            const url = this.currentGuild ?
                `/api/leveling/stats?guild_id=${this.currentGuild}` :
                '/api/leveling/stats';
            
            const response = await fetch(url);
            const stats = await response.json();
            
            if (response.ok) {
                this.updateElement('total-users', this.formatNumber(stats.total_users));
                this.updateElement('avg-level', stats.avg_level);
                this.updateElement('xp-today', this.formatNumber(stats.xp_today));
                this.updateElement('active-users-today', this.formatNumber(stats.active_users_today));
            }
        } catch (error) {
            console.error('Error loading stats:', error);
            this.showStatus('Error loading stats', 'error');
        }
    }
    
    async loadConfiguration() {
        if (!this.currentGuild) return;
        
        try {
            const response = await fetch(`/api/leveling/config?guild_id=${this.currentGuild}`);
            const config = await response.json();
            
            if (response.ok) {
                // Populate form fields
                this.setElementValue('leveling-enabled', config.enabled);
                this.setElementValue('level-announcements', config.level_up_announcements);
                this.setElementValue('base-xp', config.base_xp);
                this.setElementValue('max-xp', config.max_xp);
                this.setElementValue('daily-cap', config.daily_xp_cap);
                this.setElementValue('min-cooldown', config.min_cooldown_seconds);
                this.setElementValue('max-cooldown', config.max_cooldown_seconds);
                this.setElementValue('min-chars', config.min_message_chars);
                this.setElementValue('min-words', config.min_message_words);
            }
        } catch (error) {
            console.error('Error loading configuration:', error);
        }
    }
    
    async saveConfiguration() {
        if (!this.currentGuild) {
            this.showStatus('Please select a guild first', 'error');
            return;
        }
        
        const saveBtn = document.getElementById('save-config');
        const originalText = saveBtn ? saveBtn.textContent : '';
        
        try {
            // Show loading state
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = 'Saving...';
            }
            
            const config = {
                guild_id: this.currentGuild,
                enabled: this.getElementValue('leveling-enabled'),
                level_up_announcements: this.getElementValue('level-announcements'),
                base_xp: parseInt(this.getElementValue('base-xp')),
                max_xp: parseInt(this.getElementValue('max-xp')),
                daily_xp_cap: parseInt(this.getElementValue('daily-cap')),
                min_cooldown_seconds: parseInt(this.getElementValue('min-cooldown')),
                max_cooldown_seconds: parseInt(this.getElementValue('max-cooldown')),
                min_message_chars: parseInt(this.getElementValue('min-chars')),
                min_message_words: parseInt(this.getElementValue('min-words'))
            };
            
            const response = await fetch('/api/leveling/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showStatus('Configuration saved successfully!', 'success');
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showStatus('Network error occurred', 'error');
        } finally {
            // Restore button state
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            }
        }
    }
    
    async loadLeaderboard() {
        if (!this.currentGuild) return;
        
        try {
            const limit = this.getElementValue('leaderboard-limit') || 25;
            const response = await fetch(`/api/leveling/leaderboard?guild_id=${this.currentGuild}&limit=${limit}`);
            const leaderboard = await response.json();
            
            if (response.ok) {
                this.updateLeaderboard(leaderboard);
            }
        } catch (error) {
            console.error('Error loading leaderboard:', error);
        }
    }
    
    updateLeaderboard(leaderboard) {
        const tbody = document.getElementById('leaderboard-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (leaderboard.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="5" class="no-data">No leaderboard data available</td>';
            tbody.appendChild(row);
            return;
        }
        
        leaderboard.forEach((entry, index) => {
            const row = document.createElement('tr');
            row.className = 'leaderboard-row';
            
            // Calculate progress to next level
            const progress = this.calculateLevelProgress(entry.current_level, entry.total_xp);
            const userName = entry.user_name || `User ${entry.user_id.slice(-4)}`;
            
            row.innerHTML = `
                <td class="rank-cell">
                    <span class="rank-badge rank-${this.getRankClass(entry.position || index + 1)}">#${entry.position || index + 1}</span>
                </td>
                <td class="user-cell">
                    <div class="user-avatar">${this.getUserInitial(entry.user_id)}</div>
                    <div class="user-info">
                        <div class="user-name">${userName}</div>
                        <div class="user-meta">${this.formatNumber(entry.messages_sent)} messages</div>
                    </div>
                </td>
                <td class="level-cell">
                    <span class="level-badge">${entry.current_level}</span>
                </td>
                <td class="xp-cell">
                    <span class="xp-amount">${this.formatNumber(entry.total_xp)}</span>
                </td>
                <td class="progress-cell">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <span class="progress-text">${progress}%</span>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    async loadLiveFeed() {
        if (this.feedPaused) return;
        
        try {
            const url = this.currentGuild ?
                `/api/leveling/live-feed?guild_id=${this.currentGuild}&limit=20` :
                '/api/leveling/live-feed?limit=20';
            
            const response = await fetch(url);
            const feed = await response.json();
            
            if (response.ok) {
                this.updateLiveFeed(feed);
            } else {
                console.error('Error in live feed response:', feed.error);
            }
        } catch (error) {
            console.error('Error loading live feed:', error);
        }
    }
    
    updateLiveFeed(feedData) {
        const feedContainer = document.getElementById('xp-feed');
        if (!feedContainer) return;
        
        feedContainer.innerHTML = '';
        
        if (feedData.length === 0) {
            feedContainer.innerHTML = '<div class="no-data">No recent XP activity</div>';
            return;
        }
        
        feedData.slice(0, 20).forEach(entry => {
            const feedItem = document.createElement('div');
            feedItem.className = 'xp-feed-item';
            
            const timestamp = new Date(entry.timestamp).toLocaleTimeString();
            const capIndicator = entry.daily_cap_applied ? ' 🔒' : '';
            const userName = entry.user_name || `User ${entry.user_id.slice(-4)}`;
            
            feedItem.innerHTML = `
                <div class="feed-avatar">${this.getUserInitial(entry.user_id)}</div>
                <div class="feed-content">
                    <div class="feed-text">
                        <strong>${userName}</strong> earned
                        <span class="xp-amount">+${entry.xp_awarded} XP${capIndicator}</span>
                    </div>
                    <div class="feed-meta">
                        ${entry.word_count} words • ${entry.char_count} chars • ${timestamp}
                    </div>
                </div>
            `;
            
            feedContainer.appendChild(feedItem);
        });
    }
    
    toggleFeed() {
        this.feedPaused = !this.feedPaused;
        const toggleBtn = document.getElementById('toggle-feed');
        
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (this.feedPaused) {
                icon.className = 'fas fa-play';
                toggleBtn.title = 'Resume feed';
            } else {
                icon.className = 'fas fa-pause';
                toggleBtn.title = 'Pause feed';
                this.loadLiveFeed(); // Immediately load when resuming
            }
        }
    }
    
    async applyManualAdjustment() {
        const userId = this.getElementValue('target-user');
        const adjustType = this.getElementValue('adjust-type');
        const amount = parseInt(this.getElementValue('adjust-amount'));
        
        if (!userId || !adjustType || isNaN(amount)) {
            this.showStatus('Please fill in all fields', 'error');
            return;
        }
        
        if (!this.currentGuild) {
            this.showStatus('Please select a guild first', 'error');
            return;
        }
        
        const applyBtn = document.getElementById('apply-adjustment');
        const originalText = applyBtn ? applyBtn.textContent : '';
        
        try {
            // Show loading state
            if (applyBtn) {
                applyBtn.disabled = true;
                applyBtn.textContent = 'Applying...';
            }
            
            // Resolve user name for confirmation
            const response = await fetch(`/api/leveling/user-stats?user_id=${userId}&guild_id=${this.currentGuild}`);
            let userName = `User ${userId.slice(-4)}`;
            if (response.ok) {
                const userStats = await response.json();
                userName = userStats.user_name || userName;
            }
            
            const adjustResponse = await fetch('/api/leveling/manual-adjust', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    guild_id: this.currentGuild,
                    type: adjustType,
                    amount: amount
                })
            });
            
            const result = await adjustResponse.json();
            
            if (adjustResponse.ok) {
                this.showStatus(`Successfully applied ${adjustType} for ${userName}: ${result.message}`, 'success');
                // Clear form
                this.setElementValue('target-user', '');
                this.setElementValue('adjust-amount', '');
                // Refresh leaderboard
                this.loadLeaderboard();
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error applying adjustment:', error);
            this.showStatus('Network error occurred', 'error');
        } finally {
            // Restore button state
            if (applyBtn) {
                applyBtn.disabled = false;
                applyBtn.textContent = originalText;
            }
        }
    }
    
    async lookupUser() {
        const userId = this.getElementValue('lookup-user');
        
        if (!userId) {
            this.showStatus('Please enter a user ID', 'error');
            return;
        }
        
        if (!this.currentGuild) {
            this.showStatus('Please select a guild first', 'error');
            return;
        }
        
        const lookupBtn = document.getElementById('lookup-btn');
        const originalText = lookupBtn ? lookupBtn.textContent : '';
        
        try {
            // Show loading state
            if (lookupBtn) {
                lookupBtn.disabled = true;
                lookupBtn.textContent = 'Looking up...';
            }
            
            const response = await fetch(`/api/leveling/user-stats?user_id=${userId}&guild_id=${this.currentGuild}`);
            const stats = await response.json();
            
            if (response.ok) {
                this.displayUserStats(stats);
                this.showStatus('User stats loaded successfully', 'success');
            } else {
                this.showStatus(`Error: ${stats.error}`, 'error');
            }
        } catch (error) {
            console.error('Error looking up user:', error);
            this.showStatus('Network error occurred', 'error');
        } finally {
            // Restore button state
            if (lookupBtn) {
                lookupBtn.disabled = false;
                lookupBtn.textContent = originalText;
            }
        }
    }
    
    displayUserStats(stats) {
        const userStatsContainer = document.getElementById('user-stats');
        if (!userStatsContainer) return;
        
        const progress = this.calculateLevelProgress(stats.current_level, stats.total_xp);
        const rankPosition = stats.rank_info?.position || 'N/A';
        const rankTitle = stats.rank_info?.rank_title || 'No Rank';
        const userName = stats.user_name || `User ${stats.user_id?.slice(-4) || 'Unknown'}`;
        
        userStatsContainer.innerHTML = `
            <div class="user-stats-header">
                <h4>${userName}</h4>
            </div>
            <div class="user-stats-grid">
                <div class="user-stat">
                    <label>Current Level</label>
                    <span class="level-badge">${stats.current_level}</span>
                </div>
                <div class="user-stat">
                    <label>Total XP</label>
                    <span>${this.formatNumber(stats.total_xp)}</span>
                </div>
                <div class="user-stat">
                    <label>Current XP</label>
                    <span>${this.formatNumber(stats.current_xp)}</span>
                </div>
                <div class="user-stat">
                    <label>Messages</label>
                    <span>${this.formatNumber(stats.messages_sent)}</span>
                </div>
                <div class="user-stat">
                    <label>Daily XP</label>
                    <span>${this.formatNumber(stats.daily_xp_earned || 0)}</span>
                </div>
                <div class="user-stat">
                    <label>Server Rank</label>
                    <span>#${rankPosition}</span>
                </div>
                <div class="user-stat">
                    <label>Rank Title</label>
                    <span>${rankTitle}</span>
                </div>
            </div>
            <div class="level-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <span class="progress-text">${progress}% to next level</span>
            </div>
        `;
        
        userStatsContainer.style.display = 'block';
    }
    
    startPeriodicUpdates() {
        // Update live feed every 5 seconds
        this.feedUpdateInterval = setInterval(() => {
            if (!this.feedPaused && this.currentGuild) {
                this.loadLiveFeed();
            }
        }, 5000);
        
        // Update leaderboard every 30 seconds
        this.leaderboardUpdateInterval = setInterval(() => {
            if (this.currentGuild) {
                this.loadLeaderboard();
                this.loadStats();
            }
        }, 30000);
    }
    
    // Utility functions
    calculateLevelProgress(level, totalXp) {
        // Calculate XP required for current and next level
        const currentLevelXp = 50 * (level * level) + (100 * level);
        const nextLevelXp = 50 * ((level + 1) * (level + 1)) + (100 * (level + 1));
        const xpInLevel = totalXp - currentLevelXp;
        const xpNeeded = nextLevelXp - currentLevelXp;
        
        return Math.min(Math.round((xpInLevel / xpNeeded) * 100), 100);
    }
    
    getRankClass(rank) {
        if (rank === 1) return 'gold';
        if (rank === 2) return 'silver';
        if (rank === 3) return 'bronze';
        if (rank <= 10) return 'top10';
        return 'default';
    }
    
    getUserInitial(userId) {
        return userId.slice(-1).toUpperCase();
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    getElementValue(id) {
        const element = document.getElementById(id);
        if (!element) return null;
        
        if (element.type === 'checkbox') {
            return element.checked;
        }
        return element.value;
    }
    
    setElementValue(id, value) {
        const element = document.getElementById(id);
        if (!element) return;
        
        if (element.type === 'checkbox') {
            element.checked = value;
        } else {
            element.value = value;
        }
    }
    
    showLoadingState(show) {
        const levelingSection = document.getElementById('leveling-view');
        if (!levelingSection) return;
        
        if (show) {
            // Create and show loading indicator
            let loader = levelingSection.querySelector('.loading-indicator');
            if (!loader) {
                loader = document.createElement('div');
                loader.className = 'loading-indicator';
                loader.innerHTML = `
                    <div class="spinner"></div>
                    <p>Loading guild data...</p>
                `;
                levelingSection.appendChild(loader);
            }
            loader.style.display = 'flex';
        } else {
            // Hide loading indicator
            const loader = levelingSection.querySelector('.loading-indicator');
            if (loader) {
                loader.style.display = 'none';
            }
        }
    }
    
    showStatus(message, type) {
        const statusElement = document.getElementById('status-message');
        if (!statusElement) {
            // Create a fallback status element if none exists
            console.log(`Status: ${message} (${type})`);
            return;
        }
        
        statusElement.textContent = message;
        statusElement.className = `status-message ${type}`;
        statusElement.style.display = 'block';
        
        // Clear any existing timeout
        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
        }
        
        // Auto-hide after 5 seconds
        this.statusTimeout = setTimeout(() => {
            statusElement.style.display = 'none';
        }, 5000);
    }

    // ========================================
    // RANK MANAGEMENT METHODS
    // ========================================

    async loadRanks() {
        if (!this.currentGuild) return;

        try {
            const response = await fetch(`/api/leveling/ranks?guild_id=${this.currentGuild}`);
            const ranks = await response.json();

            if (response.ok) {
                this.displayRanks(ranks);
            }
        } catch (error) {
            console.error('Error loading ranks:', error);
        }
    }

    displayRanks(ranks) {
        const ranksBody = document.getElementById('ranks-body');
        if (!ranksBody) return;

        ranksBody.innerHTML = '';

        if (ranks.length === 0) {
            ranksBody.innerHTML = '<tr><td colspan="6" class="no-data">No ranks configured</td></tr>';
            return;
        }

        ranks.forEach(rank => {
            const row = document.createElement('tr');
            row.className = 'rank-row';

            const levelRange = rank.level_max ?
                `${rank.level_min} - ${rank.level_max}` :
                `${rank.level_min}+`;

            row.innerHTML = `
                <td class="rank-name-cell">
                    <div class="rank-display">
                        ${rank.emoji ? `<span class="rank-emoji">${rank.emoji}</span>` : ''}
                        <span class="rank-name">${rank.name}</span>
                    </div>
                </td>
                <td class="level-range-cell">${levelRange}</td>
                <td class="user-count-cell">${rank.user_count || 0}</td>
                <td class="color-cell">
                    <div class="color-preview" style="background-color: ${rank.color}"></div>
                    <span>${rank.color}</span>
                </td>
                <td class="role-cell">
                    ${rank.discord_role_id ?
                        `<span class="role-badge">${rank.discord_role_id}</span>` :
                        '<span class="no-role">None</span>'}
                </td>
                <td class="actions-cell">
                    <button class="action-btn edit-btn" onclick="editRank(${rank.id})" title="Edit Rank">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete-btn" onclick="deleteRank(${rank.id})" title="Delete Rank">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;

            ranksBody.appendChild(row);
        });
    }

    showRankModal(rankId = null) {
        const modal = document.getElementById('rank-modal');
        const title = document.getElementById('rank-modal-title');
        const form = document.getElementById('rank-form');

        if (!modal || !title || !form) return;

        // Reset form
        form.reset();
        document.getElementById('rank-id').value = rankId || '';

        if (rankId) {
            title.textContent = 'Edit Rank';
            this.loadRankData(rankId);
        } else {
            title.textContent = 'Add New Rank';
        }

        modal.style.display = 'block';
    }

    async loadRankData(rankId) {
        try {
            const response = await fetch(`/api/leveling/ranks/${rankId}?guild_id=${this.currentGuild}`);
            const rank = await response.json();

            if (response.ok) {
                document.getElementById('rank-name').value = rank.name || '';
                document.getElementById('rank-level-min').value = rank.level_min || '';
                document.getElementById('rank-level-max').value = rank.level_max || '';
                document.getElementById('rank-color').value = rank.color || '#ffffff';
                document.getElementById('rank-emoji').value = rank.emoji || '';
                document.getElementById('rank-role-id').value = rank.discord_role_id || '';
                document.getElementById('rank-description').value = rank.description || '';
            }
        } catch (error) {
            console.error('Error loading rank data:', error);
            this.showStatus('Error loading rank data', 'error');
        }
    }

    async saveRank() {
        const rankId = document.getElementById('rank-id').value;
        const formData = {
            guild_id: this.currentGuild,
            name: document.getElementById('rank-name').value.trim(),
            level_min: parseInt(document.getElementById('rank-level-min').value),
            level_max: document.getElementById('rank-level-max').value ?
                parseInt(document.getElementById('rank-level-max').value) : null,
            color: document.getElementById('rank-color').value,
            emoji: document.getElementById('rank-emoji').value.trim(),
            discord_role_id: document.getElementById('rank-role-id').value.trim() || null,
            description: document.getElementById('rank-description').value.trim()
        };

        // Validation
        if (!formData.name || !formData.level_min) {
            this.showStatus('Please fill in required fields', 'error');
            return;
        }

        if (formData.level_max && formData.level_max < formData.level_min) {
            this.showStatus('Max level must be greater than min level', 'error');
            return;
        }

        try {
            const url = rankId ? `/api/leveling/ranks/${rankId}` : '/api/leveling/ranks';
            const method = rankId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showStatus(`Rank ${rankId ? 'updated' : 'created'} successfully!`, 'success');
                this.closeModal('rank-modal');
                this.loadRanks();
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error saving rank:', error);
            this.showStatus('Network error occurred', 'error');
        }
    }

    async deleteRank(rankId) {
        if (!confirm('Are you sure you want to delete this rank? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/leveling/ranks/${rankId}?guild_id=${this.currentGuild}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok) {
                this.showStatus('Rank deleted successfully!', 'success');
                this.loadRanks();
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting rank:', error);
            this.showStatus('Network error occurred', 'error');
        }
    }

    // ========================================
    // TEMPLATE MANAGEMENT METHODS
    // ========================================

    async loadTemplates(type = 'default_levelup') {
        if (!this.currentGuild) return;

        try {
            const response = await fetch(`/api/leveling/templates?guild_id=${this.currentGuild}&type=${type}`);
            const templates = await response.json();

            if (response.ok) {
                this.displayTemplates(templates, type);
            }
        } catch (error) {
            console.error('Error loading templates:', error);
        }
    }

    displayTemplates(templates, type) {
        const templatesContent = document.getElementById('templates-content');
        if (!templatesContent) return;

        templatesContent.innerHTML = '';

        if (templates.length === 0) {
            templatesContent.innerHTML = '<div class="no-data">No templates found for this type</div>';
            return;
        }

        templates.forEach(template => {
            const templateCard = document.createElement('div');
            templateCard.className = 'template-card';

            templateCard.innerHTML = `
                <div class="template-header">
                    <div class="template-info">
                        <h4 class="template-name">${template.name}</h4>
                        <span class="template-priority">Priority: ${template.priority}</span>
                    </div>
                    <div class="template-status">
                        <span class="status-badge ${template.enabled ? 'enabled' : 'disabled'}">
                            ${template.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                    </div>
                </div>
                <div class="template-content-preview">
                    <code>${template.content.length > 100 ?
                        template.content.substring(0, 100) + '...' :
                        template.content}</code>
                </div>
                <div class="template-actions">
                    <button class="action-btn preview-btn" onclick="previewTemplateById(${template.id})" title="Preview">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn edit-btn" onclick="editTemplate(${template.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete-btn" onclick="deleteTemplate(${template.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            templatesContent.appendChild(templateCard);
        });
    }

    switchTemplateTab(type) {
        // Update active tab
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-type="${type}"]`).classList.add('active');

        // Load templates for selected type
        this.loadTemplates(type);
    }

    showTemplateModal(templateId = null) {
        const modal = document.getElementById('template-modal');
        const title = document.getElementById('template-modal-title');
        const form = document.getElementById('template-form');

        if (!modal || !title || !form) return;

        // Reset form
        form.reset();
        document.getElementById('template-id').value = templateId || '';
        document.getElementById('template-enabled').checked = true;

        if (templateId) {
            title.textContent = 'Edit Template';
            this.loadTemplateData(templateId);
        } else {
            title.textContent = 'Add Message Template';
            // Set default type from active tab
            const activeTab = document.querySelector('.tab-btn.active');
            if (activeTab) {
                document.getElementById('template-type').value = activeTab.dataset.type;
            }
        }

        modal.style.display = 'block';
    }

    async loadTemplateData(templateId) {
        try {
            const response = await fetch(`/api/leveling/templates/${templateId}?guild_id=${this.currentGuild}`);
            const template = await response.json();

            if (response.ok) {
                document.getElementById('template-name').value = template.name || '';
                document.getElementById('template-type').value = template.type || '';
                document.getElementById('template-content').value = template.content || '';
                document.getElementById('template-conditions').value = template.conditions || '';
                document.getElementById('template-priority').value = template.priority || 0;
                document.getElementById('template-enabled').checked = template.enabled || false;
            }
        } catch (error) {
            console.error('Error loading template data:', error);
            this.showStatus('Error loading template data', 'error');
        }
    }

    async saveTemplate() {
        const templateId = document.getElementById('template-id').value;
        const formData = {
            guild_id: this.currentGuild,
            name: document.getElementById('template-name').value.trim(),
            type: document.getElementById('template-type').value,
            content: document.getElementById('template-content').value.trim(),
            conditions: document.getElementById('template-conditions').value.trim(),
            priority: parseInt(document.getElementById('template-priority').value) || 0,
            enabled: document.getElementById('template-enabled').checked
        };

        // Validation
        if (!formData.name || !formData.type || !formData.content) {
            this.showStatus('Please fill in required fields', 'error');
            return;
        }

        // Validate JSON conditions if provided
        if (formData.conditions) {
            try {
                JSON.parse(formData.conditions);
            } catch (e) {
                this.showStatus('Invalid JSON in conditions field', 'error');
                return;
            }
        }

        try {
            const url = templateId ? `/api/leveling/templates/${templateId}` : '/api/leveling/templates';
            const method = templateId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showStatus(`Template ${templateId ? 'updated' : 'created'} successfully!`, 'success');
                this.closeModal('template-modal');
                this.loadTemplates(formData.type);
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error saving template:', error);
            this.showStatus('Network error occurred', 'error');
        }
    }

    async deleteTemplate(templateId) {
        if (!confirm('Are you sure you want to delete this template? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(`/api/leveling/templates/${templateId}?guild_id=${this.currentGuild}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok) {
                this.showStatus('Template deleted successfully!', 'success');
                const activeTab = document.querySelector('.tab-btn.active');
                if (activeTab) {
                    this.loadTemplates(activeTab.dataset.type);
                }
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting template:', error);
            this.showStatus('Network error occurred', 'error');
        }
    }

    async previewTemplateById(templateId) {
        try {
            const response = await fetch(`/api/leveling/templates/${templateId}/preview?guild_id=${this.currentGuild}`);
            const preview = await response.json();

            if (response.ok) {
                this.showPreviewModal(preview.preview);
            } else {
                this.showStatus(`Error: ${preview.error}`, 'error');
            }
        } catch (error) {
            console.error('Error previewing template:', error);
            this.showStatus('Network error occurred', 'error');
        }
    }

    previewTemplate() {
        const content = document.getElementById('template-content').value.trim();
        if (!content) {
            this.showStatus('Please enter template content first', 'error');
            return;
        }

        // Generate preview with sample data
        const sampleData = {
            user: '@TestUser',
            level: '10',
            previous_level: '9',
            xp: '2500',
            xp_needed: '275',
            rank: 'Advanced',
            previous_rank: 'Intermediate',
            guild: 'Test Server',
            leaderboard_position: '15'
        };

        let preview = content;
        Object.keys(sampleData).forEach(key => {
            const regex = new RegExp(`\\{${key}\\}`, 'g');
            preview = preview.replace(regex, sampleData[key]);
        });

        this.showPreviewModal(preview);
    }

    showPreviewModal(previewContent) {
        const modal = document.getElementById('preview-modal');
        const content = document.getElementById('preview-content');

        if (!modal || !content) return;

        content.textContent = previewContent;
        modal.style.display = 'block';
    }

    showVariableReference() {
        const modal = document.getElementById('variable-reference-modal');
        if (!modal) return;

        modal.style.display = 'block';

        // Add click handlers to copy variables
        modal.querySelectorAll('code').forEach(codeEl => {
            codeEl.style.cursor = 'pointer';
            codeEl.onclick = () => {
                navigator.clipboard.writeText(codeEl.textContent).then(() => {
                    this.showStatus(`Copied "${codeEl.textContent}" to clipboard`, 'success');
                });
            };
        });
    }

    // ========================================
    // MODAL MANAGEMENT
    // ========================================

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    destroy() {
        if (this.feedUpdateInterval) {
            clearInterval(this.feedUpdateInterval);
        }
        if (this.leaderboardUpdateInterval) {
            clearInterval(this.leaderboardUpdateInterval);
        }
    }
}

// Export for global access
window.LevelingDashboard = LevelingDashboard;
