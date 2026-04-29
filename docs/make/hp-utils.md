# hp-utils 0.3.2 - DEPRECATED
  - Package: [master/make/pkgs/hp-utils/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/hp-utils/)
  - Steward: -

[hp-utils](http://www.michaeldenk.de/projects/hp-utils/)
is a port of several [HPLIP](http://hplipopensource.com/) tools from
Python to C. hp-utils uses the libhpmud library and requires the
[HPLIP](hplip.md) package.

hp-utils provides command-line tools and also offers a web interface
(by default at [http://fritz.box:83/](http://fritz.box:83/)). It
currently shows printer status and ink level and can start print-head
cleaning.

The following tools are included:

  ------------------ ---------------------------------------------------------------------------
  **hp-probe**       Probe connected HP devices.
  **hp-status**      Display current status for supported HPLIP printers.
  **hp-levels**      Display bar graphs of current supply levels for supported HPLIP printers.
  **hp-clean**       Cartridge cleaning utility for HPLIP supported inkjet printers.
  **hp-printserv**   Simple print server.
  **hp-timedate**    Set the time and date on an HP Officejet.
  **hp-faxsetup**    Setup fax settings on an HP Officejet.
  ------------------ ---------------------------------------------------------------------------
