# Small Web Server with BusyBox

BusyBox includes a small web server that can be started like this:

```
	httpd -P /var/run/port90.pid -p 90 -c /mod/etc/webcfg.conf -h /var/media/ftp/irgendwo/htdocs/ -r "Port 90"
```

This line starts the web server on port 90. To reach it, use
[http://fritz.box:90](http://fritz.box:90). If a file named `index.html`
has been placed in `/var/media/ftp/irgendwo/htdocs/`, it is displayed.

Directory contents are not displayed automatically. To add that, create a
CGI script named `index.cgi` in the `cgi-bin` subdirectory, in this
example `/var/media/ftp/irgendwo/htdocs/cgi-bin/index.cgi`.

```
	#!/bin/sh

	# generate a standards-compliant HTTP header
	echo -en "Content-Type: text/html\r\n\r\n"
	cat << EOF
	<html>
	  <head>
		<title>Index of ${QUERY_STRING}</title>
	  </head>
	  <body>
		<h2>Index of ${QUERY_STRING}</h2>
		<table cellspacing="2" border="0">
		  <tr align="left"><th>Name</th><th>&nbsp;&nbsp;Last modified</th><th>&nbsp;&nbsp;Size</th></tr>
		  <tr><td colspan="3"><hr></td></tr>
		  <tr><td>$([ "$QUERY_STRING" == "/" ] || echo '<a href="..">..</a>')</td></tr>
		  $(
			# redirect all errors into the void
			exec 2>/dev/null
			# date format 1 for matching the directory listing
			date_format1="[A-Z][a-z]{2} [A-Z][a-z]{2} [ 123][0-9] [0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4}"
			# long replacement expression, kept separate, that generates a table row
			replace="<tr><td><tt><a href="\3">\3<\/a><\/tt><\/td><td><tt>\&nbsp;\&nbsp;\2<\/tt><\/td><td align=right><tt>\&nbsp;\&nbsp;\1<\/tt><\/td><\/tr>"
			# date format 2 for separating a leading space before the day number,
			# which must be replaced by a fixed HTML space, &nbsp;
			date_format2="([A-Z][a-z]{2} [A-Z][a-z]{2} ) ([0-9] [0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4})"
			busybox ls -lLep ../${QUERY_STRING} |
			  # filter out "cgi-bin" in the root directory
			  ([ "$QUERY_STRING" == "/" ] && grep -v 'cgi-bin' || cat) |
			  # number lines so the order within both groups, directories and
			  # everything else, is preserved later while sorting
			  awk '{printf("%5d %s\n", NR,$0)}' |
			  # put "X" before directories, "Y" before everything else ("X" < "Y")
			  sed -r 's/^([0-9 ]+ d)/X \1/' |
			  sed -r 's/^([0-9 ]+)/Y \1/' |
			  # sorting groups the entries
			  sort |
			  # remove sort helpers and unneeded columns
			  sed -r 's/^([^ ]+ +){6}(.*)/\2/' |
			  # replace directory file sizes with "---"
			  sed -r 's/^[0-9]+(.*)\/$/---\1/' |
			  # generate one table row per directory entry
			  sed -r "s/^([-0-9, ]+) ($date_format1) +(.*)$/$replace/" |
			  # special case: leading space before the day number in the date
			  sed -r "s/$date_format2/\1\&nbsp;\2/"
		  )
		</table>
	  </body>
	</html>
	EOF
```

BusyBox httpd can also execute PHP scripts if the PHP package is
installed. Add this new line to `/mod/etc/webcfg.conf`:

```
	*.php:/usr/bin/php-cgi
```

To process `index.php` files, insert these lines into the `index.cgi`
script after the first line:

```
	if test -s "../${QUERY_STRING}/index.php" ; then
	  echo -e "Status: 302 Found\r"
	  echo -e "Location: index.php\r"
	  exit 0
	fi
```

### Further Links

-   [IPPF article](http://www.ip-phone-forum.de/showthread.php?p=1211135)

