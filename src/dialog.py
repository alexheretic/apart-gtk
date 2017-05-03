from gi.repository import Gtk


def appropriate_icon(msg_type: Gtk.MessageType) -> str:
    if msg_type == Gtk.MessageType.ERROR:
        return 'dialog-error'
    if msg_type == Gtk.MessageType.WARNING:
        return 'dialog-warning'
    return 'dialog-information'


class OkCancelDialog(Gtk.MessageDialog):
    def __init__(self, root: Gtk.Window, text: str,
                 ok_button_text: str = Gtk.STOCK_OK,
                 cancel_button_text: str = Gtk.STOCK_CANCEL,
                 header: str = '',
                 message_type: Gtk.MessageType = Gtk.MessageType.WARNING):
        Gtk.MessageDialog.__init__(self, root, 0, message_type=message_type)
        self.set_title(header)
        self.icon = Gtk.Image()
        self.icon.set_from_icon_name(appropriate_icon(message_type), Gtk.IconSize.LARGE_TOOLBAR)
        self.text = Gtk.Label(text)
        heading = Gtk.Box()
        heading.add(self.icon)
        heading.add(self.text)

        self.get_message_area().add(heading)
        self.get_message_area().set_spacing(0)
        self.add_button(cancel_button_text, Gtk.ResponseType.CANCEL)
        self.add_button(ok_button_text, Gtk.ResponseType.OK)
        self.show_all()


class OkDialog(Gtk.MessageDialog):
    def __init__(self, root: Gtk.Window, text: str,
                 ok_button_text: str = Gtk.STOCK_OK,
                 header: str = '',
                 message_type: Gtk.MessageType = Gtk.MessageType.ERROR):
        Gtk.MessageDialog.__init__(self, root, 0, message_type=message_type)
        self.set_title(header)
        self.icon = Gtk.Image()
        self.icon.set_from_icon_name(appropriate_icon(message_type), Gtk.IconSize.LARGE_TOOLBAR)
        self.text = Gtk.Label(text)
        heading = Gtk.Box()
        heading.add(self.icon)
        heading.add(self.text)

        self.get_message_area().add(heading)
        self.get_message_area().set_spacing(0)
        self.add_button(ok_button_text, Gtk.ResponseType.OK)
        self.show_all()
