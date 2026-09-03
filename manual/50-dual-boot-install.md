# Dual Boot Install

You can install Maslow OS to free space alongside Windows or another operating system on supported x86_64 hardware.

This installation method still comes with LUKS encryption for the partition by default so it's effectively no different than full drive and simply requires free space to be available on the disk.

## Making Space on Windows

To install alongside Windows, type `disk management` in the start menu and select the option for **Create and format hard disk partitions**.

 ![dual-boot-1](images/dual-boot-1.webp)

Find the appropriate partition, right click, and choose **Shrink Volume**.

![dual-boot-2](images/dual-boot-2.webp)

Input the amount you'd like to shrink the volume by. This becomes the total space for Maslow OS, including its boot partition.

 ![dual-boot-3](images/dual-boot-3.webp)

When you're finished, you should see something like this, where the 50GB section is where we'll install Maslow OS in this example.

 ![dual-boot-4](images/dual-boot-4.webp)

## Installing Maslow OS

The Maslow OS install process is otherwise the same as normal. After you select your disk, you'll be given the option of **Free space install**. Select that option to prevent wiping the full disk.

 ![dual-boot-5](images/dual-boot-5.webp)

Confirm that everything looks good and wait for the install to finish like normal. This is also where you could elect to install unencrypted (not recommended) just like on a full-drive install.
 ![dual-boot-6](images/dual-boot-6.webp)

## Adding Other Installs to the Bootloader

When the Maslow OS installation finishes, Limine is the default bootloader. You can also add Limine entries for other installations such as Windows.

To do that, run `limine-scan` and follow the prompts to add the items you want to the Limine configuration. When you boot, you'll see the Maslow OS entry as well as Windows Boot Manager or other detected systems.

## Bitlocker

It's important to note that this install method is not compatible with Bitlocker as it encrypts the entire drive, not just the partition. If you encounter an error stating that Bitlocker is enabled, boot to Windows, go to **Settings -> Privacy & Security -> Device encryption** and toggle Bitlocker off. It may take some time to decrypt the drive.

 ![dual-boot-7](images/dual-boot-7.webp)
