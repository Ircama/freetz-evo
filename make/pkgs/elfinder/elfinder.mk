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

# ============================================================================
# Download elFinder source
# The upstream tag is the raw version number (e.g. "2.1.66").
# We store it locally using a Freetz-style unique filename.
# ============================================================================
$(DL_DIR)/$(ELFINDER_PKG_SOURCE): | $(DL_DIR)
	$(DL_TOOL) -o $(ELFINDER_PKG_SOURCE) $(DL_DIR) $(ELFINDER_PKG_VERSION).tar.gz $(ELFINDER_SITE) $(ELFINDER_HASH)

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
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MOONO)),    $(DL_DIR)/$(ELFINDER_THEME_MOONO_SOURCE)) \
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_WINDOWS10)),$(DL_DIR)/$(ELFINDER_THEME_WIN10_SOURCE)) \
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_MATERIAL)), $(DL_DIR)/$(ELFINDER_THEME_MATERIAL_SOURCE)) \
	$(if $(filter y,$(FREETZ_PACKAGE_ELFINDER_WITH_THEME_BOOTSTRAP)),$(DL_DIR)/$(ELFINDER_THEME_BOOTSTRAP_SOURCE))

$(pkg)-precompiled: $($(PKG)_ELFINDER_WEBDIR)/.installed

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

$(PKG_FINISH)
