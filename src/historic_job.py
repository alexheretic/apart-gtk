from datetime import datetime, timezone
from enum import auto, Enum
from typing import *
from gi.repository import Gtk
import humanize
from apartcore import ApartCore
from gtktools import GridRowTenant
from partinfo import key_and_val
import settings
from util import *

FINISHED_JOB_COLUMNS = 3
RERUN_TEXT = 'Rerun'
FORGET_TEXT = 'Clear'
DELETE_TEXT = 'Delete'
DURATION_KEY = 'Runtime'


class RevealState(Enum):
    REVEALED = auto()
    HIDDEN = auto()

    @classmethod
    def default(cls) -> 'RevealState':
        return cls.HIDDEN


class FinishedClone:
    def __init__(self, final_message: Dict,
                 progress_view: 'ProgressAndHistoryView',
                 core: ApartCore,
                 icon_name: str,
                 forget_on_rerun: bool = True):
        self.msg = final_message
        self.finish: datetime = self.msg['finish']
        self.core = core
        self.progress_view = progress_view
        self.tenant = None
        self.forget_on_rerun = forget_on_rerun
        self.extra_user_state: RevealState = None

        self.icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        self.title_label = Gtk.Label(self.purpose(), xalign=0)
        self.title_inner_box = Gtk.Box(hexpand=True)
        self.title_inner_box.add(self.icon)
        self.title_inner_box.add(self.title_label)
        self.title_inner_box.get_style_context().add_class('finished-job-title')
        self.title_inner_box.show_all()
        self.title_box = Gtk.EventBox(visible=True)
        self.title_box.add(self.title_inner_box)

        self.title_box.connect('button-press-event', self.on_row_click)

        self.finish_label = Gtk.Label('', halign=Gtk.Align.START, visible=True, hexpand=True)
        self.finish_label.get_style_context().add_class('finish-label')
        self.finish_label.get_style_context().add_class('dim-label')
        self.finish_box = Gtk.EventBox(visible=True)
        self.finish_box.add(self.finish_label)
        self.finish_box.connect('button-press-event', self.on_row_click)

        self.rerun_btn = Gtk.Button(RERUN_TEXT, halign=Gtk.Align.END, visible=True)
        self.rerun_btn.connect('clicked', self.rerun)
        self.forget_btn = Gtk.Button(FORGET_TEXT, halign=Gtk.Align.END, visible=True)
        self.forget_btn.connect('clicked', self.forget)
        self.buttons = Gtk.Box(visible=True)
        self.buttons.add(self.rerun_btn)
        self.buttons.add(self.forget_btn)
        self.buttons.get_style_context().add_class('job-buttons')

        self.extra = Gtk.Revealer(transition_duration=settings.animation_duration_ms(), visible=True)
        self.extra.set_reveal_child(RevealState.default() is RevealState.REVEALED)
        self.update()

    def purpose(self) -> str:
        return '{} -> {}'.format(rm_dev(self.msg['source']), extract_directory(self.msg['destination']))

    def similar_to(self, other: 'FinishedClone') -> bool:
        """:return True => other is similar enough for both not to need to appear in the history grid"""
        return type(self) == type(other) and self.purpose() == other.purpose()

    def remove_from_grid(self):
        if not self.tenant:
            raise Exception('Not added to a grid')
        self.tenant.evict()
        self.tenant = None

    def on_row_click(self, *args):
        self.toggle_reveal_extra()
        self.extra_user_state = RevealState.REVEALED if self.extra.get_reveal_child() else RevealState.HIDDEN

    def toggle_reveal_extra(self):
        revealed = self.extra.get_reveal_child()
        if revealed:
            self.extra.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        else:
            self.extra.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.extra.set_reveal_child(not revealed)

    def default_extra_reveal(self):
        """Return the extra reveal state to default or as user has indicated"""
        default = self.extra_user_state or RevealState.default()
        if default is RevealState.HIDDEN and self.extra.get_reveal_child() or \
           default is RevealState.REVEALED and not self.extra.get_reveal_child():
            self.toggle_reveal_extra()

    def reveal_extra(self):
        if not self.extra.get_reveal_child():
            self.toggle_reveal_extra()

    def update(self):
        finished_delta = datetime.now(timezone.utc) - self.finish
        if finished_delta < timedelta(minutes=1):
            finished_str = "just now"
        else:
            finished_str = humanize.naturaltime(finished_delta)

        self.finish_label.set_text(finished_str)

    def forget(self, button=None):
        self.progress_view.forget(self)

    def rerun(self, button=None):
        backup_dir = extract_directory(self.msg['destination'])
        backup_name = extract_name(self.msg['destination'])
        self.core.send('type: clone\nsource: {}\ndestination: {}\nname: {}'.format(self.msg['source'],
                                                                                   backup_dir,
                                                                                   backup_name))
        if self.forget_on_rerun:
            self.forget()


class FailedClone(FinishedClone):
    def __init__(self, final_message: Dict, progress_view: 'ProgressAndHistoryView', core: ApartCore):
        FinishedClone.__init__(self, final_message, progress_view, core, icon_name='dialog-error')

        self.fail_reason = key_and_val('Failed', self.msg['error'])
        self.duration = key_and_val(DURATION_KEY, str(round_to_second(self.msg['finish'] - self.msg['start'])))
        self.stats = Gtk.VBox()
        self.stats.add(self.fail_reason)
        self.stats.add(self.duration)
        self.stats.get_style_context().add_class('finished-job-stats')
        self.stats.show_all()
        self.extra.add(self.stats)

        self.update()

    def add_to_grid(self, grid: Gtk.Grid):
        if self.tenant:
            raise Exception('Already added to a grid')
        tenant = self.tenant = GridRowTenant(grid)
        base = 0
        if tenant.base_row > 0:
            tenant.attach(Gtk.Separator(visible=True, hexpand=True), width=FINISHED_JOB_COLUMNS)
            base += 1
        tenant.attach(self.title_box, top=base)
        tenant.attach(self.finish_box, top=base, left=1)
        tenant.attach(self.buttons, top=base, left=2)
        tenant.attach(self.extra, top=base+1, width=FINISHED_JOB_COLUMNS)


class SuccessfulClone(FinishedClone):
    def __init__(self, final_message: Dict, progress_view: 'ProgressAndHistoryView', core: ApartCore):
        FinishedClone.__init__(self, final_message, progress_view, core, icon_name='object-select-symbolic',
                               forget_on_rerun=False)
        self.duration = key_and_val(DURATION_KEY, str(round_to_second(self.msg['finish'] - self.msg['start'])))
        self.image_size = key_and_val('Image size', humanize.naturalsize(99999999999, binary=True))
        self.filename = key_and_val('Image file', extract_filename(self.msg['destination']))
        self.stats = Gtk.VBox()
        for stat in [self.filename, self.image_size, self.duration]:
            self.stats.add(stat)
        self.stats.get_style_context().add_class('finished-job-stats')
        self.stats.show_all()
        self.extra.add(self.stats)

    def add_to_grid(self, grid: Gtk.Grid):
        if self.tenant:
            raise Exception('Already added to a grid')
        tenant = self.tenant = GridRowTenant(grid)
        base = 0
        if tenant.base_row > 0:
            tenant.attach(Gtk.Separator(visible=True, hexpand=True), width=FINISHED_JOB_COLUMNS)
            base += 1
        tenant.attach(self.title_box, top=base)
        tenant.attach(self.finish_box, top=base, left=1)
        tenant.attach(self.buttons, top=base, left=2)
        tenant.attach(self.extra, top=base + 1, width=FINISHED_JOB_COLUMNS)

    def similar_to(self, other: FinishedClone) -> bool:
        """
        As successful clones indicate space being taken up on the file system, it should only be lost from the history 
        if another task overwrote the same file (which as it includes at to-minute timestamp should be rare)
        """
        return FinishedClone.similar_to(self, other) and self.msg['destination'] == other.msg['destination']
