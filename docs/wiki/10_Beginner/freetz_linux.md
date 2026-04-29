# Freetz Linux

### Freetz Linux under VirtualBox

1. Start VirtualBox, choose File -> Import Appliance, and follow the
dialog. Select the Freetz Linux file you just downloaded as the image.
2. The import takes a moment. Afterwards, use **Change** to check the
settings.

### Freetz Linux under VMware

Depending on which VMware product should run Freetz Linux later, I tried
two approaches. These tools are helpful, though not all of them are
needed for both approaches:

-   [Freetz-Linux](http://www.ip-phone-forum.de/showpost.php?p=1400234&postcount=1)
    itself
-   [Virtualbox](https://www.virtualbox.org/wiki/Downloads)
-   [VMWare OVF
    Tool](http://www.vmware.com/support/developer/ovf/)
-   [Notepad++](http://notepad-plus-plus.org/) as a good editor
-   [VMware vCenter Converter
    standalone](http://downloads.vmware.com/de/d/info/infrastructure_operations_management/vmware_vcenter_converter_standalone/5_0)

### Freetz Linux under VMware ESXi V4.1 Hypervisor (also works with vSphere Hypervisor 5.5)

1. Start VirtualBox, choose File -> Import Appliance, and follow the dialog.
2. The import takes a moment. Afterwards, choose File -> Export Appliance
    and follow the dialog.\
    Select storage location and filename, changing the file extension from
    `*.ova` to `*.ovf`.
The OVF version should be set to 1.0.
3. Load the generated `*.ovf` file into a text editor.
4. <vssd:VirtualSystemType>virtualbox-2.2</vssd:VirtualSystemType>
change to <vssd:VirtualSystemType>vmx-07</vssd:VirtualSystemType>
and save the `*.ovf` file.\
`vmx-07` denotes VM version 7, for example ESXi V4.1. Older VM versions
should work with `vmx-04`.
5. Start the vSphere Client and connect to the ESXi hypervisor.
6. Choose File -> Deploy OVF Template. Follow the dialog, make the desired
settings, and wait for the import to finish.
7a. Start the virtual machine.
7b. If you get a segmentation fault during system startup, shut down the
VM, enable paravirtualization in the VM settings, and start the VM again.

### Freetz Linux under VMware Player V2.5

1. Start VirtualBox, choose File -> Import Appliance, and follow the dialog.
2. The import takes a moment. Afterwards, choose File -> Export Appliance
and follow the dialog.\
Select storage location and filename, changing the file extension from
`*.ova` to `*.ovf`.
3. Load the generated `*.ovf` file into a text editor.
4. <vssd:VirtualSystemType>virtualbox-2.2</vssd:VirtualSystemType>
change to <vssd:VirtualSystemType>vmx-07</vssd:VirtualSystemType>
and save the `*.ovf` file.\
`vmx-07` denotes VM version 7, for example ESXi V4.1. Older VM versions
should work with `vmx-04`.
5. Open a command prompt: Windows -> Start -> Run -> `cmd` -> Enter.
6. Change into the OVFTool directory and convert the VM like this:\
`ovftool [*.ovf file] [*.vmx file]`
7. Start VMware Player and load the VM.

The `*.vmx` file created in scenario 2 can also be used on the ESXi
hypervisor and manually added to the inventory through the datastore
browser. Keep the segmentation fault note above in mind. Creating the
`*.vmx` and `*.vmdk` files may be useful anyway so you can store the
converted Freetz Linux.

For information: I only had to use the VMware vCenter Converter
standalone listed above once on an ESXi hypervisor because neither of the
two described methods worked.

Here are some screenshots matching the notes above:

[![convert command line](../../screenshots/222_md.jpg)](../../screenshots/222.jpg)



[![Screenshot](../../screenshots/223_md.jpg)](../../screenshots/223.jpg)



[![Screenshot](../../screenshots/224_md.jpg)](../../screenshots/224.jpg)



[![Screenshot](../../screenshots/225_md.jpg)](../../screenshots/225.jpg)




### Freetz Linux under Virtual PC

I tested this under Windows XP x86 with Virtual PC 2007 and under Windows
7 x86_64 with Windows Virtual PC. These tools are helpful:

-   [Freetz-Linux](http://www.ip-phone-forum.de/showpost.php?p=1400234&postcount=1) itself
-   [Virtualbox](https://www.virtualbox.org/wiki/Downloads)
-   [Virtual PC 2007](http://www.microsoft.com/downloads/de-de/details.aspx?FamilyID=04d26402-3199-48a3-afa2-2dc0b40a73b6) for Windows XP
-   [Windows Virtual PC](http://www.microsoft.com/windows/virtual-pc/) for Windows 7; XP mode is not required

1a. Start VirtualBox, choose File -> Import Appliance, and follow the
dialog. The import takes a moment.
1b. Exit VirtualBox.\
2. Run these commands to convert the two hard disks:\
`VBoxManage.exe clonehd freetz-linux-1.2.1-disk1.vmdk freetz.vhd --format VHD`\
`VBoxManage.exe clonehd freetz-linux-1.2.1-disk2.vmdk freetz2.vhd --format VHD`\
3a. Start Virtual PC and create a new virtual computer; see the screenshot
for details.
3b. Start the new virtual PC.
4. Most likely, the graphics resolution and similar settings are not
detected correctly; see the screenshot. If so, continue with step 5.
5. Restart the virtual machine with the key combination [Alt Gr]+[Del].\
6. While the Grub boot manager is active, press [Esc] to reach the menu.
7a. Press [e] on the first menu entry. Press [e] again on the kernel boot
parameters. Add these boot options: `vga=791 noreplace-paravirt`.\
7b. Press [Return].\
7c. Press [b] to start Ubuntu.\
8. The usual Ubuntu screen should appear and Freetz Linux should start up
to the console login.\
9. Make the manual entries persistent in the Grub configuration. Run:\
`sudo nano /boot/grub/menu.lst`\
Near the bottom of the file, add the options used during the first boot.\
Save with [Ctrl]+[O] and exit with [Ctrl]+[X].\
10. Restart the virtual machine to check whether the values were saved.

Here are some screenshots matching the notes above:

[![vpc2007_convert.jpg](../../screenshots/230_md.jpg)](../../screenshots/230.jpg)



[![vpc2007_params.jpg](../../screenshots/233_md.jpg)](../../screenshots/233.jpg)



[![vpc2007_wrong_graphic.jpg](../../screenshots/234_md.jpg)](../../screenshots/234.jpg)



[![vpc2007_kernel_boot_params.jpg](../../screenshots/232_md.jpg)](../../screenshots/232.jpg)



[![vpc2007_freetz_linux.jpg](../../screenshots/231_md.jpg)](../../screenshots/231.jpg)



[![vpc2007_grub.jpg](../../screenshots/235_md.jpg)](../../screenshots/235.jpg)


