// Leveling section specific functionality

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

        // Level range management event listeners
        const addRangeBtn = document.getElementById('add-range-btn');
        if (addRangeBtn) {
            addRangeBtn.addEventListener('click', () => {
                this.showRangeModal();
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
                    // guild.name already includes the full ID in the format "Guild Name (ID)"
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
                this.loadTemplates(),
                this.loadLevelRanges()
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
            // Use the resolved name which includes full ID, or fallback with full ID
            const userName = entry.user_name || `User (${entry.user_id})`;
            const rangeName = entry.range_info?.name || entry.range_info?.range_name || entry.range_name;
            
            // Create range badge HTML if range exists
            const rangeBadge = rangeName ?
                `<span class="range-badge">${rangeName}</span>` : '';
            
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
                    ${rangeBadge}${entry.rank_title ? `<span class="rank-title"> • ${entry.rank_title}</span>` : ''}
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
            // Use the resolved name which includes full ID, or fallback with full ID
            const userName = entry.user_name || `User (${entry.user_id})`;
            
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
            let userName = `User (${userId})`;
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
        const rangeInfo = stats.range_info && Object.keys(stats.range_info).length ? stats.range_info : null;
        const rangeName = rangeInfo?.name || rangeInfo?.range_name || 'No Range';
        const rangeTier = rangeInfo
            ? `${rangeInfo.min_level}${rangeInfo.max_level !== null && rangeInfo.max_level !== undefined ? ` - ${rangeInfo.max_level}` : '+'}`
            : '—';
        // Use the resolved name which includes full ID, or fallback with full ID
        const userName = stats.user_name || `User (${stats.user_id || 'Unknown'})`;
        
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
                <div class="user-stat">
                    <label>Level Range</label>
                    <span>${rangeName}</span>
                </div>
                <div class="user-stat">
                    <label>Range Tier</label>
                    <span>${rangeTier}</span>
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
            const response = await fetch(`/api/leveling/ranks?guild_id=${this.currentGuild}`);
            const ranks = await response.json();

            if (response.ok) {
                const rank = ranks.find(r => r.id === rankId);
                if (rank) {
                    document.getElementById('rank-name').value = rank.name || '';
                    document.getElementById('rank-level-min').value = rank.level_min || '';
                    document.getElementById('rank-level-max').value = rank.level_max || '';
                    document.getElementById('rank-color').value = rank.color || '#ffffff';
                    document.getElementById('rank-emoji').value = rank.emoji || '';
                    document.getElementById('rank-role-id').value = rank.discord_role_id || '';
                    document.getElementById('rank-description').value = rank.description || '';
                }
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
            leaderboard_position: '15',
            range: 'Expert',
            tier: '3'
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
    // LEVEL RANGE MANAGEMENT METHODS
    // ========================================

    async loadLevelRanges() {
        if (!this.currentGuild) return;

        try {
            const response = await fetch(`/api/leveling/ranges/guild/${this.currentGuild}`);
            const ranges = await response.json();

            if (response.ok) {
                this.displayLevelRanges(ranges);
            }
        } catch (error) {
            console.error('Error loading level ranges:', error);
        }
    }

    displayLevelRanges(ranges) {
        const rangesContainer = document.getElementById('ranges-list');
        if (!rangesContainer) return;

        rangesContainer.innerHTML = '';

        if (ranges.length === 0) {
            rangesContainer.innerHTML = '<div class="no-data">No level ranges configured</div>';
            return;
        }

        ranges.forEach(range => {
            const rangeItem = document.createElement('div');
            rangeItem.className = 'range-item';

            rangeItem.innerHTML = `
                <div class="range-header">
                    <div class="range-info">
                        <h4 class="range-name">${range.range_name}</h4>
                        <span class="range-levels">Levels ${range.min_level} - ${range.max_level}</span>
                    </div>
                    <div class="range-actions">
                        <button class="action-btn edit-btn" onclick="levelingDashboard.editRange(${range.id})" title="Edit Range">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="action-btn delete-btn" onclick="levelingDashboard.deleteRange(${range.id})" title="Delete Range">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                ${range.description ? `<div class="range-description">${range.description}</div>` : ''}
            `;

            rangesContainer.appendChild(rangeItem);
        });
    }

    showRangeModal(rangeId = null) {
        const modal = document.getElementById('range-modal');
        const title = document.getElementById('range-modal-title');
        const form = document.getElementById('range-form');

        if (!modal || !title || !form) return;

        // Reset form
        form.reset();
        document.getElementById('range-id').value = rangeId || '';

        if (rangeId) {
            title.textContent = 'Edit Level Range';
            this.loadRangeData(rangeId);
        } else {
            title.textContent = 'Add New Level Range';
        }

        modal.style.display = 'block';
    }

    async loadRangeData(rangeId) {
        try {
            const ranges = await fetch(`/api/leveling/ranges/guild/${this.currentGuild}`);
            const allRanges = await ranges.json();
            
            if (ranges.ok) {
                const range = allRanges.find(r => r.id === rangeId);
                if (range) {
                    document.getElementById('range-name').value = range.range_name || '';
                    document.getElementById('range-min-level').value = range.min_level || '';
                    document.getElementById('range-max-level').value = range.max_level || '';
                    document.getElementById('range-description').value = range.description || '';
                }
            }
        } catch (error) {
            console.error('Error loading range data:', error);
            this.showStatus('Error loading range data', 'error');
        }
    }

    async saveRange() {
        const rangeId = document.getElementById('range-id').value;
        const formData = {
            guild_id: this.currentGuild,
            range_name: document.getElementById('range-name').value.trim(),
            min_level: parseInt(document.getElementById('range-min-level').value),
            max_level: parseInt(document.getElementById('range-max-level').value),
            description: document.getElementById('range-description').value.trim()
        };

        // Validation
        if (!formData.range_name || isNaN(formData.min_level) || isNaN(formData.max_level)) {
            this.showStatus('Please fill in all required fields', 'error');
            return;
        }

        if (formData.min_level >= formData.max_level) {
            this.showStatus('Maximum level must be greater than minimum level', 'error');
            return;
        }

        try {
            const url = '/api/leveling/ranges';
            const method = rangeId ? 'PUT' : 'POST';
            const body = rangeId ? { ...formData, range_id: parseInt(rangeId) } : formData;

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const result = await response.json();

            if (response.ok) {
                this.showStatus(`Level range ${rangeId ? 'updated' : 'created'} successfully!`, 'success');
                this.closeModal('range-modal');
                this.loadLevelRanges();
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error saving range:', error);
            this.showStatus('Network error occurred', 'error');
        }
    }

    async deleteRange(rangeId) {
        if (!confirm('Are you sure you want to delete this level range? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/leveling/ranges', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    guild_id: this.currentGuild,
                    range_id: rangeId
                })
            });

            const result = await response.json();

            if (response.ok) {
                this.showStatus('Level range deleted successfully!', 'success');
                this.loadLevelRanges();
            } else {
                this.showStatus(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting range:', error);
            this.showStatus('Network error occurred', 'error');
        }
    }

    editRange(rangeId) {
        this.showRangeModal(rangeId);
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

    destroy() {
        if (this.feedUpdateInterval) {
            clearInterval(this.feedUpdateInterval);
        }
        if (this.leaderboardUpdateInterval) {
            clearInterval(this.leaderboardUpdateInterval);
        }
    }
}

// Initialize leveling dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.levelingDashboard = new LevelingDashboard();
});

// Export for global access
window.LevelingDashboard = LevelingDashboard;
