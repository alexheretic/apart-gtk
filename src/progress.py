from typing import *
import gi
from apartcore import ApartCore, MessageListener
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk, Gdk


class ProgressView(Gtk.Stack):
    def __init__(self, core: ApartCore):
        Gtk.Stack.__init__(self)
        self.core = core

        self.nothing_label = Gtk.Label('Nothing in progress', xalign=0.5, vexpand=True)
        self.nothing_label.get_style_context().add_class('dim-label')
        self.add(self.nothing_label)

        self.listener = MessageListener(message_predicate=lambda m: m['type'] == 'clone',
                                        on_message=lambda m: GLib.idle_add(self.on_clone_message, m))
        self.listener.listen_to(core)

        self.fail_listener = MessageListener(message_predicate=lambda m: m['type'] == 'clone-failed',
                                             on_message=lambda m: GLib.idle_add(self.on_clone_fail_message, m))
        self.fail_listener.listen_to(core)

        ## TODO clone-failed message

        self.jobs: Dict[str, Job] = {}
        self.job_progress = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL,
                                     row_spacing=6,
                                     column_spacing=6)
        self.job_progress.rows_in_use = 0
        self.job_progress.get_style_context().add_class('jobs')
        self.add(self.job_progress)
        self.show_all()

    def on_clone_message(self, msg: Dict):
        job = self.jobs.get(msg['id'])
        if not job:
            job = Job(self.core)
            self.jobs[msg['id']] = job
            job.add_to_grid(self.job_progress)
        job.handle_message(msg)
        self.update_view()

    def on_clone_fail_message(self, msg: Dict):
        job = self.jobs.get(msg['id'])
        if not job:
            job = Job(self.core)
            self.jobs[msg['id']] = job
            job.add_to_grid(self.job_progress)
        job.handle_fail_message(msg)
        self.update_view()

    def update_view(self):
        if self.jobs:
            self.set_visible_child(self.job_progress)
        else:
            self.set_visible_child(self.nothing_label)


class Job:
    def __init__(self, core: ApartCore):
        self.core = core
        self.last_message = None
        self.fail_message = None

        self.title = Gtk.Label('blah -> /somewhere/something.apt.etc', xalign=0, visible=True)
        self.title.get_style_context().add_class('job-title')

        self.progress_bar = Gtk.ProgressBar(hexpand=True, visible=True)

        self.cancel_btn = Gtk.Button('Cancel', visible=True)
        self.cancel_btn.get_style_context().add_class('job-cancel-btn')
        self.cancel_btn.connect('clicked', self.cancel)

    def add_to_grid(self, grid: Gtk.Grid):
        if grid.rows_in_use > 0:
            grid.attach(Gtk.Separator(visible=True), left=0, top=grid.rows_in_use, height=1, width=2)
            grid.rows_in_use += 1

        row = grid.rows_in_use
        grid.attach(self.title, left=0, top=row, height=1, width=1)
        grid.attach(self.cancel_btn, left=1, top=row, height=1, width=1)
        grid.attach(self.progress_bar, left=0, top=row+1, height=1, width=2)
        grid.rows_in_use += 2

    def handle_message(self, msg: Dict):
        self.last_message = msg
        self.progress_bar.set_fraction(msg['complete'])
        self.title.set_text('{} -> {}'.format(msg['source'], msg['destination']))
        if msg.get('finish'):
            pass

    def cancel(self, b):
        self.core.send('type: cancel-clone\nid: {}'.format(self.last_message['id']))

    def handle_fail_message(self, msg: Dict):
        self.fail_message = msg
        self.progress_bar.set_text(msg['error'])
        self.progress_bar.set_show_text(True)
        self.progress_bar.get_style_context().add_class('failed')
        self.cancel_btn.hide()
