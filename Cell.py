from Day_Functions import *
from Shift_Functions import *


class Cell:
    df = None

    def __init__(self, row, day, assigned_shift=None):
        self.row = row
        self.day = day
        self.assigned_shift = assigned_shift
        self.potential_shifts = []

    @property
    def previous_day_shift(self):
        prev_assigned_shift = self.df.at[self.row, previous(self.day)].assigned_shift
        if prev_assigned_shift != None:
            return prev_assigned_shift
        else:
            prev_potential_shifts = self.df.at[self.row, previous(self.day)].potential_shifts
            return prev_potential_shifts

    @property
    def next_day_shift(self):
        next_assigned_shift = self.df.at[self.row, next(self.day)].assigned_shift
        if next_assigned_shift != None:
            return next_assigned_shift
        else:
            next_potential_shifts = self.df.at[self.row, next(self.day)].potential_shifts
            return next_potential_shifts

    def set_potential_shifts(self):
        pass

    def update_potential_shifts(self):
        # Compare to previous cell
        prev_shift = self.previous_day_shift
        # Determine case (assigned shift or list of potential_shifts)
        # Case 1: RDO
        if prev_shift == 'X':
            pass
        # Case 2: list of potential shifts
        elif isinstance(prev_shift, list):
            pass
        # Case 3: assigned shift
        else:
            pass

        # Compare to next cell
        next_shift = self.next_day_shift
        # Determine case (assigned shift or list of potential_shifts)
        # Case 1: RDO
        if next_shift == "X":
            pass
        # Case 2: list of potential shifts
        if isinstance(next_shift, list):
            pass
        # Case 2: assigned shift
        else:
            pass

    def assign_shift(self, shift):
        self.assigned_shift = shift

    def shift_can_be_assigned(self):
        pass


