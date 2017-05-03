from gi.repository import Gtk


class WarningDialog(Gtk.MessageDialog):
    def __init__(self, root: Gtk.Window, text: str, ok_button_text: str = Gtk.STOCK_OK,
                 cancel_button_text: str = Gtk.STOCK_CANCEL, header: str = ''):
        Gtk.MessageDialog.__init__(self, root, 0, message_type=Gtk.MessageType.WARNING)
        # self.set_decorated()
        self.set_title(header)
        self.icon = Gtk.Image.new_from_icon_name('dialog-warning', Gtk.IconSize.LARGE_TOOLBAR)
        self.text = Gtk.Label(text)
        heading = Gtk.Box()
        heading.add(self.icon)
        heading.add(self.text)

        self.get_message_area().add(heading)
        self.get_message_area().set_spacing(0)
        self.add_button(cancel_button_text, Gtk.ResponseType.CANCEL)
        self.add_button(ok_button_text, Gtk.ResponseType.OK)
        self.show_all()
