# Installation

Freetz provides build scripts to create a modified firmware image from an original AVM firmware.

Important:

- Distributing original or modified firmware images may violate licensing terms.
- Installing modified firmware can void vendor warranty.
- For problems caused by modified firmware, do not contact AVM support.

## Recommended Build Environment

Use a Linux environment:

- Native Linux installation, or
- A virtual Linux environment (recommended if your main OS is Windows/macOS)

A maintained VM-based environment is often the easiest entry point for beginners.

## Before You Start

1. Back up your FRITZ!Box settings and important credentials.
2. Download the correct recovery image for your exact device model.
3. Ensure enough free disk space for sources, toolchains, and build artifacts.
4. Verify network connectivity in your build environment.

## Get the Sources

```sh
git clone https://github.com/Freetz-NG/freetz-ng ~/freetz-ng
cd ~/freetz-ng
```

## Install Build Dependencies

Install the required packages for your Linux distribution, then verify all toolchain prerequisites.

If dependency installation fails, update package indexes and retry.

## Configure

```sh
make menuconfig
```

In menuconfig:

1. Select your exact hardware model.
2. Select the firmware version.
3. Enable only a minimal package set for the first build.

## Build

```sh
make
```

The first build can take a while because toolchains and source archives are prepared.

## Flash

Use a supported flash path:

- Web interface upload, or
- tools/push_firmware (bootloader-based workflow)

Always keep a recovery path ready before flashing.

## First Boot Validation

After flashing:

1. Confirm device reachability.
2. Check internet/telephony baseline.
3. Open the Freetz interface and verify enabled packages.
4. Apply package settings gradually.

## Update Workflow

For later changes:

1. Update sources.
2. Re-run menuconfig if needed.
3. Rebuild and flash.
4. Validate after each iteration.

## Troubleshooting Basics

- Build fails early:
  Check for missing dependencies and host OS limitations.
- Build fails after config changes:
  Revert recent options and rebuild incrementally.
- Device is unstable after flashing:
  Recover to stock firmware and retry from a minimal configuration.

## Safety Checklist

1. Correct device model selected.
2. Correct firmware selected.
3. Recovery image available.
4. Backup completed.
5. Minimal first image strategy applied.
