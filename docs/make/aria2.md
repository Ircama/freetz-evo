# aria2 1.37.0/AriaNg 1.3.13 (HTTP(s)/(s)FTP/Torrent/Metalink downloader)
  - Homepage: [https://aria2.github.io/](https://aria2.github.io/)
  - Manpage: [https://aria2.github.io/manual/en/html/](https://aria2.github.io/manual/en/html/)
  - Changelog: [https://github.com/aria2/aria2/releases](https://github.com/aria2/aria2/releases)
  - Repository: [https://github.com/aria2/aria2.git](https://github.com/aria2/aria2.git)
  - Package: [master/make/pkgs/aria2/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/aria2/)
  - Steward: -
  - Maintainer: [@Ircama](https://github.com/Ircama)

**Build notes:**

aria2c 1.37.0 crashes with SIGFPE on MIPS when built with uClibc 1.0.57

aria2c terminates with Floating point exception (SIGFPE) immediately on startup when compiled against uClibc 1.0.57 on MIPS. The crash occurs before main() returns, during constructors execution.

Workaround: linking against jemalloc instead of uClibc's built-in allocator prevents the crash, suggesting the issue lies in uClibc's memory allocator implementation.
