/* ble2uart_gateway sensor portal ------------------------------------------
 * Dependency-free dashboard: it reads /cgi-bin/extra/ble2uart_gateway/portal
 * (JSON produced by `ble2uart-gateway --portal`) and draws the charts on a
 * plain canvas, so the page also works on a router without Internet access.
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
	var COLORS = ["#0b6bcb", "#1a7f37", "#b45309", "#8250df", "#b42318", "#0e7490", "#6b7280", "#a16207"];

	var TEXT = {
		it: {
			subtitle: "Sensori", refresh: "Aggiorna ora", config: "Configurazione",
			devices: "Dispositivi", series: "Grandezze", samples: "Campioni", updated: "Ultimo dato",
			never: "nessun dato", chartHint: "Tocca una grandezza per disegnarne il grafico.",
			chartEmpty: "Seleziona una grandezza dall'elenco.",
			chartLimit: "Massimo {n} grandezze per grafico.",
			loading: "Caricamento\u2026", failed: "Errore: {error}", noDevices: "Nessun sensore nel database.",
			on: "attivo", off: "inattivo", true_: "s\u00ec", false_: "no", now: "ora",
			sec: "s", min: "min", hour: "h", day: "g",
			range1h: "1 h", range6h: "6 h", range24h: "24 h", range7d: "7 g", range30d: "30 g", rangeAll: "tutto",
			points: "{n} punti", loginExpired: "Sessione scaduta: ricaricare la pagina e accedere.",
			emptyDatabase: "Il database non contiene ancora misure."
		},
		en: {
			subtitle: "Sensors", refresh: "Refresh now", config: "Configuration",
			devices: "Devices", series: "Attributes", samples: "Samples", updated: "Latest sample",
			never: "no data", chartHint: "Tap an attribute to draw its chart.",
			chartEmpty: "Select an attribute from the list.",
			chartLimit: "At most {n} attributes per chart.",
			loading: "Loading\u2026", failed: "Error: {error}", noDevices: "No sensors in the database.",
			on: "on", off: "off", true_: "yes", false_: "no", now: "now",
			sec: "s", min: "min", hour: "h", day: "d",
			range1h: "1 h", range6h: "6 h", range24h: "24 h", range7d: "7 d", range30d: "30 d", rangeAll: "all",
			points: "{n} points", loginExpired: "Session expired: reload the page and sign in.",
			emptyDatabase: "The database does not contain measurements yet."
		},
		de: {
			subtitle: "Sensoren", refresh: "Jetzt aktualisieren", config: "Konfiguration",
			devices: "Ger\u00e4te", series: "Messwerte", samples: "Messwerte", updated: "Letzter Wert",
			never: "keine Daten", chartHint: "Messwert antippen, um das Diagramm zu zeichnen.",
			chartEmpty: "Messwert aus der Liste w\u00e4hlen.",
			chartLimit: "H\u00f6chstens {n} Messwerte pro Diagramm.",
			loading: "Lade\u2026", failed: "Fehler: {error}", noDevices: "Keine Sensoren in der Datenbank.",
			on: "aktiv", off: "inaktiv", true_: "ja", false_: "nein", now: "jetzt",
			sec: "s", min: "min", hour: "h", day: "T",
			range1h: "1 h", range6h: "6 h", range24h: "24 h", range7d: "7 T", range30d: "30 T", rangeAll: "alles",
			points: "{n} Punkte", loginExpired: "Sitzung abgelaufen: Seite neu laden und anmelden.",
			emptyDatabase: "Die Datenbank enth\u00e4lt noch keine Messwerte."
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
	var state = {
		catalog: null,
		selected: [],
		range: 86400,
		charts: [],
		busy: false,
		error: "",
		hover: null
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
						throw new Error(data.error || "unknown error");
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

	function bytes(value) {
		var units = ["B", "KiB", "MiB", "GiB", "TiB"];
		var index = 0;
		while (value >= 1024 && index < units.length - 1) { value /= 1024; index++; }
		return (index === 0 ? value : value.toFixed(1)) + " " + units[index];
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
		}
		if (series.kind === "boolean") {
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
		var stamp = document.createElement("span");
		stamp.className = "t";
		stamp.textContent = age(series.last_ns, now);
		button.appendChild(attribute);
		button.appendChild(value);
		button.appendChild(stamp);
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
			if (state.selected.length >= MAX_SERIES) {
				state.error = t("chartLimit", { n: MAX_SERIES });
				render();
				return;
			}
			state.selected.push(key);
		}
		state.error = "";
		loadCharts();
		render();
	}

	function renderRanges() {
		els.ranges.textContent = "";
		RANGES.forEach(function (item) {
			var button = document.createElement("button");
			button.type = "button";
			button.textContent = t(item.label);
			button.setAttribute("aria-pressed", state.range === item.seconds ? "true" : "false");
			button.addEventListener("click", function () {
				state.range = item.seconds;
				loadCharts();
				render();
			});
			els.ranges.appendChild(button);
		});
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

	function renderLegend() {
		els.legend.textContent = "";
		state.charts.forEach(function (chart, index) {
			var chip = document.createElement("button");
			chip.type = "button";
			chip.className = "chip";
			chip.style.setProperty("--swatch", COLORS[index % COLORS.length]);
			var dot = document.createElement("i");
			var text = document.createElement("span");
			text.textContent = seriesLabel(chart);
			chip.appendChild(dot);
			chip.appendChild(text);
			chip.title = t("chartHint");
			chip.addEventListener("click", function () {
				state.selected = state.selected.filter(function (key) { return key !== chart.key; });
				state.charts = state.charts.filter(function (item) { return item.key !== chart.key; });
				render();
			});
			els.legend.appendChild(chip);
		});
	}

	/* ---------------------------------------------------------------- chart */

	function drawChart() {
		var canvas = els.canvas;
		var empty = els.chartempty;
		var title = els.charttitle;
		renderLegend();

		var charts = state.charts.filter(function (chart) { return chart.points && chart.points.length; });
		if (!state.selected.length) {
			title.textContent = "\u2014";
			empty.textContent = t("chartEmpty");
			empty.hidden = false;
			els.chartinfo.textContent = "";
			clearCanvas(canvas);
			return;
		}
		title.textContent = state.charts.map(seriesLabel).join("  \u00b7  ");
		if (!charts.length) {
			empty.textContent = t("loading");
			empty.hidden = false;
			clearCanvas(canvas);
			return;
		}
		empty.hidden = true;

		var now = Date.now();
		var to = state.range === 0
			? Math.max.apply(null, charts.map(function (chart) { return chart.points[chart.points.length - 1][0]; }))
			: now;
		var from = state.range === 0
			? Math.min.apply(null, charts.map(function (chart) { return chart.points[0][0]; }))
			: now - state.range * 1000;
		if (to - from < 60000) { to = from + 60000; }

		var values = [];
		charts.forEach(function (chart) {
			chart.points.forEach(function (point) { values.push(point[1]); });
		});
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
			var index = state.charts.indexOf(chart);
			drawSeries(context, chart, box, from, to, yMin, yMax, COLORS[index % COLORS.length]);
		});

		els.chartinfo.textContent = t("points", { n: charts.reduce(function (sum, chart) { return sum + chart.points.length; }, 0) });
		state.view = { box: box, from: from, to: to, yMin: yMin, yMax: yMax };
	}

	function drawSeries(context, chart, box, from, to, yMin, yMax, color) {
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

		var hover = state.hover;
		if (hover && hover.key === chart.key) {
			var point = nearest(points, hover.ms);
			if (point) {
				context.fillStyle = color;
				context.beginPath();
				context.arc(scaleX(point[0]), scaleY(point[1]), 3.5, 0, Math.PI * 2);
				context.fill();
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

	function pad2(value) { return value < 10 ? "0" + value : String(value); }

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
		canvas.getContext("2d").clearRect(0, 0, size.width, size.height);
	}

	/* ---------------------------------------------------------------- hover */

	function onMove(event) {
		var view = state.view;
		if (!view) { return; }
		var canvas = els.canvas;
		var rect = canvas.getBoundingClientRect();
		var x = event.clientX - rect.left;
		if (x < view.box.left || x > view.box.right) { hideTip(); return; }
		var ms = view.from + (x - view.box.left) / (view.box.right - view.box.left) * (view.to - view.from);
		var nearestChart = null;
		var nearestDistance = Infinity;
		state.charts.forEach(function (chart) {
			if (!chart.points || !chart.points.length) { return; }
			var point = nearest(chart.points, ms);
			var distance = Math.abs(point[0] - ms);
			if (distance < nearestDistance) { nearestDistance = distance; nearestChart = chart; }
		});
		if (!nearestChart) { hideTip(); return; }
		var chosen = nearest(nearestChart.points, ms);
		state.hover = { key: nearestChart.key, ms: chosen[0] };
		drawChart();

		els.tip.textContent = "";
		var head = document.createElement("b");
		var when = new Date(chosen[0]);
		head.textContent = pad2(when.getDate()) + "/" + pad2(when.getMonth() + 1) + " " +
			pad2(when.getHours()) + ":" + pad2(when.getMinutes()) + ":" + pad2(when.getSeconds());
		els.tip.appendChild(head);
		state.charts.forEach(function (chart, index) {
			if (!chart.points || !chart.points.length) { return; }
			var point = nearest(chart.points, chosen[0]);
			var row = document.createElement("div");
			row.className = "row";
			row.style.setProperty("--swatch", COLORS[index % COLORS.length]);
			var dot = document.createElement("i");
			var label = document.createElement("span");
			label.textContent = chart.attribute;
			var value = document.createElement("em");
			value.textContent = chart.kind === "boolean"
				? (point[1] >= 0.5 ? t("on") : t("off"))
				: number(point[1], chart.unit) + (chart.unit ? " " + chart.unit : "");
			row.appendChild(dot);
			row.appendChild(label);
			row.appendChild(value);
			els.tip.appendChild(row);
		});
		els.tip.hidden = false;
		var tipWidth = els.tip.offsetWidth || 160;
		var left = event.clientX + 14;
		if (left + tipWidth > window.innerWidth - 8) { left = event.clientX - tipWidth - 14; }
		els.tip.style.left = Math.max(6, left) + "px";
		els.tip.style.top = Math.max(6, event.clientY - 12) + "px";
	}

	function hideTip() {
		if (state.hover) { state.hover = null; drawChart(); }
		els.tip.hidden = true;
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
			return request(query).then(function (data) {
				return {
					key: key,
					mac: parts[0],
					attribute: parts[1],
					unit: parts[2],
					kind: data.kind,
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
			tip: document.getElementById("tip")
		};
		pickLanguage();
		document.documentElement.lang = lang;
		document.getElementById("reload").addEventListener("click", function () { loadCatalog(true); });
		els.canvas.addEventListener("mousemove", onMove);
		els.canvas.addEventListener("mouseleave", hideTip);
		els.canvas.addEventListener("touchstart", function (event) {
			if (event.touches.length) { onMove(event.touches[0]); }
		}, { passive: true });
		window.addEventListener("resize", function () { drawChart(); });
		loadCatalog(false);
		window.setInterval(function () { loadCatalog(true); }, REFRESH_MS);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start);
	} else {
		start();
	}
})();
