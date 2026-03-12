$(call PKG_INIT_BIN, 2.1.66)
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=fc86ef7988dafd6a608731ff85e6593d85b45e59d3b44afcbecdca02531669a7
$(PKG)_SITE:=https://github.com/Studio-42/elFinder/archive/refs/tags
### WEBSITE:=https://github.com/Studio-42/elFinder
### MANPAGE:=https://github.com/Studio-42/elFinder/wiki
### CHANGES:=https://github.com/Studio-42/elFinder/releases
### CVSREPO:=https://github.com/Studio-42/elFinder
### SUPPORT:=Ircama

# elFinder unpacked directory
ELFINDER_DIR:=$(SOURCE_DIR)/elFinder-$($(PKG)_VERSION)

# ============================================================================
# Target web directory
# ============================================================================
$(PKG)_ELFINDER_WEBDIR:=$($(PKG)_DEST_DIR)/usr/mww/elfinder

# Intermediate variables to prevent double expansion in recipes
ELFINDER_PKG_ELFINDER_WEBDIR := $($(PKG)_ELFINDER_WEBDIR)
ELFINDER_PKG_MAKE_DIR        := $($(PKG)_MAKE_DIR)
ELFINDER_PKG_SOURCE          := $($(PKG)_SOURCE)
ELFINDER_PKG_VERSION         := $($(PKG)_VERSION)
ELFINDER_SITE                := $($(PKG)_SITE)
ELFINDER_HASH                := $($(PKG)_HASH)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_MEDIAINFO
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_UNRAR
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_P7ZIP
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_FTP_VOLUME
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_ALLOW_ALL_UPLOADS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_MAX_UPLOAD_SIZE
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_THEME_MOONO
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_THEME_WINDOWS10
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_THEME_MATERIAL
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_ELFINDER_WITH_THEME_BOOTSTRAP

# ============================================================================
# 3rd-party theme sources
# ============================================================================
ELFINDER_THEME_MOONO_SOURCE     := elfinder-theme-moono-master.tar.gz
ELFINDER_THEME_MOONO_SITE       := https://github.com/lokothodida/elfinder-theme-moono/archive/refs/heads
ELFINDER_THEME_MOONO_HASH       := 8784a4fd3f7edae933189abf526ce713c6cba55c6717fdf7769831ba48631ab7

ELFINDER_THEME_WIN10_SOURCE     := elfinder-theme-windows-10-master.tar.gz
ELFINDER_THEME_WIN10_SITE       := https://github.com/lokothodida/elfinder-theme-windows-10/archive/refs/heads
ELFINDER_THEME_WIN10_HASH       := 74698658777ce5c66b235f5904997a250a41901f601601c0e39848b9d9608ff2

ELFINDER_THEME_MATERIAL_SOURCE  := elfinder-theme-material-master.tar.gz
ELFINDER_THEME_MATERIAL_SITE    := https://github.com/RobiNN1/elFinder-Material-Theme/archive/refs/heads
ELFINDER_THEME_MATERIAL_HASH    := 41f2f3a84d1fef17a50208905c2cef9de03a920cd2923e7ce04d43eeb19ab307

# Bootstrap theme lives inside the LibreICONS monorepo (themes/elFinder/)
ELFINDER_THEME_BOOTSTRAP_SOURCE := elfinder-theme-bootstrap-libreicons-master.tar.gz
ELFINDER_THEME_BOOTSTRAP_SITE   := https://github.com/StudioJunkyard/LibreICONS/archive/refs/heads
ELFINDER_THEME_BOOTSTRAP_HASH   := 87f8e5c956ab4dbd1bde4b40f0c372213a14c8a65c382da92453c2cff582997a

# jQuery and jQuery UI (not bundled in the elFinder tarball)
ELFINDER_JQUERY_SOURCE          := jquery-3.7.1.min.js
ELFINDER_JQUERY_SITE            := https://code.jquery.com
ELFINDER_JQUERY_HASH            := fc9a93dd241f6b045cbff0481cf4e1901becd0e12fb45166a8f17f95823f0b1a

ELFINDER_JQUERYUI_SOURCE        := jquery-ui-1.13.3.min.js
ELFINDER_JQUERYUI_SITE          := https://code.jquery.com/ui/1.13.3
ELFINDER_JQUERYUI_HASH          := b30d2234d5e63896d085816e0bd385da43a50f929029ed72e657c19f80bd4a38

ELFINDER_JQUERYUI_CSS_SOURCE    := jquery-ui-1.13.3.min.css
ELFINDER_JQUERYUI_CSS_SITE      := https://code.jquery.com/ui/1.13.3/themes/base
ELFINDER_JQUERYUI_CSS_HASH      := 5e2a8c299afa299746a26440969111454ea30b2f2eab052ccbe43efffcbc077f

# jQuery UI theme icon images (referenced via relative url() in the CSS)
ELFINDER_JQUERYUI_ICONS_SITE   := https://code.jquery.com/ui/1.13.3/themes/base/images
ELFINDER_JQUERYUI_ICON_444_SOURCE  := jquery-ui-icon-444444.png
ELFINDER_JQUERYUI_ICON_444_HASH   := bd0cd718fd018bf306c3327063eb10a7a929c0df9ac1b387192a574370c65625
ELFINDER_JQUERYUI_ICON_555_SOURCE  := jquery-ui-icon-555555.png
ELFINDER_JQUERYUI_ICON_555_HASH   := 7dfffbbe96d18869a4fd6266164671a7aa9e8396614b6008db01fcf71671fe02
ELFINDER_JQUERYUI_ICON_7620_SOURCE := jquery-ui-icon-777620.png
ELFINDER_JQUERYUI_ICON_7620_HASH  := 8f8775b19cabddeebc3d14d34cfe796bd30d7ccfbc8b3ddda4d920efba75e7f8
ELFINDER_JQUERYUI_ICON_7777_SOURCE := jquery-ui-icon-777777.png
ELFINDER_JQUERYUI_ICON_7777_HASH  := 3eb52a825d71a218153461e907580cc650a165aec2fc36e25bce5b177d5e77fb
ELFINDER_JQUERYUI_ICON_CC_SOURCE   := jquery-ui-icon-cc0000.png
ELFINDER_JQUERYUI_ICON_CC_HASH    := 8f98c3119565b3d2fabc79d090fe279fd73df290b18f347ff4afbab4f637216c
ELFINDER_JQUERYUI_ICON_FFF_SOURCE  := jquery-ui-icon-ffffff.png
ELFINDER_JQUERYUI_ICON_FFF_HASH   := 288abba3b3c02948d4b2317486b73ba46339ed4bd331a5ca40a4635477e7a32e

# ============================================================================
# Download elFinder source
# The upstream tag is the raw version number (e.g. "2.1.66").
# We store it locally using a Freetz-style unique filename.
# ============================================================================
$(DL_DIR)/$(ELFINDER_PKG_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_PKG_SOURCE) $(DL_DIR) $(ELFINDER_PKG_VERSION).tar.gz $(ELFINDER_SITE) $(ELFINDER_HASH)

# jQuery and jQuery UI are single-file downloads (no tarball extraction needed)
$(DL_DIR)/$(ELFINDER_JQUERY_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERY_SOURCE) $(DL_DIR) $(ELFINDER_JQUERY_SOURCE) $(ELFINDER_JQUERY_SITE) $(ELFINDER_JQUERY_HASH)

$(DL_DIR)/$(ELFINDER_JQUERYUI_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_SOURCE) $(DL_DIR) $(ELFINDER_JQUERYUI_SOURCE) $(ELFINDER_JQUERYUI_SITE) $(ELFINDER_JQUERYUI_HASH)

$(DL_DIR)/$(ELFINDER_JQUERYUI_CSS_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_CSS_SOURCE) $(DL_DIR) $(ELFINDER_JQUERYUI_CSS_SOURCE) $(ELFINDER_JQUERYUI_CSS_SITE) $(ELFINDER_JQUERYUI_CSS_HASH)

# jQuery UI icon images (stored with descriptive local names, installed as ui-icons_*.png)
$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_444_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_ICON_444_SOURCE) $(DL_DIR) ui-icons_444444_256x240.png $(ELFINDER_JQUERYUI_ICONS_SITE) $(ELFINDER_JQUERYUI_ICON_444_HASH)
$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_555_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_ICON_555_SOURCE) $(DL_DIR) ui-icons_555555_256x240.png $(ELFINDER_JQUERYUI_ICONS_SITE) $(ELFINDER_JQUERYUI_ICON_555_HASH)
$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_7620_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_ICON_7620_SOURCE) $(DL_DIR) ui-icons_777620_256x240.png $(ELFINDER_JQUERYUI_ICONS_SITE) $(ELFINDER_JQUERYUI_ICON_7620_HASH)
$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_7777_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_ICON_7777_SOURCE) $(DL_DIR) ui-icons_777777_256x240.png $(ELFINDER_JQUERYUI_ICONS_SITE) $(ELFINDER_JQUERYUI_ICON_7777_HASH)
$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_CC_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_ICON_CC_SOURCE) $(DL_DIR) ui-icons_cc0000_256x240.png $(ELFINDER_JQUERYUI_ICONS_SITE) $(ELFINDER_JQUERYUI_ICON_CC_HASH)
$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_FFF_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_JQUERYUI_ICON_FFF_SOURCE) $(DL_DIR) ui-icons_ffffff_256x240.png $(ELFINDER_JQUERYUI_ICONS_SITE) $(ELFINDER_JQUERYUI_ICON_FFF_HASH)

ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MOONO),y)
$(DL_DIR)/$(ELFINDER_THEME_MOONO_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_THEME_MOONO_SOURCE) $(DL_DIR) master.tar.gz $(ELFINDER_THEME_MOONO_SITE) $(ELFINDER_THEME_MOONO_HASH)
endif

ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_WINDOWS10),y)
$(DL_DIR)/$(ELFINDER_THEME_WIN10_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_THEME_WIN10_SOURCE) $(DL_DIR) master.tar.gz $(ELFINDER_THEME_WIN10_SITE) $(ELFINDER_THEME_WIN10_HASH)
endif

ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MATERIAL),y)
$(DL_DIR)/$(ELFINDER_THEME_MATERIAL_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_THEME_MATERIAL_SOURCE) $(DL_DIR) master.tar.gz $(ELFINDER_THEME_MATERIAL_SITE) $(ELFINDER_THEME_MATERIAL_HASH)
endif

ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_BOOTSTRAP),y)
$(DL_DIR)/$(ELFINDER_THEME_BOOTSTRAP_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_THEME_BOOTSTRAP_SOURCE) $(DL_DIR) master.tar.gz $(ELFINDER_THEME_BOOTSTRAP_SITE) $(ELFINDER_THEME_BOOTSTRAP_HASH)
endif

$(PKG_UNPACKED)

# Theme tarballs are extra prerequisites when enabled
$($(PKG)_ELFINDER_WEBDIR)/.installed: \
	$(DL_DIR)/$(ELFINDER_PKG_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERY_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_CSS_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_444_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_555_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_7620_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_7777_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_CC_SOURCE) \
	$(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_FFF_SOURCE) \
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MOONO)),    $(DL_DIR)/$(ELFINDER_THEME_MOONO_SOURCE)) \
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_WINDOWS10)),$(DL_DIR)/$(ELFINDER_THEME_WIN10_SOURCE)) \
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MATERIAL)), $(DL_DIR)/$(ELFINDER_THEME_MATERIAL_SOURCE)) \
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_BOOTSTRAP)),$(DL_DIR)/$(ELFINDER_THEME_BOOTSTRAP_SOURCE))

# Fixed variable names: captured at parse time so recipes expand correctly
# at execution time (after $(PKG) has been overwritten by later packages).
ELFINDER_PKG_CGI    := $($(PKG)_DEST_DIR)/usr/lib/cgi-bin/elfinder.cgi
ELFINDER_PKG_RC     := $($(PKG)_DEST_DIR)/etc/init.d/rc.elfinder
ELFINDER_PKG_CFGDIR := $($(PKG)_MAKE_DIR)/files/root

$(ELFINDER_PKG_CGI): $(ELFINDER_PKG_CFGDIR)/usr/lib/cgi-bin/elfinder.cgi
	$(INSTALL_FILE)
	chmod 755 $@

$(ELFINDER_PKG_RC): $(ELFINDER_PKG_CFGDIR)/etc/init.d/rc.elfinder
	$(INSTALL_FILE)
	chmod 755 $@

$(pkg)-precompiled: $($(PKG)_ELFINDER_WEBDIR)/.installed \
	$(ELFINDER_PKG_CGI) $(ELFINDER_PKG_RC)

# ============================================================================
# Install elFinder
# ============================================================================
$($(PKG)_ELFINDER_WEBDIR)/.installed:
	$(call UNPACK_TARBALL,$(DL_DIR)/$(ELFINDER_PKG_SOURCE),$(SOURCE_DIR))
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)

	# Copy elFinder core web assets (CSS, JS, images, sounds)
	cp -a $(ELFINDER_DIR)/css $(ELFINDER_PKG_ELFINDER_WEBDIR)/
	cp -a $(ELFINDER_DIR)/img $(ELFINDER_PKG_ELFINDER_WEBDIR)/
	cp -a $(ELFINDER_DIR)/js  $(ELFINDER_PKG_ELFINDER_WEBDIR)/
	cp -a $(ELFINDER_DIR)/sounds $(ELFINDER_PKG_ELFINDER_WEBDIR)/

	# Install jQuery and jQuery UI into the js/ and css/ directories
	cp $(DL_DIR)/$(ELFINDER_JQUERY_SOURCE)       $(ELFINDER_PKG_ELFINDER_WEBDIR)/js/jquery.min.js
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_SOURCE)     $(ELFINDER_PKG_ELFINDER_WEBDIR)/js/jquery-ui.min.js
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_CSS_SOURCE) $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/jquery-ui.min.css
	# jQuery UI icon images (css/images/ – relative path expected by jquery-ui.min.css)
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/images
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_444_SOURCE)  $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/images/ui-icons_444444_256x240.png
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_555_SOURCE)  $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/images/ui-icons_555555_256x240.png
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_7620_SOURCE) $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/images/ui-icons_777620_256x240.png
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_7777_SOURCE) $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/images/ui-icons_777777_256x240.png
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_CC_SOURCE)   $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/images/ui-icons_cc0000_256x240.png
	cp $(DL_DIR)/$(ELFINDER_JQUERYUI_ICON_FFF_SOURCE)  $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/images/ui-icons_ffffff_256x240.png

	# Copy PHP connector and all volume drivers
	cp -a $(ELFINDER_DIR)/php $(ELFINDER_PKG_ELFINDER_WEBDIR)/

	# Remove .dist templates (replaced by our Freetz-specific connector.php)
	$(RM) -f $(ELFINDER_PKG_ELFINDER_WEBDIR)/php/connector.minimal.php-dist
	$(RM) -f $(ELFINDER_PKG_ELFINDER_WEBDIR)/php/connector.maximal.php-dist

	# Remove unnecessary build/VCS artefacts
	$(RM) -rf $(ELFINDER_PKG_ELFINDER_WEBDIR)/.git*
	$(RM) -f  $(ELFINDER_PKG_ELFINDER_WEBDIR)/bower.json
	$(RM) -f  $(ELFINDER_PKG_ELFINDER_WEBDIR)/composer.json

	# Install Freetz-specific files (index.html + PHP connector template)
	@if [ -d "$(ELFINDER_PKG_MAKE_DIR)/files/root/usr/mww/elfinder" ]; then \
		cp -a $(ELFINDER_PKG_MAKE_DIR)/files/root/usr/mww/elfinder/* $(ELFINDER_PKG_ELFINDER_WEBDIR)/; \
	fi

	# Fix permissions: conf/ directory must be writable by the web server
	@if [ -d "$(ELFINDER_PKG_ELFINDER_WEBDIR)/conf" ]; then \
		chmod a+rw $(ELFINDER_PKG_ELFINDER_WEBDIR)/conf; \
		find $(ELFINDER_PKG_ELFINDER_WEBDIR)/conf -type f -exec chmod a+rw {} \; ; \
	fi

	# PHP .tmp directory (used by some volume drivers for caching)
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)/php/.tmp
	chmod a+rwx $(ELFINDER_PKG_ELFINDER_WEBDIR)/php/.tmp

	# Files storage directory (default local-fs root - will typically be replaced
	# at runtime by the configured ELFINDER_BASEDIR, but needs to exist)
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)/files
	chmod a+rwx $(ELFINDER_PKG_ELFINDER_WEBDIR)/files

	# -------------------------------------------------------------------------
	# Install optional 3rd-party themes into css/themes/<name>/
	# Each theme must provide a css/theme.css that overrides the default skin.
	# -------------------------------------------------------------------------
ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MOONO),y)
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/moono
	mkdir -p $(SOURCE_DIR)/elfinder-themes
	$(call UNPACK_TARBALL,$(DL_DIR)/$(ELFINDER_THEME_MOONO_SOURCE),$(SOURCE_DIR)/elfinder-themes)
	cp -a $(SOURCE_DIR)/elfinder-themes/elfinder-theme-moono-master/moono/css \
		$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/moono/
	$(RM) -rf $(SOURCE_DIR)/elfinder-themes/elfinder-theme-moono-master
endif

ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_WINDOWS10),y)
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/windows-10
	mkdir -p $(SOURCE_DIR)/elfinder-themes
	$(call UNPACK_TARBALL,$(DL_DIR)/$(ELFINDER_THEME_WIN10_SOURCE),$(SOURCE_DIR)/elfinder-themes)
	cp -a $(SOURCE_DIR)/elfinder-themes/elfinder-theme-windows-10-master/windows-10/css \
		$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/windows-10/
	cp -a $(SOURCE_DIR)/elfinder-themes/elfinder-theme-windows-10-master/windows-10/images \
		$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/windows-10/
	$(RM) -rf $(SOURCE_DIR)/elfinder-themes/elfinder-theme-windows-10-master
endif

ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MATERIAL),y)
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/material
	mkdir -p $(SOURCE_DIR)/elfinder-themes
	$(call UNPACK_TARBALL,$(DL_DIR)/$(ELFINDER_THEME_MATERIAL_SOURCE),$(SOURCE_DIR)/elfinder-themes)
	cp -a $(SOURCE_DIR)/elfinder-themes/elFinder-Material-Theme-master/Material/css \
		$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/material/
	cp -a $(SOURCE_DIR)/elfinder-themes/elFinder-Material-Theme-master/Material/font \
		$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/material/
	$(RM) -rf $(SOURCE_DIR)/elfinder-themes/elFinder-Material-Theme-master
endif

ifeq ($(FREETZ_PACKAGE_ELFINDER_WITH_THEME_BOOTSTRAP),y)
	# Bootstrap theme is inside the LibreICONS monorepo at themes/elFinder/
	mkdir -p $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/bootstrap
	mkdir -p $(SOURCE_DIR)/elfinder-themes
	$(call UNPACK_TARBALL,$(DL_DIR)/$(ELFINDER_THEME_BOOTSTRAP_SOURCE),$(SOURCE_DIR)/elfinder-themes)
	cp -a $(SOURCE_DIR)/elfinder-themes/LibreICONS-master/themes/elFinder/css \
		$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/bootstrap/
	cp -a $(SOURCE_DIR)/elfinder-themes/LibreICONS-master/themes/elFinder/img \
		$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/bootstrap/
	# Rename the main CSS to the conventional theme.css name
	@if [ -f "$(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/bootstrap/css/theme-bootstrap-libreicons-svg.css" ]; then \
		cp $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/bootstrap/css/theme-bootstrap-libreicons-svg.css \
		   $(ELFINDER_PKG_ELFINDER_WEBDIR)/css/themes/bootstrap/css/theme.css; \
	fi
	$(RM) -rf $(SOURCE_DIR)/elfinder-themes/LibreICONS-master
endif

	@echo ">>> elFinder web interface installed successfully" $(SILENT)
	touch $@

$(pkg):

$(pkg)-uninstall:
	$(RM) -r $(ELFINDER_PKG_ELFINDER_WEBDIR)
	$(RM) $(ELFINDER_PKG_CGI)
	$(RM) $(ELFINDER_PKG_RC)

$(PKG_FINISH)
