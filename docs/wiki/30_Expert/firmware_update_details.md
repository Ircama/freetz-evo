# Firmware Update Flow

During a firmware update through the AVM web interface, roughly the
following happens. This description does not claim to be complete.

-   The whole process is controlled by the binary
    `/usr/www/cgi-bin/firmwarecfg`, which is called by the web server.
-   `firmwarecfg` first calls the shell script `/bin/prepare_fwupgrade`
    to stop several services and free RAM for the firmware archive. Traces
    of possible earlier updates in the RAM disk (`/var`) are also removed.
    `prepare_fwupgrade` is called with either *start* or
    *start_from_internet*, depending on whether the update should be loaded
    from AVM's site or from disk. The main difference is that the DSL
    daemon `dsld` is not stopped at first in the second case.
-   After most FRITZ!Box activity has been shut down, the firmware image is
    transferred to the RAM disk and unpacked there with `tar`. During this
    step, the package's digital signature is checked. If it cannot be
    verified correctly, or if it is missing, the familiar warning about
    unapproved firmware is shown later in the web interface. At first, the
    web-interface user is simply asked by `firmwarecfg` whether the
    firmware should be installed anyway. Assume the user confirms.
-   The most important files from the unpacked firmware archive are now:
    -   `/var/install`
    -   `/var/tmp/kernel.image`
    -   `/var/tmp/filesystem.image`
-   The last two files exist only for a "real" update, not for a pseudo
    update such as enabling Telnet or installing software like the
    *LCR Updater*. In many cases `filesystem.image` has length zero
    because `kernel.image` contains all data required for flashing.
-   `/bin/prepare_fwupgrade` is called a second time, now with parameter
    *end*. The remaining services that could interfere with the update,
    for example by accessing flash storage, are stopped for good.
-   The shell script `/var/install`, unpacked from the firmware image, is
    called. It does quite a lot, for example:
-   It performs checks that determine the current state of the box, how
    the flash area is partitioned, and what needs to be done to prepare
    the update. Depending on what the script finds, it returns one of
    these values at the end:
    -   *INSTALL_SUCCESS_NO_REBOOT (0)*: everything is okay, no reboot is
        required. This should be returned only if neither filesystem nor
        kernel in flash is changed.
    -   *INSTALL_SUCCESS_REBOOT = 1*: the standard value for real firmware
        updates. Everything is okay, reboot the box.
    -   *INSTALL_WRONG_HARDWARE = 2*: reject installation because the
        hardware does not match the firmware image, for example wrong
        Annex or wrong OEM.
    -   *INSTALL_KERNEL_CHECKSUM = 3*: invalid kernel checksum. If the two
        image files, kernel and filesystem, exist, their CRC checksums are
        verified by calling `/var/chksum`, which is also included in AVM
        packages. If the checksums are invalid, not to be confused with the
        signature mentioned above, no update takes place.
    -   *INSTALL_FILESYSTEM_CHECKSUM = 4*: see the previous point.
    -   *INSTALL_URLADER_CHECKSUM = 5*: would mean that the new Urlader to
        be installed has a wrong checksum. Firmware updates usually do not
        contain a new Urlader.
    -   *INSTALL_OTHER_ERROR = 6*: other error.
    -   *INSTALL_FIRMWARE_VERSION = 7*: problem with the current firmware
        version. Either the current version cannot be detected for some
        reason, or the version jump is too large because an ancient version
        is installed and an intermediate update is needed first.
    -   *INSTALL_DOWNGRADE_NEEDED = 8*: an attempt is being made to install
        firmware with a lower version number. Current firmware normally
        blocks this, so a recovery or manual downgrade is required to get
        around it. Another option would be to comment out the check in the
        script.
-   The script also has a switch *-f*, which makes it accept any firmware
    version number and can therefore perform a downgrade. As far as known,
    this switch cannot be set through the web interface. It is probably
    used by AVM's recovery tools. Using this switch also makes the install
    script delete the settings in flash, resetting the box to factory
    defaults. In principle this could be prevented by commenting it out in
    the script, but often it makes sense to keep it. A downgrade means that
    existing settings for features of a newer firmware version may be
    interpreted incorrectly by an older firmware, which in the worst case
    could make the box hang during startup and require recovery.
-   At the end, special cases are handled if necessary, for example
    removing obsolete settings or converting old dialing rules.
-   During the process, the script also writes another script to
    `/var/post_install`. This is later called indirectly by the leading
    process `firmwarecfg` through `init reboot`, unless one of the error
    return values prevents it. `post_install` sets environment variables
    needed for flashing and loads the module contained in the firmware
    image: `/var/flash_update.o` for kernel 2.4 or `/var/flash_update.ko`
    for kernel 2.6.
-   There is also a standard `/var/post_install`, extracted from
    `/var.tar` during system startup and called before every reboot. The
    call mechanism through `/etc/inittab` is the same, but the script
    content is completely different from the special pre-flash version.
-   The actual flash process now happens, if necessary.

After the possible reboot, the box either runs a new firmware or has the
desired additional functionality installed. What `/var/install` does and
which return value it provides is fundamentally up to each firmware
builder. The other framework conditions are as described above.

[Alexander Kriegisch (kriegaex)](http://www.ip-phone-forum.de/member.php?u=117253)


