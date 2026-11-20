/**
 * API Client Module for Emergency Intelligence and Response System (EOCC).
 * Connects frontend to the Render backend REST endpoints and MJPEG video feed.
 */

const ApiService = (function () {
    const DEFAULT_BACKEND_URL = "http://localhost:5000";

    function getBackendUrl() {
        if (window.BACKEND_URL && window.BACKEND_URL.trim() !== "") {
            return window.BACKEND_URL.replace(/\/+$/, "");
        }
        const stored = localStorage.getItem("EMERGENCY_BACKEND_URL");
        if (stored && stored.trim() !== "") {
            return stored.replace(/\/+$/, "");
        }
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            return DEFAULT_BACKEND_URL;
        }
        return DEFAULT_BACKEND_URL;
    }

    function setBackendUrl(url) {
        if (!url || url.trim() === "") {
            localStorage.removeItem("EMERGENCY_BACKEND_URL");
        } else {
            const cleanUrl = url.trim().replace(/\/+$/, "");
            localStorage.setItem("EMERGENCY_BACKEND_URL", cleanUrl);
        }
    }

    function getMediaUrl(relativePath) {
        if (!relativePath) return "";
        if (relativePath.startsWith("http://") || relativePath.startsWith("https://")) {
            return relativePath;
        }
        const base = getBackendUrl();
        const cleanPath = relativePath.startsWith("/") ? relativePath : `/${relativePath}`;
        return `${base}${cleanPath}`;
    }

    function getStreamUrl(cameraIndex = 0) {
        const base = getBackendUrl();
        return `${base}/api/stream?source=${cameraIndex}&t=${Date.now()}`;
    }

    async function testLatency(customUrl = null) {
        const base = (customUrl || getBackendUrl()).replace(/\/+$/, "");
        const start = performance.now();
        const res = await fetch(`${base}/api/health`, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const latency = Math.round(performance.now() - start);
        return { data, latency };
    }

    async function request(endpoint, options = {}) {
        const base = getBackendUrl();
        const url = `${base}${endpoint}`;

        const defaultHeaders = {};
        if (!(options.body instanceof FormData)) {
            defaultHeaders["Content-Type"] = "application/json";
        }

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...(options.headers || {})
            }
        };

        try {
            const response = await fetch(url, config);
            const contentType = response.headers.get("content-type") || "";

            let data;
            if (contentType.includes("application/json")) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                const message = (data && data.error) || (data && data.message) || response.statusText || "Request failed";
                throw new Error(`[${response.status}] ${message}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    }

    return {
        getBackendUrl,
        setBackendUrl,
        getMediaUrl,
        getStreamUrl,
        testLatency,

        // Core API routes
        checkHealth: () => request("/api/health"),
        getStats: () => request("/api/stats"),
        getIncidents: (params = {}) => {
            const query = new URLSearchParams();
            if (params.limit) query.append("limit", params.limit);
            if (params.risk_level) query.append("risk_level", params.risk_level);
            if (params.status) query.append("status", params.status);
            const qs = query.toString() ? `?${query.toString()}` : "";
            return request(`/api/incidents${qs}`);
        },
        getIncidentById: (id) => request(`/api/incidents/${id}`),
        updateIncidentStatus: (id, status, notes = "") =>
            request(`/api/incidents/${id}/status`, {
                method: "POST",
                body: JSON.stringify({ status, notes })
            }),
        dispatchSimulatedEmergency: (id, agency = "Highway Emergency Rescue & Traffic Patrol") =>
            request(`/api/incidents/${id}/dispatch`, {
                method: "POST",
                body: JSON.stringify({ agency })
            }),
        createManualAlert: (alertData) =>
            request("/api/incidents/manual-alert", {
                method: "POST",
                body: JSON.stringify(alertData)
            }),
        detectImage: (file, locationTag = "Surveillance Camera Ingestion") => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("location_tag", locationTag);
            return request("/api/detect/image", {
                method: "POST",
                body: formData
            });
        },
        detectVideo: (file, locationTag = "Surveillance Video Feed", sampleRate = 2) => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("location_tag", locationTag);
            formData.append("frame_sample_rate", sampleRate);
            return request("/api/detect/video", {
                method: "POST",
                body: formData
            });
        }
    };
})();

window.ApiService = ApiService;
