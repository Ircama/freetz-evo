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

error_reporting(0); // Set E_ALL for debugging

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

// Load defaults first, then overlay with saved values
$_cfg = elfinder_parse_cfg('/etc/default.elfinder/elfinder.cfg');
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
        $found = trim(shell_exec('which ' . escapeshellarg($name) . ' 2>/dev/null'));
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
is_readable('./vendor/autoload.php') && require './vendor/autoload.php';
require './autoload.php';

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

$_url = elfcfg('ELFINDER_URL', '');
if ($_url === '') {
    $_url = '/';
}

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
$opts = array(
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
            'plugins'       => $_mediaInfoPlugin,
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
