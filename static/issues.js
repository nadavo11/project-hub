(() => {
    'use strict';
    const API = '/api/issues';
    const STATUSES = { open: 'Open', in_progress: 'In progress', in_review: 'In review', done: 'Done', closed: "Closed (won't fix)" };
    const CLOSED = ['done', 'closed'];
    const PRIORITIES = { low: 'Low', medium: 'Medium', high: 'High', critical: 'Critical' };
    const TYPES = { bug: 'Bug', feature: 'Feature', task: 'Task', question: 'Question' };
    const TEMPLATES = {
        bug: '## Summary\n\n## Steps to reproduce\n1. \n\n## Expected behaviour\n\n## Actual behaviour\n\n## Environment and logs\n',
        feature: '## Problem\n\n## Proposed solution\n\n## Alternatives considered\n',
        task: '## Goal\n\n## Acceptance criteria\n- [ ] \n',
        question: '## Question\n\n## What I have tried\n',
    };
    const root = document.getElementById('tab-issues');
    const badge = document.getElementById('badge-issues');
    const filters = { state: 'open', q: '', type: '', priority: '', assignee: '', label: '', project: '', sort: 'updated' };
    let ai = {}, issues = [], loaded = false, layout = 'board', route = null, current = null, ui = null;
    let busy = false, toastTimer = 0;

    const me = () => {
        try { return JSON.parse(localStorage.getItem('hub:name')) || 'Guest'; } catch { return 'Guest'; }
    };
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
    const projectOptions = () => Object.fromEntries(HubProjects.all().map(project => [project.id, project.name]));
    const projectBadge = issue => HubProjects.badge(issue.project);
    function select(options, value, onChange, label, blank) {
        const node = el('select', 'iss-select', undefined, { 'aria-label': label });
        if (blank !== undefined) node.append(new Option(blank, ''));
        for (const [key, text] of Object.entries(options)) node.append(new Option(text, key));
        node.value = value;
        node.addEventListener('change', () => onChange(node.value));
        return node;
    }
    function ago(stamp) {
        const seconds = Math.max(0, (Date.now() - Date.parse(stamp)) / 1000);
        if (seconds < 60) return 'just now';
        for (const [size, unit] of [[86400 * 30, 'mo'], [86400, 'd'], [3600, 'h'], [60, 'm']]) {
            if (seconds >= size) return `${Math.floor(seconds / size)}${unit} ago`;
        }
        return 'just now';
    }
    const when = stamp => el('time', '', ago(stamp), { datetime: stamp, title: new Date(stamp).toLocaleString() });
    const aiLabels = { working: 'AI working…', needs_input: 'AI needs your reply', failed: 'AI failed', stopped: 'AI stopped', done: 'AI report' };
    function aiLink(number) {
        const link = ai[number], label = link && aiLabels[link.state];
        if (!label) return null;
        const badge = el('a', `ai-link ${link.state}`, `✨ ${label} →`, { href: `#chat/${link.channel}/thread/${link.thread}`, title: 'Open the AI discussion for this issue' });
        if (link.agent) badge.prepend(hubAgentIdentity.avatar(link.agent, 'agent-avatar'));
        return badge;
    }
    function who(name, number) {
        const short = hubAgentIdentity.actorShort(name) || (name === 'AI' && ai[number]?.agent) || '';
        if (!short) return el('strong', '', name);
        const node = el('strong', 'agent-actor');
        node.append(hubAgentIdentity.avatar(short, 'agent-avatar'), hubAgentIdentity.name(short));
        return node;
    }
    const isClosed = issue => CLOSED.includes(issue.status);
    const overdue = issue => issue.due && !isClosed(issue) && issue.due < new Date().toLocaleDateString('sv');

    function toast(message, isError) {
        let node = document.getElementById('issuesToast');
        if (!node) { node = el('div', 'iss-toast', undefined, { id: 'issuesToast', role: 'status', 'aria-live': 'polite' }); document.body.append(node); }
        node.textContent = message;
        node.classList.toggle('error', Boolean(isError));
        node.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => node.classList.remove('show'), isError ? 6000 : 2500);
    }
    async function api(path, method = 'GET', body, base = API) {
        let response;
        try {
            response = await fetch(base + path, {
                method, headers: body ? { 'Content-Type': 'application/json' } : {},
                body: body ? JSON.stringify({ actor: me(), ...body }) : undefined,
            });
        } catch { throw new Error('Could not reach the server. Check your connection and retry.'); }
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw Object.assign(new Error(data.error || 'Request failed.'), { status: response.status, current: data.current });
        return data;
    }
    function updateBadge() {
        const open = issues.filter(issue => !isClosed(issue)).length;
        badge.hidden = !open;
        badge.textContent = open > 99 ? '99+' : String(open);
    }
    HubProjects.ready.then(() => { if (!root.hidden && route === null && loaded) { ui = null; renderList(); } });
    async function load() {
        if (busy) return;
        busy = true;
        try {
            const data = await api('');
            issues = data.issues; ai = data.ai || {};
            loaded = true;
            updateBadge();
            if (!root.hidden) { if (route === null) renderList(); else if (ui?.kind === 'detail') { await refreshDetail(); if (ui?.kind === 'detail' && current) { paintHeader(); paintTimeline(); } } }
        } catch (error) {
            if (!root.hidden && !loaded) renderFatal(error.message);
        } finally { busy = false; }
    }
    function renderFatal(message) {
        root.replaceChildren(el('div', 'empty-state', message), button('Retry', 'btn btn-primary', load));
    }

    function go(hash) {
        if (location.hash === hash) show(); else location.hash = hash;
    }
    function show() {
        const parts = location.hash.slice(1).split('/');
        if (parts[0] !== 'issues') return;
        ui = null;
        if (parts[1] === 'new') { route = 'new'; renderForm(); }
        else if (/^\d+$/.test(parts[1] || '')) { route = Number(parts[1]); renderDetail(route); }
        else { route = null; renderList(); }
    }

    // ---- list and board ----
    function matches(issue) {
        const { state, q, type, priority, assignee, label, project } = filters;
        if (state === 'open' && isClosed(issue)) return false;
        if (state === 'closed' && !isClosed(issue)) return false;
        if (type && issue.type !== type) return false;
        if (priority && issue.priority !== priority) return false;
        if (assignee === '__none' ? issue.assignee : assignee && issue.assignee !== assignee) return false;
        if (label && !issue.labels.includes(label)) return false;
        if (project && (issue.project || '') !== (project === '__none' ? '' : project)) return false;
        const needle = q.trim().toLowerCase();
        return !needle || `#${issue.number} ${issue.title} ${issue.body} ${issue.reporter} ${issue.assignee} ${issue.labels.join(' ')}`.toLowerCase().includes(needle);
    }
    const rank = { critical: 0, high: 1, medium: 2, low: 3 };
    const sorters = {
        updated: (a, b) => b.updated_at.localeCompare(a.updated_at),
        newest: (a, b) => b.number - a.number,
        oldest: (a, b) => a.number - b.number,
        priority: (a, b) => rank[a.priority] - rank[b.priority] || b.updated_at.localeCompare(a.updated_at),
        due: (a, b) => (a.due || '9999').localeCompare(b.due || '9999') || a.number - b.number,
        comments: (a, b) => b.comment_count - a.comment_count,
    };
    function pill(text, kind, value) { return el('span', `pill ${kind} ${kind}-${value}`, text); }
    function labelPills(issue) {
        const wrap = el('span', 'labels');
        for (const label of issue.labels) wrap.append(el('span', 'label-chip', label));
        return wrap;
    }
    function statusIcon(issue) {
        const node = el('span', `state-icon s-${issue.status}`, undefined, { title: STATUSES[issue.status], role: 'img', 'aria-label': STATUSES[issue.status] });
        node.textContent = { open: '○', in_progress: '◐', in_review: '◕', done: '✓', closed: '⊘' }[issue.status];
        return node;
    }
    function row(issue) {
        const link = el('a', 'iss-title', issue.title, { href: `#issues/${issue.number}` });
        const meta = el('div', 'iss-meta');
        meta.append(el('span', '', `#${issue.number}`), el('span', '', `opened by ${hubAgentIdentity.actorShort(issue.reporter) ? hubAgentIdentity.name(hubAgentIdentity.actorShort(issue.reporter)) : issue.reporter}`), when(issue.created_at));
        if (issue.assignee) meta.append(el('span', '', `→ ${issue.assignee}`));
        if (issue.due) meta.append(el('span', overdue(issue) ? 'due overdue' : 'due', `due ${issue.due}${overdue(issue) ? ' (overdue)' : ''}`));
        if (issue.comment_count) meta.append(el('span', '', `💬 ${issue.comment_count}`));
        const aiBadge = aiLink(issue.number);
        if (aiBadge) meta.append(aiBadge);
        const main = el('div', 'iss-main');
        const head = el('div', 'iss-head');
        head.append(link, pill(TYPES[issue.type], 'type', issue.type), pill(PRIORITIES[issue.priority], 'prio', issue.priority), ...[projectBadge(issue)].filter(Boolean), labelPills(issue));
        main.append(head, meta);
        const item = el('li', `iss-row${isClosed(issue) ? ' closed' : ''}`);
        item.append(statusIcon(issue), main);
        return item;
    }
    function card(issue) {
        const item = el('li', 'board-card', undefined, { draggable: 'true', 'data-number': issue.number });
        const link = el('a', 'iss-title', issue.title, { href: `#issues/${issue.number}` });
        const meta = el('div', 'iss-meta');
        meta.append(el('span', '', `#${issue.number}`), pill(PRIORITIES[issue.priority], 'prio', issue.priority), pill(TYPES[issue.type], 'type', issue.type));
        if (issue.assignee) meta.append(el('span', '', `→ ${issue.assignee}`));
        if (issue.project) meta.append(projectBadge(issue));
        const mover = select(STATUSES, issue.status, status => patch(issue.number, { status }, issue.rev), `Move issue ${issue.number} to`);
        const aiBadge = aiLink(issue.number);
        if (aiBadge) meta.append(aiBadge);
        item.append(link, meta, labelPills(issue), mover);
        item.addEventListener('dragstart', event => { event.dataTransfer.setData('text/plain', String(issue.number)); event.dataTransfer.effectAllowed = 'move'; });
        return item;
    }
    async function patch(number, fields, rev) {
        try {
            const updated = await api(`/${number}`, 'PATCH', { ...fields, rev });
            const index = issues.findIndex(issue => issue.number === number);
            if (index >= 0) issues[index] = { ...updated, comments: undefined, activity: undefined, comment_count: updated.comments.length };
            updateBadge();
            return updated;
        } catch (error) {
            toast(error.message, true);
            await load();
            if (route === number) renderDetail(number);
            return null;
        } finally {
            if (route === null) renderList();
        }
    }
    function distinct(key) {
        return [...new Set(issues.flatMap(issue => key === 'labels' ? issue.labels : issue[key] ? [issue[key]] : []))].sort((a, b) => a.localeCompare(b));
    }
    function renderList() {
        if (ui?.kind !== 'list') {
            root.replaceChildren();
            const head = el('div', 'iss-bar');
            head.append(el('h2', '', 'Issues'));
            const search = el('input', 'iss-search', undefined, { type: 'search', placeholder: 'Search issues…', 'aria-label': 'Search issues', autocomplete: 'off', value: filters.q });
            search.addEventListener('input', () => { filters.q = search.value; renderResults(); });
            const toggle = el('div', 'seg', undefined, { role: 'group', 'aria-label': 'Layout' });
            for (const [key, text] of [['list', 'List'], ['board', 'Board']]) {
                toggle.append(button(text, 'seg-btn', () => { layout = key; renderList(); }, { 'aria-pressed': String(layout === key) }));
            }
            const aiButton = button('✨ AI add issue', 'btn', () => { ui.aiPanel.hidden = !ui.aiPanel.hidden; if (!ui.aiPanel.hidden) ui.aiText.focus(); }, { title: 'Describe a problem or idea; an agent turns it into a complete issue' });
            head.append(search, toggle, aiButton, button('New issue', 'btn btn-primary', () => go('#issues/new')));
            const aiPanel = el('form', 'ai-panel');
            aiPanel.hidden = true;
            const aiText = el('textarea', 'iss-input', undefined, { rows: '4', maxlength: '5000', 'aria-label': 'Describe the issue for the AI', placeholder: 'Describe the problem or idea in your own words. The AI will investigate and write a complete issue.' });
            const aiError = el('p', 'iss-error', undefined, { role: 'alert' });
            aiError.hidden = true;
            const aiSend = el('button', 'btn btn-primary', '✨ Create with AI', { type: 'submit' });
            const aiActions = el('div', 'iss-actions');
            aiActions.append(button('Cancel', 'btn btn-secondary', () => { aiPanel.hidden = true; }), aiSend);
            const aiProject = select(projectOptions(), filters.project && filters.project !== '__none' ? filters.project : '', () => {}, 'Project for the AI', 'No project');
            aiPanel.append(aiText, aiProject, aiError, aiActions);
            aiPanel.addEventListener('submit', async event => {
                event.preventDefault();
                if (!aiText.value.trim()) { aiError.textContent = 'Describe the issue first.'; aiError.hidden = false; return; }
                aiSend.disabled = true; aiError.hidden = true;
                try {
                    const result = await api('/ai-add', 'POST', { description: aiText.value, project: aiProject.value }, '/api/agents/issues');
                    aiText.value = ''; aiPanel.hidden = true;
                    toast(`Issue #${result.issue} created. The AI is working on it.`);
                    await load();
                } catch (error) {
                    aiError.textContent = error.status === 401
                        ? 'Unlock Agent chat in the heart channel first, then try again.'
                        : `AI add issue failed: ${error.message}`;
                    aiError.hidden = false;
                } finally { aiSend.disabled = false; }
            });
            const bar = el('div', 'iss-filters');
            const results = el('div', 'iss-results');
            root.append(head, aiPanel, bar, results);
            ui = { kind: 'list', bar, results, search, toggle, aiPanel, aiText };
        }
        ui.toggle.querySelectorAll('.seg-btn').forEach((node, index) => node.setAttribute('aria-pressed', String(layout === ['list', 'board'][index])));
        renderFilters();
        renderResults();
    }
    function renderFilters() {
        const { bar } = ui;
        const focus = document.activeElement?.dataset?.filter;
        bar.replaceChildren();
        const counts = { open: issues.filter(issue => !isClosed(issue)).length, closed: issues.filter(isClosed).length };
        const tabs = el('div', 'seg', undefined, { role: 'group', 'aria-label': 'State' });
        for (const [key, text] of [['open', `Open ${counts.open}`], ['closed', `Closed ${counts.closed}`], ['all', `All ${issues.length}`]]) {
            tabs.append(button(text, 'seg-btn', () => { filters.state = key; renderList(); }, { 'aria-pressed': String(filters.state === key), 'data-filter': `state-${key}` }));
        }
        bar.append(tabs);
        const pick = (key, options, label, blank) => {
            const node = select(options, filters[key], value => { filters[key] = value; renderList(); }, label, blank);
            node.dataset.filter = key;
            bar.append(node);
        };
        pick('type', TYPES, 'Filter by type', 'Any type');
        pick('priority', PRIORITIES, 'Filter by priority', 'Any priority');
        pick('assignee', { __none: 'Unassigned', ...Object.fromEntries(distinct('assignee').map(name => [name, name])) }, 'Filter by assignee', 'Any assignee');
        pick('project', { __none: 'No project', ...projectOptions() }, 'Filter by project', 'Any project');
        pick('label', Object.fromEntries(distinct('labels').map(name => [name, name])), 'Filter by label', 'Any label');
        pick('sort', { updated: 'Recently updated', newest: 'Newest', oldest: 'Oldest', priority: 'Priority', due: 'Due date', comments: 'Most commented' }, 'Sort issues');
        if (focus) bar.querySelector(`[data-filter="${focus}"]`)?.focus({ preventScroll: true });
    }
    function renderResults() {
        const { results } = ui;
        results.replaceChildren();
        if (!loaded) { results.append(el('div', 'empty-state', 'Loading issues…')); return; }
        const shown = issues.filter(matches).sort(sorters[filters.sort]);
        results.dataset.count = String(shown.length);
        if (!shown.length) {
            const empty = el('div', 'empty-state');
            const filtered = filters.q || filters.type || filters.priority || filters.assignee || filters.label || filters.project;
            empty.append(el('h3', '', issues.length ? (filtered ? 'No issues match these filters' : `No ${filters.state === 'all' ? '' : filters.state + ' '}issues`) : 'No issues yet'),
                el('p', '', issues.length ? 'Try changing the search or filters.' : 'Report a bug, request a feature or track a task from start to finish.'),
                button('New issue', 'btn btn-primary', () => go('#issues/new')));
            results.append(empty);
            return;
        }
        if (layout === 'board') {
            const board = el('div', 'board');
            for (const [status, text] of Object.entries(STATUSES)) {
                const column = el('section', 'board-col', undefined, { 'aria-label': text, 'data-status': status });
                const items = shown.filter(issue => issue.status === status);
                column.append(el('h3', '', `${text} · ${items.length}`));
                const list = el('ul', 'board-list');
                for (const issue of items) list.append(card(issue));
                column.append(list);
                column.addEventListener('dragover', event => { event.preventDefault(); column.classList.add('over'); });
                column.addEventListener('dragleave', () => column.classList.remove('over'));
                column.addEventListener('drop', event => {
                    event.preventDefault(); column.classList.remove('over');
                    const issue = issues.find(item => item.number === Number(event.dataTransfer.getData('text/plain')));
                    if (issue && issue.status !== status) patch(issue.number, { status }, issue.rev);
                });
                board.append(column);
            }
            results.append(board);
        } else {
            const list = el('ul', 'iss-list');
            for (const issue of shown) list.append(row(issue));
            results.append(list);
        }
    }

    // ---- new issue ----
    function field(label, control, hint) {
        const wrap = el('label', 'iss-field');
        wrap.append(el('span', 'iss-label', label), control);
        if (hint) wrap.append(el('span', 'iss-hint', hint));
        return wrap;
    }
    function renderForm() {
        const form = el('form', 'iss-form');
        form.noValidate = true;
        const title = el('input', 'iss-input', undefined, { maxlength: '200', required: '', placeholder: 'Short, specific summary', autocomplete: 'off' });
        const type = select(TYPES, 'bug', value => { if (!body.value.trim() || Object.values(TEMPLATES).includes(body.value)) body.value = TEMPLATES[value]; }, 'Type');
        const priority = select(PRIORITIES, 'medium', () => {}, 'Priority');
        const project = select(projectOptions(), '', () => {}, 'Project', 'No project');
        const assignee = el('input', 'iss-input', undefined, { maxlength: '40', placeholder: 'Name (optional)', list: 'issueAssignees', autocomplete: 'off' });
        const datalist = el('datalist', '', undefined, { id: 'issueAssignees' });
        for (const name of distinct('assignee')) datalist.append(new Option(name));
        const labels = el('input', 'iss-input', undefined, { placeholder: 'comma, separated', autocomplete: 'off' });
        const due = el('input', 'iss-input', undefined, { type: 'date' });
        const body = el('textarea', 'iss-input iss-body', undefined, { maxlength: '20000', rows: '12', placeholder: 'Describe the issue. Markdown is supported.' });
        body.value = TEMPLATES.bug;
        const error = el('p', 'iss-error', undefined, { role: 'alert' });
        error.hidden = true;
        const submit = el('button', 'btn btn-primary', 'Report issue', { type: 'submit' });
        form.append(el('h2', '', 'New issue'), field('Title', title), field('Description', body),
            el('div', 'iss-grid', undefined), error);
        form.querySelector('.iss-grid').append(field('Type', type), field('Priority', priority), field('Project', project), field('Assignee', assignee), field('Due date', due), field('Labels', labels), datalist);
        const actions = el('div', 'iss-actions');
        actions.append(submit, button('Cancel', 'btn btn-secondary', () => go('#issues')));
        form.append(actions);
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (!title.value.trim()) { error.textContent = 'Enter a title.'; error.hidden = false; title.focus(); return; }
            submit.disabled = true; error.hidden = true;
            try {
                const created = await api('', 'POST', {
                    title: title.value, body: body.value.trim() === TEMPLATES[type.value].trim() ? '' : body.value, type: type.value, priority: priority.value, project: project.value,
                    assignee: assignee.value, due: due.value, labels: labels.value.split(',').map(item => item.trim()).filter(Boolean),
                });
                issues.push({ ...created, comments: undefined, activity: undefined, comment_count: 0 });
                updateBadge();
                toast(`Issue #${created.number} reported`);
                go(`#issues/${created.number}`);
            } catch (failure) {
                error.textContent = failure.message; error.hidden = false; submit.disabled = false;
            }
        });
        root.replaceChildren(form);
        ui = { kind: 'form' };
        title.focus({ preventScroll: true });
    }

    // ---- detail ----
    async function renderDetail(number) {
        ui = { kind: 'detail', number, editing: new Set() };
        root.replaceChildren(el('div', 'empty-state', 'Loading issue…'));
        try {
            current = await api(`/${number}`);
        } catch (error) {
            if (route !== number) return;
            const box = el('div', 'empty-state');
            box.append(el('h3', '', error.status === 404 ? 'Issue not found' : 'Could not load the issue'), el('p', '', error.message),
                button('Back to issues', 'btn btn-primary', () => go('#issues')));
            root.replaceChildren(box);
            return;
        }
        if (route !== number) return;
        buildDetail();
    }
    async function refreshDetail() {
        const number = ui.number;
        try {
            const latest = await api(`/${number}`);
            if (route !== number || ui?.kind !== 'detail') return;
            if (latest.rev === current.rev && latest.comments.length === current.comments.length && latest.comments.every((c, i) => c.edited_at === current.comments[i].edited_at)) return;
            current = latest;
            paintSide(); paintTimeline();
            if (!ui.editing.has('title')) paintHeader();
            if (!ui.editing.has('body')) paintBody();
        } catch (error) {
            if (error.status === 404 && route === number) renderDetail(number);
        }
    }
    function buildDetail() {
        const wrap = el('div', 'iss-detail');
        const back = el('a', 'back-link', '← All issues', { href: '#issues' });
        ui.header = el('header', 'dt-head');
        ui.bodyBox = el('section', 'dt-body');
        ui.timeline = el('ol', 'timeline');
        ui.side = el('aside', 'dt-side', undefined, { 'aria-label': 'Issue details' });
        const comment = el('form', 'comment-form');
        const text = el('textarea', 'iss-input', undefined, { rows: '4', maxlength: '10000', placeholder: 'Leave a comment (Markdown supported)', 'aria-label': 'Comment' });
        const err = el('p', 'iss-error', undefined, { role: 'alert' });
        err.hidden = true;
        const send = el('button', 'btn btn-primary', 'Comment', { type: 'submit' });
        const toggle = button('', 'btn btn-secondary', null);
        ui.toggle = toggle;
        const actions = el('div', 'iss-actions');
        actions.append(toggle, send);
        comment.append(text, err, actions);
        text.addEventListener('keydown', event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); comment.requestSubmit(); } });
        comment.addEventListener('submit', async event => {
            event.preventDefault();
            if (!text.value.trim()) { err.textContent = 'Write something first.'; err.hidden = false; return; }
            send.disabled = true; err.hidden = true;
            try {
                const created = await api(`/${current.number}/comments`, 'POST', { text: text.value });
                current.comments.push(created); text.value = '';
                paintTimeline(); noteComment(1);
            } catch (failure) { err.textContent = failure.message; err.hidden = false; }
            send.disabled = false;
        });
        toggle.addEventListener('click', async () => {
            const closing = !isClosed(current);
            const body = { status: closing ? 'done' : 'open' };
            if (closing && text.value.trim()) {
                try { current.comments.push(await api(`/${current.number}/comments`, 'POST', { text: text.value })); text.value = ''; noteComment(1); } catch (failure) { toast(failure.message, true); return; }
            }
            await change(body);
        });
        const main = el('div', 'dt-main');
        main.append(ui.bodyBox, ui.timeline, comment);
        const layoutBox = el('div', 'dt-layout');
        layoutBox.append(main, ui.side);
        wrap.append(back, ui.header, layoutBox);
        root.replaceChildren(wrap);
        paintHeader(); paintBody(); paintSide(); paintTimeline();
    }
    function noteComment(delta) {
        const summary = issues.find(issue => issue.number === current.number);
        if (summary) summary.comment_count += delta;
    }
    async function change(fields) {
        try {
            current = await api(`/${current.number}`, 'PATCH', { ...fields, rev: current.rev });
            const index = issues.findIndex(issue => issue.number === current.number);
            if (index >= 0) issues[index] = { ...current, comments: undefined, activity: undefined, comment_count: current.comments.length };
            updateBadge();
            paintHeader(); paintBody(); paintSide(); paintTimeline();
            return true;
        } catch (error) {
            toast(error.message, true);
            if (error.status === 409) { current = await api(`/${current.number}`).catch(() => current); paintHeader(); paintBody(); paintSide(); paintTimeline(); }
            return false;
        }
    }
    function paintHeader() {
        const { header } = ui;
        header.replaceChildren();
        const titleRow = el('div', 'dt-title');
        titleRow.append(el('h2', '', current.title), el('span', 'dt-num', `#${current.number}`));
        const edit = button('Edit', 'link-btn', () => {
            ui.editing.add('title');
            const input = el('input', 'iss-input', undefined, { maxlength: '200', 'aria-label': 'Title', value: current.title });
            const save = async () => {
                if (!input.value.trim()) { toast('A title is required.', true); return; }
                if (input.value.trim() !== current.title && !(await change({ title: input.value }))) return;
                ui.editing.delete('title'); paintHeader();
            };
            input.addEventListener('keydown', event => { if (event.key === 'Enter') save(); if (event.key === 'Escape') { ui.editing.delete('title'); paintHeader(); } });
            titleRow.replaceChildren(input, button('Save', 'btn btn-primary btn-sm', save), button('Cancel', 'btn btn-secondary btn-sm', () => { ui.editing.delete('title'); paintHeader(); }));
            input.focus(); input.select();
        });
        titleRow.append(edit);
        const sub = el('div', 'iss-meta');
        const state = el('span', `state-pill s-${current.status}`, STATUSES[current.status]);
        sub.append(state, el('span', '', `${current.reporter} opened this`), when(current.created_at));
        if (current.closed_at) sub.append(el('span', '', '· closed'), when(current.closed_at));
        const aiBadge = aiLink(current.number);
        if (aiBadge) sub.append(aiBadge);
        header.append(titleRow, sub);
        document.title = `#${current.number} ${current.title} · Project Hub`;
    }
    function markdown(node, text) {
        if (typeof hubMarkdown !== 'undefined') node.replaceChildren(hubMarkdown.render(text));
        else node.textContent = text;
    }
    function paintBody() {
        const box = ui.bodyBox;
        box.replaceChildren();
        const head = el('div', 'dt-box-head');
        head.append(el('strong', '', 'Description'), button('Edit', 'link-btn', () => {
            ui.editing.add('body');
            const area = el('textarea', 'iss-input iss-body', undefined, { rows: '10', maxlength: '20000', 'aria-label': 'Description' });
            area.value = current.body;
            const done = () => { ui.editing.delete('body'); paintBody(); };
            const actions = el('div', 'iss-actions');
            actions.append(button('Save', 'btn btn-primary', async () => { if (area.value === current.body || await change({ body: area.value })) done(); }), button('Cancel', 'btn btn-secondary', done));
            box.replaceChildren(head, area, actions);
            area.focus();
        }));
        const content = el('div', 'md');
        if (current.body.trim()) markdown(content, current.body); else content.append(el('p', 'muted', 'No description provided.'));
        box.append(head, content);
    }
    function sideRow(label, control) {
        const wrap = el('div', 'side-row');
        wrap.append(el('span', 'iss-label', label), control);
        return wrap;
    }
    function paintSide() {
        const { side } = ui;
        side.replaceChildren();
        ui.toggle.textContent = isClosed(current) ? 'Reopen issue' : 'Close as done';
        side.append(
            sideRow('Status', select(STATUSES, current.status, status => change({ status }), 'Status')),
            sideRow('Priority', select(PRIORITIES, current.priority, priority => change({ priority }), 'Priority')),
            sideRow('Type', select(TYPES, current.type, type => change({ type }), 'Type')),
            sideRow('Project', select(projectOptions(), current.project || '', project => change({ project }), 'Project', 'No project')),
        );
        const assignee = el('input', 'iss-input', undefined, { maxlength: '40', 'aria-label': 'Assignee', placeholder: 'Unassigned', value: current.assignee, list: 'issueAssignees' });
        const datalist = el('datalist', '', undefined, { id: 'issueAssignees' });
        for (const name of distinct('assignee')) datalist.append(new Option(name));
        assignee.addEventListener('change', () => change({ assignee: assignee.value }));
        const mine = button('Assign to me', 'link-btn', () => change({ assignee: me() }));
        side.append(sideRow('Assignee', assignee), datalist, mine);
        const due = el('input', 'iss-input', undefined, { type: 'date', 'aria-label': 'Due date', value: current.due });
        due.addEventListener('change', () => change({ due: due.value }));
        side.append(sideRow('Due date', due));
        const labels = el('input', 'iss-input', undefined, { 'aria-label': 'Labels', placeholder: 'comma, separated', value: current.labels.join(', ') });
        labels.addEventListener('change', () => change({ labels: labels.value.split(',').map(item => item.trim()).filter(Boolean) }));
        side.append(sideRow('Labels', labels));
        side.append(button('Delete issue', 'btn btn-danger', async () => {
            if (!confirm(`Delete issue #${current.number} permanently? This cannot be undone.`)) return;
            try {
                await api(`/${current.number}`, 'DELETE');
                issues = issues.filter(issue => issue.number !== current.number);
                updateBadge(); toast(`Issue #${current.number} deleted`); go('#issues');
            } catch (error) { toast(error.message, true); }
        }));
    }
    function describe(entry) {
        const text = value => Array.isArray(value) ? (value.join(', ') || 'none') : (STATUSES[value] || PRIORITIES[value] || TYPES[value] || value || 'none');
        switch (entry.type) {
            case 'created': return 'opened this issue';
            case 'edited': return `edited the ${entry.field}`;
            case 'renamed': return `renamed from “${entry.from}” to “${entry.to}”`;
            case 'labels': return `changed labels: ${text(entry.from)} → ${text(entry.to)}`;
            case 'due': return `changed the due date: ${entry.from || 'none'} → ${entry.to || 'none'}`;
            default: return `changed ${entry.type}: ${text(entry.from)} → ${text(entry.to)}`;
        }
    }
    function paintTimeline() {
        const events = [
            ...current.activity.filter(entry => entry.type !== 'created').map(entry => ({ at: entry.at, entry })),
            ...current.comments.map(comment => ({ at: comment.created_at, comment })),
        ].sort((a, b) => a.at.localeCompare(b.at));
        const keep = ui.timeline.querySelector('textarea:focus');
        if (keep) return;
        ui.timeline.replaceChildren();
        for (const { entry, comment } of events) {
            const item = el('li', entry ? 'tl-event' : 'tl-comment');
            if (entry) {
                item.append(who(entry.actor, current.number), ' ', describe(entry), ' ', when(entry.at));
            } else {
                const head = el('div', 'dt-box-head');
                const byline = el('span');
                byline.append(who(comment.author, current.number), ' commented ', when(comment.created_at));
                if (comment.edited_at) byline.append(' · edited');
                head.append(byline);
                const content = el('div', 'md');
                markdown(content, comment.text);
                if (comment.author === me()) {
                    const actions = el('span', 'tl-actions');
                    actions.append(button('Edit', 'link-btn', () => {
                        const area = el('textarea', 'iss-input', undefined, { rows: '4', maxlength: '10000', 'aria-label': 'Edit comment' });
                        area.value = comment.text;
                        const save = button('Save', 'btn btn-primary btn-sm', async () => {
                            if (!area.value.trim()) return;
                            try { Object.assign(comment, await api(`/${current.number}/comments/${comment.id}`, 'PATCH', { text: area.value })); paintTimeline(); } catch (error) { toast(error.message, true); }
                        });
                        item.replaceChildren(head, area, el('div', 'iss-actions'));
                        item.lastChild.append(save, button('Cancel', 'btn btn-secondary btn-sm', paintTimeline));
                        area.focus();
                    }), button('Delete', 'link-btn danger', async () => {
                        if (!confirm('Delete this comment?')) return;
                        try { await api(`/${current.number}/comments/${comment.id}`, 'DELETE'); current.comments = current.comments.filter(item => item.id !== comment.id); noteComment(-1); paintTimeline(); } catch (error) { toast(error.message, true); }
                    }));
                    head.append(actions);
                }
                item.append(head, content);
            }
            ui.timeline.append(item);
        }
    }

    window.addEventListener('hub-view', event => {
        if (event.detail.view !== 'issues') { document.title = 'Project Hub'; return; }
        document.title = 'Issues · Project Hub';
        show();
        load();
    });
    document.addEventListener('DOMContentLoaded', load);
    setInterval(() => { if (!document.hidden) load(); }, 10000);
})();
