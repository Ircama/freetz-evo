/* ble2uart_gateway sensor portal ------------------------------------------
 * Dependency-free dashboard: it reads /cgi-bin/extra/ble2uart_gateway/portal
 * (JSON produced by `ble2uart-gateway --portal`) and draws the charts on a
 * plain canvas, so the page also works on a router without Internet access.
 *
 * Chart interactions: hover crosshair with one marker per series, drag to zoom
 * into a time window, + / - / reset buttons, fullscreen.
 */
(function () {
	"use strict";

	var ENDPOINTS = [
		"/cgi-bin/extra/ble2uart_gateway/portal",
		"/cgi-bin/ble2uart_gateway/portal.cgi"
	];
	var endpoint = ENDPOINTS[0];
	var REFRESH_MS = 30000;
	var MAX_SERIES = 6;
	var MAX_SELECTED = 18;
	var MIN_WINDOW_MS = 60000;
	var COLORS = ["#0b6bcb", "#1a7f37", "#b45309", "#8250df", "#b42318", "#0e7490", "#6b7280", "#a16207"];

	var TEXT = {
		it: {
			subtitle: "Sensori", refresh: "Aggiorna ora", config: "Configurazione",
			resetView: "Reimposta le viste salvate",
			splitHint: "Trascina per ridimensionare i valori e il grafico (frecce sinistra/destra)",
			resetViewConfirm: "Azzerare grandezze, intervallo e zoom salvati in questo browser?",
			devices: "Dispositivi", series: "Grandezze", samples: "Campioni", updated: "Ultimo dato",
			never: "nessun dato", chartHint: "Tocca una grandezza per disegnarne il grafico.",
			chartEmpty: "Seleziona una grandezza dall'elenco.",
			chartLimit: "Massimo {n} grandezze per grafico.",
			chartModeUnits: "Dividi per unit\u00e0",
			chartModeSingle: "Un solo grafico",
			chartModeHint: "Un grafico per unit\u00e0 (temperatura, umidit\u00e0, tensione\u2026)",
			noRange: "Nessun dato nell'intervallo selezionato.",
			loading: "Caricamento\u2026", failed: "Errore: {error}", noDevices: "Nessun sensore nel database.",
			on: "attivo", off: "inattivo", true_: "s\u00ec", false_: "no", now: "ora",
			sec: "s", min: "min", hour: "h", day: "g",
			range1h: "1 h", range6h: "6 h", range24h: "24 h", range7d: "7 g", range30d: "30 g", rangeAll: "tutto",
			points: "{n} punti", loginExpired: "Sessione scaduta: ricaricare la pagina e accedere.",
			emptyDatabase: "Il database non contiene ancora misure.",
			zoomIn: "Ingrandisci", zoomOut: "Riduci", zoomReset: "Reimposta zoom",
			fullscreen: "Schermo intero", exitFullscreen: "Esci da schermo intero",
			zoomHint: "Trascina sul grafico per selezionare un intervallo.",
			zoomRange: "Zoom: {from} \u2192 {to}",
			panLeft: "Indietro nel tempo", panRight: "Avanti nel tempo",
			helpOpen: "Aiuto e scorciatoie", helpLink: "Aiuto e scorciatoie (?)",
			helpTitle: "Scorciatoie di tastiera e mouse",
			helpPan: "Sposta la finestra nel tempo di un quarto della durata visibile.",
			helpPanFine: "Passo breve, un decimo della durata visibile.",
			helpZoom: "Ingrandisce o riduce intorno al centro della finestra.",
			helpReset: "Torna all'intervallo scelto con i pulsanti 1 h … tutto.",
			helpFullscreen: "Schermo intero del grafico; premi di nuovo per uscire.",
			helpDragZoom: "Trascina sul grafico per selezionare un intervallo di tempo.",
			helpDragPan: "Trascina tenendo premuto Maiusc per spostare la finestra.",
			helpHelp: "Apre o chiude questa finestra di aiuto.",
			helpClose: "Chiudi", helpNote: "I dati si aggiornano da soli ogni 30 secondi.",
			maximize: "Schermo intero della pagina (senza barra del browser)",
			maximizeOff: "Esci da schermo intero",
			helpAppFullscreen: "Schermo intero della pagina: nasconde la barra del browser e la barra di stato, come un'app installata.",
			install: "Installa l'app",
			offlineBanner: "Offline: valori salvati dall'ultimo aggiornamento riuscito.",
			offlineData: "nessun collegamento al Fritz!Box e nessun dato in cache",
			pwaTitle: "Installa il portale come app",
			pwaBodyChrome: "Il browser non ha ancora offerto l'installazione. Apri il menu del browser (\u22ee) e scegli \u201cInstalla app\u201d o \u201cAggiungi a schermata Home\u201d. L'installazione richiede https oppure localhost: con http://fritz.box il browser mostra solo un segnalibro.",
			pwaBodyIos: "Tocca <kbd>Condividi</kbd>, poi <kbd>Aggiungi a Home</kbd>: il portale si apre a schermo intero con l'icona dei sensori.",
			pwaBodyInstalled: "Il portale \u00e8 installato: aprilo dall'icona sul telefono o dal menu delle app del browser."
		},
		en: {
			subtitle: "Sensors", refresh: "Refresh now", config: "Configuration",
			resetView: "Reset the saved views",
			splitHint: "Drag to resize the values and the chart (left/right arrows)",
			resetViewConfirm: "Clear the attributes, time range and zoom saved in this browser?",
			devices: "Devices", series: "Attributes", samples: "Samples", updated: "Latest sample",
			never: "no data", chartHint: "Tap an attribute to draw its chart.",
			chartEmpty: "Select an attribute from the list.",
			chartLimit: "At most {n} attributes per chart.",
			chartModeUnits: "Split by unit",
			chartModeSingle: "Single chart",
			chartModeHint: "One chart per unit (temperature, humidity, voltage\u2026)",
			noRange: "No data in the selected range.",
			loading: "Loading\u2026", failed: "Error: {error}", noDevices: "No sensors in the database.",
			on: "on", off: "off", true_: "yes", false_: "no", now: "now",
			sec: "s", min: "min", hour: "h", day: "d",
			range1h: "1 h", range6h: "6 h", range24h: "24 h", range7d: "7 d", range30d: "30 d", rangeAll: "all",
			points: "{n} points", loginExpired: "Session expired: reload the page and sign in.",
			emptyDatabase: "The database does not contain measurements yet.",
			zoomIn: "Zoom in", zoomOut: "Zoom out", zoomReset: "Reset zoom",
			fullscreen: "Fullscreen", exitFullscreen: "Exit fullscreen",
			zoomHint: "Drag on the chart to select a time range.",
			zoomRange: "Zoom: {from} \u2192 {to}",
			panLeft: "Back in time", panRight: "Forward in time",
			helpOpen: "Help and shortcuts", helpLink: "Help and shortcuts (?)",
			helpTitle: "Keyboard and mouse shortcuts",
			helpPan: "Move the window in time by a quarter of the visible span.",
			helpPanFine: "Small step, one tenth of the visible span.",
			helpZoom: "Zoom in or out around the centre of the window.",
			helpReset: "Return to the range selected with the 1 h … all buttons.",
			helpFullscreen: "Chart fullscreen; press again to leave it.",
			helpDragZoom: "Drag on the chart to select a time range.",
			helpDragPan: "Drag while holding Shift to move the window.",
			helpHelp: "Open or close this help window.",
			helpClose: "Close", helpNote: "Data refreshes automatically every 30 seconds.",
			maximize: "Page fullscreen (no browser bar)",
			maximizeOff: "Leave fullscreen",
			helpAppFullscreen: "Fullscreen for the whole page: hides the browser and status bars, like an installed app.",
			install: "Install the app",
			offlineBanner: "Offline: values cached by the last successful refresh.",
			offlineData: "no connection to the router and no cached data",
			pwaTitle: "Install the portal as an app",
			pwaBodyChrome: "The browser has not offered the installation yet. Open the browser menu (\u22ee) and choose \u201cInstall app\u201d or \u201cAdd to Home screen\u201d. Installing needs https or localhost: over http://fritz.box the browser only stores a bookmark.",
			pwaBodyIos: "Tap <kbd>Share</kbd>, then <kbd>Add to Home Screen</kbd>: the portal opens full screen with the sensor icon.",
			pwaBodyInstalled: "The portal is installed: open it from the icon on the phone or from the browser app menu."
		},
		de: {
			subtitle: "Sensoren", refresh: "Jetzt aktualisieren", config: "Konfiguration",
			resetView: "Gespeicherte Ansichten zur\u00fccksetzen",
			splitHint: "Ziehen, um Werte und Diagramm zu skalieren (Pfeiltasten links/rechts)",
			resetViewConfirm: "Gespeicherte Messwerte, Zeitraum und Zoom in diesem Browser l\u00f6schen?",
			devices: "Ger\u00e4te", series: "Messwerte", samples: "Messwerte", updated: "Letzter Wert",
			never: "keine Daten", chartHint: "Messwert antippen, um das Diagramm zu zeichnen.",
			chartEmpty: "Messwert aus der Liste w\u00e4hlen.",
			chartLimit: "H\u00f6chstens {n} Messwerte pro Diagramm.",
			chartModeUnits: "Nach Einheit trennen",
			chartModeSingle: "Ein Diagramm",
			chartModeHint: "Ein Diagramm pro Einheit (Temperatur, Feuchte, Spannung\u2026)",
			noRange: "Keine Daten im gew\u00e4hlten Zeitraum.",
			loading: "Lade\u2026", failed: "Fehler: {error}", noDevices: "Keine Sensoren in der Datenbank.",
			on: "aktiv", off: "inaktiv", true_: "ja", false_: "nein", now: "jetzt",
			sec: "s", min: "min", hour: "h", day: "T",
			range1h: "1 h", range6h: "6 h", range24h: "24 h", range7d: "7 T", range30d: "30 T", rangeAll: "alles",
			points: "{n} Punkte", loginExpired: "Sitzung abgelaufen: Seite neu laden und anmelden.",
			emptyDatabase: "Die Datenbank enth\u00e4lt noch keine Messwerte.",
			zoomIn: "Vergr\u00f6\u00dfern", zoomOut: "Verkleinern", zoomReset: "Zoom zur\u00fccksetzen",
			fullscreen: "Vollbild", exitFullscreen: "Vollbild beenden",
			zoomHint: "Im Diagramm ziehen, um einen Zeitraum zu w\u00e4hlen.",
			zoomRange: "Zoom: {from} \u2192 {to}",
			panLeft: "Zur\u00fcck", panRight: "Vorw\u00e4rts",
			helpOpen: "Hilfe und Tasten", helpLink: "Hilfe und Tasten (?)",
			helpTitle: "Tastatur- und Mausbefehle",
			helpPan: "Verschiebt das Fenster um ein Viertel der sichtbaren Dauer.",
			helpPanFine: "Kleiner Schritt, ein Zehntel der sichtbaren Dauer.",
			helpZoom: "Vergr\u00f6\u00dfert oder verkleinert um die Fenstermitte.",
			helpReset: "Zur\u00fcck zum mit 1 h … alles gew\u00e4hlten Zeitraum.",
			helpFullscreen: "Diagramm im Vollbild; erneut dr\u00fccken zum Beenden.",
			helpDragZoom: "Im Diagramm ziehen, um einen Zeitraum zu w\u00e4hlen.",
			helpDragPan: "Mit gedr\u00fcckter Umschalttaste ziehen, um das Fenster zu verschieben.",
			helpHelp: "\u00d6ffnet oder schlie\u00dft dieses Hilfefenster.",
			helpClose: "Schlie\u00dfen", helpNote: "Die Daten werden alle 30 Sekunden automatisch aktualisiert.",
			maximize: "Ganzseitiges Vollbild (ohne Browserleiste)",
			maximizeOff: "Vollbild beenden",
			helpAppFullscreen: "Vollbild der ganzen Seite: blendet Browser- und Statusleiste aus, wie eine installierte App.",
			install: "App installieren",
			offlineBanner: "Offline: Werte aus der letzten erfolgreichen Aktualisierung.",
			offlineData: "keine Verbindung zum Router und keine gespeicherten Daten",
			pwaTitle: "Portal als App installieren",
			pwaBodyChrome: "Der Browser hat die Installation noch nicht angeboten. Browsermen\u00fc (\u22ee) \u00f6ffnen und \u201eApp installieren\u201c bzw. \u201eZum Startbildschirm hinzuf\u00fcgen\u201c w\u00e4hlen. Die Installation braucht https oder localhost: \u00fcber http://fritz.box legt der Browser nur ein Lesezeichen an.",
			pwaBodyIos: "<kbd>Teilen</kbd> antippen, dann <kbd>Zum Home-Bildschirm</kbd>: Das Portal \u00f6ffnet im Vollbild mit dem Sensor-Symbol.",
			pwaBodyInstalled: "Das Portal ist installiert: \u00fcber das Symbol am Telefon oder das App-Men\u00fc des Browsers \u00f6ffnen."
		}
	};

	var RANGES = [
		{ seconds: 3600, label: "range1h" },
		{ seconds: 21600, label: "range6h" },
		{ seconds: 86400, label: "range24h" },
		{ seconds: 604800, label: "range7d" },
		{ seconds: 2592000, label: "range30d" },
		{ seconds: 0, label: "rangeAll" }
	];

	var lang = "en";
	var CHART_MODE_KEY = "ble2uart-portal-chartmode";

	var state = {
		catalog: null,
		selected: [],
		range: 86400,
		zoom: null,
		charts: [],
		error: "",
		hover: null,
		drag: null,
		pan: null,
		view: null,
		blocks: [],
		active: null,
		chartMode: "unit"
	};
	var els = {};

	function t(key, values) {
		var table = TEXT[lang] || TEXT.en;
		var text = table[key] || TEXT.en[key] || key;
		if (values) {
			Object.keys(values).forEach(function (name) {
				text = text.replace("{" + name + "}", values[name]);
			});
		}
		return text;
	}

	function pickLanguage() {
		var stored = null;
		try { stored = window.localStorage.getItem("ble2uart-portal-lang"); } catch (e) { stored = null; }
		var candidate = (stored || navigator.language || "en").slice(0, 2).toLowerCase();
		lang = TEXT[candidate] ? candidate : "en";
	}

	/* ---------------------------------------------------------- persistence
	 * The selected attributes, the time range and the zoom window are stored in
	 * the browser (localStorage, with a cookie as a fallback), so closing and
	 * reopening the portal restores the last views. The header button with the
	 * reset icon (id="resetview") deletes the stored state. */
	var STORE_KEY = "ble2uart-portal-view";
	var STORE_DAYS = 365;

	function cookieRead(name) {
		var parts = document.cookie ? document.cookie.split("; ") : [];
		for (var index = 0; index < parts.length; index++) {
			var pair = parts[index].split("=");
			if (pair[0] === name) {
				try { return decodeURIComponent(pair.slice(1).join("=")); } catch (e) { return null; }
			}
		}
		return null;
	}

	function cookieWrite(name, value, days) {
		var expires = "";
		if (days > 0) {
			expires = "; expires=" + new Date(Date.now() + days * 86400000).toUTCString();
		} else {
			expires = "; expires=Thu, 01 Jan 1970 00:00:00 GMT";
		}
		document.cookie = name + "=" + encodeURIComponent(value) + expires + "; path=/; SameSite=Lax";
	}

	function readStore() {
		var raw = null;
		try { raw = window.localStorage.getItem(STORE_KEY); } catch (e) { raw = null; }
		if (raw === null) { raw = cookieRead(STORE_KEY); }
		if (!raw) { return null; }
		try { return JSON.parse(raw); } catch (e) { return null; }
	}

	function writeStore() {
		var data = {
			selected: state.selected.slice(0, MAX_SELECTED),
			range: state.range,
			zoom: state.zoom ? { from: Math.round(state.zoom.from), to: Math.round(state.zoom.to) } : null
		};
		var raw = JSON.stringify(data);
		try { window.localStorage.setItem(STORE_KEY, raw); } catch (e) { /* private mode */ }
		try { cookieWrite(STORE_KEY, raw, STORE_DAYS); } catch (e) { /* cookies disabled */ }
	}

	function clearStore() {
		try { window.localStorage.removeItem(STORE_KEY); } catch (e) { /* ignore */ }
		try { window.localStorage.removeItem(SPLIT_KEY); } catch (e) { /* ignore */ }
		try { cookieWrite(STORE_KEY, "", -1); } catch (e) { /* ignore */ }
	}

	function restoreStore() {
		var data = readStore();
		if (!data || typeof data !== "object") { return; }
		if (Object.prototype.toString.call(data.selected) === "[object Array]") {
			state.selected = data.selected
				.filter(function (key) { return typeof key === "string"; })
				.slice(0, MAX_SELECTED);
		}
		var ranges = RANGES.map(function (item) { return item.seconds; });
		if (ranges.indexOf(data.range) >= 0) { state.range = data.range; }
		var zoom = data.zoom;
		if (zoom && typeof zoom.from === "number" && typeof zoom.to === "number" && zoom.to > zoom.from) {
			state.zoom = { from: zoom.from, to: zoom.to };
		}
	}

	/* ------------------------------------------------------------- splitter
	 * Values on the left, chart on the right, with a draggable vertical line
	 * between them. The share is kept in the browser like the chart view, and
	 * the splitter element is created here because the page shell is generated
	 * by the daemon: a missing splitter would make the chart fall into the
	 * fixed 8px grid column and disappear. */
	var SPLIT_KEY = "ble2uart-portal-split-v2";
	var splitPct = 47;   /* share of the values column, in percent */
	var SPLIT_COLUMNS_FIXED = 28;   /* 8px splitter + two 10px gaps */
	var SPLIT_POINTER_OFFSET = 14;   /* 10px gap + half of the 8px splitter */

	function splitRead() {
		var stored = null;
		try { stored = window.localStorage.getItem(SPLIT_KEY); } catch (e) { stored = null; }
		var value = Number(stored);
		if (!isFinite(value) || value < 20 || value > 80) { return 47; }
		return value;
	}

	function splitApply(pct) {
		var layout = document.querySelector(".playout");
		if (!layout) { return; }
		splitPct = Math.min(80, Math.max(20, Math.round(pct)));
		layout.style.setProperty("--device-fr", splitPct + "fr");
		layout.style.setProperty("--chart-fr", (100 - splitPct) + "fr");
		try { window.localStorage.setItem(SPLIT_KEY, String(splitPct)); } catch (e) { /* ignore */ }
		drawChart();
	}

	function ensureSplitter() {
		var layout = document.querySelector(".playout");
		var chart = layout && layout.querySelector(".pchart");
		if (!layout || !chart) { return; }
		splitApply(splitRead());
		if (layout.querySelector(".psplitter")) { return; }
		var bar = document.createElement("div");
		bar.className = "psplitter";
		bar.tabIndex = 0;
		bar.setAttribute("role", "separator");
		bar.setAttribute("aria-orientation", "vertical");
		bar.setAttribute("aria-valuemin", "25");
		bar.setAttribute("aria-valuemax", "80");
		bar.title = t("splitHint");
		layout.insertBefore(bar, chart);
		var dragging = false;
		var onMove = function (event) {
			if (!dragging) { return; }
			var rect = layout.getBoundingClientRect();
			var available = rect.width - SPLIT_COLUMNS_FIXED;
			if (available <= 0) { return; }
			// The pointer position *is* the left share: the fr split distributes only
			// the space left after the splitter column and the two gaps, and the gap
			// plus half of the splitter has to be discounted so the line stays under
			// the cursor.
			splitApply((event.clientX - rect.left - SPLIT_POINTER_OFFSET) / available * 100);
		};
		var onStop = function () {
			if (!dragging) { return; }
			dragging = false;
			bar.removeAttribute("aria-valuenow");
			window.removeEventListener("pointermove", onMove);
			window.removeEventListener("pointerup", onStop);
			window.removeEventListener("pointercancel", onStop);
		};
		bar.addEventListener("pointerdown", function (event) {
			if (event.button !== 0) { return; }
			dragging = true;
			bar.setAttribute("aria-valuenow", String(splitPct));
			window.addEventListener("pointermove", onMove);
			window.addEventListener("pointerup", onStop);
			window.addEventListener("pointercancel", onStop);
			event.preventDefault();
		});
		bar.addEventListener("keydown", function (event) {
			if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") { return; }
			splitApply(splitPct + (event.key === "ArrowLeft" ? -2 : 2));
			bar.setAttribute("aria-valuenow", String(splitPct));
			event.preventDefault();
		});
	}

	/** Header button: forget the stored views and start from an empty chart. */
	function resetView() {
		if (!window.confirm(t("resetViewConfirm"))) { return; }
		clearStore();
		state.selected = [];
		state.charts = [];
		state.range = 86400;
		state.zoom = null;
		state.blocks.forEach(function (item) { item.hover = null; });
		state.error = "";
		splitApply(47);
		render();
	}

	/* ---------------------------------------------------------------- fetch */

	function request(query) {
		var url = endpoint + "?" + query;
		return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
			.then(function (response) {
				return response.text().then(function (body) {
					if (response.status === 404 && ENDPOINTS.indexOf(endpoint) === 0) {
						throw new Error("endpoint");
					}
					var data = null;
					try { data = JSON.parse(body); } catch (e) { data = null; }
					if (!data) {
						throw new Error(t("loginExpired"));
					}
					if (data.ok === false) {
						throw new Error(data.error === "offline" ? t("offlineData") : (data.error || "unknown error"));
					}
					return data;
				});
			})
			.catch(function (error) {
				if (error && error.message === "endpoint" && ENDPOINTS.length > 1) {
					endpoint = ENDPOINTS[1];
					return request(query);
				}
				throw error;
			});
	}

	/* --------------------------------------------------------------- format */

	function number(value, unit) {
		if (value === null || value === undefined) { return "\u2014"; }
		if (typeof value === "boolean") { return value ? t("true_") : t("false_"); }
		if (typeof value === "string") { return value; }
		if (typeof value === "number") {
			var digits = Math.abs(value) >= 100 ? 0 : (Math.abs(value) >= 10 ? 1 : 2);
			return value.toFixed(digits).replace(/\.0+$/, "");
		}
		if (typeof value === "object") { return JSON.stringify(value); }
		return String(value);
	}

	function age(ns, now) {
		if (!ns) { return t("never"); }
		var seconds = Math.max(0, Math.round((now - ns) / 1e9));
		if (seconds < 60) { return seconds + " " + t("sec"); }
		if (seconds < 3600) { return Math.round(seconds / 60) + " " + t("min"); }
		if (seconds < 86400) { return (seconds / 3600).toFixed(seconds < 36000 ? 1 : 0) + " " + t("hour"); }
		return (seconds / 86400).toFixed(seconds < 864000 ? 1 : 0) + " " + t("day");
	}

	function pad2(value) { return value < 10 ? "0" + value : String(value); }

	function stamp(ms) {
		var date = new Date(ms);
		return pad2(date.getDate()) + "/" + pad2(date.getMonth() + 1) + " " +
			pad2(date.getHours()) + ":" + pad2(date.getMinutes());
	}

	function keyOf(mac, series) {
		return mac + "|" + series.attribute + "|" + series.unit;
	}

	/* --------------------------------------------------------------- render */

	function render() {
		renderHeader();
		renderKpis();
		renderDevices();
		renderRanges();
		renderZoom();
		drawChart();
	}

	function renderHeader() {
		var catalog = state.catalog;
		document.getElementById("subtitle").textContent = t("subtitle");
		document.getElementById("reload").title = t("refresh");
		document.getElementById("config").title = t("config");
		if (!catalog) { return; }
		var newest = 0;
		(catalog.devices || []).forEach(function (device) {
			(device.series || []).forEach(function (series) {
				if (series.last_ns > newest) { newest = series.last_ns; }
			});
		});
		var dot = document.querySelector(".pdot");
		var seconds = newest ? (Date.now() - newest / 1e6) / 1000 : null;
		dot.className = "pdot " + (seconds === null ? "" : seconds < 900 ? "pok" : "pstale");
		els.stamp.textContent = newest ? age(newest, Date.now() * 1e6) : t("never");
	}

	function renderKpis() {
		var catalog = state.catalog;
		els.kpis.textContent = "";
		if (!catalog) { return; }
		var series = 0;
		var newest = 0;
		var devices = catalog.devices || [];
		devices.forEach(function (device) {
			(device.series || []).forEach(function (item) {
				series++;
				if (item.last_ns > newest) { newest = item.last_ns; }
			});
		});
		var kpis = [
			[t("devices"), String(devices.length), ""],
			[t("series"), String(series), ""],
			[t("samples"), catalog.samples ? String(catalog.samples) : "\u2014", ""],
			[t("updated"), newest ? age(newest, catalog.now_ns) : t("never"), catalog.database || ""]
		];
		kpis.forEach(function (item) {
			var box = document.createElement("div");
			box.className = "pkpi";
			var name = document.createElement("span");
			name.className = "k";
			name.textContent = item[0];
			var value = document.createElement("span");
			value.className = "v";
			value.textContent = item[1];
			if (item[2]) { value.title = item[2]; }
			box.appendChild(name);
			box.appendChild(value);
			els.kpis.appendChild(box);
		});
	}

	function renderDevices() {
		var catalog = state.catalog;
		var now = catalog ? catalog.now_ns : Date.now() * 1e6;
		els.devices.textContent = "";
		if (state.error) {
			var failure = document.createElement("p");
			failure.className = "pfail";
			failure.textContent = t("failed", { error: state.error });
			els.devices.appendChild(failure);
			return;
		}
		if (!catalog) {
			var loading = document.createElement("p");
			loading.className = "pempty";
			loading.textContent = t("loading");
			els.devices.appendChild(loading);
			return;
		}
		if (!catalog.devices || !catalog.devices.length) {
			var empty = document.createElement("p");
			empty.className = "pempty";
			empty.textContent = t("emptyDatabase");
			els.devices.appendChild(empty);
			return;
		}
		catalog.devices.forEach(function (device) {
			var section = document.createElement("section");
			section.className = "pdevice";
			var header = document.createElement("header");
			var title = document.createElement("h3");
			title.textContent = device.name || device.mac;
			var right = document.createElement("span");
			right.className = "page";
			right.textContent = age(device.last_ns, now);
			header.appendChild(title);
			header.appendChild(right);
			var mac = document.createElement("span");
			mac.className = "pmac";
			mac.textContent = device.mac;
			header.appendChild(mac);
			section.appendChild(header);

			var grid = document.createElement("div");
			grid.className = "pseries";
			(device.series || []).forEach(function (series) {
				grid.appendChild(card(device.mac, series, now));
			});
			section.appendChild(grid);
			els.devices.appendChild(section);
		});
	}

	function card(mac, series, now) {
		var key = keyOf(mac, series);
		var index = state.selected.indexOf(key);
		var selected = index >= 0;
		var button = document.createElement("button");
		button.type = "button";
		button.className = "pcard" + (series.kind === "text" ? " pstatic" : "") + (selected ? " psel" : "");
		if (selected) {
			button.style.setProperty("--swatch", COLORS[index % COLORS.length]);
		}
		var attribute = document.createElement("span");
		attribute.className = "a";
		attribute.textContent = series.attribute;
		var value = document.createElement("span");
		value.className = "v";
		if (series.kind === "boolean") {
			value.className += " pboo " + (series.value ? "pon" : "poff");
			value.textContent = series.value ? t("on") : t("off");
		} else {
			value.textContent = number(series.value);
			if (series.unit) {
				var unit = document.createElement("span");
				unit.className = "u";
				unit.textContent = series.unit;
				value.appendChild(unit);
			}
		}
		var stampLine = document.createElement("span");
		stampLine.className = "t";
		stampLine.textContent = age(series.last_ns, now);
		button.appendChild(attribute);
		button.appendChild(value);
		button.appendChild(stampLine);
		if (series.kind !== "text") {
			button.addEventListener("click", function () { toggle(mac, series); });
			button.title = t("chartHint");
		}
		return button;
	}

	function toggle(mac, series) {
		var key = keyOf(mac, series);
		var index = state.selected.indexOf(key);
		if (index >= 0) {
			state.selected.splice(index, 1);
		} else {
			var unit = series && series.unit ? series.unit : "";
			var samePanel = state.charts.filter(function (chart) { return (chart.unit || "") === unit; }).length;
			if (samePanel >= MAX_SERIES) {
				state.error = t("chartLimit", { n: MAX_SERIES });
				render();
				return;
			}
			state.selected.push(key);
		}
		state.error = "";
		state.zoom = null;
		state.hover = null;
		writeStore();
		loadCharts();
		render();
	}

	function renderRanges() {
		els.ranges.textContent = "";
		RANGES.forEach(function (item) {
			var button = document.createElement("button");
			button.type = "button";
			button.textContent = t(item.label);
			button.setAttribute("aria-pressed", state.range === item.seconds && !state.zoom ? "true" : "false");
			button.addEventListener("click", function () {
				state.range = item.seconds;
				state.zoom = null;
				state.hover = null;
				writeStore();
				loadCharts();
				render();
			});
			els.ranges.appendChild(button);
		});
	}

	function renderZoom() {
		var active = !!state.zoom;
		els.zoominfo.hidden = !active;
		els.zoominfo.textContent = active ? t("zoomRange", { from: stamp(state.zoom.from), to: stamp(state.zoom.to) }) : "";
		els.zoomreset.disabled = !active;
		els.zoomout.disabled = !active;
		els.zoomin.title = t("zoomIn") + " (+) \u00b7 " + t("zoomHint");
		els.zoomout.title = t("zoomOut") + " (\u2212)";
		els.zoomreset.title = t("zoomReset") + " (0)";
		els.panleft.title = t("panLeft") + " (\u2190)";
		els.panright.title = t("panRight") + " (\u2192)";
		var hasChart = !!(state.charts && state.charts.some(function (chart) { return chart.points && chart.points.length; }));
		els.panleft.disabled = !hasChart;
		els.panright.disabled = !hasChart;
		els.help.title = t("helpOpen");
		if (els.resetview) { els.resetview.title = t("resetView"); }
		els.helplink.textContent = t("helpLink");
		var full = document.fullscreenElement === els.panel;
		els.fullscreen.title = full ? t("exitFullscreen") : t("fullscreen");
		els.fullscreen.textContent = full ? "\u2715" : "\u26f6";
	}

	var SHORTCUTS = [
		{ keys: "\u2190 \u2192", label: "helpPan" },
		{ keys: "Shift + \u2190 \u2192", label: "helpPanFine" },
		{ keys: "+ \u2212", label: "helpZoom" },
		{ keys: "0 / Home / R", label: "helpReset" },
		{ keys: "F", label: "helpFullscreen" },
		{ keys: "M", label: "helpAppFullscreen" },
		{ keys: "Drag", label: "helpDragZoom" },
		{ keys: "Shift + drag", label: "helpDragPan" },
		{ keys: "?", label: "helpHelp" }
	];

	/** Help lives in a modal dialog instead of a tooltip on the whole panel, so
	 *  it never overlaps the hover tooltip of the chart. */
	function renderHelp() {
		els.helptitle.textContent = t("helpTitle");
		els.helpnote.textContent = t("helpNote");
		els.helpclose.textContent = t("helpClose");
		els.helpbody.textContent = "";
		SHORTCUTS.forEach(function (item) {
			var term = document.createElement("dt");
			term.textContent = item.keys;
			var detail = document.createElement("dd");
			detail.textContent = t(item.label);
			els.helpbody.appendChild(term);
			els.helpbody.appendChild(detail);
		});
	}

	function openHelp() {
		hideTip();
		if (!els.helpbox) { return; }
		renderHelp();
		if (els.helpbox.showModal && !els.helpbox.open) { els.helpbox.showModal(); }
	}

	function seriesLabel(chart) {
		var device = findDevice(chart.mac);
		var name = device ? (device.name || device.mac) : chart.mac;
		return name + " \u00b7 " + chart.attribute + (chart.unit ? " (" + chart.unit + ")" : "");
	}

	function findDevice(mac) {
		var catalog = state.catalog;
		if (!catalog || !catalog.devices) { return null; }
		for (var index = 0; index < catalog.devices.length; index++) {
			if (catalog.devices[index].mac === mac) { return catalog.devices[index]; }
		}
		return null;
	}

	/* ------------------------------------------------------ chart panels */

	/** Colour of a series: stable across panels and the legend. */
	function colorOf(chart) {
		var index = state.charts.indexOf(chart);
		return COLORS[(index < 0 ? 0 : index) % COLORS.length];
	}

	/** Panel key of a series: its unit (booleans and unitless values group too). */
	function panelKey(chart) {
		if (chart.unit) { return chart.unit; }
		if (chart.kind === "boolean") { return "\u2022"; }
		return "";
	}

	/** Series split into panels: one per unit when chartMode is "unit". */
	function groupCharts() {
		if (!state.charts.length || state.chartMode === "single") { return [state.charts.slice()]; }
		var groups = [];
		var seen = {};
		state.charts.forEach(function (chart) {
			var key = panelKey(chart);
			if (!seen.hasOwnProperty(key)) { seen[key] = groups.length; groups.push([]); }
			groups[seen[key]].push(chart);
		});
		return groups;
	}

	function removeSeries(chart) {
		state.selected = state.selected.filter(function (key) { return key !== chart.key; });
		state.charts = state.charts.filter(function (item) { return item.key !== chart.key; });
		state.zoom = null;
		state.blocks.forEach(function (block) { block.hover = null; });
		writeStore();
		render();
	}

	function createBlock() {
		var root = document.createElement("div");
		root.className = "pchartblock";
		var title = document.createElement("h3");
		title.className = "pchartblocktitle";
		var wrap = document.createElement("div");
		wrap.className = "pcanvas";
		var canvas = document.createElement("canvas");
		var empty = document.createElement("div");
		empty.className = "pempty";
		wrap.appendChild(canvas);
		wrap.appendChild(empty);
		var legend = document.createElement("div");
		legend.className = "plegend";
		root.appendChild(title);
		root.appendChild(wrap);
		root.appendChild(legend);
		var block = {
			root: root, title: title, canvas: canvas, empty: empty, legend: legend,
			charts: [], view: null, hover: null, drag: null, pan: null
		};
		root.__block = block;
		canvas.addEventListener("mousemove", function (event) { onMove(block, event); });
		canvas.addEventListener("mousedown", function (event) { onDown(block, event); });
		canvas.addEventListener("mouseleave", function () { if (!block.drag) { hideTip(block); } });
		canvas.addEventListener("touchstart", function (event) {
			if (event.touches.length === 1) {
				state.active = block;
				var ms = timeAt(block, event.touches[0].clientX);
				if (ms !== null) { showTip(block, ms, event.touches[0].clientX, event.touches[0].clientY); }
			}
		}, { passive: true });
		canvas.addEventListener("touchend", function () { hideTip(block); });
		return block;
	}

	/** Create/remove panels so that there is one per series group. */
	function syncBlocks(groups) {
		var host = els.blocks;
		if (!host) { return; }
		while (host.children.length > groups.length) { host.removeChild(host.lastElementChild); }
		while (host.children.length < groups.length) { host.appendChild(createBlock().root); }
		state.blocks = [];
		for (var index = 0; index < groups.length; index++) {
			var block = host.children[index].__block;
			if (!block) { continue; }
			block.charts = groups[index];
			state.blocks.push(block);
		}
		if (state.blocks.indexOf(state.active) < 0) { state.active = state.blocks[0] || null; }
	}

	/** Host element for the panels, plus the split/merge toggle button. */
	function ensureChartHost() {
		if (els.blocks) { return; }
		var panel = els.panel;
		var single = panel.querySelector(".pcanvas");
		var host = document.createElement("div");
		host.className = "pcanvases";
		if (single && single.parentNode === panel) { panel.insertBefore(host, single); } else { panel.appendChild(host); }
		if (single) { single.hidden = true; }
		var legend = document.getElementById("legend");
		if (legend) { legend.hidden = true; }
		var title = document.getElementById("charttitle");
		if (title) { title.hidden = true; }
		els.blocks = host;
		var controls = panel.querySelector(".pcontrols");
		if (controls && !els.chartmode) {
			var button = document.createElement("button");
			button.type = "button";
			button.id = "chartmode";
			button.addEventListener("click", function () {
				state.chartMode = state.chartMode === "unit" ? "single" : "unit";
				chartModeWrite(state.chartMode);
				render();
			});
			controls.appendChild(button);
			els.chartmode = button;
		}
	}

	function chartModeWrite(mode) {
		try { window.localStorage.setItem(CHART_MODE_KEY, mode); } catch (e) { /* ignore */ }
	}

	function chartModeRead() {
		var stored = null;
		try { stored = window.localStorage.getItem(CHART_MODE_KEY); } catch (e) { stored = null; }
		return stored === "single" ? "single" : "unit";
	}

	function renderChartMode() {
		if (!els.chartmode) { return; }
		var split = state.chartMode === "unit";
		els.chartmode.textContent = split ? t("chartModeSingle") : t("chartModeUnits");
		els.chartmode.title = t("chartModeHint");
		els.chartmode.setAttribute("aria-pressed", split ? "true" : "false");
	}

	function renderLegend(block) {
		block.legend.textContent = "";
		block.charts.forEach(function (chart) {
			var chip = document.createElement("button");
			chip.type = "button";
			chip.className = "chip";
			chip.style.setProperty("--swatch", colorOf(chart));
			var dot = document.createElement("i");
			var text = document.createElement("span");
			text.textContent = seriesLabel(chart);
			chip.appendChild(dot);
			chip.appendChild(text);
			chip.title = t("chartHint");
			chip.addEventListener("click", function () { removeSeries(chart); });
			block.legend.appendChild(chip);
		});
	}

	/* ---------------------------------------------------------------- chart */

	/** Time window currently displayed by the chart, in milliseconds. */
	function viewWindow(charts) {
		if (state.zoom) { return { from: state.zoom.from, to: state.zoom.to }; }
		var now = Date.now();
		if (state.range === 0 && charts && charts.length) {
			var from = Infinity;
			var to = -Infinity;
			charts.forEach(function (chart) {
				var points = chart.points || [];
				if (points.length) {
					from = Math.min(from, points[0][0]);
					to = Math.max(to, points[points.length - 1][0]);
				}
			});
			if (isFinite(from) && isFinite(to)) {
				return { from: Math.min(from, to - MIN_WINDOW_MS), to: to };
			}
		}
		return { from: now - state.range * 1000, to: now };
	}

	function drawChart() {
		ensureChartHost();
		syncBlocks(groupCharts());
		renderChartMode();
		renderZoom();
		state.blocks.forEach(drawBlock);
		var total = 0;
		state.charts.forEach(function (chart) {
			if (chart.points) { total += chart.points.length; }
		});
		els.chartinfo.textContent = state.selected.length && total ? t("points", { n: total }) : "";
	}

	function drawBlock(block) {
		var canvas = block.canvas;
		var empty = block.empty;
		var title = block.title;
		renderLegend(block);

		var charts = block.charts.filter(function (chart) { return chart.points && chart.points.length; });
		if (!state.selected.length) {
			title.textContent = "\u2014";
			empty.textContent = t("chartEmpty");
			empty.hidden = false;
			block.view = null;
			clearCanvas(canvas);
			return;
		}
		title.textContent = block.charts.map(seriesLabel).join("  \u00b7  ");
		if (!charts.length) {
			empty.textContent = state.zoom ? t("noRange") : t("loading");
			empty.hidden = false;
			clearCanvas(canvas);
			return;
		}
		empty.hidden = true;

		var window_ = viewWindow(charts);
		var from = window_.from;
		var to = window_.to;
		if (to - from < MIN_WINDOW_MS) { to = from + MIN_WINDOW_MS; }

		var values = [];
		charts.forEach(function (chart) {
			chart.points.forEach(function (point) {
				if (point[0] >= from && point[0] <= to) { values.push(point[1]); }
			});
		});
		if (!values.length) {
			charts.forEach(function (chart) {
				chart.points.forEach(function (point) { values.push(point[1]); });
			});
		}
		var yMin = Math.min.apply(null, values);
		var yMax = Math.max.apply(null, values);
		if (charts.every(function (chart) { return chart.kind === "boolean"; })) {
			yMin = 0;
			yMax = 1;
		} else if (yMax - yMin < 0.5) {
			yMin -= 0.5;
			yMax += 0.5;
		} else {
			var pad = (yMax - yMin) * 0.08;
			yMin -= pad;
			yMax += pad;
		}

		var size = resize(canvas);
		var context = canvas.getContext("2d");
		var style = getComputedStyle(document.body);
		var ink = style.color;
		var line = style.getPropertyValue("--line").trim() || "#ddd";
		var muted = style.getPropertyValue("--muted").trim() || "#888";
		var accent = style.getPropertyValue("--accent").trim() || "#0b6bcb";

		var box = { left: 52, right: size.width - 12, top: 10, bottom: size.height - 26 };
		context.clearRect(0, 0, size.width, size.height);
		if (box.right - box.left < 40 || box.bottom - box.top < 40) { return; }
		context.font = "11px -apple-system, Segoe UI, Roboto, sans-serif";
		context.textBaseline = "middle";

		var ticks = niceTicks(yMin, yMax, 5);
		context.strokeStyle = line;
		context.fillStyle = muted;
		context.lineWidth = 1;
		ticks.forEach(function (value) {
			var y = box.bottom - (value - yMin) / (yMax - yMin) * (box.bottom - box.top);
			context.beginPath();
			context.moveTo(box.left, Math.round(y) + 0.5);
			context.lineTo(box.right, Math.round(y) + 0.5);
			context.stroke();
			context.textAlign = "right";
			context.fillText(formatTick(value), box.left - 6, y);
		});

		var steps = size.width < 520 ? 3 : 5;
		var timeFormat = timeFormatter(to - from);
		for (var step = 0; step <= steps; step++) {
			var moment = from + (to - from) * step / steps;
			var x = box.left + (box.right - box.left) * step / steps;
			context.fillStyle = muted;
			context.textAlign = step === 0 ? "left" : step === steps ? "right" : "center";
			context.fillText(timeFormat(moment), x, box.bottom + 13);
		}
		context.textAlign = "center";
		context.fillStyle = ink;

		charts.forEach(function (chart) {
			drawSeries(block, context, chart, box, from, to, yMin, yMax, colorOf(chart));
		});

		block.view = { box: box, from: from, to: to, yMin: yMin, yMax: yMax };

		if (block.hover) {
			var hoverX = box.left + (block.hover.ms - from) / (to - from) * (box.right - box.left);
			if (hoverX >= box.left && hoverX <= box.right) {
				context.save();
				context.strokeStyle = accent;
				context.globalAlpha = 0.55;
				context.lineWidth = 1;
				context.setLineDash([4, 3]);
				context.beginPath();
				context.moveTo(Math.round(hoverX) + 0.5, box.top);
				context.lineTo(Math.round(hoverX) + 0.5, box.bottom);
				context.stroke();
				context.restore();
			}
		}

		if (block.drag) {
			var left = Math.min(block.drag.x0, block.drag.x1);
			var right = Math.max(block.drag.x0, block.drag.x1);
			context.save();
			context.fillStyle = accent;
			context.globalAlpha = 0.12;
			context.fillRect(left, box.top, right - left, box.bottom - box.top);
			context.globalAlpha = 0.6;
			context.strokeStyle = accent;
			context.lineWidth = 1;
			context.strokeRect(left + 0.5, box.top + 0.5, right - left, box.bottom - box.top);
			context.restore();
		}

	}

	function drawSeries(block, context, chart, box, from, to, yMin, yMax, color) {
		var points = chart.points;
		if (!points.length) { return; }
		var scaleX = function (ms) { return box.left + (ms - from) / (to - from) * (box.right - box.left); };
		var scaleY = function (value) { return box.bottom - (value - yMin) / (yMax - yMin) * (box.bottom - box.top); };
		context.strokeStyle = color;
		context.lineWidth = 1.8;
		context.lineJoin = "round";
		context.lineCap = "round";
		context.beginPath();
		if (chart.kind === "boolean") {
			points.forEach(function (point, index) {
				var x = scaleX(point[0]);
				var y = scaleY(point[1]);
				if (index === 0) { context.moveTo(x, y); } else { context.lineTo(x, scaleY(points[index - 1][1])); context.lineTo(x, y); }
			});
		} else {
			points.forEach(function (point, index) {
				var x = scaleX(point[0]);
				var y = scaleY(point[1]);
				if (index === 0) { context.moveTo(x, y); } else { context.lineTo(x, y); }
			});
		}
		context.stroke();

		if (points.length === 1) {
			context.fillStyle = color;
			context.beginPath();
			context.arc(scaleX(points[0][0]), scaleY(points[0][1]), 2.5, 0, Math.PI * 2);
			context.fill();
		}

		// Hover: one marker per series, at the sample nearest to the pointer,
		// only when that sample is close enough to the cursor time.
		if (block.hover) {
			var point = nearest(points, block.hover.ms);
			var tolerance = Math.max((chart.bucket_ns || 6e10) / 1e6 / 2, 60000);
			if (point && Math.abs(point[0] - block.hover.ms) <= tolerance) {
				var markerX = scaleX(point[0]);
				var markerY = scaleY(point[1]);
				context.fillStyle = color;
				context.strokeStyle = getComputedStyle(document.body).getPropertyValue("--panel").trim() || "#fff";
				context.lineWidth = 2;
				context.beginPath();
				context.arc(markerX, markerY, 4, 0, Math.PI * 2);
				context.fill();
				context.stroke();
			}
		}
	}

	function nearest(points, ms) {
		var best = null;
		var distance = Infinity;
		points.forEach(function (point) {
			var delta = Math.abs(point[0] - ms);
			if (delta < distance) { distance = delta; best = point; }
		});
		return best;
	}

	function niceTicks(min, max, count) {
		var span = max - min;
		if (!(span > 0)) { return [min]; }
		var raw = span / count;
		var magnitude = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
		var residual = raw / magnitude;
		var step = magnitude * (residual >= 7.5 ? 10 : residual >= 3.5 ? 5 : residual >= 1.5 ? 2 : 1);
		var ticks = [];
		for (var value = Math.ceil(min / step) * step; value <= max + step * 0.001; value += step) {
			ticks.push(Math.round(value * 1e6) / 1e6);
		}
		return ticks;
	}

	function formatTick(value) {
		if (Math.abs(value) >= 1000) { return value.toFixed(0); }
		if (Math.abs(value) >= 10) { return value.toFixed(1).replace(/\.0$/, ""); }
		return value.toFixed(2).replace(/\.?0+$/, "");
	}

	function timeFormatter(span) {
		if (span <= 2 * 3600e3) {
			return function (ms) { var date = new Date(ms); return pad2(date.getHours()) + ":" + pad2(date.getMinutes()); };
		}
		if (span <= 3 * 86400e3) {
			return function (ms) {
				var date = new Date(ms);
				return pad2(date.getDate()) + "/" + pad2(date.getMonth() + 1) + " " + pad2(date.getHours()) + ":" + pad2(date.getMinutes());
			};
		}
		return function (ms) { var date = new Date(ms); return pad2(date.getDate()) + "/" + pad2(date.getMonth() + 1); };
	}

	function resize(canvas) {
		var ratio = window.devicePixelRatio || 1;
		var width = canvas.clientWidth || canvas.parentNode.clientWidth;
		var height = canvas.clientHeight || canvas.parentNode.clientHeight;
		if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
			canvas.width = Math.round(width * ratio);
			canvas.height = Math.round(height * ratio);
		}
		var context = canvas.getContext("2d");
		context.setTransform(ratio, 0, 0, ratio, 0, 0);
		return { width: width, height: height };
	}

	function clearCanvas(canvas) {
		var size = resize(canvas);
		var ratio = window.devicePixelRatio || 1;
		var context = canvas.getContext("2d");
		context.save();
		context.setTransform(1, 0, 0, 1, 0, 0);
		context.clearRect(0, 0, canvas.width, canvas.height);
		context.restore();
		context.setTransform(ratio, 0, 0, ratio, 0, 0);
		return size;
	}

	/* ------------------------------------------------------- pointer / zoom */

	function timeAt(block, clientX) {
		var view = block.view;
		if (!view) { return null; }
		var x = localX(block.canvas, clientX);
		if (x < view.box.left || x > view.box.right) { return null; }
		return view.from + (x - view.box.left) / (view.box.right - view.box.left) * (view.to - view.from);
	}

	function localX(canvas, clientX) {
		var rect = canvas.getBoundingClientRect();
		return clientX - rect.left;
	}

	function onMove(block, event) {
		if (block.pan) {
			var moved = localX(block.canvas, event.clientX) - block.pan.x;
			if (Math.abs(moved) > 2) { block.pan.moved = true; }
			var view = block.view;
			if (view) {
				var span = block.pan.to - block.pan.from;
				var shift = -moved * span / (view.box.right - view.box.left);
				var shifted = clampWindow(block.pan.from + shift, block.pan.to + shift);
				state.zoom = { from: shifted.from, to: shifted.to };
				els.tip.hidden = true;
				drawChart();
			}
			return;
		}
		if (block.drag) {
			block.drag.x1 = localX(block.canvas, event.clientX);
			els.tip.hidden = true;
			drawChart();
			return;
		}
		state.active = block;
		var ms = timeAt(block, event.clientX);
		if (ms === null) { hideTip(block); return; }
		showTip(block, ms, event.clientX, event.clientY);
	}

	function showTip(block, ms, clientX, clientY) {
		var changed = !block.hover || Math.abs(block.hover.ms - ms) > 1;
		block.hover = { ms: ms };
		if (changed) { drawChart(); }

		els.tip.textContent = "";
		var head = document.createElement("b");
		var date = new Date(ms);
		head.textContent = stamp(ms) + ":" + pad2(date.getSeconds());
		els.tip.appendChild(head);
		block.charts.forEach(function (chart) {
			if (!chart.points || !chart.points.length) { return; }
			var point = nearest(chart.points, ms);
			var tolerance = Math.max((chart.bucket_ns || 6e10) / 1e6, 60000);
			var row = document.createElement("div");
			row.className = "row";
			row.style.setProperty("--swatch", colorOf(chart));
			var dot = document.createElement("i");
			var label = document.createElement("span");
			label.textContent = chart.attribute;
			var value = document.createElement("em");
			if (point && Math.abs(point[0] - ms) <= tolerance) {
				value.textContent = chart.kind === "boolean"
					? (point[1] >= 0.5 ? t("on") : t("off"))
					: number(point[1], chart.unit) + (chart.unit ? " " + chart.unit : "");
			} else {
				value.textContent = "\u2014";
			}
			row.appendChild(dot);
			row.appendChild(label);
			row.appendChild(value);
			els.tip.appendChild(row);
		});
		els.tip.hidden = false;
		var tipWidth = els.tip.offsetWidth || 160;
		var left = clientX + 14;
		if (left + tipWidth > window.innerWidth - 8) { left = clientX - tipWidth - 14; }
		els.tip.style.left = Math.max(6, left) + "px";
		els.tip.style.top = Math.max(6, clientY - 12) + "px";
	}

	function hideTip(block) {
		if (block.hover) { block.hover = null; drawChart(); }
		els.tip.hidden = true;
	}

	function onDown(block, event) {
		if (!block.view || event.button !== 0) { return; }
		state.active = block;
		var x = localX(block.canvas, event.clientX);
		if (x < block.view.box.left || x > block.view.box.right) { return; }
		if (event.shiftKey) {
			block.pan = { x: x, from: block.view.from, to: block.view.to, moved: false };
			hideTip(block);
			block.canvas.style.cursor = "grabbing";
			return;
		}
		block.drag = { x0: x, x1: x };
		hideTip(block);
		block.canvas.style.cursor = "col-resize";
	}

	function onUp(block) {
		var pan = block.pan;
		block.pan = null;
		block.canvas.style.cursor = "crosshair";
		if (pan) {
			if (pan.moved) { loadCharts(); render(); } else { drawChart(); }
			return;
		}
		var drag = block.drag;
		block.drag = null;
		if (!drag) { return; }
		var view = block.view;
		if (!view) { drawChart(); return; }
		var width = Math.abs(drag.x1 - drag.x0);
		if (width < 8) { drawChart(); return; }
		var span = view.to - view.from;
		var ratioFrom = (drag.x0 - view.box.left) / (view.box.right - view.box.left);
		var ratioTo = (drag.x1 - view.box.left) / (view.box.right - view.box.left);
		var from = view.from + Math.min(ratioFrom, ratioTo) * span;
		var to = view.from + Math.max(ratioFrom, ratioTo) * span;
		applyZoom(block, from, to);
	}

	function applyZoom(block, from, to) {
		if (!(to - from >= MIN_WINDOW_MS)) { to = from + MIN_WINDOW_MS; }
		state.zoom = { from: Math.round(from), to: Math.round(to) };
		block.hover = null;
		writeStore();
		loadCharts();
		render();
	}

	/** Keep a window inside [0, now]. */
	function clampWindow(from, to) {
		var span = Math.max(to - from, MIN_WINDOW_MS);
		var now = Date.now();
		if (to > now) { to = now; from = to - span; }
		if (from < 0) { from = 0; to = span; }
		return { from: Math.round(from), to: Math.round(to) };
	}

	function panBy(block, fraction) {
		if (!block) { return; }
		var view = block.view;
		if (!view) { return; }
		var span = Math.max(view.to - view.from, MIN_WINDOW_MS);
		var shift = span * fraction;
		var clamped = clampWindow(view.from + shift, view.to + shift);
		applyZoom(block, clamped.from, clamped.to);
	}

	function onKey(event) {
		if (event.ctrlKey || event.metaKey || event.altKey) { return; }
		var target = event.target || {};
		var tag = String(target.tagName || "").toLowerCase();
		if (tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable) { return; }
		if (els.helpbox && els.helpbox.open) { return; }
		if (event.key === "?" || event.key === "h" || event.key === "H") {
			openHelp();
			event.preventDefault();
			return;
		}
		if (!state.selected.length) { return; }
		var handled = true;
		switch (event.key) {
		case "ArrowLeft": panBy(state.active, event.shiftKey ? -0.1 : -0.25); break;
		case "ArrowRight": panBy(state.active, event.shiftKey ? 0.1 : 0.25); break;
		case "+": case "=": zoomBy(state.active, 0.5); break;
		case "-": case "_": zoomBy(state.active, 2); break;
		case "0": case "Home": case "r": case "R": resetZoom(); break;
		case "f": case "F": toggleFullscreen(); break;
		case "m": case "M": toggleAppFullscreen(); break;
		default: handled = false;
		}
		if (handled) { event.preventDefault(); }
	}

	function zoomBy(block, factor) {
		if (!block) { return; }
		var view = block.view;
		var current = state.zoom || (view ? { from: view.from, to: view.to } : null);
		if (!current) { return; }
		var center = (current.from + current.to) / 2;
		var half = Math.max((current.to - current.from) / 2 * factor, MIN_WINDOW_MS / 2);
		var from = center - half;
		var to = center + half;
		var now = Date.now();
		if (to > now) {
			to = now;
			from = Math.max(0, to - half * 2);
		}
		applyZoom(block, from, to);
	}

	function resetZoom() {
		state.zoom = null;
		state.blocks.forEach(function (item) { item.hover = null; });
		writeStore();
		loadCharts();
		render();
	}

	function toggleFullscreen() {
		if (document.fullscreenElement === els.panel) {
			document.exitFullscreen().catch(function () {});
			return;
		}
		var request = els.panel.requestFullscreen || els.panel.webkitRequestFullscreen;
		if (request) {
			var result = request.call(els.panel);
			if (result && result.catch) { result.catch(function () {}); }
		}
	}

	/* ----------------------------------------------------------------- data */

	function loadCatalog(silent) {
		if (!silent && !state.catalog) { render(); }
		return request("action=info").then(function (info) {
			return request("action=catalog").then(function (catalog) {
				catalog.samples = info.samples;
				catalog.size = info.size_bytes;
				catalog.wal = info.wal_bytes;
				catalog.schema = info.schema;
				state.catalog = catalog;
				state.error = "";
				var known = {};
				(catalog.devices || []).forEach(function (device) {
					(device.series || []).forEach(function (series) { known[keyOf(device.mac, series)] = true; });
				});
				state.selected = state.selected.filter(function (key) { return known[key]; });
				render();
				if (state.selected.length) { loadCharts(); }
			});
		}).catch(function (error) {
			state.error = error.message || String(error);
			render();
		});
	}

	function loadCharts() {
		var keys = state.selected.slice();
		state.charts = state.charts.filter(function (chart) { return keys.indexOf(chart.key) >= 0; });
		if (!keys.length) { state.charts = []; drawChart(); return Promise.resolve(); }
		var jobs = keys.map(function (key) {
			var parts = key.split("|");
			var device = findDevice(parts[0]);
			var series = null;
			if (device) {
				(device.series || []).forEach(function (item) {
					if (item.attribute === parts[1] && item.unit === parts[2]) { series = item; }
				});
			}
			var kind = series ? series.kind : "numeric";
			var query = "action=series&mac=" + encodeURIComponent(parts[0]) +
				"&attribute=" + encodeURIComponent(parts[1]) +
				"&unit=" + encodeURIComponent(parts[2]) +
				"&kind=" + encodeURIComponent(kind) +
				"&range=" + state.range;
			if (state.zoom) {
				query += "&from=" + Math.round(state.zoom.from * 1e6) + "&to=" + Math.round(state.zoom.to * 1e6);
			}
			return request(query).then(function (data) {
				return {
					key: key,
					mac: parts[0],
					attribute: parts[1],
					unit: parts[2],
					kind: data.kind,
					bucket_ns: data.bucket_ns,
					points: data.points || []
				};
			}).catch(function () {
				return { key: key, mac: parts[0], attribute: parts[1], unit: parts[2], kind: kind, points: [] };
			});
		});
		return Promise.all(jobs).then(function (charts) {
			state.charts = charts;
			drawChart();
		});
	}

	/* --------------------------------------------------------------- web app
	 * The portal is installable: the CGI also serves a manifest
	 * (?action=manifest) and a service worker (?action=sw) that caches this page
	 * and the last JSON answers, so a home-screen icon opens it without the
	 * browser chrome and the values stay readable when the router is offline.
	 * Browsers only allow this in a secure context (https or localhost), so the
	 * registration is skipped over plain http and the icon button explains the
	 * manual "Add to Home screen" instead. */
	var installEvent = null;

	function pwaStandalone() {
		if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) { return true; }
		return window.navigator.standalone === true;
	}

	function pwaIos() {
		return /iPad|iPhone|iPod/.test(window.navigator.userAgent || "") ||
			(window.navigator.platform === "MacIntel" && window.navigator.maxTouchPoints > 1);
	}

	function showInstall(visible) {
		if (!els.install) { return; }
		els.install.hidden = !visible;
		els.install.title = t("install");
		els.install.setAttribute("aria-label", t("install"));
	}

	function openPwaHelp() {
		if (!els.pwahelp) { return; }
		els.pwahelptitle.textContent = t("pwaTitle");
		var body = pwaStandalone() ? t("pwaBodyInstalled") : (pwaIos() ? t("pwaBodyIos") : t("pwaBodyChrome"));
		els.pwahelpbody.innerHTML = body;
		els.pwahelpclose.textContent = t("helpClose");
		if (typeof els.pwahelp.showModal === "function") {
			els.pwahelp.showModal();
		} else {
			els.pwahelp.setAttribute("open", "");
		}
	}

	function updateNet() {
		var offline = window.navigator.onLine === false;
		if (els.netstate) {
			els.netstate.hidden = !offline;
			els.netstate.textContent = t("offlineBanner");
		}
	}

	/* Page-level fullscreen: an installed web app launches without browser
	 * chrome (manifest "display": "fullscreen"); this button and the M key do
	 * the same in a normal tab and hide the system status bar too, so the
	 * dashboard fills the screen like a native app. The chart keeps its own
	 * fullscreen button (F). */
	function appFullscreenApi() {
		var root = document.documentElement;
		if (root.requestFullscreen) {
			return { enter: "requestFullscreen", exit: "exitFullscreen", element: "fullscreenElement" };
		}
		if (root.webkitRequestFullscreen) {
			return { enter: "webkitRequestFullscreen", exit: "webkitExitFullscreen", element: "webkitFullscreenElement" };
		}
		return null;
	}

	function appFullscreenOn() {
		return !!(document.fullscreenElement || document.webkitFullscreenElement);
	}

	function toggleAppFullscreen() {
		var api = appFullscreenApi();
		if (!api) { return; }
		if (appFullscreenOn()) {
			var exit = document.exitFullscreen || document.webkitExitFullscreen;
			if (exit) {
				var leaving = exit.call(document);
				if (leaving && leaving.catch) { leaving.catch(function () { }); }
			}
			return;
		}
		var entered = document.documentElement[api.enter]({ navigationUI: "hide" });
		if (entered && entered.catch) { entered.catch(function () { }); }
	}

	function syncMaximize() {
		if (!els.maximize) { return; }
		var on = appFullscreenOn();
		if (on) { els.maximize.classList.add("on"); } else { els.maximize.classList.remove("on"); }
		els.maximize.title = on ? t("maximizeOff") : t("maximize");
		els.maximize.setAttribute("aria-label", els.maximize.title);
		els.maximize.setAttribute("aria-pressed", on ? "true" : "false");
	}

	function registerServiceWorker() {
		if (!("serviceWorker" in window.navigator)) { return; }
		/* Without a secure context the browser rejects every registration; the
		 * manifest stays valid, so the manual "Add to Home screen" still works. */
		if (!window.isSecureContext) { return; }
		window.navigator.serviceWorker.register("?action=sw", { scope: "/" })
			.then(function (registration) {
				/* A new asset version waits instead of taking over mid-load.
				 * Activate it now that the page is idle, so the next reload
				 * already uses the fresh CSS and JavaScript. */
				var promote = function (worker) {
					if (worker) { worker.postMessage("skip-waiting"); }
				};
				promote(registration.waiting);
				registration.addEventListener("updatefound", function () {
					var installing = registration.installing;
					if (!installing) { return; }
					installing.addEventListener("statechange", function () {
						if (installing.state === "installed" && registration.waiting) { promote(installing); }
					});
				});
			})
			.catch(function (error) {
				if (window.console && console.warn) { console.warn("service worker not registered:", error); }
			});
	}

	function setupPwa() {
		if (els.manifest) { els.manifest.href = "?action=manifest&lang=" + lang; }
		if (pwaStandalone()) { document.documentElement.classList.add("pwa-standalone"); }
		showInstall(false);
		if (els.install) {
			els.install.addEventListener("click", function () {
				if (installEvent) {
					var prompt = installEvent;
					installEvent = null;
					prompt.prompt();
					if (prompt.userChoice && prompt.userChoice.then) {
						prompt.userChoice.then(function (choice) {
							if (choice && choice.outcome === "accepted") { showInstall(false); }
						});
					}
					return;
				}
				openPwaHelp();
			});
		}
		window.addEventListener("beforeinstallprompt", function (event) {
			event.preventDefault();
			installEvent = event;
			showInstall(true);
		});
		window.addEventListener("appinstalled", function () {
			installEvent = null;
			showInstall(false);
		});
		/* Safari never fires beforeinstallprompt: offer the Share menu instead. */
		if (pwaIos() && !pwaStandalone()) { showInstall(true); }
		if (els.maximize) {
			els.maximize.hidden = !appFullscreenApi();
			els.maximize.addEventListener("click", toggleAppFullscreen);
			syncMaximize();
		}
		window.addEventListener("online", updateNet);
		window.addEventListener("offline", updateNet);
		updateNet();
		registerServiceWorker();
	}

	/* ----------------------------------------------------------------- init */

	function start() {
		els = {
			kpis: document.getElementById("kpis"),
			devices: document.getElementById("devices"),
			ranges: document.getElementById("ranges"),
			canvas: document.getElementById("canvas"),
			chartempty: document.getElementById("chartempty"),
			charttitle: document.getElementById("charttitle"),
			chartinfo: document.getElementById("chartinfo"),
			legend: document.getElementById("legend"),
			stamp: document.getElementById("stamp"),
			tip: document.getElementById("tip"),
			panel: document.querySelector(".pchart"),
			panleft: document.getElementById("panleft"),
			panright: document.getElementById("panright"),
			zoomin: document.getElementById("zoomin"),
			zoomout: document.getElementById("zoomout"),
			zoomreset: document.getElementById("zoomreset"),
			zoominfo: document.getElementById("zoominfo"),
			fullscreen: document.getElementById("fullscreen"),
			help: document.getElementById("help"),
			resetview: document.getElementById("resetview"),
			install: document.getElementById("install"),
			maximize: document.getElementById("maximize"),
			manifest: document.getElementById("manifest"),
			netstate: document.getElementById("netstate"),
			pwahelp: document.getElementById("pwahelp"),
			pwahelptitle: document.getElementById("pwahelptitle"),
			pwahelpbody: document.getElementById("pwahelpbody"),
			pwahelpclose: document.getElementById("pwahelpclose"),
			helplink: document.getElementById("helplink"),
			helpbox: document.getElementById("helpbox"),
			helptitle: document.getElementById("helptitle"),
			helpbody: document.getElementById("helpbody"),
			helpnote: document.getElementById("helpnote"),
			helpclose: document.getElementById("helpclose")
		};
		pickLanguage();
		document.documentElement.lang = lang;
		setupPwa();
		restoreStore();
		ensureSplitter();
		ensureChartHost();
		state.chartMode = chartModeRead();
		if (els.resetview) {
			els.resetview.title = t("resetView");
			els.resetview.addEventListener("click", resetView);
		}
		document.getElementById("reload").addEventListener("click", function () { loadCatalog(true); });
		/* Pointer events live on each chart panel, see createBlock(). */
		window.addEventListener("mouseup", function () {
			for (var index = 0; index < state.blocks.length; index++) {
				var block = state.blocks[index];
				if (block.drag || block.pan) { onUp(block); return; }
			}
		});
		els.panleft.addEventListener("click", function () { panBy(state.active, -0.25); });
		els.panright.addEventListener("click", function () { panBy(state.active, 0.25); });
		els.zoomin.addEventListener("click", function () { zoomBy(state.active, 0.5); });
		els.zoomout.addEventListener("click", function () { zoomBy(state.active, 2); });
		els.zoomreset.addEventListener("click", resetZoom);
		els.fullscreen.addEventListener("click", toggleFullscreen);
		els.help.addEventListener("click", openHelp);
		els.helplink.addEventListener("click", openHelp);
		document.addEventListener("fullscreenchange", function () { syncMaximize(); renderZoom(); drawChart(); });
		document.addEventListener("webkitfullscreenchange", function () { syncMaximize(); });
		window.addEventListener("resize", function () { drawChart(); });
		document.addEventListener("keydown", onKey);
		loadCatalog(false);
		window.setInterval(function () { loadCatalog(true); }, REFRESH_MS);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start);
	} else {
		start();
	}
})();
