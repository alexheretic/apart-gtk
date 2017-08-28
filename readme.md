Apart GTK
=========
Linux GUI for cloning & restoring disk partitions to & from compressed image files, using [partclone](http://partclone.org) to do the heavy lifting.

![Usage](https://raw.githubusercontent.com/alexheretic/apart-gtk/readme-images/apart-gtk-usage.gif?raw=true "Usage")

## Install
* Arch: available on the [AUR](https://aur.archlinux.org/packages/apart-gtk)
* Ubuntu/Debian: .deb package available [in releases](https://github.com/alexheretic/apart-gtk/releases)
* Fedora: .rpm package available [in releases](https://github.com/alexheretic/apart-gtk/releases)

If you have dependency issues, see the build sections for your distro. The GTK 3.22 requirement means you'll probably need a >= 2017 distro.

## Dependencies
* python >= 3.5
* python-gobject, GTK >= 3.22
* pyzmq, humanize, pyyaml
* polkit - for non-root usage
* apart-core
  * zeromq > 4
  * partclone
  * pigz
  * lz4 *(optional: adds compression option)*
  * zstd >= 1.2.0 *(optional: adds compression option)*

## Build on Arch
`pacman -Syu --needed python python-gobject python-yaml python-pyzmq python-humanize gtk3 pigz partclone zeromq polkit rustup git`

Follow build steps below.

## Build on Ubuntu >= 17.04
Build deps: `apt install build-essential git libzmq3-dev curl pkg-config python3` + `rustup`

Run deps: `apt install policykit-1 partclone pigz python3-humanize python3-zmq python3-yaml libgtk-3-0`

Follow build steps below.

## Build on Fedora >= 25
`dnf install git zeromq-devel rust cargo python3-zmq python3-yaml python3-humanize pigz polkit gtk3`

Install partclone, ie with something like
```sh
wget https://forensics.cert.org/fedora/cert/25/x86_64//partclone-0.2.90-1.fc25.x86_64.rpm
rpm -Uvh partclone-0.2.90-1.fc25.x86_64.rpm
```

Follow build steps below.

## Build
Run `./configure` then `make` having installed the above build dependencies

## Manual Install
After building run `make install` which copies the build made in ./target to /usr
```
/usr
├─ bin
│  └─ apart-gtk
├─ lib/apart-gtk
│  ├─ apart-core
│  └─ src
│     ├─ app.py
│     └─ ... python files
└─ share
   ├─ applications/apart-gtk.desktop
   ├─ icons/hicolor/scalable/apps/apart.svg
   ├─ icons/hicolor/48x48/apps/apart.png
   └─ polkit-1/actions/com.github.alexheretic.pkexec.apart-gtk.policy
```

`make uninstall` can be used to remove these files

## Run in test mode
With the dev dependencies installed run `./start-test-app` to run from src/ a version of the code with
partclone & partition info mocked. This is useful for GUI development, as you can clone and restore without data risk.
