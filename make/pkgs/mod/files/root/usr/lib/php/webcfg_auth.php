<?php
/**
 * Shared WebCFG authentication helper for PHP/CGI applications.
 *
 * Supports both modes:
 * - Form-based session login (MOD_HTTPD_NEWLOGIN=yes)
 * - Legacy Basic Authentication (MOD_HTTPD_NEWLOGIN!=yes)
 */

if (!function_exists('webcfg_parse_export_cfg')) {
    function webcfg_parse_export_cfg($file) {
        $cfg = array();
        if (!is_readable($file)) {
            return $cfg;
        }
        $lines = @file($file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        if (!is_array($lines)) {
            return $cfg;
        }
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#') {
                continue;
            }
            if (strpos($line, 'export ') === 0) {
                $line = substr($line, 7);
            }
            $eq = strpos($line, '=');
            if ($eq === false) {
                continue;
            }
            $key = trim(substr($line, 0, $eq));
            $val = trim(substr($line, $eq + 1));
            if (strlen($val) >= 2) {
                $first = $val[0];
                $last = $val[strlen($val) - 1];
                if (($first === "'" && $last === "'") || ($first === '"' && $last === '"')) {
                    $val = substr($val, 1, -1);
                }
            }
            $cfg[$key] = $val;
        }
        return $cfg;
    }
}

if (!function_exists('webcfg_load_mod_cfg')) {
    function webcfg_load_mod_cfg() {
        $cfg = array();
        $files = array(
            '/etc/default.mod/mod.cfg',
            '/mod/etc/default.mod/mod.cfg',
            '/mod/external/etc/default.mod/mod.cfg',
            '/mod/etc/conf/mod.cfg',
            '/var/mod/etc/conf/mod.cfg',
        );
        foreach ($files as $file) {
            $tmp = webcfg_parse_export_cfg($file);
            foreach ($tmp as $k => $v) {
                $cfg[$k] = $v;
            }
        }
        return $cfg;
    }
}

if (!function_exists('webcfg_cfg_get')) {
    function webcfg_cfg_get($cfg, $key, $default = '') {
        return isset($cfg[$key]) ? (string)$cfg[$key] : (string)$default;
    }
}

if (!function_exists('webcfg_is_newlogin_enabled')) {
    function webcfg_is_newlogin_enabled($cfg) {
        return strtolower(trim(webcfg_cfg_get($cfg, 'MOD_HTTPD_NEWLOGIN', 'no'))) === 'yes';
    }
}

if (!function_exists('webcfg_authenticated_user')) {
    function webcfg_authenticated_user($cfg) {
        $user = trim(webcfg_cfg_get($cfg, 'MOD_HTTPD_USER', 'admin'));
        if ($user === '') {
            $user = 'admin';
        }
        return $user;
    }
}

if (!function_exists('webcfg_validate_sid_session')) {
    function webcfg_validate_sid_session($cfg) {
        $sid = isset($_COOKIE['SID']) ? trim((string)$_COOKIE['SID']) : '';
        if (!preg_match('/^[a-f0-9]{16,64}$/', $sid)) {
            return false;
        }

        $idfile = '/tmp/' . $sid . '.webcfg';
        if (!is_file($idfile)) {
            return false;
        }

        $timeout = (int)webcfg_cfg_get($cfg, 'MOD_HTTPD_SESSIONTIMEOUT', '600');
        if ($timeout < 0) {
            $timeout = 600;
        }

        $mtime = @filemtime($idfile);
        if (!is_int($mtime) || $mtime <= 0) {
            return false;
        }

        // Keep behavior consistent with login.sh semantics.
        $lastacc = time() - $mtime;
        if ($lastacc > $timeout) {
            @unlink($idfile);
            return false;
        }

        @touch($idfile);
        return true;
    }
}

if (!function_exists('webcfg_require_basic_auth')) {
    function webcfg_require_basic_auth($cfg) {
        $user = webcfg_cfg_get($cfg, 'MOD_HTTPD_USER', 'admin');
        $hash = webcfg_cfg_get($cfg, 'MOD_HTTPD_PASSWD', '');

        $reqUser = isset($_SERVER['PHP_AUTH_USER']) ? (string)$_SERVER['PHP_AUTH_USER'] : '';
        $reqPass = isset($_SERVER['PHP_AUTH_PW']) ? (string)$_SERVER['PHP_AUTH_PW'] : '';

        $ok = false;
        if ($reqUser !== '' && $reqUser === $user && $hash !== '') {
            $crypt = @crypt($reqPass, $hash);
            if (is_string($crypt) && hash_equals($hash, $crypt)) {
                $ok = true;
            }
        }

        if ($ok) {
            if (!isset($_SERVER['REMOTE_USER']) || $_SERVER['REMOTE_USER'] === '') {
                $_SERVER['REMOTE_USER'] = $reqUser;
            }
            return true;
        }

        header('WWW-Authenticate: Basic realm="Freetz"');
        http_response_code(401);
        header('Content-Type: text/plain; charset=UTF-8');
        echo "Authentication required\n";
        exit;
    }
}

if (!function_exists('webcfg_login_redirect_url')) {
    function webcfg_login_redirect_url($subpage) {
        $subpage = ltrim((string)$subpage, '/');
        $subpage = preg_replace('/[^-_a-zA-Z0-9\.\/?=]/', '', $subpage);
        if ($subpage === '') {
            $subpage = '';
        }
        return '/cgi-bin/login.cgi?subpage=' . $subpage;
    }
}

if (!function_exists('webcfg_require_auth')) {
    function webcfg_require_auth($options = array()) {
        if (php_sapi_name() === 'cli') {
            return true;
        }

        $cfg = webcfg_load_mod_cfg();
        $mode = isset($options['mode']) ? (string)$options['mode'] : 'redirect';
        $subpage = isset($options['subpage']) ? (string)$options['subpage'] : '';
        $loginUrl = isset($options['login_url']) ? (string)$options['login_url'] : '';
        if ($loginUrl === '') {
            $loginUrl = webcfg_login_redirect_url($subpage);
        }

        if (webcfg_is_newlogin_enabled($cfg)) {
            if (webcfg_validate_sid_session($cfg)) {
                if (!isset($_SERVER['REMOTE_USER']) || $_SERVER['REMOTE_USER'] === '') {
                    $_SERVER['REMOTE_USER'] = webcfg_authenticated_user($cfg);
                }
                return true;
            }

            if ($mode === 'json') {
                http_response_code(403);
                header('Content-Type: application/json; charset=UTF-8');
                echo json_encode(array(
                    'error' => 'Authentication required',
                    'auth_required' => true,
                    'login_url' => $loginUrl
                ));
                exit;
            }

            header('Location: ' . $loginUrl);
            exit;
        }

        return webcfg_require_basic_auth($cfg);
    }
}
