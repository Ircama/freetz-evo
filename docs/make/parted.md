# parted 3.6 (binary only)
  - Toolchain: needs `130-atari-no-locale-api.patch` on uClibc without full locale support (0.9.32, 1.0.14); works out of the box on uClibc 1.0.58
  - Homepage: [https://www.gnu.org/software/parted/](https://www.gnu.org/software/parted/)
  - Manpage: [https://www.gnu.org/software/parted/manual/](https://www.gnu.org/software/parted/manual/)
  - Changelog: [https://git.savannah.gnu.org/cgit/parted.git/tree/NEWS](https://git.savannah.gnu.org/cgit/parted.git/tree/NEWS)
  - Repository: [https://git.savannah.gnu.org/cgit/parted.git](https://git.savannah.gnu.org/cgit/parted.git)
  - Package: [master/make/pkgs/parted/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/parted/)
  - Steward: Ircama
GNU Parted is a command-line partition editor.

Typical tools included by this package:

- `parted`: interactive partition editor
- `partprobe`: asks the kernel to re-read the partition table
