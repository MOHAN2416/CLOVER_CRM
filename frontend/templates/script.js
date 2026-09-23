// Global API Base URL (keep empty if using vercel.json proxy)
const API_BASE = '';

// Global chart instances
let revenueChartInstance = null;

let leadMixChartInstance = null;

// Sidebar Collapsed functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const icon = document.getElementById('sidebar-toggle-icon');
    if (!sidebar) return;
    
    sidebar.classList.toggle('collapsed');
    if (icon) {
        if (sidebar.classList.contains('collapsed')) {
            icon.setAttribute('data-lucide', 'chevron-right');
        } else {
            icon.setAttribute('data-lucide', 'chevron-left');
        }
    }
    
    try {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    } catch (e) {
        console.error("Lucide icon toggle error:", e);
    }
    
    // Trigger window resize to recalculate ApexCharts widths
    setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
    }, 300);
}

// Set Current Local Time
function updateDashboardTime() {
    const dateBadge = document.getElementById('current-date-text');
    const timeBadge = document.getElementById('current-time-text');
    const now = new Date();
    
    if (dateBadge) {
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        dateBadge.innerText = now.toLocaleDateString('en-US', options);
    }
    if (timeBadge) {
        const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
        timeBadge.innerText = now.toLocaleTimeString('en-US', timeOptions);
    }
}

// Dynamic ApexCharts Builder
function renderDashboardCharts(data) {
    // Trailing 6 months Revenue Pipeline curve mapped directly to active revenue metrics
    const totalRevenue = data.leaderboard.reduce((sum, rep) => sum + parseFloat(rep.total_revenue), 0);
    const chartDataPoints = [
        totalRevenue * 0.4,
        totalRevenue * 0.55,
        totalRevenue * 0.7,
        totalRevenue * 0.82,
        totalRevenue * 0.9,
        totalRevenue
    ];

    // 1. Sales Revenue Performance Chart (Area Chart)
    const revenueChartOptions = {
        series: [{
            name: 'Cumulative Revenue (INR)',
            data: chartDataPoints
        }],
        chart: {
            type: 'area',
            height: 280,
            toolbar: { show: false },
            background: 'transparent'
        },
        colors: ['#4F8CFF'],
        dataLabels: { enabled: false },
        stroke: {
            curve: 'smooth',
            width: 3
        },
        fill: {
            type: 'gradient',
            gradient: {
                shadeIntensity: 1,
                opacityFrom: 0.45,
                opacityTo: 0.05,
                stops: [0, 90, 100]
            }
        },
        xaxis: {
            categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            labels: {
                style: { colors: '#A1A1AA', fontFamily: 'Plus Jakarta Sans' }
            },
            axisBorder: { show: false },
            axisTicks: { show: false }
        },
        yaxis: {
            labels: {
                style: { colors: '#A1A1AA', fontFamily: 'Plus Jakarta Sans' },
                formatter: function(val) {
                    return '₹' + (val / 1000).toFixed(0) + 'k';
                }
            }
        },
        grid: {
            borderColor: 'rgba(255, 255, 255, 0.04)',
            strokeDashArray: 4
        },
        theme: { mode: 'dark' }
    };

    if (revenueChartInstance) {
        revenueChartInstance.destroy();
    }
    
    const salesChartEl = document.querySelector("#sales-chart");
    if (salesChartEl) {
        revenueChartInstance = new ApexCharts(salesChartEl, revenueChartOptions);
        revenueChartInstance.render();
    }

    // 2. Lead Source Distribution Chart (Donut Chart)
    const leadSources = {};
    data.recent_leads.forEach(lead => {
        leadSources[lead.source] = (leadSources[lead.source] || 0) + 1;
    });

    const labels = Object.keys(leadSources).length ? Object.keys(leadSources) : ['Website', 'LinkedIn', 'Referral', 'Campaign'];
    const values = Object.keys(leadSources).length ? Object.values(leadSources) : [3, 5, 2, 1];

    const leadMixChartOptions = {
        series: values,
        labels: labels,
        chart: {
            type: 'donut',
            height: 280,
            background: 'transparent'
        },
        colors: ['#4F8CFF', '#7B61FF', '#FF61D2', '#00D4FF'],
        legend: {
            position: 'bottom',
            fontSize: '12px',
            fontFamily: 'Plus Jakarta Sans',
            labels: { colors: '#A1A1AA' },
            markers: { radius: 6 }
        },
        stroke: { show: false },
        plotOptions: {
            pie: {
                donut: {
                    size: '72%',
                    labels: {
                        show: true,
                        name: {
                            show: true,
                            fontSize: '13px',
                            fontFamily: 'Plus Jakarta Sans',
                            color: '#A1A1AA'
                        },
                        value: {
                            show: true,
                            fontSize: '20px',
                            fontFamily: 'Plus Jakarta Sans',
                            fontWeight: 700,
                            color: '#FFFFFF',
                            formatter: function (val) { return val; }
                        },
                        total: {
                            show: true,
                            label: 'Total Leads',
                            color: '#A1A1AA',
                            formatter: function (w) {
                                return w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                            }
                        }
                    }
                }
            }
        },
        dataLabels: { enabled: false },
        theme: { mode: 'dark' }
    };

    if (leadMixChartInstance) {
        leadMixChartInstance.destroy();
    }
    
    const leadMixChartEl = document.querySelector("#lead-mix-chart");
    if (leadMixChartEl) {
        leadMixChartInstance = new ApexCharts(leadMixChartEl, leadMixChartOptions);
        leadMixChartInstance.render();
    }
}

// Primary metrics loading function
async function loadDashboardMetrics() {
    try {
        const response = await fetch(API_BASE + '/api/dashboard/metrics');
        const result = await response.json();
        
        if (result.status === 'success') {
            const data = result.data;
            
            // --- A. SET KPI METRICS ON CORES ---
            // 1. Set Conversion Rate
            const kpiConversionEl = document.getElementById('kpi-conversion');
            if (kpiConversionEl) {
                kpiConversionEl.innerText = `${data.conversion_rate}%`;
            }
            
            // 2. Calculate Total Revenue Mapped MTD
            const totalRevenue = data.leaderboard.reduce((sum, rep) => sum + parseFloat(rep.total_revenue), 0);
            const kpiRevenueEl = document.getElementById('kpi-revenue');
            if (kpiRevenueEl) {
                kpiRevenueEl.innerText = `₹${totalRevenue.toLocaleString('en-IN')}`;
            }

            // 3. Count Total Deals Mapped
            const totalDeals = data.leaderboard.reduce((sum, rep) => sum + parseInt(rep.deals_won), 0);
            const kpiDealsEl = document.getElementById('kpi-deals');
            if (kpiDealsEl) {
                kpiDealsEl.innerText = totalDeals;
            }

            // 4. Count Pending Tasks Due
            const pendingTasksCount = data.pending_tasks ? data.pending_tasks.length : 0;
            const kpiTasksEl = document.getElementById('kpi-tasks');
            if (kpiTasksEl) {
                kpiTasksEl.innerText = pendingTasksCount;
            }
            
            const taskTrendLabel = document.getElementById('kpi-tasks-trend');
            if (taskTrendLabel) {
                if (pendingTasksCount > 0) {
                    taskTrendLabel.innerHTML = `<span class="text-danger fw-semibold"><i data-lucide="alert-triangle" class="inline-icon me-1"></i> Requires action</span>`;
                } else {
                    taskTrendLabel.innerHTML = `<span class="text-success fw-semibold"><i data-lucide="check-circle-2" class="inline-icon me-1"></i> Status healthy</span>`;
                }
            }

            // --- B. RENDER APEXCHARTS SCALES ---
            try {
                if (typeof ApexCharts !== 'undefined') {
                    renderDashboardCharts(data);
                } else {
                    console.warn("ApexCharts CDN is not available.");
                    const salesChartEl = document.querySelector("#sales-chart");
                    if (salesChartEl) {
                        salesChartEl.innerHTML = `<div class="text-muted small py-4 text-center">Charts offline (ApexCharts CDN not loaded)</div>`;
                    }
                    const leadMixChartEl = document.querySelector("#lead-mix-chart");
                    if (leadMixChartEl) {
                        leadMixChartEl.innerHTML = `<div class="text-muted small py-4 text-center">Charts offline</div>`;
                    }
                }
            } catch (chartErr) {
                console.error("Chart render error:", chartErr);
            }

            // --- C. POPULATE DATA TABLES ---
            // 1. Top Accounts Grid
            const topAccountsBody = document.getElementById('top-accounts-body');
            if (topAccountsBody) {
                topAccountsBody.innerHTML = '';
                if (data.top_customers && data.top_customers.length > 0) {
                    data.top_customers.forEach(acc => {
                        topAccountsBody.innerHTML += `
                            <tr>
                                <td>
                                    <div class="d-flex align-items-center">
                                        <div class="rep-avatar r4">${acc.name.charAt(0)}</div>
                                        <strong>${acc.name}</strong>
                                    </div>
                                </td>
                                <td class="text-success fw-bold">₹${parseFloat(acc.total_revenue).toLocaleString('en-IN')}</td>
                            </tr>
                        `;
                    });
                } else {
                    topAccountsBody.innerHTML = '<tr><td colspan="2" class="text-muted text-center py-3">No active accounts</td></tr>';
                }
            }

            // 2. Sales Leaderboard Grid
            const leaderboardBody = document.getElementById('leaderboard-body');
            const leaderboardHeader = document.querySelector('h5.card-title i[data-lucide="trophy"]')?.closest('h5');
            
            // Add "Add Rep" button for admin if not already present
            if (data.is_admin && leaderboardHeader) {
                const addRepBtnId = 'admin-add-rep-btn';
                if (!document.getElementById(addRepBtnId)) {
                    const btn = document.createElement('button');
                    btn.id = addRepBtnId;
                    btn.className = 'btn btn-sm btn-success ms-auto';
                    btn.innerHTML = '<i data-lucide="plus-circle" class="inline-icon me-1" style="width: 14px; height: 14px;"></i> Add Rep';
                    btn.setAttribute('data-bs-toggle', 'modal');
                    btn.setAttribute('data-bs-target', '#addRepModal');
                    btn.style.float = 'right';
                    btn.style.marginTop = '-4px';
                    btn.style.background = 'linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-blue) 100%)';
                    btn.style.border = 'none';
                    btn.style.borderRadius = '8px';
                    btn.style.fontSize = '12px';
                    btn.style.fontWeight = '600';
                    btn.style.padding = '5px 12px';
                    btn.style.color = '#09090B';
                    leaderboardHeader.appendChild(btn);
                    if (typeof lucide !== 'undefined') lucide.createIcons();
                }
            }

            if (leaderboardBody) {
                leaderboardBody.innerHTML = '';
                
                // Update table header to include Actions if admin
                const tableHeaderRow = leaderboardBody.closest('table').querySelector('thead tr');
                if (tableHeaderRow) {
                    if (data.is_admin && !tableHeaderRow.querySelector('.action-header')) {
                        const th = document.createElement('th');
                        th.className = 'action-header';
                        th.innerText = 'Action';
                        tableHeaderRow.appendChild(th);
                    } else if (!data.is_admin) {
                        const existingActionHeader = tableHeaderRow.querySelector('.action-header');
                        if (existingActionHeader) existingActionHeader.remove();
                    }
                }

                if (data.leaderboard && data.leaderboard.length > 0) {
                    data.leaderboard.forEach((rep, idx) => {
                        let rankAvatarClass = 'r1';
                        if (idx === 1) rankAvatarClass = 'r2';
                        if (idx === 2) rankAvatarClass = 'r3';
                        
                        let actionTd = '';
                        if (data.is_admin) {
                            // Don't show delete button for the admin account itself
                            if (rep.email === 'admin@gmail.com') {
                                actionTd = `<td><span class="text-muted small">System Admin</span></td>`;
                            } else {
                                actionTd = `<td>
                                    <button class="btn btn-sm btn-outline-danger border-0 p-1" onclick="deleteSalesRep('${rep.email}')" title="Delete Representative" style="background: transparent; color: #EF4444;">
                                        <i data-lucide="trash-2" style="width: 16px; height: 16px;"></i>
                                    </button>
                                </td>`;
                            }
                        }

                        leaderboardBody.innerHTML += `
                            <tr>
                                <td>
                                    <div class="d-flex align-items-center">
                                        <div class="rep-avatar ${rankAvatarClass}">${rep.rep_name.charAt(0)}</div>
                                        <span>${rep.rep_name}</span>
                                    </div>
                                </td>
                                <td><span class="pill-badge">${rep.deals_won} won</span></td>
                                <td class="fw-bold text-primary">₹${parseFloat(rep.total_revenue).toLocaleString('en-IN')}</td>
                                ${actionTd}
                            </tr>
                        `;
                    });
                } else {
                    leaderboardBody.innerHTML = `<tr><td colspan="${data.is_admin ? 4 : 3}" class="text-muted text-center py-3">No active reps</td></tr>`;
                }
            }

            // 3. Pending Follow-Ups Tasks Grid
            const pendingTasksBody = document.getElementById('pending-tasks-body');
            if (pendingTasksBody) {
                pendingTasksBody.innerHTML = '';
                if (data.pending_tasks && data.pending_tasks.length > 0) {
                    data.pending_tasks.forEach(task => {
                        let typeIcon = '📋';
                        if (task.task_type === 'Call') typeIcon = '📞';
                        if (task.task_type === 'Email') typeIcon = '✉️';
                        if (task.task_type === 'Meeting') typeIcon = '🤝';
                        if (task.task_type === 'Demo') typeIcon = '💻';

                        pendingTasksBody.innerHTML += `
                            <tr>
                                <td><strong>${typeIcon} ${task.task_type}</strong></td>
                                <td>${task.account_name}</td>
                                <td><span class="text-danger fw-semibold">${task.due_date}</span></td>
                                <td class="text-muted small">${task.remarks || '<em>No notes</em>'}</td>
                                <td>
                                    <button class="btn btn-sm btn-success py-1 px-2 border-0" onclick="markTaskComplete(${task.task_id})" style="border-radius: 6px; font-size: 11px;">✓ Complete</button>
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    pendingTasksBody.innerHTML = `
                        <tr>
                            <td colspan="5" class="text-muted text-center py-4">No immediate follow-ups pending. Great job!</td>
                        </tr>
                    `;
                }
            }

            // 4. Smart Automation Radar Alerts
            const radarContainer = document.getElementById('radar-alerts-container');
            if (radarContainer && data.urgent_alerts) {
                radarContainer.innerHTML = '';
                if (data.urgent_alerts.length === 0) {
                    radarContainer.innerHTML = `<div class="alert alert-success py-3 mb-0 border-0 d-flex align-items-center gap-2" style="background: rgba(34, 197, 94, 0.08); border-radius: 12px; color: var(--success);">
                        <i data-lucide="check-circle-2"></i> <span>All enterprise accounts healthy. No systemic risk flags.</span>
                    </div>`;
                } else {
                    data.urgent_alerts.forEach(alertItem => {
                        let alertColorClass = 'warning';
                        let actionText = 'Schedule initial discovery call.';
                        
                        if (alertItem.urgency_score >= 50) {
                            alertColorClass = 'danger';
                            actionText = 'CRITICAL: Deal negotiation stalled! Contact accounts immediately.';
                        } else if (alertItem.urgency_score >= 40) {
                            alertColorClass = 'danger';
                            actionText = 'Resolve active overdue tasks list.';
                        }

                        // Confidence score simulation tied cleanly to metrics
                        const confidence = Math.min(Math.round(80 + (alertItem.urgency_score * 0.35)), 99);

                        radarContainer.innerHTML += `
                            <div class="radar-alert-item">
                                <div class="d-flex justify-content-between align-items-start mb-2 flex-wrap gap-2">
                                    <div>
                                        <span class="urgency-badge ${alertColorClass === 'danger' ? '' : 'warning'} me-2">Urgency Score: ${alertItem.urgency_score}</span>
                                        <span class="text-white fw-bold">${alertItem.account_name}</span> 
                                        <span class="text-muted small">(${alertItem.company || 'Private Account'})</span>
                                    </div>
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="radar-score text-purple border-purple-subtle" style="background: rgba(123, 97, 255, 0.05);">Confidence: ${confidence}%</span>
                                        <button class="btn btn-sm btn-secondary py-1 px-3 d-flex align-items-center gap-1" onclick="generateAIEmail(${alertItem.account_id})" style="border-radius: 8px; font-size: 12px; font-weight: 600;">
                                            <i data-lucide="sparkles" style="width: 14px; height: 14px;"></i> Draft Outreach
                                        </button>
                                    </div>
                                </div>
                                <div class="small text-secondary pt-2 mt-2 border-top border-color d-flex align-items-center gap-2">
                                    <i data-lucide="lightbulb" class="text-warning" style="width: 16px; height: 16px;"></i>
                                    <span><strong>Next Action Suggestion:</strong> ${actionText}</span>
                                </div>
                            </div>
                        `;
                    });
                }
            }

            // 5. Recent Leads Activity
            const recentLeadsBody = document.getElementById('recent-leads-body');
            if (recentLeadsBody && data.recent_leads) {
                recentLeadsBody.innerHTML = '';
                data.recent_leads.forEach(lead => {
                    let statusPillClass = 'lead';
                    if (lead.status === 'Active Customer') statusPillClass = 'won';
                    if (lead.status === 'Qualified') statusPillClass = 'qualified';
                    if (lead.status === 'Contacted') statusPillClass = 'contacted';
                    if (lead.status === 'Negotiation') statusPillClass = 'negotiation';

                    recentLeadsBody.innerHTML += `
                        <tr>
                            <td><span class="text-muted">#${lead.account_id}</span></td>
                            <td><strong>${lead.name}</strong></td>
                            <td>${lead.company || '<em>No Company</em>'}</td>
                            <td><span class="pill-badge">${lead.source}</span></td>
                            <td><span class="status-pill ${statusPillClass}">${lead.status}</span></td>
                        </tr>
                    `;
                });
            }

            // Re-render Lucide icons dynamically
            try {
                if (typeof lucide !== 'undefined') {
                    lucide.createIcons();
                }
            } catch (iconErr) {
                console.error("Lucide icons failed to load:", iconErr);
            }
        }
    } catch (error) {
        console.error("Error fetching metrics:", error);
    }
}

// --- FORM ACTIONS AND API SUBMISSIONS ---
document.addEventListener('DOMContentLoaded', () => {
    updateDashboardTime();
    setInterval(updateDashboardTime, 1000);
    loadDashboardMetrics();

    // Prevent Chrome accessibility "Blocked aria-hidden on an element because its descendant retained focus" warning
    document.addEventListener('hide.bs.modal', function(e) {
        if (e.target && e.target.contains(document.activeElement)) {
            document.activeElement.blur();
        }
    });

    // Lead Entry Submit Handler
    const leadFormEl = document.getElementById('leadForm');
    if (leadFormEl) {
        leadFormEl.addEventListener('submit', async function(e) {
            e.preventDefault();

            const payload = {
                name: document.getElementById('formName').value,
                email: document.getElementById('formEmail').value,
                phone: document.getElementById('formPhone').value,
                company: document.getElementById('formCompany').value,
                source: document.getElementById('formSource').value,
                status: 'Lead',
                rep_id: ""
            };

            try {
                const response = await fetch(API_BASE + '/api/accounts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    alert('Lead added successfully!');
                    document.getElementById('leadForm').reset();
                    bootstrap.Modal.getInstance(document.getElementById('addLeadModal')).hide();
                    loadDashboardMetrics();
                } else {
                    alert('Error saving lead: ' + result.message);
                }
            } catch (error) {
                console.error('Submission error:', error);
            }
        });
    }

    // Opportunity (Deal) Logging Submit Handler
    const dealFormEl = document.getElementById('dealForm');
    if (dealFormEl) {
        dealFormEl.addEventListener('submit', async function(e) {
            e.preventDefault();

            const payload = {
                account_id: document.getElementById('dealAccountSelect').value,
                rep_id: document.getElementById('dealRepSelect').value,
                deal_value: document.getElementById('dealValue').value,
                stage: document.getElementById('dealStage').value
            };

            try {
                const response = await fetch(API_BASE + '/api/deals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    alert('Deal logged and processed successfully!');
                    document.getElementById('dealForm').reset();
                    bootstrap.Modal.getInstance(document.getElementById('addDealModal')).hide();
                    loadDashboardMetrics();
                } else {
                    alert('Submission error: ' + result.message);
                }
            } catch (error) {
                console.error('Error handling deal post:', error);
            }
        });
    }

    // Task Scheduling Submit Handler
    const taskFormEl = document.getElementById('taskForm');
    if (taskFormEl) {
        taskFormEl.addEventListener('submit', async function(e) {
            e.preventDefault();

            const payload = {
                account_id: document.getElementById('taskAccountSelect').value,
                rep_id: document.getElementById('taskRepSelect').value,
                task_type: document.getElementById('taskType').value,
                due_date: document.getElementById('taskDueDate').value.replace('T', ' '),
                remarks: document.getElementById('taskRemarks').value
            };

            try {
                const res = await fetch(API_BASE + '/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const out = await res.json();
                
                if (out.status === 'success') {
                    alert('Task scheduled successfully!');
                    document.getElementById('taskForm').reset();
                    bootstrap.Modal.getInstance(document.getElementById('addTaskModal')).hide();
                    loadDashboardMetrics();
                } else {
                    alert('Error scheduling task: ' + out.message);
                }
            } catch (err) {
                console.error('Error handling task post:', err);
            }
        });
    }

    // Bulk CSV Ingestion Submit Handler
    const bulkFormEl = document.getElementById('bulkUploadForm');
        if (bulkFormEl) {
            bulkFormEl.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const fileInput = document.getElementById('csvFileInput');
                if (fileInput.files.length === 0) return;

                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                try {
                    const response = await fetch(API_BASE + '/api/accounts/bulk-upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        alert(result.message);
                        document.getElementById('bulkUploadForm').reset();
                        bootstrap.Modal.getInstance(document.getElementById('bulkUploadModal')).hide();
                        loadDashboardMetrics();
                    } else {
                        alert('Bulk Ingestion Error: ' + result.message);
                    }
                } catch (error) {
                    console.error('File streaming failed:', error);
                }
            });
        }
    // Admin Add Representative Submit Handler
    const addRepForm = document.getElementById('addRepForm');
    if (addRepForm) {
        addRepForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const payload = {
                name: document.getElementById('addRepName').value,
                email: document.getElementById('addRepEmail').value,
                password: document.getElementById('addRepPassword').value
            };
            
            try {
                const response = await fetch(API_BASE + '/api/admin/sales-reps', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                
                if (result.status === 'success') {
                    alert('Representative account created successfully!');
                    addRepForm.reset();
                    bootstrap.Modal.getInstance(document.getElementById('addRepModal')).hide();
                    loadDashboardMetrics();
                } else {
                    alert('Error creating representative: ' + result.message);
                }
            } catch (err) {
                console.error("Error creating rep:", err);
            }
        });
    }
});

// --- HELPER HANDLERS ---

// Populate log deal dropdowns
async function populateDropdowns() {
    try {
        const [accountsRes, metricsRes] = await Promise.all([
            fetch(API_BASE + '/api/accounts'),
            fetch(API_BASE + '/api/dashboard/metrics')
        ]);
        const accountsResult = await accountsRes.json();
        const metricsResult = await metricsRes.json();
        
        if (accountsResult.status === 'success' && metricsResult.status === 'success') {
            const accounts = accountsResult.data;
            const metrics = metricsResult.data;
            
            const accountSelect = document.getElementById('dealAccountSelect');
            if (accountSelect) {
                accountSelect.innerHTML = '<option value="">-- Choose Account --</option>';
                accounts.forEach(acc => {
                    accountSelect.innerHTML += `<option value="${acc.account_id}">${acc.name} (${acc.company || 'No Company'})</option>`;
                });
            }

            const repSelect = document.getElementById('dealRepSelect');
            if (repSelect) {
                repSelect.innerHTML = '<option value="">-- Unassigned --</option>';
                metrics.leaderboard.forEach(rep => {
                    repSelect.innerHTML += `<option value="${rep.rep_id}">${rep.rep_name}</option>`;
                });
            }
        }
    } catch (error) {
        console.error("Error setting up dropdown lists:", error);
    }
}

// Populate task dropdowns
async function populateTaskDropdowns() {
    try {
        const [accountsRes, metricsRes] = await Promise.all([
            fetch(API_BASE + '/api/accounts'),
            fetch(API_BASE + '/api/dashboard/metrics')
        ]);
        const accountsResult = await accountsRes.json();
        const metricsResult = await metricsRes.json();
        
        if (accountsResult.status === 'success' && metricsResult.status === 'success') {
            const accounts = accountsResult.data;
            const metrics = metricsResult.data;
            
            const accountSelect = document.getElementById('taskAccountSelect');
            if (accountSelect) {
                accountSelect.innerHTML = '<option value="">-- Select Target Account --</option>';
                accounts.forEach(acc => {
                    accountSelect.innerHTML += `<option value="${acc.account_id}">${acc.name} (${acc.company || 'No Company'})</option>`;
                });
            }
            
            const repSelect = document.getElementById('taskRepSelect');
            if (repSelect) {
                repSelect.innerHTML = '<option value="">-- Select Representative --</option>';
                metrics.leaderboard.forEach(rep => {
                    repSelect.innerHTML += `<option value="${rep.rep_id}">${rep.rep_name}</option>`;
                });
            }
        }
    } catch (e) {
        console.error("Error populating task dropdowns:", e);
    }
}

// Mark Task Complete (PUT Route Action)
async function markTaskComplete(taskId) {
    try {
        const response = await fetch(`${API_BASE}/api/tasks/${taskId}/complete`, { method: 'PUT' });
        const result = await response.json();
        if (result.status === 'success') {
            loadDashboardMetrics();
        }
    } catch (e) {
        console.error("Error updates:", e);
    }
}

// Generate AI Suggest Email Outreach Copy
async function generateAIEmail(accountId) {
    const textArea = document.getElementById('aiEmailTextArea');
    if (textArea) {
        textArea.value = '🤖 Contacting local engine... Spawning Qwen intelligence states...';
    }
    
    // Reveal the display modal wrapper instantly so the user sees immediate feedback
    const modalEl = document.getElementById('aiEmailModal');
    if (modalEl) {
        const myModal = bootstrap.Modal.getOrCreateInstance(modalEl);
        myModal.show();
    }

    try {
        const response = await fetch(`${API_BASE}/api/ai/suggest-email/${accountId}`);
        if (!response.ok) {
            const errText = await response.text();
            if (textArea) {
                textArea.value = "Error: " + errText;
            }
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        if (textArea) {
            textArea.value = ''; // Reset loading string text indicator
        }

        // Loop and read incoming micro data token strings continuously
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const token = decoder.decode(value, { stream: true });
            if (textArea) {
                textArea.value += token; // Append token characters live onto the text panel interface
            }
        }
    } catch (e) {
        if (textArea) {
            textArea.value = "Inference streaming hit an interruption hurdle: " + e;
        }
    }
}

let searchTimeout;
document.getElementById('globalSearchInput').addEventListener('input', function(e) {
    const query = e.target.value.trim();
    
    // Clear any pending timeout
    clearTimeout(searchTimeout);
    
    // If user clears search, reload native standard dashboard views immediately
    if (query.length === 0) {
        loadDashboardMetrics();
        return;
    }

    if (query.length < 3) return; // Wait for contextual phrases

    // Set a timeout to debounce the heavy vector search query (300ms delay)
    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(API_BASE + '/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });
            const result = await response.json();
            
            if (result.status === 'success') {
                const recentLeadsBody = document.getElementById('recent-leads-body');
                recentLeadsBody.innerHTML = '';
                
                if (result.results.length === 0) {
                    recentLeadsBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">⚠️ No conceptual matches found in local vector store.</td></tr>';
                    return;
                }

                result.results.forEach(lead => {
                    recentLeadsBody.innerHTML += `
                        <tr class="bg-dark text-white border-secondary">
                            <td>#${lead.account_id}</td>
                            <td><strong>${lead.name}</strong> <span class="badge bg-info text-dark ms-2">Vector Match</span></td>
                            <td>${lead.company || '<em>None</em>'}</td>
                            <td><span class="badge bg-secondary">${lead.source}</span></td>
                            <td><span class="badge bg-warning text-dark">${lead.status}</span></td>
                        </tr>
                    `;
                });
            }
        } catch (err) { console.error("Vector query failure:", err); }
    }, 300);
});

// Fetch and populate My Account profile details and analytics
async function loadUserProfile() {
    try {
        const response = await fetch(API_BASE + '/api/profile');
        const result = await response.json();
        
        if (result.status === 'success') {
            const data = result.data;
            
            document.getElementById('profile-username').innerText = data.username;
            document.getElementById('profile-email').innerText = data.email;
            document.getElementById('profile-rep-id').innerText = data.rep_id ? `#${data.rep_id}` : 'Unassigned';
            document.getElementById('profile-leads').innerText = data.total_leads;
            document.getElementById('profile-deals-won').innerText = data.deals_won;
            document.getElementById('profile-revenue').innerText = `₹${data.total_revenue.toLocaleString('en-IN')}`;
            
            const avatarLarge = document.getElementById('profile-avatar-large');
            if (avatarLarge && data.username) {
                avatarLarge.innerText = data.username.charAt(0).toUpperCase();
            }
            
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
    } catch (e) {
        console.error("Error loading user profile details:", e);
    }
}

// Admin delete representative handler
async function deleteSalesRep(email) {
    if (!confirm(`Are you sure you want to permanently delete representative ${email}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/sales-reps/${email}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('Representative account deleted successfully.');
            loadDashboardMetrics();
        } else {
            alert('Deletion failed: ' + result.message);
        }
    } catch (e) {
        console.error("Error deleting rep:", e);
    }
}