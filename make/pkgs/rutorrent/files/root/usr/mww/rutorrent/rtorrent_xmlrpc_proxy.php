<?php
/**
 * rtorrent XMLRPC Proxy
 * 
 * Exposes HTTP/XMLRPC endpoint and translates requests to SCGI protocol
 * for communication with rtorrent daemon.
 * 
 * This proxy allows standard XMLRPC clients to communicate with rtorrent
 * which uses SCGI transport instead of HTTP.
 * 
 * @author freetz-ng
 * @license GPL-2.0
 */

$_webcfgAuth = '';
if (is_readable('/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/usr/lib/php/webcfg_auth.php';
} elseif (is_readable('/mod/external/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/mod/external/usr/lib/php/webcfg_auth.php';
}
if ($_webcfgAuth !== '') {
    require_once $_webcfgAuth;
    $subpage = 'rutorrent/';
    $loginUrl = '/cgi-bin/conf/rtorrent?subpage=rutorrent/';
    webcfg_require_auth(array('mode' => 'redirect', 'subpage' => $subpage, 'login_url' => $loginUrl));
}

// Configuration
// Traditional SCGI ports are 5000 or 5555, but 16891 avoids conflicts with Flask, Docker, UPnP, etc.
define('RTORRENT_SCGI_HOST', '127.0.0.1');
define('RTORRENT_SCGI_PORT', 16891);  // High port unlikely to conflict with other services
define('RTORRENT_SCGI_TIMEOUT_DEFAULT', $_ENV['RTORRENT_SCGI_TIMEOUT'] ?? 10);  // Configurable via env or default 10 seconds
define('DEBUG_MODE', false);  // Set to true to enable logging

/**
 * Get timeout value with validation
 * Can be overridden via query parameter ?timeout=30
 * 
 * @return int Validated timeout in seconds (1-300)
 */
function get_timeout() {
    // Check query parameter override
    if (isset($_GET['timeout'])) {
        $timeout = filter_var($_GET['timeout'], FILTER_VALIDATE_INT);
        if ($timeout !== false && $timeout >= 1 && $timeout <= 300) {
            return $timeout;
        }
    }
    // Use default/env value
    $timeout = RTORRENT_SCGI_TIMEOUT_DEFAULT;
    return max(1, min(300, (int)$timeout));
}

/**
 * Send SCGI request to rtorrent
 * 
 * @param string $host SCGI host
 * @param int $port SCGI port
 * @param string $request XMLRPC request XML
 * @param int $timeout Connection timeout in seconds
 * @return string SCGI response
 * @throws Exception on connection/communication errors
 */
function scgi_request($host, $port, $request, $timeout = 10) {
    $sock = @fsockopen($host, $port, $errno, $errstr, $timeout);
    if (!$sock) {
        throw new Exception("Cannot connect to rtorrent SCGI at {$host}:{$port} - {$errstr} (errno: {$errno})");
    }
    
    // Set socket timeout
    stream_set_timeout($sock, $timeout);
    
    // Build SCGI netstring
    $content_length = strlen($request);
    $scgi_headers = "CONTENT_LENGTH\0{$content_length}\0SCGI\x001\0";
    $netstring = strlen($scgi_headers) . ":" . $scgi_headers . "," . $request;
    
    // Send request
    $bytes_written = fwrite($sock, $netstring);
    if ($bytes_written === false || $bytes_written < strlen($netstring)) {
        fclose($sock);
        throw new Exception("Failed to send complete SCGI request");
    }
    
    // Read response
    $response = stream_get_contents($sock);
    $meta = stream_get_meta_data($sock);
    fclose($sock);
    
    if ($meta['timed_out']) {
        throw new Exception("SCGI request timed out after {$timeout} seconds");
    }
    
    if ($response === false) {
        throw new Exception("Failed to read SCGI response");
    }
    
    return $response;
}

/**
 * Extract XMLRPC response from SCGI response
 * 
 * @param string $scgi_response Full SCGI response with headers
 * @return string XMLRPC XML response
 */
function extract_xmlrpc_from_scgi($scgi_response) {
    // SCGI responses have HTTP-like headers followed by XML
    // Find the start of XML (<?xml or <methodResponse)
    $xml_markers = array('<?xml', '<methodResponse', '<methodCall');
    
    foreach ($xml_markers as $marker) {
        $pos = strpos($scgi_response, $marker);
        if ($pos !== false) {
            return substr($scgi_response, $pos);
        }
    }
    
    // If no XML markers found, try to extract after double newline
    $pos = strpos($scgi_response, "\r\n\r\n");
    if ($pos !== false) {
        return trim(substr($scgi_response, $pos + 4));
    }
    
    // Last resort: return as-is
    return $scgi_response;
}

/**
 * Send XMLRPC error response
 * 
 * @param int $code Fault code
 * @param string $message Fault message
 */
function send_xmlrpc_error($code, $message) {
    header('Content-Type: text/xml; charset=utf-8');
    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
    echo '<methodResponse>' . "\n";
    echo '<fault>' . "\n";
    echo '<value><struct>' . "\n";
    echo '<member><name>faultCode</name><value><int>' . intval($code) . '</int></value></member>' . "\n";
    echo '<member><name>faultString</name><value><string>' . htmlspecialchars($message, ENT_XML1, 'UTF-8') . '</string></value></member>' . "\n";
    echo '</struct></value>' . "\n";
    echo '</fault>' . "\n";
    echo '</methodResponse>' . "\n";
}

/**
 * Log debug message
 * 
 * @param string $message Message to log
 */
function debug_log($message) {
    if (DEBUG_MODE) {
        error_log('[rtorrent_xmlrpc_proxy] ' . $message);
    }
}

// Main execution
try {
    // Handle GET requests (info page)
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        header('Content-Type: text/html; charset=utf-8');
        ?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>rtorrent XMLRPC Proxy</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .info { background: #e7f3ff; padding: 10px; border-left: 4px solid #007bff; margin: 20px 0; }
        .success { background: #d4edda; padding: 10px; border-left: 4px solid #28a745; margin: 20px 0; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
    </style>
</head>
<body>
    <h1>rtorrent XMLRPC Proxy</h1>
    
    <div class="success">
        <strong>✓ Proxy is running</strong><br>
        SCGI Target: <?php echo htmlspecialchars(RTORRENT_SCGI_HOST . ':' . RTORRENT_SCGI_PORT); ?>
    </div>
    
    <div class="info">
        <strong>ℹ Information</strong><br>
        This proxy translates HTTP/XMLRPC requests to SCGI protocol for rtorrent.
    </div>
    
    <h2>Usage</h2>
    <p>POST XMLRPC requests to this endpoint using any XMLRPC client library.</p>
    
    <h3>Command Line Example</h3>
    <pre>xmlrpc <?php echo htmlspecialchars('http://' . $_SERVER['HTTP_HOST'] . $_SERVER['SCRIPT_NAME']); ?> system.client_version</pre>
    
    <h3>With Authentication</h3>
    <pre>xmlrpc --user admin --password yourpass \
  <?php echo htmlspecialchars('http://' . $_SERVER['HTTP_HOST'] . $_SERVER['SCRIPT_NAME']); ?> \
  system.client_version</pre>
    
    <h3>Query Torrents</h3>
    <pre>xmlrpc <?php echo htmlspecialchars('http://' . $_SERVER['HTTP_HOST'] . $_SERVER['SCRIPT_NAME']); ?> \
  d.multicall2 '' main d.name= d.size_bytes= --user admin --password yourpass</pre>
    
    <h3>Custom Timeout</h3>
    <p>Add <code>?timeout=N</code> parameter for longer operations (1-300 seconds):</p>
    <pre>xmlrpc <?php echo htmlspecialchars('http://' . $_SERVER['HTTP_HOST'] . $_SERVER['SCRIPT_NAME'] . '?timeout=30'); ?> \
  system.client_version --user admin --password yourpass</pre>
    
    <h2>Supported Methods</h2>
    <ul>
        <li><code>system.client_version</code> - Get rtorrent version</li>
        <li><code>system.hostname</code> - Get system hostname</li>
        <li><code>system.pid</code> - Get rtorrent PID</li>
        <li><code>download_list</code> - List torrent hashes</li>
        <li><code>d.multicall2</code> - Query multiple torrent properties</li>
        <li>And all other rtorrent XMLRPC methods...</li>
    </ul>
    
    <h2>Technical Details</h2>
    <ul>
        <li><strong>Transport:</strong> HTTP/XMLRPC → SCGI</li>
        <li><strong>Timeout:</strong> <?php echo get_timeout(); ?> seconds (default: <?php echo RTORRENT_SCGI_TIMEOUT_DEFAULT; ?>, configurable via <code>?timeout=30</code>)</li>
        <li><strong>Character Encoding:</strong> UTF-8</li>
    </ul>
</body>
</html>
        <?php
        exit(0);
    }
    
    // Handle POST requests (XMLRPC)
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        http_response_code(405);
        send_xmlrpc_error(-32600, 'Only POST requests are supported for XMLRPC calls');
        exit(1);
    }
    
    // Read raw POST data
    $raw_request = file_get_contents('php://input');
    
    if (empty($raw_request)) {
        send_xmlrpc_error(-32600, 'Empty request body');
        exit(1);
    }
    
    debug_log("Received request: " . strlen($raw_request) . " bytes");
    
    // Validate XMLRPC request format
    if (strpos($raw_request, '<methodCall>') === false) {
        send_xmlrpc_error(-32600, 'Invalid XMLRPC request: missing <methodCall>');
        exit(1);
    }
    
    // Forward request to rtorrent via SCGI
    try {
        $timeout = get_timeout();
        $scgi_response = scgi_request(RTORRENT_SCGI_HOST, RTORRENT_SCGI_PORT, $raw_request, $timeout);
        debug_log("Received SCGI response: " . strlen($scgi_response) . " bytes");
        
        // Extract XMLRPC from SCGI response
        $xmlrpc_response = extract_xmlrpc_from_scgi($scgi_response);
        
        // Validate response
        if (empty($xmlrpc_response)) {
            throw new Exception("Empty response from rtorrent");
        }
        
        if (strpos($xmlrpc_response, '<methodResponse>') === false && 
            strpos($xmlrpc_response, '<?xml') === false) {
            throw new Exception("Invalid XMLRPC response from rtorrent");
        }
        
        // Send response
        header('Content-Type: text/xml; charset=utf-8');
        header('Content-Length: ' . strlen($xmlrpc_response));
        echo $xmlrpc_response;
        
        debug_log("Response sent successfully");
        
    } catch (Exception $e) {
        debug_log("Error: " . $e->getMessage());
        send_xmlrpc_error(-1, $e->getMessage());
        exit(1);
    }
    
} catch (Exception $e) {
    error_log('[rtorrent_xmlrpc_proxy] Fatal error: ' . $e->getMessage());
    send_xmlrpc_error(-32603, 'Internal proxy error: ' . $e->getMessage());
    exit(1);
}

