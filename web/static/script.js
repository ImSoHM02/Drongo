function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update basic stats
            document.getElementById('total-messages').textContent = data.total_messages.toLocaleString();
            document.getElementById('unique-users').textContent = data.unique_users.toLocaleString();
            document.getElementById('recent-messages').textContent = data.recent_messages.toLocaleString();
            document.getElementById('last-updated').textContent = data.last_updated;

            // Update top users
            const topUsersHtml = data.top_users.map((user, index) => `
                <div class="user-entry">
                    <div>
                        <span class="rank">#${index + 1}</span>
                        <span class="user-id">User ${user[0]}</span>
                    </div>
                    <span class="message-count">${user[1].toLocaleString()} messages</span>
                </div>
            `).join('');
            
            document.getElementById('top-users').innerHTML = topUsersHtml;
        })
        .catch(error => {
            console.error('Error fetching stats:', error);
        });
}

// Update stats immediately and then every 30 seconds
updateStats();
setInterval(updateStats, 30000);

// Add smooth transitions for stat updates
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'characterData' || mutation.type === 'childList') {
            const element = mutation.target.parentElement || mutation.target;
            element.classList.add('updated');
            setTimeout(() => element.classList.remove('updated'), 1000);
        }
    });
});

// Observe stat elements for changes
const statElements = document.querySelectorAll('.stat-card p, .user-entry');
statElements.forEach(element => {
    observer.observe(element, {
        characterData: true,
        childList: true,
        subtree: true
    });
});
