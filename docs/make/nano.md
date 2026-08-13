# Nano 9.2 (binary only)
  - Homepage: [https://www.nano-editor.org/](https://www.nano-editor.org/)
  - Manpage: [https://www.nano-editor.org/docs.php](https://www.nano-editor.org/docs.php)
  - Changelog: [https://www.nano-editor.org/dist/v9/NEWS](https://www.nano-editor.org/dist/v9/NEWS)
  - Repository: [https://git.savannah.gnu.org/cgit/nano.git/](https://git.savannah.gnu.org/cgit/nano.git/)
  - Package: [master/make/pkgs/nano/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/nano/)
  - Steward: [@fda77](https://github.com/fda77)

**Nano** is a small text editor for the console, but unlike (n)vi it is
operated like a normal editor, for example Windows Notepad. It is
therefore not necessary to learn many commands before it can be used.
This often makes it much better suited than vi for beginners and users
who are not fluent touch typists.

To make the Pos1 and Home keys usable in Nano, setting the TERM
environment variable is helpful, at least for me with the combination of
putty and Windows:

```
export TERM=xterm
```

in rc.custom does the trick.

