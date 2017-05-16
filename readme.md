Apart GTK
=========
Linux GUI for cloning & restoring disk partitions to & from compressed image files.

![Usage](https://raw.githubusercontent.com/alexheretic/apart-gtk/readme-images/apart-gtk-usage.gif?raw=true "Usage")

## Install
Available on the [Arch Linux AUR](https://aur.archlinux.org/packages/apart-gtk), working on other package formats.

## Dependencies
* python >= 3.5
* python-gobject, GTK >= 3.22
* polkit - for non-root usage
* apart-core
  * zeromq > 4
  * partclone
  * pigz

## Additional Python Dependencies
See dev-requirements.txt for python requirements, these can be installed with `pip3 install -r dev-requirements.txt` or similar. These can be bundled with the app, see *Build*.

The apart-core project is written in Rust, so will require rustup and uses cargo to build.

## Build in Ubuntu
To build make sure you have Python 3, rustup and `libzmq3-dev`. If you have pip issues try `sudo easy_install3 -U pip`. To run you'll need to install `apt install policykit-1 partclone pigz`, and python dependencies from above.

## Run in test mode
With the dev dependencies installed run `./start-test-app` to run from src/ a version of the code with
partclone & partition info mocked. This is useful for GUI development, as you can clone and restore without data risk.

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
