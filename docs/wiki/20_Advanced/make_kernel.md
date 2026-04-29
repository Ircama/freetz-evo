# Configure and Compile the Kernel

A toolchain is required; see `Cross-Compiler / Toolchain erstellen`. If
problems with missing directories ever occur, `make world` can help. In
normal cases, this should not be necessary.

1.  Select the correct box type, because only the kernel for the
    corresponding box is compiled.
2.  `make kernel-dirclean` deletes the currently unpacked kernel source
    tree. This means compiling from completely clean kernel sources. If
    you do not want that, try `make kernel-clean` instead.
3.  `make kernel-menuconfig` opens kernel configuration. The configuration
    is saved back to `./make/linux/Config.<kernel-ref>` afterwards.
4.  `make kernel-precompiled` compiles the kernel and kernel modules:
    -   `./kernel/kernel-<kernel-ref>.bin`
    -   `./kernel/modules-<kernel-ref>/`


