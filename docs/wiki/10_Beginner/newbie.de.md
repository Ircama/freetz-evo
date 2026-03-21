# Freetz for Beginners

This page is a practical quick-start for first-time Freetz users.

## What Is Freetz?

Freetz is a build environment that lets you create a customized firmware image based on vendor firmware. You can add, remove, and adjust features for your own device.

## What You Need

1. A Linux build environment (native or virtual machine).
2. The correct recovery image for your exact FRITZ!Box model.
3. A backup of current router settings.
4. Enough disk space and stable internet access for source downloads.

## First-Time Mindset

- Start with a minimal image.
- Enable only features you can explain and verify.
- Avoid complex options early (custom kernel/module experiments, deep patch sets).

Minimal first builds make troubleshooting much easier.

## Typical First Build

1. Clone the Freetz sources.
2. Run make menuconfig.
3. Select the correct box model and firmware.
4. Keep package selection minimal.
5. Build with make.
6. Flash the image and test core functions.

## Validate After Flashing

Check these basics first:

1. Device boots normally.
2. Web interface reachable.
3. Internet access works.
4. Telephony works.
5. Freetz page is available.

Only after this baseline is stable should you add more packages.

## Common Beginner Mistakes

- Enabling too many packages at once.
- Skipping backups and recovery preparation.
- Using unsupported firmware/device combinations.
- Debugging multiple simultaneous changes.

## If Something Goes Wrong

1. Stay calm and recover to stock firmware if required.
2. Return to a minimal known-good Freetz config.
3. Reintroduce changes one by one.
4. Ask the community with exact build/config details.

## Community and Support

Community support is available via Freetz and IP-Phone forum channels.
Provide clear context when asking for help:

- Device model
- Firmware version
- Selected packages/patches
- Build errors or runtime symptoms
