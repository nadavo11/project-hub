const hubAgentIdentity = (() => {
    const EMOJI = ['🦊','🐙','🦉','🐳','🦄','🐲','🦖','🐼','🦩','🐸','🦔','🐝','🦋','🐧','🦝','🐯','🦜','🐢','🦦','🐨','👾','🛸','🧙','🧚'];
    const ACTOR = /^agent-([0-9a-f]{8})$/;
    function look(short) {
        let h = 2166136261, g = 0x9e3779b9;
        for (const c of short) { h = Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0; g = Math.imul(g ^ c.charCodeAt(0), 2246822519) >>> 0; }
        return { emoji: EMOJI[h % EMOJI.length], hue: h % 360, seed: h.toString(36) + g.toString(36) };
    }
    function avatar(short, className = 'msg-avatar') {
        const v = look(short), box = document.createElement('span');
        box.className = className; box.textContent = v.emoji; box.setAttribute('aria-hidden', 'true');
        box.style.background = `linear-gradient(145deg, hsl(${v.hue} 80% 65%), hsl(${(v.hue + 60) % 360} 80% 75%))`;
        const img = document.createElement('img');
        img.className = 'msg-avatar-img'; img.alt = ''; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer';
        img.onload = () => { box.textContent = ''; box.append(img); };
        img.src = `https://api.dicebear.com/9.x/thumbs/svg?seed=${encodeURIComponent(v.seed)}`;
        return box;
    }
    const actorShort = actor => ACTOR.exec(actor || '')?.[1] || '';
    const name = short => `Agent ${short}`;
    return { avatar, actorShort, name };
})();

const hubAgents = (() => {
    let disposeCurrent = () => {};
    const selections = new Map();
    let drafts = {};
    try { drafts = JSON.parse(sessionStorage.getItem('hub:agent-drafts') || '{}'); } catch { /* Optional draft recovery. */ }

    function node(tag, className = '', content = '') {
        const element = document.createElement(tag);
        element.className = className;
        element.textContent = content;
        return element;
    }
    function button(label, action, className = 'btn') {
        const element = node('button', className, label);
        element.type = 'button';
        element.addEventListener('click', action);
        return element;
    }
    function input(label, placeholder, limit) {
        const element = node('input');
        element.setAttribute('aria-label', label);
        element.placeholder = placeholder;
        element.maxLength = limit;
        return element;
    }
    function saveDrafts() {
        try { sessionStorage.setItem('hub:agent-drafts', JSON.stringify(drafts)); return true; }
        catch { return false; }
    }

    function mount(main, channel) {
        disposeCurrent();
        let disposed = false, opened = false, authenticated = false, authKnown = false, busy = false;
        let selected = selections.get(channel.id) || null, channelState = null, threadState = null;
        let sending = false, creating = false, lastThread = null;
        let authVersion = 0;
        const abort = new AbortController();
        const messageRows = new Map(), eventRows = new Map(), threadTabs = new Map();
        const modes = node('div', 'chat-modes');
        const tabs = node('div', 'chat-tabs');
        tabs.setAttribute('role', 'tablist');
        tabs.setAttribute('aria-label', 'Channel chats');
        const shared = button('Shared', () => show(false), 'chat-tab');
        shared.id = 'sharedChatTab';
        shared.setAttribute('role', 'tab');
        shared.setAttribute('aria-controls', 'sharedChatPanel');
        shared.setAttribute('aria-selected', 'true');
        tabs.append(shared);
        modes.append(tabs);
        main.querySelector('.pane-head').after(modes);
        const panel = node('section', 'agent-panel');
        panel.id = 'agentChatPanel';
        panel.setAttribute('role', 'tabpanel');
        panel.hidden = true;
        const error = node('p', 'agent-error');
        error.setAttribute('role', 'alert');
        error.hidden = true;
        function fail(message) { error.textContent = message; error.hidden = !message; }
        const locked = node('form', 'agent-unlock');
        const key = input('Operator key', 'Paste your operator key', 200);
        key.type = 'password';
        key.autocomplete = 'off';
        const unlock = node('button', 'btn btn-primary', 'Unlock Agent chat');
        unlock.type = 'submit';
        const unlockNote = node('p', '', 'Private to operator-key holders. Agents act with full user permissions.');
        unlockNote.title = 'Use HTTPS or an SSH tunnel; plain HTTP does not protect your key or conversations.';
        locked.append(node('h3', '', 'Agent chat'), unlockNote, key, unlock);
        const content = node('div', 'agent-content');
        content.hidden = true;
        const toggle = button('Enable AI', async () => {
            if (!channelState) return;
            toggle.disabled = true;
            try {
                await api(`channels/${channel.id}`, 'PATCH', { enabled: !channelState.enabled });
                fail(''); await refresh();
            } catch (e) { fail(e.message); }
            finally { toggle.disabled = false; }
        });
        toggle.setAttribute('role', 'switch');
        toggle.setAttribute('aria-label', 'AI for this channel');
        toggle.setAttribute('aria-checked', 'false');
        toggle.title = 'Full user permissions · Each thread keeps its own context · Copilot usage is billed normally';
        let service = '';
        const lockButton = button('Lock', async () => {
            try {
                await api('session', 'DELETE');
                drafts = {}; saveDrafts();
                lock();
            } catch (e) { fail(e.message); }
        }, 'link-btn');
        const toolbar = node('div', 'agent-channel-controls');
        toolbar.hidden = true;
        const newButton = button('+ New', () => {
            creating = true;
            selected = null; threadState = null;
            history.replaceState(null, '', `#chat/${channel.id}`);
            show(true);
            if (authenticated) { title.focus(); loadModels(); }
            else key.focus();
        });
        newButton.id = 'newAgentChat';
        newButton.setAttribute('aria-controls', panel.id);
        newButton.title = 'New private agent chat';
        const lockHint = button('🔒 Private chats', () => { creating = false; show(true); key.focus(); }, 'btn chat-lock-hint');
        lockHint.hidden = true;
        lockHint.title = 'Private agent chat tabs are hidden until you unlock with the operator key';
        lockHint.setAttribute('aria-controls', panel.id);
        const archiveMenu = node('details', 'chat-archive');
        archiveMenu.hidden = true;
        const archiveSummary = node('summary', 'chat-archive-toggle');
        archiveSummary.setAttribute('aria-label', 'Archived chats');
        archiveSummary.title = 'Archived chats';
        archiveSummary.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M3 5h18v4H3zM5 9v10h14V9M10 13h4"/></svg>';
        const archiveCount = node('span', 'badge');
        archiveSummary.append(archiveCount);
        const archivePopover = node('div', 'chat-archive-pop');
        const archiveHead = node('div', 'chat-archive-head', 'Archived chats');
        const archiveList = node('div', 'chat-archive-list');
        archivePopover.append(archiveHead, archiveList);
        archiveMenu.append(archiveSummary, archivePopover);
        document.addEventListener('click', event => { if (!archiveMenu.contains(event.target)) archiveMenu.open = false; }, { signal: abort.signal });
        archiveMenu.addEventListener('keydown', event => { if (event.key === 'Escape') { archiveMenu.open = false; archiveSummary.focus(); } });
        async function setArchived(id, archived) {
            try {
                await api(`threads/${id}`, 'PATCH', { archived });
                fail('');
                if (archived && id === selected && opened) { selected = null; selections.delete(channel.id); show(false); }
                await refresh();
            } catch (e) { fail(e.message); }
        }
        modes.append(lockHint, newButton, archiveMenu);
        const newForm = node('form', 'agent-new-thread');
        newForm.hidden = true;
        const title = input('New thread title', 'What are we working on?', 120);
        title.required = true;
        const create = node('button', 'btn btn-primary', 'Create thread');
        create.type = 'submit';
        const modelSelect = node('select', 'agent-model');
        modelSelect.setAttribute('aria-label', 'Model');
        modelSelect.append(new Option('Default model', ''));
        let modelNames = new Map(), defaultModel = '', modelsFailedAt = 0;
        modelSelect.disabled = true;
        let modelsLoaded = false;
        async function loadModels() {
            if (modelsLoaded || Date.now() - modelsFailedAt < 30000) return;
            modelSelect.options[0].textContent = 'Loading models…';
            try {
                const { models } = await api('models');
                const current = modelSelect.value;
                modelNames = new Map(models.map(model => [model.id, model.name]));
                defaultModel = models.find(model => model.default)?.name || '';
                modelSelect.replaceChildren(new Option(defaultModel ? `Default (${defaultModel})` : 'Default model', ''));
                for (const model of models) {
                    modelSelect.append(new Option(model.cost ? `${model.name} — ${model.cost} cost` : model.name, model.id));
                }
                updateModelChip();
                modelSelect.value = current;
                modelsLoaded = true;
            } catch (e) {
                modelsFailedAt = Date.now();
                modelSelect.options[0].textContent = 'Default model';
                if (e.name !== 'AbortError' && creating) fail('Model list unavailable: ' + e.message);
            }
            modelSelect.disabled = false;
        }
        newForm.append(title, modelSelect, create);
        const modelChip = node('div', 'agent-model-chip');
        modelChip.hidden = true;
        function agentLabel(thread) {
            const model = thread.model ? (modelNames.get(thread.model) || thread.model) : defaultModel || 'default model';
            return `Agent #${thread.id} · ${model} · ${thread.session_id.slice(0, 8)}`;
        }
        function updateModelChip() {
            const id = threadState?.thread.model;
            const name = id ? (modelNames.get(id) || id) : defaultModel ? `${defaultModel} (default)` : 'Default model';
            const project = threadState?.thread.project;
            modelChip.textContent = `Model: ${name}`;
            if (project && window.HubProjects) modelChip.append(' · ', window.HubProjects.badge(project));
            if (threadState) modelChip.title = `Owned by ${agentLabel(threadState.thread)}. Resume in Copilot CLI: copilot --resume=${threadState.thread.session_id}`;
            modelChip.hidden = !threadState;
            message.placeholder = `Message the agent (${id ? (modelNames.get(id) || id) : defaultModel || 'default model'})…`;
        }
        const threadControls = node('div', 'agent-thread-controls');
        const state = node('span', 'agent-run-state');
        state.setAttribute('role', 'status');
        const stop = button('Stop', async () => {
            try { await api(`threads/${selected}/stop`, 'POST', {}); fail(''); await refresh(); }
            catch (e) { fail(e.message); }
        }, 'btn danger');
        const close = button('Close thread', async () => {
            if (!threadState) return;
            try {
                await api(`threads/${selected}`, 'PATCH', { closed: !threadState.thread.closed });
                fail(''); await refresh();
            } catch (e) { fail(e.message); }
        }, 'link-btn');
        const more = node('details', 'agent-more');
        const moreSummary = node('summary', '', '⋯');
        moreSummary.setAttribute('aria-label', 'More options');
        const moreMenu = node('div', 'agent-more-menu');
        moreMenu.append(close, lockButton);
        more.append(moreSummary, moreMenu);
        more.addEventListener('click', event => { if (event.target.closest('.agent-more-menu')) more.open = false; });
        toolbar.append(toggle, more);
        main.querySelector('.pane-head').append(toolbar);
        threadControls.append(state, stop);
        threadControls.hidden = true;
        const log = node('div', 'agent-log');
        log.tabIndex = 0;
        log.setAttribute('aria-label', 'Agent thread conversation and activity');
        const empty = node('p', 'agent-empty', 'Start a thread to begin.');
        const messages = node('div', 'agent-messages');
        const blocks = new Map();
        function activityBlock(jobId) {
            let block = blocks.get(jobId);
            if (block) return block;
            const el = node('details', 'agent-activity');
            const summary = node('summary', 'thought-summary');
            const orb = node('span', 'thought-orb');
            orb.setAttribute('aria-hidden', 'true');
            const chevron = node('span', 'thought-chevron', '›');
            chevron.setAttribute('aria-hidden', 'true');
            block = { el, title: node('span', 'thought-title', 'Thought process'), step: node('span', 'thought-step'),
                count: node('span', 'thought-count'), events: node('div', 'agent-events'), rows: new Map() };
            summary.append(orb, block.title, block.step, block.count, chevron);
            summary.setAttribute('aria-live', 'polite');
            el.append(summary, block.events);
            el.hidden = true;
            blocks.set(jobId, block);
            return block;
        }
        const older = button('Load earlier activity', async () => {
            const first = Math.min(...eventRows.keys());
            try {
                const id = selected;
                const history = await api(`threads/${id}?before=${first}`);
                if (id !== selected) return;
                renderEvents(history.events);
                older.hidden = !history.has_older_events;
                layoutActivity(threadState?.jobs || []);
            } catch (e) { fail(e.message); }
        }, 'link-btn');
        older.hidden = true;
        log.append(empty, older, messages);
        const form = node('form', 'agent-composer');
        const message = node('textarea');
        message.setAttribute('aria-label', 'Message agent');
        message.placeholder = 'Message the agent…';
        message.rows = 2;
        message.maxLength = 16000;
        const send = node('button', 'btn btn-primary', 'Send');
        send.type = 'submit';
        form.append(window.hubWithEmoji ? window.hubWithEmoji(message) : message, send);
        content.append(newForm, threadControls, modelChip, log, form);
        panel.append(error, locked, content);
        main.append(panel);

        async function api(path, method = 'GET', body) {
            const response = await fetch('/api/agents/' + path, {
                method, credentials: 'same-origin', signal: AbortSignal.any([abort.signal, AbortSignal.timeout(15000)]),
                ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
            });
            const data = await response.json();
            if (disposed) throw new DOMException('Panel closed', 'AbortError');
            if (!response.ok) {
                if (response.status === 401 && path !== 'session') lock();
                throw new Error(data.error || `Request failed (${response.status}).`);
            }
            return data;
        }
        function lock() {
            const wasAuthenticated = authenticated;
            authVersion++;
            authenticated = false; authKnown = true;
            locked.hidden = false; content.hidden = true;
            clearTimeline(); lastThread = null;
            threadState = null; channelState = null;
            if (wasAuthenticated) key.value = '';
            message.value = '';
            for (const tab of threadTabs.values()) tab.parentElement.remove();
            threadTabs.clear();
            archiveList.replaceChildren(); archiveMenu.hidden = true; archiveMenu.open = false;
            state.textContent = ''; threadControls.hidden = true;
            updateView();
        }
        function updateView() {
            shared.setAttribute('aria-selected', String(!opened));
            shared.tabIndex = !opened || creating || !authenticated ? 0 : -1;
            for (const [id, tab] of threadTabs) {
                const active = opened && !creating && id === selected;
                tab.setAttribute('aria-selected', String(active));
                tab.tabIndex = active ? 0 : -1;
            }
            panel.setAttribute('aria-labelledby', threadTabs.get(selected)?.id || newButton.id);
            toolbar.hidden = !opened || !authenticated;
            lockHint.hidden = authenticated || !authKnown;
            newForm.hidden = !creating;
            log.hidden = creating || !selected;
            form.hidden = creating || !selected;
            if (creating) threadControls.hidden = true;
            updateSend();
        }
        function show(on) {
            opened = on;
            main.dataset.agentMode = String(on);
            panel.hidden = !on;
            main.querySelector('.shared-chat-panel').hidden = on;
            updateView();
            if (on) refresh();
            else if (location.hash.includes('/thread/')) history.replaceState(null, '', `#chat/${channel.id}`);
        }
        function choose(id) {
            creating = false;
            selected = Number(id);
            selections.set(channel.id, selected);
            history.replaceState(null, '', `#chat/${channel.id}/thread/${selected}`);
            message.value = drafts[selected]?.text || '';
            threadState = null; lastThread = null;
            clearTimeline();
            threadControls.hidden = true; modelChip.hidden = true; empty.hidden = false;
            message.readOnly = !!drafts[selected]?.nonce;
            show(true);
            revealActiveTab();
        }
        const INDICATORS = {
            working: ['Working', '⏳'], done: ['Done', '✓'], waiting: ['Waiting for your input', '?'], error: ['Error', '!'],
        };
        function threadIndicator(thread) { return thread.indicator || ''; }
        function revealActiveTab() {
            if (opened && !creating) {
                threadTabs.get(selected)?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
            }
        }
        tabs.addEventListener('keydown', event => {
            if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            const items = [...tabs.querySelectorAll('.chat-tab')];
            const current = items.indexOf(document.activeElement);
            if (current < 0) return;
            event.preventDefault();
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
                : (current + (event.key === 'ArrowRight' ? 1 : -1) + items.length) % items.length;
            items[next].focus();
            items[next].click();
        });
        locked.addEventListener('submit', async event => {
            event.preventDefault();
            unlock.disabled = true;
            try {
                await api('session', 'POST', { key: key.value });
                authVersion++;
                key.value = ''; authenticated = true; fail(''); await refresh();
                if (creating) { title.focus(); loadModels(); }
            } catch (e) { fail(e.message); }
            finally { unlock.disabled = false; }
        });
        newForm.addEventListener('submit', async event => {
            event.preventDefault();
            create.disabled = true;
            try {
                const thread = await api(`channels/${channel.id}/threads`, 'POST', { title: title.value, model: modelSelect.value });
                fail(''); title.value = ''; newForm.hidden = true;
                choose(thread.id);
            } catch (e) { fail(e.message); }
            finally { create.disabled = false; }
        });
        message.addEventListener('input', () => {
            if (!selected) return;
            drafts[selected] = { text: message.value };
            if (!saveDrafts()) fail('Draft storage is unavailable. Keep this page open until your message is confirmed.');
            updateSend();
        });
        message.addEventListener('keydown', event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
                event.preventDefault(); form.requestSubmit();
            }
        });
        function updateSend() {
            const canSend = authenticated && channelState?.enabled && threadState && !threadState.thread.closed;
            message.disabled = !canSend || sending;
            send.disabled = !canSend || sending || !message.value.trim();
            message.readOnly = !!drafts[selected]?.nonce;
            send.textContent = sending ? 'Sending…' : drafts[selected]?.nonce ? 'Retry' : 'Send';
        }
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (send.disabled) return;
            const id = selected;
            const entry = drafts[id]?.nonce ? drafts[id] : {
                text: message.value, nonce: crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`,
            };
            drafts[id] = entry; saveDrafts(); sending = true; updateSend();
            try {
                await api(`threads/${id}/messages`, 'POST', entry);
                delete drafts[id]; saveDrafts();
                if (id === selected) message.value = '';
                fail('');
            } catch (e) {
                fail(`${e.message} Delivery was not confirmed. Retry uses the same request ID to avoid duplicate work.`);
            } finally {
                sending = false; updateSend(); refresh();
            }
        });
        function clearTimeline() {
            messages.replaceChildren(); messageRows.clear(); eventRows.clear(); blocks.clear();
        }
        function renderEvents(items) {
            for (const item of items) {
                if (eventRows.has(item.id)) continue;
                const block = activityBlock(item.job);
                const detail = node('details', 'agent-event');
                const label = item.kind.startsWith('tool.') ? item.kind.replace('tool.execution_', 'Tool ') : item.kind;
                let tool = '';
                if (item.kind.startsWith('tool.')) { try { tool = JSON.parse(item.text).toolName || ''; } catch { /* plain text */ } }
                const summary = node('summary', '', `${new Date(item.created * 1000).toLocaleTimeString()} · ${label}${tool ? ` · ${tool}` : ''}`);
                detail.dataset.kind = item.kind;
                detail.dataset.id = item.id;
                if (tool) detail.dataset.tool = tool;
                detail.append(summary, node('pre', '', item.text));
                eventRows.set(item.id, detail);
                block.rows.set(item.id, detail);
                const next = [...block.rows.keys()].filter(id => id > item.id).sort((a, b) => a - b)[0];
                block.events.insertBefore(detail, next ? block.rows.get(next) : null);
            }
        }
        const snippet = text => { const line = String(text).replace(/\s+/g, ' ').trim(); return line.length > 90 ? line.slice(0, 89) + '…' : line; };
        // Each turn's activity sits between its request and its reply, not at the bottom.
        function layoutActivity(jobs) {
            const running = new Set(jobs.filter(job => ['running', 'cancelling'].includes(job.status)).map(job => job.id));
            const reply = new Map(), request = new Map();
            for (const item of threadState.messages) {
                if (item.job == null) continue;
                (item.role === 'user' ? request : reply).set(item.job, messageRows.get(item.id));
            }
            for (const [jobId, block] of blocks) {
                const isRunning = running.has(jobId);
                const entries = [...block.rows.entries()].sort((a, b) => a[0] - b[0]);
                block.el.hidden = entries.length === 0;
                block.el.classList.toggle('is-working', isRunning);
                block.title.textContent = isRunning ? 'Thinking' : 'Thought process';
                block.count.textContent = entries.length ? `${entries.length} steps` : '';
                block.step.textContent = '';
                if (isRunning && entries.length) {
                    const latest = entries.at(-1)[1];
                    const note = [...entries].reverse().find(([, row]) => row.dataset.kind === 'assistant');
                    const parts = [];
                    if (note) parts.push(snippet(note[1].querySelector('pre').textContent));
                    if (latest.dataset.kind === 'tool.execution_start') parts.push(`Using ${latest.dataset.tool || 'tool'}`);
                    else if (!note) parts.push('Working…');
                    block.step.textContent = parts.join(' · ');
                }
                const before = reply.get(jobId), after = request.get(jobId);
                if (before) messages.insertBefore(block.el, before);
                else if (after) messages.insertBefore(block.el, after.nextSibling);
                else messages.append(block.el);
            }
        }
        function renderThread(data) {
            const stick = lastThread !== selected || log.scrollTop + log.clientHeight >= log.scrollHeight - 48;
            if (lastThread !== selected) {
                clearTimeline();
                lastThread = selected; message.value = drafts[selected]?.text || '';
            }
            threadState = data;
            loadModels().then(updateModelChip);
            updateModelChip();
            if (!document.hidden) window.dispatchEvent(new CustomEvent('hub-thread-seen', { detail: data.thread.id }));
            for (const item of data.messages) {
                if (!messageRows.has(item.id)) {
                    const row = node('article', `agent-message ${item.role}`);
                    const isUser = item.role === 'user';
                    const body = node('div', 'msg-body');
                    const text = node('div', 'msg-text');
                    if (typeof hubMarkdown === 'undefined') text.textContent = item.text;
                    else { try { text.append(hubMarkdown.render(item.text)); } catch { text.textContent = item.text; } }
                    body.append(node('div', 'msg-author', isUser ? 'You' : agentLabel(data.thread)), text);
                    const avatar = isUser ? node('span', 'msg-avatar', '🧑‍🚀') : hubAgentIdentity.avatar(data.thread.session_id.slice(0, 8));
                    row.append(avatar, body);
                    messages.append(row); messageRows.set(item.id, row);
                }
                if (item.nonce && item.nonce === drafts[selected]?.nonce) {
                    delete drafts[selected]; saveDrafts(); message.value = ''; fail('');
                }
            }
            renderEvents(data.events);
            if (!eventRows.size || Math.min(...eventRows.keys()) >= (data.events[0]?.id || Infinity)) {
                older.hidden = !data.has_older_events;
            }
            empty.hidden = data.messages.length > 0;
            const last = data.jobs.at(-1);
            const running = data.jobs.find(job => ['running', 'cancelling'].includes(job.status));
            layoutActivity(data.jobs);
            const queued = data.jobs.filter(job => job.status === 'queued').length;
            state.textContent = data.thread.closed ? 'Thread closed' : running
                ? (running.status === 'cancelling' ? 'Stopping…' : 'Working…') + (queued ? ` · ${queued} queued` : '')
                : last && last.status !== 'done' ? (last.error || last.status) : '';
            if (!state.textContent && service) state.textContent = service;
            threadControls.hidden = !state.textContent && !running && !queued;
            stop.hidden = !running && !queued;
            close.textContent = data.thread.closed ? 'Reopen thread' : 'Close thread';
            close.hidden = false;
            const tab = threadTabs.get(selected);
            if (tab) tab.title = `${data.thread.title} · Private agent chat · Copilot session: ${data.thread.session_id}`;
            if (stick) log.scrollTop = log.scrollHeight;
            updateSend();
        }
        async function refresh() {
            if (disposed || busy || document.hidden) return;
            busy = true;
            const requestedThread = selected;
            const requestedAuth = authVersion;
            try {
                if (!authenticated) {
                    const session = await api('session');
                    if (requestedAuth !== authVersion) return;
                    authenticated = session.authenticated; authKnown = true;
                    if (!authenticated) { lock(); return; }
                }
                locked.hidden = true; content.hidden = false;
                channelState = await api(`channels/${channel.id}`);
                if (disposed || !authenticated || requestedAuth !== authVersion) return;
                toggle.textContent = channelState.enabled ? 'AI on' : 'AI off';
                toggle.setAttribute('aria-checked', String(channelState.enabled));
                service = channelState.online ? '' : 'Coordinator offline · requests wait in the queue';
                const activeThreads = channelState.threads.filter(thread => !thread.archived);
                const archivedThreads = channelState.threads.filter(thread => thread.archived);
                const ids = new Set(activeThreads.map(thread => thread.id));
                for (const [id, tab] of threadTabs) {
                    if (!ids.has(id)) { tab.parentElement.remove(); threadTabs.delete(id); }
                }
                archiveMenu.hidden = !archivedThreads.length;
                archiveCount.textContent = archivedThreads.length;
                archiveList.replaceChildren(...archivedThreads.map(thread => {
                    const row = node('div', 'chat-archive-row');
                    const name = node('span', 'chat-archive-name', thread.title);
                    name.title = thread.title;
                    const restore = button('Restore', () => { archiveMenu.open = false; setArchived(thread.id, false); }, 'btn btn-sm');
                    restore.setAttribute('aria-label', `Restore chat ${thread.title}`);
                    row.append(name, restore);
                    return row;
                }));
                let revealSelection = false;
                activeThreads.forEach((thread, index) => {
                    let tab = threadTabs.get(thread.id);
                    if (!tab) {
                        const wrap = node('div', 'chat-tab-wrap');
                        const x = button('×', () => setArchived(thread.id, true), 'chat-tab-x');
                        x.setAttribute('aria-label', `Archive chat ${thread.title}`);
                        x.title = 'Archive chat';
                        tab = button('', () => choose(thread.id), 'chat-tab');
                        tab.id = `agentChatTab-${thread.id}`;
                        tab.setAttribute('role', 'tab');
                        tab.setAttribute('aria-controls', panel.id);
                        tab.title = 'Private agent chat';
                        wrap.append(tab, x);
                        threadTabs.set(thread.id, tab);
                        if (thread.id === selected) revealSelection = true;
                    }
                    const label = thread.closed ? `${thread.title} (closed)` : thread.title;
                    const indicator = threadIndicator(thread);
                    const [name] = INDICATORS[indicator] || [''];
                    if (tab.dataset.label !== label || (tab.dataset.indicator || '') !== indicator) {
                        tab.dataset.label = label; tab.dataset.indicator = indicator;
                        tab.replaceChildren();
                        if (indicator) {
                            const dot = node('span', `tab-indicator ${indicator}`, { error: '!', waiting: '?', done: '✓' }[indicator] || '');
                            dot.setAttribute('aria-hidden', 'true');
                            tab.append(dot);
                        }
                        tab.append(label);
                        if (name) tab.setAttribute('aria-description', name); else tab.removeAttribute('aria-description');
                    }
                    const wrap = tab.parentElement;
                    if (tabs.children[index + 1] !== wrap) tabs.insertBefore(wrap, tabs.children[index + 1] || null);
                });
                updateView();
                if (revealSelection) revealActiveTab();
                if (opened && selected && !creating) {
                    const id = selected;
                    const data = await api(`threads/${id}`);
                    if (!authenticated || requestedAuth !== authVersion) return;
                    if (data.thread.channel !== channel.id) throw new Error('This thread belongs to another channel. Choose a thread from this channel.');
                    if (id === selected) renderThread(data);
                } else {
                    threadState = null; stop.hidden = true; close.hidden = true; state.textContent = service; threadControls.hidden = creating || !service;
                    updateSend();
                }
            } catch (e) { if (!disposed) fail(e.message); }
            finally {
                busy = false;
                if (!disposed && (requestedThread !== selected || (authenticated && requestedAuth !== authVersion))) queueMicrotask(refresh);
            }
        }
        const timer = setInterval(refresh, 2000);
        const resize = new ResizeObserver(revealActiveTab);
        resize.observe(tabs);
        disposeCurrent = () => {
            disposed = true; abort.abort(); clearInterval(timer); resize.disconnect(); delete main.dataset.agentMode;
        };
        function syncRoute() {
            const route = location.hash.split('/');
            if (disposed || route[0] !== '#chat' || route[1] !== String(channel.id)) return;
            if (route[2] === 'thread' && /^\d+$/.test(route[3] || '')) {
                if (!opened || creating || selected !== Number(route[3])) choose(route[3]);
            } else show(false);
        }
        window.addEventListener('hashchange', syncRoute, { signal: abort.signal });
        window.addEventListener('popstate', syncRoute, { signal: abort.signal });
        syncRoute();
        refresh();
    }
    return { mount, dispose: () => disposeCurrent() };
})();
