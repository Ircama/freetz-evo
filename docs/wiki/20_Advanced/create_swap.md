# Create and Enable Swap

## What is swap and why use it?

Swap extends available memory by moving inactive pages from RAM to a file or partition on storage.
On FRITZ!Box devices with limited RAM, swap can improve stability when running memory-heavy packages.

Important: swap on flash/USB storage is slower than RAM and increases write activity.
Use moderate sizes and avoid over-relying on swap for performance.

## Prerequisite: enable Swap options in build config

If **Settings -> Swap** is missing in the WebIF, enable it in build configuration:

1. Run `make menuconfig`
2. Open **Additional patches**
3. Enable **Add swap options** (`FREETZ_ADD_SWAPOPTIONS`)
4. Rebuild and flash firmware

After flashing, open:

`http://fritz.box:81/cgi-bin/conf/mod`

## Method A: create swap from WebIF

In **Settings -> Swap**:

1. Set **Path** to a writable storage location, for example:
   - `/var/media/ftp/uStor01/swapfile`
   - or a partition path such as `/dev/sda1`
2. Set **Size** in MB (when creating a swap file)
3. Click **Create swap file**
4. Set start mode to **Automatic**
5. Save settings

To activate immediately without reboot:

1. Open **Services**
2. Start service **Swap**

## Method B: create swap file manually (Linux shell)

Use this if you prefer shell-based setup or are on older branches.

Example (64 MB):

```bash
dd if=/dev/zero of=swapfile bs=1k count=64000
mkswap swapfile
scp swapfile root@fritz.box:/var/media/ftp/uStor01/
```

Then configure the same path in **Settings -> Swap**, enable **Automatic**, save, and start the Swap service.

## Verification

From shell, check active swap:

```bash
cat /proc/swaps
```

Expected result: your configured swap file or partition appears in the list.

## Recommended values

- Typical size for routers: 64 to 256 MB
- `swappiness`: start with 60, then tune if needed
- Prefer USB/external storage over internal flash when possible

## Troubleshooting

- **Swap section not visible in WebIF**: enable `FREETZ_ADD_SWAPOPTIONS` and rebuild.
- **Service fails to start**: verify file path exists and permissions allow access.
- **No entry in `/proc/swaps`**: check service status and run start manually from Services page.


