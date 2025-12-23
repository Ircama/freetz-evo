<?php
// ruTorrent dynamic configuration for Freetz-NG
// This file is auto-loaded by ruTorrent to configure SCGI connection

// Auto-detect first available USB storage
function autodetect_storage() {
	// Load Freetz config
	$mod_cfg = '/mod/etc/conf/mod.cfg';
	$stor_prefix = 'uStor';
	if (file_exists($mod_cfg)) {
		$lines = file($mod_cfg, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
		foreach ($lines as $line) {
			if (preg_match("/^export MOD_STOR_PREFIX='([^']+)'/", $line, $matches)) {
				$stor_prefix = $matches[1];
				break;
			}
		}
	}
	
	// Try ${stor_prefix}01 first
	$default_path = "/var/media/ftp/{$stor_prefix}01/rtorrent";
	if (is_dir("/var/media/ftp/{$stor_prefix}01")) {
		return $default_path;
	}
	
	// Try to find any mounted USB storage
	$usb_dirs = glob('/var/media/ftp/*', GLOB_ONLYDIR);
	if (!empty($usb_dirs)) {
		return $usb_dirs[0] . '/rtorrent';
	}
	
	// Fallback to tmpfs
	return '/var/tmp/rtorrent';
}

// Read SCGI socket path from rtorrent's active .rtorrent.rc file
$scgi_socket = '/tmp/rpc.socket';  // Default fallback

// Find BASEDIR - try /mod/etc/conf first (user config), then /etc/default (default)
$basedir = '';
$use_home = false;
$config_files = ['/mod/etc/conf/rtorrent.cfg', '/etc/default.rtorrent/rtorrent.cfg'];
foreach ($config_files as $freetz_cfg) {
	if (file_exists($freetz_cfg)) {
		$lines = file($freetz_cfg, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
		foreach ($lines as $line) {
			if (preg_match("/^(export )?RTORRENT_BASEDIR=['\"]?([^'\"\s]+)['\"]?/", $line, $matches)) {
				$basedir = $matches[2];
			}
			if (preg_match("/^(export )?RUTORRENT_USES_HOME=['\"]?([^'\"\s]+)['\"]?/", $line, $matches)) {
				if (strtolower($matches[2]) === 'yes') {
					$use_home = true;
				}
			}
		}
		if (!empty($basedir)) {
			break; // Exit loop if BASEDIR found in this config file
		}
	}
}

// If BASEDIR not set or empty, try to auto-detect
if (empty($basedir)) {
	$basedir = autodetect_storage();
}

// Try to read SCGI configuration from .rtorrent.rc in BASEDIR
$rtorrent_rc = $basedir . '/.rtorrent.rc';
$download_dir = $basedir . '/downloads/';  // Default assumption

// Ensure SCGI defaults are always defined (avoid PHP notices that can break JSON output)
$scgi_host = 'unix://' . $scgi_socket;
$scgi_port = 0;

if (file_exists($rtorrent_rc)) {
	$lines = file($rtorrent_rc, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
	foreach ($lines as $line) {
		// Match: network.scgi.open_port = 127.0.0.1:5000 (TCP mode)
		if (preg_match('/^\s*network\.scgi\.open_port\s*=\s*(.+)/', $line, $matches)) {
			$tcp_config = trim($matches[1]);
			// Parse host:port
			if (preg_match('/^([^:]+):(\d+)$/', $tcp_config, $parts)) {
				$scgi_host = $parts[1];
				$scgi_port = (int)$parts[2];
				break;
			}
		}
		// Match: network.scgi.open_local = /path/to/socket (UNIX socket mode)
		if (preg_match('/^\s*network\.scgi\.open_local\s*=\s*(.+)/', $line, $matches)) {
			$socket_path = trim($matches[1]);
			// Handle relative paths - if not starting with /, assume /tmp/
			if ($socket_path[0] !== '/') {
				$socket_path = '/tmp/' . $socket_path;
			}
			$scgi_host = 'unix://' . $socket_path;
			$scgi_port = 0;
			break;
		}
		// Match: method.insert = cfg.download, ... (to find download directory)
		if (preg_match('/^\s*method\.insert\s*=\s*cfg\.download,\s*private\|const\|string,\s*\(cat,\(cfg\.basedir\),"([^"]+)"\)/', $line, $matches)) {
			$download_subdir = $matches[1];
			$download_dir = $basedir . '/' . ltrim($download_subdir, '/');
		}
	}
}

// Export values for ruTorrent's conf/config.php which reads from $_ENV.
// This avoids relying on the webserver/FastCGI environment propagation.
if (!isset($_ENV['RU_SCGI_HOST']) || $_ENV['RU_SCGI_HOST'] === '') {
	$_ENV['RU_SCGI_HOST'] = $scgi_host;
}
if (!isset($_ENV['RU_SCGI_PORT']) || $_ENV['RU_SCGI_PORT'] === '') {
	$_ENV['RU_SCGI_PORT'] = $scgi_port;
}
if (!isset($_ENV['RU_TOP_DIR']) || $_ENV['RU_TOP_DIR'] === '') {
	if ($use_home) {
		$top_dir = rtrim($basedir, '/') . '/';
	} else {
		$top_dir = rtrim($download_dir, '/') . '/';
	}
	if ($top_dir === '/' || empty($basedir)) {
		$top_dir = '/tmp/';  // Fallback safe directory
	}
	$_ENV['RU_TOP_DIR'] = $top_dir;
}

// Note: $scgi_host and $scgi_port are now set from .rtorrent.rc
// They can be used directly by ruTorrent's config.php
$al_diagnostic = false;

