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
        let disposed = false, opened = false, authenticated = false, busy = false;
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
            if (authenticated) title.focus();
            else key.focus();
        });
        newButton.id = 'newAgentChat';
        newButton.setAttribute('aria-controls', panel.id);
        newButton.title = 'New private agent chat';
        modes.append(newButton);
        const newForm = node('form', 'agent-new-thread');
        newForm.hidden = true;
        const title = input('New thread title', 'What are we working on?', 120);
        title.required = true;
        const create = node('button', 'btn btn-primary', 'Create thread');
        create.type = 'submit';
        newForm.append(title, create);
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
        const activity = node('details', 'agent-activity');
        const activitySummary = node('summary', '', 'Activity');
        const events = node('div', 'agent-events');
        const older = button('Load earlier activity', async () => {
            const first = Math.min(...eventRows.keys());
            try {
                const id = selected;
                const history = await api(`threads/${id}?before=${first}`);
                if (id !== selected) return;
                renderEvents(history.events);
                older.hidden = !history.has_older_events;
            } catch (e) { fail(e.message); }
        }, 'link-btn');
        older.hidden = true;
        activity.append(activitySummary, older, events);
        log.append(empty, messages, activity);
        const form = node('form', 'agent-composer');
        const message = node('textarea');
        message.setAttribute('aria-label', 'Message agent');
        message.placeholder = 'Message the agent…';
        message.rows = 2;
        message.maxLength = 16000;
        const send = node('button', 'btn btn-primary', 'Send');
        send.type = 'submit';
        form.append(message, send);
        content.append(newForm, threadControls, log, form);
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
            authenticated = false;
            locked.hidden = false; content.hidden = true;
            messages.replaceChildren(); events.replaceChildren();
            messageRows.clear(); eventRows.clear(); lastThread = null;
            threadState = null; channelState = null;
            if (wasAuthenticated) key.value = '';
            message.value = '';
            for (const tab of threadTabs.values()) tab.remove();
            threadTabs.clear();
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
            messages.replaceChildren(); events.replaceChildren(); messageRows.clear(); eventRows.clear();
            threadControls.hidden = true; activity.hidden = true; empty.hidden = false;
            message.readOnly = !!drafts[selected]?.nonce;
            show(true);
            revealActiveTab();
        }
        function revealActiveTab() {
            if (opened && !creating) {
                threadTabs.get(selected)?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
            }
        }
        tabs.addEventListener('keydown', event => {
            if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            const items = [...tabs.children];
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
                if (creating) title.focus();
            } catch (e) { fail(e.message); }
            finally { unlock.disabled = false; }
        });
        newForm.addEventListener('submit', async event => {
            event.preventDefault();
            create.disabled = true;
            try {
                const thread = await api(`channels/${channel.id}/threads`, 'POST', { title: title.value });
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
        function renderEvents(items) {
            for (const item of items) {
                if (eventRows.has(item.id)) continue;
                const detail = node('details', 'agent-event');
                const label = item.kind.startsWith('tool.') ? item.kind.replace('tool.execution_', 'Tool ') : item.kind;
                const summary = node('summary', '', `${new Date(item.created * 1000).toLocaleTimeString()} · ${label}`);
                detail.append(summary, node('pre', '', item.text));
                eventRows.set(item.id, detail);
                const next = [...eventRows.keys()].filter(id => id > item.id).sort((a, b) => a - b)[0];
                events.insertBefore(detail, next ? eventRows.get(next) : null);
            }
        }
        function renderThread(data) {
            const stick = lastThread !== selected || log.scrollTop + log.clientHeight >= log.scrollHeight - 48;
            if (lastThread !== selected) {
                messages.replaceChildren(); events.replaceChildren(); messageRows.clear(); eventRows.clear();
                lastThread = selected; message.value = drafts[selected]?.text || '';
            }
            threadState = data;
            for (const item of data.messages) {
                if (!messageRows.has(item.id)) {
                    const row = node('article', `agent-message ${item.role}`);
                    row.append(node('div', 'msg-text', item.text));
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
            activity.hidden = eventRows.size === 0;
            const last = data.jobs.at(-1);
            const running = data.jobs.find(job => ['running', 'cancelling'].includes(job.status));
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
                    authenticated = session.authenticated;
                    if (!authenticated) { lock(); return; }
                }
                locked.hidden = true; content.hidden = false;
                channelState = await api(`channels/${channel.id}`);
                if (disposed || !authenticated || requestedAuth !== authVersion) return;
                toggle.textContent = channelState.enabled ? 'AI on' : 'AI off';
                toggle.setAttribute('aria-checked', String(channelState.enabled));
                service = channelState.online ? '' : 'Coordinator offline · requests wait in the queue';
                const ids = new Set(channelState.threads.map(thread => thread.id));
                for (const [id, tab] of threadTabs) {
                    if (!ids.has(id)) { tab.remove(); threadTabs.delete(id); }
                }
                let revealSelection = false;
                channelState.threads.forEach((thread, index) => {
                    let tab = threadTabs.get(thread.id);
                    if (!tab) {
                        tab = button('', () => choose(thread.id), 'chat-tab');
                        tab.id = `agentChatTab-${thread.id}`;
                        tab.setAttribute('role', 'tab');
                        tab.setAttribute('aria-controls', panel.id);
                        tab.title = 'Private agent chat';
                        threadTabs.set(thread.id, tab);
                        if (thread.id === selected) revealSelection = true;
                    }
                    const label = thread.closed ? `${thread.title} (closed)` : thread.title;
                    if (tab.textContent !== label) tab.textContent = label;
                    if (tabs.children[index + 1] !== tab) tabs.insertBefore(tab, tabs.children[index + 1] || null);
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
