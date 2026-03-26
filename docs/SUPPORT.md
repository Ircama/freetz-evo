# Support
How can I support Freetz-NG?

 * __[Sponsor](#sponsor)__<a id='sponsor'></a><br>
    - [![](https://img.shields.io/static/v1?label=GitHub&message=fda77&logo=GitHub&color=%230e8e86)](https://github.com/sponsors/fda77)
 * __[UNTESTED](#untested)__<a id='untested'></a><br>
   In `menuconfig` and in [FIRMWARES](FIRMWARES.md), several devices are marked as `UNTESTED`.<br>
   Because of missing hardware, it was not possible to verify whether Freetz-NG works on them.<br>
   If you run Freetz-NG successfully on one of these devices, please report back.<br>
   Ideally include screenshots of `Box-Info` and `Flashspeicher`.<br>
 * __[Source code](#source-code)__<a id='source-code'></a><br>
   Building a modified image requires the matching AVM source code.<br>
   Since AVM uses software licensed under terms like GPL, they must provide source code,<br>
   but usually only on request.<br>
   Everyone should send an email for each owned device to [fritzbox_info@avm.de](mailto:fritzbox_info@avm.de).<br>
   Do this for every published FRITZ!OS version, including so-called "Labor" builds.<br>
   AVM then publishes the package on [osp.avm.de/](https://osp.avm.de/).<br>
 * __[Pull request](#pull-request)__<a id='pull-request'></a><br>
   Contributing your own changes to Freetz-NG:
    - Create your own fork on [github.com/Freetz-NG/freetz-ng/](https://github.com/Freetz-NG/freetz-ng/) using `Fork`.
    - Clone your fork: `git clone https://github.com/USERNAME/freetz-ng.git`
    - Create a branch: `git branch BRANCHNAME` ; `git checkout BRANCHNAME` ; `git push -u origin BRANCHNAME`
    - Commit and push your changes: `git add . ; git commit -m "DESCRIPTION" ; git push`
    - Open a PR from your fork using `New pull request` on [github.com/Freetz-NG/freetz-ng/](https://github.com/Freetz-NG/freetz-ng/).
 * __[Mailbox format](#mailbox-format)__<a id='mailbox-format'></a><br>
   If creating a pull request is too much effort, you can also send a patch:
    - Clone: `git clone https://github.com/Freetz-NG/freetz-ng.git`
    - Ensure your name is set: `git config --global user.name "GITHUB-NAME"`
    - Ensure your email is set: `git config --global user.email GITHUB-NAME@users.noreply.github.com`
    - Make your changes, add/remove files as needed.
    - Stage all changes: `git add .`
    - Create a commit: `git commit -m "DESCRIPTION"`
    - Create patch file(s): `git format-patch origin/HEAD`
    - Remove all local changes again: `git reset --hard origin/HEAD`
 * __[Package bump](#package-bump)__<a id='package-bump'></a><br>
   Minimal steps to update a package/library version:
    - Read the changelog, there may be relevant behavior changes.
    - Note: libraries are in `make/libs/$PKG/`, not in `make/pkgs/$PKG/`.
    - Update `docs/CHANGELOG.md`.
    - Update version in `make/pkgs/$PKG/Config.in`.
    - Update version in `make/pkgs/$PKG/$PKG.mk`.
    - Update checksum in `make/pkgs/$PKG/$PKG.mk`.
    - If filename includes version, update `make/pkgs/$PKG/external.*`.
    - Refresh existing patches in `make/pkgs/$PKG/patches/` with `make $PKG-autofix`.
    - Test build with `make $PKG-recompile`.
    - Best practice: flash and test on a real FRITZ!Box.
 * __[Wiki](#wiki)__<a id='wiki'></a><br>
    Many parts of the wiki at [freetz-ng.github.io/](https://freetz-ng.github.io/) are outdated and need updates.<br>
    All wiki files are available in the checkout under `docs/wiki/`.<br>

