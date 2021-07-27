from Cell import *
from ShiftLine import *
import pandas as pd

# list of days to aid in looping through various tasks
days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


# def create_empty_dataframe(number_of_workers, shift_length):
#     blank_schedule = {}
#     for day in days:
#         blank_schedule[day] = [None] * number_of_workers
#         df_to_return = pd.DataFrame(blank_schedule)
#     for day in days:
#         for i in range(number_of_workers):
#             cell = Cell(i, day, shift_length)
#             df_to_return.at[i, day] = cell
#     return df_to_return

def create_empty_dataframe(number_of_workers):
    blank_schedule = {}
    for day in days:
        blank_schedule[day] = [None] * number_of_workers
        df_to_return = pd.DataFrame(blank_schedule)
    return df_to_return


def create_shift_lines(number_of_workers, shift_length):
    shift_lines = []
    for row in range(number_of_workers):
        shift_line = ShiftLine(row, shift_length)
        shift_lines.append(shift_line)
    return shift_lines


def set_shifts_assigned(df, number_of_workers):
    shifts_assigned_on = {}
    for day in days:
        shifts_assigned_on[day] = {}
        for i in range(number_of_workers):
            current_shift = df.at[i, day]
            if current_shift != None:
                try:
                    shifts_assigned_on[day][current_shift] += 1
                except KeyError:
                    shifts_assigned_on[day][current_shift] = 1
    return shifts_assigned_on


def set_missing_shifts(shifts_assigned, daily_shifts):
    shifts_assigned_on = shifts_assigned
    missing_shifts = {}
    for day in days:
        missing_shifts[day] = {}
        for shift in daily_shifts[day].keys():
            try:
                if shifts_assigned_on[day][shift] < daily_shifts[day][shift]:
                    missing_shifts[day][shift] = daily_shifts[day][shift] - shifts_assigned_on[day][shift]
                elif shifts_assigned_on[day][shift] == daily_shifts[day][shift]:
                    missing_shifts[day][shift] = 0
            except KeyError:
                missing_shifts[day][shift] = daily_shifts[day][shift]
    return missing_shifts


class Schedule:
    list_of_top_3 = []

    def __init__(self, data):
        self.data = data
        self.df = create_empty_dataframe(data.number_of_workers)
        self.shift_lines = create_shift_lines(data.number_of_workers, data.shift_length)
        self.rdo_pair_triples = []
        self.shifts_assigned = set_shifts_assigned(self.df, self.data.number_of_workers)
        self.missing_shifts = set_missing_shifts(self.shifts_assigned, self.data.daily_shifts)

    # assigns rdo pairs to schedule
    # stores name of each rdo pair/triple to schedule attribute
    # stores in each cell the type/location of RDO in its row
    def assign_rdo(self):
        first_row_to_fill = 0
        pair_triple_lists = []
        for pair_triple, quantity in self.data.rdo_dict.items():
            # store the name of each rdo pair/triple as an attribute of schedule
            self.rdo_pair_triples.append(pair_triple)
            # create a list of all days with an RDO for the current range of rows
            pair_triple_days = pair_triple.split("_")
            pair_triple_lists.append(pair_triple_days)
            # cycle through the correct number of rows based on RDO pair_triple quantity
            for row in range(first_row_to_fill, first_row_to_fill + quantity):
                # store in each shift line the type/location of the RDO in its row
                self.shift_lines[row].rdo_pair_triple = pair_triple
                for day in days:
                    # Assign RDO to df and shift line
                    if day in pair_triple_days:
                        self.df.at[row, day] = "X"
                        self.shift_lines[row].assign_shift(day, "X")
            # advance to the next group of rdo pairs / triples
            first_row_to_fill += quantity

    # determine if a row contains any unassigned shift
    def row_not_filled(self, row):
        row_not_filled = False
        for day in days:
            if self.df.at[row, day] == None:
                row_not_filled = True
                break
            else:
                continue
        return row_not_filled

    def assign_preferred_shift_order(self):
        # track if each type of rdo pair/triple has been filled with as many rows as possible
        # assume false after entering the loop and then turn back to true if a row is successfully filled
        pair_triple_filled_with_pso = {}
        for pair_triple in self.rdo_pair_triples:
            pair_triple_filled_with_pso[pair_triple] = True

        # continue to try to fill in PSO as long as you were able to fill a row on the last pass
        while True in pair_triple_filled_with_pso.values():
            # track row index (so you can start looking at the last row filled - not the beginning!)
            row_to_fill = 0
            # Look at every type of rdo pair_triple
            for pair_triple in self.rdo_pair_triples:
                # only attempt to fill this type if it was filled last time
                if pair_triple_filled_with_pso[pair_triple]:
                    # Look at each row:
                    row_identified = False
                    for row in range(row_to_fill, self.data.number_of_workers):
                        # Determine if it contains the correct RDO type
                        if pair_triple == self.shift_lines[row].rdo_pair_triple:
                            # Determine if row is empty
                            if self.row_not_filled(row):
                                # note that this is the most recent filled row
                                row_to_fill = row
                                row_identified = True
                                # break out of looping through rows
                                break
                    # if entire loop is completed without identifying a row...
                    if not row_identified:
                        # set to false and reset row
                        pair_triple_filled_with_pso[pair_triple] = False
                        # move to next pair triple
                        continue

                # ask shift line to fill itself with PSO
                # will return true or false based on success
                pair_triple_filled_with_pso[pair_triple] = self.shift_lines[row].fill_with_pso()

    def update_shifts_assigned_and_missing_shifts_with_assigned_shift(self, day, shift):
        try:
            self.shifts_assigned[day][shift] += 1
        except KeyError:
            self.shifts_assigned[day][shift] = 1

        self.missing_shifts[day][shift] -= 1

    def update_shifts_assigned_and_missing_shifts_with_removed_shift(self, day, shift):
        self.shifts_assigned[day][shift] -= 1
        self.missing_shifts[day][shift] += 1

    # assign a list of all potential shifts on a day to any cell that is not an RDO
    def set_potential_shifts(self):
        # look at each shift_line
        for row in range(len(self.shift_lines)):
            potential_shifts_dict = self.shift_lines[row].set_potential_shifts()

            if self.row_not_filled(row):
                for day in days:
                    self.df.loc[row, day] = potential_shifts_dict[day]
                    print(potential_shifts_dict[day])

    def cell_before_two_consecutive_rdo(self, cell):
        current_cell = cell
        one_cell_after = cell.next_day_cell
        two_cells_after = one_cell_after.next_day_cell
        for day in days:
            # determine if cell is before 2 day consecutive RDO
            if one_cell_after.assigned_shift == 'X' and two_cells_after.assigned_shift == 'X':
               if current_cell.assigned_shift == None:
                   return "empty"
               else:
                   return 'filled'
            else:
                return False

    # this allows you to identify a type of shift you would like to fill at the end of a shift line (before RDO)
    def assign_shift_before_rdo(self, shift_type):
        # first assign shifts on blank day before RDO
        # only one loop necessary (multiple loops will not free up days before RDO)
        # look at each cell
        for day in days:
            shifts_of_type = self.data.shifts_on_day_of_type[day][shift_type].copy()
            for row in range(self.data.number_of_workers):
                current_cell = self.df.at[row, day]
                # determine if cell is blank and if next day is an RDO
                if self.cell_before_two_consecutive_rdo(current_cell) == 'empty':
                    # look at each shift of given type
                    for shift in shifts_of_type:
                        try:
                            # try to assign shift
                            current_cell.assign_shift(shift)
                            # if it can be assigned, don't try to assign other shifts (break)
                            break
                        except ShiftCannotBeAssignedError:
                            # if shift cannot be assigned, continue to look at the rest of the shifts
                            continue
                    # check if you assigned the last of a shift; remove if you did
                    if self.missing_shifts[day][shift] == 0:
                        shifts_of_type.remove(shift)
                        # check if there are no more shifts to assign; if so move to next day
                        if len(shifts_of_type) == 0:
                            break

