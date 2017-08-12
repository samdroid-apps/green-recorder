# Green Recorder

![Green Recorder](http://i.imgur.com/EAZefUa.png)

## About

A simple desktop recorder for Linux systems. Built using Python, GTK+ 3 and ffmpeg. It supports recording audio and video on almost all Linux interfaces. Also, Green Recorder is the **first desktop program to support Wayland display server on GNOME session**.

The following formats are currently supported: **mkv**, **avi**, **mp4**, **wmv**, **gif** and **nut** (And only WebM for Wayland's GNOME session). You can stop the recording process easily by right-clicking the icon and choosing "Stop Record". Or middle-clicking the recording icon in the notifications area (but doesn't work on all interfaces).

You can choose the audio input source you want from the list. You can also set the default values you want from the preferences window. And a lot more.

Here's a GIF image recorded with Green Recorder for Green Recorder:

![Green Recorder](https://media.giphy.com/media/3o6vXLgAWsH8qAcpDa/giphy.gif)

Please, consider supporting us on Patreon if you like the software. More features and new versions would be released with each goal we achieve there: https://www.patreon.com/fossproject


### How it works?

It uses the D-Bus API to connect to the built-in screencasting tool in GNOME Shell. It uses this to record video. To record audio, it launches an instance of ffmpeg in the background. After the recording is finished, it merges the two files into the WebM file.

For Xorg, it uses ffmpeg only for both audio and video.

By default, On Wayland only, Green Recorder uses the V8 encoder instead of the default V9 encoder in GNOME Shell because of the CPU & RAM consumption issue with V9. Which - now - should also give you better performance. On Xorg, each format uses its own default encoder.

Also, for GIF format, Green Recorder first records the required video as a raw video. And then it generated the GIF image from the raw video. In this way, you'll get an optimized GIF image size which is at least 10x better than the normal ffmpeg recording.

### Localization

Green Recorder supports localization. If you want to translate the program into your language, fork the repository on GitHub and create a new file under "po" folder with your language ISO code (like fr.po, de.po, cs.po..). And translate the strings from there.

Alternatively, you can open the green-recorder.pot file using programs like PoEdit and start translating.

## Download

### Ubuntu 16.04/16.10/17.04/17.10 or Linux Mint 18/18.1/18.2

Make sure you have enabled the multiverse and universe repositories before trying to install the program from the PPA (to be able to download the dependencies). You can install Green Recorder from the following PPA:

    sudo add-apt-repository ppa:fossproject/ppa
    sudo apt update
    sudo apt install green-recorder

### Debian

You can grab the Debian packages directly from the PPA itself and install it on any Debian distribution. You mainly need the "green-recorder" package and "python3-pydbus". Other dependancies (like ffmpeg) are probably in Debian repositories: http://ppa.launchpad.net/fossproject/ppa/ubuntu/

### Fedora 24/25/26/Rawhide

To install Green Recorder on Fedora 24:

    sudo dnf config-manager --add-repo http://download.opensuse.org/repositories/home:mhsabbagh/Fedora_24/home:mhsabbagh.repo
    sudo dnf install green-recorder

Fedora 25:

    sudo dnf config-manager --add-repo http://download.opensuse.org/repositories/home:mhsabbagh/Fedora_25/home:mhsabbagh.repo
    sudo dnf install green-recorder

Fedora 26:

    sudo dnf config-manager --add-repo http://download.opensuse.org/repositories/home:mhsabbagh/Fedora_26/home:mhsabbagh.repo
    sudo dnf install green-recorder

Fedora Rawhide:

    sudo dnf config-manager --add-repo http://download.opensuse.org/repositories/home:mhsabbagh/Fedora_Rawhide/home:mhsabbagh.repo
    sudo dnf install green-recorder

### CentOS 7

Run the following commands as root:

    cd /etc/yum.repos.d/
    wget http://download.opensuse.org/repositories/home:mhsabbagh/CentOS_7/home:mhsabbagh.repo
    yum install green-recorder

### Arch Linux

You can install Green recorder using your [AUR helper](https://wiki.archlinux.org/index.php/AUR_helpers):

    yaourt -S green-recorder-git

### Other Distributions

The program requires the pydbus python3 module, install it first:

    sudo pip3 install pydbus

The source code is available to download via: [https://github.com/green-project/green-recorder/archive/master.zip](https://github.com/green-project/green-recorder/archive/master.zip). You can simply download it and install the dependencies on your distribution (gir1.2-appindicator3, gawk, python3-gobject, python3-urllib3, x11-utils, ffmpeg, pydbus, pulseaudio, xdg-open (or xdg-utils), python3-configparser, imagemagick). And then run:

    meson . build
    cd build
    ninja
    sudo ninja install

You may have to install meson or ninja.  However, if you just type the commands into your terminal; your shell may prompt you to install the correct packages (thanks PackageKit)!

## Contact

The program is released under GPL 3. For contact: mhsabbagh[at]outlook.com.
