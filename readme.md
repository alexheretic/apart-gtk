Apart GTK
=========
Linux GUI for cloning & restoring disk partitions to & from compressed image files.

![Usage](apart-gtk-usage.gif?raw=true "Usage")

## Install
Available on the [Arch Linux AUR](https://aur.archlinux.org/packages/apart-gtk), working on other package formats.

## Dependencies
* python-gobject (ie GTK3)
* apart-core
  * zeromq
  * partclone
  * pigz

## Additional Python Dependencies
See dev-requirements.txt for python requirements, these can be installed with `pip install -r dev-requirements.txt` or similar. These can be bundled with the app, see *Build*.

The apart-core project is written in Rust, so will require rustup and uses cargo to build.

## Run in test mode
With the dev dependencies installed run `./start-test-app` to run from src/ a version of the code with
partclone & partition info mocked. This is useful for GUI development, as you can clone and restore without data risk.

## Build
Run `./build-dist` to build the distribution files to ./target. Optionally `./build-dist --no-python-deps` can be called to skip the python dependency bundling.

## Manual Install
An install looks like the following,after running `./build-dist` copy from ./target to /usr
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
