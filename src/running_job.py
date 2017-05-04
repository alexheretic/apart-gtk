from gi.repository import Gtk
import humanize
from apartcore import ApartCore
from gtktools import GridRowTenant
from partinfo import key_and_val
from util import *

RUNNING_JOB_COLUMNS = 2


class RunningJob:
    def __init__(self, core: ApartCore, on_finish: Callable[[Dict], None]):
        """:param on_finish: called when job has received it's final message, with the this message as an arg"""
        self.core = core
        self.on_finish = on_finish
        self.last_message: Dict = None
        self.fail_message: Dict = None
        self.tenant: GridRowTenant = None
        self.start: datetime = None
        self.cancelling = False

        # row 1
        self.title = Gtk.Label('', xalign=0, visible=True)
        self.title.get_style_context().add_class('job-title')
        self.cancel_btn = Gtk.Button('Cancel', visible=True, halign=Gtk.Align.END)
        self.cancel_btn.get_style_context().add_class('job-cancel-btn')
        self.cancel_btn.connect('clicked', self.cancel)

        # row 2
        self.rate = key_and_val('Rate', '')
        self.rate.show_all()
        self.elapsed = key_and_val('Elapsed', '')
        self.elapsed.show_all()
        self.estimated_completion = key_and_val('Remaining', '')

        # row 3
        self.progress_bar = Gtk.ProgressBar(hexpand=True, visible=True)

    def add_to_grid(self, grid: Gtk.Grid):
        if self.tenant:
            raise Exception('Already added to a grid')

        tenant = self.tenant = GridRowTenant(grid)
        tenant_top = 0
        if tenant.base_row > 0:
            tenant.attach(Gtk.Separator(visible=True), width=RUNNING_JOB_COLUMNS)
            tenant_top += 1

        tenant.attach(self.title, top=tenant_top)
        tenant.attach(self.cancel_btn, left=1, top=tenant_top)
        tenant.attach(self.progress_bar, top=tenant_top + 1, width=RUNNING_JOB_COLUMNS)
        box = Gtk.Box(visible=True)
        box.get_style_context().add_class('job-stats')
        box.add(self.elapsed)
        box.add(self.rate)
        box.add(self.estimated_completion)
        tenant.attach(box, top=tenant_top + 2, width=RUNNING_JOB_COLUMNS)

    def remove_from_grid(self):
        if not self.tenant:
            raise Exception('Not added to a grid')
        self.tenant.evict()
        self.tenant = None

    def handle_message(self, msg: Dict):
        if msg['type'] in ['clone', 'restore']:
            self.last_message = msg
            self.progress_bar.set_fraction(msg['complete'])
            if not self.start:
                self.start = msg['start'].replace(tzinfo=msg['start'].tzinfo or timezone.utc)
                self.update()
            if msg.get('finish'):
                self.finish()
            else:
                self.rate.value_label.set_text(msg.get('rate') or 'Initializing')

        elif msg['type'] in ['clone-failed', 'restore-failed']:
            self.fail_message = msg
            self.finish()

    def update(self) -> bool:
        if self.fail_message or self.last_message.get('finish'):
            return False

        elapsed_str = str(round_to_second(datetime.now(timezone.utc) - self.start))
        self.elapsed.value_label.set_text(elapsed_str)
        if not self.cancelling:
            self.update_remaining()
        return True

    def update_remaining(self):
        if self.last_message.get('estimated_finish'):
            estimated_remaining = self.last_message['estimated_finish'] - datetime.now(timezone.utc)
            if estimated_remaining < timedelta(seconds=5):
                estimated_remaining_str = 'a few seconds'
            else:
                estimated_remaining_str = humanize.naturaldelta(estimated_remaining)
            self.estimated_completion.value_label.set_text(estimated_remaining_str)
            self.estimated_completion.show_all()

    def cancel(self, *args):
        self.cancel_btn.set_sensitive(False)
        self.cancel_btn.set_tooltip_text("Cancelling")
        self.cancelling = True

    def finish(self):
        self.on_finish(self.fail_message or self.last_message)

    def finished(self) -> bool:
        return bool(self.fail_message or self.last_message and self.last_message.get('finish'))


class RunningClone(RunningJob):
    """Display representation of a running partition clone"""
    def __init__(self, core: ApartCore, on_finish: Callable[[Dict], None]):
        RunningJob.__init__(self, core, on_finish)

    def cancel(self, *args):
        RunningJob.cancel(self, *args)
        self.core.send('type: cancel-clone\nid: {}'.format(self.last_message['id']))

    def handle_message(self, msg: Dict):
        RunningJob.handle_message(self, msg)
        if not self.finished():
            self.title.set_text('{} -> {}'.format(rm_dev(self.last_message['source']),
                                                  extract_directory(self.last_message['destination'])))


class RunningRestore(RunningJob):
    """Display representation of a running partition restore"""
    def __init__(self, core: ApartCore, on_finish: Callable[[Dict], None]):
        RunningJob.__init__(self, core, on_finish)

    def cancel(self, *args):
        RunningJob.cancel(self, *args)
        self.core.send('type: cancel-restore\nid: {}'.format(self.last_message['id']))

    def handle_message(self, msg: Dict):
        RunningJob.handle_message(self, msg)
        if not self.finished():
            self.title.set_text('{} -> {}'.format(self.last_message['source'],
                                                  rm_dev(self.last_message['destination'])))


def create(msg: Dict, core: ApartCore, on_finish: Callable[[Dict], None]) -> RunningJob:
    msg_type = msg['type']
    if msg_type.startswith('clone'):
        return RunningClone(core, on_finish)
    elif msg_type.startswith('restore'):
        return RunningRestore(core, on_finish)
    raise Exception('Cannot create RunningJob from unknown type: ' + msg_type)
