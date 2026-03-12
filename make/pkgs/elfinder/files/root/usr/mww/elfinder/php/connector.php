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
$_saved = elfinder_parse_cfg('/mod/etc/conf/elfinder.cfg');
foreach ($_saved as $k => $v) {
    $_cfg[$k] = $v;
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
if ($_mediainfo !== '') {
    $_mediaInfoPlugin = array(
        'MediaInfo' => array(
            'enable'       => true,
            'mediaInfoCmd' => $_mediainfo,
        ),
    );
}

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
    $_bind['info'] = array('Plugin.MediaInfo.onInfo');
    $_plugin       = $_mediaInfoPlugin;
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
