// Stats section specific functionality

class StatsManager {
    constructor() {
        this.charts = {};
        this.stats = {
            messages_processed: 0,
            commands_executed: 0,
            active_users: 0,
            uptime_seconds: 0
        };
        this.init();
    }
    
    init() {
        this.setupCharts();
        this.startPeriodicUpdates();
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
    
    startPeriodicUpdates() {
        setInterval(() => {
            if (this.stats.uptime_seconds !== undefined) {
                this.stats.uptime_seconds++;
                this.updateElement('uptime', this.formatUptime(this.stats.uptime_seconds));
            }
        }, 1000);
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
    
    // Method to resize charts when stats view becomes visible
    resizeCharts() {
        setTimeout(() => {
            if (this.charts.activity) {
                try {
                    this.charts.activity.resize();
                } catch (e) {
                    // Ignore resize errors
                }
            }
        }, 50);
    }
}

// Initialize stats manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.statsManager = new StatsManager();
});

// Export for global access
window.StatsManager = StatsManager;