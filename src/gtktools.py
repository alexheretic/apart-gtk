from typing import *
from gi.repository import Gtk


def rows(grid: Gtk.Grid) -> int:
    return max(map(lambda child: grid.child_get_property(child, 'top-attach'), grid.get_children()), default=-1) + 1


class GridRowTenant:
    """Tool for managing one-time adding and later removing of exclusive owners of rows of a shared grid"""
    def __init__(self, grid: Gtk.Grid):
        self.grid = grid
        self.base_row = rows(grid)
        self.attached = []

    def attach(self, widget, left=0, top=0, height=1, width=1):
        self.grid.attach(widget, left=left, top=self.base_row + top, height=height, width=width)
        self.attached.append(widget)
        if hasattr(self.grid, 'on_row_change'):
            self.grid.on_row_change()

    def all_row_numbers(self):
        return map(lambda c: self.grid.child_get_property(c, 'top-attach'), self.attached)

    def evict(self):
        for row in reversed(sorted(set(self.all_row_numbers()))):
            self.grid.remove_row(row)
        if hasattr(self.grid, 'on_row_change'):
            self.grid.on_row_change()

        top = self.grid.get_child_at(top=0, left=0)
        if top and type(top) is Gtk.Separator:
            top.hide()
