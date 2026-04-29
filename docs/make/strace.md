# strace 4.9/5.0/6.19 (binary only)
  - Homepage: [https://www.strace.io/](https://www.strace.io/)
  - Manpage: [https://man7.org/linux/man-pages/man1/strace.1.html](https://man7.org/linux/man-pages/man1/strace.1.html)
  - Changelog: [https://github.com/strace/strace/releases](https://github.com/strace/strace/releases)
  - Repository: [https://github.com/strace/strace](https://github.com/strace/strace)
  - Package: [master/make/pkgs/strace/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/strace/)
  - Steward: [@fda77](https://github.com/fda77)

**[strace](http://sourceforge.net/projects/strace/)**
traces the system calls and signals of a process. It places itself
between a user process and the kernel and logs all activity at this
interface. When the traced process makes a system call, *strace* prints
the name, arguments, and return value of that system call. When the
traced process receives a signal, *strace* prints the signal name. If a
system call returns with an error, the error message associated with the
error status is displayed, if available.

In short, *strace* is usually used when "something does not work and
nobody knows why". In other words: a program crashes, a process hangs,
and you want to find out during which action this happens.

Its sibling [ltrace](ltrace.md) can also be helpful here: instead of
system calls, *ltrace* logs library calls.

### Tip: Avoiding "unfinished" and "resumed" in strace Logs

When strace is called with "-f" to follow subprocesses or threads,
interrupted system calls often appear in the log because strace records
the start and return time of calls separately when an interruption occurs.
Readability suffers, because further down it is often no longer clear
which "resumed" belongs to which "unfinished" call (in this example it is
still easy):

```
719   14:55:13.562840 clock_gettime(CLOCK_MONOTONIC,  <unfinished ...>
1010  14:55:13.563457 getppid( <unfinished ...>
719   14:55:13.563818 <... clock_gettime resumed> {337216, 716098754}) = 0
1010  14:55:13.564329 <... getppid resumed> ) = 719
719   14:55:13.564701 clock_gettime(CLOCK_MONOTONIC,  <unfinished ...>
1010  14:55:13.565066 poll([{fd=21, events=POLLIN}], 1, 2000 <unfinished ...>
719   14:55:13.565543 <... clock_gettime resumed> {337216, 717736704}) = 0
```

Using "-ff" writes a separate log file per PID, but then the timeline can
no longer be followed clearly. If both are desired together, the following
script helps. The *sed* command is so complicated because, when the script
is called with multiple "-p" options, the PIDs that appear as the first
column in this mode must first be removed from the individual files;
otherwise sorting by timestamp would not be possible:

```
#!/bin/sh

# Logfile as first parameter is required
logfile="$1"
shift

# Ctrl-C should only kill strace, not the rest of the script
trap '' INT

# Create one logfile per pid, then consolidate them into one,
# sorted by timestamp and containing the pid as 2nd column
strace -tt -ff -o "$logfile" "$@"
{
for file in "$logfile".*; do
pid=$(printf "%-5u" "${file##$logfile.}")
cat "$file" | sed -r "s/^([0-9]+ +)?([^ ]+)(.*)/2 $pid3/"
done
} | sort > "$logfile"

# Clean up temporary logfiles
rm "$logfile".*
```

### Further Links

-   [strace
    project page](http://sourceforge.net/projects/strace/)
    (Sourceforge)
-   [Article: tracing system calls with
    ''strace''](http://www.pronix.de/pronix-585.html)
-   [strace Man
    page](http://linux.die.net/man/1/strace)


