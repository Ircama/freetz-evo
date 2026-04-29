# Compile Your Own Programs

After the toolchain has been downloaded or built, it can be used to
compile your own programs, or programs that are not yet available as
packages.

Add the MIPS compiler to the path:

```
	export PATH=/pfad/zu/freetz/toolchain/target/bin:$PATH
```

Options for `./configure`:

```
	./configure --build=i386-linux-gnu --target=mipsel-linux --host=mipsel-linux
```

(`i386-linux-gnu` is not strictly required, but `configure` complains if
it is not specified. On 64-bit platforms or non-Intel architectures, the
value must of course be different.)

Static linking of binaries, so they include the required libraries
instead of using separate ones. This does not work with every program:

```
	LDFLAGS=-static ./configure ...
```

Statically linked binaries are easier to install because they contain
everything they need. However, they are larger, and if they duplicate
functionality shared with other programs, they waste storage space. They
also need to be updated separately when, for example, a security issue in
a library is patched. It is best to use static binaries only for testing
or when there is no practical alternative.

In some cases it is advisable to set the `CC` variable explicitly. It can
also help to specify `CFLAGS`:

```
	./configure ... CC="mipsel-linux-gcc" CFLAGS="-Os -pipe -march=4kc -Wa,--trap"
```


