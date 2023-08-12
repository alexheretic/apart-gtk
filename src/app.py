#!/usr/bin/env python3
import argparse
import gi
gi.require_version('Gtk', '3.0')  # require version before other importing
import os
import signal
from apartcore import ApartCore, MessageListener
from main import CloneBody
from typing import *
from dialog import OkDialog
from gi.repository import GLib, Gtk, Gdk

# App versions, "major.minor", major => new stuff, minor => fixes
__version__ = '0.27'


class LoadingBody(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)
        self.spinner = Gtk.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, expand=True)
        self.spinner.start()
        self.add(self.spinner)


class Window(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='apart')
        self.dying = False
        self.status_listener = MessageListener(
            on_message=lambda m: GLib.idle_add(self.on_status_msg, m),
            message_predicate=lambda m: m['type'] == 'status')
        self.core = ApartCore(listeners=[self.status_listener],
                              on_finish=lambda code: GLib.idle_add(self.on_delete))
        self.sources = None
        self.sources_interest = []  # array of callbacks on sources update

        self.set_default_size(height=300, width=300 * 16/9)

        self.loading_body = LoadingBody()
        self.clone_body = None

        self.add(self.loading_body)

        self.connect('delete-event', self.on_delete)

        self.set_icon_name('apart')

    def register_interest_in_sources(self, on_update_callback: Callable[[Dict], None]):
        """
        Register a callback to be run every time a new sources message is received
        Note callbacks are run on the GTK main thread
        Run callback immediately if sources are available
        """
        if self.sources:
            on_update_callback(self.sources)
        self.sources_interest.append(on_update_callback)

    def on_status_msg(self, msg: Dict):
        if msg['status'] == 'dying':
            self.on_delete()
        elif msg['status'] == 'started':
            if msg['sources']:
                self.sources = msg['sources']
                self.clone_body = CloneBody(self.core,
                                            sources=msg['sources'],
                                            z_options=msg['compression_options'])
                self.remove(self.loading_body)
                self.add(self.clone_body)
                self.clone_body.show_all()
            else:
                err_dialog = OkDialog(self,
                                      text='No partitions found',
                                      ok_button_text='Exit',
                                      message_type=Gtk.MessageType.ERROR)
                err_dialog.run()
                err_dialog.destroy()
                self.on_delete()
        elif self.clone_body and msg['status'] == 'running':
            self.sources = msg['sources']
            # TODO move to sources_interest with a reliable way of getting toplevel
            self.clone_body.update_sources(msg['sources'])
            for callback in self.sources_interest:
                callback(self.sources)

    def on_delete(self, *args):
        if self.dying:
            return
        self.status_listener.stop_listening()
        if self.clone_body:
            self.remove(self.clone_body)
            self.clone_body.destroy()
            self.add(self.loading_body)
        self.core.kill()
        self.destroy()
        Gtk.main_quit()
        self.dying = True


def main():
    win = Window()
    # allow keyboard interrupt / nodemon to end program cleanly
    for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGUSR2]:
        signal.signal(sig, lambda _s, _f: win.on_delete())

    style_provider = Gtk.CssProvider()
    style_provider.load_from_path(os.path.dirname(os.path.realpath(__file__)) + "/apart.css")
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Apart GTK v{} GUI for cloning & restoring partitions'.format(__version__),
        prog='apart-gtk')
    parser.add_argument('--version', '-v', action='version', version='%(prog)s v{}'.format(__version__))
    parser.parse_args()
    main()
