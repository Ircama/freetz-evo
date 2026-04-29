# Targets of Freetz's `make`


```
help                                    Shows docs/wiki/20_Advanced/make_targets.md

menuconfig                              Configuration with Ncurses (needs ncurses-devel)
menuconfig-single                       Configuration with Ncurses (single menu)
menuconfig-nocache                      Configuration with Ncurses (without caching .in files)
nconfig                                 Alternative configuration (needs ncurses-devel)
nconfig-single                          Alternative configuration (single menu)
gconfig                                 Configuration with GTK+2 (needs libglade2-devel)
xconfig                                 Configuration with QT5 (needs qt5-qtbase-devel)
config                                  Configuration (dialog)

olddefconfig                            Updates the existing .config file automatically
oldconfig                               Updates the existing .config file interactively
reuseconfig                             Removes device- and toolchain-related settings from the .config file
allnoconfig                             Sets everything to (n)o
allyesconfig                            Sets everything to (y)es
listnewconfig                           Shows a list of new configuration symbols, one per line
config-compress                         Keeps only non-default selections and no signing key password

config-clean-deps                       Deselects everything that is not mandatory
config-clean-deps-keep-busybox          Deselects everything except BusyBox applets
config-clean-deps-modules               Deselects all kernel modules
config-clean-deps-libs                  Deselects all libraries
config-clean-deps-busybox               Deselects all BusyBox applets
config-clean-deps-terminfo              Deselects all Terminfo files

cacheclean                              Removes small cached files and directories
clean                                   Removes unpacked images and some cache files
dirclean                                Cleans sources, except tools and .config
distclean                               Cleans everything except the download directory

$(pkg)-unpacked                         Unpacks and patches $(pkg)
$(pkg)-precompiled                      Compiles package/library $(pkg)
$(pkg)-recompile                        Recompiles package/library $(pkg)
$(pkg)-autofix                          Adjusts patches of package/library $(pkg)
$(pkg)-dirclean                         Removes the build directory of $(pkg)
$(pkg)-distclean                        Removes the build directory and all target files of $(pkg)

kernel-menuconfig                       Configuration of the selected kernel
kernel-precompiled                      Compiles the selected kernel
kernel-dirclean                         Cleans all files of the selected kernel

tools-push_firmware                     Builds the tools required by push_firmware (pfp)
tools                                   Builds the tools required by the current selection
tools-all                               Builds all available Freetz tools
tools-allexcept-local                   Builds all non-local Freetz tools (dl-tools)
tools-distclean-local                   Cleans all local tools (dl-tools)
tools-dirclean                          Cleans all Freetz tools

uclibc-autofix                          Adjusts patches of the selected uClibc
uclibc-menuconfig                       Configuration of the selected uClibc
uclibc-olddefconfig                     Updates the selected uClibc .config file

firmware-nocompile                      Creates firmware without packages and libraries
mirror                                  Downloads all selected package source files
release                                 Creates a release file (change .version first)

push_firmware                           Calls tools/push_firmware with images/latest.image (pf)
                                        For more options, run: tools/push_firmware -h
recover                                 Calls tools/recover-eva with the configured firmware
```

