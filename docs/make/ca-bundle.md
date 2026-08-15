# CA-bundle 2026-08-13
  - Homepage: [https://www.curl.se/ca](https://www.curl.se/ca)
  - Package: [master/make/pkgs/ca-bundle/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ca-bundle/)
  - Steward: [@fda77](https://github.com/fda77)

The CA bundle is a package of root CA (Certificate Authority) certificates.
<br>
 * It can be used to verify the trustworthiness of HTTPS certificates.
 * When run as user ```root```, the programs ```wget``` and ```curl``` use these certificates automatically.
 * Other users or programs must be told about the file ```/mod/etc/ssl/certs/ca-bundle.crt```.

