from typing import *
from gi.repository import Gtk
import humanize
from apartcore import ApartCore


def key_and_val(key: str, val: str, visible=False) -> Gtk.Box:
    box = Gtk.Box(visible=visible)
    key_label = Gtk.Label(key, visible=visible)
    key_label.get_style_context().add_class('info-key')
    key_label.get_style_context().add_class('dim-label')
    box.add(key_label)
    val_label = Gtk.Label(val, visible=visible)
    val_label.get_style_context().add_class('info-val')
    box.add(val_label)
    box.key_label = key_label
    box.value_label = val_label
    return box


class PartitionInfo(Gtk.Box):
    def __init__(self, part: Dict[str, Any], core: ApartCore, main_view: 'MainView'):
        Gtk.Box.__init__(self)
        self.part = part
        self.core = core
        self.main_view = main_view

        self.add(key_and_val('Name', self.name()))
        self.add(key_and_val('Type', self.part.get('fstype', 'unknown')))
        self.add(key_and_val('Label', self.part.get('label', 'none')))
        self.add(key_and_val('Size', humanize.naturalsize(self.part['size'], binary=True)))
        self.clone_button = Gtk.Button("Clone", halign=Gtk.Align.END)
        self.restore_button = Gtk.Button("Restore", halign=Gtk.Align.END)
        if self.is_mounted():
            self.clone_button.set_sensitive(False)
            self.clone_button.set_tooltip_text('Partition is currently mounted')
            self.restore_button.set_sensitive(False)
            self.restore_button.set_tooltip_text('Partition is currently mounted')
        else:
            self.clone_button.connect('clicked', lambda b: self.main_view.show_new_clone())
            self.restore_button.connect('clicked', lambda b: self.main_view.show_new_restore())
        buttons = Gtk.Box(hexpand=True, halign=Gtk.Align.END)
        buttons.add(self.clone_button)
        buttons.add(self.restore_button)
        self.add(buttons)
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
        from restoreentry import RestoreFromImageEntry

        current_view = main_view.get_visible_child()
        if not self.is_mounted():
            self.clone_button.set_sensitive(type(current_view) is not CloneToImageEntry)
            self.restore_button.set_sensitive(type(current_view) is not RestoreFromImageEntry)

    def is_mounted(self) -> bool:
        return self.part['mounted']
