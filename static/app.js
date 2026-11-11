const hubMotion = (() => {
    const root = document.documentElement;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const running = new WeakMap();
    const active = new Set();
    const easing = 'cubic-bezier(.23, 1, .32, 1)';
    root.dataset.input = 'pointer';
    document.addEventListener('pointerdown', () => { root.dataset.input = 'pointer'; }, { capture: true, passive: true });
    function stopMotion() {
        active.forEach(animation => animation.cancel());
        active.clear();
    }
    document.addEventListener('keydown', () => {
        root.dataset.input = 'keyboard';
        stopMotion();
    }, true);
    reduced.addEventListener('change', () => { if (reduced.matches) stopMotion(); });

    function animate(node, frames, options = {}) {
        if (!node?.getClientRects().length || reduced.matches || root.dataset.input === 'keyboard') return;
        running.get(node)?.cancel();
        const animation = node.animate(frames, { duration: 220, easing, ...options });
        running.set(node, animation);
        active.add(animation);
        animation.finished.then(() => active.delete(animation), () => active.delete(animation));
    }

    document.addEventListener('DOMContentLoaded', () => {
        const nav = document.querySelector('.navigation');
        const indicator = document.createElement('span');
        indicator.className = 'nav-highlight';
        indicator.setAttribute('aria-hidden', 'true');
        nav.prepend(indicator);
        let positioned = false;
        let last = '';
        let previousView = root.dataset.view;
        function position() {
            const target = nav.querySelector('[aria-current="page"]');
            if (!target) return;
            const { offsetLeft: x, offsetTop: y, offsetWidth: width, offsetHeight: height } = target;
            const next = [x, y, width, height].join(':');
            if (next === last) return;
            const from = indicator.getBoundingClientRect();
            const bounds = nav.getBoundingClientRect();
            running.get(indicator)?.cancel();
            Object.assign(indicator.style, { width: `${width}px`, height: `${height}px`, transform: `translate(${x}px, ${y}px)` });
            if (positioned) animate(indicator, [
                { transform: `translate(${from.left - bounds.left}px, ${from.top - bounds.top}px) scale(${from.width / width}, ${from.height / height})` },
                { transform: `translate(${x}px, ${y}px) scale(1)` },
            ]);
            positioned = true; last = next;
        }
        new ResizeObserver(position).observe(nav);
        new MutationObserver(() => {
            position();
            if (previousView !== root.dataset.view && root.dataset.view === 'projects') {
                reveal(document.getElementById('tab-projects'));
            }
            previousView = root.dataset.view;
        }).observe(root, { attributes: true, attributeFilter: ['data-view'] });
        position();
        reveal(document.querySelector('.hero'));
    });

    function reveal(node, delay = 0) {
        animate(node, [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }],
            { duration: 240, delay, fill: 'backwards' });
    }
    return { reveal, complete: node => animate(node, [
        { transform: 'scale(1)' }, { transform: 'scale(.84)', offset: .35 }, { transform: 'scale(1)' },
    ], { duration: 200 }) };
})();

const urls = {
    'prior-art': '/prior-art/',
    localization: `http://${location.hostname}:8010/`,
    'video-agents': `http://${location.hostname}:8000/`,
    sample4geo: `http://${location.hostname}:8025/`,
    crossview: `http://${location.hostname}:8012/`,
    pointmatching: `http://${location.hostname}:8013/`,
};
const hostUrl = url => (url ? url.replace('//127.0.0.1:', `//${location.hostname}:`) : url);
const labels = { ready: 'Running', stopped: 'On demand', starting: 'Starting', error: 'Needs attention', unavailable: 'Unavailable' };
const icons = {
    'prior-art': ['M11 21H5V3h9l5 5v3M14 3v5h5', 'M8 12h3M8 16h2', 'M19 19l3 3', 'circle:16,16,4'],
    localization: ['circle:12,12,8', 'circle:12,12,3', 'M12 1v4M12 19v4M1 12h4M19 12h4'],
    'video-agents': ['M15 5H3v14h12Z', 'm15 9 6-4v14l-6-4Z', 'm7 9 4 3-4 3Z'],
    sample4geo: ['m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Z', 'M9 3v16M15 5v16', 'M3 12l6-3 6 5 6-4'],
    pointmatching: ['circle:6,7,2.5', 'circle:18,17,2.5', 'M8 8l8 8', 'M4 17h4M16 7h4'],
    crossview: ['M2 4h8v16H2Z', 'M14 4h8v16h-8Z', 'm6 11 2-3 2 3', 'm16 13 2 3 2-3'],
};
const pending = new Map();
const errors = new Map();
const manualLinks = new Set();
const cards = new Map();
let projects = [];
let connected = false;
let fetching = false;
let pollTimer;

function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
}

function projectIcon(id) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    for (const [name, value] of Object.entries({ viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.6', 'aria-hidden': 'true' })) {
        svg.setAttribute(name, value);
    }
    for (const shape of icons[id] || []) {
        const circle = shape.startsWith('circle:');
        const child = document.createElementNS(svg.namespaceURI, circle ? 'circle' : 'path');
        if (circle) {
            const [cx, cy, r] = shape.slice(7).split(',');
            for (const [name, value] of Object.entries({ cx, cy, r })) child.setAttribute(name, value);
        } else child.setAttribute('d', shape);
        svg.append(child);
    }
    return svg;
}

function schedulePoll() {
    clearTimeout(pollTimer);
    const starting = pending.size || projects.some(project => project.state === 'starting');
    pollTimer = setTimeout(fetchProjects, starting ? 2000 : 8000);
}

async function request(path, options = {}) {
    const response = await fetch(path, { ...options, signal: AbortSignal.timeout(10000) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
}

async function fetchProjects() {
    if (fetching) return;
    fetching = true;
    try {
        const data = await request('/api/projects');
        if (!Array.isArray(data.projects)) throw new Error('Invalid project response');
        projects = data.projects.filter(project => Object.hasOwn(urls, project.id));
        connected = true;
        for (const project of projects) {
            const launch = pending.get(project.id);
            if (!launch || launch.phase !== 'starting') continue;
            if (project.state === 'ready') complete(project.id, hostUrl(project.url));
            else if (['error', 'unavailable', 'stopped'].includes(project.state)) {
                fail(project.id, project.message || 'Startup stopped. Please retry.');
            } else {
                launch.message = project.message || 'Getting things ready...';
                waitingMessage(launch.tab, launch.message);
            }
        }
    } catch (error) {
        connected = false;
        for (const launch of pending.values()) {
            waitingMessage(launch.tab, 'Connection interrupted. Reconnecting automatically...');
        }
    } finally {
        fetching = false;
        render();
        schedulePoll();
    }
}

function makeCard(project) {
    const card = element('article', 'card');
    card.dataset.projectId = project.id;
    const icon = element('div', `card-icon ${project.id}`);
    icon.append(projectIcon(project.id));
    icon.setAttribute('aria-hidden', 'true');
    const header = element('div', 'card-header');
    const title = element('h3', '');
    const description = element('p', 'card-description');
    const badge = element('div', 'card-state');
    const badgeText = element('span', '');
    badge.append(element('span', 'state-dot'), badgeText);
    header.append(icon, title, badge);
    const message = element('p', 'card-message');
    message.setAttribute('aria-live', 'polite');
    const actions = element('div', 'card-actions');
    const button = element('button', 'btn btn-primary');
    button.type = 'button';
    button.addEventListener('click', () => launchProject(project.id));
    const link = element('a', 'btn btn-secondary', 'Open in new tab');
    link.href = urls[project.id];
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    actions.append(button, link);
    card.append(header, description, message, actions);
    document.getElementById('projectsGrid').append(card);
    hubMotion.reveal(card, Math.min(cards.size * 40, 160));
    const nodes = { card, title, description, badge, badgeText, message, button, link };
    cards.set(project.id, nodes);
    return nodes;
}

function render() {
    const status = document.getElementById('connectionStatus');
    status.querySelector('.status-dot').className = `status-dot ${connected ? 'connected' : 'disconnected'}`;
    const statusText = status.querySelector('.status-text');
    const connectionLabel = connected ? 'Connected' : 'Reconnecting…';
    if (statusText.textContent !== connectionLabel) statusText.textContent = connectionLabel;
    document.getElementById('errorBanner').style.display = connected ? 'none' : 'flex';
    document.getElementById('errorMessage').textContent =
        'The dashboard connection was interrupted. Retrying automatically.';
    if (projects.length) {
        document.querySelectorAll('.skeleton').forEach(node => node.remove());
    }
    const summary = document.getElementById('projectSummary');
    const summaryText = connected
        ? `${projects.length} projects · ${projects.filter(project => project.state === 'ready').length} ready to open`
        : 'Reconnecting to your projects…';
    if (summary && summary.textContent !== summaryText) summary.textContent = summaryText;
    for (const project of projects) {
        const nodes = cards.get(project.id) || makeCard(project);
        const launching = pending.has(project.id);
        const failed = errors.get(project.id);
        const effective = launching ? 'starting' : failed ? 'error' : project.state;
        nodes.card.dataset.state = effective;
        nodes.card.className = `card${effective === 'unavailable' ? ' disabled' : ''}${launching ? ' launching' : ''}`;
        nodes.title.textContent = project.name;
        nodes.description.textContent = project.description;
        nodes.badge.className = `card-state ${effective}`;
        nodes.badgeText.textContent = labels[effective] || 'Unknown';
        const message = failed || (launching ? pending.get(project.id).message :
            ['starting', 'error', 'unavailable'].includes(effective) ? project.message : '') || '';
        if (nodes.message.textContent !== message) nodes.message.textContent = message;
        nodes.message.hidden = !message;
        nodes.message.className = `card-message ${effective === 'error' ? 'error-msg' : ''}`;
        nodes.button.disabled = !connected || ['starting', 'unavailable'].includes(effective);
        nodes.button.textContent = {
            ready: 'Open', stopped: 'Start', starting: 'Starting…',
            error: 'Retry', unavailable: 'Not available',
        }[effective] || 'Not available';
        nodes.button.setAttribute('aria-label', `${nodes.button.textContent} ${project.name}${effective === 'ready' ? ' in a new tab' : ''}`);
        nodes.button.setAttribute('aria-busy', String(effective === 'starting'));
        nodes.link.setAttribute('aria-label', `Open ${project.name} in a new tab`);
        nodes.link.hidden = !connected || effective !== 'ready' || !manualLinks.has(project.id);
    }
}

function waitingMessage(tab, message) {
    if (!tab || tab.closed) return;
    try {
        const doc = tab.document;
        doc.title = 'Preparing your workspace';
        let text = doc.getElementById('launch-status');
        if (!text) {
            doc.documentElement.style.colorScheme = 'light dark';
            doc.body.style.cssText = 'margin:0;background:Canvas;color:CanvasText;font:16px system-ui;padding:10vh 10vw;line-height:1.6';
            const heading = doc.createElement('h1');
            heading.textContent = 'Opening your workspace';
            text = doc.createElement('p');
            text.id = 'launch-status';
            text.setAttribute('role', 'status');
            const hint = doc.createElement('p');
            hint.textContent = 'You can return to Project Hub while this finishes. No terminal needed.';
            doc.body.replaceChildren(heading, text, hint);
        }
        text.textContent = message;
    } catch {
        // A user may have navigated the waiting tab elsewhere.
    }
}

function complete(id, url) {
    const launch = pending.get(id);
    if (url !== urls[id]) {
        fail(id, 'The project returned an unexpected address. Please retry.');
        return;
    }
    if (launch?.tab && !launch.tab.closed) {
        try {
            launch.tab.location.href = url;
        } catch {
            manualLinks.add(id);
        }
    } else {
        manualLinks.add(id);
    }
    pending.delete(id);
    errors.delete(id);
}

function fail(id, message) {
    const launch = pending.get(id);
    waitingMessage(launch?.tab, `${message} Return to Project Hub to retry.`);
    pending.delete(id);
    errors.set(id, message);
}

async function launchProject(id) {
    if (!connected || pending.has(id)) return;
    const project = projects.find(item => item.id === id);
    if (!project || project.state === 'unavailable') return;
    const tab = window.open('', '_blank');
    if (tab) tab.opener = null;
    errors.delete(id);
    manualLinks.delete(id);
    const launch = { tab, phase: 'request', message: 'Preparing your workspace...' };
    pending.set(id, launch);
    waitingMessage(tab, launch.message);
    render();
    try {
        const data = await request(`/api/projects/${id}/launch`, { method: 'POST' });
        if (data.state === 'ready') {
            project.state = 'ready';
            project.url = hostUrl(data.url);
            complete(id, hostUrl(data.url));
        } else if (data.state === 'starting') {
            launch.phase = 'starting';
            launch.message = data.message || 'Starting. Your workspace will open automatically.';
            project.state = 'starting';
            waitingMessage(tab, launch.message);
        } else {
            throw new Error('Unexpected startup response. Please retry.');
        }
    } catch (error) {
        fail(id, error.message);
    }
    render();
    schedulePoll();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('errorRetry').addEventListener('click', fetchProjects);
    document.querySelector('.skip-link').addEventListener('click', event => {
        event.preventDefault();
        const main = document.querySelector('main:not([hidden])');
        main?.focus();
    });
    fetchProjects();
});
