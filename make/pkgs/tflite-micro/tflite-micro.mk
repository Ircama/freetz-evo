# TensorFlow Lite for Microcontrollers (TFLM)
# Uses the official project-generation script to create a flat source tree,
# then cross-compiles it with the freetz toolchain into:
#   - libtflm.a   (static library, installed into staging dir)
#   - headers      (installed into staging dir under usr/include/tflite-micro)
# Optionally, a hello_world binary can be built and installed on the target.
#
# NOTE: libtflm.a is a STATIC library - it only goes into the staging area.
# It does NOT appear in "Shared libraries" of menuconfig.  Other packages
# that want to link against it can reference $(TARGET_TOOLCHAIN_STAGING_DIR).
#
# Build requires Python 3 on the host.  numpy and Pillow are installed
# automatically into the freetz host Python during tree generation.

# Pinned to commit f5302ed (Mar 18 2026)
TFLITE_MICRO_COMMIT := f5302ed4fa99b7ec697e578057a1f61445a442fe

$(call PKG_INIT_BIN, 20260318)
# TFLM is compiled with -std=c++17, which requires GCC >= 7; the old GCC 4.6.4
# toolchain rejects it ("cc1plus: error: unrecognized command line option
# '-std=c++17'"). There is no FREETZ_TARGET_GCC_7_MIN symbol, so the package is
# gated on FREETZ_TARGET_GCC_8_MIN in Config.in. NOT a uClibc gate: uClibc
# 1.0.14 with GCC 5.5 would also fail on -std=c++17, so a uClibc gate would be
# wrong; the GCC gate keeps uClibc >= 1.0.58 (GCC 13.4) working with no
# regression.
$(PKG)_SOURCE:=$(pkg)-$($(PKG)_VERSION).tar.gz
$(PKG)_HASH:=f8073aa2e768f1429fe68b9d1d4b61a61496be4493d9352b9a6e56cc05052de4
$(PKG)_SITE:=https://github.com/tensorflow/tflite-micro/archive/$(TFLITE_MICRO_COMMIT)
$(PKG)_SOURCE_DOWNLOAD_NAME:=$(pkg)-$($(PKG)_VERSION).tar.gz
### WEBSITE:=https://github.com/tensorflow/tflite-micro
### MANPAGE:=https://www.tensorflow.org/lite/microcontrollers
### CHANGES:=https://github.com/tensorflow/tflite-micro/commits/main
### CVSREPO:=https://github.com/tensorflow/tflite-micro
### STEWARD:=Ircama

$(PKG)_BUILD_PREREQ := python3

$(PKG)_TARBALL_STRIP_COMPONENTS := 1

# Eagerly-evaluated (:=) shortcuts - locked before PKG/pkg is overwritten
# by the next included package, so recipe bodies always expand correctly.
TFLITE_MICRO_TREE_DIR        := $(TFLITE_MICRO_DIR)/tflm-tree
TFLITE_MICRO_GEN_DIR         := $(TFLITE_MICRO_DIR)/gen
TFLITE_MICRO_LIB_STAGING_DIR := $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/lib
TFLITE_MICRO_INC_STAGING_DIR := $(TARGET_TOOLCHAIN_STAGING_DIR)/usr/include/tflite-micro
TFLITE_MICRO_TARGET_HELLO_BINARY := $(TFLITE_MICRO_DEST_DIR)/usr/bin/tflm-hello-world

$(PKG_SOURCE_DOWNLOAD)
$(PKG_UNPACKED)
$(PKG_CONFIGURED_NOP)

# ---------------------------------------------------------------------------
# Step 1: install Python build prerequisites, then run the project-generation
# script to create a flat source tree in $(TFLITE_MICRO_TREE_DIR).
# ---------------------------------------------------------------------------
$(TFLITE_MICRO_TREE_DIR)/.generated: $(TFLITE_MICRO_DIR)/.configured
	@$(call _ECHO,installing Python build prerequisites)
	@$(call _ECHO,generating tflm source tree)
	$(call HostPython3, \
		export PATH="$(HOST_TOOLS_DIR)/usr/bin:$$PATH"; \
		$(HOST_PYTHON3_BIN) -m pip --version >/dev/null 2>&1 || $(HOST_PYTHON3_BIN) -m ensurepip --upgrade; \
		$(HOST_PYTHON3_BIN) -m pip install --disable-pip-version-check --no-input --upgrade \
			--target=$(HOST_TOOLS_DIR)/usr/lib/python$(PYTHON3_MAJOR_VERSION) numpy Pillow; \
		cd $(TFLITE_MICRO_DIR); \
	, tensorflow/lite/micro/tools/project_generation/create_tflm_tree.py \
			-e hello_world \
			$(CURDIR)/$(TFLITE_MICRO_TREE_DIR))
	@# array.h is not copied by create_tflm_tree.py but is required by kernel_util.cc
	cp $(TFLITE_MICRO_DIR)/tensorflow/lite/array.h \
		$(TFLITE_MICRO_TREE_DIR)/tensorflow/lite/array.h
	@touch $@

# ---------------------------------------------------------------------------
# Step 2: cross-compile all sources into libtflm.a (shell loop - sources
# are unknown at parse time, discovered only after tree generation)
# ---------------------------------------------------------------------------
TFLITE_MICRO_INC := -I$(TFLITE_MICRO_TREE_DIR) \
	-I$(TFLITE_MICRO_TREE_DIR)/third_party/gemmlowp \
	-I$(TFLITE_MICRO_TREE_DIR)/third_party/flatbuffers/include \
	-I$(TFLITE_MICRO_TREE_DIR)/third_party/ruy \
	-I$(TFLITE_MICRO_TREE_DIR)/third_party/kissfft

$(TFLITE_MICRO_DIR)/gen/libtflm.a: $(TFLITE_MICRO_TREE_DIR)/.generated
	@$(call _ECHO,building libtflm.a)
	mkdir -p $(TFLITE_MICRO_GEN_DIR)/obj
	find $(TFLITE_MICRO_TREE_DIR)/tensorflow $(TFLITE_MICRO_TREE_DIR)/third_party \
		\( -name '*.cc' -o -name '*.c' \) | sort | \
	while read src; do \
		rel=$${src#$(TFLITE_MICRO_TREE_DIR)/}; \
		obj=$(TFLITE_MICRO_GEN_DIR)/obj/$${rel%.*}.o; \
		mkdir -p $$(dirname $$obj); \
		case "$$src" in \
		*.cc) \
			$(TARGET_CXX) $(TARGET_CFLAGS) -std=c++17 \
				-fno-rtti -fno-exceptions -ffunction-sections -fdata-sections \
				$(TFLITE_MICRO_INC) \
				-c $$src -o $$obj || exit 1 ;;  \
		*.c) \
			$(TARGET_CC) $(TARGET_CFLAGS) \
				-ffunction-sections -fdata-sections \
				$(TFLITE_MICRO_INC) \
				-c $$src -o $$obj || exit 1 ;; \
		esac; \
	done
	find $(TFLITE_MICRO_GEN_DIR)/obj -name '*.o' | sort | \
		xargs $(TARGET_AR) rcs $(TFLITE_MICRO_DIR)/gen/libtflm.a
	$(TARGET_RANLIB) $(TFLITE_MICRO_DIR)/gen/libtflm.a

# ---------------------------------------------------------------------------
# Step 3 (optional): hello_world example binary
# ---------------------------------------------------------------------------
ifeq ($(strip $(FREETZ_PACKAGE_TFLITE_MICRO_HELLO_WORLD)),y)

$(TFLITE_MICRO_DIR)/gen/hello_world: $(TFLITE_MICRO_DIR)/gen/libtflm.a
	@$(call _ECHO,building hello_world example)
	# Keep hello_world_test.cc (it provides main), skip only benchmarks.
	find $(TFLITE_MICRO_TREE_DIR)/examples/hello_world -name '*.cc' \
		! -name '*benchmark.cc' | sort | \
	while read src; do \
		rel=$${src#$(TFLITE_MICRO_TREE_DIR)/}; \
		obj=$(TFLITE_MICRO_GEN_DIR)/obj/$${rel%.*}.o; \
		mkdir -p $$(dirname $$obj); \
		$(TARGET_CXX) $(TARGET_CFLAGS) -std=c++17 \
			-fno-rtti -fno-exceptions -ffunction-sections -fdata-sections \
			$(TFLITE_MICRO_INC) \
			-I$(TFLITE_MICRO_TREE_DIR)/examples/hello_world \
			-c $$src -o $$obj || exit 1; \
	done
	objs=`find $(TFLITE_MICRO_GEN_DIR)/obj/examples/hello_world -name '*.o' | sort`; \
	$(TARGET_CXX) $(TARGET_CFLAGS) -Wl,--gc-sections \
		$$objs $(TFLITE_MICRO_DIR)/gen/libtflm.a -lm -o $@

$(TFLITE_MICRO_TARGET_HELLO_BINARY): $(TFLITE_MICRO_DIR)/gen/hello_world
	$(INSTALL_BINARY_STRIP)

endif # FREETZ_PACKAGE_TFLITE_MICRO_HELLO_WORLD

# ---------------------------------------------------------------------------
# Install static library + headers into the staging area.
# (libtflm.a is a static lib - it is not installed to the target filesystem.)
# ---------------------------------------------------------------------------
$(TFLITE_MICRO_LIB_STAGING_DIR)/libtflm.a: $(TFLITE_MICRO_DIR)/gen/libtflm.a
	mkdir -p $(TFLITE_MICRO_LIB_STAGING_DIR)
	cp -a $< $@
	mkdir -p $(TFLITE_MICRO_INC_STAGING_DIR)
	cd $(TFLITE_MICRO_TREE_DIR) && \
	find tensorflow third_party \( -name '*.h' -o -name '*.hpp' \) | \
	while read f; do \
		dst=$(TFLITE_MICRO_INC_STAGING_DIR)/$$f; \
		mkdir -p $$(dirname $$dst); \
		cp $$f $$dst; \
	done

# ---------------------------------------------------------------------------
# Standard freetz phony targets
# ---------------------------------------------------------------------------

# $(pkg) = "install to staging" target, used as dependency by other packages
$(pkg): $(TFLITE_MICRO_LIB_STAGING_DIR)/libtflm.a

# $(pkg)-precompiled = built by the normal freetz build flow.
# Static lib goes to staging only; hello_world binary goes to target if enabled.
$(pkg)-precompiled: $(TFLITE_MICRO_LIB_STAGING_DIR)/libtflm.a \
                    $(if $(FREETZ_PACKAGE_TFLITE_MICRO_HELLO_WORLD),$(TFLITE_MICRO_TARGET_HELLO_BINARY))

$(pkg)-clean:
	$(RM) -r $(TFLITE_MICRO_GEN_DIR) $(TFLITE_MICRO_TREE_DIR)
	$(RM) $(TFLITE_MICRO_LIB_STAGING_DIR)/libtflm.a
	$(RM) -r $(TFLITE_MICRO_INC_STAGING_DIR)

$(pkg)-uninstall:
	$(RM) $(TFLITE_MICRO_TARGET_HELLO_BINARY)
	$(RM) -r $(TFLITE_MICRO_INC_STAGING_DIR)
	$(RM) $(TFLITE_MICRO_LIB_STAGING_DIR)/libtflm.a

$(PKG_FINISH)
