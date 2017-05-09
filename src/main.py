from apartcore import ApartCore
from typing import *
from cloneentry import CloneToImageEntry
from partinfo import PartitionInfo
from progress import ProgressAndHistoryView
from gi.repository import Gtk
from restoreentry import RestoreFromImageEntry
import settings


class CloneBody(Gtk.Box):
    def __init__(self, core: ApartCore, sources: List[Dict[str, Any]]):
        Gtk.Box.__init__(self)
        self.core = core

        right_panes = Gtk.VPaned(expand=True)
        self.main_view = MainView(core)
        self.info_view = ClonePartInfo(sources, core, self.main_view)
        right_panes.pack1(self.info_view, shrink=False)
        right_panes.pack2(self.main_view, shrink=False)

        self.side_bar_box = Gtk.EventBox()
        self.side_bar_box.add(Gtk.StackSidebar(stack=self.info_view))
        self.side_bar_box.connect('button-press-event', self.side_bar_click)

        self.paned = Gtk.Paned(expand=True)
        self.paned.pack1(self.side_bar_box, shrink=False)
        self.paned.pack2(right_panes, shrink=False)

        self.add(self.paned)

    def update_sources(self, sources: List[Dict[str, Any]]):
        self.info_view.update_sources(sources)

    def side_bar_click(self, *args):
        self.core.send('type: status-request')


class ClonePartInfo(Gtk.Stack):
    def __init__(self, sources: List[Dict[str, Any]], core: ApartCore, main_view: 'MainView'):
        Gtk.Stack.__init__(self)
        self.core = core
        self.sources = sources
        self.main_view = main_view
        self.updating = False

        self.connect('notify::visible-child', self.on_child_change)
        self.get_style_context().add_class('part-info')

        self.update_sources(sources)
        self.show_all()

    def on_child_change(self, *args):
        visible = self.get_visible_child()
        if visible:
            self.main_view.new_clone.use_defaults_for(visible)
            self.main_view.new_restore.use_defaults_for(visible)

    def update_sources(self, sources: List[Dict[str, Any]]):
        previous_visible = self.get_visible_child_name()

        parts = []
        for source in sources:
            for part in source['parts']:
                # ignore partitions <= 1 MiB
                if part['size'] > 1048576:
                    parts.append(PartitionInfo(part, self.core, self.main_view))

        changed_partition_info = False
        names = list(map(lambda p: p.name(), parts))
        for child in self.get_children():
            if self.child_get_property(child, 'name') not in names:
                child.destroy()
                changed_partition_info = True

        for info in parts:
            existing = self.get_child_by_name(info.name())
            if not existing or (existing and existing.part != info.part):
                if existing:
                    existing.destroy()
                self.add_titled(info, name=info.name(), title=info.title())
                info.show_all()
                changed_partition_info = True

        if changed_partition_info and previous_visible and self.get_child_by_name(previous_visible):
            self.set_visible_child_name(previous_visible)


class MainView(Gtk.Stack):
    def __init__(self, core: ApartCore):
        Gtk.Stack.__init__(self)
        self.set_transition_type(Gtk.StackTransitionType.NONE)
        self.set_transition_duration(settings.animation_duration_ms())
        self.new_clone = CloneToImageEntry(self, core)
        self.add_named(self.new_clone, name='new-clone')
        self.progress = ProgressAndHistoryView(core)
        self.add_named(self.progress, name='progress')
        self.new_restore = RestoreFromImageEntry(self, core)
        self.add_named(self.new_restore, name='new-restore')

    def show(self, name, fade: bool):
        if fade:
            self.set_visible_child_full(name, Gtk.StackTransitionType.CROSSFADE)
        else:
            self.set_visible_child_name(name)

    def show_progress(self, fade: bool = False):
        self.show('progress', fade)

    def show_new_clone(self, fade: bool = False):
        self.show('new-clone', fade)

    def show_new_restore(self, fade: bool = False):
        self.show('new-restore', fade)
