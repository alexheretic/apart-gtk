from enum import Enum
from gi.repository import Gtk, GLib
import humanize
from apartcore import ApartCore, MessageListener
from dialog import OkCancelDialog, OkDialog
from gtktools import GridRowTenant
from partinfo import key_and_val
import settings
from util import *

FINISHED_JOB_COLUMNS = 3
FORGET_TEXT = 'Clear'
FORGET_TIP = 'Remove from history'
RERUN_TIP = 'Run again'
DELETE_TIP = 'Delete image file'
DURATION_KEY = 'Runtime'


class RevealState(Enum):
    REVEALED = 1
    HIDDEN = 2

    @classmethod
    def default(cls) -> 'RevealState':
        return cls.HIDDEN


class FinishedJob:
    def __init__(self, final_message: Dict,
                 progress_view: 'ProgressAndHistoryView',
                 core: ApartCore,
                 icon_name: str,
                 forget_on_rerun: bool = True):
        self.msg = final_message
        self.finish = self.msg['finish']  # datetime
        self.core = core
        self.progress_view = progress_view
        self.tenant = None
        self.forget_on_rerun = forget_on_rerun
        self.extra_user_state = None  # RevealState

        self.source_available = True  # source (ie /dev/sdX) is available currently

        self.duration = key_and_val(DURATION_KEY, str(round_to_second(self.msg['finish'] - self.msg['start'])))

        self.icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        title_source = Gtk.Label('', xalign=0)
        title_name = Gtk.Label('', xalign=0)
        title_destination = Gtk.Label('', xalign=0)

        if final_message['type'].startswith('clone'):
            title_source.set_text(rm_dev(self.msg['source']))
            title_name.set_text(extract_name(self.msg['destination']))
            title_name.get_style_context().add_class("job-name")
            title_destination.set_text('-> ' + extract_directory(self.msg['destination']))
        else:
            title_source.set_text(extract_filename(self.msg['source']))
            title_destination.set_text(' -> ' + rm_dev(self.msg['destination']))

        self.title_inner_box = Gtk.Box(hexpand=True)
        self.title_inner_box.add(self.icon)
        self.title_inner_box.add(title_source)
        self.title_inner_box.add(title_name)
        self.title_inner_box.add(title_destination)
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

        self.rerun_btn = Gtk.Button.new_from_icon_name('view-refresh-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        self.rerun_btn.set_tooltip_text(RERUN_TIP)
        self.rerun_btn.connect('clicked', self.rerun)
        self.forget_btn = Gtk.Button(FORGET_TEXT)
        self.forget_btn.set_tooltip_text(FORGET_TIP)
        self.forget_btn.connect('clicked', self.forget)
        self.buttons = Gtk.Box(visible=True, halign=Gtk.Align.END)
        self.buttons.add(self.rerun_btn)
        self.buttons.add(self.forget_btn)
        self.buttons.get_style_context().add_class('job-buttons')
        self.buttons.show_all()

        self.extra = Gtk.Revealer(transition_duration=settings.animation_duration_ms(), visible=True)
        self.extra.set_reveal_child(RevealState.default() is RevealState.REVEALED)
        self.update()

    def purpose(self) -> str:
        return '{} -> {}'.format(rm_dev(self.msg['source']), extract_directory(self.msg['destination']))

    def similar_to(self, other: 'FinishedJob') -> bool:
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
        self.rerun_btn.set_sensitive(self.source_available)
        tooltip = RERUN_TIP if self.source_available else rm_dev(self.msg['source']) + " not currently available"
        self.rerun_btn.set_tooltip_text(tooltip)


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

    def add_to_grid(self, grid: Gtk.Grid):
        raise Exception('abstract')

    def on_source_update(self, sources: Dict):
        source_part_name = rm_dev(self.msg['source'])
        for disk in sources:
            for part in disk['parts']:
                if part['name'] == source_part_name:
                    self.source_available = True
                    return

        self.source_available = False


class FailedClone(FinishedJob):
    def __init__(self, final_message: Dict, progress_view: 'ProgressAndHistoryView', core: ApartCore):
        FinishedJob.__init__(self, final_message, progress_view, core, icon_name='dialog-error')
        self.fail_reason = key_and_val('Failed', self.msg['error'])
        self.stats = Gtk.VBox()
        self.stats.add(self.fail_reason)
        self.stats.add(self.duration)
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
        tenant.attach(self.extra, top=base+1, width=FINISHED_JOB_COLUMNS)

        grid.get_toplevel().register_interest_in_sources(on_update_callback=self.on_source_update)


class SuccessfulClone(FinishedJob):
    def __init__(self, final_message: Dict, progress_view: 'ProgressAndHistoryView', core: ApartCore):
        FinishedJob.__init__(self, final_message, progress_view, core, icon_name='object-select-symbolic',
                             forget_on_rerun=False)
        self.image_size = key_and_val('Image size', humanize.naturalsize(self.msg['image_size'], binary=True))
        self.filename = key_and_val('Image file', extract_filename(self.msg['destination']))
        self.stats = Gtk.VBox()
        for stat in [self.filename, self.image_size, self.duration]:
            self.stats.add(stat)
        self.stats.get_style_context().add_class('finished-job-stats')
        self.stats.show_all()
        self.extra.add(self.stats)
        self.delete_image_btn = Gtk.Button.new_from_icon_name('user-trash-full-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        self.delete_image_btn.set_tooltip_text(DELETE_TIP)
        self.delete_image_btn.show_all()
        self.delete_image_btn.connect('clicked', self.delete_image)
        self.buttons.add(self.delete_image_btn)
        self.buttons.reorder_child(self.delete_image_btn, 0)

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

        grid.get_toplevel().register_interest_in_sources(on_update_callback=self.on_source_update)

    def similar_to(self, other: FinishedJob) -> bool:
        """
        As successful clones indicate space being taken up on the file system, it should only be lost from the history
        if another task overwrote the same file (which as it includes at to-minute timestamp should be rare)
        """
        return FinishedJob.similar_to(self, other) and self.msg['destination'] == other.msg['destination']

    def delete_image(self, arg=None):
        filename = self.msg['destination']
        dialog = OkCancelDialog(self.delete_image_btn.get_toplevel(),
                                header='Delete image file',
                                text="Delete {}?".format(filename),
                                message_type=Gtk.MessageType.WARNING)
        user_response = dialog.run()
        dialog.destroy()
        if user_response != Gtk.ResponseType.OK:
            return

        for btn in self.buttons.get_children():
            btn.set_sensitive(False)
            btn.set_tooltip_text('Deleting...')

        def on_response(msg: Dict):
            if msg['type'] == 'deleted-clone':
                self.forget()
            else:  # failed
                err_dialog = OkDialog(self.delete_image_btn.get_toplevel(),
                                      header='Delete failed',
                                      text='Could not delete {}: {}'.format(filename, msg['error']),
                                      message_type=Gtk.MessageType.ERROR)
                err_dialog.run()
                err_dialog.destroy()
                for btn in self.buttons.get_children():
                    btn.set_sensitive(True)
                self.forget_btn.set_tooltip_text(FORGET_TIP)
                self.rerun_btn.set_tooltip_text(RERUN_TIP)
                self.delete_image_btn.set_tooltip_text(DELETE_TIP)

        MessageListener(message_predicate=lambda m: m['type'] in ['deleted-clone', 'delete-clone-failed'] and
                                                    m['file'] == filename,
                        on_message=lambda m: GLib.idle_add(on_response, m),
                        listen_to=self.core,
                        one_time=True)

        self.core.send('type: delete-clone\nfile: ' + filename)


class FailedRestore(FinishedJob):
    def __init__(self, final_message: Dict, progress_view: 'ProgressAndHistoryView', core: ApartCore):
        FinishedJob.__init__(self, final_message, progress_view, core, icon_name='dialog-error')
        self.fail_reason = key_and_val('Failed', self.msg['error'])
        self.image_source = key_and_val('Restoring from', self.msg['source'])
        self.stats = Gtk.VBox()
        for stat in [self.fail_reason, self.image_source, self.duration]:
            self.stats.add(stat)
        self.stats.get_style_context().add_class('finished-job-stats')
        self.stats.show_all()
        self.extra.add(self.stats)
        # naive rerun is unsafe for restore jobs as /dev/abc1 may refer to different partition than when last run
        self.rerun_btn.destroy()

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

    def purpose(self) -> str:
        """Note: used for similarity"""
        return 'Restore {}'.format(rm_dev(self.msg['destination']))


class SuccessfulRestore(FinishedJob):
    def __init__(self, final_message: Dict, progress_view: 'ProgressAndHistoryView', core: ApartCore):
        FinishedJob.__init__(self, final_message, progress_view, core, icon_name='object-select-symbolic',
                             forget_on_rerun=False)
        self.stats = Gtk.VBox()
        self.image_source = key_and_val('Restored from', self.msg['source'])
        for stat in [self.image_source, self.duration]:
            self.stats.add(stat)
        self.stats.get_style_context().add_class('finished-job-stats')
        self.stats.show_all()
        self.extra.add(self.stats)
        # naive rerun is unsafe for restore jobs as /dev/abc1 may refer to different partition than when last run
        self.rerun_btn.destroy()

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

    def purpose(self) -> str:
        """Note: used for similarity"""
        return 'Restored {}'.format(rm_dev(self.msg['destination']))


def create(final_message: Dict, progress_view: 'ProgressAndHistoryView', core: ApartCore) -> FinishedJob:
    msg_type = final_message['type']
    if msg_type == 'clone':
        return SuccessfulClone(final_message, progress_view=progress_view, core=core)
    elif msg_type == 'clone-failed':
        return FailedClone(final_message, progress_view=progress_view, core=core)
    elif msg_type == 'restore':
        return SuccessfulRestore(final_message, progress_view=progress_view, core=core)
    elif msg_type == 'restore-failed':
        return FailedRestore(final_message, progress_view=progress_view, core=core)
    raise Exception('Unknown type: ' + msg_type)
