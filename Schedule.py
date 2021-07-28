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
                        self.shift_lines[row].insert_shift_into_shifts_dict(day, "X")
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

    def update_potential_shifts(self):
        for row in range(self.data.number_of_workers):
            shift_line = self.shift_lines[row]
            for day in days:
                shift_line.update_potential_shifts_on_day(day)

    # this allows you to identify a type of shift you would like to fill at the end of a shift line (before RDO)
    def assign_desired_shift_before_rdo(self, shift_type):
        # first assign shifts on blank day before RDO
        # only one loop necessary (multiple loops will not free up days before RDO)
        # look at each shift line
        for row in range(self.data.number_of_workers):
            shift_line = self.shift_lines[row]
            # skip shift lines that are already filled
            if shift_line.is_filled:
                continue
            # try to assign desired shift of type on blank day before RDO
            try:
                shift_line.assign_shift_on_empty_before_consecutive_rdo(shift_type)
            except ShiftAlreadyFilledError:
                print('The program tried to fill a cell that was already filled')

        # next try to assign shifts on blank day before shift of same shift_type
        # track if any shift was assigned on a pass through all shift lines
        shift_assigned_during_loop = True

        # multiple loops necessary as it may be possible to stack multiple times
        while shift_assigned_during_loop:
            shift_assigned_during_loop = False

            for row in range(self.data.number_of_workers):
                shift_line = self.shift_lines[row]
                # skip shift lines that are already filled
                if shift_line.is_filled:
                    continue
                # try to assign desired shift of type on blank day before shift of same type
                try:
                    shift_assigned_during_loop = shift_line.assign_shift_on_empty_before_shift_of_same_type(shift_type)
                except Exception as error:
                    print('The program encountered an error while filling a blank cell before a shift of type {}'.format(shift_type))
                    print(error)

        # next try to assign shifts on filled day before shift of same type
        # track if any shift was assigned on a pass through all shift lines
        shift_assigned_during_loop = True

        # multiple loops necessary as it may be possible to stack multiple times
        while shift_assigned_during_loop:
            shift_assigned_during_loop = False

            for row in range(self.data.number_of_workers):
                shift_line = self.shift_lines[row]
                # try to assign desired shift of type on blank day before shift of same type
                try:
                    shift_assigned_during_loop = shift_line.replace_filled_shift_before_shift_of_same_type(shift_type)
                except Exception as error:
                    print(
                        'The program encountered an error while filling a blank cell before a shift of type {}'.format(shift_type))
                    print(error)

    def fill_remaining_schedule(self):
        # look at each day
        for day in days:
            # assume no row needs to be filled
            first_row_to_fill = self.data.number_of_workers
            # find the shift line where the day is the day before two consecutive days off
            day_before_consecutive_rdo_identified = False
            # look at each row / shift_line
            for row in range(self.data.number_of_workers):
                shift_line = self.shift_lines[row]
                # find day before consecutive rdo
                day_after_consecutive_rdo = shift_line.get_day_before_consecutive_rdo()
                # check if this day matches the current day
                if day_after_consecutive_rdo == day:
                    day_before_consecutive_rdo_identified = True
                # check if this day is empty
                if day_before_consecutive_rdo_identified and shift_line.shifts_dict[day] == '-':
                    first_row_to_fill = row
                    break

            # Loop from identified row to last row, filling shifts
            for i in range(first_row_to_fill, self.data.number_of_workers):
                # look at each row
                shift_line = self.shift_lines[i]
                # determine if cell is empty on the current day
                if shift_line.shifts_dict[day] == '-':
                    # if cell is empty - try to assign shifts
                    # make sure potential shifts list is in the correct order (all mids should be gone so just sort)
                    shift_line.potential_shifts_dict[day].sort()
                    # look at all potential shifts
                    for shift in shift_line.potential_shifts_dict[day]:
                        try:
                            # if shift can be assigned, there will be no error
                            shift_line.assign_shift(day, shift)
                            # break from loop of potential shifts and proceed to next loop
                            break
                        except ShiftCannotBeAssignedError or BusinessRulesFailedError:
                            # if shift can't be assigned, move on to next potential shift in list
                            continue
                else:
                    # if cell is not empty, move to the next row
                    continue

            # Loop from first row to identified row, filling shifts
            for i in range(0, first_row_to_fill):
                # look at each row
                shift_line = self.shift_lines[i]
                # determine if cell is empty on the current day
                if shift_line.shifts_dict[day] == '-':
                    # if cell is empty - try to assign shifts
                    # make sure potential shifts list is in the correct order (all mids should be gone so just sort)
                    shift_line.potential_shifts_dict[day].sort()
                    # look at all potential shifts
                    for shift in shift_line.potential_shifts_dict[day]:
                        try:
                            # if shift can be assigned, there will be no error
                            shift_line.assign_shift(day, shift)
                            # break from loop of potential shifts and proceed to next loop
                            break
                        except ShiftCannotBeAssignedError or BusinessRulesFailedError:
                            # if shift can't be assigned, move on to next potential shift in list
                            continue
                else:
                    # if cell is not empty, move to the next row
                    continue

    def determine_if_shift_lines_are_filled(self):
        for shift_line in self.shift_lines:
            shift_line.is_filled = True
            for day in days:
                if shift_line.shifts_dict[day] == '-':
                    shift_line.is_filled = False
                    break

    def clean_up_missing_shifts_dict(self):
        cleaned_missing_shifts = {}
        for day in days:
            cleaned_missing_shifts[day] = {}
            for shift, quantity in self.missing_shifts[day].items():
                if quantity > 0:
                    cleaned_missing_shifts[day][shift] = quantity

        self.missing_shifts = cleaned_missing_shifts

    def fill_empty_cells_by_swapping(self):
        # might require multiple passes - track if a successful swap occurs
        successful_swap = True

        # keep looping until no successful swap occurs
        while successful_swap:
            # assume no successful swap occurs
            successful_swap = False

            # look at each shift line
            for row in range(len(self.shift_lines)):
                shift_line = self.shift_lines[row]
                # only look at shift line if it is not full:
                if not shift_line.is_filled:
                    days_with_missing_shifts = []
                    # look at each day and create list of days with missing shifts
                    for day in days:
                        if shift_line.shifts_dict[day] == '-':
                            days_with_missing_shifts.append(day)

                    # determine if the shift line has missing shifts
                    if len(days_with_missing_shifts) > 0:
                        # ask shift line to try to fill by swapping
                        successful_swap = shift_line.fill_by_swapping(days_with_missing_shifts)
                        if successful_swap:
                            shift_line.is_filled = True
                            self.clean_up_missing_shifts_dict()









