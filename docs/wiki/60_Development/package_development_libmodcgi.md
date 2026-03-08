# libmodcgi.sh

This library is used to generate web pages within the Freetz web interface. Include it with:

```
source /usr/lib/libmodcgi.sh
```

### cgi

**This interface is under development and may change on a daily basis.**

The `cgi` function allows various settings to be configured for the current page. `cgi` must be called before `cgi_begin`.

The available options are:

`--style=URI`

> The CSS stylesheet at address `URI` will be additionally included.
> This option can be used multiple times.

> Relative URLs are resolved relative to `/style/` within the Freetz web interface.
> If a stylesheet is stored in the filesystem at `/usr/share/style/pkg/status.css`,
> it can be included via `--style=pkg/status.css`.

`--id=ID`

> The body tag of the page receives this ID; the ID is also used to
> highlight the active menu item in the navigation.

`--help=PATH`

> A path (starting with "/") that specifies the help page for the current page.
> (In the main Freetz interface, this path is currently appended to
> [http://trac_freetz_org/wiki](http://trac_freetz_org/wiki).)

### cgi_begin

Starts an HTML page in Freetz style. (Everything that belongs at the beginning of a page is written,
from the HTTP header through the HTML header to navigation elements and similar.)

All pages in the Freetz web interface are currently encoded in ISO-8859-1 (Latin 1).

Usage:

```
cgi_begin TITLE
```

- TITLE is the already HTML-encoded title of the page.

### cgi_end

Closes an HTML page in Freetz style.

### sec_begin

Starts a section with the title TITLE. How a "section" is rendered in detail in the HTML output
depends on the chosen skin; however, a surrounding `<div class="section">` is guaranteed.

```
sec_begin TITLE [ID]
```

An ID can optionally be specified in order to reference the section. At the HTML level,
this will be the ID of the mentioned div element.

### sec_end

Ends a section.

### html

This function HTML-encodes its input. Short inputs can be passed as arguments; for longer inputs,
`html` should be used as a filter:

```
    echo "<input value='$(html "$VALUE")'> ..."
    log_output | html
```

### check, select

TODO

### href

Generates a link to a dynamically registered page in the Freetz web interface.
The arguments are similar to those of `modreg`:

```
href file <pkg> <id>
href extra <pkg> <cgi-name>
href status <pkg> [<cgi-name>]
href cgi <pkg> [<key-value>]...
```

Typical usage in a package called foo:

```
    cat << EOF
      <a href="$(href file foo advanced)">Edit configuration file</a>
    EOF
```

(if the file was previously registered with `modreg file foo advanced ...`.)

### back_button

TODO

### sec_level

TODO

### stat_bar

TODO

### cgi_param

TODO

### cgi_error, print_error

```
cgi_error MESSAGE
print_error MESSAGE
```

`cgi_error` generates a complete error page (including cgi_begin/cgi_end) with the given message.
`print_error` generates only the error message and can be used within an existing page.

### path_info

Splits PATH_INFO into segments at "/"; returns the segments in the given variables.
If there are not more variables than segments, the final variable will receive the remaining unsplit PATH_INFO.

```
PATH_INFO=/foo/bar/baz
path_info package id rest
```

will set

```
package=foo
id=bar
rest=/baz
```

### valid

Validates certain types of input data. Currently supported:

`valid package PACKAGE`

> Returns true if PACKAGE is a valid package name.

`valid id NAME`

> Returns true if NAME is a valid identifier (identifying files, extras,
> or status pages within a package).

The validation is currently fairly lenient (mainly just protection against path operations
such as "." and "/" in the name). The output of `valid` should not currently be used as
a benchmark for constructing valid names.
