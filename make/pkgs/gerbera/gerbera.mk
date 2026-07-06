$(call PKG_INIT_BIN, 3.2.1)
### STEWARD:=Ircama

$(PKG)_SOURCE_DOWNLOAD_NAME:=v$($(PKG)_VERSION).tar.gz
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=6b89d0c416b6d98e34634e5b1121f340315d60b088e9e6b2fca423488760030f
$(PKG)_SITE:=https://github.com/gerbera/gerbera/archive/refs/tags
### WEBSITE:=https://gerbera.io/
### CHANGES:=https://github.com/gerbera/gerbera/releases
### CVSREPO:=https://github.com/gerbera/gerbera

$(PKG)_BINARY:=$($(PKG)_DIR)/build/gerbera
$(PKG)_TARGET_BINARY:=$($(PKG)_DEST_DIR)/usr/bin/gerbera
$(PKG)_INSTALLED_STAMP:=$($(PKG)_DIR)/.installed

$(PKG)_DEPENDS_ON += cmake-host
$(PKG)_DEPENDS_ON += libupnp
$(PKG)_DEPENDS_ON += libfmt
$(PKG)_DEPENDS_ON += spdlog
$(PKG)_DEPENDS_ON += jsoncpp
$(PKG)_DEPENDS_ON += libzip
$(PKG)_DEPENDS_ON += sqlite
$(PKG)_DEPENDS_ON += pugixml
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_CURL),curl)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_AVCODEC),ffmpeg)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_EXIF),libexif)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_TAGLIB),taglib)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_MAGIC),libmagic)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_NPUPNP),libnpupnp)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_JS),duktape)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_FFMPEGTHUMBNAILER),libffmpegthumbnailer)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_EXIV2),exiv2)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_MATROSKA),libmatroska)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_WAVPACK),libwavpack)
$(PKG)_DEPENDS_ON += $(if $(FREETZ_PACKAGE_GERBERA_WITH_ICU),icu)

$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_CURL
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_AVCODEC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_EXIF
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_INOTIFY
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_JS
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_STATIC_LIBUPNP
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_TAGLIB
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_MAGIC
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_NPUPNP
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_FFMPEGTHUMBNAILER
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_EXIV2
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_MATROSKA
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_WAVPACK
$(PKG)_REBUILD_SUBOPTS += FREETZ_PACKAGE_GERBERA_WITH_ICU

$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_INSTALL_PREFIX="/usr"
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_BUILD_TYPE=Release
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SKIP_RPATH=YES
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_SYSTEM_NAME=Linux
$(PKG)_CONFIGURE_OPTIONS += -DCMAKE_CROSSCOMPILING=ON
$(PKG)_CONFIGURE_OPTIONS += -DWITH_NPUPNP=$(if $(FREETZ_PACKAGE_GERBERA_WITH_NPUPNP),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_ICU=$(if $(FREETZ_PACKAGE_GERBERA_WITH_ICU),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_JS=$(if $(FREETZ_PACKAGE_GERBERA_WITH_JS),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_AVCODEC=$(if $(FREETZ_PACKAGE_GERBERA_WITH_AVCODEC),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_WAVPACK=$(if $(FREETZ_PACKAGE_GERBERA_WITH_WAVPACK),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_FFMPEGTHUMBNAILER=$(if $(FREETZ_PACKAGE_GERBERA_WITH_FFMPEGTHUMBNAILER),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_EXIF=$(if $(FREETZ_PACKAGE_GERBERA_WITH_EXIF),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_EXIV2=$(if $(FREETZ_PACKAGE_GERBERA_WITH_EXIV2),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_MATROSKA=$(if $(FREETZ_PACKAGE_GERBERA_WITH_MATROSKA),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_SYSTEMD=OFF
$(PKG)_CONFIGURE_OPTIONS += -DWITH_LASTFM=OFF
$(PKG)_CONFIGURE_OPTIONS += -DWITH_ONLINE_SERVICES=OFF
$(PKG)_CONFIGURE_OPTIONS += -DWITH_ZIP=OFF
$(PKG)_CONFIGURE_OPTIONS += -DWITH_INOTIFY=$(if $(FREETZ_PACKAGE_GERBERA_WITH_INOTIFY),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DSTATIC_LIBUPNP=$(if $(FREETZ_PACKAGE_GERBERA_STATIC_LIBUPNP),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_DEBUG=OFF
$(PKG)_CONFIGURE_OPTIONS += -DWITH_TESTS=OFF
$(PKG)_CONFIGURE_OPTIONS += -DWITH_TAGLIB=$(if $(FREETZ_PACKAGE_GERBERA_WITH_TAGLIB),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_MAGIC=$(if $(FREETZ_PACKAGE_GERBERA_WITH_MAGIC),ON,OFF)
$(PKG)_CONFIGURE_OPTIONS += -DWITH_CURL=$(if $(FREETZ_PACKAGE_GERBERA_WITH_CURL),ON,OFF)

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)

# Gerbera uses CMake with out-of-tree build
$($(PKG)_DIR)/.configured: $($(PKG)_DIR)/.unpacked
	@$(call _ECHO,configuring)
	# uClibc does not provide std::strerror or std::memcpy in C++ namespace, replace with C versions
	find $(GERBERA_DIR)/src -name '*.h' -o -name '*.cc' -o -name '*.cpp' | xargs sed -i \
		-e 's/std::strerror/strerror/g' \
		-e 's/std::memcpy/memcpy/g' \
		-e 's/std::memmove/memmove/g' \
		-e 's/std::memcmp/memcmp/g' \
		-e 's/std::memset/memset/g' \
		-e 's/std::strncpy/strncpy/g' \
		-e 's/std::strncat/strncat/g' \
		-e 's/std::strcat/strcat/g' \
		-e 's/std::strcpy/strcpy/g' \
		-e 's/std::strtok/strtok/g' \
		-e 's/std::strncmp/strncmp/g' \
		-e 's/std::strcmp/strcmp/g' \
		-e 's/std::strlen/strlen/g' \
		-e 's/std::strchr/strchr/g' \
		-e 's/std::strrchr/strrchr/g' \
		-e 's/std::strstr/strstr/g' \
		-e 's/std::strspn/strspn/g' \
		-e 's/std::strcspn/strcspn/g' \
	2>/dev/null || true
	# fmt >= 11 requires explicit include for fmt::format (deprecated in core.h)
	find $(GERBERA_DIR)/src -name '*.h' -o -name '*.cc' | xargs sed -i 's|#include <fmt/core.h>|#include <fmt/format.h>|g' 2>/dev/null || true
	mkdir -p $(GERBERA_DIR)/build
	cd $(GERBERA_DIR)/build && \
		$(TARGET_CONFIGURE_ENV) $(MAKE_ENV) $(CMAKE) \
		$(GERBERA_CONFIGURE_OPTIONS) \
		..
	@touch $@

$($(PKG)_BINARY): $($(PKG)_DIR)/.configured
	$(SUBMAKE) -C $(GERBERA_DIR)/build

$($(PKG)_TARGET_BINARY) $($(PKG)_INSTALLED_STAMP): $($(PKG)_BINARY)
	$(SUBMAKE) -C $(GERBERA_DIR)/build \
		DESTDIR="$(FREETZ_BASE_DIR)/$(GERBERA_DEST_DIR)" \
		install
	# Remove unnecessary files
	$(RM) -r $(GERBERA_DEST_DIR)/etc/init.d 2>/dev/null || true
	$(RM) -r $(GERBERA_DEST_DIR)/usr/share/gerbera/web 2>/dev/null || true
	@touch $@

$(pkg):

$(pkg)-precompiled: \
	$(if $(FREETZ_PACKAGE_GERBERA_DAEMON),$($(PKG)_INSTALLED_STAMP))

$(pkg)-clean:
	-$(SUBMAKE) -C $(GERBERA_DIR)/build clean 2>/dev/null || true
	$(RM) $($(PKG)_INSTALLED_STAMP)

$(pkg)-uninstall:
	$(RM) $(GERBERA_TARGET_BINARY)

$(PKG_FINISH)
