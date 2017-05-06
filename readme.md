Apart GTK
=========
Linux GUI for cloning disk partitions to images using the GTK toolkit.

![Usage](apart-gtk-usage.gif?raw=true "Usage")

## Dependencies
* python-gobject (ie GTK3)
* apart-core
  * zeromq
  * partclone
  * pigz

## Dev Dependencies
See dev-requirements.txt for python requirements, these can be installed with `pip install -r dev-requirements.txt`.

The apart-core project is written in Rust, so will require rustup and uses cargo to build.

## Run in test mode
With the dev dependencies installed run `./start-test-app` to run from src/ a version of the code with 
partclone & partition info mocked. This is useful for GUI development, as you can clone and restore without actual 
data risk

## Build
Run `./build-dist`

## Install
Linux install will add the following:
```
/usr
├─ bin
│  ├─ apart-gtk
│  └─ apart-gtk-polkit
├─ lib/apart-gtk
│  ├─ apart-core
│  └─ src
│     ├─ app.py
│     ...
│     └─ python files & dependencies
└─ share
   ├─ applications/apart.desktop
   ├─ icons/hicolor/scalable/apps/apart.svg
   ├─ icons/hicolor/48x48/apps/apart.png
   └─ polkit-1/actions/apart.policy
```
