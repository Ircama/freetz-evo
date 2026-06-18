default_password_set() {
	# Check legacy Basic Auth password (MOD_HTTPD_PASSWD)
	[ "$MOD_HTTPD_PASSWD" == '$1$$zO6d3zi9DefdWLMB.OHaO.' ] && return 0
	# Check form-based login password (/tmp/flash/mod/webmd5) when available
	[ -f /tmp/flash/mod/webmd5 ] && \
		[ "$(cat /tmp/flash/mod/webmd5 | tr -d '\n')" = "465d0ff27bb239292778dc3a0c2f28d9" ] && return 0
	return 1
}

if default_password_set; then
	print_warning "$(lang \
	  de:"Standard-Passwort gesetzt. <a href=\"/cgi-bin/passwd.cgi\">Bitte &auml;ndern!</a> " \
	  en:"Default password set. <a href=\"/cgi-bin/passwd.cgi\">Please change!</a>" \
	)"
fi
