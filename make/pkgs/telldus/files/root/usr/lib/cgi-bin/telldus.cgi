#!/bin/sh

. /usr/lib/libmodcgi.sh

sec_begin "$(lang de:"Starttyp" en:"Start type")"
cgi_print_radiogroup_service_starttype "enabled" "$TELLDUS_ENABLED" "" "" 0
sec_end

sec_begin "$(lang de:"Konfiguration" en:"Configuration")"
cat << EOF
<p>$(lang de:"Datei" en:"File"): <code>/mod/etc/conf/tellstick.conf</code></p>
<p>$(lang de:"Aufbau wie in /etc/tellstick.conf: Controller und Geraete in der Syntax von libconfuse. Die Zeilen fuer user und group sind Pflicht." en:"Same layout as /etc/tellstick.conf: controllers and devices in libconfuse syntax. The user and group lines are mandatory.")</p>
<textarea name="devices" cols="90" rows="14" wrap="off">$(html "$TELLDUS_DEVICES")</textarea>
EOF
sec_end

sec_begin "$(lang de:"Erweitert" en:"Advanced")"
cgi_print_radiogroup_active "debug" "$TELLDUS_DEBUG" "" "$(lang de:"Debug-Protokoll (telldusd --debug)" en:"Debug logging (telldusd --debug)")"
cat << EOF
<p>$(lang de:"Zusaetzliche Kommandozeilenoptionen" en:"Additional command line options"): <input type="text" name="extra_args" size="60" maxlength="255" value="$(html "$TELLDUS_EXTRA_ARGS")"></p>
EOF
sec_end

sec_begin "$(lang de:"Hinweise" en:"Notes")"
cat << EOF
<p>$(lang de:"tdtool ist die Kommandozeile des Daemons" en:"tdtool is the command line client of the daemon"): <code>tdtool --list</code></p>
<p>$(lang de:"Domoticz erreicht den Daemon ueber den Unix-Socket" en:"Domoticz reaches the daemon through the unix socket"): <code>TelldusClient</code></p>
<p>$(lang de:"Protokoll" en:"Log"): <code>/tmp/rc.telldus.log</code></p>
<p>$(lang de:"Der Tellstick muss als USB-Geraet erkannt werden" en:"The Tellstick has to be recognised as a USB device"): <code>dmesg</code></p>
EOF
sec_end
