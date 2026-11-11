(() => {
    'use strict';
    const API = '/api/workspace/';
    const $ = id => document.getElementById(id);
    const errors = new Map();
    const store = {
        get(key, fallback) {
            try { return JSON.parse(localStorage.getItem('hub:' + key)) ?? fallback; }
            catch { errors.set('storage', 'Local storage is unavailable. Keep this page open until your changes are saved.'); return fallback; }
        },
        set(key, value) {
            try { localStorage.setItem('hub:' + key, JSON.stringify(value)); return true; }
            catch { setError('storage', 'Drafts could not be stored on this device. Keep this page open until your changes are saved.'); return false; }
        },
    };
    const S = { channels: [], lists: [], chat: [], notes: [], todos: [], templates: [], trash: [] };
    const kinds = { chat: 'channels', notes: 'notes', todos: 'lists' };
    const labels = { chat: 'channel', notes: 'note', todos: 'task list' };
    const limits = { chat: 60, notes: 200, todos: 100 };
    const builtins = {
        chat: [
            { name: 'Agent chat✨', icon: '✨', intro: '', desc: 'Private AI threads · unlock and enable AI to start' },
            { name: 'General', icon: '💬', intro: 'Welcome! Share what you are working on.', desc: 'A place for everyday conversation' },
            { name: 'Announcements', icon: '📣', intro: 'Post updates here. Keep it short and link to details.', desc: 'Updates and releases' },
            { name: 'Questions', icon: '❓', intro: 'Add context, what you tried, and what you expected.', desc: 'Ask for help' },
            { name: 'Experiments', icon: '🧪', intro: 'Share run IDs, configs and metrics so others can reproduce.', desc: 'Results and findings' },
            { name: 'Bugs', icon: '🐞', intro: 'What happened, what you expected, and steps to reproduce.', desc: 'Report and triage problems' },
            { name: 'Random', icon: '🎲', intro: '', desc: 'Off-topic and fun' },
        ],
        notes: [
            { name: 'Meeting notes', icon: '📝', body: '# Meeting notes\n\nDate:\nAttendees:\n\n## Agenda\n- \n\n## Decisions\n- \n\n## Actions\n- [ ] ', desc: 'Agenda, decisions, and actions' },
            { name: 'Experiment log', icon: '🧪', body: '# Experiment log\n\n## Hypothesis\n\n## Setup\n\n## Results\n\n## Next steps\n', desc: 'From hypothesis to result' },
            { name: 'Paper summary', icon: '📄', body: '# Paper summary\n\nLink:\n\n## Problem\n\n## Approach\n\n## Results\n\n## Relevance\n', desc: 'The ideas worth remembering' },
            { name: 'Idea', icon: '💡', body: '# Idea\n\nThe idea in one sentence:\n\n## Why it matters\n\n## How we could try it\n\n## Risks and unknowns\n', desc: 'Capture it before it goes' },
            { name: 'Daily standup', icon: '☀️', body: '# Standup\n\n## Yesterday\n- \n\n## Today\n- \n\n## Blockers\n- ', desc: 'Yesterday, today, and blockers' },
            { name: 'Bug report', icon: '🐞', body: '# Bug report\n\n## Summary\n\n## Steps to reproduce\n1. \n\n## Expected\n\n## Actual\n\n## Environment and logs\n', desc: 'Reproducible and clear' },
        ],
        todos: [
            { name: 'Experiment checklist', icon: '✅', items: ['Define hypothesis and metric', 'Prepare dataset split', 'Run baseline', 'Run experiment', 'Compare results', 'Write up findings'], desc: 'A repeatable research process' },
            { name: 'Weekly plan', icon: '📅', items: ['Plan the week', 'Make time for deep work', 'Review progress', 'Share a weekly summary'], desc: 'A little structure for the week' },
            { name: 'Paper review', icon: '📄', items: ['Skim abstract and figures', 'Read method section', 'Check evaluation and baselines', 'Write summary note', 'Decide: adopt, adapt or skip'], desc: 'Read, summarise, decide' },
            { name: 'Release checklist', icon: '🚀', items: ['Run tests', 'Update documentation', 'Tag and build', 'Deploy', 'Announce the release'], desc: 'Ship with confidence' },
            { name: 'Meeting prep', icon: '📝', items: ['Write agenda', 'Collect updates', 'Prepare demo', 'Capture action items'], desc: 'Walk in ready' },
        ],
    };
    const selected = store.get('sel', {});
    const seen = store.get('seen', {});
    const noteDrafts = store.get('note-drafts', {});
    const chatDrafts = store.get('chat-drafts', {});
    const outbox = store.get('chat-outbox', {});
    const noteStates = new Map();
    let me = store.get('name', '') || `Guest-${Math.floor(1000 + Math.random() * 9000)}`;
    let mode = 'chat', active = false, loaded = false, fetching = false, refreshAgain = false;
    let epoch = 0, writes = 0, mainKey = '', search = '', modalTrigger = null, modalVersion = 0;
    let aiTasks = {};
    let chatStates = {};
    const chatLabels = { error: 'Error', waiting: 'Waiting for input', working: 'Working', done: 'Done' };
    const chatPriority = ['error', 'waiting', 'working', 'done'];
    let lastChatStates = null;
    const sideRows = new Map();
    let sideMode = '';
    let pane = null;
    for (const entries of Object.values(outbox)) {
        for (const entry of entries) {
            entry.state = 'failed';
            entry.error = 'Sending was interrupted. Check the conversation before retrying to avoid a duplicate.';
        }
    }

    function el(tag, className = '', text, attrs = {}) {
        const node = document.createElement(tag);
        node.className = className;
        if (text !== undefined) node.textContent = text;
        for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
        return node;
    }
    function button(text, className, action, attrs) {
        const node = el('button', className || 'btn', text, { type: 'button', ...attrs });
        if (action) node.addEventListener('click', action);
        return node;
    }
    const EMOJI_GROUPS = {
        Smileys: '😀 😂 🙂 😉 😍 🤔 😎 🥳 😴 😅 🙌 👍 👏 🙏 💪 👀',
        Work: '📝 📄 📚 📌 📎 📅 📊 📈 💡 🎯 🔧 🛠️ 💻 🔬 🧪 🧠',
        Status: '✅ ❌ ⚠️ ❓ ❗ ⭐ 🔥 🚀 🎉 🏆 🔒 🔔 ⏰ 🐞 ✨ 💬',
        Nature: '🌱 🌳 🌸 ☀️ 🌙 ⚡ 🌈 ❄️ 🐶 🐱 🦊 🐢 🍎 ☕ 🍕 🎵',
        Symbols: '❤️ 💙 💚 💜 🟢 🟡 🔴 🔵 ➕ ➖ ➡️ 🔗 🏠 🌍 🎲 🎨',
    };
    let emojiPop = null;
    function closeEmoji() {
        if (!emojiPop) return;
        const { node, anchor } = emojiPop; emojiPop = null;
        node.remove(); anchor.setAttribute('aria-expanded', 'false');
        document.removeEventListener('pointerdown', emojiOutside, true);
        document.removeEventListener('keydown', emojiKey, true);
    }
    function emojiOutside(event) { if (emojiPop && !emojiPop.node.contains(event.target) && !emojiPop.anchor.contains(event.target)) closeEmoji(); }
    function emojiKey(event) {
        if (event.key !== 'Escape' || !emojiPop) return;
        event.preventDefault(); event.stopPropagation();
        const { anchor } = emojiPop; closeEmoji(); anchor.focus({ preventScroll: true });
    }
    function openEmoji(anchor, pick, clearLabel) {
        const reopen = emojiPop?.anchor !== anchor;
        closeEmoji();
        if (!reopen) return;
        const node = el('div', 'emoji-pop', undefined, { role: 'dialog', 'aria-label': 'Choose an icon' });
        for (const [group, list] of Object.entries(EMOJI_GROUPS)) {
            node.append(el('p', 'emoji-group', group));
            const grid = el('div', 'emoji-grid');
            for (const emoji of list.split(' ')) {
                grid.append(button(emoji, 'emoji-opt', () => { closeEmoji(); pick(emoji); }, { 'aria-label': `Icon ${emoji}` }));
            }
            node.append(grid);
        }
        if (clearLabel) node.append(button(clearLabel, 'link-btn emoji-clear', () => { closeEmoji(); pick(''); }));
        (document.querySelector('dialog[open]') || document.body).append(node);
        const box = anchor.getBoundingClientRect();
        const width = Math.min(300, innerWidth - 16);
        node.style.width = `${width}px`;
        node.style.left = `${Math.max(8, Math.min(box.left, innerWidth - width - 8))}px`;
        const room = innerHeight - box.bottom - 8;
        if (room < 220 && box.top > room) { node.style.bottom = `${innerHeight - box.top + 6}px`; node.style.maxHeight = `${Math.max(160, box.top - 14)}px`; }
        else { node.style.top = `${box.bottom + 6}px`; node.style.maxHeight = `${Math.max(160, room - 6)}px`; }
        anchor.setAttribute('aria-expanded', 'true');
        emojiPop = { node, anchor };
        document.addEventListener('pointerdown', emojiOutside, true);
        document.addEventListener('keydown', emojiKey, true);
        node.querySelector('.emoji-opt').focus({ preventScroll: true });
    }
    // Wraps a text field with a button that inserts an emoji at the caret.
    function withEmoji(field) {
        const wrap = el('span', `emoji-field${field.tagName === 'TEXTAREA' ? ' multiline' : ''}`);
        const add = button('☺', 'emoji-add', () => openEmoji(add, emoji => {
            const max = Number(field.getAttribute('maxlength')) || Infinity;
            if (field.value.length + emoji.length > max) return;
            const start = field.selectionStart ?? field.value.length, end = field.selectionEnd ?? start;
            field.focus({ preventScroll: true });
            field.setRangeText(emoji, start, end, 'end');
            field.dispatchEvent(new Event('input', { bubbles: true }));
        }), { 'aria-label': `Add icon to ${field.getAttribute('aria-label') || 'text'}`, title: 'Add icon', 'aria-haspopup': 'dialog', 'aria-expanded': 'false' });
        wrap.append(field, add);
        return wrap;
    }
    window.hubWithEmoji = withEmoji;
    function iconButton(current, defaultIcon, pick) {
        const node = button('', 'icon-pick', null, { 'aria-haspopup': 'dialog', 'aria-expanded': 'false' });
        node.addEventListener('click', () => openEmoji(node, async emoji => {
            node.disabled = true;
            try { await pick(emoji); } finally { node.disabled = false; }
        }, 'Remove icon'));
        node.setIcon = value => {
            text(node, value || '＋');
            node.classList.toggle('empty', !value);
            node.setAttribute('aria-label', value ? `Change icon (${value})` : 'Add icon');
            node.title = value ? 'Change icon' : 'Add icon';
        };
        node.setIcon(current);
        return node;
    }
    function richText(node, value) {
        const source = String(value);
        if (node.dataset.src === source) return;
        node.dataset.src = source;
        node.replaceChildren(hubMarkdown.render(source));
    }
    function text(node, value) { if (node.textContent !== String(value)) node.textContent = value; }
    function setError(key, error) {
        if (error) errors.set(key, error.message || String(error)); else errors.delete(key);
        const box = $('wsError');
        if (box) { text(box, [...errors.values()].join(' ')); box.hidden = !errors.size; }
    }
    async function api(path, method = 'GET', body) {
        const writing = method !== 'GET';
        if (writing) { writes++; epoch++; }
        try {
            const response = await fetch(API + path, {
                method, signal: AbortSignal.timeout(15000), credentials: 'same-origin',
                ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
            });
            let data;
            try { data = await response.json(); } catch { throw new Error(`The hub returned an unreadable response (${response.status}).`); }
            if (!response.ok) {
                const error = new Error(data.error || `Request failed (${response.status}).`);
                error.status = response.status;
                error.current = data.current;
                throw error;
            }
            return data;
        } finally {
            if (writing) {
                writes--; epoch++;
                if (!writes && !fetching && refreshAgain) queueMicrotask(refresh);
            }
        }
    }
    function upsert(kind, item) {
        const index = S[kind].findIndex(row => row.id === item.id);
        if (index < 0) S[kind].push(item); else S[kind][index] = item;
    }
    function rows(view = mode) { return S[kinds[view]] || []; }
    function current() { return rows().find(row => String(row.id) === String(selected[mode])); }
    function channelMessages(id) { return S.chat.filter(message => message.channel === id); }
    function atBottom(log) { return log.scrollTop + log.clientHeight >= log.scrollHeight - 48; }
    function unread(id) { return channelMessages(id).filter(message => message.id > (seen[id] || 0)).length; }
    function ago(timestamp) {
        const minutes = Math.max(0, Math.floor((Date.now() / 1000 - timestamp) / 60));
        if (minutes < 1) return 'just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
        return new Date(timestamp * 1000).toLocaleDateString();
    }
    const chatGlyphs = { error: '!', waiting: '?', done: '✓', working: '' };
    const chatSeen = store.get('chat-seen', {});
    function topKind(items) { return chatPriority.find(kind => items.some(item => item.kind === kind)) || ''; }
    function chatDot(el_, kind) {
        el_.className = kind ? `chat-state ${kind}` : 'chat-state';
        el_.hidden = !kind;
        el_.textContent = chatGlyphs[kind] || '';
        if (kind) { el_.title = chatLabels[kind]; el_.setAttribute('aria-label', chatLabels[kind]); }
    }
    function markThreadSeen(thread) {
        const item = Object.values(chatStates).flat().find(entry => entry.thread === thread);
        if (!item || item.kind !== 'done' || chatSeen[thread] === item.job) return;
        chatSeen[thread] = item.job; store.set('chat-seen', chatSeen); updateBadges(); renderSide();
    }
    function attention() {
        return Object.values(chatStates).flat().filter(item => ['error', 'waiting'].includes(item.kind)
            || (item.kind === 'done' && chatSeen[item.thread] !== item.job));
    }
    function announceChatStates() {
        const names = Object.fromEntries(S.channels.map(channel => [String(channel.id), channel.name]));
        const flat = Object.fromEntries(Object.values(chatStates).flat().map(item => [item.thread, item.kind]));
        if (lastChatStates) {
            for (const [id, items] of Object.entries(chatStates)) {
                for (const item of items) {
                    if (lastChatStates[item.thread] === 'working' && ['error', 'waiting', 'done'].includes(item.kind)) {
                        toast(`#${names[id] || id}: ${chatLabels[item.kind].toLowerCase()}`, 'Open', () => navigate('chat', Number(id)));
                        $('workspaceToast').dataset.kind = item.kind;
                    }
                }
            }
        }
        lastChatStates = flat;
    }
    function updateBadges() {
        const needs = attention(), top = topKind(needs), mark = $('badge-chat-state');
        if (mark) {
            mark.hidden = !needs.length; text(mark, needs.length > 99 ? '99+' : needs.length);
            mark.className = `badge chat-alert ${top}`;
            mark.title = needs.length ? `${needs.length} chat${needs.length > 1 ? 's' : ''} need attention · ${chatLabels[top]}` : '';
        }
        for (const [id, count] of [['badge-chat', S.channels.reduce((sum, channel) => sum + unread(channel.id), 0)], ['badge-todos', S.todos.filter(task => !task.done).length]]) {
            if ($(id)) { $(id).hidden = !count; text($(id), count > 99 ? '99+' : count); }
        }
    }
    window.addEventListener('hub-thread-seen', event => markThreadSeen(event.detail));
    function markSeen(id) {
        if (!active || mode !== 'chat' || document.hidden || !pane?.log || pane.id !== id
            || !pane.log.getClientRects().length || !atBottom(pane.log)) return;
        const messages = channelMessages(id);
        const last = messages.length ? messages[messages.length - 1].id : 0;
        if (last > (seen[id] || 0)) { seen[id] = last; store.set('seen', seen); renderSide(); updateBadges(); }
    }

    // Polls reconcile keyed rows; neither the selected editor nor a focused sidebar button is replaced.
    function renderSide() {
        if (!active) return;
        const list = $('sideList');
        if (sideMode !== mode) { list.replaceChildren(); sideRows.clear(); sideMode = mode; }
        $('sideSearch').hidden = false;
        $('sideSearch').placeholder = `Search ${mode === 'todos' ? 'lists and tasks' : mode}`;
        $('sideSearch').setAttribute('aria-label', $('sideSearch').placeholder);
        text($('sideNew'), `New ${labels[mode]}`);
        if ($('sideTitle')) text($('sideTitle'), { chat: 'Channels', notes: 'Notes', todos: 'Task lists' }[mode]);
        const query = search.trim().toLowerCase();
        const matching = rows().filter(row => {
            const content = mode === 'chat' ? channelMessages(row.id).map(message => message.text).join(' ')
                : mode === 'todos' ? S.todos.filter(task => task.list === row.id).map(task => task.text).join(' ')
                    : (noteStates.get(row.id)?.body ?? row.body);
            return `${row.name || row.title} ${content || ''}`.toLowerCase().includes(query);
        });
        if (mode === 'notes') matching.sort((a, b) => Number(noteStates.get(b.id)?.pinned ?? b.pinned ?? false)
            - Number(noteStates.get(a.id)?.pinned ?? a.pinned ?? false));
        if ($('sideSummary')) text($('sideSummary'), loaded ? `${matching.length} ${matching.length === 1 ? labels[mode] : mode === 'todos' ? 'task lists' : labels[mode] + 's'}` : 'Connecting…');
        const ids = new Set(matching.map(row => String(row.id)));
        for (const [id, entry] of sideRows) if (!ids.has(id)) { entry.li.remove(); sideRows.delete(id); }
        list.querySelector('.side-empty')?.remove();
        if (!matching.length) {
            list.append(el('li', 'side-sub side-empty', !loaded ? (errors.has('connection') ? 'Unable to load. Reconnecting…' : 'Loading…') : query ? 'No matches. Try another search.' : `No ${labels[mode]}s yet.`));
        }
        for (const row of matching) {
            const id = String(row.id);
            let entry = sideRows.get(id);
            if (!entry) {
                const view = mode;
                const li = el('li');
                const item = button('', 'side-item', () => navigate(view, row.id));
                const icon = el('span', 'side-icon', '', { 'aria-hidden': 'true' });
                const content = el('span', 'side-text');
                const title = el('span', 'side-title');
                const sub = el('span', 'side-sub');
                const badge = el('span', 'badge');
                const state = el('span', 'chat-state'); state.hidden = true;
                const project = el('span', 'side-project'); project.hidden = true;
                content.append(title, project, sub);
                item.append(icon, content, state, badge);
                li.append(item); list.append(li);
                entry = { li, item, icon, title, sub, badge, state, project }; sideRows.set(id, entry);
            }
            const on = String(selected[mode]) === id;
            entry.item.classList.toggle('active', on);
            if (on) entry.item.setAttribute('aria-current', 'true'); else entry.item.removeAttribute('aria-current');
            text(entry.icon, row.icon || (mode === 'chat' ? '#' : mode === 'todos' ? '✓' : '▤'));
            text(entry.title, (mode === 'notes' ? noteStates.get(row.id)?.title : '') || row.title || row.name);
            let sub = '';
            if (mode === 'chat') {
                const messages = channelMessages(row.id);
                const last = messages[messages.length - 1];
                sub = last ? `${last.author}: ${last.text}` : 'No messages yet';
            } else if (mode === 'todos') {
                const tasks = S.todos.filter(task => task.list === row.id);
                sub = tasks.length ? `${tasks.filter(task => task.done).length} of ${tasks.length} complete` : 'No tasks yet';
            } else sub = (noteStates.get(row.id)?.body ?? row.body ?? '').replace(/\s+/g, ' ').slice(0, 90) || 'Empty note';
            text(entry.sub, sub);
            const projectId = (mode === 'notes' ? noteStates.get(row.id)?.project ?? row.project : row.project) || '';
            if (entry.project.dataset.project !== projectId) {
                entry.project.dataset.project = projectId;
                entry.project.textContent = '';
                const mark = window.HubProjects?.badge(projectId);
                if (mark) entry.project.append(mark);
                entry.project.hidden = !mark;
            }
            const count = mode === 'chat' ? unread(row.id) : 0;
            entry.badge.hidden = !count;
            text(entry.badge, count);
            chatDot(entry.state, mode === 'chat' ? topKind((chatStates[row.id] || []).filter(item => item.kind !== 'done' || chatSeen[item.thread] !== item.job)) : '');
        }
        const focused = document.activeElement;
        const scroll = list.scrollTop;
        matching.forEach((row, index) => {
            const node = sideRows.get(String(row.id)).li;
            if (list.children[index] !== node) list.insertBefore(node, list.children[index] || null);
        });
        if (focused?.isConnected && list.contains(focused) && document.activeElement !== focused) focused.focus({ preventScroll: true });
        list.scrollTop = scroll;
    }
    function detail(on) { $('tab-workspace').dataset.detail = String(on); }
    function routeHash(view, id) { return '#' + (view === 'todos' ? 'tasks' : view) + (id == null ? '' : '/' + encodeURIComponent(id)); }
    function navigate(view, id) {
        const hash = routeHash(view, id);
        if (location.hash === hash) { if (id != null) detail(true); return; }
        history.replaceState({ ...history.state, workspaceSelection: { ...selected } }, '', location.href);
        history.pushState(null, '', hash);
        applyRoute();
    }
    function applyRoute() {
        closeDialog();
        flushNotes();
        let [view, raw] = location.hash.slice(1).split('/');
        if (view === 'workspace') view = ['chat', 'notes', 'todos'].includes(store.get('mode', 'chat')) ? store.get('mode', 'chat') : 'chat';
        if (view === 'tasks') view = 'todos';
        if (!['chat', 'notes', 'todos', 'issues'].includes(view)) view = 'projects';
        const oldMode = mode;
        active = view !== 'projects' && view !== 'issues';
        if (active) {
            mode = view;
            store.set('mode', mode);
            if (raw !== undefined) { try { selected[mode] = decodeURIComponent(raw); } catch { selected[mode] = raw; } }
            else if (history.state?.workspaceSelection && Object.hasOwn(history.state.workspaceSelection, mode)) selected[mode] = history.state.workspaceSelection[mode];
            else if (loaded && !current()) selected[mode] = rows()[0]?.id ?? null;
            store.set('sel', selected);
        }
        document.documentElement.dataset.view = view;
        $('tab-projects').hidden = view !== 'projects';
        $('tab-workspace').hidden = !active;
        $('tab-issues').hidden = view !== 'issues';
        window.dispatchEvent(new CustomEvent('hub-view', { detail: { view, id: view === 'issues' ? raw : undefined } }));
        document.querySelectorAll('.nav-item[data-view]').forEach(node => {
            const on = node.dataset.view === view;
            node.classList.toggle('active', on);
            if (on) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current');
        });
        if (oldMode !== mode) { search = ''; $('sideSearch').value = ''; }
        detail(raw !== undefined);
        render();
        if (active) refresh();
    }
    function render() {
        renderSide(); updateBadges();
        if (!active) return;
        const row = current();
        const key = `${mode}:${row?.id ?? selected[mode] ?? ''}:${loaded}`;
        if (key !== mainKey) {
            hubAgents.dispose();
            mainKey = key; pane = null;
            const main = $('wsMain');
            main.replaceChildren();
            if (!loaded) {
                main.append(el('div', 'empty-state', errors.has('connection') ? 'Unable to load the workspace. Reconnecting…' : 'Loading your workspace…'));
            } else if (!row) {
                const box = el('div', 'empty-state');
                box.append(el('h2', '', selected[mode] != null ? 'This item is not available' : `A fresh start`),
                    el('p', '', selected[mode] != null ? 'It may have been moved to Trash. Choose another item or check Trash.' : `Create a ${labels[mode]} or choose a template to get started.`),
                    button(`New ${labels[mode]}`, 'btn btn-primary', () => createBlank(mode)),
                    button('Use template', 'btn', () => openTemplates(mode)));
                main.append(box);
                if (mode === 'notes' && noteDrafts[selected.notes]) buildOrphanDraft(main, selected.notes);
            } else {
                pane = { id: row.id, view: mode };
                if (mode === 'notes') buildNote(main, row);
                if (mode === 'chat') buildChat(main, row);
                if (mode === 'todos') buildTasks(main, row);
            }
            if (loaded) hubMotion.reveal(main);
        }
        if (row && pane) {
            if (pane.projectSelect && document.activeElement !== pane.projectSelect) pane.projectSelect.setValue((mode === 'notes' ? stateFor(row).project : row.project) || '');
            if (mode === 'notes') updateNote(row);
            else {
                if (document.activeElement !== pane.title && !pane.title.dataset.unsaved) pane.title.value = row.name;
                if (mode === 'chat') updateChat(); else updateTasks();
            }
        }
    }
    function header(row, view) {
        const head = el('div', 'pane-head');
        head.append(button('← Back', 'pane-back', () => navigate(view), { 'aria-label': 'Back to list' }));
        const title = el('input', `pane-title${view === 'notes' ? ' note-title' : ''}`, undefined,
            { 'aria-label': view === 'notes' ? 'Note title' : `${labels[view]} name`, maxlength: limits[view] });
        title.value = row.title || row.name;
        pane.title = title;
        const picker = iconButton(row.icon, '', async emoji => {
            if (view === 'notes') { const state = stateFor(row); state.icon = emoji; picker.setIcon(emoji); changeNote(state, state.title, state.body); return; }
            try {
                const latest = rows(view).find(item => item.id === row.id) || row;
                upsert(kinds[view], await api(`${kinds[view]}/${row.id}`, 'PATCH', { icon: emoji, revision: latest.revision }));
                picker.setIcon(emoji); setError(`icon:${row.id}`, null); renderSide();
            } catch (error) {
                setError(`icon:${row.id}`, `Icon was not saved: ${error.message}`);
                if (error.current) upsert(kinds[view], error.current);
            }
        });
        if (view === 'notes') picker.setIcon(stateFor(row).icon);
        pane.iconPicker = picker;
        const titleBox = el('div', 'pane-titlebox'); titleBox.append(picker, withEmoji(title)); head.append(titleBox);
        const current = (view === 'notes' ? stateFor(row).project : row.project) || '';
        const project = window.HubProjects?.select(current, async value => {
            if (view === 'notes') { const state = stateFor(row); state.project = value; changeNote(state, state.title, state.body); return; }
            try {
                const latest = rows(view).find(item => item.id === row.id) || row;
                upsert(kinds[view], await api(`${kinds[view]}/${row.id}`, 'PATCH', { project: value, revision: latest.revision }));
                setError(`project:${row.id}`, null); renderSide();
            } catch (error) {
                setError(`project:${row.id}`, `Project was not saved: ${error.message}`);
                project.setValue(((rows(view).find(item => item.id === row.id) || row).project) || '');
                if (error.current) upsert(kinds[view], error.current);
            }
        }, `Project for this ${labels[view]}`);
        if (project) { pane.projectSelect = project; head.append(project, window.HubProjects.astraButton(project)); }
        if (view !== 'notes') {
            title.addEventListener('input', () => { title.dataset.unsaved = 'true'; });
            title.addEventListener('change', async () => {
                const name = title.value.trim();
                if (!name) { setError(`rename:${row.id}`, 'Enter a name before saving.'); return; }
                title.disabled = true;
                try {
                    const latest = rows(view).find(item => item.id === row.id);
                    upsert(kinds[view], await api(`${kinds[view]}/${row.id}`, 'PATCH', { name, revision: latest.revision }));
                    delete title.dataset.unsaved; setError(`rename:${row.id}`, null); renderSide();
                } catch (error) {
                    setError(`rename:${row.id}`, `Name was not saved: ${error.message} Edit the name to retry.`);
                    if (error.current) upsert(kinds[view], error.current);
                } finally { title.disabled = false; }
            });
        }
        head.append(button('Save as template', 'link-btn', () => saveAsTemplate(view, row.id)),
            button('Delete', 'icon-btn danger', () => confirmDelete(view, row.id), { 'aria-label': `Delete ${labels[view]}` }));
        return head;
    }
    async function refresh() {
        if (document.hidden) return;
        if (fetching || writes) { refreshAgain = true; return; }
        refreshAgain = false;
        fetching = true;
        const start = epoch;
        try {
            const snapshot = await api('snapshot');
            if (start !== epoch || writes) { refreshAgain = true; return; }
            for (const kind of Object.keys(S)) S[kind] = Array.isArray(snapshot[kind]) ? snapshot[kind] : [];
            aiTasks = snapshot.ai_tasks || {};
            chatStates = snapshot.chat_states || {};
            announceChatStates();
            for (const state of noteStates.values()) {
                const note = S.notes.find(item => item.id === state.id);
                state.deleted = !note;
                if (!note) { clearTimeout(state.timer); continue; }
                if (state.saving || pane?.state === state || state.baseRevision === note.revision) continue;
                if (state.dirty) state.conflict = note;
                else {
                    state.title = note.title; state.body = note.body || ''; state.pinned = !!note.pinned; state.icon = note.icon || ''; state.project = note.project || ''; state.baseRevision = note.revision;
                    state.remote = null;
                }
            }
            loaded = true;
            setError('connection', null);
            if (active && !location.hash.includes('/') && !current()) {
                selected[mode] = rows()[0]?.id ?? null;
                store.set('sel', selected);
            }
            render();
        } catch (error) {
            setError('connection', `Hub connection unavailable: ${error.message} Changes not yet saved will stay as drafts.`);
            if (!loaded && active) { mainKey = ''; render(); }
        } finally {
            fetching = false;
            if (refreshAgain && !writes && !document.hidden) queueMicrotask(refresh);
        }
    }

    // Notes keep an acknowledged revision separate from the text currently being typed.
    function stateFor(note) {
        let state = noteStates.get(note.id);
        if (!state) {
            const draft = noteDrafts[note.id];
            state = {
                id: note.id, title: draft?.title ?? note.title, body: draft?.body ?? note.body ?? '',
                pinned: draft?.pinned ?? !!note.pinned, icon: draft?.icon ?? note.icon ?? '', project: draft?.project ?? note.project ?? '',
                baseRevision: draft?.baseRevision ?? note.revision, version: 0, dirty: !!draft,
                saving: false, error: draft ? 'An unsaved draft was recovered from this device.' : '', conflict: null, remote: null, timer: null,
            };
            if (draft && state.baseRevision !== note.revision) state.conflict = note;
            noteStates.set(note.id, state);
        }
        return state;
    }
    function persistNote(state) {
        if (state.dirty) noteDrafts[state.id] = { title: state.title, body: state.body, pinned: state.pinned, icon: state.icon, project: state.project, baseRevision: state.baseRevision };
        else delete noteDrafts[state.id];
        store.set('note-drafts', noteDrafts);
    }
    function changeNote(state, title, body) {
        state.title = title; state.body = body; state.version++; state.dirty = true;
        persistNote(state);
        clearTimeout(state.timer);
        if (!state.conflict) state.timer = setTimeout(() => saveNote(state), 650);
        updateNoteStatus(state); renderSide();
    }
    async function saveNote(state) {
        clearTimeout(state.timer);
        if (!state.dirty || state.saving || state.conflict || state.deleted) return;
        if (!state.title.trim()) { state.error = 'Add a title to save this note.'; updateNoteStatus(state); return; }
        const sent = { title: state.title, body: state.body, pinned: state.pinned, icon: state.icon, project: state.project, revision: state.baseRevision };
        const version = state.version;
        state.saving = true; state.error = ''; updateNoteStatus(state);
        try {
            const saved = await api(`notes/${state.id}`, 'PATCH', sent);
            upsert('notes', saved);
            state.baseRevision = saved.revision;
            state.remote = null;
            if (version === state.version) { state.dirty = false; state.title = saved.title; state.body = saved.body || ''; state.pinned = !!saved.pinned; state.icon = saved.icon || ''; state.project = saved.project || ''; }
            persistNote(state); setError(`note:${state.id}`, null);
        } catch (error) {
            state.error = error.message;
            if (error.status === 409 && error.current) { state.conflict = error.current; upsert('notes', error.current); }
            setError(`note:${state.id}`, `Note “${state.title || 'Untitled'}” is not saved. ${state.conflict ? 'Resolve the newer version before saving.' : error.message}`);
            persistNote(state);
        } finally {
            state.saving = false;
            updateNoteStatus(state); renderSide();
            if (state.dirty && !state.error && !state.conflict) saveNote(state);
        }
    }
    function flushNotes() {
        for (const state of noteStates.values()) if (state.dirty && !state.error && !state.conflict) saveNote(state);
    }
    function buildNote(main, note) {
        const state = stateFor(note);
        const head = header(note, 'notes');
        pane.title.value = state.title;
        const pin = button(state.pinned ? 'Unpin' : 'Pin', 'icon-btn pin', () => {
            state.pinned = !state.pinned;
            changeNote(state, state.title, state.body);
        });
        const status = el('span', 'save-status', '', { id: 'noteStatus', role: 'status', 'aria-live': 'polite' });
        head.append(pin, status);
        const toolbar = el('div', 'editor-toolbar');
        const edit = button('Edit', 'btn', () => setPreview(false), { 'aria-pressed': 'true' });
        const preview = button('Preview', 'btn', () => setPreview(true), { 'aria-pressed': 'false' });
        toolbar.append(edit, preview, el('span', 'hint', 'Markdown supported · Changes save automatically'));
        const actions = el('div', 'draft-actions');
        const editor = el('div', 'note-editor');
        const body = el('textarea', '', undefined, { id: 'noteBody', 'aria-label': 'Note body', maxlength: 50000, placeholder: 'Start writing…' });
        body.value = state.body;
        const bodyWrap = withEmoji(body);
        const rendered = el('article', 'note-preview');
        rendered.hidden = true;
        Object.assign(pane, { state, body, status, actions, rendered, pin });
        function setPreview(on) {
            bodyWrap.hidden = on; rendered.hidden = !on;
            edit.setAttribute('aria-pressed', String(!on)); preview.setAttribute('aria-pressed', String(on));
            if (on) markdown(rendered, state.body);
        }
        const onInput = () => changeNote(state, pane?.id === note.id ? pane.title.value : state.title, body.value);
        pane.title.addEventListener('input', onInput);
        body.addEventListener('input', onInput);
        for (const field of [pane.title, body]) {
            field.addEventListener('keydown', event => {
                if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); saveNote(state); }
            });
            field.addEventListener('blur', () => setTimeout(() => { if (pane?.state === state) updateNote(S.notes.find(item => item.id === note.id) || note); }, 0));
        }
        editor.append(bodyWrap, rendered);
        main.append(head, toolbar, actions, editor);
    }
    function updateNote(note) {
        const state = pane.state;
        if (!state.saving && note.revision !== state.baseRevision) {
            if (state.dirty) state.conflict = note;
            else if ([pane.body, pane.title].includes(document.activeElement)) state.remote = note;
            else {
                state.title = note.title; state.body = note.body || ''; state.pinned = !!note.pinned; state.icon = note.icon || ''; state.project = note.project || ''; state.baseRevision = note.revision;
                state.remote = null;
                pane.title.value = state.title; pane.body.value = state.body; pane.iconPicker?.setIcon(state.icon);
                if (!pane.rendered.hidden) markdown(pane.rendered, state.body);
            }
        }
        updateNoteStatus(state);
    }
    function updateNoteStatus(state) {
        if (pane?.state !== state) return;
        text(pane.pin, state.pinned ? 'Unpin' : 'Pin');
        pane.pin.classList.toggle('on', state.pinned);
        pane.pin.setAttribute('aria-label', state.pinned ? 'Unpin note' : 'Pin note');
        pane.pin.setAttribute('aria-pressed', String(state.pinned));
        const status = state.conflict ? 'Conflict · your draft is kept' : state.saving ? 'Saving…'
            : state.error ? 'Not saved · draft kept' : state.remote ? 'A newer version is available'
                : state.dirty ? 'Unsaved changes' : 'Saved';
        text(pane.status, status);
        const signature = `${!!state.conflict}:${!!state.error}:${!!state.remote}:${state.saving}`;
        if (pane.actions.dataset.signature === signature) return;
        pane.actions.dataset.signature = signature;
        pane.actions.replaceChildren();
        if (state.conflict) {
            pane.actions.append(el('span', '', 'Someone changed this note. Your draft has not been overwritten.'),
                button('Review conflict', 'btn', () => reviewConflict(state)));
        } else if (state.error) {
            pane.actions.append(el('span', '', state.error), button('Retry save', 'btn', () => saveNote(state)));
        } else if (state.remote) {
            pane.actions.append(el('span', 'remote-update', 'A newer version is ready. Your cursor has been left in place.'),
                button('Load latest', 'btn', () => loadNote(state, state.remote)));
        }
    }
    function loadNote(state, latest) {
        clearTimeout(state.timer);
        state.title = latest.title; state.body = latest.body || ''; state.pinned = !!latest.pinned; state.icon = latest.icon || ''; state.project = latest.project || ''; state.baseRevision = latest.revision;
        state.dirty = false; state.conflict = null; state.remote = null; state.error = ''; state.version++;
        upsert('notes', latest); persistNote(state); setError(`note:${state.id}`, null);
        if (pane?.state === state) {
            pane.title.value = state.title; pane.body.value = state.body; pane.iconPicker?.setIcon(state.icon);
            if (!pane.rendered.hidden) markdown(pane.rendered, state.body);
            updateNoteStatus(state);
        }
        renderSide();
    }
    function reviewConflict(state) {
        const latest = state.conflict;
        const grid = openDialog('Resolve note conflict');
        grid.append(el('p', '', 'Both versions are shown below. Keeping your draft explicitly replaces the server version shown here.'),
            el('h3', '', 'Your draft'), el('pre', 'template-preview', `${state.title}${state.pinned ? ' · Pinned' : ''}\n\n${state.body}`),
            el('h3', '', 'Latest saved version'), el('pre', 'template-preview', `${latest.title}${latest.pinned ? ' · Pinned' : ''}\n\n${latest.body || ''}`));
        const actions = el('div', 'dialog-actions');
        actions.append(button('Load latest / discard draft', 'btn', () => { loadNote(state, latest); closeDialog(); }),
            button('Keep my draft', 'btn btn-primary', () => {
                state.baseRevision = latest.revision; state.conflict = null; state.error = '';
                persistNote(state); closeDialog(); saveNote(state);
            }));
        grid.append(actions);
    }
    function buildOrphanDraft(main, id) {
        const draft = noteDrafts[id];
        const box = el('div', 'draft-actions');
        box.append(el('p', '', 'An unsaved draft for this note is still on this device. Restore the note from Trash, or save the draft as a new note.'),
            button('Recover draft as new note', 'btn', async event => {
                const control = event.currentTarget; control.disabled = true;
                try {
                    const note = await api('notes', 'POST', { title: draft.title.trim() || 'Recovered note', body: draft.body, pinned: !!draft.pinned, icon: draft.icon || '', project: draft.project || '' });
                    upsert('notes', note); delete noteDrafts[id]; noteStates.delete(Number(id)); store.set('note-drafts', noteDrafts);
                    setError(`note:${id}`, null); navigate('notes', note.id);
                } catch (error) { setError(`note:${id}`, error); } finally { control.disabled = false; }
            }));
        main.append(box);
    }
    function inlineMarkdown(target, source) {
        const pattern = /(`[^`]+`|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*)/g;
        let offset = 0;
        for (const match of source.matchAll(pattern)) {
            target.append(document.createTextNode(source.slice(offset, match.index)));
            const value = match[0];
            if (value.startsWith('`')) target.append(el('code', '', value.slice(1, -1)));
            else if (value.startsWith('**')) target.append(el('strong', '', value.slice(2, -2)));
            else {
                const parts = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(value);
                try {
                    const url = new URL(parts[2], location.href);
                    if (!['http:', 'https:', 'mailto:'].includes(url.protocol)) throw new Error();
                    target.append(el('a', '', parts[1], { href: url.href, rel: 'noopener noreferrer', target: '_blank' }));
                } catch { target.append(document.createTextNode(value)); }
            }
            offset = match.index + value.length;
        }
        target.append(document.createTextNode(source.slice(offset)));
    }
    function markdown(target, source) {
        target.replaceChildren();
        let code = null, list = null;
        for (const line of source.split('\n')) {
            if (/^\s*```/.test(line)) {
                if (code) code = null;
                else { code = el('code'); const pre = el('pre'); pre.append(code); target.append(pre); }
                list = null; continue;
            }
            if (code) { code.append(document.createTextNode(line + '\n')); continue; }
            const heading = /^(#{1,6})\s+(.+)$/.exec(line);
            const item = /^\s*[-*]\s+(?:\[([ xX])\]\s*)?(.*)$/.exec(line);
            if (item) {
                if (!list) { list = el('ul'); target.append(list); }
                const li = el('li');
                if (item[1] !== undefined) li.append(document.createTextNode(item[1].toLowerCase() === 'x' ? '☑ ' : '☐ '));
                inlineMarkdown(li, item[2]); list.append(li); continue;
            }
            list = null;
            if (!line.trim()) continue;
            const node = el(heading ? `h${heading[1].length}` : 'p');
            inlineMarkdown(node, heading ? heading[2] : line); target.append(node);
        }
        if (!source.trim()) target.append(el('p', 'hint', 'Nothing to preview yet.'));
    }

    // The composer draft and each pending payload are separate durable records.
    function buildChat(main, channel) {
        const head = header(channel, 'chat');
        head.append(button(`Posting as ${me}`, 'identity-control', openIdentity));
        const log = el('div', 'chat-log', undefined, { id: 'chatLog', 'aria-label': 'Conversation', tabindex: '0' });
        const older = button('Show older messages', 'link-btn', () => {
            const height = log.scrollHeight, top = log.scrollTop;
            pane.limit += 300; updateChat();
            log.scrollTop = top + log.scrollHeight - height;
        });
        const messages = el('div', 'chat-messages');
        const jump = button('↓ New messages', 'jump', () => { log.scrollTop = log.scrollHeight; jump.hidden = true; markSeen(channel.id); });
        jump.hidden = true;
        log.append(older, messages);
        const pending = el('div', 'outbox', undefined, { 'aria-label': 'Unsent messages' });
        const composer = el('form', 'composer');
        const input = el('textarea', '', undefined, { 'aria-label': 'Message', placeholder: `Message #${channel.name}`, maxlength: 4000, rows: 2 });
        input.value = chatDrafts[channel.id] || '';
        const send = el('button', 'btn btn-primary', 'Send', { type: 'submit' });
        send.disabled = !input.value.trim();
        function remember() {
            chatDrafts[channel.id] = input.value; store.set('chat-drafts', chatDrafts);
            send.disabled = !input.value.trim();
            input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
        }
        input.addEventListener('input', remember);
        input.addEventListener('keydown', event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); composer.requestSubmit(); }
        });
        composer.addEventListener('submit', event => {
            event.preventDefault();
            if (!input.value.trim()) return;
            const entry = { id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`, text: input.value, author: me, state: 'pending', error: '' };
            (outbox[channel.id] ||= []).push(entry); store.set('chat-outbox', outbox);
            input.value = ''; remember();
            sendMessage(channel.id, entry);
        });
        composer.append(withEmoji(input), send);
        Object.assign(pane, { log, messages, older, jump, pending, input, send, remember, limit: 300, messageRows: new Map(), pendingSignature: '' });
        log.addEventListener('scroll', () => { if (atBottom(log)) { jump.hidden = true; markSeen(channel.id); } });
        const shared = el('section', 'shared-chat-panel', undefined, { id: 'sharedChatPanel', role: 'tabpanel', 'aria-labelledby': 'sharedChatTab' });
        shared.append(log, jump, pending, composer, el('div', 'hint', 'Shared conversation · Enter to send · Shift+Enter for a new line'));
        main.append(head, shared);
        hubAgents.mount(main, channel);
    }
    async function sendMessage(channel, entry) {
        if (entry.sending) return;
        entry.sending = true; entry.state = 'pending'; entry.error = '';
        store.set('chat-outbox', outbox); updateOutbox(channel);
        try {
            const message = await api('chat', 'POST', { channel, author: entry.author, text: entry.text });
            upsert('chat', message);
            outbox[channel] = (outbox[channel] || []).filter(item => item.id !== entry.id);
            setError(`chat:${entry.id}`, null);
        } catch (error) {
            entry.state = 'failed';
            entry.error = `${error.message} Check the conversation before retrying if the connection was interrupted.`;
            setError(`chat:${entry.id}`, 'A message was not confirmed. Its text is kept in the channel outbox.');
        } finally {
            delete entry.sending; store.set('chat-outbox', outbox);
            if (pane?.view === 'chat' && pane.id === channel) { updateChat(); updateOutbox(channel); }
            renderSide(); updateBadges();
        }
    }
    function updateOutbox(channel) {
        if (pane?.view !== 'chat' || pane.id !== channel) return;
        const entries = outbox[channel] || [];
        const signature = JSON.stringify(entries);
        if (pane.pendingSignature === signature) return;
        pane.pendingSignature = signature; pane.pending.replaceChildren(); pane.pending.hidden = !entries.length;
        for (const entry of entries) {
            const box = el('div', 'outbox-item');
            const pendingText = el('div', 'msg-text md-host'); richText(pendingText, entry.text);
            box.append(pendingText, el('p', 'save-status', entry.state === 'pending' ? 'Sending…' : entry.error));
            if (entry.state === 'failed') {
                box.append(button('Retry send', 'btn', () => sendMessage(channel, entry)),
                    button('Move to draft', 'btn', () => {
                        const combined = [pane.input.value, entry.text].filter(Boolean).join('\n');
                        if (combined.length > 4000) {
                            setError(`chat:${entry.id}`, 'The combined draft would exceed 4,000 characters. Send or shorten the current draft first. Your failed message is still kept.');
                            return;
                        }
                        pane.input.value = combined;
                        pane.remember();
                        outbox[channel] = outbox[channel].filter(item => item.id !== entry.id);
                        store.set('chat-outbox', outbox); setError(`chat:${entry.id}`, null); updateOutbox(channel);
                    }));
            }
            pane.pending.append(box);
        }
    }
    function updateChat() {
        if (pane?.view !== 'chat') return;
        const { log, messages, messageRows } = pane;
        const all = channelMessages(pane.id);
        const visible = all.slice(-pane.limit);
        const stick = !pane.chatReady || atBottom(log);
        const ids = new Set(visible.map(message => message.id));
        for (const [id, node] of messageRows) if (!ids.has(id)) { node.remove(); messageRows.delete(id); }
        pane.older.hidden = all.length <= pane.limit;
        text(pane.older, `Show older messages (${Math.max(0, all.length - pane.limit)} remaining)`);
        messages.querySelector('.empty-state')?.remove();
        if (!all.length) messages.append(el('div', 'empty-state', 'This channel is quiet. Start a conversation below.'));
        let added = false;
        visible.forEach((message, index) => {
            let node = messageRows.get(message.id);
            if (!node) {
                node = el('article', 'msg first');
                const avatar = el('div', 'avatar', (message.author || '?').slice(0, 1).toUpperCase(), { 'aria-hidden': 'true' });
                let hue = 0;
                for (const letter of message.author || '') hue = (hue * 31 + letter.codePointAt(0)) % 360;
                avatar.style.setProperty('--avatar-hue', hue);
                const body = el('div', 'msg-body');
                const meta = el('div', 'msg-meta');
                const date = new Date(message.ts * 1000);
                const today = date.toDateString() === new Date().toDateString();
                const concise = date.toLocaleString([], { hour: '2-digit', minute: '2-digit',
                    ...(!today ? { month: 'short', day: 'numeric', ...(date.getFullYear() !== new Date().getFullYear() ? { year: 'numeric' } : {}) } : {}) });
                meta.append(el('b', '', message.author), el('time', '', concise, { datetime: date.toISOString(), title: date.toLocaleString() }));
                const msgText = el('div', 'msg-text md-host'); richText(msgText, message.text);
                body.append(meta, msgText);
                node.append(avatar, body, button('×', 'icon-btn danger', () => deleteItem('chat', message.id), { 'aria-label': 'Move message to Trash' }));
                messageRows.set(message.id, node); added = true;
            }
            if (node.dataset.revision !== String(message.revision)) {
                richText(node.querySelector('.msg-text'), message.text);
                text(node.querySelector('.msg-meta b'), message.author);
                node.dataset.revision = String(message.revision);
            }
            if (messages.children[index] !== node) {
                messages.insertBefore(node, messages.children[index] || null);
                if (pane.chatReady && stick) hubMotion.reveal(node);
            }
        });
        if (stick) { log.scrollTop = log.scrollHeight; pane.jump.hidden = true; }
        else if (added) pane.jump.hidden = false;
        pane.chatReady = true; updateOutbox(pane.id);
        requestAnimationFrame(() => { if (pane?.log === log) markSeen(pane.id); });
    }
    function openIdentity() {
        const grid = openDialog('Conversation display name');
        grid.append(el('p', '', 'This name labels your messages on this device. It is not an account or authentication. Everyone with hub access shares this workspace.'));
        const label = el('label', '', 'Display name');
        const input = el('input', '', undefined, { maxlength: 40, 'aria-label': 'Display name' });
        input.value = me; label.append(withEmoji(input));
        grid.append(label, button('Save name', 'btn btn-primary', () => {
            if (!input.value.trim()) { input.setCustomValidity('Enter a display name.'); input.reportValidity(); return; }
            me = input.value.trim(); store.set('name', me);
            document.querySelectorAll('.identity-control').forEach(node => text(node, `Posting as ${me}`)); closeDialog();
        }));
        input.addEventListener('input', () => input.setCustomValidity(''));
    }

    // Task controls stay in place after updates, including completion and priority changes.
    function buildTasks(main, list) {
        const head = header(list, 'todos');
        head.append(button('Clear completed', 'link-btn', () => clearCompleted(list.id)));
        const progress = el('div', 'progress-label', '', { id: 'progressLabel' });
        const track = el('div', 'progress');
        const bar = el('div', '', '', { id: 'progressBar' }); track.append(bar);
        const tasks = el('div', 'tasks', undefined, { id: 'taskList' });
        const form = el('form', 'add-task');
        const input = el('input', '', undefined, { 'aria-label': 'New task', placeholder: 'Add a task', maxlength: 500, autocomplete: 'off' });
        const add = el('button', 'btn btn-primary', 'Add', { type: 'submit' });
        form.append(withEmoji(input), add);
        form.addEventListener('submit', async event => {
            event.preventDefault();
            const value = input.value;
            if (!value.trim() || add.disabled) return;
            add.disabled = true;
            try {
                upsert('todos', await api('todos', 'POST', { list: list.id, text: value }));
                if (input.value === value) input.value = '';
                setError(`add:${list.id}`, null); render();
            } catch (error) { setError(`add:${list.id}`, error); } finally { add.disabled = false; }
        });
        Object.assign(pane, { progress, bar, tasks, taskRows: new Map() });
        main.append(head, progress, track, tasks, form);
    }
    function updateTasks() {
        if (pane?.view !== 'todos') return;
        const tasks = S.todos.filter(task => task.list === pane.id);
        const count = tasks.filter(task => task.done).length;
        text(pane.progress, tasks.length ? `${count} of ${tasks.length} complete` : 'No tasks yet');
        pane.bar.style.transform = `scaleX(${tasks.length ? count / tasks.length : 0})`;
        const ids = new Set(tasks.map(task => task.id));
        for (const [id, entry] of pane.taskRows) {
            if (!ids.has(id)) {
                if (entry.row.contains(document.activeElement)) {
                    const target = entry.row.nextElementSibling?.querySelector('button')
                        || entry.row.previousElementSibling?.querySelector('button')
                        || $('wsMain').querySelector('.add-task button');
                    target?.focus({ preventScroll: true });
                }
                entry.row.remove(); pane.taskRows.delete(id);
            }
        }
        pane.tasks.querySelector('.empty-state')?.remove();
        if (!tasks.length) pane.tasks.append(el('div', 'empty-state', 'Add the first task below.'));
        for (const task of tasks) {
            let entry = pane.taskRows.get(task.id);
            if (!entry) {
                entry = makeTask(task); pane.taskRows.set(task.id, entry); pane.tasks.append(entry.row);
                if (pane.tasksReady) hubMotion.reveal(entry.row);
            }
            entry.task = task;
            const completionChanged = entry.initialized && entry.row.classList.contains('done') !== !!task.done;
            entry.row.classList.toggle('done', !!task.done);
            if (completionChanged) hubMotion.complete(entry.check.parentElement);
            entry.initialized = true;
            entry.check.checked = !!task.done;
            entry.check.setAttribute('aria-label', `${task.done ? 'Reopen' : 'Complete'} ${task.text}`);
            text(entry.label, task.text);
            updateAi(entry, task);
            text(entry.star, task.starred ? '★' : '☆');
            entry.star.classList.toggle('on', !!task.starred);
            entry.star.setAttribute('aria-pressed', String(!!task.starred));
        }
        pane.tasksReady = true;
    }
    const aiStates = {
        working: 'AI working…', needs_input: 'AI needs your reply', failed: 'AI failed', stopped: 'AI stopped', done: 'AI report',
    };
    function updateAi(entry, task) {
        const link = aiTasks[task.id];
        const label = link && aiStates[link.state];
        entry.ai.hidden = !!task.done || link?.state === 'working' || link?.state === 'needs_input';
        entry.ai.textContent = link ? '✨ Retry AI' : '✨ AI complete';
        entry.aiLink.hidden = !label;
        if (label) {
            const key = `${link.agent || ''}|${label}`;
            if (entry.aiLink.dataset.key !== key) {
                entry.aiLink.dataset.key = key;
                entry.aiLink.replaceChildren(...(link.agent ? [hubAgentIdentity.avatar(link.agent, 'agent-avatar')] : []), `${label} →`);
            }
            entry.aiLink.className = `ai-task-link ${link.state}`;
            entry.aiLink.href = `#chat/${link.channel}/thread/${link.thread}`;
            entry.aiLink.title = 'Open this task’s dedicated discussion';
        }
    }
    function makeTask(task) {
        const row = el('div', 'task');
        const check = el('input', '', undefined, { type: 'checkbox' });
        const checkTarget = el('label', 'task-check');
        checkTarget.append(check);
        const label = button(task.text, 'task-text');
        const star = button('☆', 'icon-btn star', null, { 'aria-label': 'Priority' });
        const remove = button('×', 'icon-btn danger', () => deleteItem('todos', task.id), { 'aria-label': `Delete task: ${task.text}` });
        const ai = button('✨ AI complete', 'btn ai-task', null, { title: 'Spawn an agent that completes this task and reports in chat' });
        const aiLink = el('a', 'ai-task-link');
        const entry = { row, check, label, star, remove, ai, aiLink, task, busy: false };
        ai.addEventListener('click', async () => {
            ai.disabled = true;
            try {
                await api(`../agents/tasks/${task.id}/ai-complete`, 'POST', {});
                setError(`ai:${task.id}`, null); await refresh();
            } catch (error) {
                setError(`ai:${task.id}`, error.status === 401
                    ? 'Unlock Agent chat in the heart channel first, then press AI complete again.'
                    : `AI complete failed: ${error.message}`);
            } finally { ai.disabled = false; }
        });
        const update = async fields => {
            if (entry.busy) return false;
            entry.busy = true; check.disabled = star.disabled = remove.disabled = true;
            try {
                upsert('todos', await api(`todos/${task.id}`, 'PATCH', { ...fields, revision: entry.task.revision }));
                setError(`task:${task.id}`, null); render(); return true;
            } catch (error) {
                if (error.current) upsert('todos', error.current);
                setError(`task:${task.id}`, `Task was not saved: ${error.message}`); render(); return false;
            } finally { entry.busy = false; check.disabled = star.disabled = remove.disabled = false; }
        };
        check.addEventListener('change', () => { const done = check.checked; check.checked = !!entry.task.done; update({ done }); });
        star.addEventListener('click', () => update({ starred: !entry.task.starred }));
        label.addEventListener('click', () => {
            if (entry.editing) return;
            entry.editing = true; label.hidden = true;
            const controls = el('form', 'task-edit-actions');
            const input = el('input', 'edit', undefined, { 'aria-label': 'Edit task', maxlength: 500 });
            input.value = entry.task.text;
            const save = el('button', 'btn', 'Save', { type: 'submit' });
            const finish = () => { controls.remove(); label.hidden = false; entry.editing = false; label.focus({ preventScroll: true }); };
            controls.append(withEmoji(input), save, button('Cancel', 'btn', finish));
            row.insertBefore(controls, star); input.focus({ preventScroll: true }); input.select();
            controls.addEventListener('submit', async event => {
                event.preventDefault();
                if (!input.value.trim() || save.disabled) return;
                save.disabled = true;
                if (await update({ text: input.value })) finish(); else save.disabled = false;
            });
            input.addEventListener('keydown', event => { if (event.key === 'Escape') { event.preventDefault(); finish(); } });
        });
        row.append(checkTarget, label, aiLink, ai, star, remove);
        return entry;
    }
    function clearCompleted(id) {
        const count = S.todos.filter(task => task.list === id && task.done).length;
        const grid = openDialog('Clear completed tasks');
        grid.append(el('p', '', count ? `Move ${count} completed ${count === 1 ? 'task' : 'tasks'} to Trash? You can restore them together.` : 'There are no completed tasks in this list.'));
        if (!count) return;
        const version = modalVersion;
        dialogSubmit(grid, 'Move completed to Trash', async () => {
            const result = await api('clear-completed', 'POST', { list: id });
            if (version === modalVersion) closeDialog();
            await refresh();
            if (result.undo_id) toast(`${result.count} completed tasks moved to Trash.`, 'Undo', () => restore(result.undo_id));
        });
    }

    function openDialog(title) {
        const modal = $('modal');
        if (!modal.open) modalTrigger = document.activeElement;
        const replacingFocusedContent = modal.open && $('templateGrid').contains(document.activeElement);
        modalVersion++;
        text($('modalTitle'), title);
        const grid = $('templateGrid'); grid.replaceChildren();
        modal.hidden = false;
        if (!modal.open) modal.showModal();
        else if (replacingFocusedContent) $('modalClose').focus({ preventScroll: true });
        return grid;
    }
    function closeDialog() { if ($('modal').open) $('modal').close(); }
    function dialogSubmit(grid, label, action) {
        const error = el('p', 'dialog-error', '', { role: 'alert' }); error.hidden = true;
        const submit = button(label, 'btn btn-primary', async () => {
            submit.disabled = true; error.hidden = true;
            try { await action(); }
            catch (failure) { text(error, failure.message); error.hidden = false; }
            finally { submit.disabled = false; }
        });
        grid.append(error, el('div', 'dialog-actions'));
        grid.lastChild.append(submit);
        return submit;
    }
    function toast(message, label, action) {
        const box = $('workspaceToast');
        if (!box) return;
        box.replaceChildren(el('span', '', message)); delete box.dataset.kind;
        if (action) box.append(button(label, 'toast-action', async event => {
            const control = event.currentTarget; control.disabled = true;
            try { await action(); box.hidden = true; } catch (error) { setError('recovery', error); control.disabled = false; }
        }));
        box.append(button('×', 'icon-btn', () => { box.hidden = true; }, { 'aria-label': 'Dismiss notification' }));
        box.hidden = false;
    }
    async function createBlank(view) {
        const control = $('sideNew');
        if (control.disabled) return;
        control.disabled = true;
        try {
            const item = await api(kinds[view], 'POST', view === 'notes' ? { title: 'Untitled note', body: '' } : { name: view === 'chat' ? 'New channel' : 'New task list' });
            upsert(kinds[view], item);
            setError('create', null); navigate(view, item.id);
        } catch (error) { setError('create', error); } finally { control.disabled = false; }
    }
    function openTemplates(view) {
        const grid = openDialog(`Templates for ${view === 'todos' ? 'tasks' : view}`);
        for (const template of [...builtins[view], ...S.templates.filter(template => template.kind === view)]) {
            const card = button('', 'template', () => previewTemplate(view, template));
            card.append(el('span', 't-icon', template.icon || '▤'), el('span', 't-name', template.name),
                el('span', 't-desc', template.id ? 'Saved workspace template' : template.desc));
            grid.append(card);
        }
    }
    function templatePayload(view, source) {
        return {
            kind: view, name: source.name, icon: source.icon || '',
            ...(view === 'notes' ? { body: source.body || '' } : view === 'chat' ? { intro: source.intro || '' } : { items: source.items || [] }),
        };
    }
    function previewTemplate(view, template) {
        const grid = openDialog('Preview template');
        grid.append(button('← All templates', 'link-btn', () => openTemplates(view)));
        const detail = el('div', 'template-detail');
        const label = el('label', '', `New ${labels[view]} name`);
        const name = el('input', '', undefined, { 'aria-label': `New ${labels[view]} name`, maxlength: limits[view], required: '' });
        name.value = template.name; label.append(withEmoji(name)); detail.append(label);
        if (view === 'notes') { const preview = el('div', 'template-preview note-preview'); markdown(preview, template.body || ''); detail.append(preview); }
        else if (view === 'chat') detail.append(el('p', 'template-preview', template.intro || 'No welcome message. A blank conversation will be created.'));
        else { const list = el('ul', 'template-preview'); for (const item of template.items || []) list.append(el('li', '', item)); detail.append(list); }
        grid.append(detail);
        const version = modalVersion;
        dialogSubmit(grid, 'Create', async () => {
            if (!name.value.trim()) throw new Error('Enter a name.');
            const result = await api('create', 'POST', { ...templatePayload(view, template), name: name.value.trim() });
            upsert(result.kind, result.item);
            const childKind = view === 'chat' ? 'chat' : 'todos';
            for (const child of result.children || []) upsert(childKind, child);
            if (version === modalVersion) { closeDialog(); navigate(view, result.item.id); }
            else { render(); toast(`Created ${result.item.title || result.item.name}.`, 'Open', () => navigate(view, result.item.id)); }
        });
        if (template.id) grid.append(button('Delete saved template', 'link-btn danger', async event => {
            const control = event.currentTarget; control.disabled = true;
            if (await deleteItem('templates', template.id)) openTemplates(view); else control.disabled = false;
        }));
    }
    function saveAsTemplate(view, id) {
        const row = rows(view).find(item => item.id === id);
        if (!row) return;
        const state = view === 'notes' ? stateFor(row) : null;
        const payload = templatePayload(view, {
            name: state?.title || row.title || row.name, icon: row.icon,
            body: state?.body || '', items: S.todos.filter(task => task.list === id).map(task => task.text),
            intro: channelMessages(id)[0]?.text || '',
        });
        const grid = openDialog('Save as template');
        grid.append(el('p', '', view === 'chat' ? 'Captures the first message as a welcome message, not the conversation history. Templates are shared with everyone using this hub.'
            : view === 'todos' ? 'Captures task text only. New tasks start incomplete, without priority. Templates are shared.'
                : 'Captures the text currently in your editor, including your draft. Templates are shared.'));
        const name = el('input', '', undefined, { 'aria-label': 'Template name', maxlength: 100 });
        name.value = payload.name.slice(0, 100);
        const label = el('label', '', 'Template name'); label.append(withEmoji(name)); grid.append(label);
        grid.append(el('pre', 'template-preview', view === 'notes' ? payload.body : view === 'chat' ? payload.intro || 'No welcome message' : payload.items.join('\n')));
        const version = modalVersion;
        dialogSubmit(grid, 'Save template', async () => {
            if (!name.value.trim()) throw new Error('Enter a template name.');
            upsert('templates', await api('templates', 'POST', { ...payload, name: name.value.trim() }));
            if (version === modalVersion) closeDialog();
            toast('Template saved. Find it under Use template.');
        });
    }
    function confirmDelete(view, id) {
        const row = rows(view).find(item => item.id === id);
        if (!row) return;
        const grid = openDialog(`Delete ${labels[view]}?`);
        grid.append(el('p', '', `Move “${row.title || row.name}”${view === 'chat' ? ' and its messages' : view === 'todos' ? ' and its tasks' : ''} to Trash? You can restore it later.`));
        if (view === 'notes' && stateFor(row).dirty) grid.append(el('p', '', 'Your unsaved draft will stay on this device and can be recovered after restoring the note.'));
        const version = modalVersion;
        dialogSubmit(grid, 'Move to Trash', async () => {
            const state = noteStates.get(id);
            if (view === 'notes' && state?.saving) throw new Error('A save is in progress. Try again when it finishes.');
            if (view === 'notes' && state) clearTimeout(state.timer);
            if (await deleteItem(kinds[view], id)) {
                if (version === modalVersion) {
                    closeDialog(); selected[view] = null; store.set('sel', selected); navigate(view); render();
                }
            } else throw new Error('The item could not be moved to Trash. Try again.');
        });
    }
    async function deleteItem(kind, id) {
        const key = `delete:${kind}:${id}`;
        try {
            const result = await api(`${kind}/${id}`, 'DELETE');
            S[kind] = S[kind].filter(item => item.id !== id);
            if (kind === 'notes' && noteStates.has(id)) {
                const state = noteStates.get(id); state.deleted = true; clearTimeout(state.timer);
            }
            if (kind === 'channels') S.chat = S.chat.filter(message => message.channel !== id);
            if (kind === 'lists') S.todos = S.todos.filter(task => task.list !== id);
            setError(key, null); render();
            toast('Moved to Trash.', 'Undo', () => restore(result.undo_id));
            refresh(); return true;
        } catch (error) { setError(key, error); return false; }
    }
    async function restore(id) {
        const result = await api(`trash/${id}/restore`, 'POST', {});
        if (result.item && S[result.kind]) upsert(result.kind, result.item);
        if (result.kind === 'notes' && noteStates.has(result.item?.id)) noteStates.get(result.item.id).deleted = false;
        S.trash = S.trash.filter(item => item.id !== id);
        setError('recovery', null);
        await refresh(); render();
    }
    async function openTrash() {
        const grid = openDialog('Trash');
        const version = modalVersion;
        grid.append(el('p', '', 'Loading Trash…'));
        await refresh();
        if (version !== modalVersion || !$('modal').open) return;
        grid.replaceChildren(el('p', '', 'Deleted items stay here until restored. Restoring a channel or list also restores its contents.'));
        if (!loaded || errors.has('connection')) grid.append(el('p', 'dialog-error', 'Trash could not be refreshed. Entries below may be out of date.'));
        if (loaded && !S.trash.length) grid.append(el('p', '', 'Trash is empty.'));
        for (const item of S.trash) {
            const row = el('div', 'template-detail');
            row.append(el('strong', '', item.label), el('span', 'hint', ` ${item.kind} · ${ago(item.ts)}`));
            const error = el('p', 'dialog-error', '', { role: 'alert' }); error.hidden = true;
            const control = button('Restore', 'btn', async () => {
                control.disabled = true;
                try { await restore(item.id); row.remove(); toast('Restored from Trash.'); }
                catch (failure) { text(error, failure.message); error.hidden = false; control.disabled = false; }
            });
            row.append(control, error); grid.append(row);
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        store.set('name', me);
        setError('startup', null);
        document.querySelectorAll('.nav-item[data-view]').forEach(node => node.addEventListener('click', event => {
            event.preventDefault(); navigate(node.dataset.view);
        }));
        $('sideNew').addEventListener('click', () => createBlank(mode));
        $('sideTemplates')?.addEventListener('click', () => openTemplates(mode));
        $('workspaceTrash')?.addEventListener('click', openTrash);
        $('sideSearch').addEventListener('input', event => { search = event.target.value; renderSide(); });
        $('modalClose').addEventListener('click', closeDialog);
        $('modal').addEventListener('close', () => {
            modalVersion++;
            if (modalTrigger?.isConnected) modalTrigger.focus({ preventScroll: true });
        });
        $('modal').addEventListener('click', event => {
            if (event.target !== $('modal')) return;
            const bounds = $('modal').getBoundingClientRect();
            if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeDialog();
        });
        window.addEventListener('hashchange', applyRoute);
        window.addEventListener('beforeunload', event => {
            const unsaved = [...noteStates.values()].some(state => state.dirty || state.saving)
                || Object.values(outbox).some(entries => entries.length)
                || (errors.has('storage') && Object.values(chatDrafts).some(Boolean));
            if (unsaved) { event.preventDefault(); event.returnValue = ''; }
        });
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) flushNotes();
            else { refresh(); if (pane?.view === 'chat') markSeen(pane.id); }
        });
        window.addEventListener('online', refresh);
        setInterval(() => { if (!document.hidden) refresh(); }, 5000);
        applyRoute(); refresh();
    });
})();
