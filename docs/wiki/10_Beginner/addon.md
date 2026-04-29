# Installing Addon Packages

Packages that are not yet integrated into Freetz can be installed as
so-called *addon packages*. Download the desired package **before**
creating the image and unpack it into `./addon`. The following example
assumes that you are in the unpacked Freetz directory:

```
tar -C addon -xjvf /pfad/zu/addon-paket-0.1-freetz.tar.bz2
```

After that, add the package to `./addon/static.pkg` on a new line. In
the example above, that entry would be `addon-paket-0.1`. Addon packages
are started after the integrated packages, in the order in which they
appear in `./addon/static.pkg`.

Note: if the addon package is another version of a package that is
already integrated, disable the original package in `make menuconfig`
under *Package selection* to avoid version conflicts.


### Extension since r15856 / 3dda64565e

Files matching `addon/*.pkg` can be used for activation. This has the
advantage that the `.pkg` file can be included in the addon archive, so
other addons are not disabled.<br>
It also makes updates easier to distribute when the version number is not
part of the `.pkg` filename.

Example with two addons:
- Directory `addon/ding-v1/`, file `addon/ding.pkg` containing `ding-v1`
- Directory `addon/dong-v1/`, file `addon/dong.pkg` containing `dong-v1`

Updating one addon:
- Directory `addon/ding-v2/`, file `addon/ding.pkg` containing `ding-v2`

This automatically disables the old addon version and activates the new one.

