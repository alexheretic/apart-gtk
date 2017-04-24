import gi
from apartcore import ApartCore, MessageListener
from typing import *
import humanize
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk, Pango


class PartitionInfo(Gtk.Grid):
    def __init__(self, part: Dict[str, Any], core: ApartCore, main_view: 'MainView'):
        Gtk.Grid.__init__(self)
        self.part = part
        self.core = core
        self.main_view = main_view

        def prop_grid(key, val):
            g = Gtk.Grid()
            key_label = Gtk.Label(key)
            key_label.get_style_context().add_class('part-info-key')
            key_label.get_style_context().add_class('dim-label')
            g.add(key_label)
            val_label = Gtk.Label(val)
            val_label.get_style_context().add_class('part-info-val')
            g.add(val_label)
            return g

        self.add(prop_grid('name', self.dev_name()))
        self.add(prop_grid('type', self.part.get('fstype', 'unknown')))
        self.add(prop_grid('label', self.part.get('label', 'none')))
        self.add(prop_grid('size', humanize.naturalsize(self.part['size'], binary=True)))
        clone_button = Gtk.Button("Clone", hexpand=True, halign=Gtk.Align.END)
        if self.part['mounted']:
            clone_button.set_sensitive(False)
            clone_button.set_tooltip_text('Partition is currently mounted')
        else:
            clone_button.connect('clicked', lambda b: self.main_view.show_new_clone())
        self.add(clone_button)

    def name(self):
        return self.part['name']

    def dev_name(self):
        return '/dev/' + self.name()

    def label(self):
        return self.part.get('label')

    def title(self):
        max_length = 10
        label = self.part.get('label', '').strip()
        if len(label) > max_length:
            label = label[:max_length-3].rstrip() + '...'
        return '{} {}'.format(self.name(), label)
