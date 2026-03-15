<?php
/**
 * elFinder PHP connector for Freetz-EVO / FritzBox
 *
 * This file is part of the squashfs image and is read-only.
 * Configuration is read at runtime from /mod/etc/conf/elfinder.cfg
 * (written by the Freetz web interface save hook).
 *
 * No file generation is required – this connector works with both
 * read-only (non-externalized) and writable (externalized) setups.
 */

// Log all PHP errors to a file without corrupting the JSON response.
// To diagnose issues: ssh root@fritz.box 'tail -f /tmp/elfinder.log'
// Set to 0 in production once stable.
error_reporting(E_ALL);
ini_set('display_errors', '0');
ini_set('log_errors',     '1');
ini_set('error_log',      '/tmp/elfinder.log');

// The FritzBox PHP CGI default of 16MB is not enough:
// finfo_file() alone needs ~7MB for the MIME-type magic database.
// Raise the limit before elFinder initializes.
ini_set('memory_limit', '48M');

// Enforce WebCFG authentication for php-cgi entrypoints.
$_webcfgAuth = '';
if (is_readable('/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/usr/lib/php/webcfg_auth.php';
} elseif (is_readable('/mod/external/usr/lib/php/webcfg_auth.php')) {
    $_webcfgAuth = '/mod/external/usr/lib/php/webcfg_auth.php';
}
$_cmd = isset($_REQUEST['cmd']) ? (string)$_REQUEST['cmd'] : '';
$_allowAnonymousFileCmd = ($_cmd === 'file');
if ($_webcfgAuth !== '') {
    require_once $_webcfgAuth;
    if (!$_allowAnonymousFileCmd) {
        // Always return to the UI page after login; using connector URI here
        // can cause login loops or landing on raw JSON responses.
        $subpage = 'elfinder/';
        $loginUrl = '/cgi-bin/conf/elfinder?subpage=elfinder/';
        webcfg_require_auth(array('mode' => 'json', 'subpage' => $subpage, 'login_url' => $loginUrl));
    }
}

if (isset($_REQUEST['cmd']) && (string)$_REQUEST['cmd'] === 'auth_ping') {
    header('Content-Type: application/json; charset=UTF-8');
    echo json_encode(array('success' => true, 'authenticated' => true));
    exit;
}

// ---------------------------------------------------------------------------
// Parse shell-style config files (export VAR='value')
// ---------------------------------------------------------------------------
function elfinder_parse_cfg($file) {
    $cfg = array();
    if (!is_readable($file)) {
        return $cfg;
    }
    foreach (file($file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        // Skip comments and non-export lines
        if ($line === '' || $line[0] === '#') continue;
        if (strpos($line, 'export ') !== 0) continue;
        $line = substr($line, 7); // strip "export "
        $eq = strpos($line, '=');
        if ($eq === false) continue;
        $key = trim(substr($line, 0, $eq));
        $val = trim(substr($line, $eq + 1));
        // Strip surrounding single or double quotes
        if (strlen($val) >= 2 &&
            (($val[0] === "'" && $val[strlen($val)-1] === "'") ||
             ($val[0] === '"' && $val[strlen($val)-1] === '"'))) {
            $val = substr($val, 1, strlen($val) - 2);
        }
        $cfg[$key] = $val;
    }
    return $cfg;
}

function elfinder_json_exit($payload) {
    header('Content-Type: application/json; charset=UTF-8');
    echo json_encode($payload);
    exit;
}

function elfinder_cfg_quote($value) {
    return "'" . str_replace("'", "'\\''", (string)$value) . "'";
}

function elfinder_cfg_upsert_export(&$lines, $key, $value) {
    $prefix = 'export ' . $key . '=';
    $replacement = $prefix . elfinder_cfg_quote($value);
    $updated = false;
    foreach ($lines as $i => $line) {
        if (strpos(trim($line), $prefix) === 0) {
            $lines[$i] = $replacement;
            $updated = true;
            break;
        }
    }
    if (!$updated) {
        $lines[] = $replacement;
    }
}

// Load defaults first: check multiple locations for resilience
// (firmware build: /etc/default.elfinder/, dev deploy: /mod/external/etc/default.elfinder/)
$_cfg = array();
foreach (array(
    '/mod/external/etc/default.elfinder/elfinder.cfg',
    '/etc/default.elfinder/elfinder.cfg',
    '/mod/etc/default.elfinder/elfinder.cfg',
) as $_cfgfile) {
    $_cfg = elfinder_parse_cfg($_cfgfile);
    if (!empty($_cfg)) break;
}
// Saved config may live at /mod/etc/conf or /var/mod/etc/conf depending on setup.
foreach (array(
    '/mod/etc/conf/elfinder.cfg',
    '/var/mod/etc/conf/elfinder.cfg',
) as $_savedCfgFile) {
    $_saved = elfinder_parse_cfg($_savedCfgFile);
    foreach ($_saved as $k => $v) {
        $_cfg[$k] = $v;
    }
}

// Custom command used by MovieInfo UI to persist TMDb/OMDb keys directly
// through the authenticated connector path, avoiding endpoint alias issues.
if (isset($_REQUEST['cmd']) && (string)$_REQUEST['cmd'] === 'movieinfo_setkeys') {
    $_tmdbKey = isset($_REQUEST['tmdb_api_key']) ? trim((string)$_REQUEST['tmdb_api_key']) : '';
    $_omdbKey = isset($_REQUEST['omdb_api_key']) ? trim((string)$_REQUEST['omdb_api_key']) : '';
    $_saveCfg = isset($_REQUEST['save_config']) ? strtolower(trim((string)$_REQUEST['save_config'])) : '0';

    if ($_tmdbKey !== '' && !preg_match('/^[A-Za-z0-9]{16,128}$/', $_tmdbKey)) {
        elfinder_json_exit(array('success' => false, 'error' => 'Invalid TMDb API key format'));
    }
    if ($_omdbKey !== '' && !preg_match('/^[A-Za-z0-9]{6,128}$/', $_omdbKey)) {
        elfinder_json_exit(array('success' => false, 'error' => 'Invalid OMDb API key format'));
    }
    if ($_tmdbKey === '' && $_omdbKey === '') {
        elfinder_json_exit(array('success' => false, 'error' => 'No API key provided'));
    }

    if ($_saveCfg === '1' || $_saveCfg === 'yes' || $_saveCfg === 'true') {
        $_cfgDir = is_dir('/var/mod/etc/conf') ? '/var/mod/etc/conf' : '/mod/etc/conf';
        $_cfgFile = $_cfgDir . '/elfinder.cfg';
        if (!is_dir($_cfgDir)) {
            @mkdir($_cfgDir, 0777, true);
        }

        $_lines = array();
        if (is_readable($_cfgFile)) {
            $_raw = @file($_cfgFile, FILE_IGNORE_NEW_LINES);
            if (is_array($_raw)) {
                $_lines = $_raw;
            }
        }

        if ($_tmdbKey !== '') {
            elfinder_cfg_upsert_export($_lines, 'ELFINDER_MOVIEINFO_TMDB_API_KEY', $_tmdbKey);
        }
        if ($_omdbKey !== '') {
            elfinder_cfg_upsert_export($_lines, 'ELFINDER_MOVIEINFO_OMDB_API_KEY', $_omdbKey);
        }

        $_out = implode("\n", $_lines);
        if ($_out !== '') {
            $_out .= "\n";
        }

        if (@file_put_contents($_cfgFile, $_out) === false) {
            elfinder_json_exit(array('success' => false, 'error' => 'Failed to save MovieInfo API key(s)'));
        }

        elfinder_json_exit(array(
            'success' => true,
            'saved' => true,
            'message' => 'MovieInfo API key(s) saved'
        ));
    }

    elfinder_json_exit(array(
        'success' => true,
        'saved' => false,
        'message' => 'MovieInfo API key(s) accepted for this session'
    ));
}

// Helper to get config value with fallback
function elfcfg($key, $default = '') {
    global $_cfg;
    return isset($_cfg[$key]) && $_cfg[$key] !== '' ? $_cfg[$key] : $default;
}

// ---------------------------------------------------------------------------
// External tool paths (FritzBox / BusyBox compatible)
// ---------------------------------------------------------------------------
define('ELFINDER_TAR_PATH',   '/bin/tar');
define('ELFINDER_GZIP_PATH',  '/bin/gzip');
define('ELFINDER_BZIP2_PATH', '/bin/bzip2');

// Optional tools from Freetz packages or auto-detected from PATH
function elfinder_find_bin($configured, $names) {
    if ($configured !== '' && is_executable($configured)) {
        return $configured;
    }
    foreach ((array)$names as $name) {
        $found = trim((string)shell_exec('which ' . escapeshellarg($name) . ' 2>/dev/null'));
        if ($found !== '' && is_executable($found)) {
            return $found;
        }
    }
    return '';
}

$_unrar    = elfinder_find_bin(elfcfg('ELFINDER_UNRAR_PATH'), 'unrar');
$_7z       = elfinder_find_bin(elfcfg('ELFINDER_7Z_PATH'),    array('7za', '7z'));
$_convert  = elfinder_find_bin(elfcfg('ELFINDER_CONVERT_PATH'), 'convert');
$_mediainfo = elfinder_find_bin(elfcfg('ELFINDER_MEDIAINFO_PATH'), 'mediainfo');
$_movieInfoTmdbKey = trim((string)elfcfg('ELFINDER_MOVIEINFO_TMDB_API_KEY', ''));
$_movieInfoOmdbKey = trim((string)elfcfg('ELFINDER_MOVIEINFO_OMDB_API_KEY', ''));
$_movieInfoProvider = strtolower(trim((string)elfcfg('ELFINDER_MOVIEINFO_PROVIDER', 'auto')));
$_movieInfoLang = trim((string)elfcfg('ELFINDER_MOVIEINFO_LANG', 'en'));

// Run MediaInfo plugin only when explicitly requested by the UI.
$_withMediaInfo = false;
if (isset($_REQUEST['with_mediainfo'])) {
    $_miReq = strtolower(trim((string)$_REQUEST['with_mediainfo']));
    if ($_miReq === '1' || $_miReq === 'yes' || $_miReq === 'true' || $_miReq === 'on') {
        $_withMediaInfo = true;
    }
}

// Optional request-time override (interactive panel in UI):
// enable only when explicitly requested to avoid browser-stored stale values
// silently overriding valid persisted config.
$_useRequestKeys = false;
if (isset($_REQUEST['movieinfo_use_request_keys'])) {
    $_tmpUse = strtolower(trim((string)$_REQUEST['movieinfo_use_request_keys']));
    if ($_tmpUse === '1' || $_tmpUse === 'yes' || $_tmpUse === 'true' || $_tmpUse === 'on') {
        $_useRequestKeys = true;
    }
}
if ($_useRequestKeys && isset($_REQUEST['movieinfo_tmdb_api_key'])) {
    $_tmpTmdb = trim((string)$_REQUEST['movieinfo_tmdb_api_key']);
    if ($_tmpTmdb !== '') {
        $_movieInfoTmdbKey = $_tmpTmdb;
    }
}
if ($_useRequestKeys && isset($_REQUEST['movieinfo_omdb_api_key'])) {
    $_tmpOmdb = trim((string)$_REQUEST['movieinfo_omdb_api_key']);
    if ($_tmpOmdb !== '') {
        $_movieInfoOmdbKey = $_tmpOmdb;
    }
}
if (isset($_REQUEST['movieinfo_provider'])) {
    $_tmpProvider = strtolower(trim((string)$_REQUEST['movieinfo_provider']));
    if ($_tmpProvider === 'tmdb' || $_tmpProvider === 'omdb' || $_tmpProvider === 'wikipedia' || $_tmpProvider === 'imdb' || $_tmpProvider === 'auto') {
        $_movieInfoProvider = $_tmpProvider;
    }
}

if ($_unrar   !== '') define('ELFINDER_UNRAR_PATH',   $_unrar);
if ($_7z      !== '') define('ELFINDER_7Z_PATH',      $_7z);
if ($_convert !== '') define('ELFINDER_CONVERT_PATH', $_convert);

// ---------------------------------------------------------------------------
// elFinder autoload
// ---------------------------------------------------------------------------
// Use __DIR__ so the path is always relative to this file's location,
// regardless of what the web server sets as the current working directory.
is_readable(__DIR__ . '/vendor/autoload.php') && require __DIR__ . '/vendor/autoload.php';
if (!is_readable(__DIR__ . '/autoload.php')) {
    header('Content-Type: application/json');
    echo json_encode(array('error' => 'elFinder PHP library not found. Check that autoload.php is deployed to the php/ directory.'));
    exit;
}
require __DIR__ . '/autoload.php';

// ---------------------------------------------------------------------------
// Network volume drivers
// ---------------------------------------------------------------------------
// FTP volume driver – enabled when ELFINDER_WITH_FTP_VOLUME=yes (build option)
// At runtime the config key ELFINDER_ENABLE_FTP is not stored separately;
// the build-time option bakes FTP support in or out via this connector.
// FREETZ_PACKAGE_ELFINDER_WITH_FTP_VOLUME_PLACEHOLDER
elFinder::$netDrivers['ftp'] = 'FTP';
// END_PLACEHOLDER

// ---------------------------------------------------------------------------
// Access control: hide/lock dot-files (except volume root)
// ---------------------------------------------------------------------------
function access($attr, $path, $data, $volume, $isDir, $relpath) {
    $basename = basename($path);
    return $basename[0] === '.'
        && strlen($relpath) !== 1
        ? !($attr == 'read' || $attr == 'write')
        :  null;
}

// ---------------------------------------------------------------------------
// Upload MIME-type filter
// ---------------------------------------------------------------------------
$_uploadAllowStr = elfcfg('ELFINDER_UPLOAD_ALLOW',
    'image/,audio/,video/,text/plain,application/pdf,' .
    'application/zip,application/x-gzip,application/x-bzip2,' .
    'application/x-7z-compressed,application/x-rar-compressed,' .
    'application/octet-stream');
$_uploadAllow = array_values(array_filter(array_map('trim', explode(',', $_uploadAllowStr))));

// ---------------------------------------------------------------------------
// PHP upload size limits
// ---------------------------------------------------------------------------
$_maxSize = elfcfg('ELFINDER_MAX_UPLOAD_SIZE', '64M');
@ini_set('upload_max_filesize', $_maxSize);
@ini_set('post_max_size',       $_maxSize);

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
$_basedir = elfcfg('ELFINDER_BASEDIR', '/var/media/ftp');
if (!is_dir($_basedir)) {
    $_basedir = '/var/media/ftp';
}
$_basedir = rtrim($_basedir, '/');

// ELFINDER_URL: base HTTP URL under which the basedir is served by the web server.
// Example: if /var/media/ftp is accessible at http://fritz.box:81/files/, set '/files/'.
// IMPORTANT: leave empty if the basedir is NOT directly served via HTTP (e.g. AVM
// MediaServer at /MediaServer/ is on a different port/service – do NOT use it here).
// When empty, elFinder uses the PHP connector for all file access (download/preview
// via connector instead of direct HTTP links – slightly slower but always correct).
$_url = elfcfg('ELFINDER_URL', '');

// Thumbnail directory
$_tmbPath = elfcfg('ELFINDER_THUMBPATH', '');
$_tmbURL  = '';
if ($_tmbPath === '') {
    $_tmbPath = $_basedir . '/.tmb';
    $_tmbURL  = rtrim($_url, '/') . '/.tmb/';
}
if (!is_dir($_tmbPath)) {
    @mkdir($_tmbPath, 0777, true);
}

// Trash directory
$_trashPath = $_basedir . '/.trash';
if (!is_dir($_trashPath)) {
    @mkdir($_trashPath, 0777, true);
}

// ---------------------------------------------------------------------------
// MediaInfo plugin
// ---------------------------------------------------------------------------
$_mediaInfoPlugin = array();
if ($_withMediaInfo && $_mediainfo !== '') {
    $_mediaInfoPlugin = array(
        'MediaInfo' => array(
            'enable'       => true,
            'mediaInfoCmd' => $_mediainfo,
        ),
    );
}

$_movieInfoPlugin = array();
if ($_movieInfoProvider !== 'tmdb' && $_movieInfoProvider !== 'omdb' && $_movieInfoProvider !== 'wikipedia' && $_movieInfoProvider !== 'imdb' && $_movieInfoProvider !== 'auto') {
    $_movieInfoProvider = 'auto';
}
$_movieInfoPlugin = array(
    'MovieInfo' => array(
        'enable'      => true,
        'provider'    => $_movieInfoProvider,
        'tmdbApiKey'  => $_movieInfoTmdbKey,
        'omdbApiKey'  => $_movieInfoOmdbKey,
        'language'    => $_movieInfoLang,
        'cacheFile'   => '/tmp/elfinder-movieinfo-cache.json',
        'cacheTtl'    => 43200,
        'httpTimeout' => 4,
    ),
);

// ---------------------------------------------------------------------------
// elFinder connector options
// ---------------------------------------------------------------------------
// MediaInfo: register via the global 'bind' + 'plugin' keys (top-level opts).
// The 'info' post-command hook fires after elFinder assembles the file stat
// array, so the plugin can append mediainfo text without patching core code.
// The volume-level 'plugin' key is a different mechanism used only for
// upload/paste events (e.g. Sanitizer, Watermark) – do NOT use it here.
$_bind   = array();
$_plugin = array();
if (!empty($_mediaInfoPlugin)) {
    $_bind['info'][] = 'Plugin.MediaInfo.onInfo';
    $_plugin = array_merge($_plugin, $_mediaInfoPlugin);
}
if (!empty($_movieInfoPlugin)) {
    $_bind['info'][] = 'Plugin.MovieInfo.onInfo';
    $_plugin = array_merge($_plugin, $_movieInfoPlugin);
}

$opts = array(
    'bind'   => $_bind,
    'plugin' => $_plugin,
    'roots' => array(
        // Main volume – LocalFileSystem
        array(
            'driver'        => 'LocalFileSystem',
            'path'          => $_basedir . '/',
            'URL'           => $_url,
            'trashHash'     => 't1_Lw',
            'winHashFix'    => DIRECTORY_SEPARATOR !== '/',
            'tmbPath'       => $_tmbPath,
            'tmbURL'        => $_tmbURL,
            'uploadDeny'    => array('all'),
            'uploadAllow'   => $_uploadAllow,
            'uploadOrder'   => array('deny', 'allow'),
            'accessControl' => 'access',
            'attributes'    => array(
                array('pattern' => '/^\\./', 'read' => false, 'write' => false,
                      'hidden' => true, 'locked' => false),
            ),
        ),
        // Trash volume
        array(
            'id'            => '1',
            'driver'        => 'Trash',
            'path'          => $_trashPath . '/',
            'tmbURL'        => $_tmbURL,
            'winHashFix'    => DIRECTORY_SEPARATOR !== '/',
            'uploadDeny'    => array('all'),
            'uploadAllow'   => $_uploadAllow,
            'uploadOrder'   => array('deny', 'allow'),
            'accessControl' => 'access',
        ),
    ),
);

// ---------------------------------------------------------------------------
// Run connector
// ---------------------------------------------------------------------------
$connector = new elFinderConnector(new elFinder($opts));
$connector->run();
