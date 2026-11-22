const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../files/root/usr/mww/ble2uart_gateway/portal.js'), 'utf8');
new vm.Script(source);

function functionSource(name) {
    const start = source.indexOf('\tfunction ' + name + '(');
    assert(start >= 0, name);
    const end = source.indexOf('\n\t}', start);
    assert(end > start, name);
    return source.slice(start, end + 3);
}

class Element {
    constructor(tag) {
        this.tag = tag;
        this.children = [];
        this.events = {};
        this.attributes = {};
        this.isConnected = true;
    }
    appendChild(child) { this.children.push(child); return child; }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(name, callback) { this.events[name] = callback; }
    set textContent(value) { this.text = value; this.children = []; }
    get textContent() { return (this.text || '') + this.children.map(child => child.textContent).join(' '); }
}

async function main() {
    const zooms = [], captures = new Set();
    let panWrites = 0, panLoads = 0;
    let holdClock = 0, holdId = 0;
    const holds = new Map();
    const touching = {
        state: {}, els: {tip: {}},
        hideTip() {}, showTip() {}, drawChart() {},
        writeStore() { panWrites++; }, loadCharts() { panLoads++; }, render() {},
        MIN_WINDOW_MS: 60000, Date: {now: () => 10800000},
        HOLD_RESET_MS: 650,
        window: {setTimeout(callback, delay) { const id = ++holdId; holds.set(id, {callback, at: holdClock + delay}); return id; },
            clearTimeout: id => holds.delete(id)},
        applyZoom: (block, from, to) => zooms.push([from, to]),
    };
    vm.createContext(touching);
    vm.runInContext(['clearHold', 'onAxisContextMenu', 'cancelGesture', 'onPointerDown', 'onPointerMove', 'onPointerUp', 'timeAt', 'localX', 'onMove', 'onDown', 'onUp', 'clampWindow', 'resetZoom'].map(functionSource).join('\n'), touching);
    const canvas = {style: {}, getBoundingClientRect: () => ({left: 10, top: 20, height: 260}),
        setPointerCapture: id => captures.add(id), hasPointerCapture: id => captures.has(id), releasePointerCapture: id => captures.delete(id)};
    const panel = {canvas, view: {box: {left: 50, right: 350, top: 10, bottom: 200}, from: 0, to: 3600000}};
    const pointer = (x, y, extra = {}) => ({pointerId: 1, pointerType: 'touch', isPrimary: true, button: 0, clientX: x + 10, clientY: y + 20, ...extra});
    touching.onPointerDown(panel, pointer(100, 100));
    touching.onPointerMove(panel, pointer(104, 101));
    assert.equal(panel.drag, undefined);
    touching.onPointerMove(panel, pointer(200, 102));
    assert.equal(panel.drag.x0, 100);
    touching.onPointerUp(panel, pointer(250, 103));
    assert.deepEqual(zooms.pop(), [600000, 2400000]);
    assert.equal(captures.size, 0);
    touching.onPointerDown(panel, pointer(100, 100));
    touching.onPointerMove(panel, pointer(102, 150));
    touching.onPointerUp(panel, pointer(104, 170));
    assert.equal(zooms.length, 0);
    touching.onPointerDown(panel, pointer(100, 100));
    touching.onPointerUp(panel, pointer(100, 100));
    assert.equal(zooms.length, 0);
    touching.onPointerDown(panel, pointer(100, 100));
    touching.onPointerUp(panel, pointer(200, 100));
    assert.deepEqual(zooms.pop(), [600000, 1800000]);
    touching.onPointerDown(panel, pointer(100, 100));
    touching.onPointerMove(panel, pointer(220, 100));
    touching.cancelGesture(panel);
    touching.onPointerUp(panel, pointer(240, 100));
    assert.equal(zooms.length, 0);
    touching.onPointerDown(panel, pointer(100, 100));
    touching.onPointerMove(panel, pointer(220, 100));
    touching.onPointerDown(panel, pointer(250, 100, {pointerId: 2, isPrimary: false}));
    touching.onPointerUp(panel, pointer(240, 100));
    assert.equal(zooms.length, 0);
    touching.onPointerDown(panel, pointer(300, 100));
    touching.onPointerMove(panel, pointer(-20, 100));
    touching.onPointerUp(panel, pointer(-50, 100));
    assert.deepEqual(zooms.pop(), [0, 3000000]);
    touching.onPointerDown(panel, pointer(100, 100, {pointerType: 'mouse'}));
    touching.onPointerUp(panel, pointer(200, 100, {pointerType: 'mouse'}));
    assert.deepEqual(zooms.pop(), [600000, 1800000]);
    Object.assign(touching, {document: {createElement: tag => new Element(tag)}, t: key => key});
    vm.runInContext(functionSource('createBlock'), touching);
    const wired = touching.createBlock();
    Object.assign(wired.canvas, canvas);
    wired.view = panel.view;
    for (const event of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'lostpointercapture', 'pointerleave']) {
        assert.equal(typeof wired.canvas.events[event], 'function', event);
    }
    assert.equal(wired.canvas.events.touchstart, undefined);
    assert.equal(wired.canvas.events.mousedown, undefined);
    wired.canvas.events.pointerdown(pointer(100, 100));
    wired.canvas.events.pointermove(pointer(200, 100));
    wired.canvas.events.pointerup(pointer(250, 100));
    assert.deepEqual(zooms.pop(), [600000, 2400000]);
    wired.canvas.events.pointerdown(pointer(100, 100));
    wired.canvas.events.pointermove(pointer(200, 100));
    wired.canvas.events.pointercancel({pointerId: 1});
    wired.canvas.events.pointerup(pointer(250, 100));
    assert.equal(zooms.length, 0);

    panel.view.from = 3600000;
    panel.view.to = 7200000;
    touching.state.zoom = null;
    touching.onPointerDown(panel, pointer(250, 230));
    touching.onPointerMove(panel, pointer(175, 231));
    assert.equal(panel.drag, null);
    assert.equal(panel.pan.moved, true);
    assert.equal(panLoads, 0);
    touching.onPointerUp(panel, pointer(175, 231));
    assert.equal(touching.state.zoom.from, 4500000);
    assert.equal(touching.state.zoom.to, 8100000);
    assert.equal(panWrites, 1);
    assert.equal(panLoads, 1);
    touching.onPointerDown(panel, pointer(100, 230));
    touching.onPointerUp(panel, pointer(175, 230));
    assert.equal(touching.state.zoom.from, 2700000);
    assert.equal(touching.state.zoom.to, 6300000);
    assert.equal(panWrites, 2);
    const previous = touching.state.zoom;
    touching.onPointerDown(panel, pointer(250, 230));
    touching.onPointerMove(panel, pointer(100, 230));
    touching.cancelGesture(panel);
    assert.equal(touching.state.zoom.from, previous.from);
    assert.equal(touching.state.zoom.to, previous.to);
    assert.equal(panLoads, 2);
    touching.onPointerDown(panel, pointer(100, 230));
    touching.onPointerMove(panel, pointer(103, 250));
    touching.onPointerUp(panel, pointer(104, 250));
    assert.equal(panLoads, 2);
    touching.onPointerDown(panel, pointer(100, 230));
    touching.onPointerUp(panel, pointer(100, 230));
    assert.equal(panLoads, 2);
    touching.onPointerDown(panel, pointer(100, 230));
    touching.onPointerUp(panel, pointer(-900, 230));
    assert.equal(touching.state.zoom.to, 10800000);
    assert.equal(touching.state.zoom.to - touching.state.zoom.from, 3600000);
    touching.onPointerDown(panel, pointer(20, 230));
    touching.onPointerUp(panel, pointer(95, 230));
    assert.equal(touching.state.zoom.from, 2700000);
    assert.equal(touching.state.zoom.to, 6300000);
    touching.state.zoom = null;
    touching.onPointerDown(panel, pointer(20, 230));
    touching.onPointerMove(panel, pointer(95, 230));
    touching.cancelGesture(panel);
    assert.equal(touching.state.zoom, null);
    wired.canvas.events.pointerdown(pointer(100, 100));
    wired.canvas.events.pointermove(pointer(200, 100));
    wired.canvas.events.lostpointercapture({pointerId: 1});
    wired.canvas.events.pointerup(pointer(250, 100));
    assert.equal(zooms.length, 0);

    const advanceHold = until => {
        for (const [id, timer] of [...holds.entries()].sort((first, second) => first[1].at - second[1].at)) {
            if (timer.at <= until) { holdClock = timer.at; holds.delete(id); timer.callback(); }
        }
        holdClock = until;
    };
    assert.equal(holds.size, 0);
    touching.state.blocks = [panel, wired];
    touching.state.zoom = {from: 4500000, to: 5400000};
    const writesBeforeHold = panWrites;
    wired.canvas.events.pointerdown(pointer(100, 230));
    advanceHold(649);
    assert.equal(touching.state.zoom.from, 4500000);
    advanceHold(650);
    assert.equal(touching.state.zoom, null);
    assert.equal(panWrites, writesBeforeHold + 1);
    assert.equal(captures.size, 0);
    wired.canvas.events.pointerup(pointer(100, 230));
    assert.equal(panWrites, writesBeforeHold + 1);
    touching.state.zoom = {from: 4500000, to: 5400000};
    wired.canvas.events.pointerdown(pointer(100, 230));
    wired.canvas.events.pointermove(pointer(103, 231));
    advanceHold(1300);
    assert.equal(touching.state.zoom, null);
    for (const action of ['release', 'move', 'vertical', 'cancel', 'secondFinger', 'insidePlot']) {
        touching.state.zoom = {from: 4500000, to: 5400000};
        wired.canvas.events.pointerdown(pointer(100, action === 'insidePlot' ? 100 : 230));
        if (action === 'release') wired.canvas.events.pointerup(pointer(100, 230));
        if (action === 'move') wired.canvas.events.pointermove(pointer(120, 230));
        if (action === 'vertical') wired.canvas.events.pointermove(pointer(100, 250));
        if (action === 'cancel') wired.canvas.events.pointercancel({pointerId: 1});
        if (action === 'secondFinger') wired.canvas.events.pointerdown(pointer(150, 230, {pointerId: 2, isPrimary: false}));
        advanceHold(holdClock + 1000);
        assert(touching.state.zoom, action + ': unexpected reset');
        touching.cancelGesture(wired);
    }
    let contextPrevented = false;
    wired.canvas.events.contextmenu(pointer(100, 230, {preventDefault() { contextPrevented = true; }}));
    assert.equal(contextPrevented, true);
    contextPrevented = false;
    wired.canvas.events.contextmenu(pointer(100, 100, {preventDefault() { contextPrevented = true; }}));
    assert.equal(contextPrevented, false);

    let clock = 0, nextTimer = 0, retries = 0;
    const timers = new Map(), dot = new Element('span');
    const health = {
        state: {catalog: null, error: '', settings: {refreshSeconds: 30, refreshMinutes: 0}, refreshStartedAt: 0,
            connection: {pending: {}, failures: {}, retry: null, deadline: null, attempts: 0}},
        ERROR_GRACE_MS: 15000, REFRESH_MS: 30000,
        Date: {now: () => clock}, document: {querySelector: () => dot}, t: (key, values) => key + (values ? ' ' + values.seconds : ''),
        window: {setTimeout(callback, delay) { const id = ++nextTimer; timers.set(id, {callback, at: clock + delay}); return id; }, clearTimeout: id => timers.delete(id)},
        renderDevices() {}, loadCatalog() { retries++; },
    };
    vm.createContext(health);
    vm.runInContext(['refreshStatus', 'autoRefreshActive', 'connectionStatus', 'renderConnection', 'connectionChanged', 'updateConnection'].map(functionSource).join('\n'), health);
    const advance = until => {
        while (true) {
            const due = [...timers.entries()].filter(([, timer]) => timer.at <= until).sort((first, second) => first[1].at - second[1].at)[0];
            if (!due) break;
            clock = due[1].at; timers.delete(due[0]); due[1].callback();
        }
        clock = until;
    };
    health.updateConnection('catalog', true);
    assert.equal(dot.className, 'pdot pupdating');
    health.updateConnection('catalog', false, new Error('Failed to fetch'));
    assert.equal(dot.className, 'pdot pstale');
    assert.equal(health.state.error, '');
    advance(1000);
    assert.equal(retries, 1);
    health.state.catalog = {devices: []};
    health.updateConnection('catalog', false);
    assert.equal(dot.className, 'pdot pok');
    assert(dot.title.includes('refreshEnabled 30'));
    assert.equal(dot.attributes['aria-pressed'], 'true');
    advance(20000);
    assert.equal(health.state.error, '');
    health.updateConnection('catalog', true);
    health.updateConnection('catalog', false, new Error('Failed to fetch'));
    advance(34999);
    assert.equal(health.state.error, '');
    advance(35000);
    assert.equal(dot.className, 'pdot perror');
    assert.equal(health.state.error, 'Failed to fetch');
    health.updateConnection('catalog', false);
    assert.equal(dot.className, 'pdot pok');
    health.updateConnection('charts', false, new Error('series failed'));
    health.updateConnection('catalog', false);
    assert.equal(dot.className, 'pdot pstale');
    health.updateConnection('charts', false);
    health.updateConnection('catalog', false, Object.assign(new Error('login expired'), {retryable: false}));
    assert.equal(dot.className, 'pdot perror');
    assert.equal(health.state.error, 'login expired');
    assert.equal(health.state.connection.retry, null);

    let refreshClock = 0, refreshes = 0;
    const refreshTimers = new Map();
    const scheduling = {
        state: {settings: {refreshSeconds: 30, refreshMinutes: 0}, refreshStartedAt: 0, refreshTimer: null, connection: {retry: null}},
        Date: {now: () => refreshClock},
        window: {setTimeout(callback, delay) { const id = ++nextTimer; refreshTimers.set(id, {callback, at: refreshClock + delay}); return id; }, clearTimeout: id => refreshTimers.delete(id)},
        loadCatalog: () => { refreshes++; return Promise.resolve(); }, renderConnection() {}, connectionChanged() {},
    };
    vm.createContext(scheduling);
    vm.runInContext(['refreshStatus', 'autoRefreshActive', 'scheduleRefresh', 'configureRefresh', 'toggleRefresh'].map(functionSource).join('\n'), scheduling);
    const advanceRefresh = async until => {
        while (true) {
            const due = [...refreshTimers.entries()].filter(([, timer]) => timer.at <= until).sort((first, second) => first[1].at - second[1].at)[0];
            if (!due) break;
            refreshClock = due[1].at; refreshTimers.delete(due[0]); due[1].callback();
            await new Promise(resolve => setImmediate(resolve));
        }
        refreshClock = until;
    };
    scheduling.configureRefresh();
    await advanceRefresh(90000);
    assert.equal(refreshes, 3);
    assert.equal(scheduling.autoRefreshActive(), true);
    scheduling.state.settings.refreshSeconds = 10;
    scheduling.state.settings.refreshMinutes = 1;
    scheduling.configureRefresh();
    assert.equal(refreshTimers.size, 1);
    await advanceRefresh(149999);
    assert.equal(refreshes, 8);
    scheduling.state.connection.retry = scheduling.window.setTimeout(() => { throw new Error('retry survived expiry'); }, 5000);
    await advanceRefresh(150000);
    assert.equal(scheduling.autoRefreshActive(), false);
    assert.equal(scheduling.state.connection.retry, null);
    await advanceRefresh(200000);
    assert.equal(refreshes, 8);
    await scheduling.loadCatalog(true, false);
    assert.equal(refreshes, 9);
    assert.equal(scheduling.autoRefreshActive(), false);
    scheduling.state.settings.refreshSeconds = 120;
    scheduling.configureRefresh();
    await advanceRefresh(260000);
    assert.equal(scheduling.autoRefreshActive(), false);
    assert.equal(refreshes, 9);
    scheduling.state.settings.refreshMinutes = 0;
    scheduling.configureRefresh();
    await advanceRefresh(500000);
    assert.equal(refreshes, 11);
    scheduling.state.connection.retry = scheduling.window.setTimeout(() => { throw new Error('retry survived manual pause'); }, 5000);
    await scheduling.toggleRefresh();
    assert.equal(scheduling.refreshStatus(), 'refreshStopped');
    assert.equal(scheduling.state.connection.retry, null);
    assert.equal(refreshTimers.size, 0);
    await advanceRefresh(800000);
    assert.equal(refreshes, 11);
    await scheduling.toggleRefresh();
    assert.equal(scheduling.refreshStatus(), 'refreshEnabled');
    assert.equal(refreshes, 12);
    await advanceRefresh(920000);
    assert.equal(refreshes, 13);
    scheduling.state.settings.refreshMinutes = 1;
    scheduling.configureRefresh();
    await advanceRefresh(980000);
    assert.equal(scheduling.refreshStatus(), 'refreshExpired');
    await scheduling.toggleRefresh();
    assert.equal(scheduling.refreshStatus(), 'refreshEnabled');
    assert.equal(scheduling.state.refreshStartedAt, 980000);
    assert.equal(refreshes, 14);
    let storedPreferences = null, savedCookie = null;
    const persistence = {
        state: {settings: {}}, SETTINGS_KEY: 'preferences', LEGACY_CHART_KEY: 'legacy', STORE_DAYS: 365,
        window: {localStorage: {getItem: key => key === 'preferences' && storedPreferences ? JSON.stringify(storedPreferences) : null,
            setItem: (key, value) => { storedPreferences = JSON.parse(value); }}},
        cookieRead: () => null, cookieWrite: (key, value) => { savedCookie = JSON.parse(value); },
    };
    vm.createContext(persistence);
    vm.runInContext(['stringList', 'settingsRead', 'settingsWrite'].map(functionSource).join('\n'), persistence);
    for (const [stored, expected] of [
        [{refreshSeconds: 12, refreshMinutes: 5}, [12, 5]],
        [{theme: 'dark'}, [30, 0]],
        [{refreshSeconds: 0, refreshMinutes: -1}, [30, 0]],
        [{refreshSeconds: '10', refreshMinutes: 1.5}, [30, 0]],
        [{refreshSeconds: 86400, refreshMinutes: 525600}, [86400, 525600]],
    ]) {
        storedPreferences = stored;
        persistence.state.settings = {refreshSeconds: 30, refreshMinutes: 0};
        persistence.settingsRead();
        assert.deepEqual([persistence.state.settings.refreshSeconds, persistence.state.settings.refreshMinutes], expected);
    }
    persistence.settingsWrite();
    assert.equal(storedPreferences.refreshSeconds, 86400);
    assert.equal(savedCookie.refreshMinutes, 525600);
    storedPreferences = null;
    persistence.cookieRead = () => JSON.stringify(savedCookie);
    persistence.state.settings = {refreshSeconds: 30, refreshMinutes: 0};
    persistence.settingsRead();
    assert.equal(persistence.state.settings.refreshSeconds, 86400);
    assert.equal(persistence.state.settings.refreshMinutes, 525600);
    for (const [stored, expected] of [[{}, 'linear'], [{line: 'smooth'}, 'smooth'], [{line: 'unknown'}, 'linear']]) {
        storedPreferences = stored;
        persistence.settingsRead();
        assert.equal(persistence.state.settings.line, expected);
    }
    persistence.state.settings.line = 'smooth';
    persistence.settingsWrite();
    assert.equal(storedPreferences.line, 'smooth');
    assert.equal(savedCookie.line, 'smooth');
    health.state.settings.refreshMinutes = 1;
    health.state.refreshStartedAt = 0;
    clock = 60000;
    health.updateConnection('catalog', false);
    assert(dot.attributes['aria-label'].includes('refreshExpired 30'));
    assert.equal(dot.className, 'pdot pexpired');
    assert.equal(dot.attributes['aria-pressed'], 'false');
    health.state.refreshPaused = true;
    health.renderConnection();
    assert.equal(dot.className, 'pdot pmanual');
    assert(dot.title.includes('refreshStopped 30'));
    health.updateConnection('catalog', false, new Error('network failed after expiry'));
    assert.equal(health.state.connection.retry, null);

    let responseMode = 'network';
    const fetchTimers = new Map();
    const fetching = {
        endpoint: '/portal', ENDPOINTS: ['/portal', '/fallback'], REQUEST_TIMEOUT_MS: 8000,
        DOMParser: class {
            parseFromString(body) { return {querySelector: () => body.includes('type="password"') ? {} : null}; }
        },
        endpointUrl: (endpoint, query) => endpoint + '?' + query, t: key => key,
        window: {setTimeout(callback) { const id = ++nextTimer; fetchTimers.set(id, callback); return id; }, clearTimeout: id => fetchTimers.delete(id)},
        fetch() {
            if (responseMode === 'network') return Promise.reject(new Error('Failed to fetch'));
            if (responseMode === 'timeout') return new Promise(() => {});
            const status = responseMode === 'server' ? 503 : responseMode === 'auth' ? 403 : 200;
            return Promise.resolve({status, ok: status === 200, headers: {get: () => responseMode === 'cached' ? 'offline' : null},
                text: () => Promise.resolve(responseMode === 'login' ? '<form><input type="password"></form>' : responseMode === 'invalid' ? '{"devices":' : '{"devices":[]}')});
        },
    };
    vm.createContext(fetching);
    vm.runInContext(functionSource('request'), fetching);
    await assert.rejects(fetching.request('action=catalog'), /Failed to fetch/);
    responseMode = 'server';
    await assert.rejects(fetching.request('action=catalog'), error => error.message === 'httpError' && error.retryable === true);
    for (const mode of ['auth', 'login']) {
        responseMode = mode;
        await assert.rejects(fetching.request('action=catalog'), error => error.message === 'loginExpired' && error.retryable === false);
    }
    responseMode = 'invalid';
    await assert.rejects(fetching.request('action=catalog'), error => error.message === 'invalidResponse' && error.retryable === true);
    responseMode = 'cached';
    assert.equal((await fetching.request('action=catalog'))._portalOffline, true);
    assert.equal(fetchTimers.size, 0);
    responseMode = 'timeout';
    const timedOut = assert.rejects(fetching.request('action=catalog'), /requestTimeout/);
    [...fetchTimers.values()].forEach(callback => callback());
    await timedOut;
    assert.equal(fetchTimers.size, 0);

    const oldChart = {key: 'AABBCCDDEEFF|temperature|C', points: [[123, 21]], kind: 'numeric'};
    const graph = {
        state: {selected: [oldChart.key], range: 3600, zoom: null, charts: [oldChart], chartGeneration: 0},
        request: () => Promise.reject(new Error('temporary series error')), findDevice: () => null,
        updateConnection(channel, pending, error) { graph.lastError = error; }, drawChart() {}, revealPage() {}, t: key => key,
    };
    vm.createContext(graph);
    vm.runInContext(functionSource('loadCharts'), graph);
    await graph.loadCharts();
    assert.equal(graph.state.charts[0], oldChart);
    assert.equal(graph.lastError.message, 'temporary series error');
    let finishSeries;
    graph.request = () => new Promise(resolve => { finishSeries = resolve; });
    const pendingChart = graph.loadCharts();
    assert.equal(graph.loadCharts(), pendingChart);
    finishSeries({kind: 'numeric', points: [[456, 22]]});
    await pendingChart;
    assert.equal(graph.state.charts[0].points[0][1], 22);
    assert.equal(graph.lastError, undefined);
    const pendingSeries = [];
    graph.request = () => new Promise(resolve => pendingSeries.push(resolve));
    graph.state.range = 7200;
    const olderRange = graph.loadCharts();
    graph.state.range = 86400;
    const newerRange = graph.loadCharts();
    pendingSeries[1]({kind: 'numeric', points: [[789, 23]]});
    await newerRange;
    pendingSeries[0]({kind: 'numeric', points: [[456, 19]]});
    await olderRange;
    assert.equal(graph.state.charts[0].points[0][1], 23);

    let catalogCalls = 0, rejectCatalog, finishCatalog;
    const catalogUpdates = [];
    const catalogTest = {
        state: {catalog: {devices: []}, selected: [], stats: null},
        request(query) { assert.equal(query, 'action=catalog'); catalogCalls++; return new Promise((resolve, reject) => { finishCatalog = resolve; rejectCatalog = reject; }); },
        updateConnection(channel, pending, error) { catalogUpdates.push({channel, pending, error}); },
        render() {}, revealPage() {}, loadMeta() {}, keyOf() {},
    };
    vm.createContext(catalogTest);
    vm.runInContext(functionSource('loadCatalog'), catalogTest);
    const firstCatalog = catalogTest.loadCatalog(true, false);
    assert.equal(catalogTest.loadCatalog(true, false), firstCatalog);
    rejectCatalog(new Error('temporary catalog error'));
    await firstCatalog;
    assert.equal(catalogCalls, 1);
    assert(catalogTest.state.catalog);
    assert.equal(catalogUpdates.at(-1).error.message, 'temporary catalog error');
    const nextCatalog = catalogTest.loadCatalog(true, false);
    finishCatalog({devices: []});
    await nextCatalog;
    assert.equal(catalogUpdates.at(-1).error, null);

    const rust = fs.readFileSync(path.join(__dirname, '../src/src/portal.rs'), 'utf8');
    const workerSource = rust.match(/const PORTAL_SW: &str = r#"([\s\S]*?)"#;/)[1];
    const listeners = {};
    let cacheHit = true;
    const worker = {
        URL, Request, Response, Headers,
        self: {location: {pathname: '/portal', origin: 'http://localhost'}, addEventListener: (name, callback) => { listeners[name] = callback; }},
        fetch: () => Promise.reject(new Error('offline')),
        caches: {match: () => Promise.resolve(cacheHit ? new Response('{"devices":[]}', {headers: {'Content-Type': 'application/json'}}) : null)},
    };
    vm.createContext(worker);
    vm.runInContext(workerSource, worker);
    for (const available of [true, false]) {
        cacheHit = available;
        let reply;
        listeners.fetch({request: new Request('http://localhost/portal?action=catalog'), respondWith: promise => { reply = promise; }});
        const response = await reply;
        assert.equal(response.headers.get('X-Portal-Cache'), 'offline');
        const data = await response.json();
        assert.equal(available ? Array.isArray(data.devices) : data.error === 'offline', true);
    }

    const timeContext = {};
    vm.createContext(timeContext);
    vm.runInContext(functionSource('timeTicks'), timeContext);
    const from = Date.parse('2026-11-05T08:03:17Z');
    for (const width of [180, 320, 600, 1200]) {
        for (const span of [60000, 3600000, 6 * 3600000, 86400000, 7 * 86400000, 90 * 86400000, 3 * 365 * 86400000]) {
            const ticks = timeContext.timeTicks(from, from + span, width, 100);
            assert(ticks.length >= 2 && ticks.length <= 16, `${width}px ${span}ms: ${ticks.length} ticks`);
            assert(ticks.every((tick, index) => tick >= from && tick <= from + span && (!index || tick > ticks[index - 1])));
            if (width >= 320) {
                assert(ticks.every((tick, index) => !index || (tick - ticks[index - 1]) * width / span >= 60), 'crowded grid');
            }
        }
    }
    const hourly = timeContext.timeTicks(from, from + 3600000, 600, 100);
    assert.equal(hourly[1] - hourly[0], 600000);
    assert.equal(timeContext.timeTicks(from, from, 600).length, 0);
    assert.equal(timeContext.timeTicks(from, from + 3600000, 0).length, 0);
    timeContext.pad2 = value => String(value).padStart(2, '0');
    vm.runInContext(functionSource('timeFormatter'), timeContext);
    const shortTicks = timeContext.timeTicks(from, from + 60000, 1200, 100);
    assert.equal(new Set(shortTicks.map(timeContext.timeFormatter(60000))).size, shortTicks.length);
    for (const start of ['2026-11-05T08:03:17Z', '2026-03-27T08:00:00Z', '2026-10-23T08:00:00Z']) {
        const stamp = Date.parse(start);
        const days = timeContext.timeTicks(stamp, stamp + 7 * 86400000, 600, 100);
        assert(days.length >= 5 && days.every(tick => new Date(tick).getHours() === 0));
    }

    const strokes = [];
    const drawing = {
        globalAlpha: 1, path: [], stack: [],
        beginPath() { this.path = []; },
        moveTo(...point) { this.path.push(point); },
        lineTo(...point) { this.path.push(point); },
        stroke() { strokes.push({path: this.path.slice(), alpha: this.globalAlpha, width: this.lineWidth, color: this.strokeStyle}); },
        save() { this.stack.push(this.globalAlpha); },
        restore() { this.globalAlpha = this.stack.pop(); },
        clearRect() {}, fillText() {}, measureText() { return {width: 40}; },
    };
    const chart = {kind: 'numeric', points: [[from, 20], [from + 3600000, 22]]};
    const block = {canvas: {getContext: () => drawing}, empty: {}, title: {}, charts: [chart]};
    Object.assign(timeContext, {
        state: {selected: ['temperature']}, MIN_WINDOW_MS: 60000,
        getComputedStyle: () => ({color: '#222', getPropertyValue: () => '#ddd'}), document: {body: {}},
        renderLegend() {}, blockTitle: () => 'Temperature', chartPoints: chart => chart.points,
        viewWindow: () => ({from, to: from + 3600000}), resize: () => ({width: 664, height: 300}),
        timeFormatter: () => () => '08:10', colorOf: () => '#123', drawSeries() {}, block,
    });
    vm.runInContext(['niceTicks', 'formatTick', 'drawBlock'].map(functionSource).join('\n') + '\ndrawBlock(block);', timeContext);
    const vertical = strokes.filter(stroke => stroke.path[0][0] === stroke.path[1][0]);
    const horizontal = strokes.filter(stroke => stroke.path[0][1] === stroke.path[1][1]);
    assert.equal(vertical.length, 6);
    assert(horizontal.length > 0);
    assert(vertical.every(stroke => stroke.alpha === horizontal[0].alpha && stroke.width === horizontal[0].width && stroke.color === horizontal[0].color));
    assert(vertical.every(stroke => stroke.path[0][1] === block.view.box.top && stroke.path[1][1] === block.view.box.bottom));
    assert.equal(drawing.globalAlpha, 1);

    const curves = {};
    vm.createContext(curves);
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../files/root/usr/mww/ble2uart_gateway/portal-curves.js'), 'utf8'), curves);
    vm.runInContext(functionSource('drawSeries'), curves);
    const samples = [[0, 0], [10, 1], [30, 1], [40, 0], [60, 3]];
    const originalSamples = JSON.stringify(samples);
    const paths = [];
    const pen = {
        beginPath() { paths.length = 0; }, moveTo(...point) { paths.push(['move', ...point]); },
        lineTo(...point) { paths.push(['line', ...point]); }, bezierCurveTo(...points) { paths.push(['curve', ...points]); },
        stroke() {}, arc() {}, fill() {},
    };
    Object.assign(curves, {state: {settings: {line: 'linear', points: false}}, chartPoints: chart => chart.points});
    const box = {left: 0, right: 60, top: 0, bottom: 3};
    const renderLine = kind => curves.drawSeries({}, pen, {points: samples, kind}, box, 0, 60, 0, 3, '#123', 0);
    renderLine('numeric');
    assert.equal(paths.filter(command => command[0] === 'line').length, samples.length - 1);
    assert(!paths.some(command => command[0] === 'curve'));
    curves.state.settings.line = 'smooth';
    renderLine('numeric');
    const segments = paths.filter(command => command[0] === 'curve');
    assert.equal(segments.length, samples.length - 1);
    segments.forEach((segment, index) => {
        assert.deepEqual(segment.slice(-2), [samples[index + 1][0], 3 - samples[index + 1][1]]);
        const low = Math.min(3 - samples[index][1], 3 - samples[index + 1][1]);
        const high = Math.max(3 - samples[index][1], 3 - samples[index + 1][1]);
        assert(segment[2] >= low && segment[2] <= high && segment[4] >= low && segment[4] <= high);
        assert(segment.slice(1).every(Number.isFinite));
    });
    renderLine('boolean');
    assert(!paths.some(command => command[0] === 'curve'));
    assert.equal(paths.filter(command => command[0] === 'line').length, 2 * (samples.length - 1));
    assert.equal(JSON.stringify(samples), originalSamples);
    const library = curves.PortalCurves;
    curves.PortalCurves = undefined;
    renderLine('numeric');
    assert(!paths.some(command => command[0] === 'curve'));
    curves.PortalCurves = library;
    for (const points of [[[0, 0]], [[0, 0], [10, 1]], [[0, 0], [0, 1], [10, 2]]]) {
        curves.drawSeries({}, pen, {points, kind: 'numeric'}, box, 0, 60, 0, 3, '#123', 0);
        assert(!paths.some(command => command[0] === 'curve'));
    }

    for (const mode of ['success', 'empty', 'failure', 'pending']) {
        let calls = 0;
        const context = {
            state: {deviceMeta: {}, catalog: {}},
            render() {},
            request(query) {
                assert.equal(query, 'action=meta');
                calls++;
                if (mode === 'failure') return Promise.reject(new Error('offline'));
                if (mode === 'pending') return new Promise(() => {});
                return Promise.resolve({devices: mode === 'empty' ? [] : [{mac: 'AABBCCDDEEFF', phy: 'Coded'}]});
            },
        };
        vm.createContext(context);
        vm.runInContext(functionSource('loadMeta'), context);
        for (let attempt = 0; attempt < 10; attempt++) {
            context.loadMeta();
            await new Promise(resolve => setImmediate(resolve));
        }
        assert.equal(calls, 1, mode);
        if (mode === 'success') assert.equal(context.state.deviceMeta.AABBCCDDEEFF.phy, 'Coded');
    }

    const device = {mac: 'AABBCCDDEEFF', name: '<sensor>', label: 'Kitchen', manufacturer: 'TestCo',
        model: 'Probe', firmware_version: '', last_ns: 1700000000000000000,
        series: [{attribute: 'contact', unit: '', kind: 'boolean', type: 'boolean', series_id: 0,
            first_ns: 1699999999000000000, last_ns: 1700000000000000000, value: false}]};
    const context = {
        state: {catalog: {devices: [device]}, deviceMeta: {[device.mac]: {phy: 'Coded', decoder: 'both', wire_format: 'bt_home_v2'}}, openDeviceInfo: {}},
        els: {devices: new Element('div')},
        document: {createElement: tag => new Element(tag), createTextNode: text => ({textContent: text})},
        t: key => key, age: () => 'now', isHiddenDevice: () => false, isHiddenSeries: () => false,
        keyOf: () => '', card: () => new Element('button'),
        request() { throw new Error('Opening details must not fetch'); },
    };
    vm.createContext(context);
    vm.runInContext(functionSource('deviceDetail') + '\n' + functionSource('renderDevices'), context);
    context.renderDevices();
    const details = context.els.devices.children[0].children.find(child => child.tag === 'details');
    assert(details);
    assert(details.children[0].attributes['aria-label'].includes('Kitchen'));
    assert.equal(details.children[0].children[0].className, 'pdevmeta');
    assert.equal(details.children[0].children[1].className, 'pinfo');
    for (const label of ['deviceMac', 'deviceName', 'deviceLabel', 'deviceManufacturer', 'deviceModel',
        'deviceFirmware', 'deviceLast', 'deviceSeries', 'devicePhy', 'deviceDecoder', 'deviceFormat',
        'seriesAttribute', 'seriesValue', 'seriesUnit', 'seriesKind', 'seriesType', 'seriesId', 'seriesFirst']) {
        assert(details.textContent.includes(label), label);
    }
    for (const value of ['<sensor>', 'unknown', 'false', 'Coded', 'both', 'bt_home_v2']) {
        assert(details.textContent.includes(value), value);
    }
    details.open = true;
    details.events.toggle();
    context.renderDevices();
    assert.equal(context.els.devices.children[0].children.find(child => child.tag === 'details').open, true);
    context.state.error = 'persistent connection error';
    context.renderDevices();
    assert.equal(context.els.devices.children[0].className, 'pfail');
    assert.equal(context.els.devices.children[0].attributes.role, 'alert');
    assert(context.els.devices.children.some(child => child.tag === 'section'));
    console.log('Portal UI: axis hold reset/pan, touch zoom/cancellation, curve interpolation, connection recovery and persistence passed');
}

main().catch(error => { console.error(error); process.exitCode = 1; });