from datetime import datetime, timezone
from typing import *
from gi.repository import Gtk
import humanize
from apartcore import ApartCore
from gtktools import GridRowTenant
from partinfo import key_and_val
from util import *

RUNNING_JOB_COLUMNS = 2


class RunningClone:
    def __init__(self, core: ApartCore, on_finish: Callable[[Dict], None]):
        """:param on_finish: called when run has finished, with the final message"""
        self.core = core
        self.on_finish = on_finish
        self.last_message: Dict = None
        self.fail_message: Dict = None
        self.tenant: GridRowTenant = None
        self.start: datetime = None

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
        self.last_message = msg
        self.progress_bar.set_fraction(msg['complete'])
        self.title.set_text('{} -> {}'.format(rm_dev(msg['source']), extract_directory(msg['destination'])))
        self.rate.value_label.set_text(msg.get('rate') or 'Initializing')
        if not self.start:
            self.start = msg['start'].replace(tzinfo=msg['start'].tzinfo or timezone.utc)
            self.update()
        if msg.get('finish'):
            self.finish()

    def update(self) -> bool:
        if self.fail_message or self.last_message.get('finish'):
            return False

        elapsed_str = str(round_to_second(datetime.now(timezone.utc) - self.start))
        self.elapsed.value_label.set_text(elapsed_str)
        self.update_remaining()
        return True

    def update_remaining(self):
        if self.last_message.get('estimatedFinish'):
            estimated_remaining = self.last_message['estimatedFinish'] - datetime.now(timezone.utc)
            if estimated_remaining < timedelta(seconds=5):
                estimated_remaining_str = 'a few seconds'
            else:
                estimated_remaining_str = humanize.naturaldelta(estimated_remaining)
            self.estimated_completion.value_label.set_text(estimated_remaining_str)
            self.estimated_completion.show_all()

    def cancel(self, b):
        self.core.send('type: cancel-clone\nid: {}'.format(self.last_message['id']))

    def handle_fail_message(self, msg: Dict):
        self.fail_message = msg
        self.finish()

    def finish(self):
        self.on_finish(self.fail_message or self.last_message)
