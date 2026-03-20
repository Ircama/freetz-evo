### WEBSITE:=https://uclibc-ng.org/
### MANPAGE:=https://uclibc-ng.org/docs/
### CHANGES:=https://gogs.waldemar-brodkorb.de/oss/uclibc-ng/releases
### CVSREPO:=https://cgit.uclibc-ng.org/cgi/cgit/uclibc-ng.git/
### SUPPORT:=fda77
### VERSION:=0.9.28/0.9.29/0.9.32.1/0.9.33.2/1.0.14/1.0.57

Build notes:

aria2c 1.37.0 crashes with SIGFPE on MIPS when built with uClibc 1.0.57

aria2c terminates with Floating point exception (SIGFPE) immediately on startup when compiled against uClibc 1.0.57 on MIPS. The crash occurs before main() returns, during constructors execution.

Workaround: linking against jemalloc instead of uClibc's built-in allocator prevents the crash, suggesting the issue lies in uClibc's memory allocator implementation.issssss
