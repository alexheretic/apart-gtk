import re
from apartcore import ApartCore
from partinfo import PartitionInfo
from gi.repository import Gtk
from typing import *

invalid_name_re = re.compile(r'[^A-Za-z0-9 _-]')


class CloneToImageEntry(Gtk.Box):
    def __init__(self, main_view: 'MainView', core: ApartCore, z_options: List[str]):
        Gtk.Box.__init__(self,
                         orientation=Gtk.Orientation.VERTICAL,
                         expand=True,
                         halign=Gtk.Align.CENTER)
        self.main_view = main_view
        self.core = core

        self.title = Gtk.Label('', xalign=0.5)
        self.title.get_style_context().add_class('dim-label')

        self.name_label = Gtk.Label("Backup name", xalign=1.0)
        self.name_label.get_style_context().add_class('dim-label')
        self.name_entry = Gtk.Entry()
        self.name_entry.connect('changed', self.on_name_change)

        self.dir_label = Gtk.Label("Backup directory", xalign=1.0)
        self.dir_label.get_style_context().add_class('dim-label')
        self.dir_entry = Gtk.FileChooserButton(title='Select Backup Directory',
                                               action=Gtk.FileChooserAction.SELECT_FOLDER)

        ordered_z_options = []
        for z_option in z_options:
            if z_option == 'uncompressed':
                ordered_z_options.append(z_option)
        for z_option in z_options:
            if z_option != 'uncompressed':
                ordered_z_options.append(z_option)

        z_store = Gtk.ListStore(str, str)
        for z_option in ordered_z_options:
            if z_option == 'uncompressed':
                z_store.append([z_option, 'None'])
            else:
                z_store.append([z_option, z_option])

        z_renderer = Gtk.CellRendererText()
        self.z_label = Gtk.Label("Compression", xalign=1.0)
        self.z_label.get_style_context().add_class('dim-label')
        self.z_entry = Gtk.ComboBox.new_with_model(z_store)
        self.z_entry.pack_start(z_renderer, True)
        self.z_entry.add_attribute(z_renderer, 'text', 1)

        if 'zst' in ordered_z_options:
            self.z_entry.set_active(ordered_z_options.index('zst'))
        elif 'gz' in ordered_z_options:
            self.z_entry.set_active(ordered_z_options.index('gz'))
        elif 'lz4' in ordered_z_options:
            self.z_entry.set_active(ordered_z_options.index('lz4'))
        else:
            self.z_entry.set_active(0)

        self.z_entry.connect('changed', self.update_title)

        self.options = Gtk.Grid(row_spacing=6)
        self.options.get_style_context().add_class('new-clone-options')
        self.options.attach(self.title, left=0, top=0, width=2, height=1)
        self.options.attach_next_to(self.name_label, self.title,
                                    side=Gtk.PositionType.BOTTOM, width=1, height=1)
        self.options.attach_next_to(self.name_entry, self.name_label,
                                    side=Gtk.PositionType.RIGHT, width=1, height=1)

        self.options.attach_next_to(self.z_label, self.name_label,
                                    side=Gtk.PositionType.BOTTOM, width=1, height=1)
        self.options.attach_next_to(self.z_entry, self.z_label,
                                    side=Gtk.PositionType.RIGHT, width=1, height=1)

        self.options.attach_next_to(self.dir_label, self.z_label,
                                    side=Gtk.PositionType.BOTTOM, width=1, height=1)
        self.options.attach_next_to(self.dir_entry, self.dir_label,
                                    side=Gtk.PositionType.RIGHT, width=1, height=1)

        self.cancel_btn = Gtk.Button('Cancel')
        self.cancel_btn.connect('clicked', lambda v: self.main_view.show_progress())
        self.start_btn = Gtk.Button('Create Image')
        self.start_btn.connect('clicked', lambda v: self.start_clone())

        self.buttons = Gtk.Box(halign=Gtk.Align.END)
        self.buttons.get_style_context().add_class('new-clone-buttons')
        self.buttons.add(self.cancel_btn)
        self.buttons.add(self.start_btn)

        self.add(self.options)
        self.options.attach_next_to(self.buttons, self.dir_label,
                                    side=Gtk.PositionType.BOTTOM, width=2, height=1)

        self.last_part_info = None

    def use_defaults_for(self, part_info: PartitionInfo):
        default_backup_name = part_info.label() or part_info.name()
        self.name_entry.set_text(default_backup_name.replace(' ', '_'))

        self.last_part_info = part_info
        self.update_title()

        if part_info.is_mounted():
            self.start_btn.set_sensitive(False)
            self.start_btn.set_tooltip_text('Partition is currently mounted')
        else:
            self.start_btn.set_sensitive(True)
            self.start_btn.set_tooltip_text(None)

    def update_title(self, *args: None):
        compression = True
        active = self.z_entry.get_active_iter()
        if active:
            model = self.z_entry.get_model()
            if model[active][0] == 'uncompressed':
                compression = False

        if self.last_part_info:
            if compression:
                self.title.set_text(self.last_part_info.dev_name() + ' ⟶ compressed image file')
            else:
                self.title.set_text(self.last_part_info.dev_name() + ' ⟶ uncompressed image file')

    def start_clone(self):
        backup_dir = self.dir_entry.get_filename()
        if not backup_dir or not self.last_part_info:
            return

        backup_name = self.backup_name()
        source = self.last_part_info.dev_name()

        compression = ""
        active = self.z_entry.get_active_iter()
        if active:
            model = self.z_entry.get_model()
            compression = "compression: {}".format(model[active][0])

        self.core.send('type: clone\nsource: {}\ndestination: {}\nname: {}\n{}'.format(source,
                                                                                       backup_dir,
                                                                                       backup_name,
                                                                                       compression))
        self.main_view.show_progress(fade=True)

    def backup_name(self):
        return self.name_entry.get_text() or \
               self.last_part_info and (self.last_part_info.label() or self.last_part_info.name())

    def on_name_change(self, entry):
        entry.set_text(re.sub(invalid_name_re, '', entry.get_text()))
        if len(entry.get_text()) > 0 and self.last_part_info and not self.last_part_info.is_mounted():
            self.start_btn.set_sensitive(True)
        else:
            self.start_btn.set_sensitive(False)
