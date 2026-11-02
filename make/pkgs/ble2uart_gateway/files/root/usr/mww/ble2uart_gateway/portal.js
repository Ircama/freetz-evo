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
	/* The freetz proxy exposes the portal as
	 *   /cgi-bin/freetz_proxy?service=freetz&path=/cgi-bin/extra/ble2uart_gateway/portal
	 * and forwards every other query parameter upstream. Inside that context the
	 * API calls have to go back through the proxy, otherwise they hit the FRITZ!
	 * web server on that path, which answers with its login page ("sessione
	 * scaduta"). */
	var PROXY = (function () {
		try {
			var params = new URLSearchParams(window.location.search || "");
			var service = params.get("service") || "";
			var path = params.get("path") || "";
			if (service && path.indexOf("ble2uart_gateway") >= 0) {
				return { service: service, path: path };
			}
		} catch (e) { /* no URLSearchParams: older browser, direct access */ }
		return null;
	})();

	function endpointUrl(path, query) {
		if (PROXY) {
			var base = window.location.pathname +
				"?service=" + encodeURIComponent(PROXY.service) +
				"&path=" + encodeURIComponent(PROXY.path);
			return query ? base + "&" + query : base;
		}
		return query ? path + "?" + query : path;
	}

	var REFRESH_MS = 30000;
	var MAX_SERIES = 6;
	var MAX_SELECTED = 18;
	var MIN_WINDOW_MS = 60000;
	/* Series colours: hues 137.5° apart (the golden angle), so any number of
	 * lines stays distinct - a fixed list put blue next to teal and amber next
	 * to brown, which looked like the same colour on a small screen. */
	var HUE_STEP = 137.508;
	function colorAt(index) {
		var dark = document.documentElement.getAttribute("data-theme") === "dark";
		var hue = Math.round(((index < 0 ? 0 : index) * HUE_STEP) % 360);
		return "hsl(" + hue + (dark ? " 72% 66%" : " 70% 40%") + ")";
	}

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
			options: "Opzioni del grafico",
			optGroup: "Suddivisione",
			optGroupUnit: "Un grafico per unit\u00e0 di misura",
			optGroupFamily: "Un grafico per grandezza",
			optGroupSingle: "Un solo grafico",
			optGroupHint: "Per grandezza raggruppa nomi equivalenti come temperature, temp e theengs_temperature.",
			optUnits: "Unit\u00e0 di misura",
			optUnitsNative: "Come memorizzate",
			optUnitsMetric: "Metriche (\u00b0C, mm, kg\u2026)",
			optUnitsImperial: "Imperiali (\u00b0F, in, lb\u2026)",
			optPoints: "Mostra i punti",
			optPointsHint: "Un puntino per ogni campione del grafico",
			moveUp: "Sposta su", moveDown: "Sposta gi\u00f9",
			prefsTitle: "Preferenze",
			prefTitle: "Titolo",
			prefTheme: "Tema", themeSystem: "Tema di sistema", themeLight: "Tema chiaro", themeDark: "Tema scuro",
			prefSubtitle: "Sottotitolo",
			prefHint: "Vuoto = valore predefinito. Le preferenze restano in questo browser.",
			prefFullscreen: "Avvia a schermo intero",
			prefFullscreenHint: "L'app installata si apre senza barra del browser (manifest display: standalone). Lo schermo intero vero e proprio si aggiunge col pulsante \u2b1c o col tasto M; in una scheda serve un gesto: si attiva al primo tocco sulla pagina.",
			prefUiLock: "Blocca le modifiche alla UX",
			prefUiLockHint: "Nasconde le croci dei widget, le frecce di riordino dei grafici, la selezione delle grandezze, il pulsante che ripristina le viste e le opzioni del grafico. Le preferenze tornano modificabili togliendo questa spunta. Con il blocco attivo, toccando un valore il grafico scorre fino alla sua curva e la illumina.",
			prefSplitLock: "Blocca la larghezza delle colonne",
			prefSplitLockHint: "Il separatore fra valori e grafico non si trascina pi\u00f9 (e le frecce non lo spostano): la suddivisione resta quella scelta, anche su un tablet.",
			tapToChart: "Tocca per vedere la curva nel grafico",
			notCharted: "Questa grandezza non \u00e8 nel grafico: sblocca le modifiche alla UX per aggiungerla.",
			prefConfig: "Mostra il collegamento alla configurazione",
			prefMaximize: "Mostra il pulsante di massimizzazione",
			prefResetHidden: "Mostra di nuovo riquadri e grafici nascosti",
			prefHidden: "Nascosti: {n} riquadri, {m} grafici, {k} sensori",
			hideBox: "Nascondi questo riquadro",
			hidePanel: "Nascondi questo grafico",
			showHidden: "mostra {n} nascosti",
			showHiddenDevices: "mostra {n} sensori nascosti",
			hideDevice: "Nascondi questo sensore",
			prefKpis: "Indicatori",
			prefShowKpis: "Mostra la sezione degli indicatori",
			prefSensors: "Sensori",
			prefBoxes: "Riquadri dei valori",
			prefNoItems: "Nessun elemento da elencare.",
			hideKpi: "Nascondi questo indicatore",
			optPanels: "Grafici visibili",
			optNoPanels: "Nessun grafico: seleziona prima una grandezza.",
			family_temperature: "Temperatura", family_humidity: "Umidit\u00e0",
			family_absolute_humidity: "Umidit\u00e0 assoluta", family_pressure: "Pressione",
			family_illuminance: "Illuminamento", family_voltage: "Tensione",
			family_battery: "Batteria", family_conductivity: "Conducibilit\u00e0",
			family_co2: "CO\u2082", family_particulates: "Particolato",
			family_weight: "Peso", family_speed: "Velocit\u00e0", family_distance: "Distanza",
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
			pwaBodyChrome: "Il browser non ha offerto l'installazione. Su http://fritz.box manca il contesto sicuro richiesto (https oppure localhost): senza di esso non c'\u00e8 service worker, non compare l'icona + di Samsung Internet n\u00e9 il pulsante Installa, e \u201cAggiungi a schermata Home\u201d crea solo un segnalibro che si apre con la barra dell'URL. Per un'app vera apri il portale in https, oppure in localhost con un tunnel SSH (ssh -L 8181:localhost:81 root@fritz.box).",
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
			options: "Chart options",
			optGroup: "Grouping",
			optGroupUnit: "One chart per unit",
			optGroupFamily: "One chart per quantity",
			optGroupSingle: "Single chart",
			optGroupHint: "Per quantity folds equivalent names such as temperature, temp and theengs_temperature.",
			optUnits: "Unit system",
			optUnitsNative: "As stored",
			optUnitsMetric: "Metric (\u00b0C, mm, kg\u2026)",
			optUnitsImperial: "Imperial (\u00b0F, in, lb\u2026)",
			optPoints: "Show the points",
			optPointsHint: "A small dot for every sample of the chart",
			moveUp: "Move up", moveDown: "Move down",
			prefsTitle: "Preferences",
			prefTitle: "Title",
			prefTheme: "Theme", themeSystem: "System theme", themeLight: "Light theme", themeDark: "Dark theme",
			prefSubtitle: "Subtitle",
			prefHint: "Empty = default value. The preferences stay in this browser.",
			prefFullscreen: "Start in fullscreen",
			prefFullscreenHint: "The installed app opens without the browser chrome (manifest display: standalone). True fullscreen is added with the \u2b1c button or the M key; in a browser tab it needs a gesture: it starts on the first tap on the page.",
			prefUiLock: "Lock the UI changes",
			prefUiLockHint: "Hides the crosses of the widgets, the chart reorder arrows, the series selection, the button that resets the saved views and the chart options. Clear this box to edit the preferences again. While locked, tapping a value scrolls to its curve and highlights it.",
			prefSplitLock: "Lock the column width",
			prefSplitLockHint: "The separator between the values and the chart cannot be dragged any more (and the arrow keys do not move it): the split stays as chosen, also on a tablet.",
			tapToChart: "Tap to find its curve in the chart",
			notCharted: "This value is not in the chart: clear the UI lock to add it.",
			prefConfig: "Show the link to the configuration",
			prefMaximize: "Show the maximize button",
			prefResetHidden: "Show the hidden boxes and charts again",
			prefHidden: "Hidden: {n} boxes, {m} charts, {k} sensors",
			hideBox: "Hide this box",
			hidePanel: "Hide this chart",
			showHidden: "show {n} hidden",
			showHiddenDevices: "show {n} hidden sensors",
			hideDevice: "Hide this sensor",
			prefKpis: "Indicators",
			prefShowKpis: "Show the indicator section",
			prefSensors: "Sensors",
			prefBoxes: "Value boxes",
			prefNoItems: "Nothing to list here.",
			hideKpi: "Hide this indicator",
			optPanels: "Visible charts",
			optNoPanels: "No charts: select a quantity first.",
			family_temperature: "Temperature", family_humidity: "Humidity",
			family_absolute_humidity: "Absolute humidity", family_pressure: "Pressure",
			family_illuminance: "Illuminance", family_voltage: "Voltage",
			family_battery: "Battery", family_conductivity: "Conductivity",
			family_co2: "CO\u2082", family_particulates: "Particulates",
			family_weight: "Weight", family_speed: "Speed", family_distance: "Distance",
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
			pwaBodyChrome: "The browser has not offered the installation. http://fritz.box is not a secure context (https or localhost), so there is no service worker, no + icon in Samsung Internet and no install button - \u201cAdd to Home screen\u201d only stores a bookmark that opens with the URL bar. For a real app open the portal over https, or over localhost through an SSH tunnel (ssh -L 8181:localhost:81 root@fritz.box).",
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
			options: "Diagrammoptionen",
			optGroup: "Aufteilung",
			optGroupUnit: "Ein Diagramm pro Einheit",
			optGroupFamily: "Ein Diagramm pro Messgr\u00f6\u00dfe",
			optGroupSingle: "Ein einziges Diagramm",
			optGroupHint: "Pro Messgr\u00f6\u00dfe werden gleichwertige Namen wie temperature, temp und theengs_temperature zusammengefasst.",
			optUnits: "Einheitensystem",
			optUnitsNative: "Wie gespeichert",
			optUnitsMetric: "Metrisch (\u00b0C, mm, kg\u2026)",
			optUnitsImperial: "Imperial (\u00b0F, in, lb\u2026)",
			optPoints: "Punkte anzeigen",
			optPointsHint: "Ein kleiner Punkt pro Messwert im Diagramm",
			moveUp: "Nach oben", moveDown: "Nach unten",
			prefsTitle: "Einstellungen",
			prefTitle: "Titel",
			prefTheme: "Design", themeSystem: "Systemdesign", themeLight: "Helles Design", themeDark: "Dunkles Design",
			prefSubtitle: "Untertitel",
			prefHint: "Leer = Standardwert. Die Einstellungen bleiben in diesem Browser.",
			prefFullscreen: "Im Vollbild starten",
			prefFullscreenHint: "Die installierte App \u00f6ffnet ohne Browserleiste (Manifest display: standalone). Das echte Vollbild kommt mit der \u2b1c-Taste oder der Taste M; im Browser-Tab braucht es eine Geste: es startet beim ersten Tippen.",
			prefUiLock: "UX-\u00c4nderungen sperren",
			prefUiLockHint: "Blendet die Kreuze der Widgets, die Pfeile zum Umsortieren der Diagramme, die Auswahl der Messgr\u00f6\u00dfen, die R\u00fccksetzung der gespeicherten Ansichten und die Diagrammoptionen aus. Zum Bearbeiten der Einstellungen das H\u00e4kchen wieder entfernen. Bei gesperrter Oberfl\u00e4che springt ein Tippen auf einen Wert zur Kurve und hebt sie hervor.",
			prefSplitLock: "Spaltenbreite sperren",
			prefSplitLockHint: "Der Trenner zwischen Werten und Diagramm l\u00e4sst sich nicht mehr ziehen (auch nicht mit den Pfeiltasten): die Aufteilung bleibt wie gew\u00e4hlt, auch auf einem Tablet.",
			tapToChart: "Tippen, um die Kurve im Diagramm zu finden",
			notCharted: "Dieser Wert ist nicht im Diagramm: zum Hinzuf\u00fcgen die Sperre der Oberfl\u00e4che aufheben.",
			prefConfig: "Link zur Konfiguration anzeigen",
			prefMaximize: "Maximieren-Schaltfl\u00e4che anzeigen",
			prefResetHidden: "Versteckte Kacheln und Diagramme wieder anzeigen",
			prefHidden: "Versteckt: {n} Kacheln, {m} Diagramme, {k} Sensoren",
			hideBox: "Diese Kachel ausblenden",
			hidePanel: "Dieses Diagramm ausblenden",
			showHidden: "{n} versteckte anzeigen",
			showHiddenDevices: "{n} versteckte Sensoren anzeigen",
			hideDevice: "Diesen Sensor ausblenden",
			prefKpis: "Kennzahlen",
			prefShowKpis: "Kennzahlen-Bereich anzeigen",
			prefSensors: "Sensoren",
			prefBoxes: "Messwert-Kacheln",
			prefNoItems: "Nichts aufzulisten.",
			hideKpi: "Diese Kennzahl ausblenden",
			optPanels: "Sichtbare Diagramme",
			optNoPanels: "Keine Diagramme: zuerst eine Messgröße wählen.",
			family_temperature: "Temperatur", family_humidity: "Luftfeuchte",
			family_absolute_humidity: "Absolute Feuchte", family_pressure: "Luftdruck",
			family_illuminance: "Beleuchtungsst\u00e4rke", family_voltage: "Spannung",
			family_battery: "Batterie", family_conductivity: "Leitf\u00e4higkeit",
			family_co2: "CO\u2082", family_particulates: "Feinstaub",
			family_weight: "Gewicht", family_speed: "Geschwindigkeit", family_distance: "Entfernung",
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
			pwaBodyChrome: "Der Browser hat die Installation nicht angeboten. http://fritz.box ist kein sicherer Kontext (https oder localhost): damit gibt es keinen Service Worker, kein +-Symbol in Samsung Internet und keinen Installieren-Knopf - \u201eZum Startbildschirm hinzuf\u00fcgen\u201c legt nur ein Lesezeichen an, das mit Adressleiste \u00f6ffnet. F\u00fcr eine echte App das Portal \u00fcber https \u00f6ffnen, oder \u00fcber localhost mit einem SSH-Tunnel (ssh -L 8181:localhost:81 root@fritz.box).",
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
	var SETTINGS_KEY = "ble2uart-portal-settings-v1";
	var ORDER_KEY = "ble2uart-portal-order-v1";
	var LEGACY_CHART_KEY = "ble2uart-portal-chartmode";

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
		/* Last answer of `action=info`: the catalog is refreshed every 30 s but
		 * the statistics are not, and without them the "samples" indicator
		 * would fall back to a dash after the first refresh. */
		stats: null,
		/* false until the charts are composed: only then the page is shown, and
		 * never covered again by the placeholder. */
		firstLoad: false,
		/* Preferences of the page, kept in the browser: how series are grouped,
		 * which unit system is shown, whether a dot marks every sample, the two
		 * titles, the default fullscreen mode, the config link and the boxes or
		 * panels the user hid. */
		settings: {
			theme: "system",
			group: "unit", units: "native", points: false,
			title: "", subtitle: "", fullscreen: false, showConfig: true, showMaximize: true,
			showKpis: true, hiddenKpis: [],
			hiddenSeries: [], hiddenPanels: [], hiddenDevices: [],
			/* Locked: the layout becomes read-only (no crosses, no reorder
			 * arrows, no adding/removing series, no reset, no chart options). */
			uiLocked: false,
			/* Locked separately: the separator between the values and the chart
			 * does not move, so a touch on a tablet cannot resize the columns. */
			splitLocked: false
		},
		order: []
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

	/* ------------------------------------------------- chart preferences
	 * Grouping, unit system and sample dots are per browser preferences, kept
	 * next to the view. The daemon always serves the stored units and values,
	 * so switching to imperial is only a display change. */
	function settingsRead() {
		var raw = null;
		try { raw = window.localStorage.getItem(SETTINGS_KEY); } catch (e) { raw = null; }
		/* Cookie fallback, like the saved views: a private window or an embedded
		 * webview can drop localStorage between sessions, and then the UI lock
		 * would silently come back unlocked. */
		if (!raw) { raw = cookieRead(SETTINGS_KEY); }
		var stored = null;
		try { stored = raw ? JSON.parse(raw) : null; } catch (e) { stored = null; }
		if (stored && typeof stored === "object") {
			if (stored.theme === "system" || stored.theme === "light" || stored.theme === "dark") {
				state.settings.theme = stored.theme;
			}
			if (stored.group === "unit" || stored.group === "family" || stored.group === "single") {
				state.settings.group = stored.group;
			}
			if (stored.units === "native" || stored.units === "metric" || stored.units === "imperial") {
				state.settings.units = stored.units;
			}
			state.settings.points = stored.points === true;
			state.settings.fullscreen = stored.fullscreen === true;
			state.settings.showConfig = stored.showConfig !== false;
			state.settings.showMaximize = stored.showMaximize !== false;
			state.settings.title = typeof stored.title === "string" ? stored.title.slice(0, 60) : "";
			state.settings.subtitle = typeof stored.subtitle === "string" ? stored.subtitle.slice(0, 60) : "";
			state.settings.hiddenSeries = stringList(stored.hiddenSeries);
			state.settings.hiddenPanels = stringList(stored.hiddenPanels);
			state.settings.hiddenDevices = stringList(stored.hiddenDevices);
			state.settings.hiddenKpis = stringList(stored.hiddenKpis);
			state.settings.showKpis = stored.showKpis !== false;
			state.settings.uiLocked = stored.uiLocked === true;
			state.settings.splitLocked = stored.splitLocked === true;
			return;
		}
		/* Migrate the old split/merge toggle of the previous version. */
		try {
			if (window.localStorage.getItem(LEGACY_CHART_KEY) === "single") { state.settings.group = "single"; }
		} catch (e) { /* ignore */ }
	}

	function settingsWrite() {
		var raw = JSON.stringify(state.settings);
		try { window.localStorage.setItem(SETTINGS_KEY, raw); } catch (e) { /* ignore */ }
		/* The lock is the one setting that cannot be restored by tapping
		 * something, so it is also kept in a cookie for browsers that forget
		 * localStorage (private windows, embedded webviews). The lists of hidden
		 * items can push the JSON over the cookie limit, so the cookie keeps the
		 * switches and the layout fields only: everything else comes from
		 * localStorage anyway. */
		var small = {
			theme: state.settings.theme,
			group: state.settings.group,
			units: state.settings.units,
			points: state.settings.points,
			fullscreen: state.settings.fullscreen,
			showConfig: state.settings.showConfig,
			showMaximize: state.settings.showMaximize,
			showKpis: state.settings.showKpis,
			uiLocked: state.settings.uiLocked,
			splitLocked: state.settings.splitLocked,
			title: state.settings.title,
			subtitle: state.settings.subtitle
		};
		cookieWrite(SETTINGS_KEY, JSON.stringify(small), STORE_DAYS);
	}

	/** Keep only the strings of an array read from the browser storage. */
	function stringList(value) {
		if (Object.prototype.toString.call(value) !== "[object Array]") { return []; }
		return value.filter(function (item) { return typeof item === "string"; });
	}

	function listAdd(list, key) {
		if (list.indexOf(key) < 0) { list.push(key); }
		return list;
	}

	function listRemove(list, key) {
		var index = list.indexOf(key);
		if (index >= 0) { list.splice(index, 1); }
		return list;
	}

	function orderRead() {
		var raw = null;
		try { raw = window.localStorage.getItem(ORDER_KEY); } catch (e) { raw = null; }
		var stored = null;
		try { stored = raw ? JSON.parse(raw) : null; } catch (e) { stored = null; }
		if (Object.prototype.toString.call(stored) === "[object Array]") {
			state.order = stored.filter(function (key) { return typeof key === "string"; });
		}
	}

	function orderWrite() {
		try { window.localStorage.setItem(ORDER_KEY, JSON.stringify(state.order)); } catch (e) { /* ignore */ }
	}

	/* ------------------------------------------------- attribute families
	 * The ATC decoder publishes "temperature", the Theengs decoder
	 * "theengs_temperature": the same physical quantity under two names. The
	 * classifier folds synonyms into one family, so "one chart per quantity"
	 * can put them on the same axis. */
	var FAMILY_ALIASES = {
		temperature: ["temperature", "temp", "tempc", "tempf", "temp_c", "temp_f", "celsius", "fahrenheit", "dew_point", "dewpoint", "heat_index", "apparent_temperature"],
		humidity: ["humidity", "hum", "rel_humidity", "relative_humidity"],
		absolute_humidity: ["absolute_humidity", "abs_humidity", "humidity_absolute"],
		pressure: ["pressure", "press", "barometer"],
		illuminance: ["illuminance", "lux", "light", "light_level", "brightness"],
		voltage: ["voltage", "battery_v", "batt_v", "battery_voltage"],
		battery: ["battery", "battery_level", "battery_percent", "battery_percentage", "batt"],
		conductivity: ["conductivity", "ec"],
		co2: ["co2", "carbon_dioxide"],
		particulates: ["pm1", "pm2_5", "pm25", "pm10"],
		weight: ["weight", "mass"],
		speed: ["speed", "wind_speed"],
		distance: ["depth", "distance", "rain", "precipitation"]
	};
	var FAMILY_LOOKUP = null;

	function familyLookup() {
		if (FAMILY_LOOKUP) { return FAMILY_LOOKUP; }
		var map = {};
		Object.keys(FAMILY_ALIASES).forEach(function (family) {
			map[family] = family;
			FAMILY_ALIASES[family].forEach(function (alias) { map[alias] = family; });
		});
		FAMILY_LOOKUP = map;
		return map;
	}

	/** Canonical quantity of an attribute name ("theengs_temp" -> temperature). */
	function familyOf(attribute) {
		var name = String(attribute || "").toLowerCase()
			.replace(/^theengs_/, "")
			.replace(/[\s-]+/g, "_");
		var map = familyLookup();
		if (map[name]) { return map[name]; }
		var stripped = name.replace(/_(c|f|celsius|fahrenheit|percent|pct|value|level)$/, "");
		if (map[stripped]) { return map[stripped]; }
		return name;
	}

	function familyTitle(family) {
		var table = TEXT[lang] || TEXT.en;
		var key = "family_" + family;
		return table[key] || TEXT.en[key] || family.replace(/_/g, " ");
	}

	/* ------------------------------------------------------- unit systems
	 * Conversions are pure display: the stored series keeps its own unit. */
	var UNIT_ALIASES = {
		"c": "\u00b0C", "\u00b0c": "\u00b0C", "celsius": "\u00b0C",
		"f": "\u00b0F", "\u00b0f": "\u00b0F", "fahrenheit": "\u00b0F",
		"g/m3": "g/m\u00b3", "gr/m3": "g/m\u00b3", "lx": "lux", "degc": "\u00b0C", "degf": "\u00b0F"
	};

	function canonicalUnit(unit) {
		var text = String(unit || "").trim();
		if (!text) { return ""; }
		var key = text.toLowerCase();
		return UNIT_ALIASES.hasOwnProperty(key) ? UNIT_ALIASES[key] : text;
	}

	function identity(value) { return value; }

	/* unit -> [target unit, transform] for each non-native system */
	var CONVERSIONS = {
		"\u00b0C": { imperial: ["\u00b0F", function (v) { return v * 9 / 5 + 32; }] },
		"\u00b0F": { metric: ["\u00b0C", function (v) { return (v - 32) * 5 / 9; }] },
		"K": {
			metric: ["\u00b0C", function (v) { return v - 273.15; }],
			imperial: ["\u00b0F", function (v) { return (v - 273.15) * 9 / 5 + 32; }]
		},
		"mm": { imperial: ["in", function (v) { return v / 25.4; }] },
		"cm": { imperial: ["in", function (v) { return v / 2.54; }] },
		"m": { imperial: ["ft", function (v) { return v * 3.28084; }] },
		"g/m\u00b3": { imperial: ["gr/ft\u00b3", function (v) { return v * 0.436995; }] },
		"hPa": { imperial: ["inHg", function (v) { return v * 0.02953; }] },
		"mb": { imperial: ["inHg", function (v) { return v * 0.02953; }] },
		"kPa": { imperial: ["inHg", function (v) { return v * 0.2953; }] },
		"Pa": { imperial: ["inHg", function (v) { return v * 0.0002953; }] },
		"m/s": { imperial: ["mph", function (v) { return v * 2.236936; }] },
		"km/h": { imperial: ["mph", function (v) { return v * 0.621371; }] },
		"kg": { imperial: ["lb", function (v) { return v * 2.204623; }] },
		"g": { imperial: ["oz", function (v) { return v * 0.035274; }] },
		"lux": { imperial: ["fc", function (v) { return v / 10.7639; }] }
	};

	/** Display unit and value transform of a stored unit. */
	function unitPlan(unit, system) {
		var canonical = canonicalUnit(unit);
		var rule = CONVERSIONS[canonical] && CONVERSIONS[canonical][system];
		if (system === "native" || !rule) {
			return { unit: unit || "", convert: identity };
		}
		return { unit: rule[0], convert: rule[1] };
	}

	/** Cached plan of a series: unit and points already converted. */
	function chartPlan(chart) {
		var system = state.settings.units;
		if (chart.planFor === system && chart.plan) { return chart.plan; }
		var plan = unitPlan(chart.unit, system);
		chart.planFor = system;
		chart.plan = {
			unit: plan.unit,
			convert: plan.convert,
			points: (chart.points || []).map(function (point) {
				var value = plan.convert(point[1]);
				/* A boolean has no intermediate value: a bucket that mixes on and
				 * off samples would otherwise be drawn halfway up the chart. */
				if (chart.kind === "boolean") { value = value >= 0.5 ? 1 : 0; }
				return [point[0], value, point[2]];
			})
		};
		return chart.plan;
	}

	function chartUnit(chart) { return chartPlan(chart).unit; }
	function chartPoints(chart) { return chartPlan(chart).points; }

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
			/* Frozen separator (preferences): no drag, no keyboard step. */
			if (event.button !== 0 || splitLocked()) { return; }
			dragging = true;
			bar.setAttribute("aria-valuenow", String(splitPct));
			window.addEventListener("pointermove", onMove);
			window.addEventListener("pointerup", onStop);
			window.addEventListener("pointercancel", onStop);
			event.preventDefault();
		});
		bar.addEventListener("keydown", function (event) {
			if (event.key !== "ArrowLeft" && event.key !== "ArrowRight" || splitLocked()) { return; }
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
		var url = endpointUrl(endpoint, query);
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
		syncUiLock();
		renderHeader();
		renderKpis();
		renderDevices();
		renderRanges();
		renderZoom();
		drawChart();
		if (els.prefsbox) { renderPrefs(); }
	}

	function renderHeader() {
		syncMaximize();
		var catalog = state.catalog;
		/* The two titles and the link to the configuration page are user
		 * preferences: an empty field falls back to the strings the daemon
		 * shipped with the page. */
		if (els.title) { els.title.textContent = state.settings.title || DEFAULT_TITLE; }
		if (els.subtitle) { els.subtitle.textContent = state.settings.subtitle || t("subtitle"); }
		if (els.config) {
			els.config.hidden = state.settings.showConfig === false;
			els.config.title = t("config");
			els.config.setAttribute("aria-label", t("config"));
		}
		document.getElementById("reload").title = t("refresh");
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

	/** The four indicators, in the order they are also listed in the
	 *  preferences (key, caption, value, tooltip). */
	function kpiItems() {
		var catalog = state.catalog;
		var series = 0;
		var newest = 0;
		var devices = (catalog && catalog.devices) || [];
		devices.forEach(function (device) {
			(device.series || []).forEach(function (item) {
				series++;
				if (item.last_ns > newest) { newest = item.last_ns; }
			});
		});
		return [
			{ key: "devices", label: t("devices"), value: String(devices.length), note: "" },
			{ key: "series", label: t("series"), value: String(series), note: "" },
			{ key: "samples", label: t("samples"), value: catalog && catalog.samples ? String(catalog.samples) : "\u2014", note: "" },
			{ key: "updated", label: t("updated"), value: newest ? age(newest, catalog.now_ns) : t("never"), note: (catalog && catalog.database) || "" }
		];
	}

	/** Layout locked: everything that edits the page is hidden and ignored. */
	function uiLocked() {
		return state.settings.uiLocked === true;
	}

	/** Locked tap on a value box: scroll to its curve and flash it. A value
	 *  that is not in the chart cannot be added while the layout is locked, so
	 *  the panel says so instead of doing nothing at all. */
	function flashSeries(key) {
		var chart = null;
		var block = null;
		state.charts.forEach(function (item) {
			if (item.key === key) { chart = item; }
		});
		if (chart) {
			state.blocks.forEach(function (item) {
				if (item.charts.indexOf(chart) >= 0) { block = item; }
			});
		}
		if (!block) {
			if (els.panel && els.panel.scrollIntoView) {
				els.panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
			}
			flashMessage(t("notCharted"));
			return;
		}
		if (block.root.scrollIntoView) {
			block.root.scrollIntoView({ block: "nearest", behavior: "smooth" });
		}
		block.flash = { key: key, until: Date.now() + 1600 };
		drawBlock(block);
		window.setTimeout(function () {
			if (!block.flash || Date.now() < block.flash.until) { return; }
			block.flash = null;
			drawBlock(block);
		}, 1700);
	}

	/** Short note above the chart, used when a tap cannot do what it promises. */
	function flashMessage(text) {
		if (!els.panel) { return; }
		var note = document.getElementById("flashmsg");
		if (!note) {
			note = document.createElement("p");
			note.id = "flashmsg";
			note.className = "pflashmsg";
			note.hidden = true;
			els.panel.insertBefore(note, els.panel.firstElementChild);
		}
		note.textContent = text;
		note.hidden = false;
		if (flashMessage.timer) { window.clearTimeout(flashMessage.timer); }
		flashMessage.timer = window.setTimeout(function () { note.hidden = true; }, 3200);
	}

	/** The lock is one class on <body>: CSS hides the crosses, the arrows, the
	 *  reset and the chart options button, and it comes back the moment the
	 *  option is cleared in the preferences. */
/** The separator between the values and the chart, frozen too. */
	function splitLocked() {
		return state.settings.splitLocked === true;
	}

	function syncUiLock() {
		if (!document.body) { return; }
		if (uiLocked()) { document.body.classList.add("pui-locked"); }
		else { document.body.classList.remove("pui-locked"); }
		if (splitLocked()) { document.body.classList.add("psplit-locked"); }
		else { document.body.classList.remove("psplit-locked"); }
	}

	function renderKpis() {
		var catalog = state.catalog;
		els.kpis.textContent = "";
		els.kpis.hidden = state.settings.showKpis === false;
		if (!catalog || state.settings.showKpis === false) { return; }
		kpiItems().forEach(function (item) {
			if (state.settings.hiddenKpis.indexOf(item.key) >= 0) { return; }
			var box = document.createElement("div");
			box.className = "pkpi";
			var name = document.createElement("span");
			name.className = "k";
			name.textContent = item.label;
			var value = document.createElement("span");
			value.className = "v";
			value.textContent = item.value;
			if (item.note) { value.title = item.note; }
			/* Same cross as the data boxes and the charts. */
			var hide = document.createElement("button");
			hide.type = "button";
			hide.className = "pkpihide";
			hide.textContent = "\u00d7";
			hide.title = t("hideKpi");
			hide.setAttribute("aria-label", t("hideKpi"));
			hide.addEventListener("click", function () {
				listAdd(state.settings.hiddenKpis, item.key);
				settingsWrite();
				render();
			});
			box.appendChild(name);
			box.appendChild(value);
			box.appendChild(hide);
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
		var hiddenDevices = [];
		var shownDevices = catalog.devices.filter(function (device) {
			if (isHiddenDevice(device.mac)) { hiddenDevices.push(device.mac); return false; }
			return true;
		});
		shownDevices.forEach(function (device) {
			var section = document.createElement("section");
			section.className = "pdevice";
			var header = document.createElement("header");
			var title = document.createElement("h3");
			title.textContent = device.label || device.name || device.mac;
			var right = document.createElement("span");
			right.className = "page";
			right.textContent = age(device.last_ns, now);
			header.appendChild(title);
			header.appendChild(right);

			/* Cross: hide the whole sensor section, like the charts and the
			 * single boxes. */
			var hide = document.createElement("button");
			hide.type = "button";
			hide.className = "pmove phide pdevhide";
			hide.textContent = "\u00d7";
			hide.title = t("hideDevice");
			hide.setAttribute("aria-label", t("hideDevice"));
			hide.addEventListener("click", function () { hideDevice(device.mac); });
			header.appendChild(hide);
			section.appendChild(header);

			/* Boxes the user hid: not rendered here, they stay listed in the
			 * preferences, where they can be shown again. */
			var visible = (device.series || []).filter(function (series) {
				return !isHiddenSeries(keyOf(device.mac, series));
			});

			/* Second line: vendor, model and firmware from the YAML file plus the
			 * MAC of the advertisement, so two devices of the same model stay
			 * distinguishable. */
			var meta = document.createElement("div");
			meta.className = "pdevmeta";
			var maker = deviceDetail(device);
			if (maker) {
				var from = document.createElement("span");
				from.className = "pmaker";
				from.textContent = maker;
				meta.appendChild(from);
				meta.appendChild(document.createTextNode(" \u00b7 "));
			}
			var mac = document.createElement("span");
			mac.className = "pmac";
			mac.textContent = device.mac;
			meta.appendChild(mac);
			section.appendChild(meta);

			var grid = document.createElement("div");
			grid.className = "pseries";
			visible.forEach(function (series) {
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
			button.style.setProperty("--swatch", colorAt(index));
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
		/* Cross in the corner: hide this box. The series keeps feeding the
		 * charts, only its card disappears from the list. */
		var hide = document.createElement("span");
		hide.className = "pcardhide";
		hide.setAttribute("role", "button");
		hide.tabIndex = 0;
		hide.textContent = "\u00d7";
		hide.title = t("hideBox");
		hide.setAttribute("aria-label", t("hideBox"));
		var doHide = function (event) {
			if (event) { event.stopPropagation(); event.preventDefault(); }
			hideSeries(key);
		};
		hide.addEventListener("click", doHide);
		hide.addEventListener("keydown", function (event) {
			if (event.key === "Enter" || event.key === " ") { doHide(event); }
		});
		button.appendChild(hide);
		if (series.kind !== "text") {
			/* Unlocked the tap adds/removes the series; locked the page must not
			 * change, so the tap points at the chart instead. */
			button.addEventListener("click", function () {
				if (uiLocked()) { flashSeries(key); return; }
				toggle(mac, series);
			});
			button.title = uiLocked() ? t("tapToChart") : t("chartHint");
		}
		return button;
	}

	function toggle(mac, series) {
		/* Locked layout: the boxes only show values, they do not add series. */
		if (uiLocked()) { return; }
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
		var hasChart = !!(state.charts && state.charts.some(function (chart) {
			var points = chartPoints(chart);
			return points && points.length;
		}));
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
		var name = deviceLabel(chart.mac);
		var unit = chartUnit(chart);
		var detail = device ? deviceDetail(device) : "";
		return name + " \u00b7 " + chart.attribute + (unit ? " (" + unit + ")" : "") + (detail ? " \u00b7 " + detail : "");
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

	/** Name of a device: the YAML label first, then the name the decoder saw. */
	function deviceLabel(mac) {
		var device = findDevice(mac);
		if (!device) { return mac; }
		return device.label || device.name || mac;
	}

	/** "Xiaomi \u00b7 LYWSD03MMC \u00b7 fw 5.9" from the YAML identity, or "". */
	function deviceDetail(device) {
		if (!device) { return ""; }
		var parts = [];
		if (device.manufacturer) { parts.push(device.manufacturer); }
		if (device.model) { parts.push(device.model); }
		if (device.firmware_version) { parts.push("fw " + device.firmware_version); }
		return parts.join(" \u00b7 ");
	}

	/** Colour of a series: stable across panels and the legend. */
	function colorOf(chart) {
		return colorAt(state.charts.indexOf(chart));
	}

	/** Panel key of a series: its unit, its quantity, or the boolean panel. */
	function panelKey(chart) {
		var unit = chartUnit(chart);
		/* Booleans carry no unit and are states, not quantities: they always
		 * share one panel - in both grouping modes - where the lane offsets keep
		 * their two levels apart. */
		if (!unit && chart.kind === "boolean") { return "\u2022"; }
		if (state.settings.group === "family") {
			return familyOf(chart.attribute) + "|" + unit + "|" + chart.kind;
		}
		return unit;
	}

	/** Series split into panels, in the order the user chose. */
	function groupCharts(includeHidden) {
		if (!state.charts.length) { return []; }
		if (state.settings.group === "single") {
			return [{ key: "single", charts: state.charts.slice() }];
		}
		var order = [];
		var byKey = {};
		state.charts.forEach(function (chart) {
			var key = panelKey(chart);
			if (!byKey.hasOwnProperty(key)) { byKey[key] = []; order.push(key); }
			byKey[key].push(chart);
		});
		var groups = [];
		var placed = {};
		(state.order || []).forEach(function (key) {
			if (byKey.hasOwnProperty(key) && !placed[key]) {
				groups.push({ key: key, charts: byKey[key] });
				placed[key] = true;
			}
		});
		order.forEach(function (key) {
			if (!placed[key]) { groups.push({ key: key, charts: byKey[key] }); }
		});
		if (!includeHidden) {
			groups = groups.filter(function (group) {
				return state.settings.hiddenPanels.indexOf(group.key) < 0;
			});
		}
		return groups;
	}

	/** Move a panel one position up or down and remember the order. */
	function moveBlock(block, delta) {
		if (uiLocked()) { return; }
		var keys = state.blocks.map(function (item) { return item.key; });
		var index = keys.indexOf(block.key);
		var target = index + delta;
		if (index < 0 || target < 0 || target >= keys.length) { return; }
		keys.splice(target, 0, keys.splice(index, 1)[0]);
		state.order = keys;
		orderWrite();
		render();
	}

	function removeSeries(chart) {
		if (uiLocked()) { return; }
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
		var head = document.createElement("div");
		head.className = "pchartblockhead";
		var title = document.createElement("h3");
		title.className = "pchartblocktitle";
		var move = document.createElement("div");
		move.className = "pchartblockmove";
		var up = document.createElement("button");
		up.type = "button";
		up.className = "pmove";
		up.textContent = "\u25b2";
		var down = document.createElement("button");
		down.type = "button";
		down.className = "pmove";
		down.textContent = "\u25bc";
		var hide = document.createElement("button");
		hide.type = "button";
		hide.className = "pmove phide";
		hide.textContent = "\u00d7";
		hide.title = t("hidePanel");
		hide.setAttribute("aria-label", t("hidePanel"));
		move.appendChild(up);
		move.appendChild(down);
		move.appendChild(hide);
		head.appendChild(title);
		head.appendChild(move);
		var wrap = document.createElement("div");
		wrap.className = "pcanvas";
		var canvas = document.createElement("canvas");
		var empty = document.createElement("div");
		empty.className = "pempty";
		wrap.appendChild(canvas);
		wrap.appendChild(empty);
		var legend = document.createElement("div");
		legend.className = "plegend";
		root.appendChild(head);
		root.appendChild(wrap);
		root.appendChild(legend);
		var block = {
			root: root, title: title, canvas: canvas, empty: empty, legend: legend,
			key: "", up: up, down: down,
			charts: [], view: null, hover: null, drag: null, pan: null
		};
		root.__block = block;
		up.addEventListener("click", function () { moveBlock(block, -1); });
		down.addEventListener("click", function () { moveBlock(block, 1); });
		hide.addEventListener("click", function () { hidePanel(block.key); });
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
			block.charts = groups[index].charts;
			block.key = groups[index].key;
			block.up.disabled = index === 0;
			block.down.disabled = index === groups.length - 1;
			state.blocks.push(block);
		}
		if (state.blocks.indexOf(state.active) < 0) { state.active = state.blocks[0] || null; }
	}

	/** Host element for the panels, plus the chart options button. */
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
		ensureOptions();
	}

	/** Row of the options dialog: a caption and a <select>. */
	function selectRow(id, caption, values, current, onPick) {
		var row = document.createElement("label");
		var text = document.createElement("span");
		text.textContent = caption;
		var select = document.createElement("select");
		select.id = id;
		values.forEach(function (item) {
			var option = document.createElement("option");
			option.value = item[0];
			option.textContent = item[1];
			select.appendChild(option);
		});
		select.value = current;
		select.addEventListener("change", function () { onPick(select.value); });
		row.appendChild(text);
		row.appendChild(select);
		return row;
	}

	/** Dialog with the grouping, unit system and sample dots. */
	function ensureOptions() {
		if (els.options) { return; }
		var controls = els.panel.querySelector(".pcontrols");
		var button = document.createElement("button");
		button.type = "button";
		button.id = "chartopts";
		button.textContent = "\u2699";
		button.addEventListener("click", openOptions);
		if (controls) { controls.appendChild(button); } else { els.panel.appendChild(button); }
		els.options = button;

		var box = document.createElement("dialog");
		box.className = "phelp psettings";
		box.id = "chartoptsbox";
		var head = document.createElement("h3");
		head.textContent = t("options");
		box.appendChild(head);
		var body = document.createElement("div");
		body.className = "psettingsbody";
		body.appendChild(selectRow("optgroup", t("optGroup"), [
			["unit", t("optGroupUnit")],
			["family", t("optGroupFamily")],
			["single", t("optGroupSingle")]
		], state.settings.group, function (value) {
			state.settings.group = value;
			settingsWrite();
			render();
		}));
		var groupHint = document.createElement("p");
		groupHint.className = "phelphint";
		groupHint.textContent = t("optGroupHint");
		body.appendChild(groupHint);
		body.appendChild(selectRow("optunits", t("optUnits"), [
			["native", t("optUnitsNative")],
			["metric", t("optUnitsMetric")],
			["imperial", t("optUnitsImperial")]
		], state.settings.units, function (value) {
			state.settings.units = value;
			settingsWrite();
			render();
		}));
		var points = document.createElement("label");
		points.className = "pcheck";
		var box2 = document.createElement("input");
		box2.type = "checkbox";
		box2.id = "optpoints";
		box2.checked = state.settings.points === true;
		box2.addEventListener("change", function () {
			state.settings.points = box2.checked;
			settingsWrite();
			render();
		});
		var pointsText = document.createElement("span");
		pointsText.textContent = t("optPoints");
		points.appendChild(box2);
		points.appendChild(pointsText);
		body.appendChild(points);
		var pointsHint = document.createElement("p");
		pointsHint.className = "phelphint";
		pointsHint.textContent = t("optPointsHint");
		body.appendChild(pointsHint);
		var panelsHead = document.createElement("p");
		panelsHead.className = "psettingsgroup";
		panelsHead.textContent = t("optPanels");
		body.appendChild(panelsHead);
		var panels = document.createElement("div");
		panels.className = "ppanels";
		panels.id = "optpanels";
		body.appendChild(panels);
		box.appendChild(body);
		var form = document.createElement("form");
		form.method = "dialog";
		var close = document.createElement("button");
		close.type = "submit";
		close.textContent = t("helpClose");
		form.appendChild(close);
		box.appendChild(form);
		document.body.appendChild(box);
		els.optionsbox = box;
		renderOptions();
	}

	function openOptions() {
		if (!els.optionsbox) { return; }
		renderOptions();
		if (typeof els.optionsbox.showModal === "function") {
			els.optionsbox.showModal();
		} else {
			els.optionsbox.setAttribute("open", "");
		}
	}

	function renderOptions() {
		if (!els.options) { return; }
		els.options.title = t("options");
		els.options.setAttribute("aria-label", t("options"));
		var box = els.optionsbox;
		if (!box) { return; }
		var group = box.querySelector("#optgroup");
		var units = box.querySelector("#optunits");
		var points = box.querySelector("#optpoints");
		if (group) { group.value = state.settings.group; }
		if (units) { units.value = state.settings.units; }
		if (points) { points.checked = state.settings.points === true; }
		var list = box.querySelector("#optpanels");
		if (list) {
			list.textContent = "";
			var groups = groupCharts(true);
			if (!groups.length) { list.appendChild(hintRow(t("optNoPanels"))); }
			groups.forEach(function (group) {
				var row = document.createElement("label");
				row.className = "pcheck";
				var input = document.createElement("input");
				input.type = "checkbox";
				input.checked = state.settings.hiddenPanels.indexOf(group.key) < 0;
				input.addEventListener("change", function () {
					if (input.checked) { listRemove(state.settings.hiddenPanels, group.key); }
					else { listAdd(state.settings.hiddenPanels, group.key); }
					settingsWrite();
					render();
				});
				var text = document.createElement("span");
				text.textContent = titleForCharts(group.charts);
				row.appendChild(input);
				row.appendChild(text);
				list.appendChild(row);
			});
		}
		els.options.setAttribute("aria-pressed", state.settings.group === "single" ? "false" : "true");
	}

	/** Legend of a panel: the device name, plus the attribute when needed. */
	function legendLabel(chart, block) {
		var name = deviceLabel(chart.mac);
		var shared = 0;
		block.charts.forEach(function (item) {
			if (deviceLabel(item.mac) === name) { shared++; }
		});
		if (shared > 1) { return name + " \u00b7 " + chart.attribute; }
		return name;
	}

	/** Panel title without repeating "attribute (unit)" for every device. */
	function blockTitle(block) {
		return titleForCharts(block.charts);
	}

	function titleForCharts(charts) {
		var kinds = [];
		var names = [];
		charts.forEach(function (chart) {
			var label = state.settings.group === "family"
				? familyTitle(familyOf(chart.attribute))
				: chart.attribute;
			var unit = chartUnit(chart);
			var text = unit && chart.kind !== "boolean" ? label + " (" + unit + ")" : label;
			if (kinds.indexOf(text) < 0) { kinds.push(text); }
			var name = deviceLabel(chart.mac);
			if (names.indexOf(name) < 0) { names.push(name); }
		});
		return kinds.join(" \u00b7 ") + (names.length ? " \u2014 " + names.join(", ") : "");
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
			text.textContent = legendLabel(chart, block);
			chip.appendChild(dot);
			chip.appendChild(text);
			chip.title = seriesLabel(chart) + " \u2014 " + t(uiLocked() ? "tapToChart" : "chartHint");
			chip.addEventListener("click", function () {
				/* Locked: the chip cannot remove the series, it highlights the
				 * curve - the same answer as a tap on a value box. */
				if (uiLocked()) { flashSeries(chart.key); return; }
				removeSeries(chart);
			});
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
				var points = chartPoints(chart);
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
		renderOptions();
		renderZoom();
		state.blocks.forEach(drawBlock);
		var total = 0;
		state.charts.forEach(function (chart) {
			var points = chartPoints(chart);
			total += points ? points.length : 0;
		});
		els.chartinfo.textContent = state.selected.length && total ? t("points", { n: total }) : "";
	}

	function drawBlock(block) {
		var canvas = block.canvas;
		var empty = block.empty;
		var title = block.title;
		renderLegend(block);

		var charts = block.charts.filter(function (chart) {
			var points = chartPoints(chart);
			return points && points.length;
		});
		if (!state.selected.length) {
			title.textContent = "\u2014";
			empty.textContent = t("chartEmpty");
			empty.hidden = false;
			block.view = null;
			clearCanvas(canvas);
			return;
		}
		title.textContent = blockTitle(block);
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
			chartPoints(chart).forEach(function (point) {
				if (point[0] >= from && point[0] <= to) { values.push(point[1]); }
			});
		});
		if (!values.length) {
			charts.forEach(function (chart) {
				chartPoints(chart).forEach(function (point) { values.push(point[1]); });
			});
		}
		var yMin = Math.min.apply(null, values);
		var yMax = Math.max.apply(null, values);
		/* Boolean panels have two states, not a numeric scale. Two series would
		 * sit exactly on top of each other at 0 and at 1, so every series gets a
		 * small lane offset: parallel lines, a few pixels apart, all visible. */
		var lanes = {};
		var onlyBoolean = charts.every(function (chart) { return chart.kind === "boolean"; });
		if (onlyBoolean) {
			/* The series of the same level stay packed a few pixels apart, while
			 * "on" and "off" keep the whole height between them: a segment is
			 * therefore always clearly at the top (on) or at the bottom (off). */
			var step = 0.045;
			var lowest = 0;
			var highest = 0;
			charts.forEach(function (chart, index) {
				var offset = (index - (charts.length - 1) / 2) * step;
				lanes[chart.key] = offset;
				lowest = Math.min(lowest, offset);
				highest = Math.max(highest, offset);
			});
			yMin = lowest - 0.10;
			yMax = 1 + highest + 0.10;
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

		/* On a phone in portrait the timestamp labels do not fit side by side:
		 * they are rotated by 45 degrees. The margin follows the real width of
		 * the longest label (sin 45 = 0.71), otherwise the first and the last
		 * characters are cut off at the bottom of the canvas. */
		var rotateLabels = size.width < 560;
		var steps = rotateLabels ? (size.width < 380 ? 2 : 3) : (size.width < 700 ? 4 : 5);
		var timeFormat = timeFormatter(to - from);
		context.font = "11px -apple-system, Segoe UI, Roboto, sans-serif";
		var longest = 0;
		for (var probe = 0; probe <= steps; probe++) {
			var width = context.measureText(timeFormat(from + (to - from) * probe / steps)).width;
			if (width > longest) { longest = width; }
		}
		var bottomPad = rotateLabels ? Math.min(110, Math.ceil(longest * 0.72) + 16) : 26;
		var box = { left: 52, right: size.width - 12, top: 10, bottom: size.height - bottomPad };
		context.clearRect(0, 0, size.width, size.height);
		if (box.right - box.left < 40 || box.bottom - box.top < 40) { return; }
		context.font = "11px -apple-system, Segoe UI, Roboto, sans-serif";
		context.textBaseline = "middle";

		var ticks = onlyBoolean ? [0, 1] : niceTicks(yMin, yMax, 5);
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
			context.fillText(onlyBoolean ? (value >= 0.5 ? t("on") : t("off")) : formatTick(value), box.left - 6, y);
		});

		for (var step = 0; step <= steps; step++) {
			var moment = from + (to - from) * step / steps;
			var x = box.left + (box.right - box.left) * step / steps;
			context.fillStyle = muted;
			if (rotateLabels) {
				/* Anchor at the tick and read the label upwards, so long stamps
				 * ("01/11 05:00") never overlap on a narrow screen. */
				context.save();
				context.translate(x, box.bottom + 5);
				context.rotate(-Math.PI / 4);
				context.textAlign = "right";
				context.textBaseline = "middle";
				context.fillText(timeFormat(moment), step === 0 ? -4 : 0, 0);
				context.restore();
			} else {
				context.textAlign = step === 0 ? "left" : step === steps ? "right" : "center";
				context.fillText(timeFormat(moment), x, box.bottom + 13);
			}
		}
		context.textAlign = "center";
		context.fillStyle = ink;

		charts.forEach(function (chart) {
			drawSeries(block, context, chart, box, from, to, yMin, yMax, colorOf(chart), lanes[chart.key] || 0);
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

	function drawSeries(block, context, chart, box, from, to, yMin, yMax, color, lane) {
		var points = chartPoints(chart);
		if (!points.length) { return; }
		var scaleX = function (ms) { return box.left + (ms - from) / (to - from) * (box.right - box.left); };
		var lift = lane || 0;
		var scaleY = function (value) { return box.bottom - (value + lift - yMin) / (yMax - yMin) * (box.bottom - box.top); };
		context.strokeStyle = color;
		context.lineWidth = 1.8;
		context.lineJoin = "round";
		context.lineCap = "round";
		context.beginPath();
		/* A state holds until the next sample: the boolean series is drawn as a
		 * square wave, with a vertical edge exactly at the time of the change. */
		if (chart.kind === "boolean") {
			points.forEach(function (point, index) {
				var x = scaleX(point[0]);
				var y = scaleY(point[1]);
				if (index === 0) {
					context.moveTo(x, y);
				} else {
					context.lineTo(x, scaleY(points[index - 1][1]));
					context.lineTo(x, y);
				}
			});
		} else {
			points.forEach(function (point, index) {
				var x = scaleX(point[0]);
				var y = scaleY(point[1]);
				if (index === 0) { context.moveTo(x, y); } else { context.lineTo(x, y); }
			});
		}
		/* A tap on a value box marks its curve for a moment, so the eye finds it
		 * among the others. */
		var flash = block.flash && block.flash.key === chart.key && Date.now() < block.flash.until;
		if (flash) {
			context.save();
			context.strokeStyle = color;
			context.globalAlpha = 0.3;
			context.lineWidth = 10;
			context.stroke();
			context.restore();
			context.strokeStyle = color;
			context.lineWidth = 1.8;
		}
		context.stroke();

		/* Optional dots: one per sample, thinned out only when they would overlap
		 * (600 px wide chart with 5000 samples would otherwise be a solid band). */
		if (state.settings.points) {
			var span = Math.abs(box.right - box.left);
			var step = 1;
			if (span > 0 && points.length > span / 3) { step = Math.ceil(points.length / (span / 3)); }
			context.fillStyle = color;
			for (var index = 0; index < points.length; index += step) {
				context.beginPath();
				context.arc(scaleX(points[index][0]), scaleY(points[index][1]), 1.9, 0, Math.PI * 2);
				context.fill();
			}
		}

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
			var series = chartPoints(chart);
			if (!series || !series.length) { return; }
			var point = nearest(series, ms);
			var tolerance = Math.max((chart.bucket_ns || 6e10) / 1e6, 60000);
			var row = document.createElement("div");
			row.className = "row";
			row.style.setProperty("--swatch", colorOf(chart));
			var dot = document.createElement("i");
			var label = document.createElement("span");
			label.textContent = chart.attribute;
			var value = document.createElement("em");
			if (point && Math.abs(point[0] - ms) <= tolerance) {
				var unit = chartUnit(chart);
				value.textContent = chart.kind === "boolean"
					? (point[1] >= 0.5 ? t("on") : t("off"))
					: number(point[1], unit) + (unit ? " " + unit : "");
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
		if (block) {
			if (block.hover) { block.hover = null; drawChart(); }
		} else {
			/* No panel given (help button, keyboard): clear the marker
			 * everywhere. */
			var redraw = false;
			state.blocks.forEach(function (item) {
				if (item.hover) { item.hover = null; redraw = true; }
			});
			if (redraw) { drawChart(); }
		}
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

	/* ------------------------------------------------------------- busy state
	 * The first request takes a moment on the router: instead of showing
	 * widgets without data (empty KPIs and half-drawn charts), the whole page is
	 * hidden behind a single spinner until the charts are composed. Periodic
	 * refreshes are silent: they never show it again. */
	function updateBusy() {
		setBusy(!state.firstLoad);
	}

	/** Show the page: called once the charts are drawn (or when the watchdog
	 *  fires), and never undone by a later periodic refresh. */
	function revealPage() {
		if (state.firstLoad) { return; }
		state.firstLoad = true;
		updateBusy();
		/* The panels were drawn while the page was still hidden, and a
		 * display:none element has no width: without this second pass the first
		 * chart would stay blank until the next refresh or a window resize.
		 * Showing the page and drawing it here is what makes the charts appear
		 * together with everything else. */
		drawChart();
	}

	/** Full-page placeholder: one spinner while the first answers are pending. */
	function ensureFirstLoad() {
		if (document.getElementById("firstload")) { return; }
		var main = document.querySelector("main.pmain");
		if (!main) { return; }
		var box = document.createElement("div");
		box.className = "pfirstload";
		box.id = "firstload";
		var spinner = document.createElement("div");
		spinner.className = "pspinner";
		var label = document.createElement("p");
		label.textContent = t("loading");
		box.appendChild(spinner);
		box.appendChild(label);
		main.appendChild(box);
	}

	function setBusy(busy) {
		var main = document.querySelector("main.pmain");
		if (main) {
			if (busy) { main.classList.add("pfirst"); } else { main.classList.remove("pfirst"); }
		}
	}

	/** The database statistics that the KPI row shows next to the devices. */
	function mergeStats(catalog, info) {
		if (!catalog || !info) { return; }
		catalog.samples = info.samples;
		catalog.size = info.size_bytes;
		catalog.wal = info.wal_bytes;
		catalog.schema = info.schema;
	}

	function loadCatalog(silent, withStats) {
		if (!silent && !state.catalog) { render(); }
		/* `action=info` counts the rows of the samples table and sizes the
		 * database on the USB disk: it takes seconds on a router and nothing on
		 * the first screen needs it, so it runs *beside* the catalog and only
		 * refreshes the KPI row when it lands. Blocking the first paint on it
		 * was what made the charts show up late. */
		var stats = withStats ? request("action=info").catch(function () { return null; }) : null;
		return request("action=catalog").then(function (catalog) {
			state.catalog = catalog;
			state.error = "";
			if (state.stats) { mergeStats(catalog, state.stats); }
			var known = {};
			(catalog.devices || []).forEach(function (device) {
				(device.series || []).forEach(function (series) { known[keyOf(device.mac, series)] = true; });
			});
			state.selected = state.selected.filter(function (key) { return known[key]; });
			render();
			if (state.selected.length) {
				loadCharts();
			} else {
				/* Nothing to draw: the page is complete as it is. */
				revealPage();
			}
			if (stats) {
				stats.then(function (info) {
					if (!info || info.ok === false || !state.catalog) { return; }
					state.stats = info;
					mergeStats(state.catalog, info);
					renderKpis();
				});
			}
		}).catch(function (error) {
			state.error = error.message || String(error);
			render();
			revealPage();
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
		}).catch(function () {
			/* A broken series must not keep the first-load placeholder up. */
		}).then(function () {
			/* Every panel has its series: the page is composed, show it. */
			revealPage();
		});
	}

	/* --------------------------------------------------------------- web app
	 * The portal is installable: the CGI also serves a manifest
	 * (?action=manifest) and a service worker (?action=sw) that caches this page
	 * and the last JSON answers, so a home-screen icon opens it without the
	 * browser chrome and the values stay readable when the router is offline.
	 * Browsers only allow this in a secure context (https or localhost), so the
	 * registration is skipped over plain http, where an icon on the home
	 * screen only opens a bookmark with the URL bar. */
	var DEFAULT_TITLE = "ble2uart_gateway";

	/** Ask for page fullscreen as soon as the user touches the page: browsers
	 *  reject requestFullscreen without a gesture, so a saved preference can
	 *  only be honoured on the first interaction. */
	function pwaFullscreenMode() {
		return !!(window.matchMedia && window.matchMedia("(display-mode: fullscreen)").matches);
	}

	function armAutoFullscreen() {
		/* An app installed with "display": "fullscreen" is already fullscreen:
		 * asking again would open an element fullscreen inside the app window. */
		if (!state.settings.fullscreen || appFullscreenOn() || pwaFullscreenMode()) { return; }
		var go = function () {
			document.removeEventListener("pointerdown", go, true);
			document.removeEventListener("keydown", go, true);
			if (state.settings.fullscreen && !appFullscreenOn()) { toggleAppFullscreen(); }
		};
		document.addEventListener("pointerdown", go, true);
		document.addEventListener("keydown", go, true);
	}

	/* An installed app can be launched in any of the display modes of the
	 * manifest: "display-mode: standalone" alone missed "display: fullscreen",
	 * which is the mode this portal asks for. */
	function pwaStandalone() {
		if (window.navigator.standalone === true) { return true; }
		if (document.referrer && document.referrer.indexOf("android-app://") === 0) { return true; }
		if (!window.matchMedia) { return false; }
		return window.matchMedia("(display-mode: standalone)").matches ||
			window.matchMedia("(display-mode: fullscreen)").matches ||
			window.matchMedia("(display-mode: minimal-ui)").matches;
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
		els.maximize.hidden = state.settings.showMaximize === false || !appFullscreenApi();
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
		if (!window.isSecureContext || PROXY) { return; }
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

	/* The manifest is a static file in the asset directory, never the CGI:
	 * a browser fetches a manifest **without** credentials, and the CGI path is
	 * behind the freetz session, so `?action=manifest` answered with the login
	 * page and the manifest was dropped as invalid ("Syntax error"). Without a
	 * manifest there is no "display" either, so the installed app kept the URL
	 * bar. The static copies need no session; English is the fallback. */
	var MANIFEST_BASE = "/ble2uart_gateway/";

	/** Manifest of the current language: the static copies are per language
	 *  (`manifest.json` is English and also the fallback), so the installed app
	 *  is named and described in the language the user reads. It has to be a
	 *  static file - see the comment in setupPwa(). */
	function manifestHref() {
		var file = lang && lang !== "en" ? "manifest." + lang + ".json" : "manifest.json";
		return MANIFEST_BASE + file;
	}

	function ensureManifestLink() {
		var link = document.getElementById("manifest");
		/* Behind the freetz proxy the page comes from the AVM gateway, whose
		 * CSP is default-src 'none' without manifest-src: a manifest is blocked
		 * there and the proxy already strips the tag from the HTML. Leave it out
		 * instead of provoking a violation - install the app from the freetz
		 * URL (http://fritz.box:81/...), where the static manifest is served
		 * without a session and the app really opens fullscreen. */
		if (PROXY) {
			if (link && link.parentNode) { link.parentNode.removeChild(link); }
			return;
		}
		if (!link || !link.parentNode) {
			link = document.createElement("link");
			link.rel = "manifest";
			link.id = "manifest";
			document.head.appendChild(link);
		}
		var href = manifestHref();
		if (link.getAttribute("href") !== href) { link.href = href; }
	}

	function setupPwa() {
		ensureManifestLink();
		if (pwaStandalone()) { document.documentElement.classList.add("pwa-standalone"); }
		/* There is no install button: over plain http the browser cannot install
		 * anything and "add to home screen" only stores a bookmark. The header
		 * keeps the page-fullscreen button instead. */
		if (els.maximize) {
			els.maximize.addEventListener("click", toggleAppFullscreen);
			syncMaximize();
		}
		window.addEventListener("online", updateNet);
		window.addEventListener("offline", updateNet);
		updateNet();
		registerServiceWorker();
	}

	/* ---------------------------------------------------------- preferences
	 * Titles, default fullscreen mode and the configuration link are page
	 * preferences (browser only, never sent to the daemon). */
	function textRow(id, caption, value, placeholder, onInput) {
		var row = document.createElement("label");
		var text = document.createElement("span");
		text.textContent = caption;
		var input = document.createElement("input");
		input.type = "text";
		input.id = id;
		input.maxLength = 60;
		input.value = value || "";
		input.placeholder = placeholder || "";
		input.addEventListener("input", function () { onInput(input.value.trim()); });
		row.appendChild(text);
		row.appendChild(input);
		return row;
	}

	function checkRow(id, caption, checked, onChange) {
		var row = document.createElement("label");
		row.className = "pcheck";
		var input = document.createElement("input");
		input.type = "checkbox";
		input.id = id;
		input.checked = checked === true;
		input.addEventListener("change", function () { onChange(input.checked); });
		var text = document.createElement("span");
		text.textContent = caption;
		row.appendChild(input);
		row.appendChild(text);
		return row;
	}

	function hintRow(text) {
		var hint = document.createElement("p");
		hint.className = "phelphint";
		hint.textContent = text;
		return hint;
	}

	function applyTheme() {
		var dark = state.settings.theme === "dark" || (state.settings.theme === "system" &&
			window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
		document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
		var metas = document.querySelectorAll('meta[name="theme-color"]');
		for (var index = 0; index < metas.length; index++) {
			metas[index].content = dark ? "#12161c" : "#0b6bcb";
		}
	}

	function ensurePrefs() {
		if (els.prefsbox) { return; }
		if (els.prefs) {
			els.prefs.title = t("prefsTitle");
			els.prefs.setAttribute("aria-label", t("prefsTitle"));
			els.prefs.addEventListener("click", openPrefs);
		}
		var box = document.createElement("dialog");
		box.className = "phelp psettings";
		box.id = "prefsbox";
		var head = document.createElement("h3");
		head.textContent = t("prefsTitle");
		box.appendChild(head);
		var body = document.createElement("div");
		body.className = "psettingsbody";
		body.appendChild(selectRow("preftheme", t("prefTheme"), [
			["system", t("themeSystem")], ["light", t("themeLight")], ["dark", t("themeDark")]
		], state.settings.theme, function (value) {
			state.settings.theme = value;
			settingsWrite();
			applyTheme();
			render();
		}));
		body.appendChild(textRow("preftitle", t("prefTitle"), state.settings.title, DEFAULT_TITLE, function (value) {
			state.settings.title = value;
			settingsWrite();
			renderHeader();
		}));
		body.appendChild(textRow("prefsubtitle", t("prefSubtitle"), state.settings.subtitle, t("subtitle"), function (value) {
			state.settings.subtitle = value;
			settingsWrite();
			renderHeader();
		}));
		body.appendChild(hintRow(t("prefHint")));
		body.appendChild(checkRow("preffullscreen", t("prefFullscreen"), state.settings.fullscreen, function (checked) {
			state.settings.fullscreen = checked;
			settingsWrite();
			if (checked) { armAutoFullscreen(); } else if (appFullscreenOn()) { toggleAppFullscreen(); }
		}));
		body.appendChild(hintRow(t("prefFullscreenHint")));
		body.appendChild(checkRow("prefmaximize", t("prefMaximize"), state.settings.showMaximize !== false, function (checked) {
			state.settings.showMaximize = checked;
			settingsWrite();
			syncMaximize();
		}));
		body.appendChild(checkRow("prefconfig", t("prefConfig"), state.settings.showConfig !== false, function (checked) {
			state.settings.showConfig = checked;
			settingsWrite();
			renderHeader();
		}));
		body.appendChild(checkRow("prefshowkpis", t("prefShowKpis"), state.settings.showKpis !== false, function (checked) {
			state.settings.showKpis = checked;
			settingsWrite();
			render();
		}));
		/* Lock of the layout: a wall display or a shared browser should not be
		 * rearranged by a tap on a cross or an arrow. The lock lives here, so
		 * the same dialog that locks it also unlocks it. */
		body.appendChild(checkRow("prefuilock", t("prefUiLock"), state.settings.uiLocked === true, function (checked) {
			state.settings.uiLocked = checked;
			settingsWrite();
			render();
		}));
		body.appendChild(hintRow(t("prefUiLockHint")));
		body.appendChild(checkRow("prefsplitlock", t("prefSplitLock"), state.settings.splitLocked === true, function (checked) {
			state.settings.splitLocked = checked;
			settingsWrite();
			render();
		}));
		body.appendChild(hintRow(t("prefSplitLockHint")));
		/* The elements of the main window can be hidden and shown here, like the
		 * charts in the chart options: one list per kind. */
		[["prefkpis", t("prefKpis")],
		 ["prefsensors", t("prefSensors")],
		 ["prefboxes", t("prefBoxes")]].forEach(function (section) {
			var head = document.createElement("p");
			head.className = "psettingsgroup";
			head.textContent = section[1];
			body.appendChild(head);
			var list = document.createElement("div");
			list.className = "ppanels";
			list.id = section[0];
			body.appendChild(list);
		});
		var hidden = document.createElement("p");
		hidden.className = "phelphint";
		hidden.id = "prefhidden";
		body.appendChild(hidden);
		var reset = document.createElement("button");
		reset.type = "button";
		reset.className = "pwide";
		reset.textContent = t("prefResetHidden");
		reset.addEventListener("click", function () {
			state.settings.hiddenSeries = [];
			state.settings.hiddenPanels = [];
			state.settings.hiddenDevices = [];
			state.settings.hiddenKpis = [];
			state.settings.showKpis = true;
			settingsWrite();
			render();
		});
		body.appendChild(reset);
		box.appendChild(body);
		var form = document.createElement("form");
		form.method = "dialog";
		var close = document.createElement("button");
		close.type = "submit";
		close.textContent = t("helpClose");
		form.appendChild(close);
		box.appendChild(form);
		document.body.appendChild(box);
		els.prefsbox = box;
		renderPrefs();
	}

	function openPrefs() {
		if (!els.prefsbox) { return; }
		renderPrefs();
		if (typeof els.prefsbox.showModal === "function") {
			els.prefsbox.showModal();
		} else {
			els.prefsbox.setAttribute("open", "");
		}
	}

	function renderPrefs() {
		var box = els.prefsbox;
		if (!box) { return; }
		var title = box.querySelector("#preftitle");
		var subtitle = box.querySelector("#prefsubtitle");
		var fullscreen = box.querySelector("#preffullscreen");
		var config = box.querySelector("#prefconfig");
		var maximize = box.querySelector("#prefmaximize");
		var hidden = box.querySelector("#prefhidden");
		var theme = box.querySelector("#preftheme");
		if (theme) { theme.value = state.settings.theme; }
		if (title) { title.value = state.settings.title; title.placeholder = DEFAULT_TITLE; }
		if (subtitle) { subtitle.value = state.settings.subtitle; }
		if (fullscreen) { fullscreen.checked = state.settings.fullscreen === true; }
		if (config) { config.checked = state.settings.showConfig !== false; }
		if (maximize) { maximize.checked = state.settings.showMaximize !== false; }
		var showKpis = box.querySelector("#prefshowkpis");
		if (showKpis) { showKpis.checked = state.settings.showKpis !== false; }
		if (hidden) {
			hidden.textContent = t("prefHidden", {
				n: state.settings.hiddenSeries.length,
				m: state.settings.hiddenPanels.length,
				k: state.settings.hiddenDevices.length
			});
		}
		fillChoices(box.querySelector("#prefkpis"), kpiChoices());
		fillChoices(box.querySelector("#prefsensors"), deviceChoices());
		fillChoices(box.querySelector("#prefboxes"), seriesChoices());
		var lock = box.querySelector("#prefuilock");
		if (lock) { lock.checked = state.settings.uiLocked === true; }
		var splitLock = box.querySelector("#prefsplitlock");
		if (splitLock) { splitLock.checked = state.settings.splitLocked === true; }
		lockPrefs();
	}

	/** While the layout is locked every control of the dialog is read-only
	 *  except the lock itself and the close button: otherwise the lock could be
	 *  bypassed from here (or from the lists that hide the widgets). */
	function lockPrefs() {
		var box = els.prefsbox;
		if (!box) { return; }
		var locked = uiLocked();
		var controls = box.querySelectorAll("input, button");
		for (var index = 0; index < controls.length; index++) {
			var control = controls[index];
			if (control.id === "prefuilock" || control.id === "prefsplitlock" || control.type === "submit") { continue; }
			control.disabled = locked;
		}
	}

	/** One checkbox per element of a list: checked means visible. */
	function fillChoices(container, choices) {
		if (!container) { return; }
		container.textContent = "";
		if (!choices.length) {
			var none = document.createElement("p");
			none.className = "phelphint";
			none.textContent = t("prefNoItems");
			container.appendChild(none);
			return;
		}
		choices.forEach(function (choice) {
			var row = document.createElement("label");
			row.className = "pcheck";
			var input = document.createElement("input");
			input.type = "checkbox";
			input.checked = choice.visible;
			input.addEventListener("change", function () { choice.toggle(input.checked); });
			var text = document.createElement("span");
			text.textContent = choice.label;
			row.appendChild(input);
			row.appendChild(text);
			container.appendChild(row);
		});
	}

	function kpiChoices() {
		return kpiItems().map(function (item) {
			return {
				label: item.label,
				visible: state.settings.hiddenKpis.indexOf(item.key) < 0,
				toggle: function (visible) {
					if (visible) { listRemove(state.settings.hiddenKpis, item.key); }
					else { listAdd(state.settings.hiddenKpis, item.key); }
					settingsWrite();
					render();
				}
			};
		});
	}

	function deviceChoices() {
		var catalog = state.catalog;
		if (!catalog || !catalog.devices) { return []; }
		return catalog.devices.map(function (device) {
			return {
				label: device.label || device.name || device.mac,
				visible: !isHiddenDevice(device.mac),
				toggle: function (visible) {
					if (visible) { listRemove(state.settings.hiddenDevices, device.mac); }
					else { listAdd(state.settings.hiddenDevices, device.mac); }
					settingsWrite();
					render();
				}
			};
		});
	}

	function seriesChoices() {
		var catalog = state.catalog;
		if (!catalog || !catalog.devices) { return []; }
		var choices = [];
		catalog.devices.forEach(function (device) {
			(device.series || []).forEach(function (series) {
				var key = keyOf(device.mac, series);
				var unit = series.unit ? " (" + series.unit + ")" : "";
				choices.push({
					label: (device.label || device.name || device.mac) + " \u00b7 " + series.attribute + unit,
					visible: !isHiddenSeries(key),
					toggle: function (visible) {
						if (visible) { listRemove(state.settings.hiddenSeries, key); }
						else { listAdd(state.settings.hiddenSeries, key); }
						settingsWrite();
						render();
					}
				});
			});
		});
		return choices;
	}

	/* ------------------------------------------------ hidden boxes and charts
	 * Hiding is a display choice of this browser: the data stays in the
	 * database and the series stay selected for the charts that are visible. */
	function isHiddenSeries(key) {
		return state.settings.hiddenSeries.indexOf(key) >= 0;
	}

	function hideSeries(key) {
		if (uiLocked()) { return; }
		listAdd(state.settings.hiddenSeries, key);
		settingsWrite();
		render();
	}

	function showSeries(keys) {
		keys.forEach(function (key) { listRemove(state.settings.hiddenSeries, key); });
		settingsWrite();
		render();
	}

	function hidePanel(key) {
		if (uiLocked()) { return; }
		listAdd(state.settings.hiddenPanels, key);
		settingsWrite();
		render();
	}

	function isHiddenDevice(mac) {
		return state.settings.hiddenDevices.indexOf(mac) >= 0;
	}

	function hideDevice(mac) {
		if (uiLocked()) { return; }
		listAdd(state.settings.hiddenDevices, mac);
		settingsWrite();
		render();
	}

	function showDevices(macs) {
		macs.forEach(function (mac) { listRemove(state.settings.hiddenDevices, mac); });
		settingsWrite();
		render();
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
			maximize: document.getElementById("maximize"),
			prefs: document.getElementById("prefs"),
			title: document.getElementById("title"),
			subtitle: document.getElementById("subtitle"),
			config: document.getElementById("config"),
	
			netstate: document.getElementById("netstate"),
			helplink: document.getElementById("helplink"),
			helpbox: document.getElementById("helpbox"),
			helptitle: document.getElementById("helptitle"),
			helpbody: document.getElementById("helpbody"),
			helpnote: document.getElementById("helpnote"),
			helpclose: document.getElementById("helpclose")
		};
		pickLanguage();
		document.documentElement.lang = lang;
		settingsRead();
		applyTheme();
		if (window.matchMedia) {
			var themeMedia = window.matchMedia("(prefers-color-scheme: dark)");
			var themeChanged = function () {
				if (state.settings.theme !== "system") { return; }
				applyTheme();
				render();
			};
			if (themeMedia.addEventListener) { themeMedia.addEventListener("change", themeChanged); }
			else if (themeMedia.addListener) { themeMedia.addListener(themeChanged); }
		}
		if (els.title) { DEFAULT_TITLE = els.title.textContent; }
		ensurePrefs();
		if (state.settings.fullscreen) { armAutoFullscreen(); }
		setupPwa();
		restoreStore();
		ensureSplitter();
		ensureChartHost();
		orderRead();
		if (els.resetview) {
			els.resetview.title = t("resetView");
			els.resetview.addEventListener("click", resetView);
		}
		document.getElementById("reload").addEventListener("click", function () { loadCatalog(true, true); });
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
		ensureFirstLoad();
		updateBusy();
		/* Safety net: a stalled request must never hide the page for good. */
		window.setTimeout(revealPage, 20000);
		loadCatalog(false, true);
		/* The periodic refresh skips the database statistics: they do not change
		 * between two refreshes and cost the router seconds of disk access. */
		window.setInterval(function () { loadCatalog(true, false); }, REFRESH_MS);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start);
	} else {
		start();
	}
})();
