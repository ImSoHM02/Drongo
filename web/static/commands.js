// Commands section specific functionality

class CommandsManager {
    constructor() {
        this.setupEventListeners();
    }
    
    setupEventListeners() {
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
                        `<div style="margin-bottom: 0.5rem; padding: 0.5rem; background: var(--bg-primary);">
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
}

// Initialize commands manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.commandsManager = new CommandsManager();
});

// Export for global access
window.CommandsManager = CommandsManager;