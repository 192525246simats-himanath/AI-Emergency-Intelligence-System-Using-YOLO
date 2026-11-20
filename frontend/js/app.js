/**
 * EOCC Command Center Master Application Logic.
 * Handles telemetry synchronization, surveillance streams, incident workflows,
 * toast notifications, and custom operator confirmation dialogs.
 * Author: Himanath Sai & Capstone Team (Saveetha University)
 */

const App = (function () {
    let currentView = "view-overview";
    let isStreamActive = true;
    let currentCameraIndex = 0;
    let alertsFilter = "ALL";
    let incidentsCache = [];
    let statsCache = {};
    let telemetryInterval = null;
    let activeConfirmCallback = null;

    // =========================================================================
    // Core Initialization
    // =========================================================================
    function init() {
        initNavigation();
        initClock();
        initSidebarToggle();
        initNotificationDrawer();
        initSettingsHandlers();
        initUploadDropzone();
        initSurveillanceStream();
        initHistoryFilters();

        // Initial Data Fetch
        refreshAllData();

        // Check for URL hash navigation
        if (window.location.hash) {
            const hashView = window.location.hash.replace("#", "");
            if (document.getElementById(hashView)) {
                navigateTo(hashView);
            }
        }

        // Periodic Background Synchronization (Every 8 seconds)
        telemetryInterval = setInterval(() => {
            fetchStats();
            if (currentView === "view-overview" || currentView === "view-alerts" || currentView === "view-history") {
                fetchIncidents();
            }
        }, 8000);
    }

    // =========================================================================
    // Navigation & Routing
    // =========================================================================
    function initNavigation() {
        const navItems = document.querySelectorAll(".nav-item");
        navItems.forEach(item => {
            item.addEventListener("click", function (e) {
                e.preventDefault();
                const target = this.getAttribute("data-target");
                if (target) navigateTo(target);
            });
        });
    }

    function navigateTo(viewId) {
        currentView = viewId;

        // Update nav items active state
        document.querySelectorAll(".nav-item").forEach(item => {
            if (item.getAttribute("data-target") === viewId) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        // Switch visible view section
        document.querySelectorAll(".view-section").forEach(sec => {
            sec.classList.remove("active");
        });
        const activeSection = document.getElementById(viewId);
        if (activeSection) activeSection.classList.add("active");

        // Update Header Titles
        const titles = {
            "view-overview": ["Overview Dashboard", "Emergency Operations Command Center • Surveillance Zone Sector 1"],
            "view-live": ["Live Video Surveillance", "High-Definition Real-Time Optical Ingestion & YOLO Telemetry"],
            "view-upload": ["Footage & Imagery Analysis", "Batch Surveillance Upload, Multi-Class Inference & Risk Assessment"],
            "view-vehicles": ["Vehicle Detection Architecture", "COCO Multi-Class Neural Network Classification Specifications"],
            "view-analysis": ["Accident & Collision Analysis", "Spatial IoU Overlap & Centroid Proximity Heuristics"],
            "view-alerts": ["Emergency Incident Dispatch", "Active Hazard Prioritization, Operator Verification & Simulated Response"],
            "view-history": ["Incident Management History", "Comprehensive Audit Trail & Historical Incident Records"],
            "view-about": ["About EOCC System", "Senior Capstone Project Specifications • Saveetha University"],
            "view-settings": ["System Settings", "Render Backend API & Network Infrastructure Configuration"]
        };

        const pageTitle = document.getElementById("page-title");
        const pageSub = document.getElementById("page-subtitle");
        if (titles[viewId]) {
            if (pageTitle) pageTitle.textContent = titles[viewId][0];
            if (pageSub) pageSub.textContent = titles[viewId][1];
        }

        // Close sidebar on mobile upon navigation
        if (window.innerWidth <= 768) {
            const sidebar = document.getElementById("app-sidebar");
            if (sidebar) sidebar.classList.remove("open");
        }

        // Trigger view-specific refreshes
        if (viewId === "view-alerts") renderAlertsList();
        if (viewId === "view-history") renderHistoryTable();
        if (viewId === "view-settings") {
            const setInput = document.getElementById("page-settings-backend-url");
            if (setInput) setInput.value = ApiService.getBackendUrl();
        }
    }

    function initSidebarToggle() {
        const toggleBtn = document.getElementById("sidebar-toggle-btn");
        const sidebar = document.getElementById("app-sidebar");

        if (toggleBtn && sidebar) {
            toggleBtn.addEventListener("click", () => {
                sidebar.classList.toggle("open");
            });

            document.addEventListener("click", (e) => {
                if (window.innerWidth <= 768 && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                    sidebar.classList.remove("open");
                }
            });
        }
    }

    // =========================================================================
    // Live Telemetry Clock
    // =========================================================================
    function initClock() {
        const clockDisplay = document.getElementById("clock-display");
        function update() {
            if (clockDisplay) {
                const now = new Date();
                clockDisplay.textContent = now.toUTCString().slice(17, 25) + " UTC";
            }
        }
        update();
        setInterval(update, 1000);
    }

    // =========================================================================
    // Toast Notification System
    // =========================================================================
    function showToast(message, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = `toast-msg toast-${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠️',
            info: 'ℹ️'
        };

        toast.innerHTML = `
            <span style="font-size: 1rem; font-weight: 800;">${icons[type] || 'ℹ️'}</span>
            <span style="flex: 1; line-height: 1.3;">${escapeHtml(message)}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(20px)";
            toast.style.transition = "all 0.25s ease";
            setTimeout(() => toast.remove(), 250);
        }, 3500);
    }

    // =========================================================================
    // Custom Confirmation Dialog System
    // =========================================================================
    function openConfirmModal(config) {
        const modal = document.getElementById("confirm-modal");
        const titleEl = document.getElementById("confirm-modal-title");
        const msgEl = document.getElementById("confirm-modal-msg");
        const btn = document.getElementById("confirm-modal-btn");

        if (!modal) return;

        titleEl.textContent = config.title || "Confirm Action";
        msgEl.textContent = config.message || "Are you sure you wish to proceed?";
        btn.textContent = config.btnText || "Confirm";
        btn.className = `btn ${config.btnClass || 'btn-danger'}`;

        activeConfirmCallback = config.onConfirm;
        modal.classList.add("active");

        btn.onclick = () => {
            closeConfirmModal();
            if (activeConfirmCallback) activeConfirmCallback();
        };
    }

    function closeConfirmModal() {
        const modal = document.getElementById("confirm-modal");
        if (modal) modal.classList.remove("active");
        activeConfirmCallback = null;
    }

    // =========================================================================
    // Notification Drawer
    // =========================================================================
    function initNotificationDrawer() {
        const btn = document.getElementById("btn-notifications-drawer");
        const drawer = document.getElementById("notification-drawer");

        if (btn && drawer) {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                drawer.classList.toggle("active");
            });

            document.addEventListener("click", (e) => {
                if (!drawer.contains(e.target) && !btn.contains(e.target)) {
                    drawer.classList.remove("active");
                }
            });
        }
    }

    function updateNotificationDrawer() {
        const list = document.getElementById("drawer-notifications-list");
        const dot = document.getElementById("header-notif-dot");
        if (!list) return;

        const activeAlerts = incidentsCache.filter(i => i.status === "ACTIVE");

        if (dot) {
            dot.style.display = activeAlerts.length > 0 ? "block" : "none";
        }

        if (activeAlerts.length === 0) {
            list.innerHTML = `<p style="color: var(--text-muted); font-size: 0.78rem; text-align: center; padding: 1rem;">No unread critical alerts.</p>`;
            return;
        }

        list.innerHTML = activeAlerts.slice(0, 5).map(i => `
            <div class="notif-item ${i.risk_level === 'HIGH' ? 'high' : 'med'}" onclick="App.openIncidentDetail(${i.id}); document.getElementById('notification-drawer').classList.remove('active');" style="cursor: pointer;">
                <div style="display: flex; justify-content: space-between; font-weight: 700;">
                    <span>#${i.id} ${escapeHtml(i.incident_type)}</span>
                    <span class="badge ${i.risk_level === 'HIGH' ? 'badge-high' : 'badge-medium'}">${i.risk_level}</span>
                </div>
                <div style="color: var(--text-muted); font-size: 0.72rem;">${formatTimestamp(i.timestamp)}</div>
            </div>
        `).join("");
    }

    // =========================================================================
    // Settings Handlers
    // =========================================================================
    function initSettingsHandlers() {
        const quickBtn = document.getElementById("btn-quick-settings");
        const quickModal = document.getElementById("settings-modal");
        const quickInput = document.getElementById("settings-backend-url");
        const quickSave = document.getElementById("btn-save-backend-url");
        const quickTest = document.getElementById("btn-test-backend-conn");

        if (quickBtn && quickModal) {
            quickBtn.addEventListener("click", () => {
                quickInput.value = ApiService.getBackendUrl();
                const resBox = document.getElementById("settings-test-result");
                if (resBox) resBox.style.display = "none";
                quickModal.classList.add("active");
            });
        }

        if (quickSave) {
            quickSave.addEventListener("click", () => {
                const val = quickInput.value.trim();
                ApiService.setBackendUrl(val);
                closeSettingsModal();
                showToast("Backend API URL updated successfully", "success");
                refreshAllData();
                initSurveillanceStream();
            });
        }

        if (quickTest) {
            quickTest.addEventListener("click", async () => {
                const val = quickInput.value.trim() || ApiService.getBackendUrl();
                const resBox = document.getElementById("settings-test-result");
                resBox.style.display = "block";
                resBox.textContent = "Connecting to " + val + "...";
                resBox.style.color = "var(--text-secondary)";

                try {
                    const { data, latency } = await ApiService.testLatency(val);
                    resBox.style.color = "var(--risk-low)";
                    resBox.textContent = `Connected! ${data.service} (YOLOv8: ${data.yolo_model}) • Latency: ${latency}ms`;
                } catch (err) {
                    resBox.style.color = "var(--risk-high)";
                    resBox.textContent = "Connection failed: " + err.message;
                }
            });
        }

        // Full Settings Page Handlers
        const pageInput = document.getElementById("page-settings-backend-url");
        const pageSave = document.getElementById("btn-page-save-url");
        const pageTest = document.getElementById("btn-page-test-conn");
        const pageReset = document.getElementById("btn-page-reset-url");
        const pageStatus = document.getElementById("page-settings-status");

        if (pageInput) pageInput.value = ApiService.getBackendUrl();

        if (pageSave) {
            pageSave.addEventListener("click", () => {
                const val = pageInput.value.trim();
                ApiService.setBackendUrl(val);
                showToast("Backend URL saved to localStorage", "success");
                refreshAllData();
                initSurveillanceStream();
            });
        }

        if (pageReset) {
            pageReset.addEventListener("click", () => {
                ApiService.setBackendUrl("http://localhost:5000");
                pageInput.value = "http://localhost:5000";
                showToast("Reset to default localhost:5000", "info");
                refreshAllData();
                initSurveillanceStream();
            });
        }

        if (pageTest) {
            pageTest.addEventListener("click", async () => {
                const val = pageInput.value.trim() || ApiService.getBackendUrl();
                pageStatus.style.display = "block";
                pageStatus.textContent = "Connecting to " + val + "...";
                pageStatus.style.background = "var(--bg-card)";
                pageStatus.style.color = "var(--text-secondary)";

                try {
                    const { data, latency } = await ApiService.testLatency(val);
                    pageStatus.style.background = "rgba(16, 185, 129, 0.1)";
                    pageStatus.style.color = "var(--risk-low)";
                    pageStatus.textContent = `Verified! Connected to ${data.service} (Model: ${data.yolo_model}) • Round-trip Latency: ${latency}ms`;
                } catch (err) {
                    pageStatus.style.background = "rgba(239, 68, 68, 0.1)";
                    pageStatus.style.color = "var(--risk-high)";
                    pageStatus.textContent = `Failed to connect: ${err.message}. Ensure backend is running.`;
                }
            });
        }

        // Manual Alert Modal Submit
        const submitManualBtn = document.getElementById("btn-submit-manual-alert");
        if (submitManualBtn) {
            submitManualBtn.addEventListener("click", async () => {
                const type = document.getElementById("manual-type").value.trim();
                const risk = document.getElementById("manual-risk").value;
                const loc = document.getElementById("manual-location").value.trim();
                const desc = document.getElementById("manual-desc").value.trim();

                try {
                    submitManualBtn.disabled = true;
                    submitManualBtn.textContent = "Logging...";
                    await ApiService.createManualAlert({
                        incident_type: type,
                        risk_level: risk,
                        location_tag: loc,
                        description: desc,
                        objects_involved: ["operator_alert"]
                    });
                    closeManualAlertModal();
                    showToast("Manual operator alert logged into database", "success");
                    refreshAllData();
                } catch (err) {
                    showToast("Failed to log alert: " + err.message, "error");
                } finally {
                    submitManualBtn.disabled = false;
                    submitManualBtn.textContent = "Log Alert";
                }
            });
        }
    }

    function closeSettingsModal() {
        const modal = document.getElementById("settings-modal");
        if (modal) modal.classList.remove("active");
    }

    function openManualAlertModal() {
        const modal = document.getElementById("manual-alert-modal");
        if (modal) modal.classList.add("active");
    }

    function closeManualAlertModal() {
        const modal = document.getElementById("manual-alert-modal");
        if (modal) modal.classList.remove("active");
    }

    function closeIncidentModal() {
        const modal = document.getElementById("incident-detail-modal");
        if (modal) modal.classList.remove("active");
    }

    // =========================================================================
    // Telemetry & Statistics Polling
    // =========================================================================
    async function refreshAllData() {
        await checkBackendHealth();
        await fetchStats();
        await fetchIncidents();
    }

    async function checkBackendHealth() {
        const pill = document.getElementById("backend-status-pill");
        const text = document.getElementById("backend-status-text");
        const sysVal = document.getElementById("kpi-sys-status");
        const sysSub = document.getElementById("kpi-sys-sub");

        try {
            const { data, latency } = await ApiService.testLatency();
            if (pill && text) {
                pill.classList.remove("offline");
                text.textContent = `Backend Online (${latency}ms)`;
            }
            if (sysVal) sysVal.textContent = "OPERATIONAL";
            if (sysSub) sysSub.textContent = `Model: ${data.yolo_model} • Latency: ${latency}ms`;
        } catch (err) {
            if (pill && text) {
                pill.classList.add("offline");
                text.textContent = "Backend Offline";
            }
            if (sysVal) sysVal.textContent = "DISCONNECTED";
            if (sysSub) sysSub.textContent = "Click Settings to set Render URL";
        }
    }

    async function fetchStats() {
        try {
            const stats = await ApiService.getStats();
            statsCache = stats;

            // Compute dynamic total vehicles estimated from incident events
            const vehiclesEstimated = Math.max(
                stats.total_incidents * 3 + (stats.high_risk * 2),
                stats.total_incidents > 0 ? stats.total_incidents * 2 : 14
            );

            const vEl = document.getElementById("kpi-total-vehicles");
            const iEl = document.getElementById("kpi-total-incidents");
            const hEl = document.getElementById("kpi-high-risk");
            const mEl = document.getElementById("kpi-med-risk");
            const rEl = document.getElementById("kpi-resolved");

            if (vEl) vEl.textContent = vehiclesEstimated;
            if (iEl) iEl.textContent = stats.total_incidents ?? 0;
            if (hEl) hEl.textContent = stats.high_risk ?? 0;
            if (mEl) mEl.textContent = stats.medium_risk ?? 0;

            const resolved = Math.max(0, (stats.total_incidents || 0) - (stats.active_incidents || 0));
            if (rEl) rEl.textContent = resolved;

            // Sidebar Badge
            const sbBadge = document.getElementById("sidebar-alert-badge");
            if (sbBadge) {
                sbBadge.textContent = stats.active_incidents ?? 0;
                sbBadge.style.display = stats.active_incidents > 0 ? "inline-block" : "none";
            }

            // Risk Distribution Breakdown
            const total = stats.total_incidents || 1;
            const hPct = Math.round(((stats.high_risk || 0) / total) * 100);
            const mPct = Math.round(((stats.medium_risk || 0) / total) * 100);
            const lPct = Math.max(0, 100 - hPct - mPct);

            const barH = document.getElementById("bar-dist-high");
            const barM = document.getElementById("bar-dist-med");
            const barL = document.getElementById("bar-dist-low");

            if (barH) barH.style.width = `${hPct}%`;
            if (barM) barM.style.width = `${mPct}%`;
            if (barL) barL.style.width = `${lPct}%`;

            const txtH = document.getElementById("dist-high-pct");
            const txtM = document.getElementById("dist-med-pct");
            const txtL = document.getElementById("dist-low-pct");

            if (txtH) txtH.textContent = `${hPct}%`;
            if (txtM) txtM.textContent = `${mPct}%`;
            if (txtL) txtL.textContent = `${lPct}%`;

        } catch (err) {
            console.warn("Could not synchronize telemetry stats:", err.message);
        }
    }

    async function fetchIncidents() {
        try {
            const res = await ApiService.getIncidents({ limit: 100 });
            incidentsCache = res.incidents || [];
            renderOverviewTable();
            renderAlertsList();
            renderHistoryTable();
            updateNotificationDrawer();
        } catch (err) {
            console.warn("Could not fetch incident list:", err.message);
        }
    }

    // =========================================================================
    // Table & Card Renderers
    // =========================================================================
    function getRiskBadge(level) {
        const l = (level || "LOW").toUpperCase();
        if (l === "HIGH") return '<span class="badge badge-high">HIGH RISK</span>';
        if (l === "MEDIUM") return '<span class="badge badge-medium">MEDIUM RISK</span>';
        return '<span class="badge badge-low">LOW RISK</span>';
    }

    function getStatusBadge(status) {
        const s = (status || "ACTIVE").toUpperCase();
        if (s === "ACTIVE") return '<span class="badge badge-active">ACTIVE</span>';
        if (s === "ACKNOWLEDGED") return '<span class="badge badge-acknowledged">ACKNOWLEDGED</span>';
        return '<span class="badge badge-resolved">RESOLVED</span>';
    }

    function renderOverviewTable() {
        const tbody = document.getElementById("overview-incidents-tbody");
        if (!tbody) return;

        if (incidentsCache.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
                        No incidents logged. All surveillance sectors operating under normal flow.
                    </td>
                </tr>
            `;
            return;
        }

        const recent = incidentsCache.slice(0, 5);
        tbody.innerHTML = recent.map(inc => `
            <tr>
                <td><strong>#${inc.id}</strong></td>
                <td>${formatTimestamp(inc.timestamp)}</td>
                <td>${escapeHtml(inc.location_tag || 'Highway Sector 1')}</td>
                <td>${escapeHtml(inc.incident_type)}</td>
                <td>${getRiskBadge(inc.risk_level)}</td>
                <td>${Math.round((inc.confidence || 0) * 100)}%</td>
                <td>${getStatusBadge(inc.status)}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="App.openIncidentDetail(${inc.id})">Inspect</button>
                </td>
            </tr>
        `).join("");
    }

    function renderAlertsList() {
        const container = document.getElementById("alerts-card-list");
        if (!container) return;

        let filtered = incidentsCache;
        if (alertsFilter !== "ALL") {
            filtered = incidentsCache.filter(inc => inc.risk_level === alertsFilter);
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); padding: 3rem; background: var(--bg-card); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">✅</div>
                    <p>No ${alertsFilter === 'ALL' ? '' : alertsFilter} emergency alerts found. All road sectors operating normally.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(inc => `
            <div class="kpi-card ${inc.risk_level === 'HIGH' ? 'risk-high' : (inc.risk_level === 'MEDIUM' ? 'risk-med' : 'risk-low')}" style="padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.75rem;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem; flex-wrap: wrap;">
                            <strong>Incident #${inc.id}</strong>
                            ${getRiskBadge(inc.risk_level)}
                            ${getStatusBadge(inc.status)}
                            <span style="font-size: 0.75rem; color: var(--text-muted); font-family: ui-monospace, monospace;">${formatTimestamp(inc.timestamp)}</span>
                        </div>
                        <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.35rem;">
                            ${escapeHtml(inc.incident_type)} @ ${escapeHtml(inc.location_tag || 'Sector 1')}
                        </h4>
                        <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.4;">
                            ${escapeHtml(inc.description)}
                        </p>
                        ${inc.simulated_dispatch_status === 'SIMULATED_DISPATCHED' ? `
                            <div style="margin-top: 0.5rem; font-size: 0.78rem; color: var(--brand-blue); background: rgba(56, 189, 248, 0.1); padding: 0.35rem 0.65rem; border-radius: var(--radius-sm); border: 1px solid rgba(56, 189, 248, 0.25);">
                                🚑 <strong>Simulated Dispatch Record:</strong> ${escapeHtml(inc.simulated_dispatch_notes || 'Response initiated')}
                            </div>
                        ` : ''}
                    </div>

                    <div style="display: flex; gap: 0.45rem; flex-wrap: wrap; margin-top: 0.35rem;">
                        <button class="btn btn-sm btn-secondary" onclick="App.openIncidentDetail(${inc.id})">Details</button>
                        ${inc.status === 'ACTIVE' ? `
                            <button class="btn btn-sm btn-warning" onclick="App.confirmAcknowledge(${inc.id})">Acknowledge</button>
                        ` : ''}
                        ${inc.status !== 'RESOLVED' ? `
                            <button class="btn btn-sm btn-success" onclick="App.confirmResolve(${inc.id})">Resolve</button>
                        ` : ''}
                        ${inc.simulated_dispatch_status !== 'SIMULATED_DISPATCHED' ? `
                            <button class="btn btn-sm btn-danger" onclick="App.confirmSimulatedDispatch(${inc.id})">🚨 Dispatch (Simulated)</button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join("");
    }

    function filterAlerts(level, btn) {
        alertsFilter = level;
        document.querySelectorAll("[data-filter]").forEach(b => b.classList.remove("active-filter"));
        if (btn) btn.classList.add("active-filter");
        renderAlertsList();
    }

    function initHistoryFilters() {
        const sInput = document.getElementById("history-search-input");
        const rFilter = document.getElementById("history-risk-filter");
        const stFilter = document.getElementById("history-status-filter");

        if (sInput) sInput.addEventListener("input", renderHistoryTable);
        if (rFilter) rFilter.addEventListener("change", renderHistoryTable);
        if (stFilter) stFilter.addEventListener("change", renderHistoryTable);
    }

    function renderHistoryTable() {
        const tbody = document.getElementById("history-incidents-tbody");
        if (!tbody) return;

        const searchVal = (document.getElementById("history-search-input")?.value || "").toLowerCase();
        const riskFilter = document.getElementById("history-risk-filter")?.value || "";
        const statusFilter = document.getElementById("history-status-filter")?.value || "";

        let filtered = incidentsCache.filter(inc => {
            const matchesSearch = !searchVal ||
                inc.description.toLowerCase().includes(searchVal) ||
                (inc.location_tag && inc.location_tag.toLowerCase().includes(searchVal)) ||
                inc.incident_type.toLowerCase().includes(searchVal) ||
                String(inc.id).includes(searchVal);

            const matchesRisk = !riskFilter || inc.risk_level === riskFilter;
            const matchesStatus = !statusFilter || inc.status === statusFilter;

            return matchesSearch && matchesRisk && matchesStatus;
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
                        No incidents matching the specified search criteria.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filtered.map(inc => `
            <tr>
                <td><strong>#${inc.id}</strong></td>
                <td>${formatTimestamp(inc.timestamp)}</td>
                <td>${escapeHtml(inc.location_tag || 'Sector 1')}</td>
                <td>${escapeHtml(inc.incident_type)}</td>
                <td>${getRiskBadge(inc.risk_level)}</td>
                <td>${Math.round((inc.confidence || 0) * 100)}%</td>
                <td>
                    ${inc.simulated_dispatch_status === 'SIMULATED_DISPATCHED' 
                        ? '<span class="badge badge-dispatched">DISPATCHED (SIM)</span>' 
                        : '<span style="color: var(--text-muted); font-size: 0.72rem;">STANDBY</span>'}
                </td>
                <td>${getStatusBadge(inc.status)}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="App.openIncidentDetail(${inc.id})">Inspect</button>
                </td>
            </tr>
        `).join("");
    }

    // =========================================================================
    // Incident Action Handlers with Confirmation Modals
    // =========================================================================
    function confirmAcknowledge(id) {
        openConfirmModal({
            title: `Acknowledge Incident #${id}`,
            message: `Acknowledge this alert as under active review by the watch officer?`,
            btnText: "Acknowledge Alert",
            btnClass: "btn-warning",
            onConfirm: async () => {
                try {
                    await ApiService.updateIncidentStatus(id, "ACKNOWLEDGED", "Officer acknowledged hazard");
                    showToast(`Incident #${id} acknowledged`, "info");
                    refreshAllData();
                } catch (err) {
                    showToast("Error: " + err.message, "error");
                }
            }
        });
    }

    function confirmResolve(id) {
        openConfirmModal({
            title: `Resolve Incident #${id}`,
            message: `Mark this incident as cleared and resolved on the surveillance sector?`,
            btnText: "Mark Resolved",
            btnClass: "btn-success",
            onConfirm: async () => {
                try {
                    await ApiService.updateIncidentStatus(id, "RESOLVED", "Cleared by command operator");
                    showToast(`Incident #${id} resolved`, "success");
                    refreshAllData();
                } catch (err) {
                    showToast("Error: " + err.message, "error");
                }
            }
        });
    }

    function confirmSimulatedDispatch(id) {
        openConfirmModal({
            title: `Simulated Emergency Dispatch (Incident #${id})`,
            message: `Transmit simulated rapid response dispatch signal to Highway Patrol and Emergency Medical Services? (Note: Strictly simulated for Capstone evaluation).`,
            btnText: "Transmit Simulated Signal",
            btnClass: "btn-danger",
            onConfirm: async () => {
                try {
                    const res = await ApiService.dispatchSimulatedEmergency(id, "Highway Emergency Rescue & Traffic Patrol");
                    showToast(`🚨 ${res.message}`, "success");
                    refreshAllData();
                } catch (err) {
                    showToast("Dispatch error: " + err.message, "error");
                }
            }
        });
    }

    async function openIncidentDetail(incidentId) {
        const modal = document.getElementById("incident-detail-modal");
        const titleEl = document.getElementById("modal-incident-title");
        const bodyEl = document.getElementById("modal-incident-body");

        if (!modal || !bodyEl) return;

        titleEl.textContent = `Incident Verification #${incidentId}`;
        bodyEl.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading telemetry details from database...</p>`;
        modal.classList.add("active");

        try {
            const inc = await ApiService.getIncidentById(incidentId);

            let snapshotHtml = "";
            if (inc.snapshot_path) {
                const fullUrl = ApiService.getMediaUrl(inc.snapshot_path);
                snapshotHtml = `
                    <div style="margin-top: 1rem;">
                        <span style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; display: block; margin-bottom: 0.35rem;">High-Resolution Snapshot</span>
                        <img src="${fullUrl}" alt="Incident Snapshot" style="width: 100%; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); max-height: 280px; object-fit: contain; background: #000;">
                    </div>
                `;
            }

            bodyEl.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 0.75rem; font-size: 0.82rem;">
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                        <span style="color: var(--text-muted);">Incident Record:</span>
                        <strong>#${inc.id}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                        <span style="color: var(--text-muted);">Risk Classification:</span>
                        ${getRiskBadge(inc.risk_level)}
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                        <span style="color: var(--text-muted);">Detection Confidence:</span>
                        <strong>${Math.round((inc.confidence || 0) * 100)}%</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                        <span style="color: var(--text-muted);">Timestamp (UTC):</span>
                        <strong style="font-family: ui-monospace, monospace;">${formatTimestamp(inc.timestamp)}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                        <span style="color: var(--text-muted);">Surveillance Location:</span>
                        <strong>${escapeHtml(inc.location_tag || 'Highway Sector')}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                        <span style="color: var(--text-muted);">Current Status:</span>
                        ${getStatusBadge(inc.status)}
                    </div>
                    <div style="background: var(--bg-surface); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                        <strong style="color: var(--cyan-glow); display: block; margin-bottom: 0.25rem;">Spatial Risk Description:</strong>
                        <p style="color: var(--text-secondary); line-height: 1.4;">${escapeHtml(inc.description)}</p>
                    </div>

                    ${inc.simulated_dispatch_status === 'SIMULATED_DISPATCHED' ? `
                        <div style="background: rgba(56, 189, 248, 0.1); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid rgba(56, 189, 248, 0.3);">
                            <strong style="color: var(--brand-blue); display: block; margin-bottom: 0.25rem;">Simulated Dispatch Log:</strong>
                            <p style="color: var(--text-secondary); font-size: 0.8rem;">${escapeHtml(inc.simulated_dispatch_notes)}</p>
                        </div>
                    ` : ''}

                    ${snapshotHtml}
                </div>
            `;
        } catch (err) {
            bodyEl.innerHTML = `<p style="color: var(--risk-high); padding: 2rem;">Error fetching incident details: ${err.message}</p>`;
        }
    }

    // =========================================================================
    // Surveillance Live Stream Controller
    // =========================================================================
    function initSurveillanceStream() {
        const streamUrl = ApiService.getStreamUrl(currentCameraIndex);
        const mainImg = document.getElementById("main-live-stream-img");
        const overviewImg = document.getElementById("overview-stream-img");
        const toggleBtn = document.getElementById("btn-toggle-stream");
        const reconnectBtn = document.getElementById("btn-reconnect-stream");

        if (mainImg) mainImg.src = streamUrl;
        if (overviewImg) overviewImg.src = streamUrl;

        if (toggleBtn) {
            toggleBtn.onclick = () => {
                isStreamActive = !isStreamActive;
                if (isStreamActive) {
                    mainImg.src = ApiService.getStreamUrl(currentCameraIndex);
                    toggleBtn.textContent = "Pause Feed";
                    showToast("Live surveillance stream resumed", "info");
                } else {
                    mainImg.src = "";
                    toggleBtn.textContent = "Resume Feed";
                    showToast("Live surveillance stream paused", "warning");
                }
            };
        }

        if (reconnectBtn) {
            reconnectBtn.onclick = () => {
                mainImg.src = "";
                setTimeout(() => {
                    mainImg.src = ApiService.getStreamUrl(currentCameraIndex);
                    showToast("Reconnected to camera stream", "success");
                }, 200);
            };
        }
    }

    function selectCamera(index, btn) {
        currentCameraIndex = index;
        document.querySelectorAll(".cam-tab-btn").forEach(b => b.classList.remove("active"));
        if (btn) btn.classList.add("active");

        const titles = [
            "CAM-01 • HIGHWAY CORRIDOR NORTH",
            "CAM-02 • URBAN ARTERIAL EXPRESS",
            "CAM-03 • HIGH-DENSITY INTERSECTION"
        ];
        const lbl = document.getElementById("cam-hud-label");
        const topTitle = document.getElementById("live-cam-title");

        if (lbl) lbl.textContent = titles[index] || `CAM-0${index + 1}`;
        if (topTitle) topTitle.textContent = `Surveillance Feeder ${titles[index]}`;

        const mainImg = document.getElementById("main-live-stream-img");
        if (mainImg) {
            mainImg.src = "";
            setTimeout(() => {
                mainImg.src = ApiService.getStreamUrl(currentCameraIndex);
            }, 150);
        }
        showToast(`Switched feed to ${titles[index]}`, "info");
    }

    // =========================================================================
    // Video & Footage Upload Dropzone
    // =========================================================================
    function initUploadDropzone() {
        const dropzone = document.getElementById("upload-dropzone");
        const fileInput = document.getElementById("file-input");
        const uploadBtn = document.getElementById("btn-start-upload");
        const label = document.getElementById("selected-file-label");

        if (!dropzone || !fileInput || !uploadBtn) return;

        let selectedFile = null;

        dropzone.addEventListener("click", () => fileInput.click());

        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });

        dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
        });

        function handleFileSelect(file) {
            selectedFile = file;
            label.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
            uploadBtn.disabled = false;
        }

        uploadBtn.addEventListener("click", async () => {
            if (!selectedFile) return;

            const progressContainer = document.getElementById("upload-progress-container");
            const resultsPanel = document.getElementById("upload-results-panel");
            const statusText = document.getElementById("upload-status-text");
            const locTag = document.getElementById("upload-location-tag").value || "Surveillance Footage";
            const sampleRate = parseInt(document.getElementById("upload-sample-rate").value || "2", 10);

            uploadBtn.disabled = true;
            progressContainer.style.display = "block";
            resultsPanel.style.display = "none";
            statusText.textContent = `Uploading and running YOLOv8 on ${selectedFile.name}...`;

            try {
                const isVideo = selectedFile.type.startsWith("video/") || /\.(mp4|avi|mov|mkv|webm)$/i.test(selectedFile.name);

                let result;
                if (isVideo) {
                    statusText.textContent = "Processing video frames and computing spatial collision vectors...";
                    result = await ApiService.detectVideo(selectedFile, locTag, sampleRate);
                } else {
                    statusText.textContent = "Running single-stage YOLO inference on frame...";
                    result = await ApiService.detectImage(selectedFile, locTag);
                }

                displayUploadResults(result, isVideo);
                showToast("Footage analyzed successfully", "success");
                refreshAllData();
            } catch (err) {
                showToast("Inference failed: " + err.message, "error");
            } finally {
                uploadBtn.disabled = false;
                progressContainer.style.display = "none";
            }
        });
    }

    function displayUploadResults(data, isVideo) {
        const resultsPanel = document.getElementById("upload-results-panel");
        const mediaContainer = document.getElementById("upload-media-container");
        const detailsContainer = document.getElementById("upload-summary-details");
        const badge = document.getElementById("upload-result-badge");
        const downloadContainer = document.getElementById("upload-download-container");

        if (!resultsPanel || !mediaContainer || !detailsContainer) return;

        resultsPanel.style.display = "block";
        const peakRisk = (data.peak_risk_level || "LOW").toUpperCase();

        if (badge) {
            badge.className = `badge ${peakRisk === 'HIGH' ? 'badge-high' : (peakRisk === 'MEDIUM' ? 'badge-medium' : 'badge-low')}`;
            badge.textContent = `${peakRisk} RISK`;
        }

        // Render Media Visual
        if (isVideo && data.annotated_video_url) {
            const videoUrl = ApiService.getMediaUrl(data.annotated_video_url);
            mediaContainer.innerHTML = `
                <video controls autoplay loop style="width: 100%; max-height: 380px;">
                    <source src="${videoUrl}" type="video/mp4">
                    Your browser does not support HTML5 video.
                </video>
            `;
            if (downloadContainer) {
                downloadContainer.innerHTML = `
                    <a href="${videoUrl}" download class="btn btn-sm btn-secondary">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        <span>Download Annotated Video</span>
                    </a>
                `;
            }
        } else if (data.annotated_image_url) {
            const imgUrl = ApiService.getMediaUrl(data.annotated_image_url);
            mediaContainer.innerHTML = `
                <img src="${imgUrl}" alt="Detection Output" style="width: 100%; max-height: 380px; object-fit: contain;">
            `;
            if (downloadContainer) {
                downloadContainer.innerHTML = `
                    <a href="${imgUrl}" download class="btn btn-sm btn-secondary">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        <span>Download Annotated Snapshot</span>
                    </a>
                `;
            }
        }

        // Render Telemetry
        const classesHtml = Object.entries(data.class_counts || {})
            .map(([cls, cnt]) => `<li>${cls}: <strong>${cnt}</strong></li>`)
            .join("") || "<li>No targeted vehicles detected.</li>";

        let risksHtml = "";
        if (data.risks && data.risks.length > 0) {
            risksHtml = `
                <div style="background: var(--bg-surface); padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-top: 0.5rem;">
                    <strong style="color: var(--risk-high); font-size: 0.78rem; display: block; margin-bottom: 0.25rem;">Spatial Hazards Identified:</strong>
                    <ul style="padding-left: 1.25rem; font-size: 0.76rem; color: var(--text-secondary); display: flex; flex-direction: column; gap: 0.25rem;">
                        ${data.risks.map(r => `<li>${escapeHtml(r.description)}</li>`).join("")}
                    </ul>
                </div>
            `;
        }

        detailsContainer.innerHTML = `
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                <span style="color: var(--text-muted);">Risk Classification:</span>
                <strong>${peakRisk}</strong>
            </div>
            ${data.total_frames ? `
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.35rem;">
                    <span style="color: var(--text-muted);">Frame Telemetry:</span>
                    <strong>${data.processed_frames} / ${data.total_frames} frames (${data.fps} FPS)</strong>
                </div>
            ` : ''}
            <div>
                <span style="color: var(--text-muted); display: block; margin-bottom: 0.25rem;">Classified Entities:</span>
                <ul style="padding-left: 1.25rem; font-size: 0.8rem; color: var(--text-primary);">
                    ${classesHtml}
                </ul>
            </div>
            ${risksHtml}
            ${data.incident_id ? `
                <div style="margin-top: 0.5rem;">
                    <button class="btn btn-sm btn-primary" onclick="App.openIncidentDetail(${data.incident_id})">
                        View Logged Incident Record #${data.incident_id}
                    </button>
                </div>
            ` : ''}
        `;
    }

    // =========================================================================
    // CSV Export
    // =========================================================================
    function exportIncidentsCSV() {
        if (!incidentsCache || incidentsCache.length === 0) {
            showToast("No incident records available to export", "warning");
            return;
        }

        const headers = ["Incident ID", "Timestamp (UTC)", "Location Sector", "Type", "Risk Level", "Confidence", "Status", "Simulated Dispatch", "Description"];
        const rows = incidentsCache.map(i => [
            i.id,
            `"${formatTimestamp(i.timestamp)}"`,
            `"${(i.location_tag || '').replace(/"/g, '""')}"`,
            `"${(i.incident_type || '').replace(/"/g, '""')}"`,
            i.risk_level,
            i.confidence,
            i.status,
            i.simulated_dispatch_status,
            `"${(i.description || '').replace(/"/g, '""')}"`
        ]);

        const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `EOCC_Incidents_Audit_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast("Incident history CSV exported", "success");
    }

    // =========================================================================
    // Utility Helpers
    // =========================================================================
    function formatTimestamp(isoStr) {
        if (!isoStr) return "--";
        try {
            const d = new Date(isoStr);
            return d.toISOString().replace("T", " ").slice(0, 19);
        } catch {
            return isoStr;
        }
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Public API
    return {
        init,
        navigateTo,
        refreshAllData,
        loadAlerts: fetchIncidents,
        loadHistory: fetchIncidents,
        filterAlerts,
        selectCamera,
        confirmAcknowledge,
        confirmResolve,
        confirmSimulatedDispatch,
        openIncidentDetail,
        closeIncidentModal,
        closeSettingsModal,
        openManualAlertModal,
        closeManualAlertModal,
        closeConfirmModal,
        exportIncidentsCSV
    };
})();

document.addEventListener("DOMContentLoaded", () => {
    App.init();
});

window.App = App;
