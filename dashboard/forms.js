// Dashboard CRUD forms — Fase 3b
// Journalist add/edit/delete. Requires api.js (PPN_API global).
(function () {
    "use strict";

    const MARKETS = ["IT", "ES", "FR"];

    const CSS = `
.ppn-fab { position:fixed; z-index:9990; border:0; border-radius:28px; font-size:14px; font-weight:600; cursor:pointer; box-shadow:0 8px 24px rgba(37,99,235,0.35); display:none; color:#fff; background:#2563eb; padding:14px 22px; }
.ppn-fab:hover { background:#1d4ed8; }
#ppn-fab-journalist, #ppn-fab-publisher { right:24px; bottom:24px; }
#ppn-fab-campaigns { right:24px; bottom:80px; background:#475569; padding:10px 16px; font-size:13px; border-radius:22px; box-shadow:0 6px 18px rgba(71,85,105,0.3); }
#ppn-fab-campaigns:hover { background:#334155; }
.ppn-camp-table { width:100%; border-collapse:collapse; font-size:13px; }
.ppn-camp-table th { text-align:left; padding:8px 10px; background:#f3f4f6; font-size:11px; color:#374151; text-transform:uppercase; letter-spacing:0.5px; }
.ppn-camp-table td { padding:8px 10px; border-top:1px solid #e5e7eb; }
.ppn-camp-table tr:hover td { background:#f9fafb; }
#ppn-form-modal { position:fixed; inset:0; z-index:9995; display:none; font-family:-apple-system,system-ui,sans-serif; }
.ppn-form-backdrop { position:absolute; inset:0; background:rgba(0,0,0,0.55); }
.ppn-form-box { position:relative; max-width:640px; margin:6vh auto; background:#fff; border-radius:12px; box-shadow:0 20px 60px rgba(0,0,0,0.3); max-height:88vh; display:flex; flex-direction:column; }
.ppn-form-header { padding:18px 22px; border-bottom:1px solid #e5e7eb; display:flex; justify-content:space-between; align-items:center; }
.ppn-form-header h2 { margin:0; font-size:18px; color:#111; }
.ppn-form-close { background:none; border:0; font-size:22px; cursor:pointer; color:#666; line-height:1; padding:4px 8px; }
.ppn-form-body { padding:18px 22px; overflow-y:auto; }
.ppn-form-err-top { background:#fef2f2; color:#991b1b; padding:10px 12px; border-radius:8px; margin-bottom:14px; font-size:13px; display:none; }
.ppn-form-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.ppn-form-grid .full { grid-column:1 / -1; }
.ppn-form-field { display:flex; flex-direction:column; }
.ppn-form-field label { font-size:11px; color:#444; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; }
.ppn-form-field input, .ppn-form-field select, .ppn-form-field textarea { padding:8px 10px; border:1px solid #d0d7de; border-radius:6px; font-size:13px; color:#111; font-family:inherit; }
.ppn-form-field input:focus, .ppn-form-field select:focus, .ppn-form-field textarea:focus { outline:none; border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,0.15); }
.ppn-form-field textarea { resize:vertical; min-height:60px; }
.ppn-form-field .req { color:#c0392b; }
.ppn-form-err { color:#c0392b; font-size:11px; margin-top:4px; min-height:14px; }
.ppn-chip-input { border:1px solid #d0d7de; border-radius:6px; padding:4px; display:flex; flex-wrap:wrap; gap:4px; background:#fff; min-height:38px; align-items:center; }
.ppn-chip-input input { border:0; flex:1; padding:4px 6px; font-size:13px; outline:none; min-width:80px; }
.ppn-chip { background:#e0e7ff; color:#3730a3; padding:3px 8px; border-radius:4px; font-size:12px; display:inline-flex; align-items:center; gap:4px; }
.ppn-chip .x { cursor:pointer; font-weight:700; color:#6366f1; }
.ppn-chip .x:hover { color:#1e1b4b; }
.ppn-chip-suggest { position:absolute; background:#fff; border:1px solid #d0d7de; border-radius:6px; box-shadow:0 4px 12px rgba(0,0,0,0.1); max-height:180px; overflow-y:auto; z-index:10000; min-width:200px; }
.ppn-chip-suggest div { padding:6px 10px; cursor:pointer; font-size:13px; }
.ppn-chip-suggest div:hover, .ppn-chip-suggest div.hi { background:#f3f4f6; }
.ppn-form-footer { padding:14px 22px; border-top:1px solid #e5e7eb; display:flex; justify-content:space-between; gap:10px; }
.ppn-form-footer .spacer { flex:1; }
.ppn-btn { padding:9px 16px; border-radius:7px; font-size:13px; font-weight:600; cursor:pointer; border:0; }
.ppn-btn-primary { background:#2563eb; color:#fff; }
.ppn-btn-primary:hover { background:#1d4ed8; }
.ppn-btn-primary:disabled { background:#94a3b8; cursor:not-allowed; }
.ppn-btn-secondary { background:#f3f4f6; color:#374151; border:1px solid #d0d7de; }
.ppn-btn-secondary:hover { background:#e5e7eb; }
.ppn-btn-danger { background:#dc2626; color:#fff; }
.ppn-btn-danger:hover { background:#b91c1c; }
.ppn-row-edit-btn { background:#2563eb; color:#fff; border:0; border-radius:6px; padding:6px 12px; font-size:12px; font-weight:600; cursor:pointer; margin-right:8px; }
.ppn-row-edit-btn:hover { background:#1d4ed8; }
.ppn-row-del-btn { background:#fff; color:#dc2626; border:1px solid #dc2626; border-radius:6px; padding:6px 12px; font-size:12px; font-weight:600; cursor:pointer; }
.ppn-row-del-btn:hover { background:#fef2f2; }
.ppn-row-actions { margin-top:12px; padding-top:12px; border-top:1px dashed #e5e7eb; }
.ppn-toast { position:fixed; bottom:24px; left:50%; transform:translateX(-50%); background:#111; color:#fff; padding:10px 18px; border-radius:8px; font-size:13px; z-index:10001; box-shadow:0 8px 20px rgba(0,0,0,0.3); }
.ppn-toast.ok { background:#16a34a; }
.ppn-toast.err { background:#dc2626; }
`;

    function el(tag, attrs, ...children) {
        const e = document.createElement(tag);
        for (const k in (attrs || {})) {
            if (k === "class") e.className = attrs[k];
            else if (k.startsWith("on")) e.addEventListener(k.slice(2), attrs[k]);
            else e.setAttribute(k, attrs[k]);
        }
        children.flat().forEach(c => {
            if (c == null) return;
            e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
        });
        return e;
    }

    function injectCSS() {
        if (document.getElementById("ppn-forms-css")) return;
        const s = document.createElement("style");
        s.id = "ppn-forms-css";
        s.textContent = CSS;
        document.head.appendChild(s);
    }

    function toast(msg, state) {
        const t = el("div", { class: `ppn-toast ${state || ""}` }, msg);
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 2800);
    }

    // Chip widget with autocomplete datalist from provided pool
    function chipInput(container, initial, pool) {
        const chips = new Set(initial || []);
        const input = el("input", { type: "text", placeholder: "Digita e premi Invio..." });
        let suggest = null;
        let hiIdx = -1;

        function render() {
            container.innerHTML = "";
            chips.forEach(c => {
                const chip = el("span", { class: "ppn-chip" },
                    c,
                    el("span", { class: "x", onclick: () => { chips.delete(c); render(); } }, "\u00d7")
                );
                container.appendChild(chip);
            });
            container.appendChild(input);
            input.focus();
        }

        function closeSuggest() {
            if (suggest) { suggest.remove(); suggest = null; hiIdx = -1; }
        }

        function openSuggest() {
            closeSuggest();
            const q = input.value.trim().toLowerCase();
            if (!q) return;
            const matches = pool.filter(p => p.toLowerCase().includes(q) && !chips.has(p)).slice(0, 8);
            if (!matches.length) return;
            suggest = el("div", { class: "ppn-chip-suggest" });
            matches.forEach((m, i) => {
                suggest.appendChild(el("div", { onclick: () => { chips.add(m); input.value = ""; closeSuggest(); render(); } }, m));
            });
            const r = container.getBoundingClientRect();
            suggest.style.top = (r.bottom + window.scrollY + 2) + "px";
            suggest.style.left = (r.left + window.scrollX) + "px";
            suggest.style.width = r.width + "px";
            document.body.appendChild(suggest);
        }

        input.addEventListener("input", openSuggest);
        input.addEventListener("blur", () => setTimeout(closeSuggest, 150));
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                if (suggest && hiIdx >= 0) {
                    suggest.children[hiIdx].click();
                    return;
                }
                const v = input.value.trim();
                if (v && !chips.has(v)) { chips.add(v); input.value = ""; closeSuggest(); render(); }
            } else if (e.key === "Backspace" && !input.value && chips.size) {
                const last = [...chips].pop();
                chips.delete(last);
                render();
            } else if (e.key === "ArrowDown" && suggest) {
                e.preventDefault();
                hiIdx = Math.min(hiIdx + 1, suggest.children.length - 1);
                [...suggest.children].forEach((c, i) => c.classList.toggle("hi", i === hiIdx));
            } else if (e.key === "ArrowUp" && suggest) {
                e.preventDefault();
                hiIdx = Math.max(hiIdx - 1, 0);
                [...suggest.children].forEach((c, i) => c.classList.toggle("hi", i === hiIdx));
            } else if (e.key === "Escape") {
                closeSuggest();
            }
        });

        render();
        return { get: () => [...chips] };
    }

    function buildForm(journalist) {
        const isEdit = !!journalist;
        const j = journalist || {};
        const topicsPool = (window.DASHBOARD_DATA?._meta?.all_topics || []);
        const campaignsPool = (window.DASHBOARD_DATA?._meta?.all_campaigns || []);

        const modal = el("div", { id: "ppn-form-modal", style: "display:block" });
        const backdrop = el("div", { class: "ppn-form-backdrop" });
        const box = el("div", { class: "ppn-form-box" });

        const errTop = el("div", { class: "ppn-form-err-top", id: "ppn-form-err-top" });

        const header = el("div", { class: "ppn-form-header" },
            el("h2", {}, isEdit ? `Modifica giornalista #${j.id}` : "Aggiungi giornalista"),
            el("button", { class: "ppn-form-close", onclick: close }, "\u00d7")
        );

        function field(label, input, required, errId) {
            return el("div", { class: "ppn-form-field" },
                el("label", {}, label, required ? el("span", { class: "req" }, " *") : null),
                input,
                el("div", { class: "ppn-form-err", id: errId || "" })
            );
        }

        function inputEl(name, value, type) {
            return el("input", { type: type || "text", name, value: value == null ? "" : String(value) });
        }

        function selectEl(name, value, options) {
            const s = el("select", { name });
            options.forEach(o => {
                const opt = el("option", { value: o }, o || "—");
                if (o === value) opt.setAttribute("selected", "selected");
                s.appendChild(opt);
            });
            return s;
        }

        const emailInput = inputEl("email", j.email, "email");
        const marketSel = selectEl("market", j.market, ["", ...MARKETS]);
        const firstNameInput = inputEl("first_name", j.first_name);
        const lastNameInput = inputEl("last_name", j.last_name);
        const jobInput = inputEl("job_title", j.job_title);
        const pubNameInput = inputEl("publisher_name", j.publisher);
        const pubDomInput = inputEl("publisher_domain", j.domain);
        const emailTypeInput = inputEl("email_type", j.email_type);
        const emailStatusInput = inputEl("email_status", j.email_status);
        const responseStatusInput = inputEl("response_status", j.response_status);
        const linkedinInput = inputEl("linkedin", j.linkedin);
        const authorInput = inputEl("author_page", j.author_page);
        const twitterInput = inputEl("twitter", j.twitter);
        const phoneInput = inputEl("phone", j.phone);
        const priorityInput = inputEl("priority", j.priority);
        const mainTopicInput = inputEl("main_topic", j.main_topic);
        const notesInput = el("textarea", { name: "notes" }, j.notes || "");

        const topicsContainer = el("div", { class: "ppn-chip-input" });
        const campaignsContainer = el("div", { class: "ppn-chip-input" });

        const grid = el("div", { class: "ppn-form-grid" },
            field("Email", emailInput, true, "err-email"),
            field("Market", marketSel, true, "err-market"),
            field("Nome", firstNameInput),
            field("Cognome", lastNameInput),
            field("Ruolo", jobInput),
            field("Priority", priorityInput),
            field("Publisher", pubNameInput),
            field("Domain", pubDomInput),
            field("Email type", emailTypeInput),
            field("Email status", emailStatusInput),
            field("Response status", responseStatusInput),
            field("Main topic", mainTopicInput),
            field("LinkedIn URL", linkedinInput),
            field("Author page URL", authorInput),
            field("Twitter URL", twitterInput),
            field("Phone", phoneInput),
            el("div", { class: "ppn-form-field full" },
                el("label", {}, "Topics"),
                topicsContainer,
                el("div", { class: "ppn-form-err" })
            ),
            el("div", { class: "ppn-form-field full" },
                el("label", {}, "Campagne"),
                campaignsContainer,
                el("div", { class: "ppn-form-err" })
            ),
            el("div", { class: "ppn-form-field full" },
                el("label", {}, "Note"),
                notesInput,
                el("div", { class: "ppn-form-err" })
            )
        );

        const body = el("div", { class: "ppn-form-body" }, errTop, grid);

        const saveBtn = el("button", { class: "ppn-btn ppn-btn-primary", onclick: submit }, isEdit ? "Salva" : "Crea");
        const cancelBtn = el("button", { class: "ppn-btn ppn-btn-secondary", onclick: close }, "Annulla");
        const delBtn = isEdit ? el("button", { class: "ppn-btn ppn-btn-danger", onclick: delJournalist }, "Elimina") : null;

        const footer = el("div", { class: "ppn-form-footer" },
            delBtn,
            el("div", { class: "spacer" }),
            cancelBtn,
            saveBtn
        );

        box.appendChild(header);
        box.appendChild(body);
        box.appendChild(footer);
        modal.appendChild(backdrop);
        modal.appendChild(box);
        backdrop.addEventListener("click", close);
        document.body.appendChild(modal);

        const topicsChips = chipInput(topicsContainer, j.topics || [], topicsPool);
        const campaignsChips = chipInput(campaignsContainer, j.campaigns || [], campaignsPool);

        setTimeout(() => emailInput.focus(), 50);

        function close() { modal.remove(); }

        function clearErrors() {
            errTop.style.display = "none";
            errTop.textContent = "";
            box.querySelectorAll(".ppn-form-err").forEach(e => e.textContent = "");
        }

        function showErr(field, msg, general) {
            if (general) {
                errTop.textContent = msg;
                errTop.style.display = "block";
                return;
            }
            const errEl = box.querySelector(`#err-${field}`);
            if (errEl) errEl.textContent = msg;
            else { errTop.textContent = `${field}: ${msg}`; errTop.style.display = "block"; }
        }

        async function submit() {
            clearErrors();
            saveBtn.disabled = true;
            saveBtn.textContent = "Salvataggio...";

            const payload = {
                email: emailInput.value.trim(),
                market: marketSel.value,
                first_name: firstNameInput.value.trim(),
                last_name: lastNameInput.value.trim(),
                job_title: jobInput.value.trim(),
                publisher_name: pubNameInput.value.trim(),
                publisher_domain: pubDomInput.value.trim(),
                email_type: emailTypeInput.value.trim(),
                email_status: emailStatusInput.value.trim(),
                response_status: responseStatusInput.value.trim(),
                linkedin: linkedinInput.value.trim(),
                author_page: authorInput.value.trim(),
                twitter: twitterInput.value.trim(),
                phone: phoneInput.value.trim(),
                priority: priorityInput.value.trim(),
                main_topic: mainTopicInput.value.trim(),
                notes: notesInput.value.trim(),
                topics: topicsChips.get(),
                campaigns: campaignsChips.get(),
            };

            try {
                const path = isEdit ? `/api/journalists/${j.id}` : "/api/journalists";
                const method = isEdit ? "PATCH" : "POST";
                const r = await window.PPN_API.fetch(path, {
                    method,
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await r.json();
                if (!r.ok) {
                    const f = data.field;
                    const msg = data.message || "Errore sconosciuto";
                    if (f) showErr(f, msg);
                    else showErr(null, msg, true);
                    saveBtn.disabled = false;
                    saveBtn.textContent = isEdit ? "Salva" : "Crea";
                    return;
                }
                close();
                toast(isEdit ? "Giornalista aggiornato" : "Giornalista creato", "ok");
                setTimeout(() => location.reload(), 600);
            } catch (e) {
                showErr(null, `Errore di rete: ${e.message}`, true);
                saveBtn.disabled = false;
                saveBtn.textContent = isEdit ? "Salva" : "Crea";
            }
        }

        async function delJournalist() {
            if (!confirm(`Eliminare ${j.email}? (soft delete, recuperabile da admin)`)) return;
            delBtn.disabled = true;
            delBtn.textContent = "Eliminazione...";
            try {
                const r = await window.PPN_API.fetch(`/api/journalists/${j.id}`, { method: "DELETE" });
                if (!r.ok) {
                    const d = await r.json().catch(() => ({}));
                    showErr(null, d.message || `Errore ${r.status}`, true);
                    delBtn.disabled = false;
                    delBtn.textContent = "Elimina";
                    return;
                }
                close();
                toast("Giornalista eliminato", "ok");
                setTimeout(() => location.reload(), 600);
            } catch (e) {
                showErr(null, `Errore di rete: ${e.message}`, true);
                delBtn.disabled = false;
                delBtn.textContent = "Elimina";
            }
        }
    }

    // ── Publisher form ────────────────────────────────────────────
    const SCOPES = ["", "national", "european", "global"];

    function buildPublisherForm(pub) {
        const isEdit = !!pub;
        const p = pub || {};

        const modal = el("div", { id: "ppn-form-modal", style: "display:block" });
        const backdrop = el("div", { class: "ppn-form-backdrop" });
        const box = el("div", { class: "ppn-form-box" });

        const errTop = el("div", { class: "ppn-form-err-top" });

        const header = el("div", { class: "ppn-form-header" },
            el("h2", {}, isEdit ? `Modifica publisher #${p.id}` : "Aggiungi publisher"),
            el("button", { class: "ppn-form-close", onclick: close }, "\u00d7")
        );

        function field(label, input, required, errId) {
            return el("div", { class: "ppn-form-field" },
                el("label", {}, label, required ? el("span", { class: "req" }, " *") : null),
                input,
                el("div", { class: "ppn-form-err", id: errId || "" })
            );
        }

        function inputEl(name, value, type) {
            return el("input", { type: type || "text", name, value: value == null ? "" : String(value) });
        }

        function selectEl(name, value, options) {
            const s = el("select", { name });
            options.forEach(o => {
                const opt = el("option", { value: o }, o || "—");
                if (o === value) opt.setAttribute("selected", "selected");
                s.appendChild(opt);
            });
            return s;
        }

        const nameInput = inputEl("name", p.name);
        const marketSel = selectEl("market", p.market, ["", ...MARKETS]);
        const domainInput = inputEl("domain", p.domain);
        const drInput = inputEl("dr", p.dr, "number");
        drInput.setAttribute("min", "0");
        drInput.setAttribute("max", "100");
        const scopeSel = selectEl("publisher_scope", p.publisher_scope, SCOPES);
        const mediaGroupInput = inputEl("media_group", p.media_group);
        const mediaTypeInput = inputEl("media_type", p.media_type);
        const regionInput = inputEl("region", p.region);

        const grid = el("div", { class: "ppn-form-grid" },
            field("Nome testata", nameInput, true, "err-name"),
            field("Market", marketSel, true, "err-market"),
            field("Domain", domainInput),
            field("DR (0-100)", drInput),
            field("Scope", scopeSel),
            field("Regione", regionInput),
            field("Media group", mediaGroupInput),
            field("Media type", mediaTypeInput)
        );

        const body = el("div", { class: "ppn-form-body" }, errTop, grid);

        const saveBtn = el("button", { class: "ppn-btn ppn-btn-primary", onclick: submit }, isEdit ? "Salva" : "Crea");
        const cancelBtn = el("button", { class: "ppn-btn ppn-btn-secondary", onclick: close }, "Annulla");
        const delBtn = isEdit ? el("button", { class: "ppn-btn ppn-btn-danger", onclick: delPub }, "Elimina") : null;

        const footer = el("div", { class: "ppn-form-footer" },
            delBtn,
            el("div", { class: "spacer" }),
            cancelBtn,
            saveBtn
        );

        box.appendChild(header);
        box.appendChild(body);
        box.appendChild(footer);
        modal.appendChild(backdrop);
        modal.appendChild(box);
        backdrop.addEventListener("click", close);
        document.body.appendChild(modal);
        setTimeout(() => nameInput.focus(), 50);

        function close() { modal.remove(); }

        function clearErrors() {
            errTop.style.display = "none";
            errTop.textContent = "";
            box.querySelectorAll(".ppn-form-err").forEach(e => e.textContent = "");
        }

        function showErr(fld, msg, general) {
            if (general) {
                errTop.textContent = msg;
                errTop.style.display = "block";
                return;
            }
            const errEl = box.querySelector(`#err-${fld}`);
            if (errEl) errEl.textContent = msg;
            else { errTop.textContent = `${fld}: ${msg}`; errTop.style.display = "block"; }
        }

        async function submit() {
            clearErrors();
            saveBtn.disabled = true;
            saveBtn.textContent = "Salvataggio...";
            const payload = {
                name: nameInput.value.trim(),
                market: marketSel.value,
                domain: domainInput.value.trim(),
                dr: drInput.value.trim(),
                publisher_scope: scopeSel.value,
                media_group: mediaGroupInput.value.trim(),
                media_type: mediaTypeInput.value.trim(),
                region: regionInput.value.trim(),
            };
            try {
                const path = isEdit ? `/api/publishers/${p.id}` : "/api/publishers";
                const method = isEdit ? "PATCH" : "POST";
                const r = await window.PPN_API.fetch(path, {
                    method,
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await r.json();
                if (!r.ok) {
                    if (data.field) showErr(data.field, data.message || "Errore");
                    else showErr(null, data.message || `Errore ${r.status}`, true);
                    saveBtn.disabled = false;
                    saveBtn.textContent = isEdit ? "Salva" : "Crea";
                    return;
                }
                close();
                toast(isEdit ? "Publisher aggiornato" : "Publisher creato", "ok");
                setTimeout(() => location.reload(), 600);
            } catch (e) {
                showErr(null, `Errore di rete: ${e.message}`, true);
                saveBtn.disabled = false;
                saveBtn.textContent = isEdit ? "Salva" : "Crea";
            }
        }

        async function delPub() {
            if (!confirm(`Eliminare "${p.name}" (${p.market})? I giornalisti collegati resteranno ma senza publisher.`)) return;
            delBtn.disabled = true;
            delBtn.textContent = "Eliminazione...";
            try {
                const r = await window.PPN_API.fetch(`/api/publishers/${p.id}`, { method: "DELETE" });
                if (!r.ok) {
                    const d = await r.json().catch(() => ({}));
                    showErr(null, d.message || `Errore ${r.status}`, true);
                    delBtn.disabled = false;
                    delBtn.textContent = "Elimina";
                    return;
                }
                close();
                toast("Publisher eliminato", "ok");
                setTimeout(() => location.reload(), 600);
            } catch (e) {
                showErr(null, `Errore di rete: ${e.message}`, true);
                delBtn.disabled = false;
                delBtn.textContent = "Elimina";
            }
        }
    }

    async function openPublisherEdit(name, market) {
        try {
            const r = await window.PPN_API.fetch(`/api/publishers?search=${encodeURIComponent(name)}&market=${market}&limit=50`);
            if (!r.ok) { toast(`Errore ${r.status}`, "err"); return; }
            const data = await r.json();
            const match = (data.publishers || []).find(p => (p.name || "").trim().toLowerCase() === name.trim().toLowerCase() && p.market === market);
            if (!match) { toast("Publisher non trovato via API", "err"); return; }
            buildPublisherForm(match);
        } catch (e) { toast(`Errore: ${e.message}`, "err"); }
    }

    // ── Campaign manager + form ───────────────────────────────────
    function buildCampaignForm(camp) {
        const isEdit = !!camp;
        const c = camp || {};

        const modal = el("div", { id: "ppn-form-modal", style: "display:block" });
        const backdrop = el("div", { class: "ppn-form-backdrop" });
        const box = el("div", { class: "ppn-form-box" });

        const errTop = el("div", { class: "ppn-form-err-top" });
        const header = el("div", { class: "ppn-form-header" },
            el("h2", {}, isEdit ? `Modifica campagna #${c.id}` : "Aggiungi campagna"),
            el("button", { class: "ppn-form-close", onclick: close }, "\u00d7")
        );

        function field(label, input, required, errId) {
            return el("div", { class: "ppn-form-field" },
                el("label", {}, label, required ? el("span", { class: "req" }, " *") : null),
                input,
                el("div", { class: "ppn-form-err", id: errId || "" })
            );
        }

        const nameInput = el("input", { type: "text", value: c.name || "" });
        const marketSel = el("select", {});
        ["", ...MARKETS].forEach(m => {
            const o = el("option", { value: m }, m || "—");
            if (m === c.market) o.setAttribute("selected", "selected");
            marketSel.appendChild(o);
        });
        if (isEdit) marketSel.disabled = true;
        const startInput = el("input", { type: "date", value: c.date_start || "" });
        const endInput = el("input", { type: "date", value: c.date_end || "" });

        const grid = el("div", { class: "ppn-form-grid" },
            field("Nome", nameInput, true, "err-name"),
            field("Market", marketSel, true, "err-market"),
            field("Data inizio", startInput),
            field("Data fine", endInput)
        );

        const body = el("div", { class: "ppn-form-body" }, errTop, grid);
        const saveBtn = el("button", { class: "ppn-btn ppn-btn-primary", onclick: submit }, isEdit ? "Salva" : "Crea");
        const cancelBtn = el("button", { class: "ppn-btn ppn-btn-secondary", onclick: close }, "Annulla");
        const delBtn = isEdit ? el("button", { class: "ppn-btn ppn-btn-danger", onclick: delCamp }, "Elimina") : null;
        const footer = el("div", { class: "ppn-form-footer" },
            delBtn,
            el("div", { class: "spacer" }),
            cancelBtn,
            saveBtn
        );

        box.appendChild(header);
        box.appendChild(body);
        box.appendChild(footer);
        modal.appendChild(backdrop);
        modal.appendChild(box);
        backdrop.addEventListener("click", close);
        document.body.appendChild(modal);
        setTimeout(() => nameInput.focus(), 50);

        function close() { modal.remove(); }

        function showErr(fld, msg, general) {
            if (general) { errTop.textContent = msg; errTop.style.display = "block"; return; }
            const errEl = box.querySelector(`#err-${fld}`);
            if (errEl) errEl.textContent = msg;
        }

        function clearErrors() {
            errTop.style.display = "none";
            errTop.textContent = "";
            box.querySelectorAll(".ppn-form-err").forEach(e => e.textContent = "");
        }

        async function submit() {
            clearErrors();
            saveBtn.disabled = true;
            saveBtn.textContent = "Salvataggio...";
            const payload = {
                name: nameInput.value.trim(),
                date_start: startInput.value.trim(),
                date_end: endInput.value.trim(),
            };
            if (!isEdit) payload.market = marketSel.value;
            try {
                const path = isEdit ? `/api/campaigns/${c.id}` : "/api/campaigns";
                const method = isEdit ? "PATCH" : "POST";
                const r = await window.PPN_API.fetch(path, {
                    method,
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await r.json();
                if (!r.ok) {
                    if (data.field) showErr(data.field, data.message || "Errore");
                    else showErr(null, data.message || `Errore ${r.status}`, true);
                    saveBtn.disabled = false;
                    saveBtn.textContent = isEdit ? "Salva" : "Crea";
                    return;
                }
                close();
                toast(isEdit ? "Campagna aggiornata" : "Campagna creata", "ok");
                setTimeout(() => location.reload(), 600);
            } catch (e) {
                showErr(null, `Errore di rete: ${e.message}`, true);
                saveBtn.disabled = false;
                saveBtn.textContent = isEdit ? "Salva" : "Crea";
            }
        }

        async function delCamp() {
            if (!confirm(`Eliminare campagna "${c.name}"? Soft delete, giornalisti linkati mantengono storico.`)) return;
            delBtn.disabled = true;
            delBtn.textContent = "Eliminazione...";
            try {
                const r = await window.PPN_API.fetch(`/api/campaigns/${c.id}`, { method: "DELETE" });
                if (!r.ok) {
                    const d = await r.json().catch(() => ({}));
                    showErr(null, d.message || `Errore ${r.status}`, true);
                    delBtn.disabled = false;
                    delBtn.textContent = "Elimina";
                    return;
                }
                close();
                toast("Campagna eliminata", "ok");
                setTimeout(() => location.reload(), 600);
            } catch (e) {
                showErr(null, `Errore di rete: ${e.message}`, true);
                delBtn.disabled = false;
                delBtn.textContent = "Elimina";
            }
        }
    }

    async function buildCampaignManager() {
        const modal = el("div", { id: "ppn-form-modal", style: "display:block" });
        const backdrop = el("div", { class: "ppn-form-backdrop" });
        const box = el("div", { class: "ppn-form-box" });
        const header = el("div", { class: "ppn-form-header" },
            el("h2", {}, "Gestione campagne"),
            el("button", { class: "ppn-form-close", onclick: close }, "\u00d7")
        );

        const listEl = el("div", { class: "ppn-form-body" }, el("div", {}, "Caricamento..."));

        const addBtn = el("button", {
            class: "ppn-btn ppn-btn-primary",
            onclick: () => { close(); buildCampaignForm(null); },
        }, "+ Nuova campagna");
        const closeBtn = el("button", { class: "ppn-btn ppn-btn-secondary", onclick: close }, "Chiudi");
        const footer = el("div", { class: "ppn-form-footer" },
            el("div", { class: "spacer" }),
            closeBtn,
            addBtn
        );

        box.appendChild(header);
        box.appendChild(listEl);
        box.appendChild(footer);
        modal.appendChild(backdrop);
        modal.appendChild(box);
        backdrop.addEventListener("click", close);
        document.body.appendChild(modal);

        function close() { modal.remove(); }

        try {
            const r = await window.PPN_API.fetch("/api/campaigns");
            if (!r.ok) { listEl.innerHTML = `<div style='color:#c0392b'>Errore ${r.status}</div>`; return; }
            const data = await r.json();
            const camps = data.campaigns || [];
            if (!camps.length) {
                listEl.innerHTML = "<div style='color:#666'>Nessuna campagna.</div>";
                return;
            }
            listEl.innerHTML = "";
            const table = el("table", { class: "ppn-camp-table" });
            table.innerHTML = `<thead><tr><th>Nome</th><th>Market</th><th>Inizio</th><th>Fine</th><th>Giornalisti</th><th></th></tr></thead>`;
            const tbody = el("tbody", {});
            camps.forEach(c => {
                const tr = el("tr", {},
                    el("td", {}, c.name || ""),
                    el("td", {}, c.market || ""),
                    el("td", {}, c.date_start || "—"),
                    el("td", {}, c.date_end || "—"),
                    el("td", {}, String(c.journalists_count || 0))
                );
                const editCell = el("td", {},
                    el("button", {
                        class: "ppn-row-edit-btn",
                        onclick: () => { close(); buildCampaignForm(c); },
                    }, "Modifica")
                );
                tr.appendChild(editCell);
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            listEl.appendChild(table);
        } catch (e) {
            listEl.innerHTML = `<div style='color:#c0392b'>Errore: ${e.message}</div>`;
        }
    }

    // ── FABs per tab ──────────────────────────────────────────────
    function injectFAB() {
        if (document.getElementById("ppn-fab-journalist")) return;

        const fabJ = el("button", {
            id: "ppn-fab-journalist",
            class: "ppn-fab",
            onclick: () => buildForm(null),
        }, "+ Aggiungi giornalista");

        const fabC = el("button", {
            id: "ppn-fab-campaigns",
            class: "ppn-fab ppn-fab-secondary",
            onclick: () => buildCampaignManager(),
        }, "Campagne");

        const fabP = el("button", {
            id: "ppn-fab-publisher",
            class: "ppn-fab",
            onclick: () => buildPublisherForm(null),
        }, "+ Aggiungi publisher");

        document.body.appendChild(fabJ);
        document.body.appendChild(fabC);
        document.body.appendChild(fabP);

        function updateFabVisibility() {
            const dbActive = document.getElementById("page-database")?.classList.contains("active");
            const pubActive = document.getElementById("page-publishers")?.classList.contains("active");
            fabJ.style.display = dbActive ? "block" : "none";
            fabC.style.display = dbActive ? "block" : "none";
            fabP.style.display = pubActive ? "block" : "none";
        }
        updateFabVisibility();

        document.querySelectorAll(".topbar-nav button").forEach(btn => {
            btn.addEventListener("click", () => setTimeout(updateFabVisibility, 10));
        });
    }

    function injectRowEdit() {
        const tbody = document.getElementById("table-body");
        if (!tbody) return;

        function decorate() {
            const filtered = (window.DASHBOARD_DATA?.journalists || []);
            // Re-derive same sort order used by dashboard IIFE isn't available.
            // Use data-idx mapping through email/title in detail card to find journalist.
            tbody.querySelectorAll(".detail-row").forEach(detailRow => {
                if (detailRow.querySelector(".ppn-row-actions")) return;
                const card = detailRow.querySelector(".detail-card");
                if (!card) return;
                const emailLink = detailRow.querySelector('a[href^="mailto:"]');
                if (!emailLink) return;
                const email = emailLink.textContent.trim();
                const journalist = filtered.find(x => (x.email || "").trim().toLowerCase() === email.toLowerCase());
                if (!journalist) return;
                const actions = el("div", { class: "ppn-row-actions" },
                    el("button", {
                        class: "ppn-row-edit-btn",
                        onclick: (e) => { e.stopPropagation(); buildForm(journalist); }
                    }, "Modifica"),
                    el("button", {
                        class: "ppn-row-del-btn",
                        onclick: async (e) => {
                            e.stopPropagation();
                            if (!confirm(`Eliminare ${journalist.email}?`)) return;
                            try {
                                const r = await window.PPN_API.fetch(`/api/journalists/${journalist.id}`, { method: "DELETE" });
                                if (r.ok) { toast("Eliminato", "ok"); setTimeout(() => location.reload(), 500); }
                                else { const d = await r.json().catch(() => ({})); toast(d.message || `Errore ${r.status}`, "err"); }
                            } catch (err) { toast(`Errore: ${err.message}`, "err"); }
                        }
                    }, "Elimina")
                );
                card.appendChild(actions);
            });
        }

        const obs = new MutationObserver(() => decorate());
        obs.observe(tbody, { childList: true, subtree: false });
        decorate();
    }

    function injectPubCardActions() {
        const grid = document.getElementById("pub-grid");
        if (!grid) return;

        function decorate() {
            grid.querySelectorAll(".pub-card").forEach(card => {
                if (card.querySelector(".ppn-pub-actions")) return;
                const nameEl = card.querySelector(".pub-card-name");
                const marketPill = card.querySelector(".market-pill");
                if (!nameEl || !marketPill) return;

                const nameClone = nameEl.cloneNode(true);
                nameClone.querySelectorAll("span").forEach(s => s.remove());
                const name = nameClone.textContent.trim();

                let market = "";
                for (const c of marketPill.classList) {
                    if (["it", "es", "fr"].includes(c)) { market = c.toUpperCase(); break; }
                }
                if (!name || !market) return;

                const actions = el("div", { class: "ppn-pub-actions", style: "margin-top:12px; padding-top:12px; border-top:1px dashed #e5e7eb; display:flex; gap:8px;" },
                    el("button", {
                        class: "ppn-row-edit-btn",
                        onclick: (e) => { e.stopPropagation(); openPublisherEdit(name, market); }
                    }, "Modifica"),
                    el("button", {
                        class: "ppn-row-del-btn",
                        onclick: async (e) => {
                            e.stopPropagation();
                            if (!confirm(`Eliminare publisher "${name}" (${market})?`)) return;
                            try {
                                const r = await window.PPN_API.fetch(`/api/publishers?search=${encodeURIComponent(name)}&market=${market}&limit=50`);
                                if (!r.ok) { toast(`Errore ${r.status}`, "err"); return; }
                                const data = await r.json();
                                const match = (data.publishers || []).find(p => (p.name || "").trim().toLowerCase() === name.toLowerCase() && p.market === market);
                                if (!match) { toast("Non trovato", "err"); return; }
                                const d = await window.PPN_API.fetch(`/api/publishers/${match.id}`, { method: "DELETE" });
                                if (d.ok) { toast("Publisher eliminato", "ok"); setTimeout(() => location.reload(), 500); }
                                else { const err = await d.json().catch(() => ({})); toast(err.message || `Errore ${d.status}`, "err"); }
                            } catch (err) { toast(`Errore: ${err.message}`, "err"); }
                        }
                    }, "Elimina")
                );
                card.appendChild(actions);
            });
        }

        const obs = new MutationObserver(() => decorate());
        obs.observe(grid, { childList: true, subtree: false });
        decorate();
    }

    function boot() {
        injectCSS();
        injectFAB();
        injectRowEdit();
        injectPubCardActions();
    }

    if (window.DASHBOARD_DATA && document.getElementById("table-body")) boot();
    else window.addEventListener("dashboard:ready", boot, { once: true });
})();
