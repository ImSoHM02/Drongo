// Chat History Frontend JavaScript

// State management
let chatState = {
    guilds: [],
    selectedGuild: null,
    selectedChannel: null,
    channels: [],
    messages: [],
    fetchProgress: {},
    loading: false,
    messageOffset: 0
};

// Initialize chat history view
async function initChatHistory() {
    console.log('Initializing chat history view');

    // Load guilds on initialization
    await loadGuilds();

    // Set up event listeners
    setupEventListeners();

    // Start periodic updates
    startPeriodicUpdates();
}

// Load all guilds
async function loadGuilds() {
    try {
        chatState.loading = true;
        updateLoadingState();

        const response = await fetch('/api/chat/guilds');
        const data = await response.json();

        chatState.guilds = data.guilds || [];
        renderGuildList(chatState.guilds);

    } catch (error) {
        console.error('Error loading guilds:', error);
        showError('Failed to load guilds');
    } finally {
        chatState.loading = false;
        updateLoadingState();
    }
}

// Load channels for a guild
async function loadChannels(guildId) {
    try {
        const response = await fetch(`/api/chat/guild/${guildId}/channels`);
        const data = await response.json();

        chatState.channels = data.channels || [];
        renderChannelList(chatState.channels);

    } catch (error) {
        console.error('Error loading channels:', error);
        showError('Failed to load channels');
    }
}

// Load messages for a channel
async function loadMessages(guildId, channelId = null, limit = 50, offset = 0) {
    try {
        chatState.loading = true;
        updateLoadingState();

        let url = `/api/chat/guild/${guildId}/messages?limit=${limit}&offset=${offset}`;
        if (channelId) {
            url += `&channel_id=${channelId}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (offset === 0) {
            chatState.messages = data.messages || [];
        } else {
            chatState.messages = [...chatState.messages, ...(data.messages || [])];
        }

        chatState.messageOffset = offset;
        renderMessages(chatState.messages, data.has_more);

    } catch (error) {
        console.error('Error loading messages:', error);
        showError('Failed to load messages');
    } finally {
        chatState.loading = false;
        updateLoadingState();
    }
}

// Load recent messages
async function loadRecentMessages(guildId, channelId = null) {
    try {
        let url = `/api/chat/guild/${guildId}/recent`;
        if (channelId) {
            url += `?channel_id=${channelId}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        renderRecentMessages(data.messages || []);

    } catch (error) {
        console.error('Error loading recent messages:', error);
    }
}

// Toggle logging for a guild
async function toggleLogging(guildId, enabled) {
    try {
        const response = await fetch(`/api/chat/guild/${guildId}/settings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ logging_enabled: enabled })
        });

        if (response.ok) {
            // Update local state
            const guild = chatState.guilds.find(g => g.guild_id === guildId);
            if (guild) {
                guild.logging_enabled = enabled;
            }

            showSuccess(`Logging ${enabled ? 'enabled' : 'disabled'} for this guild`);
        }

    } catch (error) {
        console.error('Error toggling logging:', error);
        showError('Failed to update logging settings');
    }
}

// Load fetch progress
async function loadFetchProgress() {
    try {
        const response = await fetch('/api/chat/fetch-progress');
        const data = await response.json();

        chatState.fetchProgress = {};
        (data.progress || []).forEach(p => {
            chatState.fetchProgress[p.guild_id] = p;
        });

        updateFetchProgress();

    } catch (error) {
        console.error('Error loading fetch progress:', error);
    }
}

// Render guild list
function renderGuildList(guilds) {
    const container = document.getElementById('guild-list');
    if (!container) return;

    if (guilds.length === 0) {
        container.innerHTML = '<div class="empty-state">No guilds found</div>';
        return;
    }

    container.innerHTML = guilds.map(guild => `
        <div class="guild-item ${chatState.selectedGuild === guild.guild_id ? 'active' : ''}"
             data-guild-id="${guild.guild_id}"
             onclick="onGuildSelected('${guild.guild_id}')">
            <div class="guild-name">${escapeHtml(guild.guild_name)}</div>
            <div class="guild-stats">
                <span class="message-count">${guild.total_messages.toLocaleString()} messages</span>
                ${guild.is_scanning ? '<span class="scanning-badge">Scanning...</span>' : ''}
            </div>
            ${guild.fetch_progress.percentage < 100 ? `
                <div class="guild-progress">
                    <div class="progress-bar-mini">
                        <div class="progress-fill-mini" style="width: ${guild.fetch_progress.percentage}%"></div>
                    </div>
                    <span class="progress-text">${guild.fetch_progress.percentage}%</span>
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Render channel list
function renderChannelList(channels) {
    const container = document.getElementById('channel-list');
    if (!container) return;

    if (channels.length === 0) {
        container.innerHTML = '<div class="empty-state">No channels with messages</div>';
        return;
    }

    // Add "All Channels" option at the top
    let html = `
        <div class="channel-item ${chatState.selectedChannel === null ? 'active' : ''}"
             onclick="onChannelSelected(null)">
            <div class="channel-name"># All Channels</div>
            <div class="channel-count"></div>
        </div>
    `;

    html += channels.map(channel => `
        <div class="channel-item ${chatState.selectedChannel === channel.channel_id ? 'active' : ''}"
             data-channel-id="${channel.channel_id}"
             onclick="onChannelSelected('${channel.channel_id}')">
            <div class="channel-name"># ${escapeHtml(channel.channel_name)}</div>
            <div class="channel-count">${channel.message_count.toLocaleString()}</div>
        </div>
    `).join('');

    container.innerHTML = html;
}

// Render messages
function renderMessages(messages, hasMore = false) {
    const container = document.getElementById('message-list');
    if (!container) return;

    if (messages.length === 0) {
        container.innerHTML = '<div class="empty-state">No messages found</div>';
        return;
    }

    const html = messages.map(msg => `
        <div class="message-item" data-message-id="${msg.id}">
            <div class="message-header">
                <span class="message-author">${escapeHtml(msg.username)}</span>
                <span class="message-channel"># ${escapeHtml(msg.channel_name)}</span>
                <span class="message-timestamp">${formatTimestamp(msg.timestamp)}</span>
            </div>
            <div class="message-content">${escapeHtml(msg.message_content)}</div>
        </div>
    `).join('');

    container.innerHTML = html;

    // Show/hide load more button
    const loadMoreBtn = document.getElementById('load-more-messages');
    if (loadMoreBtn) {
        loadMoreBtn.style.display = hasMore ? 'block' : 'none';
    }
}

// Render recent messages
function renderRecentMessages(messages) {
    const container = document.getElementById('recent-messages-list');
    if (!container) return;

    if (messages.length === 0) {
        container.innerHTML = '<div class="empty-state">No recent messages</div>';
        return;
    }

    const html = messages.map(msg => `
        <div class="recent-message-item">
            <div class="recent-message-header">
                <span class="recent-message-author">${escapeHtml(msg.username)}</span>
                <span class="recent-message-time">${formatTimestamp(msg.timestamp)}</span>
            </div>
            <div class="recent-message-content">${escapeHtml(msg.message_content.substring(0, 100))}${msg.message_content.length > 100 ? '...' : ''}</div>
        </div>
    `).join('');

    container.innerHTML = html;
}

// Update fetch progress indicator
function updateFetchProgress() {
    if (!chatState.selectedGuild) return;

    const progress = chatState.fetchProgress[chatState.selectedGuild];
    if (!progress) return;

    const progressBar = document.getElementById('fetch-progress-fill');
    const progressText = document.getElementById('fetch-percentage');
    const progressStatus = document.getElementById('fetch-status');

    if (progressBar) {
        progressBar.style.width = `${progress.percentage}%`;
    }

    if (progressText) {
        progressText.textContent = `${progress.percentage}%`;
    }

    if (progressStatus) {
        if (progress.is_complete) {
            progressStatus.textContent = 'Complete';
            progressStatus.className = 'status-complete';
        } else {
            progressStatus.textContent = `Fetching (${progress.completed_channels}/${progress.total_channels} channels)`;
            progressStatus.className = 'status-active';
        }
    }
}

// Event handlers
function onGuildSelected(guildId) {
    chatState.selectedGuild = guildId;
    chatState.selectedChannel = null;
    chatState.messageOffset = 0;

    // Update UI
    renderGuildList(chatState.guilds);

    // Update guild info header
    const guild = chatState.guilds.find(g => g.guild_id === guildId);
    if (guild) {
        const nameEl = document.getElementById('selected-guild-name');
        if (nameEl) {
            nameEl.textContent = guild.guild_name;
        }

        const toggleEl = document.getElementById('logging-toggle');
        if (toggleEl) {
            toggleEl.checked = guild.logging_enabled;
        }
    }

    // Load data
    loadChannels(guildId);
    loadMessages(guildId);
    loadRecentMessages(guildId);
    updateFetchProgress();
}

function onChannelSelected(channelId) {
    chatState.selectedChannel = channelId;
    chatState.messageOffset = 0;

    // Update UI
    renderChannelList(chatState.channels);

    // Update channel name header
    const nameEl = document.getElementById('selected-channel-name');
    if (nameEl) {
        if (channelId) {
            const channel = chatState.channels.find(c => c.channel_id === channelId);
            nameEl.textContent = channel ? `# ${channel.channel_name}` : 'Channel';
        } else {
            nameEl.textContent = 'All Channels';
        }
    }

    // Load messages for this channel
    loadMessages(chatState.selectedGuild, channelId);
    loadRecentMessages(chatState.selectedGuild, channelId);
}

function onLoadMore() {
    if (!chatState.selectedGuild || chatState.loading) return;

    const newOffset = chatState.messageOffset + 50;
    loadMessages(chatState.selectedGuild, chatState.selectedChannel, 50, newOffset);
}

function onLoggingToggle(event) {
    if (!chatState.selectedGuild) return;

    const enabled = event.target.checked;
    toggleLogging(chatState.selectedGuild, enabled);
}

function onRefreshGuilds() {
    loadGuilds();
}

// Setup event listeners
function setupEventListeners() {
    const toggleEl = document.getElementById('logging-toggle');
    if (toggleEl) {
        toggleEl.addEventListener('change', onLoggingToggle);
    }

    const loadMoreBtn = document.getElementById('load-more-messages');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', onLoadMore);
    }

    const refreshBtn = document.getElementById('refresh-guilds');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', onRefreshGuilds);
    }
}

// Periodic updates
function startPeriodicUpdates() {
    // Refresh guild list every 10 seconds to update message counts and scanning status
    setInterval(() => {
        loadGuilds();
    }, 10000);

    // Update fetch progress every 5 seconds
    setInterval(() => {
        if (chatState.selectedGuild) {
            loadFetchProgress();
        }
    }, 5000);

    // Reload recent messages every 5 seconds if a guild is selected
    setInterval(() => {
        if (chatState.selectedGuild) {
            loadRecentMessages(chatState.selectedGuild, chatState.selectedChannel);
        }
    }, 5000);
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '';

    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        // Less than 1 minute
        if (diff < 60000) {
            return 'Just now';
        }

        // Less than 1 hour
        if (diff < 3600000) {
            const mins = Math.floor(diff / 60000);
            return `${mins} min${mins > 1 ? 's' : ''} ago`;
        }

        // Less than 1 day
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        }

        // Less than 7 days
        if (diff < 604800000) {
            const days = Math.floor(diff / 86400000);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        }

        // Format as date
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    } catch (error) {
        return timestamp;
    }
}

function updateLoadingState() {
    const loadingEl = document.getElementById('chat-loading');
    if (loadingEl) {
        loadingEl.style.display = chatState.loading ? 'block' : 'none';
    }
}

function showError(message) {
    console.error(message);
    // Could add toast notification here
}

function showSuccess(message) {
    console.log(message);
    // Could add toast notification here
}

// Export init function
window.initChatHistory = initChatHistory;
