<?php
/**
 * PHP Diagnostics Script for ruTorrent/rTorrent
 * URL: http://fritz.box:81/rutorrent/php-info.php
 */
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html>
<head>
    <title>PHP Diagnostics - ruTorrent on Freetz-NG</title>
    <style>
        body { font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }
        h1 { color: #4ec9b0; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
        h2 { color: #569cd6; margin-top: 30px; }
        .ok { color: #16825d; font-weight: bold; }
        .error { color: #c72e0f; font-weight: bold; }
        .warning { color: #e5a50a; font-weight: bold; }
        .info { color: #3794ff; }
        .section { background: #252526; padding: 15px; margin: 10px 0; border-left: 3px solid #007acc; }
        pre { background: #1e1e1e; padding: 10px; overflow-x: auto; border: 1px solid #3e3e42; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border: 1px solid #3e3e42; }
        th { background: #2d2d30; color: #4ec9b0; }
        .test-ok { background: #1a3a2e; }
        .test-fail { background: #3a1a1a; }
    </style>
</head>
<body>
    <h1>🔧 PHP Diagnostics for ruTorrent</h1>
    
    <div class="section">
        <h2>📋 PHP Version</h2>
        <p><strong>Version:</strong> <?php echo PHP_VERSION; ?></p>
        <p><strong>SAPI:</strong> <?php echo php_sapi_name(); ?></p>
        <p><strong>Build:</strong> <?php echo php_uname(); ?></p>
    </div>
    
    <div class="section">
        <h2>🔐 TLS / HTTPS Support (detailed)</h2>
        <?php
        $openssl_loaded = extension_loaded('openssl');
        $curl_loaded = extension_loaded('curl');
        $stream_transports = function_exists('stream_get_transports') ? stream_get_transports() : [];
        $stream_wrappers = function_exists('stream_get_wrappers') ? stream_get_wrappers() : [];
        $curl_binary = trim(@shell_exec('which curl 2>/dev/null')) ?: false;
        $curl_bin_version = $curl_binary ? trim(@shell_exec(escapeshellcmd($curl_binary) . ' --version 2>/dev/null')) : '';
        $curl_info = $curl_loaded && function_exists('curl_version') ? curl_version() : null;
        ?>
        <table>
            <tr><th>Feature</th><th>Status</th><th>Details</th></tr>
            <tr class="<?php echo $curl_loaded ? 'test-ok' : 'test-fail'; ?>">
                <td>PHP cURL extension</td>
                <td><?php echo $curl_loaded ? '<span class="ok">✓ Loaded</span>' : '<span class="warning">⚠️ Not loaded</span>'; ?></td>
                <td><?php
                    if ($curl_info) {
                        echo 'libcurl: ' . htmlspecialchars($curl_info['version']) . ' — SSL: ' . htmlspecialchars($curl_info['ssl_version']);
                    } else {
                        echo 'PHP cURL not available';
                    }
                ?></td>
            </tr>
            <tr class="<?php echo in_array('ssl', $stream_transports) || in_array('tls', $stream_transports) ? 'test-ok' : 'test-fail'; ?>">
                <td>PHP stream TLS transports</td>
                <td><?php echo (in_array('ssl', $stream_transports) || in_array('tls', $stream_transports)) ? '<span class="ok">✓ Available</span>' : '<span class="warning">⚠️ Not available</span>'; ?></td>
                <td><?php echo 'Transports: ' . htmlspecialchars(implode(', ', $stream_transports)); ?></td>
            </tr>
            <tr class="<?php echo $curl_binary ? 'test-ok' : 'test-fail'; ?>">
                <td>System curl binary</td>
                <td><?php echo $curl_binary ? '<span class="ok">✓ Found</span>' : '<span class="warning">⚠️ Not found</span>'; ?></td>
                <td><?php echo $curl_binary ? nl2br(htmlspecialchars($curl_bin_version)) : 'Used by some plugins (Snoopy) to perform HTTPS requests.'; ?></td>
            </tr>
        </table>

        <p class="info">ℹ️ ruTorrent plugins may use PHP streams, the PHP cURL extension, or the system <code>curl</code> binary. TLS termination is handled by the webserver or by libcurl; PHP's <code>openssl</code> extension is not required for core ruTorrent functionality.</p>
    </div>
    
    <div class="section">
        <h2>🧪 HTTPS Connectivity Tests</h2>
        <?php
        // choose best available method: PHP cURL, PHP streams, or system curl
        $test_sites = [
            ['name' => 'Google (Modern TLS)', 'url' => 'https://www.google.com/'],
            ['name' => 'Cloudflare DNS', 'url' => 'https://1.1.1.1/'],
            ['name' => 'GitHub', 'url' => 'https://api.github.com/'],
        ];

        echo '<table>';
        echo '<tr><th>Test Site</th><th>Status</th><th>HTTP Code</th><th>Details</th></tr>';

        foreach ($test_sites as $site) {
            $success = false;
            $http_code = 'N/A';
            $details = '';

            // 1) try PHP cURL extension if available
            if ($curl_loaded && function_exists('curl_version')) {
                $ch = curl_init();
                curl_setopt($ch, CURLOPT_URL, $site['url']);
                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                curl_setopt($ch, CURLOPT_TIMEOUT, 10);
                curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
                curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
                curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
                curl_setopt($ch, CURLOPT_MAXREDIRS, 3);
                curl_setopt($ch, CURLOPT_USERAGENT, 'PHP-HTTPS-Test/1.0');

                $result = @curl_exec($ch);
                $err = curl_error($ch);
                $errno = curl_errno($ch);
                $info = curl_getinfo($ch);
                curl_close($ch);

                $success = ($errno === 0 && isset($info['http_code']) && $info['http_code'] >= 200 && $info['http_code'] < 400);
                $http_code = $info['http_code'] ?: 'N/A';
                $details = $success ? 'Connected via PHP cURL' : ($err ? $err . ' (errno: ' . $errno . ')' : 'Failed via PHP cURL');
            }

            // 2) fallback to PHP streams
            if (!$success && (in_array('ssl', $stream_transports) || in_array('tls', $stream_transports)) && ini_get('allow_url_fopen')) {
                $ctx = stream_context_create(['ssl' => ['verify_peer'=>true, 'verify_peer_name'=>true, 'capture_peer_cert'=>true]]);
                $data = @file_get_contents($site['url'], false, $ctx);
                if ($data !== false) {
                    $success = true;
                    $http_code = 200;
                    $details = 'Connected via PHP streams';
                } else {
                    $details = 'Failed via PHP streams';
                }
            }

            // 3) fallback to system curl binary
            if (!$success && $curl_binary) {
                $cmd = escapeshellcmd($curl_binary) . ' -s -S -I --max-time 10 ' . escapeshellarg($site['url']);
                $out = @shell_exec($cmd . ' 2>&1');
                if ($out && preg_match('/HTTP\/[^ ]+\s(\d+)/', $out, $m)) {
                    $code = intval($m[1]);
                    if ($code >= 200 && $code < 400) {
                        $success = true;
                        $http_code = $code;
                        $details = 'Connected via system curl';
                    } else {
                        $http_code = $code;
                        $details = 'system curl returned HTTP ' . $code;
                    }
                } else {
                    $details = trim($out) ?: 'system curl failed';
                }
            }

            $row_class = $success ? 'test-ok' : 'test-fail';
            echo '<tr class="' . $row_class . '">';
            echo '<td>' . htmlspecialchars($site['name']) . '</td>';
            echo '<td>' . ($success ? '<span class="ok">✓ OK</span>' : '<span class="error">✗ FAIL</span>') . '</td>';
            echo '<td>' . htmlspecialchars($http_code) . '</td>';
            echo '<td>' . htmlspecialchars($details) . '</td>';
            echo '</tr>';
        }

        echo '</table>';
        echo '<p class="info">ℹ️ Tests used (in order): PHP cURL extension, PHP streams (allow_url_fopen), system curl binary.</p>';
        ?>
    </div>
    
    <div class="section">
        <h2>🔬 OpenSSL Configuration</h2>
        <?php
        if ($openssl_loaded) {
            echo '<table>';
            echo '<tr><th>Property</th><th>Value</th></tr>';
            echo '<tr><td>OpenSSL Version</td><td>' . OPENSSL_VERSION_TEXT . '</td></tr>';
            echo '<tr><td>OpenSSL Number</td><td>' . sprintf('0x%X', OPENSSL_VERSION_NUMBER) . '</td></tr>';
            
            // Check if openssl binary exists
            $openssl_bin = @shell_exec('which openssl 2>/dev/null');
            if ($openssl_bin) {
                $openssl_bin = trim($openssl_bin);
                echo '<tr><td>OpenSSL Binary</td><td>' . htmlspecialchars($openssl_bin) . '</td></tr>';
                
                // Count available ciphers
                $cipher_count = @shell_exec('openssl ciphers -v 2>/dev/null | wc -l');
                if ($cipher_count) {
                    $cipher_count = intval(trim($cipher_count));
                    echo '<tr><td>Available Cipher Suites</td><td>' . $cipher_count;
                    if ($cipher_count < 50) {
                        echo ' <span class="warning">⚠️ Low (may have limited compatibility)</span>';
                    } elseif ($cipher_count > 100) {
                        echo ' <span class="ok">✓ Good</span>';
                    } else {
                        echo ' <span class="ok">✓ OK</span>';
                    }
                    echo '</td></tr>';
                }
                
                // Check supported protocols
                $protocols = [];
                foreach (['tls1', 'tls1_1', 'tls1_2', 'tls1_3'] as $proto) {
                    $test = @shell_exec("echo | openssl s_client -{$proto} -connect google.com:443 2>&1 | grep -i 'Protocol.*:.*TLS'");
                    if ($test && strlen($test) > 5) {
                        $protocols[] = strtoupper(str_replace('_', '.', $proto));
                    }
                }
                echo '<tr><td>Supported TLS Protocols</td><td>' . implode(', ', $protocols) . '</td></tr>';
            } else {
                echo '<tr><td>OpenSSL Binary</td><td><span class="warning">Not found in PATH</span></td></tr>';
            }
            
            // Check for EC support (critical for modern sites)
            if (function_exists('openssl_get_curve_names')) {
                $curves = openssl_get_curve_names();
                echo '<tr><td>Elliptic Curves</td><td>';
                if ($curves && count($curves) > 0) {
                    echo '<span class="ok">✓ ' . count($curves) . ' curves available</span>';
                    echo '<br><small>' . implode(', ', array_slice($curves, 0, 5));
                    if (count($curves) > 5) echo ', ...';
                    echo '</small>';
                } else {
                    echo '<span class="error">✗ No curves available</span>';
                }
                echo '</td></tr>';
            }
            
            echo '</table>';
            
            echo '<p class="info">ℹ️ Elliptic Curve (EC) support is required for modern TLS connections. ';
            echo 'Without EC, many HTTPS sites (including GitHub, Cloudflare, Google) will fail to connect.</p>';
            
        } else {
            echo '<p class="error">✗ OpenSSL extension not loaded</p>';
        }
        ?>
    </div>
    
    <div class="section">
        <h2>📦 PHP Extensions</h2>
        <?php
        $extensions = get_loaded_extensions();
        sort($extensions);
        
        // Highlight ruTorrent-relevant extensions (bookkeeping follows ruTorrent docs)
        $php_version = PHP_VERSION;
        $is_php5 = version_compare($php_version, '8.0.0', '<');
        
        $rutorrent_critical = ['mbstring', 'dom', 'xml', 'session', 'curl', 'ctype', 'zlib'];
        // Additional useful extensions
        $rutorrent_optional = ['opcache', 'phar', 'json'];
        
        echo '<h3>Critical / Required for ruTorrent</h3>';
        echo '<table><tr><th>Extension</th><th>Status</th><th>Note</th></tr>';
        foreach ($rutorrent_critical as $ext) {
            $loaded = extension_loaded($ext);
            $note = '';
            switch ($ext) {
                case 'curl': $note = 'HTTP client, external requests (or system curl used by plugins)'; break;
                case 'xml': $note = 'XMLRPC communication with rTorrent (libxml)'; break;
                case 'session': $note = 'User sessions, authentication'; break;
                case 'mbstring': $note = 'Multibyte string support'; break;
                case 'dom': $note = 'XML DOM manipulation (RSS plugin)'; break;
                case 'ctype': $note = 'Character type checking'; break;
                case 'zlib': $note = 'Data compression (gzip)'; break;
            }
            echo '<tr class="' . ($loaded ? 'test-ok' : 'test-fail') . '">';
            echo '<td>' . $ext . '</td>';
            echo '<td>' . ($loaded ? '<span class="ok">✓ Loaded</span>' : '<span class="error">✗ Missing</span>') . '</td>';
            echo '<td style="font-size:0.9em; color:#858585;">' . $note . '</td>';
            echo '</tr>';
        }
        echo '</table>';
        
        echo '<h3>Optional / Recommended</h3>';
        echo '<table><tr><th>Extension</th><th>Status</th><th>Note</th></tr>';
        foreach ($rutorrent_optional as $ext) {
            $loaded = extension_loaded($ext);
            $note = '';
            switch ($ext) {
                case 'opcache': $note = 'Bytecode cache — improves performance'; break;
                case 'phar': $note = 'PHAR archives support'; break;
                case 'ctype': $note = 'Character type checks'; break;
                case 'json': $note = 'JSON handling (built-in in PHP >=5.2)'; break;
                case 'gd': $note = 'Image handling (optional)'; break;
                case 'zip': $note = 'ZIP support (optional)'; break;
                case 'zlib': $note = 'Compression support'; break;
            }
            echo '<tr>';
            echo '<td>' . $ext . '</td>';
            echo '<td>' . ($loaded ? '<span class="ok">✓ Loaded</span>' : '<span class="warning">⚠️ Not loaded</span>') . '</td>';
            echo '<td style="font-size:0.9em; color:#858585;">' . $note . '</td>';
            echo '</tr>';
        }
        echo '</table>';
        
        echo '<h3>All Loaded Extensions (' . count($extensions) . ')</h3>';
        echo '<table><tr><th>Extension</th><th>Status</th></tr>';
        foreach ($extensions as $ext) {
            echo '<tr>';
            echo '<td>' . htmlspecialchars($ext) . '</td>';
            echo '<td><span class="ok">✓ Loaded</span></td>';
            echo '</tr>';
        }
        echo '</table>';
        ?>
    </div>
    
    <div class="section">
        <h2>🔧 PHP Configuration</h2>
        <table>
            <tr><th>Directive</th><th>Value</th><th>Relevance</th></tr>
            <?php
            $directives = [
                ['name' => 'max_execution_time', 'info' => 'Max script runtime (important for long operations)'],
                ['name' => 'memory_limit', 'info' => 'Memory available to PHP scripts'],
                ['name' => 'upload_max_filesize', 'info' => 'Max torrent file upload size'],
                ['name' => 'post_max_size', 'info' => 'Max POST data size'],
                ['name' => 'allow_url_fopen', 'info' => 'Required for HTTP/HTTPS streams'],
                ['name' => 'error_reporting', 'info' => 'Error reporting level'],
                ['name' => 'display_errors', 'info' => 'Show errors in output'],
                ['name' => 'log_errors', 'info' => 'Log errors to file'],
                ['name' => 'error_log', 'info' => 'Error log file location'],
            ];
            
            foreach ($directives as $directive) {
                $value = ini_get($directive['name']);
                echo '<tr>';
                echo '<td><strong>' . $directive['name'] . '</strong></td>';
                echo '<td>' . ($value !== false && $value !== '' ? htmlspecialchars($value) : '<em>not set</em>') . '</td>';
                echo '<td style="font-size:0.85em; color:#858585;">' . $directive['info'] . '</td>';
                echo '</tr>';
            }
            ?>
        </table>
        
        <h3>SSL/TLS Configuration</h3>
        <table>
            <tr><th>Directive</th><th>Value</th></tr>
            <?php
            $ssl_directives = ['openssl.cafile', 'openssl.capath', 'curl.cainfo'];
            foreach ($ssl_directives as $directive) {
                $value = ini_get($directive);
                echo '<tr><td>' . $directive . '</td><td>' . ($value ? htmlspecialchars($value) : '<em>default</em>') . '</td></tr>';
            }
            ?>
        </table>
    </div>
    
    <div class="section">
        <h2>📁 System Paths</h2>
        <table>
            <tr><th>Resource</th><th>Path</th><th>Status</th></tr>
            <tr>
                <td>CA Certificate Bundle</td>
                <td><?php
                    $ca_bundle = '/etc/ssl/certs/ca-bundle.crt';
                    echo $ca_bundle;
                ?></td>
                <td>
                    <?php
                    if (file_exists($ca_bundle)) {
                        echo '<span class="ok">✓ Exists</span> (' . number_format(filesize($ca_bundle)) . ' bytes)';
                    } else {
                        echo '<span class="error">✗ Not found</span>';
                    }
                    ?>
                </td>
            </tr>
            <tr>
                <td>php.ini</td>
                <td><?php echo php_ini_loaded_file() ?: '<em>none</em>'; ?></td>
                <td>
                    <?php
                    $ini_file = php_ini_loaded_file();
                    if ($ini_file && file_exists($ini_file)) {
                        echo '<span class="ok">✓ Loaded</span>';
                    } elseif ($ini_file) {
                        echo '<span class="warning">⚠️ Configured but not found</span>';
                    } else {
                        echo '<span class="info">ℹ️ Using defaults</span>';
                    }
                    ?>
                </td>
            </tr>
            <tr>
                <td>Additional .ini files</td>
                <td><?php 
                    $scanned = php_ini_scanned_files();
                    echo $scanned ? str_replace(',', '<br>', $scanned) : '<em>none</em>'; 
                ?></td>
                <td><?php echo $scanned ? '<span class="ok">✓ ' . substr_count($scanned, ',') + 1 . ' file(s)</span>' : '—'; ?></td>
            </tr>
        </table>
    </div>

    
    <div class="section">
        <h2>📊 Full phpinfo()</h2>
        <p><a href="?full=1" style="color: #3794ff; text-decoration: underline;">View complete phpinfo() output</a></p>
        <?php
        if (isset($_GET['full'])) {
            echo '<div style="background: white; color: black; padding: 20px; margin-top: 20px;">';
            phpinfo();
            echo '</div>';
        }
        ?>
    </div>
    
    <div class="section">
        <h2>✅ Status Summary</h2>
        <?php
        // Check required/optional components summary
        $critical_extensions = $rutorrent_critical;
        $optional_extensions = $rutorrent_optional;
        
        $all_critical_loaded = true;
        $has_warnings = false;
        
        echo '<table>';
        echo '<tr><th>Component</th><th>Status</th></tr>';
        
        foreach ($critical_extensions as $ext) {
            $loaded = extension_loaded($ext);
            if (!$loaded) $all_critical_loaded = false;
            $description = '';
            switch ($ext) {
                case 'curl': $description = 'HTTP client, external requests (or system curl)'; break;
                case 'xml': $description = 'XMLRPC communication with rTorrent'; break;
                case 'session': $description = 'User sessions, authentication'; break;
                case 'mbstring': $description = 'Multibyte string support'; break;
                case 'dom': $description = 'XML DOM manipulation (RSS plugin)'; break;
                case 'ctype': $description = 'Character type checking'; break;
                case 'zlib': $description = 'Data compression (gzip)'; break;
            }
            echo '<tr class="' . ($loaded ? 'test-ok' : 'test-fail') . '">';
            echo '<td>' . $ext . ' Extension</td>';
            echo '<td>' . ($loaded ? '<span class="ok">✓ Available</span>' : '<span class="error">✗ Missing - ' . $description . ' may not work</span>') . '</td>';
            echo '</tr>';
        }
        
        // Check for EC support via openssl binary or extension
        $ec_supported = false;
        $openssl_bin = trim(@shell_exec('which openssl 2>/dev/null')) ?: false;
        if ($openssl_bin) {
            $curves = @shell_exec(escapeshellcmd($openssl_bin) . ' ecparam -list_curves 2>/dev/null | wc -l');
            if ($curves && intval(trim($curves)) > 0) $ec_supported = true;
        }
        if (!$ec_supported && $openssl_loaded && function_exists('openssl_get_curve_names')) {
            $curves = openssl_get_curve_names();
            if ($curves && count($curves) > 0) $ec_supported = true;
        }
        echo '<tr class="' . ($ec_supported ? 'test-ok' : 'test-fail') . '">';
        echo '<td>Elliptic Curve (EC) support (system/OpenSSL)</td>';
        echo '<td>' . ($ec_supported ? '<span class="ok">✓ Available</span>' : '<span class="error">✗ Not available - modern TLS may fail</span>') . '</td>';
        echo '</tr>';
        
        echo '</table>';
        
        if ($all_critical_loaded && $ec_supported) {
            echo '<p class="ok" style="font-size:1.1em; margin-top:15px;">✓ PHP environment looks good for ruTorrent and plugins.</p>';
        } elseif ($all_critical_loaded) {
            echo '<p class="warning" style="font-size:1.1em; margin-top:15px;">⚠️ PHP has required extensions, but system TLS (EC) support may be missing.</p>';
        } else {
            echo '<p class="error" style="font-size:1.1em; margin-top:15px;">✗ Some required PHP components are missing. ruTorrent may have reduced functionality.</p>';
        }
        ?>
    </div>
    
    <div class="section">
        <h2>🔍 Extension Dependency Verification</h2>
        <p class="info">ℹ️ The critical extensions listed above are based on static analysis of ruTorrent code using tools like <code>depends.php</code>.</p>
        <p>To verify dependencies manually, you can run:</p>
        <pre><code>wget https://raw.githubusercontent.com/RogerGee/php-ext-depends/master/depends.php
php depends.php /usr/mww/rutorrent/</code></pre>
        <p>This will show exactly which PHP extensions are loaded when executing ruTorrent code.</p>
    </div>
    
    <p style="text-align: center; margin-top: 50px; color: #858585; font-size: 0.9em;">
        PHP <?php echo PHP_VERSION; ?> on <?php echo php_uname('s') . ' ' . php_uname('r'); ?> | 
        Generated: <?php echo date('Y-m-d H:i:s'); ?>
    </p>
</body>
</html>
