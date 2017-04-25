import gi
from apartcore import ApartCore
from typing import *
from cloneentry import CloneToImageEntry
from partinfo import PartitionInfo
from progress import ProgressView

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk


class CloneBody(Gtk.Box):
    def __init__(self, core: ApartCore, sources: List[Dict[str, Any]]):
        Gtk.Box.__init__(self)
        self.core = core
        self.sources = sources

        right_panes = Gtk.VPaned(expand=True)
        self.main_view = MainView(core)
        self.info_view = ClonePartInfo(sources, core, self.main_view)
        right_panes.pack1(self.info_view, shrink=False)
        right_panes.pack2(self.main_view, shrink=False)

        self.paned = Gtk.Paned(expand=True)
        self.paned.pack1(Gtk.StackSidebar(stack=self.info_view), shrink=False)
        self.paned.pack2(right_panes, shrink=False)

        self.add(self.paned)


class ClonePartInfo(Gtk.Stack):
    def __init__(self, sources: List[Dict[str, Any]], core: ApartCore, main_view: 'MainView'):
        Gtk.Stack.__init__(self)
        self.main_view = main_view

        for source in sources:
            for part in source['parts']:
                # ignore partitions <= 1 MiB
                if part['size'] > 1048576:
                    info = PartitionInfo(part, core, main_view)
                    self.add_titled(info, name=info.name(), title=info.title())

        self.connect('notify::visible-child', self.on_child_change)
        self.get_style_context().add_class('clone-part-info')
        self.show_all()

    def on_child_change(self, stack, param):
        self.main_view.new_clone.use_defaults_for(self.get_visible_child())


class MainView(Gtk.Stack):
    def __init__(self, core: ApartCore):
        Gtk.Stack.__init__(self)
        self.set_transition_type(Gtk.StackTransitionType.NONE)
        self.set_transition_duration(200)
        self.new_clone = CloneToImageEntry(self, core)
        self.add_named(self.new_clone, name='new-clone')
        self.progress = ProgressView(core)
        self.add_named(self.progress, name='progress')

    def show(self, name, fade: bool):
        if fade:
            self.set_visible_child_full(name, Gtk.StackTransitionType.CROSSFADE)
        else:
            self.set_visible_child_name(name)

    def show_progress(self, fade: bool = False):
        self.show('progress', fade)

    def show_new_clone(self, fade: bool = False):
        self.show('new-clone', fade)
