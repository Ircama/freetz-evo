# Integrating Your Own Files into Firmware

A FRITZ!Box uses two relevant storage areas:

1. Flash storage (persistent, limited)
2. RAM (volatile, limited)

The directory /tmp is writable at runtime, but it lives in RAM. Data stored there is lost after reboot or power loss.

## Choosing an Integration Strategy

| Method | Advantages | Drawbacks |
| --- | --- | --- |
| Include files in Freetz image | Simple deployment, works offline | Requires rebuilding and flashing; flash space is limited |
| Generate via debug.cfg | Works on all boxes, no internet needed | Best for text/scripts; ongoing edits must also be maintained in debug.cfg |
| Download from web server at boot | Supports binary files, easy central updates | Requires network or local server; never store private keys publicly |
| Load from USB storage | Supports binary files, no internet needed | Requires USB storage and stable mount naming |
| Mount WebDAV or NFS share | Centralized files, less local storage use | Requires network and external service availability |

There is no universally best option. Most setups combine two or more methods.

## Method 1: Include Files in the Freetz Image

The preferred modern approach is to use the example addon:

1. Enable addon own-files-0.1 in addon/static.pkg.
2. Place files under addon/own-files-0.1/root with the target path layout.
3. Build and flash.

Example:

- Source path: addon/own-files-0.1/root/usr/bin/foo
- Target path on box: /usr/bin/foo

For volatile paths under /var, place content in addon/own-files-0.1/var.tar.

## Method 2: Create Files from debug.cfg

debug.cfg is executed at boot and can generate files dynamically. This works well for scripts and plain-text configuration files.

Guidelines:

- Keep generated artifacts in /tmp, /var/tmp, or another writable runtime location.
- Ensure generated scripts are made executable.
- Keep debug.cfg maintainable and documented.

## Method 3: Download Files During Boot

Use startup logic to fetch files from a trusted internal or external server.

Best practices:

- Validate source integrity where possible.
- Use HTTPS if credentials or sensitive data are involved.
- Never host private keys or secrets on publicly accessible endpoints.

## Method 4: Use USB Storage

Store larger or frequently changing files on USB storage and copy or execute them at startup.

Best practices:

- Use stable mount paths in startup scripts.
- Handle delayed mounts gracefully (retry logic).
- Log failures for easier troubleshooting.

## Method 5: Mount Remote Shares (WebDAV/NFS)

Mounting a share gives direct access to centrally managed files.

- WebDAV is widely available and simple to provision.
- NFS is often faster and more stable in LAN-only environments.

This approach is convenient when multiple devices should use the same file set.

## Practical Recommendations

1. Start simple: include only critical files in the image.
2. Keep mutable data outside the image (USB/share/download).
3. Separate secrets from public or synced content.
4. Add logging to startup scripts so failures are visible.
5. Reboot-test every change before relying on it in production.
