from datetime import timedelta, datetime, tzinfo, timezone
import re
from typing import *
import humanize
from apartcore import ApartCore, MessageListener
from gtktools import GridRowTenant, rows
from partinfo import key_and_val
from gi.repository import GLib, Gtk

import settings


class ProgressAndHistoryView(Gtk.Stack):
    def __init__(self, core: ApartCore):
        Gtk.Stack.__init__(self)
        self.core = core
        self.get_style_context().add_class('progress-view')

        self.nothing_label = Gtk.Label('Select a partition to clone', xalign=0.5, vexpand=True)
        self.nothing_label.get_style_context().add_class('dim-label')
        self.add(self.nothing_label)

        self.content = Gtk.VBox(valign=Gtk.Align.START)
        self.add(self.content)

        self.running_jobs_label = Gtk.Label('Running', halign=Gtk.Align.START)
        self.running_jobs_label.get_style_context().add_class('section-title')
        self.content.add(self.running_jobs_label)

        self.running_jobs: Dict[str, RunningClone] = {}
        self.running_jobs_grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL,
                                          column_spacing=6,
                                          row_spacing=6)

        self.running_jobs_grid.get_style_context().add_class('jobs')
        self.content.add(self.running_jobs_grid)

        self.finished_jobs: Dict[str, SuccessfulClone] = {}
        self.finished_jobs_label = Gtk.Label('History', halign=Gtk.Align.START)
        self.finished_jobs_label.get_style_context().add_class('section-title')
        self.content.add(self.finished_jobs_label)

        self.finished_jobs_grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL,
                                           column_spacing=6,
                                           row_spacing=6)
        self.finished_jobs_grid.get_style_context().add_class('finished-jobs')
        self.content.add(self.finished_jobs_grid)

        self.show_all()
        print('visible ' + str(self.running_jobs_label.get_property('visible')))

        self.listener = MessageListener(message_predicate=lambda m: m['type'] == 'clone',
                                        on_message=lambda m: GLib.idle_add(self.on_clone_message, m),
                                        listen_to=core)
        self.fail_listener = MessageListener(message_predicate=lambda m: m['type'] == 'clone-failed',
                                             on_message=lambda m: GLib.idle_add(self.on_clone_fail_message, m),
                                             listen_to=core)

        GLib.timeout_add(interval=1000, function=self.update_jobs)
        self.connect('destroy', self.save_history)
        GLib.idle_add(self.read_history)

    def read_history(self):
        for historic_job_msg in settings.read_history():
            if historic_job_msg.get('error'):
                job = FailedClone(historic_job_msg, progress_view=self, core=self.core)
            else:
                job = SuccessfulClone(historic_job_msg, progress_view=self, core=self.core)
            self.finished_jobs[historic_job_msg['id']] = job

        for job in sorted(self.finished_jobs.values(),
                          key=lambda j: j.finish,
                          reverse=True):
            job.add_to_grid(self.finished_jobs_grid)
        self.update_view()

    def on_clone_message(self, msg: Dict):
        job = self.running_jobs.get(msg['id'])
        if not job:
            job = RunningClone(self.core, on_finish=self.on_job_finish)
            self.running_jobs[msg['id']] = job
            job.add_to_grid(self.running_jobs_grid)
        job.handle_message(msg)
        self.update_view()

    def on_clone_fail_message(self, msg: Dict):
        job = self.running_jobs.get(msg['id'])
        if not job:
            job = RunningClone(self.core, on_finish=self.on_job_finish)
            self.running_jobs[msg['id']] = job
            job.add_to_grid(self.running_jobs_grid)
        job.handle_fail_message(msg)
        self.update_view()

    def update_view(self):
        if self.running_jobs or self.finished_jobs:
            self.set_visible_child(self.content)
        else:
            self.set_visible_child(self.nothing_label)
        self.finished_jobs_label.set_visible(not not self.finished_jobs)
        self.finished_jobs_grid.set_visible(not not self.finished_jobs)
        self.running_jobs_label.set_visible(not not self.running_jobs)
        self.running_jobs_grid.set_visible(not not self.running_jobs)

    def update_jobs(self) -> bool:
        for job in self.running_jobs.values():
            job.update()
        for job in self.finished_jobs.values():
            job.update()
        return True

    def on_job_finish(self, final_msg: Dict):
        job_id = final_msg['id']
        job = self.running_jobs[job_id]
        job.remove_from_grid()
        del self.running_jobs[job_id]
        if final_msg.get('error'):
            job = FailedClone(final_msg, progress_view=self, core=self.core)
        else:
            job = SuccessfulClone(final_msg, progress_view=self, core=self.core)

        # remove all and re-add for ordering
        to_remove = []
        for id, existing_job in self.finished_jobs.items():
            existing_job.remove_from_grid()
            if existing_job.similar_to(job):
                to_remove.append(id)

        for id in to_remove:
            del self.finished_jobs[id]

        self.finished_jobs[job_id] = job
        for job in sorted(self.finished_jobs.values(),
                          key=lambda j: j.finish,
                          reverse=True):
            job.add_to_grid(self.finished_jobs_grid)

        self.update_view()

    def forget(self, job: 'FinishedClone'):
        del self.finished_jobs[job.msg['id']]
        job.remove_from_grid()
        self.update_view()

    def save_history(self, arg=None):
        history = list(map(lambda j: j.msg, self.finished_jobs.values()))
        settings.write_history(history)


filename_re = re.compile(r"/[^/]+$")
name_re = re.compile(r"^.*/(([^/]+)-\d{4,}-\d\d-\d\dT\d{4}\.apt\..+\..+)$")
source_re = re.compile(r"^/dev/")
finished_job_col_span = 4
running_job_col_span = 2
RERUN_TEXT = 'Rerun'
FORGET_TEXT = 'Clear'
DELETE_TEXT = 'Delete'


def extract_directory(path: str) -> str:
    return re.sub(filename_re, '', path)


def extract_filename(path: str) -> str:
    m = re.fullmatch(name_re, path)
    return m.group(1)


def extract_name(path: str) -> str:
    m = re.fullmatch(name_re, path)
    return m.group(2)


def rm_dev(source: str) -> str:
    return re.sub(source_re, '', source)


def round_to_second(delta: timedelta) -> timedelta:
    micros = delta.microseconds
    truncated = delta - timedelta(microseconds=micros)
    if micros >= 500000:  # round half up
        return truncated + timedelta(seconds=1)
    return truncated


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
            tenant.attach(Gtk.Separator(visible=True), width=running_job_col_span)
            tenant_top += 1

        tenant.attach(self.title, top=tenant_top)
        tenant.attach(self.cancel_btn, left=1, top=tenant_top)
        tenant.attach(self.progress_bar, top=tenant_top + 1, width=running_job_col_span)
        box = Gtk.Box(visible=True)
        box.get_style_context().add_class('job-stats')
        box.add(self.elapsed)
        box.add(self.rate)
        box.add(self.estimated_completion)
        tenant.attach(box, top=tenant_top + 2, width=running_job_col_span)

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


class FinishedClone:
    def __init__(self, final_message: Dict,
                 progress_view: ProgressAndHistoryView,
                 core: ApartCore,
                 forget_on_rerun: bool = True):
        self.msg = final_message
        self.finish: datetime = self.msg['finish']
        self.core = core
        self.progress_view = progress_view
        self.tenant = None
        self.forget_on_rerun = forget_on_rerun

        self.finish_label = Gtk.Label('', halign=Gtk.Align.START, visible=True, hexpand=True)
        self.finish_label.get_style_context().add_class('finish-label')
        self.finish_label.get_style_context().add_class('dim-label')

        self.rerun_btn = Gtk.Button(RERUN_TEXT, halign=Gtk.Align.END, visible=True)
        self.rerun_btn.connect('clicked', self.rerun)
        self.forget_btn = Gtk.Button(FORGET_TEXT, halign=Gtk.Align.END, visible=True)
        self.forget_btn.connect('clicked', self.forget)
        self.buttons = Gtk.Box(visible=True)
        self.buttons.add(self.rerun_btn)
        self.buttons.add(self.forget_btn)
        self.buttons.get_style_context().add_class('job-buttons')
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

    def update(self):
        finished_delta = datetime.now(timezone.utc) - self.finish
        if finished_delta < timedelta(minutes=1):
            finished_str = "just now"
        else:
            finished_str = humanize.naturaltime(finished_delta)

        self.finish_label.set_text(finished_str)

    def forget(self, arg=None):
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
    def __init__(self, final_message: Dict, progress_view: ProgressAndHistoryView, core: ApartCore):
        FinishedClone.__init__(self, final_message, progress_view, core)
        # dialog-error / action-unavailable
        self.icon = Gtk.Image.new_from_icon_name('dialog-error', Gtk.IconSize.LARGE_TOOLBAR)
        self.title_label = Gtk.Label(self.purpose(), xalign=0)
        self.title = Gtk.Box(hexpand=True)
        self.title.add(self.icon)
        self.title.add(self.title_label)
        self.title.get_style_context().add_class('finished-job-title')
        self.title.show_all()

        self.description = Gtk.Label(self.msg['error'], halign=Gtk.Align.START, visible=True, hexpand=True)
        self.description.get_style_context().add_class('error')
        self.description.get_style_context().add_class('dim-label')

        self.update()

    def add_to_grid(self, grid: Gtk.Grid):
        if self.tenant:
            raise Exception('Already added to a grid')
        tenant = self.tenant = GridRowTenant(grid)
        base = 0
        if tenant.base_row > 0:
            tenant.attach(Gtk.Separator(visible=True, hexpand=True), width=finished_job_col_span)
            base += 1
        tenant.attach(self.title, top=base)
        tenant.attach(self.description, top=base, left=1)
        tenant.attach(self.finish_label, top=base, left=2)
        tenant.attach(self.buttons, top=base, left=3)


class SuccessfulClone(FinishedClone):
    def __init__(self, final_message: Dict, progress_view: ProgressAndHistoryView, core: ApartCore):
        FinishedClone.__init__(self, final_message, progress_view, core, forget_on_rerun=False)
        self.icon = Gtk.Image.new_from_icon_name('object-select-symbolic', Gtk.IconSize.LARGE_TOOLBAR)
        self.title_label = Gtk.Label(self.purpose(), xalign=0)
        self.title = Gtk.Box(hexpand=True)
        self.title.add(self.icon)
        self.title.add(self.title_label)
        self.title.get_style_context().add_class('finished-job-title')
        self.title.show_all()

        self.duration = key_and_val('Completed in', str(round_to_second(self.msg['finish'] - self.msg['start'])))
        self.image_size = key_and_val('Image size', humanize.naturalsize(99999999999, binary=True))
        self.filename = key_and_val('Image file', extract_filename(self.msg['destination']))
        self.stats = Gtk.VBox()
        for stat in [self.filename, self.image_size, self.duration]:
            self.stats.add(stat)
        self.stats.get_style_context().add_class('finished-job-stats')
        self.stats.show_all()

    def add_to_grid(self, grid: Gtk.Grid):
        if self.tenant:
            raise Exception('Already added to a grid')
        tenant = self.tenant = GridRowTenant(grid)
        base = 0
        if tenant.base_row > 0:
            tenant.attach(Gtk.Separator(visible=True, hexpand=True), width=finished_job_col_span)
            base += 1
        tenant.attach(self.title, top=base)
        tenant.attach(self.finish_label, top=base, left=1)
        tenant.attach(self.buttons, top=base, left=2)
        tenant.attach(self.stats, top=base+1, width=finished_job_col_span)

    def similar_to(self, other: FinishedClone) -> bool:
        """
        As successful clones indicate space being taken up on the file system, it should only be lost from the history 
        if another task overwrote the same file (which as it includes at to-minute timestamp should be rare)
        """
        return FinishedClone.similar_to(self, other) and self.msg['destination'] == other.msg['destination']
