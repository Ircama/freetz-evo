menuconfig FREETZ_PACKAGE_RUTORRENT
	bool "ruTorrent web interface"
	default n
	depends on FREETZ_PACKAGE_RTORRENT_DAEMON
	depends on FREETZ_PACKAGE_PHP || FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_RTORRENT_WITH_XMLRPC
	select FREETZ_PACKAGE_RTORRENT_CGI
	select FREETZ_LIB_libz
	# PHP 8.x required extensions
	select FREETZ_PACKAGE_PHP_cgi                if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_CURL          if FREETZ_PACKAGE_PHP
	select FREETZ_LIB_libcrypto_WITH_EC          if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_LIBXML        if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_LIBXML2_FULL  if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_LIBXML2_HTML  if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_DOM           if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_SESSION       if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_MBSTRING      if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_CTYPE         if FREETZ_PACKAGE_PHP
	select FREETZ_PACKAGE_PHP_WITH_ZLIB          if FREETZ_PACKAGE_PHP
	# PHP5 5.6.40 required extensions
	select FREETZ_PACKAGE_PHP5_cgi               if FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_PHP5_WITH_CURL         if FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_PHP5_WITH_LIBXML       if FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_PHP5_WITH_SESSION      if FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_PHP5_WITH_MBSTRING     if FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_PHP5_WITH_JSON         if FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_PHP5_WITH_CTYPE        if FREETZ_PACKAGE_PHP5
	select FREETZ_PACKAGE_PHP5_WITH_ZLIB         if FREETZ_PACKAGE_PHP5
	help
		Installs ruTorrent web interface to /usr/mww/rutorrent.
		Version: 5.2.10

		This option requires either PHP (8.x) or PHP5 (5.6.40) to be enabled.
		If this option is not available, go to "Packages -> Web interface & server"
		and select either "PHP" or "PHP5" first.

		PHP extensions actually used by ruTorrent code (from dependency analysis):
		- curl (HTTP requests), session (authentication), mbstring (multibyte strings)
		- dom (XML DOM, RSS plugin), xml/libxml (XMLRPC with rTorrent), SimpleXML
		- ctype, json (builtin in PHP 8.x), zlib
		
		The following PHP extensions are enabled automatically:
		- CGI support
		- CURL (with SSL/TLS via libcurl + OpenSSL)
		- LIBXML (for XMLRPC communication with rTorrent)
		- SESSION
		- MBSTRING
		- LIBXML2 FULL
		- LIBXML2 HTML
		- DOM
		- CTYPE (character type checking)
		- ZLIB (data compression)
		- ZLIB (data compression)
		
		Additional library requirements (enabled automatically):
		- libcrypto with Elliptic Curve support (for modern HTTPS/TLS)
		- zlib (compression library, used by PHP zlib extension)
		
		Served by httpd-webcfg at its default port (e.g., 81 at http://fritzbox:81/rutorrent/)
		Configure rTorrent in standard mode (e.g., http://fritz.box:81/cgi-bin/conf/rtorrent)

if FREETZ_PACKAGE_RUTORRENT

	config FREETZ_PACKAGE_RUTORRENT_WITH_P7ZIP
		bool "Enable P7ZIP support (for archive management)"
		select FREETZ_PACKAGE_P7ZIP
		default n
		help
			Enables archive management features in ruTorrent plugins.
			Allows extraction and creation of compressed archives.

	config FREETZ_PACKAGE_RUTORRENT_WITH_MEDIAINFO
		bool "Enable MediaInfo support (for multimedia asset analysis)"
		select FREETZ_PACKAGE_MEDIAINFO
		default n
		help
			Enables multimedia file analysis in ruTorrent.
			Displays codec, bitrate, and other media information.

	config FREETZ_PACKAGE_RUTORRENT_BASE_PLUGINS
		bool "ruTorrent base plugins (pgrep, curl and unrar required)"
		select FREETZ_BUSYBOX_PGREP
		select FREETZ_PACKAGE_CURL
		select FREETZ_PACKAGE_UNRAR
		default y
		help
			Include all official ruTorrent plugins from the main distribution.
			If disabled, only ruTorrent core files will be installed (no plugins).
			
			Requires: pgrep (BusyBox), curl, unrar
			
	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_TRACKERSTATUS
		bool "trackerstatus plugin"
		default n
		help
			Enhanced tracker status display plugin.
			
	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_FREETZ_FILEMANAGER
		bool "Freetz-NG filemanager plugin (p7zip and mediainfo recommended)"
		depends on FREETZ_PACKAGE_RUTORRENT_BASE_PLUGINS
		default y
		help
			Freetz-NG enhanced version of nelu's filemanager plugin.

			Requires:
			 - p7zip and mediainfo packages are recommended for full functionality.
			 - ruTorrent base plugins are required. 
			
			Features:
			 - BusyBox compatibility (uses stat instead of find -printf)
			 - p7zip RAR archive support with table format parser
			 - Enhanced UI with time field, ls-style permissions, user/group columns
			 - Directory size display
			 - Archive browsing with raw output display
			
			This replaces the filemanager plugin from ruTorrent base plugins.
			If disabled, the original nelu filemanager from base plugins will be used.

	menu "ruTorrent 3rd party plugins"
		depends on FREETZ_SHOW_DEVELOPER

	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_MEDIASTREAM
		bool "mediastream (filemanager-media)"
		default n
		help
			Media streaming plugin for filemanager.

	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_FILESHARE
		bool "fileshare (filemanager-share)"
		default n
		help
			File sharing plugin for filemanager.

	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_LOGOFF
		bool "logoff"
		default n
		help
			Adds a logout button to ruTorrent.

	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_PAUSE
		bool "pausewebui"
		default n
		help
			Pause/resume web interface plugin.

	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_INSTANTSEARCH
		bool "instantsearch"
		default n
		help
			Instant search plugin for torrent filtering.

	config FREETZ_PACKAGE_RUTORRENT_PLUGIN_TOGGLEDETAILS
		bool "toggle_details_button"
		default n
		help
			Toggle details panel button plugin.

	endmenu # ruTorrent 3rd party plugins

endif # FREETZ_PACKAGE_RUTORRENT
