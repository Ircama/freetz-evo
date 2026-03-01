# aria2 Packaging for freetz-ng

This package provides aria2, a lightweight, multi-protocol, multi-connection download utility.

## Features

- **Multi-Protocol Support**: HTTP(S), FTP, SFTP, BitTorrent, Metalink
- **Multi-Connection**: Download from multiple sources simultaneously
- **Remote Control**: JSON-RPC and XML-RPC interfaces
- **Lightweight**: Suitable for embedded systems
- **Configurable**: Extensive configuration options

## Configuration

The aria2 daemon can be configured through:

1. Configuration file: `/etc/aria2/aria2.conf`
2. Command-line options
3. JSON-RPC/XML-RPC interface

An example configuration file is provided in `aria2.conf.example`.

## Building

To build aria2 with standard options:

```bash
./configure
make
make install
```

### Build Options

- `--enable-bittorrent`: Enable BitTorrent support (default: yes)
- `--enable-metalink`: Enable Metalink support (default: yes)
- `--enable-xml-rpc`: Enable XML-RPC interface (default: yes)
- `--enable-websocket`: Enable WebSocket support (default: yes)
- `--with-libssh2`: Enable SFTP/SCP support (default: yes)
- `--with-openssl` or `--with-gnutls`: Choose TLS library

## Freetz-ng Integration

The aria2 package for freetz-ng includes:

- Configuration file management
- Optional crontab entries for auto-start
- External file handling
- Service configuration

## Files

- `Config.in`: Freetz-ng configuration options
- `aria2.mk`: Build instructions
- `external.files`: Files to be installed
- `external.in`: External package configuration
- `external.services`: Service definitions
- `aria2.conf.example`: Example configuration file
- `patches/`: Build patches (if needed)

## Dependencies

- libcares: Async DNS resolver
- libz: Compression library
- libxml2: XML-RPC support (if enabled)
- libssh2: SFTP support (if enabled)
- libnettle: BitTorrent support (if enabled)
- OpenSSL or GnuTLS: TLS support (if enabled)

## License

aria2 is released under the GPLv2 license. See the aria2 project repository for details.

## References

- GitHub: https://github.com/aria2/aria2
- Website: https://aria2.github.io/
- Manual: https://aria2.github.io/manual/en/html/
