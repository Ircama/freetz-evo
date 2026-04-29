# Troubleshooting Build Aborts

If the build process aborts, try these strategies:

 * Rebuild a single package:
```
	$ make iptables-dirclean     <--- Delete the source directory of a problematic package (iptables here)
	then continue with
	$ make iptables-precompiled  <--- Try rebuilding the problematic package from scratch
```

 * Rebuild from the beginning:
```
	$ make dirclean          <--- Delete source directories of all software built so far
	then continue with
	$ make                   <--- Try rebuilding the problematic software from scratch
```

If this does not help, use the wiki, forum, and IRC to investigate the problem further.


