const hubMarkdown = (() => {
    const SYMBOLS = {
        alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε', theta: 'θ', lambda: 'λ', mu: 'μ', pi: 'π',
        rho: 'ρ', sigma: 'σ', tau: 'τ', phi: 'φ', omega: 'ω', Gamma: 'Γ', Delta: 'Δ', Theta: 'Θ', Lambda: 'Λ',
        Pi: 'Π', Sigma: 'Σ', Phi: 'Φ', Omega: 'Ω', times: '×', cdot: '·', pm: '±', leq: '≤', le: '≤', geq: '≥',
        ge: '≥', neq: '≠', ne: '≠', approx: '≈', infty: '∞', sum: '∑', prod: '∏', int: '∫', partial: '∂',
        nabla: '∇', rightarrow: '→', to: '→', leftarrow: '←', Rightarrow: '⇒', Leftrightarrow: '⇔', in: '∈',
        forall: '∀', exists: '∃', ldots: '…', dots: '…', cdots: '⋯', sqrt: '√', degree: '°',
    };

    function el(tag, className, text) {
        const e = document.createElement(tag);
        if (className) e.className = className;
        if (text !== undefined) e.textContent = text;
        return e;
    }

    // Parses a TeX subset into DOM: \frac, \sqrt, ^, _, {}, Greek and operator symbols.
    function math(src) {
        let i = 0;
        function group() {
            if (src[i] === '{') {
                i++;
                const out = seq('}');
                i++;
                return out;
            }
            const frag = document.createDocumentFragment();
            if (i < src.length) {
                if (src[i] === '\\') frag.append(command());
                else frag.append(src[i++]);
            }
            return frag;
        }
        function command() {
            i++;
            let name = '';
            while (i < src.length && /[a-zA-Z]/.test(src[i])) name += src[i++];
            if (!name) return src[i] ? src[i++] : '';
            if (name === 'frac') {
                const f = el('span', 'md-frac');
                const n = el('span', 'md-num'), d = el('span', 'md-den');
                n.append(group()); d.append(group()); f.append(n, d);
                return f;
            }
            if (name === 'sqrt') {
                const s = el('span', 'md-sqrt');
                s.append('√', el('span', 'md-radicand'));
                s.lastChild.append(group());
                return s;
            }
            if (name === 'text' || name === 'mathrm') return group();
            return SYMBOLS[name] || name;
        }
        function seq(stop) {
            const frag = document.createDocumentFragment();
            while (i < src.length && src[i] !== stop) {
                const c = src[i];
                if (c === '^' || c === '_') {
                    i++;
                    const s = el('span', c === '^' ? 'md-sup' : 'md-sub');
                    s.append(group());
                    frag.append(s);
                } else if (c === '{') frag.append(group());
                else if (c === '\\') frag.append(command());
                else { frag.append(c); i++; }
            }
            return frag;
        }
        return seq();
    }

    const INLINE = /(`[^`\n]+`)|(\$\$[^$]+\$\$)|(\$[^$\n]+\$)|(\*\*[^*]+\*\*|__[^_]+__)|(\*[^*\s][^*]*\*|\b_[^_\s][^_]*_\b)|(~~[^~]+~~)|(\[[^\]]+\]\([^)\s]+\))|(https?:\/\/[^\s<]+)/;

    function safeUrl(url) {
        try {
            const u = new URL(url, location.href);
            return ['http:', 'https:', 'mailto:'].includes(u.protocol) ? u.href : null;
        } catch { return null; }
    }
    function link(label, url, parent) {
        const href = safeUrl(url);
        if (!href) { parent.append(label); return; }
        const a = el('a', '', label);
        a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer';
        parent.append(a);
    }

    function inline(text, parent) {
        while (text) {
            const m = INLINE.exec(text);
            if (!m) { parent.append(text); return; }
            if (m.index) parent.append(text.slice(0, m.index));
            const t = m[0];
            if (m[1]) parent.append(el('code', 'md-code', t.slice(1, -1)));
            else if (m[2]) { const s = el('span', 'md-math md-math-block'); s.append(math(t.slice(2, -2))); parent.append(s); }
            else if (m[3]) { const s = el('span', 'md-math'); s.append(math(t.slice(1, -1))); parent.append(s); }
            else if (m[4]) { const s = el('strong'); inline(t.slice(2, -2), s); parent.append(s); }
            else if (m[5]) { const s = el('em'); inline(t.slice(1, -1), s); parent.append(s); }
            else if (m[6]) { const s = el('del'); inline(t.slice(2, -2), s); parent.append(s); }
            else if (m[7]) { const k = t.indexOf(']('); link(t.slice(1, k), t.slice(k + 2, -1), parent); }
            else { const url = t.replace(/[.,;:!?)]+$/, ''); link(url, url, parent); parent.append(t.slice(url.length)); }
            text = text.slice(m.index + t.length);
        }
    }

    function render(source) {
        const root = el('div', 'md');
        const lines = String(source).replace(/\r\n?/g, '\n').split('\n');
        let i = 0;
        const isRow = (l) => l !== undefined && l.includes('|');
        const isSep = (l) => l !== undefined && /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/.test(l) && l.includes('|');
        const cells = (l) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
        const isBlockStart = (l) => /^(#{1,6}\s|```|>\s?|\s*([-*+]|\d+[.)])\s|\s*(---+|\*\*\*+)\s*$|\$\$)/.test(l);
        while (i < lines.length) {
            const line = lines[i];
            if (!line.trim()) { i++; continue; }
            let m;
            if (/^```/.test(line)) {
                const code = [];
                i++;
                while (i < lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
                i++;
                const pre = el('pre', 'md-pre');
                pre.append(el('code', '', code.join('\n')));
                root.append(pre);
            } else if (line.trim().startsWith('$$')) {
                let body = line.trim().slice(2);
                const one = body.endsWith('$$') && body.length >= 2;
                if (one) body = body.slice(0, -2);
                i++;
                while (!one && i < lines.length) {
                    const l = lines[i++];
                    if (l.includes('$$')) { body += '\n' + l.slice(0, l.indexOf('$$')); break; }
                    body += '\n' + l;
                }
                const d = el('div', 'md-math md-math-block');
                d.append(math(body.trim()));
                root.append(d);
            } else if (isRow(line) && isSep(lines[i + 1])) {
                const aligns = cells(lines[i + 1]).map(c => c.startsWith(':') && c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : '');
                const table = el('table', 'md-table');
                const addRow = (parent, tag, row) => {
                    const tr = el('tr');
                    row.forEach((c, k) => { const cell = el(tag); if (aligns[k]) cell.style.textAlign = aligns[k]; inline(c, cell); tr.append(cell); });
                    parent.append(tr);
                };
                const thead = el('thead'), tbody = el('tbody');
                addRow(thead, 'th', cells(line));
                i += 2;
                while (i < lines.length && lines[i].trim() && isRow(lines[i])) addRow(tbody, 'td', cells(lines[i++]));
                table.append(thead, tbody);
                const wrap = el('div', 'md-table-wrap');
                wrap.append(table);
                root.append(wrap);
            } else if ((m = /^(#{1,6})\s+(.*?)\s*#*$/.exec(line))) {
                const h = el('h' + m[1].length, 'md-h');
                inline(m[2], h);
                root.append(h); i++;
            } else if (/^\s*(---+|\*\*\*+)\s*$/.test(line)) {
                root.append(el('hr')); i++;
            } else if (/^>\s?/.test(line)) {
                const q = el('blockquote');
                const body = [];
                while (i < lines.length && /^>\s?/.test(lines[i])) body.push(lines[i++].replace(/^>\s?/, ''));
                q.append(...render(body.join('\n')).childNodes);
                root.append(q);
            } else if (/^\s*([-*+]|\d+[.)])\s/.test(line)) {
                const ordered = /^\s*\d/.test(line);
                const list = el(ordered ? 'ol' : 'ul');
                while (i < lines.length && /^\s*([-*+]|\d+[.)])\s/.test(lines[i]) && /^\s*\d/.test(lines[i]) === ordered) {
                    const li = el('li');
                    inline(lines[i].replace(/^\s*([-*+]|\d+[.)])\s+/, ''), li);
                    list.append(li); i++;
                }
                root.append(list);
            } else {
                const p = el('p');
                const body = [];
                while (i < lines.length && lines[i].trim() && (body.length === 0 || !(isBlockStart(lines[i]) || (isRow(lines[i]) && isSep(lines[i + 1]))))) body.push(lines[i++]);
                body.forEach((l, k) => { if (k) p.append(el('br')); inline(l, p); });
                root.append(p);
            }
        }
        return root;
    }

    return { render };
})();
