from apartcore import ApartCore
from dialog import OkCancelDialog
from partinfo import PartitionInfo
from gi.repository import Gtk
from typing import *


class RestoreFromImageEntry(Gtk.Box):
    def __init__(self, main_view: 'MainView', core: ApartCore, z_options: List[str]):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, expand=True, halign=Gtk.Align.CENTER)
        self.main_view = main_view
        self.core = core
        self.z_options = z_options

        self.title = Gtk.Label('', xalign=0.5)
        self.title.get_style_context().add_class('dim-label')

        self.image_label = Gtk.Label("Image File", xalign=1.0)
        self.image_label.get_style_context().add_class('dim-label')
        self.image_entry = Gtk.FileChooserButton(title='Select Image File')
        image_file_filter = Gtk.FileFilter()
        image_file_filter.set_name('Apart Image files')
        for z_option in z_options:
            image_file_filter.add_pattern('*.apt.*.{}'.format(z_option))
            if z_option == 'zst':  # also support .zstd from v0.14
                image_file_filter.add_pattern('*.apt.*.zstd')
        self.image_entry.add_filter(image_file_filter)
        self.image_entry.connect('selection-changed', lambda v: self.on_image_select())

        self.options = Gtk.Grid(row_spacing=6)
        self.options.get_style_context().add_class('new-clone-options')
        self.options.attach(self.title, left=0, top=0, width=2, height=1)
        self.options.attach(self.image_label, left=0, top=1, width=1, height=1)
        self.options.attach(self.image_entry, left=1, top=1, width=1, height=1)

        self.cancel_btn = Gtk.Button('Cancel')
        self.cancel_btn.connect('clicked', lambda v: self.main_view.show_progress())
        self.start_btn = Gtk.Button('Restore Partition')
        self.start_btn.set_sensitive(False)
        self.start_btn.connect('clicked', lambda v: self.user_confirm())

        self.buttons = Gtk.Box(halign=Gtk.Align.END)
        self.buttons.get_style_context().add_class('new-clone-buttons')
        self.buttons.add(self.cancel_btn)
        self.buttons.add(self.start_btn)

        self.add(self.options)
        self.options.attach_next_to(self.buttons, sibling=self.image_label,
                                    side=Gtk.PositionType.BOTTOM, width=2, height=1)
        self.last_part_info = None

    def use_defaults_for(self, part_info: PartitionInfo):
        self.last_part_info = part_info
        self.update_title()
        self.set_start_sensitivity()

    def set_start_sensitivity(self):
        if self.last_part_info:
            if self.last_part_info.is_mounted():
                self.start_btn.set_sensitive(False)
                self.start_btn.set_tooltip_text('Partition is currently mounted')
            elif not self.image_entry.get_filename():
                self.start_btn.set_sensitive(False)
                self.start_btn.set_tooltip_text('Select an image file to restore from')
            else:
                self.start_btn.set_sensitive(True)
                self.start_btn.set_tooltip_text(None)

    def update_title(self):
        z_options = ', '.join(map(lambda z: '.' + z, self.z_options))

        if self.last_part_info:
            self.title.set_text('Image file ({}) ⟶ {}'.format(z_options, self.last_part_info.dev_name()))

    def user_confirm(self):
        dialog = OkCancelDialog(self.get_toplevel(),
                                header='Overwrite partition',
                                text='Restoring this image will overwrite all current partition data',
                                ok_button_text='Restore',
                                message_type=Gtk.MessageType.WARNING)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.start()
        dialog.destroy()

    def start(self):
        image_file = self.image_entry.get_filename()
        if not image_file or not self.last_part_info:
            return

        yaml_template = 'type: restore\nsource: {source}\ndestination: {destination}'
        self.core.send(yaml_template.format(source=image_file,
                                            destination=self.last_part_info.dev_name()))
        self.main_view.show_progress(fade=True)
        self.image_entry.unselect_all()

    def on_image_select(self):
        self.set_start_sensitivity()


