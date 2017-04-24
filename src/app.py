#!/usr/bin/env python3
import os
import sys
import gi
from apartcore import ApartCore, MessageListener
from body import CloneBody
from typing import *
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk


class Header(Gtk.HeaderBar):
    def __init__(self):
        Gtk.HeaderBar.__init__(self, title='apart')
        self.set_show_close_button(True)


class LoadingBody(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)
        self.spinner = Gtk.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.spinner.start()
        self.add(self.spinner)


class Window(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='')

        self.status_listener = MessageListener(
            on_message=lambda m: GLib.idle_add(self.on_status_msg, m),
            message_predicate=lambda m: m['type'] == 'status')
        self.core = ApartCore(listeners=[self.status_listener])

        self.set_default_size(height=300, width=-1)
        self.set_titlebar(Header())

        self.loading_body = LoadingBody()
        self.clone_body = None

        self.add(self.loading_body)

        self.connect('delete-event', self.on_delete)

    def on_status_msg(self, msg: Dict):
        if msg['status'] == 'dying':
            self.on_delete()
        if msg['status'] == 'started':
            self.clone_body = CloneBody(self.core, sources=msg['sources'])
            self.remove(self.loading_body)
            self.add(self.clone_body)
            self.clone_body.show_all()

    def on_delete(self, arg1=None, arg2=None):
        self.status_listener.stop_listening()
        self.remove(self.clone_body)
        self.add(self.loading_body)
        self.core.kill()


if __name__ == "__main__":
    if os.getuid() != 0 and os.environ.get('APART_GTK_NON_ROOT') != 'Y':
        # Normally it only makes sense to run apart->partclone as root
        # Use APART_GTK_NON_ROOT=Y if otherwise
        sys.stderr.write('Root privileges are required\n')
        sys.exit(1)
    win = Window()
    win.connect("delete-event", Gtk.main_quit)

    style_provider = Gtk.CssProvider()
    style_provider.load_from_path("src/apart.css")
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win.show_all()
    Gtk.main()
