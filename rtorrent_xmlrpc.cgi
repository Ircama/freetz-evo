#!/bin/sh
#
# rtorrent XMLRPC Proxy CGI
# Exposes HTTP/XMLRPC endpoint and translates to SCGI
#

RTORRENT_HOST="127.0.0.1"
RTORRENT_PORT="5000"

# Read POST data
read_post_data() {
	if [ "$REQUEST_METHOD" = "POST" ]; then
		if [ -n "$CONTENT_LENGTH" ]; then
			dd bs=1 count=$CONTENT_LENGTH 2>/dev/null
		else
			cat
		fi
	fi
}

# Extract method name from XMLRPC request
extract_method() {
	sed -n 's/.*<methodName>\([^<]*\)<\/methodName>.*/\1/p'
}

# Extract first string parameter
extract_param() {
	sed -n 's/.*<string>\([^<]*\)<\/string>.*/\1/p' | head -1
}

# Send SCGI request using netcat
scgi_call() {
	local method="$1"
	local xmlrpc_request="<?xml version=\"1.0\"?><methodCall><methodName>$method</methodName></methodCall>"
	local content_length=${#xmlrpc_request}
	
	# Build SCGI netstring
	local scgi_headers="CONTENT_LENGTH\0${content_length}\0SCGI\x001\0"
	local header_length=${#scgi_headers}
	
	# Use printf to handle binary data
	(
		printf "%d:%s," "$header_length" "$scgi_headers"
		printf "%s" "$xmlrpc_request"
	) | nc -w 5 "$RTORRENT_HOST" "$RTORRENT_PORT" 2>/dev/null
}

# Main logic
if [ "$REQUEST_METHOD" = "GET" ]; then
	# Show info page
	cat << 'EOF'
Content-Type: text/html

<!DOCTYPE html>
<html>
<head><title>rtorrent XMLRPC Proxy</title></head>
<body>
<h1>rtorrent XMLRPC Proxy (httpd-webcfg)</h1>
<p>POST XMLRPC requests to this endpoint.</p>
<p>Example:</p>
<pre>xmlrpc http://fritz.box/cgi-bin/rtorrent_xmlrpc.cgi system.client_version</pre>
<p>This CGI script translates HTTP/XMLRPC requests to SCGI calls to rtorrent.</p>
</body>
</html>
EOF
	exit 0
fi

# Handle POST (XMLRPC request)
POST_DATA=$(read_post_data)

if [ -z "$POST_DATA" ]; then
	cat << 'EOF'
Content-Type: text/xml

<?xml version="1.0"?>
<methodResponse>
<fault>
<value><struct>
<member><name>faultCode</name><value><int>-1</int></value></member>
<member><name>faultString</name><value><string>Empty request</string></value></member>
</struct></value>
</fault>
</methodResponse>
EOF
	exit 0
fi

# Extract method name
METHOD=$(echo "$POST_DATA" | extract_method)

if [ -z "$METHOD" ]; then
	cat << 'EOF'
Content-Type: text/xml

<?xml version="1.0"?>
<methodResponse>
<fault>
<value><struct>
<member><name>faultCode</name><value><int>-1</int></value></member>
<member><name>faultString</name><value><string>Invalid XMLRPC request</string></value></member>
</struct></value>
</fault>
</methodResponse>
EOF
	exit 0
fi

# Check if netcat is available
if ! command -v nc >/dev/null 2>&1; then
	cat << 'EOF'
Content-Type: text/xml

<?xml version="1.0"?>
<methodResponse>
<fault>
<value><struct>
<member><name>faultCode</name><value><int>-1</int></value></member>
<member><name>faultString</name><value><string>netcat not available</string></value></member>
</struct></value>
</fault>
</methodResponse>
EOF
	exit 0
fi

# Call rtorrent via SCGI
RESPONSE=$(scgi_call "$METHOD")

if [ -z "$RESPONSE" ]; then
	cat << 'EOF'
Content-Type: text/xml

<?xml version="1.0"?>
<methodResponse>
<fault>
<value><struct>
<member><name>faultCode</name><value><int>-1</int></value></member>
<member><name>faultString</name><value><string>Failed to connect to rtorrent</string></value></member>
</struct></value>
</fault>
</methodResponse>
EOF
	exit 0
fi

# Extract XML from SCGI response (skip headers)
XML_RESPONSE=$(echo "$RESPONSE" | sed -n '/<\?xml/,$p')

# Return XMLRPC response
echo "Content-Type: text/xml"
echo ""
echo "$XML_RESPONSE"
