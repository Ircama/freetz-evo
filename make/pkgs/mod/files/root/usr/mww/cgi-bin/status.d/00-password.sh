default_password_set() {
	# Form-based login (MOD_HTTPD_NEWLOGIN=yes): the effective password is
	# /tmp/flash/mod/webmd5. MOD_HTTPD_PASSWD may be stale (legacy Basic Auth
	# hash not updated by all password-change paths), so only trust webmd5.
	if [ "$MOD_HTTPD_NEWLOGIN" = "yes" ]; then
		[ -f /tmp/flash/mod/webmd5 ] && \
			[ "$(cat /tmp/flash/mod/webmd5 | tr -d '\n')" = "465d0ff27bb239292778dc3a0c2f28d9" ] && return 0
		return 1
	fi
	# Legacy Basic Auth mode: check MOD_HTTPD_PASSWD (and webmd5 as fallback)
	[ "$MOD_HTTPD_PASSWD" == '$1$$zO6d3zi9DefdWLMB.OHaO.' ] && return 0
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
