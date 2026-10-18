#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type" it:"Tipo di avvio" fr:"Type de demarrage" es:"Tipo de inicio")"
cgi_print_radiogroup_service_starttype enabled "$GRAFANA_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Weboberflaeche" en:"Web interface" it:"Interfaccia web" fr:"Interface web" es:"Interfaz web")"
cat << EOF
<p><a id="grafana-open" href="#" data-port="$(html "$GRAFANA_PORT")" target="_blank" rel="noopener noreferrer">Grafana</a></p>
<script>
(function () {
	var link = document.getElementById('grafana-open');
	var address = new URL(window.location.href);
	address.protocol = 'http:';
	address.port = link.getAttribute('data-port');
	address.pathname = '/';
	address.search = '';
	address.hash = '';
	link.href = address.href;
})();
</script>
EOF
sec_end

sec_begin "Grafana"
cat << EOF
<p><label>$(lang de:"Datenverzeichnis" en:"Storage directory" it:"Directory dati" fr:"Repertoire des donnees" es:"Directorio de datos")<br>
<input type="text" name="basedir" size="55" value="$(html "$GRAFANA_BASEDIR")"></label></p>
<p><label>$(lang de:"Bind-Adresse" en:"Bind address" it:"Indirizzo di ascolto" fr:"Adresse d'ecoute" es:"Direccion de escucha")
<input type="text" name="bind" size="16" value="$(html "$GRAFANA_BIND")"></label></p>
<p><label>$(lang de:"Port" en:"Port" it:"Porta" fr:"Port" es:"Puerto")
<input type="number" name="port" min="1024" max="65535" value="$(html "$GRAFANA_PORT")"></label></p>
<p><label>$(lang de:"Prioritaet (nice)" en:"Priority (nice)" it:"Priorita (nice)" fr:"Priorite (nice)" es:"Prioridad (nice)")
<input type="number" name="nice" min="0" max="19" value="$(html "$GRAFANA_NICE")"></label></p>
<p><label>$(lang de:"Start-Wartezeit (Sekunden)" en:"Boot wait (seconds)" it:"Attesa avvio (secondi)" fr:"Attente au demarrage (secondes)" es:"Espera al inicio (segundos)")
<input type="number" name="config_wait" min="0" max="600" value="$(html "$GRAFANA_CONFIG_WAIT")"></label></p>
EOF
sec_end