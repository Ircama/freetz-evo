# Freetz Makes Your Box More Flexible

[![Screenshot](../../screenshots/52_md.png)](../../screenshots/52.png)

The stock firmware does not always include every feature users need. Freetz extends the original firmware so you can tailor your device to your own use case.

With Freetz you can:

- Add functionality, for example extra services, VPN tools, or diagnostics.
- Customize existing behavior that is too limited in stock firmware.
- Remove unneeded components to free space for features you actually use.

## How Freetz Works

A FRITZ!Box firmware image is made of many components. Freetz modifies selected parts, adjusts configuration, and can add new components while keeping the original AVM web interface available.

The result is a custom firmware image you can install using the normal firmware update workflow.

## Why You Build It Yourself

Because of licensing and redistribution restrictions, ready-made modified images are generally not distributed. Freetz provides the build system and tooling so every user can create a personal image locally.

## Requirements

- A Linux system (native or virtualized).
- Basic build dependencies required by Freetz.
- Current Freetz sources.

## Typical Workflow

[![Freetz menuconfig](../../screenshots/53_md.png)](../../screenshots/53.png)

1. Configure your image in menuconfig.
2. Build the image.
3. Flash it with the standard update process.
4. Open the Freetz pages in the web interface and configure enabled packages.

In most cases, existing FRITZ!Box settings remain intact after switching to a Freetz image.

## Legal and Support Notes

Freetz includes and integrates free software, but a working firmware also contains proprietary vendor components. This is why distributing prebuilt modified images can create legal issues.

If you run modified firmware, do not expect vendor support from AVM for issues caused by modifications. Community support is available in the IP-Phone forum:

- <http://www.ip-phone-forum.de/forumdisplay.php?f=525>
