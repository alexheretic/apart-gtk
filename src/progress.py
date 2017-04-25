from datetime import timedelta, datetime
import re
from typing import *
import gi
import humanize

from apartcore import ApartCore, MessageListener
from partinfo import key_and_val

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk


class ProgressView(Gtk.Stack):
    def __init__(self, core: ApartCore):
        Gtk.Stack.__init__(self)
        self.core = core
        self.get_style_context().add_class('progress-view')

        self.nothing_label = Gtk.Label('Select a partition to clone', xalign=0.5, vexpand=True)
        self.nothing_label.get_style_context().add_class('dim-label')
        self.add(self.nothing_label)

        self.content = Gtk.VBox(valign=Gtk.Align.START)
        self.add(self.content)

        self.running_jobs_label = Gtk.Label('In Progress', halign=Gtk.Align.START)
        self.running_jobs_label.get_style_context().add_class('section-title')
        self.content.add(self.running_jobs_label)

        self.running_jobs: Dict[str, RunningClone] = {}
        self.running_jobs_grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL,
                                          column_spacing=6,
                                          row_spacing=6)
        def c(a1, a2):
            print(a1)
            print(a2.name)

        self.running_jobs_grid.rows_in_use = 0
        self.running_jobs_grid.connect('notify::rows_in_use', c) # TODO
        self.running_jobs_grid.get_style_context().add_class('jobs')
        self.content.add(self.running_jobs_grid)

        self.finished_jobs: Dict[str, FinishedClone] = {}
        self.finished_jobs_label = Gtk.Label('Finished', halign=Gtk.Align.START)
        self.finished_jobs_label.get_style_context().add_class('section-title')
        self.content.add(self.finished_jobs_label)

        self.finished_jobs_grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL,
                                           column_spacing=6,
                                           row_spacing=6)
        self.finished_jobs_grid.rows_in_use = 0
        self.finished_jobs_grid.get_style_context().add_class('finished-jobs')
        self.content.add(self.finished_jobs_grid)

        self.show_all()

        self.listener = MessageListener(message_predicate=lambda m: m['type'] == 'clone',
                                        on_message=lambda m: GLib.idle_add(self.on_clone_message, m),
                                        listen_to=core)
        self.fail_listener = MessageListener(message_predicate=lambda m: m['type'] == 'clone-failed',
                                             on_message=lambda m: GLib.idle_add(self.on_clone_fail_message, m),
                                             listen_to=core)

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
            if self.finished_jobs:
                self.finished_jobs_label.show()
            else:
                self.finished_jobs_label.hide()
        else:
            self.set_visible_child(self.nothing_label)

    def on_job_finish(self, final_msg: Dict):
        job_id = final_msg['id']
        job = self.running_jobs[job_id]
        job.remove_from_grid(self.running_jobs_grid)
        del self.running_jobs[job_id]
        if final_msg.get('error'):
            job = FailedClone(final_msg)
        else:
            job = FinishedClone(final_msg)
        self.finished_jobs[job_id] = job
        job.add_to_grid(self.finished_jobs_grid)


filename_re = re.compile(r"/[^/]+$")
source_re = re.compile(r"^/dev/")


def rm_filename(path: str) -> str:
    return re.sub(filename_re, '', path)


def rm_dev(source: str) -> str:
    return re.sub(source_re, '', source)


class RunningClone:
    def __init__(self, core: ApartCore, on_finish: Callable[[Dict], None]):
        """:param on_finish: called when run has finished, with the final message"""
        self.core = core
        self.on_finish = on_finish
        self.last_message = None
        self.fail_message = None

        # row 1
        self.title = Gtk.Label('', xalign=0, visible=True)
        self.title.get_style_context().add_class('job-title')

        self.start = None

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
        if grid.rows_in_use > 0:
            grid.attach(Gtk.Separator(visible=True), left=0, top=grid.rows_in_use, height=1, width=3)
            grid.rows_in_use += 1

        row = grid.rows_in_use
        grid.attach(self.title, left=0, top=row, height=1, width=1)
        grid.attach(self.cancel_btn, left=1, top=row, height=1, width=1)
        grid.attach(self.progress_bar, left=0, top=row+1, height=1, width=2)

        box = Gtk.Box(visible=True)
        box.get_style_context().add_class('job-stats')
        box.add(self.elapsed)
        box.add(self.rate)
        box.add(self.estimated_completion)
        grid.attach(box, left=0, top=row+2, height=1, width=2)
        grid.rows_in_use += 3

    def remove_from_grid(self, grid: Gtk.Grid):
        grid_row = None
        for row in range(grid.rows_in_use):
            if self.title is grid.get_child_at(left=0, top=row):
                grid_row = row
                break
        if grid_row is None:
            raise Exception('remove_from_grid failed to find self.title')
        grid.remove_row(grid_row + 2)
        grid.remove_row(grid_row + 1)
        grid.remove_row(grid_row)
        grid.rows_in_use -= 3
        if grid_row > 0:
            # rm separator above
            grid.remove_row(grid_row - 1)
            grid.rows_in_use -= 1
        elif grid.rows_in_use > 0:
            # rm separator below
            grid.remove_row(0)
            grid.rows_in_use -= 1

    def handle_message(self, msg: Dict):
        self.last_message = msg
        self.progress_bar.set_fraction(msg['complete'])
        self.title.set_text('{} -> {}'.format(rm_dev(msg['source']), rm_filename(msg['destination'])))
        self.rate.value_label.set_text(msg.get('rate') or 'Initializing')
        if not self.start:
            self.start = msg['start']
            self.update_elapsed()
            GLib.timeout_add(interval=500, function=self.update_elapsed)
        if msg.get('finish'):
            self.finish()

    def update_elapsed(self) -> bool:
        if self.fail_message or self.last_message.get('finish'):
            return False

        def without_microseconds(delta: timedelta):
            return delta - timedelta(microseconds=delta.microseconds)

        elapsed_str = str(without_microseconds(datetime.utcnow() - self.start))
        self.elapsed.value_label.set_text(elapsed_str)
        self.update_remaining()
        return True

    def update_remaining(self):
        if self.last_message.get('estimatedFinish'):
            estimated_remaining = self.last_message['estimatedFinish'] - datetime.utcnow()
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
    def __init__(self, final_message: Dict):
        self.msg = final_message
        title = '{} -> {}'.format(rm_dev(self.msg['source']), rm_filename(self.msg['destination']))

        self.icon = Gtk.Image.new_from_icon_name('object-select-symbolic', Gtk.IconSize.LARGE_TOOLBAR)
        self.title_label = Gtk.Label(title, xalign=0)
        self.title = Gtk.Box()
        self.title.add(self.icon)
        self.title.add(self.title_label)
        self.title.get_style_context().add_class('finished-job-title')
        self.title.show_all()

    def add_to_grid(self, grid: Gtk.Grid):
        if grid.rows_in_use > 0:
            grid.attach(Gtk.Separator(visible=True, hexpand=True), left=0, top=grid.rows_in_use, height=1, width=3)
            grid.rows_in_use += 1

        row = grid.rows_in_use
        grid.attach(self.title, left=0, top=row, height=1, width=1)
        grid.rows_in_use += 1

    def remove_from_grid(self, grid: Gtk.Grid):
        grid_row = None
        for row in range(grid.rows_in_use):
            if self.title is grid.get_child_at(left=0, top=row):
                grid_row = row
                break
        if grid_row is None:
            raise Exception('remove_from_grid failed to find self.title')
        # grid.remove_row(grid_row + 2)
        # grid.remove_row(grid_row + 1)
        grid.remove_row(grid_row)
        grid.rows_in_use -= 1
        if grid_row > 0:
            # rm separator above
            grid.remove_row(grid_row - 1)
            grid.rows_in_use -= 1
        elif grid.rows_in_use > 0:
            # rm separator below
            grid.remove_row(0)
            grid.rows_in_use -= 1


class FailedClone:
    def __init__(self, final_message: Dict):
        self.msg = final_message
        title = '{} -> {}'.format(rm_dev(self.msg['source']), rm_filename(self.msg['destination']))
        # dialog-error / action-unavailable
        self.icon = Gtk.Image.new_from_icon_name('dialog-error', Gtk.IconSize.LARGE_TOOLBAR)
        self.icon.show()
        self.title = Gtk.Label(title, xalign=0, visible=True)

    def add_to_grid(self, grid: Gtk.Grid):
        if grid.rows_in_use > 0:
            grid.attach(Gtk.Separator(visible=True, hexpand=True), left=0, top=grid.rows_in_use, height=1, width=3)
            grid.rows_in_use += 1

        row = grid.rows_in_use
        grid.attach(self.icon, left=0, top=row, height=1, width=1)
        grid.attach(self.title, left=1, top=row, height=1, width=1)
        grid.rows_in_use += 1

    def remove_from_grid(self, grid: Gtk.Grid):
        grid_row = None
        for row in range(grid.rows_in_use):
            if self.icon is grid.get_child_at(left=0, top=row):
                grid_row = row
                break
        if grid_row is None:
            raise Exception('remove_from_grid failed to find self.title')
        # grid.remove_row(grid_row + 2)
        # grid.remove_row(grid_row + 1)
        grid.remove_row(grid_row)
        grid.rows_in_use -= 1
        if grid_row > 0:
            # rm separator above
            grid.remove_row(grid_row - 1)
            grid.rows_in_use -= 1
        elif grid.rows_in_use > 0:
            # rm separator below
            grid.remove_row(0)
            grid.rows_in_use -= 1