import gi
from apartcore import ApartCore
from partinfo import PartitionInfo

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk


class CloneToImageEntry(Gtk.Box):
    def __init__(self, main_view: 'MainView', core: ApartCore):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, expand=True)
        self.main_view = main_view
        self.core = core

        self.title = Gtk.Label('', xalign=0.5)
        self.title.get_style_context().add_class('dim-label')

        self.name_label = Gtk.Label("Backup name", xalign=1.0)
        self.name_label.get_style_context().add_class('dim-label')
        self.name_entry = Gtk.Entry()

        self.dir_label = Gtk.Label("Backup directory", xalign=1.0)
        self.dir_label.get_style_context().add_class('dim-label')
        self.dir_entry = Gtk.FileChooserButton(title='Select Backup Directory',
                                               action=Gtk.FileChooserAction.SELECT_FOLDER)

        self.options = Gtk.Grid(row_spacing=6)
        self.options.get_style_context().add_class('new-clone-options')
        self.options.attach(self.title, left=0, top=0, width=2, height=1)
        self.options.attach_next_to(self.name_label, self.title,  side=Gtk.PositionType.BOTTOM, width=1, height=1)
        self.options.attach_next_to(self.name_entry, self.name_label, side=Gtk.PositionType.RIGHT, width=1, height=1)

        self.options.attach_next_to(self.dir_label, self.name_label, side=Gtk.PositionType.BOTTOM, width=1, height=1)
        self.options.attach_next_to(self.dir_entry, self.dir_label, side=Gtk.PositionType.RIGHT, width=1, height=1)

        self.cancel_btn = Gtk.Button('Cancel')
        self.cancel_btn.connect('clicked', lambda v: self.main_view.show_progress())
        self.start_btn = Gtk.Button('Create Image')
        self.start_btn.connect('clicked', lambda v: self.start_clone())

        self.buttons = Gtk.Box(halign=Gtk.Align.END)
        self.buttons.get_style_context().add_class('new-clone-buttons')
        self.buttons.add(self.cancel_btn)
        self.buttons.add(self.start_btn)

        self.add(self.options)
        self.options.attach_next_to(self.buttons, self.dir_label, side=Gtk.PositionType.BOTTOM, width=2, height=1)

        self.last_part_info = None

    def use_defaults_for(self, part_info: PartitionInfo):
        default_backup_name = part_info.label() or part_info.name()
        self.name_entry.set_text(default_backup_name.replace(' ', '_'))
        if self.dir_entry.get_filename() is None:
            self.dir_entry.set_filename('/tmp')

        self.last_part_info = part_info
        self.update_title()

        if part_info.is_mounted():
            self.start_btn.set_sensitive(False)
            self.start_btn.set_tooltip_text('Partition is currently mounted')
        else:
            self.start_btn.set_sensitive(True)
            self.start_btn.set_tooltip_text(None)

    def update_title(self):
        if not self.last_part_info:
            return
        title = '{dev_name} -> compressed image file'.format(
            dev_name=self.last_part_info.dev_name(),
            backup_name=self.backup_name())
        self.title.set_text(title)

    def start_clone(self):
        backup_dir = self.dir_entry.get_filename()
        if not backup_dir or not self.last_part_info:
            return

        backup_name = self.backup_name()
        source = self.last_part_info.dev_name()

        self.core.send('type: clone\nsource: {}\ndestination: {}\nname: {}'.format(source, backup_dir, backup_name))
        self.main_view.show_progress(fade=True)

    def backup_name(self):
        return self.name_entry.get_text() or \
               self.last_part_info and (self.last_part_info.label() or self.last_part_info.name())
