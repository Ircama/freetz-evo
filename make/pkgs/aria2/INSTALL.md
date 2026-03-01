# aria2 Package Installation Guide for freetz-ng

## Overview

This guide explains how to integrate the aria2 package into your freetz-ng build system.

## Installation Steps

### 1. Verify Package Structure

First, verify that all the required files are present in `make/pkgs/aria2/`:

```bash
ls -la make/pkgs/aria2/
```

You should see:
- Config.in (configuration options)
- aria2.mk (build instructions)
- Makefile.in (integration settings)
- external.files (file list)
- external.in (external configuration)
- external.services (service definitions)
- aria2.conf.example (example configuration)
- aria2.init (init script)
- README.md (documentation)
- patches/ (build patches)

### 2. Register Package in Build System

#### Option A: Using menuconfig (Recommended)

The package should be automatically discovered by freetz-ng's build system. You can then select it via:

```bash
make menuconfig
```

Navigate to:
- Package Selection → Standard Packages → aria2

Or search for "aria2" in the menuconfig interface.

#### Option B: Manual Configuration

Edit `config/mod/Config.in` and add:

```
source make/pkgs/aria2/Config.in
```

Or use freetz-ng's configuration generator to automatically include it.

### 3. Configure Build Options

Select the desired aria2 build options in menuconfig:

- **Use OpenSSL/GnuTLS**: Choose your TLS library (default: OpenSSL)
- **Enable BitTorrent support**: Download torrent files (default: enabled)
- **Enable Metalink support**: Multi-source downloads (default: enabled)
- **Enable XML-RPC support**: Remote control via XML-RPC (default: enabled)
- **Enable WebSocket support**: JSON-RPC via WebSocket (default: enabled)
- **Enable SFTP/SCP support**: Via libssh2 (default: enabled)
- **Link statically**: Static linking (default: disabled)

### 4. Build the Package

Build aria2 directly:

```bash
make aria2
```

Or build the entire firmware with aria2 included:

```bash
make all
```

### 5. Verify Installation

After building, check that the aria2c binary was installed:

```bash
ls -la root/usr/bin/aria2c
```

## Configuration

### Configuration Files

Configuration files should be placed in `/etc/aria2/`:

```bash
/etc/aria2/aria2.conf          # Main configuration file
/etc/aria2/aria2.session       # Session file (auto-generated)
```

### Example Configuration

An example configuration file is provided in `aria2.conf.example`. Copy and modify it:

```bash
cp /etc/aria2/aria2.conf.example /etc/aria2/aria2.conf
vi /etc/aria2/aria2.conf
```

### Remote Control

aria2 supports remote control via:

- **JSON-RPC**: Default port 6800
- **XML-RPC**: Requires XMLRPC option enabled

Example daemon command:
```bash
/usr/bin/aria2c --daemon \
    --enable-rpc --rpc-listen-all \
    --rpc-listen-port=6800 \
    --dir=/tmp/downloads
```

## Service Management

### Using init script

An init script (`aria2.init`) is provided. To enable auto-start:

```bash
cp make/pkgs/aria2/aria2.init /etc/init.d/aria2
chmod +x /etc/init.d/aria2
/etc/init.d/aria2 start
```

### Manual Start/Stop

```bash
# Start
/usr/bin/aria2c --daemon --enable-rpc --rpc-listen-all

# Stop
pkill aria2c

# Status
ps aux | grep aria2c
```

## Troubleshooting

### Build Errors

If the build fails:

1. **Check dependencies**: Ensure all required libraries are enabled in menuconfig
2. **Review build log**: Check the build output for specific errors
3. **Clean and rebuild**:
   ```bash
   make aria2-clean
   make aria2-distclean
   make aria2
   ```

### Runtime Issues

- **Connection refused**: Check if aria2 is running and listening
- **Permission denied**: Ensure /tmp/downloads and /etc/aria2 are writable
- **Memory issues**: Consider disabling WebSocket or other optional features
- **DNS resolution**: Verify libcares is properly linked

### Testing

Run the test script to verify package structure:

```bash
bash test-aria2-package.sh
```

## Dependencies

The aria2 package requires these libraries (automatically selected based on build options):

- **libcares**: Async DNS (required)
- **libz**: Compression (required)
- **libxml2**: XML-RPC support (if enabled)
- **libssh2**: SFTP support (if enabled)
- **libnettle**: BitTorrent support (if enabled)
- **openssl** or **gnutls**: TLS support (if enabled)

## Build Customization

### Custom Patches

Add custom patches to `make/pkgs/aria2/patches/` following the format:
```
NNN-description.patch
```

Patches are automatically applied during build.

### Cross-Compilation

aria2 uses autoconf for cross-compilation. The build system automatically handles:
- Target architecture detection
- Cross-compiler selection
- Library path configuration
- Staging directory setup

## Performance Notes

For embedded systems:

1. **Static linking** (`FREETZ_PACKAGE_ARIA2_STATIC=y`): Reduces memory overhead
2. **Disable optional features**: Disable WebSocket, XML-RPC if not needed
3. **File allocation**: Use `file-allocation=none` in aria2.conf for low memory
4. **Connection limits**: Adjust `max-concurrent-downloads` based on available resources

## References

- aria2 Official: https://aria2.github.io/
- aria2 GitHub: https://github.com/aria2/aria2
- aria2 Manual: https://aria2.github.io/manual/en/html/
- freetz-ng: https://github.com/Freetz-NG/freetz-ng

## Support

For issues with the aria2 package in freetz-ng:

1. Check the aria2 manual for configuration options
2. Review freetz-ng build documentation
3. File issues on the respective GitHub repositories

## License

- aria2: GPLv2
- freetz-ng: GPLv2
- This package: Same as aria2 and freetz-ng
