#!/usr/bin/env python3
import os
import sys
import gi
from apartcore import ApartCore, MessageListener
from typing import *
import humanize
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


class CloneBody(Gtk.Box):
    def __init__(self, core: ApartCore, sources: List[Dict[str, Any]]):
        Gtk.Box.__init__(self)
        self.core = core
        self.sources = sources

        right_panes = Gtk.VPaned(expand=True)
        self.info_stack = ClonePartInfo(sources)
        right_panes.add1(self.info_stack)
        right_panes.add2(Gtk.Label("Nothing in progress", selectable=False))

        self.paned = Gtk.Paned(expand=True)
        self.paned.add1(Gtk.StackSidebar(stack=self.info_stack))
        self.paned.add2(right_panes)

        self.add(self.paned)


class ClonePartInfo(Gtk.Stack):
    def __init__(self, sources: List[Dict[str, Any]]):
        Gtk.Stack.__init__(self)
        for source in sources:
            for part in source['parts']:
                # ignore partitions <= 1 MiB
                if part['size'] > 1048576:
                    info = PartitionInfo(part)
                    self.add_titled(info.widget(), name=info.name(), title=info.title())
        self.show_all()



class PartitionInfo:
    def __init__(self, part: Dict[str, Any]):
        self.part = part
        self._widget = None

    def create_widget(self):
        def prop_grid(key, val):
            g = Gtk.Grid()
            key_label = Gtk.Label(key + ':')
            key_label.get_style_context().add_class('part-info-key')
            g.add(key_label)
            val_label = Gtk.Label(val)
            val_label.get_style_context().add_class('part-info-val')
            g.add(val_label)
            return g

        box = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE)
        box.add(prop_grid('name', '/dev/' + self.name()))
        box.add(prop_grid('type', self.part.get('fstype', 'unknown')))
        box.add(prop_grid('label', self.part.get('label', 'none')))
        box.add(prop_grid('size', humanize.naturalsize(self.part['size'], binary=True)))

        self._widget = box

    def name(self):
        return self.part['name']

    def title(self):
        max_length = 10
        label = self.part.get('label', '').strip()
        if len(label) > max_length:
            label = label[:max_length-3].rstrip() + '...'
        return '{} {}'.format(self.name(), label)

    def widget(self):
        if not self._widget:
            self.create_widget()
        return self._widget


class Window(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title='')

        self.status_listener = MessageListener(
            on_message=lambda m: GLib.idle_add(self.on_status_msg, m),
            message_predicate=lambda m: m['type'] == 'status')
        self.core = ApartCore(listeners=[self.status_listener])

        self.set_default_size(800, 400)
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
    style_provider.load_from_data("""
    .part-info-key {
      margin-right: 1ex;
    }
    """.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win.show_all()
    Gtk.main()
