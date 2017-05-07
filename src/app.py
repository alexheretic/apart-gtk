#!/usr/bin/env python3
import argparse

import gi
gi.require_version('Gtk', '3.0')  # require version before other importing
import os
import sys
from apartcore import ApartCore, MessageListener
from main import CloneBody
from typing import *
from gi.repository import GLib, Gtk, Gdk, Gio, GdkPixbuf


# App versions, "major.minor", major => new stuff, minor => fixes
__version__ = '0.6'


class LoadingBody(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)
        self.spinner = Gtk.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.spinner.start()
        self.add(self.spinner)


class Window(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='apart')

        self.status_listener = MessageListener(
            on_message=lambda m: GLib.idle_add(self.on_status_msg, m),
            message_predicate=lambda m: m['type'] == 'status')
        self.core = ApartCore(listeners=[self.status_listener])

        self.set_default_size(height=300, width=-1)

        self.loading_body = LoadingBody()
        self.clone_body = None

        self.add(self.loading_body)

        self.connect('delete-event', self.on_delete)

        self.set_icon_name('apart')

    def on_status_msg(self, msg: Dict):
        if msg['status'] == 'dying':
            self.on_delete()
        elif msg['status'] == 'started':
            self.clone_body = CloneBody(self.core, sources=msg['sources'])
            self.remove(self.loading_body)
            self.add(self.clone_body)
            self.clone_body.show_all()
        elif self.clone_body and msg['status'] == 'running':
            self.clone_body.update_sources(msg['sources'])

    def on_delete(self, arg1=None, arg2=None):
        self.status_listener.stop_listening()
        self.remove(self.clone_body)
        self.clone_body.destroy()
        self.add(self.loading_body)
        self.core.kill()


def main():
    win = Window()
    win.connect("delete-event", Gtk.main_quit)

    style_provider = Gtk.CssProvider()
    style_provider.load_from_path(os.path.dirname(os.path.realpath(__file__)) + "/apart.css")
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)

    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Apart GTK v{} GUI for cloning & restoring partitions'.format(__version__),
        prog='apart-gtk')
    parser.add_argument('--version', '-v', action='version', version='%(prog)s v{}'.format(__version__))
    parser.parse_args()
    main()
