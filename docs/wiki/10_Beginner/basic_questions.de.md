# Basic Questions

## Good to Know

- Find a menu entry in menuconfig:
  Open menuconfig and press / to search.
- Flash an image via bootloader:
  Use tools/push_firmware (or tools/push_firmware -h for help).
  After a build, make push_firmware also works.
- Flash from a Raspberry Pi:
  Copy the image to the Pi, download the current push_firmware script, make it executable, then run it.
- In-memory image format:
  Usually not required anymore, because push_firmware can flash normal images directly.
- Unpack an image:
  Use tools/fwdu unpack your.image.
- Use older modem/DSL driver files:
  Extract from a source image, place files into an addon tree, and enable the addon.
- Replace kernel:
  Avoid this unless you clearly understand why you need it.
- Build kernel modules:
  Select device/firmware in menuconfig, then enable modules in kernel-menuconfig.
- Execute files on external storage:
  If needed, enable the patch that removes noexec for external storage.
- Run custom commands at boot/shutdown:
  Use scripts in /tmp/flash/mod as appropriate for your setup.
- Edit read-only files/directories:
  Use helper tools such as vix/vimx/nanox and araw.
- Customize MOTD:
  Place your script at /tmp/flash/mod/motd and regenerate via rc.mod if needed.
- Legacy menu layout:
  Run make menuconfig-single.

## Practical Advice

1. Start from a minimal, reproducible setup.
2. Change one thing at a time and keep notes.
3. Keep recovery files ready before flashing.
4. Prefer stable package combinations first, then expand.
