// Initialize charts
const messagesCtx = document.getElementById('messagesChart').getContext('2d');
const usersCtx = document.getElementById('usersChart').getContext('2d');

const activityCtx = document.getElementById('activityChart').getContext('2d');

const messagesChart = new Chart(messagesCtx, {
    type: 'bar',
    data: {
        labels: [],
        datasets: [{
            label: 'Messages',
            backgroundColor: '#4285F4',
            data: []
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

const usersChart = new Chart(usersCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Active Users',
            borderColor: '#0F9D58',
            backgroundColor: 'rgba(15, 157, 88, 0.1)',
            fill: true,
            data: []
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

const activityChart = new Chart(activityCtx, {
    type: 'bar',
    data: {
        labels: [],
        datasets: [{
            label: 'Message Count',
            backgroundColor: '#F4B400',
            data: []
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        
        // Update basic stats
        document.getElementById('total-messages').textContent = data.total_messages.toLocaleString();
        document.getElementById('unique-users').textContent = data.unique_users.toLocaleString();
        document.getElementById('recent-messages').textContent = data.recent_messages.toLocaleString();
        document.getElementById('last-updated').textContent = new Date(data.last_updated).toLocaleString();

        // Update top users
        try {
            const topUsersHtml = data.top_users.map((user, index) => `
                <div class="user-entry">
                    <div>
                        <span class="rank">#${index + 1}</span>
                        <span class="user-id">${user[0]}</span>
                    </div>
                    <span class="message-count">${user[1].toLocaleString()} messages</span>
                </div>
            `).join('');
    
            document.getElementById('top-users').innerHTML = topUsersHtml || '<div class="empty-state">No user data available</div>';
        } catch (error) {
            console.error('Error fetching top users:', error);
        }

    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function updateChartData() {
    try {
        const response = await fetch('/api/chart_data');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();

        // Update messages chart
        messagesChart.data.labels = data.messages_over_time.map(item => item.date);
        messagesChart.data.datasets[0].data = data.messages_over_time.map(item => item.message_count);
        messagesChart.update();

        // Update users chart
        usersChart.data.labels = data.user_activity_over_time.map(item => item.date);
        usersChart.data.datasets[0].data = data.user_activity_over_time.map(item => item.active_users);
        usersChart.update();

        // Update activity chart
        activityChart.data.labels = data.user_activity_by_time.map(item => item.hour);
        activityChart.data.datasets[0].data = data.user_activity_by_time.map(item => item.message_count);
        activityChart.update();

    } catch (error) {
        console.error('Error fetching chart data:', error);
    }
}

// Initial load
updateStats();
updateChartData();

// Poll every 30 seconds
setInterval(updateStats, 30000);
setInterval(updateChartData, 30000);
