# JamVM 2.0.0 (binary only) - DEPRECATED
  - Homepage: [https://jamvm.sourceforge.net/](https://jamvm.sourceforge.net/)
  - Manpage: [https://sourceforge.net/projects/jamvm/files/jamvm/JamVM%202.0.0/](https://sourceforge.net/projects/jamvm/files/jamvm/JamVM%202.0.0/)
  - Changelog: [https://sourceforge.net/projects/jamvm/files/jamvm/](https://sourceforge.net/projects/jamvm/files/jamvm/)
  - Repository: [https://sourceforge.net/p/jamvm/code/ci/master/tree/](https://sourceforge.net/p/jamvm/code/ci/master/tree/)
  - Package: [master/make/pkgs/jamvm/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/jamvm/)
  - Steward: -

**[JamVM](http://jamvm.sourceforge.net/)** is a
new [Java Virtual
Machine](http://en.wikipedia.org/wiki/Java_Virtual_Machine)
that conforms to version 2 of the JVM specification (blue book). Compared
with [most other
VMs](http://bugblogger.com/java-vms-compared-160/), both free and
commercial, *JamVM* is extremely small (stripped executables are only
about 160K for PowerPC and 140K for Intel). Unlike other "small" VMs such
as KVM, however, it still supports the full specification and includes
support for object finalization, soft/weak/phantom references, class
unloading, the [Java Native
Interface](http://de.wikipedia.org/wiki/Java_Native_Interface)
(JNI), and the Reflection API.

JamVM uses the [GNU
Classpath](http://de.wikipedia.org/wiki/GNU_Classpath) Java class
library. A number of classes are reference classes that must be adapted
for a specific VM. These are bundled together with *JamVM*.

 * **Note:**
*JamVM* will not work with the class library from Sun's or IBM's JVMs.

Because the normal class library (glibj.zip) is over 9 MB in size, only a
reduced version (mini.jar) is installed by default. Therefore, jamvm must
be called as follows to run, for example, the file Hello.class in the
current directory:

```
jamvm -Xbootclasspath/a:/usr/share/classpath/mini.jar Hello
```

### Further Links

-   [JavaVM
    Homepage](http://jamvm.sourceforge.net/)
-   [Comparison of different
    JVMs](http://bugblogger.com/java-vms-compared-160/)
-   [List of
    JVMs](http://en.wikipedia.org/wiki/List_of_Java_virtual_machines)
-   [free Java
    implementations](http://en.wikipedia.org/wiki/Free_Java_implementations)

