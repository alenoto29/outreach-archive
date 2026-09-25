// Dashboard bootstrap — Fase 3a
// Replaces static data.js with live fetch from backend REST API.
// Populates window.DASHBOARD_DATA then dispatches "dashboard:ready".
(function () {
    "use strict";

    const POLL_INTERVAL_MS = 30000;
    let pollTimer = null;
    function schedulePoll() {
        if (pollTimer) clearTimeout(pollTimer);
        if (document.hidden) return;
        pollTimer = setTimeout(async () => { await loadData(false); schedulePoll(); }, POLL_INTERVAL_MS);
    }
    document.addEventListener && document.addEventListener("visibilitychange", () => {
        if (!document.hidden) schedulePoll();
    });
    const LS_TOKEN = "outreach_archive_token";
    const LS_USER = "outreach_archive_user";
    const LS_API = "outreach_archive_api_base";

    const CSS = `
#ppn-login-modal { position:fixed; inset:0; z-index:9999; display:none; font-family:-apple-system,system-ui,sans-serif; }
.ppn-login-backdrop { position:absolute; inset:0; background:rgba(0,0,0,0.55); }
.ppn-login-box { position:relative; max-width:380px; margin:12vh auto; background:#fff; border-radius:12px; padding:28px 26px; box-shadow:0 20px 60px rgba(0,0,0,0.25); }
.ppn-login-box h2 { margin:0 0 4px; font-size:20px; color:#111; }
.ppn-login-hint { margin:0 0 18px; color:#666; font-size:13px; }
.ppn-login-box label { display:block; margin-bottom:12px; font-size:12px; color:#444; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; }
.ppn-login-box input { display:block; width:100%; margin-top:5px; padding:10px 12px; border:1px solid #d0d7de; border-radius:8px; font-size:14px; font-weight:400; text-transform:none; letter-spacing:0; color:#111; box-sizing:border-box; }
.ppn-login-box input:focus { outline:none; border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,0.15); }
.ppn-login-err { color:#c0392b; font-size:13px; margin:4px 0 10px; display:none; }
.ppn-login-box button { width:100%; padding:11px; background:#2563eb; color:#fff; border:0; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; margin-top:4px; }
.ppn-login-box button:hover { background:#1d4ed8; }
.ppn-login-box details { margin-top:14px; font-size:12px; color:#666; }
.ppn-login-box details summary { cursor:pointer; user-select:none; }
#ppn-status-banner { position:fixed; top:0; left:0; right:0; z-index:9998; padding:10px 16px; font-family:-apple-system,system-ui,sans-serif; font-size:13px; text-align:center; display:none; }
.ppn-banner.err { background:#c0392b; color:#fff; }
.ppn-banner.warn { background:#f39c12; color:#fff; }
.ppn-banner.ok { background:#27ae60; color:#fff; }
#ppn-update-banner { position:fixed; top:0; left:0; right:0; z-index:9997; padding:10px 16px; background:#2563eb; color:#fff; font-family:-apple-system,system-ui,sans-serif; font-size:13px; text-align:center; display:none; }
#ppn-update-banner button { margin-left:12px; background:#fff; color:#2563eb; border:0; padding:4px 12px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; }
#ppn-update-banner button:hover { background:#e5e7eb; }
#ppn-update-banner .close { margin-left:8px; background:transparent; color:#fff; border:1px solid rgba(255,255,255,0.5); padding:4px 10px; }
`;

    function apiBase() {
        const override = sessionStorage.getItem(LS_API);
        if (override) return override.replace(/\/+$/, "");
        const origin = window.location.origin;
        if (origin.startsWith("http")) return origin;
        return "http://localhost:8080";
    }

    function getToken() { return sessionStorage.getItem(LS_TOKEN) || ""; }
    function getUser() { return sessionStorage.getItem(LS_USER) || ""; }

    function setCreds(token, user) {
        sessionStorage.setItem(LS_TOKEN, token);
        sessionStorage.setItem(LS_USER, user);
    }

    function clearCreds() {
        sessionStorage.removeItem(LS_TOKEN);
        sessionStorage.removeItem(LS_USER);
    }

    async function apiFetch(path, opts) {
        opts = opts || {};
        const url = `${apiBase()}${path}`;
        const headers = Object.assign({
            "Authorization": `Bearer ${getToken()}`,
            "X-User-Name": getUser(),
        }, opts.headers || {});
        return fetch(url, Object.assign({}, opts, { headers }));
    }

    function showLoginModal(errMsg) {
        let modal = document.getElementById("ppn-login-modal");
        if (!modal) {
            modal = document.createElement("div");
            modal.id = "ppn-login-modal";
            modal.innerHTML = `
                <div class="ppn-login-backdrop"></div>
                <div class="ppn-login-box">
                    <h2>Accesso dashboard</h2>
                    <p class="ppn-login-hint">Inserisci nome e token condiviso.</p>
                    <label>Nome utente
                        <input type="text" id="ppn-login-user" autocomplete="off" placeholder="es: alessandro">
                    </label>
                    <label>Token
                        <input type="password" id="ppn-login-token" autocomplete="off">
                    </label>
                    <div class="ppn-login-err" id="ppn-login-err"></div>
                    <button id="ppn-login-submit">Entra</button>
                    <details>
                        <summary>Avanzate</summary>
                        <label>API base URL
                            <input type="text" id="ppn-login-api" placeholder="${apiBase()}">
                        </label>
                    </details>
                </div>
            `;
            document.body.appendChild(modal);
            document.getElementById("ppn-login-submit").addEventListener("click", submitLogin);
            document.getElementById("ppn-login-token").addEventListener("keydown", (e) => {
                if (e.key === "Enter") submitLogin();
            });
            document.getElementById("ppn-login-user").addEventListener("keydown", (e) => {
                if (e.key === "Enter") submitLogin();
            });
        }
        const err = document.getElementById("ppn-login-err");
        err.textContent = errMsg || "";
        err.style.display = errMsg ? "block" : "none";
        document.getElementById("ppn-login-user").value = getUser();
        modal.style.display = "block";
    }

    function hideLoginModal() {
        const modal = document.getElementById("ppn-login-modal");
        if (modal) modal.style.display = "none";
    }

    async function submitLogin() {
        const user = document.getElementById("ppn-login-user").value.trim();
        const token = document.getElementById("ppn-login-token").value.trim();
        const apiOverride = document.getElementById("ppn-login-api").value.trim();
        if (!user || !token) {
            showLoginModal("Nome e token obbligatori.");
            return;
        }
        if (apiOverride) sessionStorage.setItem(LS_API, apiOverride);
        setCreds(token, user);
        const ok = await loadData(true);
        if (ok) {
            hideLoginModal();
            bootDashboard();
        }
    }

    function setBanner(state, msg) {
        let banner = document.getElementById("ppn-status-banner");
        if (!banner) {
            banner = document.createElement("div");
            banner.id = "ppn-status-banner";
            document.body.appendChild(banner);
        }
        banner.className = `ppn-banner ${state}`;
        banner.textContent = msg || "";
        banner.style.display = msg ? "block" : "none";
    }

    function computeSignature(data) {
        // Signature that changes ONLY on real mutations (not on every poll).
        // meta.generated always changes → exclude it.
        // Use: totals + max updated_at across journalists (captures add/edit/delete).
        const m = data._meta || {};
        const js = data.journalists || [];
        let maxUpd = "";
        for (let i = 0; i < js.length; i++) {
            const u = js[i].updated_at || "";
            if (u > maxUpd) maxUpd = u;
        }
        return [
            m.total_journalists || 0,
            m.total_publishers || 0,
            (m.all_campaigns || []).length,
            js.length,
            maxUpd,
        ].join("|");
    }

    function showUpdateBanner() {
        let banner = document.getElementById("ppn-update-banner");
        if (!banner) {
            banner = document.createElement("div");
            banner.id = "ppn-update-banner";
            banner.innerHTML = `
                <span>Dati aggiornati da un altro utente.</span>
                <button id="ppn-update-reload">Ricarica</button>
                <button class="close" id="ppn-update-dismiss">Dopo</button>
            `;
            document.body.appendChild(banner);
            document.getElementById("ppn-update-reload").addEventListener("click", () => location.reload());
            document.getElementById("ppn-update-dismiss").addEventListener("click", () => {
                banner.style.display = "none";
            });
        }
        banner.style.display = "block";
    }

    function isFormModalOpen() {
        const m = document.getElementById("ppn-form-modal");
        return m && m.style.display !== "none" && m.offsetParent !== null;
    }

    let lastSignature = null;
    let lastEtag = null;

    async function loadData(isLoginAttempt) {
        try {
            const headers = {};
            if (lastEtag && !isLoginAttempt) headers["If-None-Match"] = lastEtag;
            const r = await apiFetch("/api/export/json", { headers });
            if (r.status === 401) {
                if (!isLoginAttempt) clearCreds();
                showLoginModal("Token o utente non valido.");
                return false;
            }
            if (r.status === 304) {
                // Nothing changed — reuse last payload. Just mark fresh fetch.
                window.DASHBOARD_LAST_FETCH = new Date();
                setBanner("", "");
                return true;
            }
            if (!r.ok) {
                setBanner("err", `Errore API: ${r.status}`);
                return false;
            }
            const newEtag = r.headers.get("ETag");
            if (newEtag) lastEtag = newEtag;
            const data = await r.json();
            const newSig = computeSignature(data);
            const hadPrev = lastSignature !== null;
            const changed = hadPrev && newSig !== lastSignature;

            window.DASHBOARD_DATA = data;
            window.DASHBOARD_LAST_FETCH = new Date();
            setBanner("", "");
            window.dispatchEvent(new CustomEvent("dashboard:data", { detail: data }));

            // Update lastSignature ONLY when form closed. Otherwise keep stale so
            // the change will still be detected after user closes form.
            if (!isFormModalOpen()) {
                lastSignature = newSig;
                if (changed) showUpdateBanner();
            } else if (!hadPrev) {
                // First poll and form somehow open: still set baseline
                lastSignature = newSig;
            }
            return true;
        } catch (e) {
            setBanner("err", `Connessione persa. Retry in 30s. (${e.message})`);
            return false;
        }
    }

    let booted = false;
    function bootDashboard() {
        if (booted) return;
        booted = true;
        window.dispatchEvent(new CustomEvent("dashboard:ready"));
        schedulePoll();
    }

    function injectCSS() {
        if (document.getElementById("ppn-api-css")) return;
        const s = document.createElement("style");
        s.id = "ppn-api-css";
        s.textContent = CSS;
        document.head.appendChild(s);
    }

    async function init() {
        injectCSS();
        if (!getToken() || !getUser()) {
            showLoginModal();
            return;
        }
        const ok = await loadData(false);
        if (ok) bootDashboard();
    }

    window.PPN_API = {
        fetch: apiFetch,
        logout: () => { clearCreds(); location.reload(); },
        user: getUser,
        reload: () => loadData(false),
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
