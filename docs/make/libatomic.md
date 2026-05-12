# libatomic

  - Package: [master/make/libs/libatomic/](https://github.com/Ircama/freetz-evo/tree/master/make/libs/libatomic/)
  - Provides: `libatomic.so`
  - Used by: `cmus`
  - Externalization: supported

`libatomic` is GCC's runtime support library for atomic operations. On 32-bit MIPS it is required by `cmus` to satisfy 64-bit atomic references during final link and runtime.