(() => {
    'use strict';
    let projects = [];
    const listeners = new Set();
    const hue = id => [...id].reduce((sum, char) => (sum * 31 + char.charCodeAt(0)) % 360, 7);

    const load = fetch('/api/project-registry', { credentials: 'same-origin' })
        .then(response => (response.ok ? response.json() : { projects: [] }))
        .then(data => { projects = Array.isArray(data.projects) ? data.projects : []; listeners.forEach(fn => fn()); })
        .catch(() => {});

    const nameOf = id => projects.find(project => project.id === id)?.name || id || '';

    const NEW = '__new__';

    function createBadge() {
        return new Promise(resolve => {
            const overlay = document.createElement('div');
            overlay.className = 'proj-modal';
            const form = document.createElement('form');
            form.className = 'proj-form';
            form.innerHTML = `<h3>New badge</h3>
<label>Name<input name="name" maxlength="40" required autocomplete="off"></label>
<label>Directory<input name="directory" placeholder="/home/you/my-project" required autocomplete="off"></label>
<label>Description (optional)<textarea name="description" rows="3" maxlength="2000"></textarea></label>
<fieldset><legend>Manager agent</legend>
<label class="inline"><input type="radio" name="mode" value="new" checked> Create a new Astra</label>
<label class="inline"><input type="radio" name="mode" value="existing"> Use an existing agent</label>
<label class="thread" hidden>Agent thread number<input name="thread" type="number" min="1"></label></fieldset>
<p class="proj-error" role="alert" hidden></p>
<div class="proj-actions"><button type="button" data-cancel>Cancel</button><button type="submit">Create badge</button></div>`;
            overlay.append(form);
            document.body.append(overlay);
            const error = form.querySelector('.proj-error');
            const threadLabel = form.querySelector('.thread');
            const close = value => { overlay.remove(); resolve(value); };
            form.addEventListener('change', () => { threadLabel.hidden = form.mode.value !== 'existing'; });
            form.querySelector('[data-cancel]').addEventListener('click', () => close(null));
            overlay.addEventListener('mousedown', event => { if (event.target === overlay) close(null); });
            overlay.addEventListener('keydown', event => { if (event.key === 'Escape') close(null); });
            form.addEventListener('submit', async event => {
                event.preventDefault();
                const agent = form.mode.value === 'existing' ? { mode: 'existing', thread: Number(form.thread.value) } : { mode: 'new' };
                try {
                    const response = await fetch('/api/agents/projects', {
                        method: 'POST', credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: form.name.value, directory: form.directory.value.trim(), description: form.description.value, agent }),
                    });
                    const data = await response.json().catch(() => ({}));
                    if (!response.ok) {
                        throw new Error(response.status === 404
                            ? 'The hub is running an older version. Restart it to enable New badge.'
                            : data.error || 'Could not create the badge.');
                    }
                    projects = [...projects, data.project];
                    listeners.forEach(fn => fn());
                    close(data.project.id);
                } catch (failure) {
                    error.textContent = failure.message; error.hidden = false;
                }
            });
            form.name.focus();
        });
    }

    function astraButton(select) {
        const node = document.createElement('button');
        node.type = 'button';
        node.className = 'proj-astra';
        node.textContent = 'Astra';
        node.title = "Open or create this project's Astra manager";
        const sync = () => { node.hidden = !select.value || select.value === NEW; };
        select.addEventListener('change', sync);
        listeners.add(sync);
        sync();
        node.addEventListener('click', async () => {
            node.disabled = true;
            try {
                const response = await fetch(`/api/agents/projects/${encodeURIComponent(select.value)}/astra`, {
                    method: 'POST', credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' }, body: '{}',
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Could not open Astra.');
                window.alert(`${nameOf(select.value)} Astra is ready: agent thread #${data.thread}${data.created ? ' (created)' : ''}. Open it from Agent chat.`);
            } catch (error) {
                window.alert(error.message);
            } finally {
                node.disabled = false;
            }
        });
        return node;
    }

    function badge(id) {
        if (!id) return null;
        const node = document.createElement('span');
        node.className = 'proj-badge';
        node.style.setProperty('--proj-hue', hue(id));
        node.dataset.project = id;
        node.textContent = nameOf(id);
        node.title = `Project: ${nameOf(id)}`;
        return node;
    }

    function select(current, onChange, label, anyLabel = 'No project') {
        const node = document.createElement('select');
        node.className = 'proj-select';
        node.setAttribute('aria-label', label);
        const fill = value => {
            node.textContent = '';
            const none = document.createElement('option');
            none.value = ''; none.textContent = anyLabel;
            node.append(none);
            const add = document.createElement('option');
            add.value = NEW; add.textContent = '+ New badge…';
            node.append(add);
            for (const project of projects) {
                const option = document.createElement('option');
                option.value = project.id; option.textContent = project.name;
                node.append(option);
            }
            node.value = value;
        };
        fill(current || '');
        listeners.add(() => fill(current || ''));
        node.addEventListener('change', async () => {
            if (node.value !== NEW) { current = node.value; onChange(node.value); return; }
            node.value = current || '';
            const created = await createBadge();
            if (created) { fill(created); current = created; onChange(created); }
        });
        node.setValue = value => { node.value = value || ''; };
        return node;
    }

    window.HubProjects = { badge, select, astraButton, nameOf, ready: load, all: () => projects.slice() };
})();
