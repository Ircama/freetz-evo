# Basic Questions

### Good to Know

- Find an entry in `menuconfig`/`kconfig`:<br>
  Open `menuconfig` and press `/` to search.
- Flash an AVM or modified image via the bootloader:<br>
  Run `tools/push_firmware`; use `tools/push_firmware -h` for help.
  After a successful build, `make push_firmware` also works.
- Flash from a Raspberry Pi:<br>
  Copy the created image to the Raspberry Pi. Download the current
  `push_firmware` script:
  ```
  wget https://raw.githubusercontent.com/Freetz-NG/freetz-ng/master/tools/push_firmware
  ```
  Make it executable with `chmod +x push_firmware`, then run it with
  `./push_firmware ...`.
- In-memory image format:<br>
  It is usually no longer needed because `push_firmware` can flash normal
  images directly.
- Unpack an image:<br>
  Use `tools/fwdu unpack the.image` to extract the inner filesystem.
- Use older modem/DSL driver files:<br>
  Unpack the source image with `fwdu`. Copy the required files, including
  their directory structure, into a subdirectory of Freetz's `addon/`
  directory. Enable the new addon through an `addon/*.pkg` file.
  The required files depend on the device. Examples:
  - For 7490, the complete `/lib/modules/dsp_vr9/` directory
  - For 7590, the complete `/lib/modules/dsp_vr11/` directory
- Replace the kernel:<br>
  Avoid this unless you clearly understand why you need it. You will never
  have exactly the kernel expected by AVM; patches or options may be missing.
- Build kernel modules:<br>
  - If you do not know which module a device requires, attach the device to
    a Linux PC and check it with commands such as `dmesg`, `lsusb`, and
    `lsmod`.
  - Make sure the latest source code for your device is available at
    <https://osp.avm.de/> and integrated into Freetz. If it is not, ask AVM
    at <fritzbox_info@avm.de>.
  - Run `make menuconfig` and select your FRITZ!Box and FRITZ!OS version.
    Then enable the module as `M(odule)` with `make kernel-menuconfig`; use
    `/` to search.
  - To avoid repeating that configuration every time, you can submit your
    changes in `make/linux/configs/freetz/` as a pull request.
  - To copy the module file into the image, select it with `make menuconfig`.
    If it is not available there, add its name to `Kernel modules` ->
    `Own Modules`.
- Execute files on storage media:<br>
  AVM disables this by default on some storage. To allow it, select the
  `Drop noexec for (external) storages` patch. Internal storage is always
  executable with Freetz.
- Execute commands during shutdown or reboot:<br>
  Put an executable script at `/tmp/flash/mod/shutdown`.
- Edit read-only files:<br>
  Use wrapper scripts such as `vix`, `vimx`, and `nanox`.
- Make read-only directories writable:<br>
  Use `araw /some/random/path/`; it copies the directory to RAM and mounts it
  writable.
- Change the message of the day:<br>
  Put your own script at `/tmp/flash/mod/motd`. The MOTD is generated once at
  boot. To update it regularly, run `/mod/etc/init.d/rc.mod motd`, for
  example through cron.
- Use the legacy package layout in `menuconfig`:<br>
  Run `make menuconfig-single`.
- Handle Git basics:<br>
  A quick beginner-friendly starting point is <https://xkcd.com/1597/>.

### Practical Advice

1. Start from a minimal, reproducible setup.
2. Change one thing at a time and keep notes.
3. Keep recovery files ready before flashing.
4. Prefer stable package combinations first, then expand.
