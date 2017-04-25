import gi
from apartcore import ApartCore, MessageListener
from typing import *
import humanize

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk, Pango


def key_and_val(key: str, val: str, **kwargs) -> Gtk.Box:
    box = Gtk.Box(**kwargs)
    key_label = Gtk.Label(key)
    key_label.get_style_context().add_class('part-info-key')
    key_label.get_style_context().add_class('dim-label')
    box.add(key_label)
    val_label = Gtk.Label(val)
    val_label.get_style_context().add_class('part-info-val')
    box.add(val_label)
    box.key_label = key_label
    box.value_label = val_label
    return box


class PartitionInfo(Gtk.Grid):
    def __init__(self, part: Dict[str, Any], core: ApartCore, main_view: 'MainView'):
        Gtk.Grid.__init__(self)
        self.part = part
        self.core = core
        self.main_view = main_view

        self.add(key_and_val('Name', self.dev_name()))
        self.add(key_and_val('Type', self.part.get('fstype', 'unknown')))
        self.add(key_and_val('Label', self.part.get('label', 'none')))
        self.add(key_and_val('Size', humanize.naturalsize(self.part['size'], binary=True)))
        clone_button = Gtk.Button("Clone", hexpand=True, halign=Gtk.Align.END)
        if self.is_mounted():
            clone_button.set_sensitive(False)
            clone_button.set_tooltip_text('Partition is currently mounted')
        else:
            clone_button.connect('clicked', lambda b: self.main_view.show_new_clone())
        self.add(clone_button)
        self.clone_button = clone_button
        main_view.connect('notify::visible-child', self.on_main_view_change)

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

    def on_main_view_change(self, main_view: Gtk.Stack, somearg):
        from cloneentry import CloneToImageEntry

        current_view = main_view.get_visible_child()
        if type(current_view) is CloneToImageEntry:
            self.clone_button.set_opacity(0)
        else:
            self.clone_button.set_opacity(1)

    def is_mounted(self) -> bool:
        return self.part['mounted']
