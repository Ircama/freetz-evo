#!/bin/sh

if echo "&${QUERY_STRING}&" | grep -q '&hash='; then
	source /usr/mww/cgi-bin/login_check.sh
else
	source /usr/mww/cgi-bin/login_page.sh
fi

