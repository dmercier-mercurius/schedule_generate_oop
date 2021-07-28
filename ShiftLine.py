from Shift_Functions import *
from copy import deepcopy
import itertools
import pandas as pd

day_to_index = {'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6}
index_to_day = {0: 'SUN', 1: 'MON', 2: 'TUE', 3: 'WED', 4: 'THU', 5: 'FRI', 6: 'SAT'}

# list of days to aid in looping through various tasks
days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


class BusinessRulesFailedError(Exception):
    pass


class ShiftCannotBeAssignedError(Exception):
    pass


class ShiftAlreadyFilledError(Exception):
    pass


class ShiftLine:
    data = None
    schedule = None

    def __init__(self, row, shift_length):
        self.row = row
        self.shift_length = shift_length
        self.shifts_dict = {'SUN': '-', 'MON': '-', 'TUE': '-', 'WED': '-', 'THU': '-', 'FRI': '-', 'SAT': '-'}
        self.potential_shifts_dict = {'SUN': [], 'MON': [], 'TUE': [], 'WED': [], 'THU': [], 'FRI': [], 'SAT': []}
        self.rdo_pair_triple = None
        self.is_filled = False

    @property
    def shifts_list(self):
        return list(self.shifts_dict.values())

    def insert_shift_into_shifts_dict(self, day, shift):
        self.shifts_dict[day] = shift

    def remove_shift_from_shifts_dict(self, day):
        self.shifts_dict[day] = '-'

    def check_all_business_rules(self, shift_type, max_consecutive_shifts_allowed, slice_start="SUN", slice_end="SAT"):
        all_rules_passed = False

        if self.check_desirable_moves(slice_start, slice_end):
            if self.check_sufficient_rest(slice_start, slice_end):
                if self.check_consecutive_shifts_of_type(shift_type, max_consecutive_shifts_allowed):
                    all_rules_passed = True

        return all_rules_passed

    def check_sufficient_rest(self, slice_start="SUN", slice_end="SAT"):
        start_index = day_to_index[slice_start] - 1
        end_index = day_to_index[slice_end] + 1

        sufficient_rest = True

        for i in range(start_index, end_index):
            if sufficient_rest_between_shifts(self.shifts_list[i], self.shifts_list[(i+1) % 7], self.shift_length):
                continue
            else:
                sufficient_rest = False
                break

        return sufficient_rest

    def check_desirable_moves(self, slice_start="SUN", slice_end="SAT"):
        start_index = day_to_index[slice_start] - 1
        end_index = day_to_index[slice_end] + 1

        desirable_moves = True

        for i in range(start_index, end_index):
            if desirable_move_between_shifts(self.shifts_list[i], self.shifts_list[(i+1) % 7], self.shift_length):
                continue
            else:
                desirable_moves = False
                break

        return desirable_moves

    def check_consecutive_shifts_of_type(self, shift_type, max_consecutive_shifts_allowed):
        counter = 0
        for shift in self.shifts_list:
            if determine_type_of_shift(shift, self.shift_length) == shift_type:
                counter += 1
                if counter > max_consecutive_shifts_allowed:
                    return False
            else:
                counter = 0

        return True

    def push_shift_line_to_df(self):
        shifts_dict_copy = self.shifts_dict.copy()
        for day, shift in shifts_dict_copy.items():
            if shift == '-':
                shifts_dict_copy[day] = self.potential_shifts_dict[day]
        series_to_push = pd.Series(shifts_dict_copy)
        self.schedule.df.iloc[self.row] = series_to_push

    def assign_shift(self, day, shift, slice_start=False, slice_end=False):
        if not slice_start:
            slice_start = day
        if not slice_end:
            slice_end = day

        # check if shift can be assigned on day without surpassing daily shift requirements
        try:
            if self.schedule.missing_shifts[day][shift] > 0:
                # check if a shift has already been assigned (i.e. are we trying a replacement)
                if self.shifts_dict[day] != "-":
                    shift_replaced = self.shifts_dict[day]
                else:
                    shift_replaced = False

                # place shift into shift line
                self.insert_shift_into_shifts_dict(day, shift)
                # check business rules
                if self.check_all_business_rules("MID", 5, slice_start, slice_end):
                    # if all business rules passed...
                    # update all potential shifts in this shift line
                    self.update_potential_shifts_horizontal_cascade(day)
                    # update potential shifts for the current cell
                    # changes to potential lists before and after will affect this!
                    self.update_potential_shifts_on_day(day)

                    # update schedule lists
                    self.schedule.update_shifts_assigned_and_missing_shifts_with_assigned_shift(day, shift)
                    if shift_replaced:
                        self.schedule.update_shifts_assigned_and_missing_shifts_with_removed_shift(day, shift_replaced)

                    # now that lists are updated, check if assigning this caused the number of missing shifts to equal 0
                    if self.schedule.missing_shifts[day][shift] == 0:
                        self.update_potential_shifts_vertical_cascade(day)

                    self.push_shift_line_to_df()
                    return True
                else:
                    # if business rule check fails, remove shift, put back replaced shift (if any) and return error
                    self.remove_shift_from_shifts_dict(day)
                    if shift_replaced:
                        self.insert_shift_into_shifts_dict(day, shift_replaced)
                    raise BusinessRulesFailedError
            else:
                # shift cannot be assigned if number of missing shifts = 0
                raise ShiftCannotBeAssignedError
        # shift cannot be assigned if it is not in missing_shifts dictionary
        except KeyError:
            raise ShiftCannotBeAssignedError

    def get_day_before_consecutive_rdo(self):
        for i in range(len(self.shifts_list)):
            if self.shifts_list[i] != "X" and self.shifts_list[(i+1) % 7] == "X" and self.shifts_list[(i+2) % 7] == "X":
                day_before = index_to_day[i]
                return day_before

    def get_day_after_consecutive_rdo(self):
        for i in range(len(self.shifts_list)):
            if self.shifts_list[i] != "X" and self.shifts_list[i-1] == "X" and self.shifts_list[i-2] == "X":
                day_after = index_to_day[i]
                return day_after

    def get_day_for_cell_of_type_before_shift_of_type(self, cell_type, shift_type):
        for day, shift in self.shifts_dict.items():
            if cell_type == "filled":
                if self.shifts_dict[day] != 'X' and self.shifts_dict[day] != '-':
                    if determine_type_of_shift(self.shifts_dict[next(day)], self.shift_length) == shift_type:
                        return day
            elif cell_type == "empty":
                if self.shifts_dict[day] == '-':
                    if determine_type_of_shift(self.shifts_dict[next(day)], self.shift_length) == shift_type:
                        return day
        return False

    def fill_with_pso(self):

        # find first day after consecutive RDO
        day_to_fill = self.get_day_after_consecutive_rdo()

        # look at every shift in PSO
        for preferred_shift in self.data.preferred_shift_order:
            shift_assigned = False
            # check if shift for day is under daily requirements
            try:
                if self.schedule.missing_shifts[day_to_fill][preferred_shift] > 0:
                    # if so, assign shift...
                    self.insert_shift_into_shifts_dict(day_to_fill, preferred_shift)
                    # check if this shift meets business rules
                    if self.check_all_business_rules('MID', 5, day_to_fill, day_to_fill):
                        # if all rules met, indicate shift is assigned
                        shift_assigned = True
                    else:
                        # if rules not met, remove shift - loop will proceed to alt shift loop
                        self.remove_shift_from_shifts_dict(day_to_fill)
            except KeyError:
                # key error indicates pso shift should not be assigned on this day
                shift_assigned = False

            if shift_assigned == False:
                # if not, look at alternative shifts of same type
                type_of_pso_shift = determine_type_of_shift(preferred_shift, self.shift_length)
                for alt_shift in self.data.shifts_on_day_of_type[day_to_fill][type_of_pso_shift]:
                    try:
                        # check if alt shift is under daily requirements
                        if self.schedule.missing_shifts[day_to_fill][alt_shift] > 0:
                            # assign the shift
                            self.insert_shift_into_shifts_dict(day_to_fill, alt_shift)
                            # check if this alt shift meets business rules
                            if self.check_all_business_rules('MID', 5, day_to_fill, day_to_fill):
                                # if all rules met, break from alt shift loop
                                shift_assigned = True
                                break
                            else:
                                # if rules not met, remove shift and continue alt shift loop
                                self.remove_shift_from_shifts_dict(day_to_fill)
                                continue
                    except KeyError:
                        # if shift is not in missing days it cannot be assigned; proceed to next alt shift
                        continue

            # Advance to next non-rdo day if shift was successfully assigned
            if shift_assigned:
                day_to_fill = next(day_to_fill)
                while self.shifts_dict[day_to_fill] == "X":
                    day_to_fill = next(day_to_fill)
            else:
                # if you could not assign a shift, clear row and return False
                for day in days:
                    if self.shifts_dict[day] != "X":
                        self.remove_shift_from_shifts_dict(day)
                return False

        # if you make it though all preferred shifts without error, shift line is filled
        # update assigned shifts
        # push shift line to df
        # return True
        for day, shift in self.shifts_dict.items():
            if self.shifts_dict[day] != "X":
                self.is_filled = True
                self.schedule.update_shifts_assigned_and_missing_shifts_with_assigned_shift(day, shift)
                self.push_shift_line_to_df()
        return True

    def set_potential_shifts(self):
        for day in days:
            potential_shifts = []
            if self.shifts_dict[day] == 'X':
                self.potential_shifts_dict[day] = 'X'
            else:
                for shift, quantity in self.schedule.missing_shifts[day].items():
                    if quantity > 0:
                        potential_shifts.append(shift)
                self.potential_shifts_dict[day] = potential_shifts

        return self.potential_shifts_dict

    def update_potential_shifts_on_day(self, day):
        # first check if current shift is an RDO
        current_shift = self.shifts_dict[day]
        if current_shift == "X":
            # if it is, do not change potential shifts list
            # return that list was not changed
            return False

        else:
            existing_potential_shifts_list = self.potential_shifts_dict[day]

            # Compare to previous cell
            possible_shifts_after_previous = set()

            # Determine case (assigned shift or list of potential_shifts)
            prev_day = previous(day)
            prev_shift = self.shifts_dict[prev_day]
            if prev_shift == '-':
                prev_shift = self.potential_shifts_dict[prev_day]

            # Case 1: RDO
            if prev_shift == 'X':
                # any shift can follow an RDO - create set of all shifts that can follow the previous day
                for potential_shifts in self.data.potential_shifts_dict[prev_day]['after'].values():
                    possible_shifts_after_previous = possible_shifts_after_previous.union(potential_shifts)

            # Case 2: list of potential shifts
            elif isinstance(prev_shift, list):
                # find union of all sets of shifts after each given shift on previous day
                for shift, potential_shifts in self.data.potential_shifts_dict[prev_day]['after'].items():
                    if shift in prev_shift:
                        possible_shifts_after_previous = possible_shifts_after_previous.union(potential_shifts)

            # Case 3: assigned shift
            else:
                # identify set of possible shifts that come after this specific shift
                possible_shifts_after_previous = possible_shifts_after_previous.union(self.data.potential_shifts_dict[prev_day]['after'][prev_shift])

            # Compare to next cell
            possible_shifts_before_next = set()
            next_day = next(day)
            next_shift = self.shifts_dict[next_day]
            if next_shift == '-':
                next_shift = self.potential_shifts_dict[next_day]

            # Determine case (assigned shift or list of potential_shifts)

            # Case 1: RDO
            if next_shift == 'X':
                # any shift can be before an RDO - create set of all shifts that can be before the next day
                for potential_shifts in self.data.potential_shifts_dict[next_day]['before'].values():
                    possible_shifts_before_next = possible_shifts_before_next.union(potential_shifts)

            # Case 2: list of potential shifts
            elif isinstance(next_shift, list):
                # find union of all sets of shifts before each given shift on next day
                for shift, potential_shifts in self.data.potential_shifts_dict[next_day]['before'].items():
                    if shift in next_shift:
                        possible_shifts_before_next = possible_shifts_before_next.union(potential_shifts)

            # Case 3: assigned shift
            else:
                # identify set of possible shifts that come before this specific shift
                possible_shifts_before_next = possible_shifts_before_next.union(self.data.potential_shifts_dict[next_day]['before'][next_shift])

            # list of potential shifts for this day will be the intersection of shifts after previous and before next
            potential_shifts_list = list(possible_shifts_after_previous.intersection(possible_shifts_before_next))

            # make a copy of potential_shifts_list to avoid error while removing from object that is being looped over
            potential_shifts_list_copy = potential_shifts_list.copy()

            # Remove any shifts from potential shifts list is missing shifts for given shift is equal to 0
            for potential_shift in potential_shifts_list_copy:
                if self.schedule.missing_shifts[day][potential_shift] == 0:
                    potential_shifts_list.remove(potential_shift)

            if existing_potential_shifts_list == potential_shifts_list:
                potential_shifts_list_changed = False
            else:
                potential_shifts_list_changed = True

            self.potential_shifts_dict[day] = potential_shifts_list
            return potential_shifts_list_changed

    def assign_shift_on_empty_before_consecutive_rdo(self, shift_type):
        # identify day before consecutive rdo
        day_to_fill = self.get_day_before_consecutive_rdo()

        # determine if this day is empty
        if self.shifts_dict[day_to_fill] == '-':
            # if so, track if a shift could be assigned
            shift_assigned = False

            # look at each shift of given type for this day
            for shift in self.data.shifts_on_day_of_type[day_to_fill][shift_type]:
                # try to assign the given shift
                try:
                    self.assign_shift(day_to_fill, shift)
                    # if shift is assigned, break and stop looking at shifts
                    shift_assigned = True
                    break
                except ShiftCannotBeAssignedError or BusinessRulesFailedError:
                    # if shift cannot be assigned, look at the next shift
                    continue
        else:
            raise ShiftAlreadyFilledError

        if shift_assigned:
            return True
        else:
            return False

    def assign_shift_on_empty_before_shift_of_same_type(self, shift_type):
        # identify empty shift before shift of same type
        day_to_fill = self.get_day_for_cell_of_type_before_shift_of_type('empty', shift_type)

        # check if an appropriate day was found
        if day_to_fill:
            # if so, track if a shift could be assigned
            shift_assigned = False

            # look at each shift of given type for this day
            for shift in self.data.shifts_on_day_of_type[day_to_fill][shift_type]:
                # try to assign the given shift
                try:
                    self.assign_shift(day_to_fill, shift)
                    # if shift is assigned, break and stop looking at shifts
                    shift_assigned = True
                    break
                except ShiftCannotBeAssignedError or BusinessRulesFailedError:
                    # if shift cannot be assigned, look at the next shift
                    continue

        # if no such day exists, return False (no shift assigned)
        else:
            return False

        if shift_assigned:
            return True
        else:
            return False

    def replace_filled_shift_before_shift_of_same_type(self, shift_type):
        # identify empty shift before shift of same type
        day_to_fill = self.get_day_for_cell_of_type_before_shift_of_type('filled', shift_type)

        # check if an appropriate day was found
        if day_to_fill:
            # if so, track if a shift could be assigned
            shift_assigned = False

            # look at each shift of given type for this day
            for shift in self.data.shifts_on_day_of_type[day_to_fill][shift_type]:
                # try to assign the given shift
                try:
                    self.assign_shift(day_to_fill, shift)
                    # if shift is assigned, break and stop looking at shifts
                    shift_assigned = True
                    break
                except BusinessRulesFailedError:
                    # if shift cannot be assigned because of business rules, try to change previous shift
                    # this will need to be added later!!!
                    continue
                except ShiftCannotBeAssignedError:
                    # if shift cannot be assigned, look at the next shift
                    continue

        # if no such day exists, return False (no shift assigned)
        else:
            return False

        if shift_assigned:
            return True
        else:
            return False

    def update_potential_shifts_horizontal_cascade(self, start_day):
        prev_day = previous(start_day)
        prev_shift = self.shifts_dict[prev_day]
        while self.update_potential_shifts_on_day(prev_day):
            # assign shift if only one remaining in potential shifts dict and shift is unassigned
            if len(self.potential_shifts_dict[prev_day]) == 1 and prev_shift == '-':
                self.assign_shift(prev_day, self.potential_shifts_dict[prev_day][0])
            prev_day = previous(prev_day)
            prev_shift = self.shifts_dict[prev_day]

        next_day = next(start_day)
        next_shift = self.shifts_dict[next_day]
        while self.update_potential_shifts_on_day(next_day):
            # assign shift if only one remaining in potential shifts dict and shift is unassigned
            if len(self.potential_shifts_dict[next_day]) == 1 and next_shift == '-':
                self.assign_shift(next_day, self.potential_shifts_dict[next_day][0])
            next_day = next(next_day)
            next_shift = self.shifts_dict[next_day]

    def update_potential_shifts_vertical_cascade(self, day):
        for row in range(self.data.number_of_workers):
            shift_line = self.schedule.shift_lines[row]
            shift_line.update_potential_shifts_on_day(day)
            if len(shift_line.potential_shifts_dict[day]) == 1 and shift_line.shifts_dict[day] == '-':
                shift_line.assign_shift(day, shift_line.potential_shifts_dict[day][0])

            shift_line.update_potential_shifts_horizontal_cascade(day)
            shift_line.push_shift_line_to_df()

    def fill_by_swapping(self, list_of_days_with_missing_shifts):
        # look at all shift lines
        for row in range(len(self.schedule.shift_lines)):
            given_shift_line = self.schedule.shift_lines[row]
            # make a copy of the shifts_dict for shift line with missing shifts
            missing_shift_line_copy = deepcopy(self)

            # check if rdo is in range we are trying to swap
            rdo_detected = False
            for day in list_of_days_with_missing_shifts:
                if given_shift_line.shifts_dict[day] == 'X':
                    rdo_detected = True
            # if there is, move on to next shift_line
            if rdo_detected:
                continue

            # determine if shifts from given_shift_line can successfully fill missing_shift_line_copy
            # first fill each missing day with shift from given shift line
            for day in list_of_days_with_missing_shifts:
                missing_shift_line_copy.shifts_dict[day] = given_shift_line.shifts_dict[day]

            # check if missing_shift_line follows all business rules
            missing_shift_line_can_be_filled = missing_shift_line_copy.check_all_business_rules("MID", 5)

            # only proceed if the missing shift line can be filled by the given shift line
            if missing_shift_line_can_be_filled:
                # now try to fill given_shift_line with missing shifts on each day
                # make a copy of the shifts_dict for given shift line
                given_shift_line_copy = deepcopy(given_shift_line)

                # if there is only 1 day with a missing shift
                if len(list_of_days_with_missing_shifts) == 1:
                    day = list_of_days_with_missing_shifts[0]
                    # look at each missing shift on this day
                    for shift in self.schedule.missing_shifts[day].keys():
                        # place shift in given_shift_copy
                        given_shift_line_copy.shifts_dict[day] = shift
                        # check if given_shift_line_copy follows all business rules
                        given_shift_line_can_be_filled = given_shift_line_copy.check_all_business_rules("MID", 5)

                        # only proceed if the given shift line can also be filled with missing shifts
                        if given_shift_line_can_be_filled:
                            # swap the lines by assigning shift_dicts
                            self.shifts_dict = missing_shift_line_copy.shifts_dict
                            self.push_shift_line_to_df()
                            # update schedule lists
                            self.schedule.update_shifts_assigned_and_missing_shifts_with_assigned_shift(day, shift)
                            # push changes to df
                            given_shift_line.shifts_dict = given_shift_line_copy.shifts_dict
                            given_shift_line.push_shift_line_to_df()
                            print('swapped with row', row)
                            return True

                # if there are multiple days with missing shifts
                else:
                    # create a list of all possible combinations of missing shifts
                    list_of_missing_shifts_per_day = []
                    for day in list_of_days_with_missing_shifts:
                        list_of_missing_shifts_per_day.append(list(self.schedule.missing_shifts[day].keys()))
                    all_possible_missing_shift_combinations = list(itertools.product(*list_of_missing_shifts_per_day))

                    # look at each combination until a successful one if found
                    for i in range(len(all_possible_missing_shift_combinations)):
                        # look at each combo one by one
                        missing_shift_combo = all_possible_missing_shift_combinations[i]
                        # fill given_shift_line_copy with missing shifts from this combo
                        for j in range(len(list_of_days_with_missing_shifts)):
                            given_shift_line_copy.shifts_dict[list_of_days_with_missing_shifts[j]] = missing_shift_combo[j]

                        # check if given_shift_line_copy follows all business rules
                        given_shift_line_can_be_filled = given_shift_line_copy.check_all_business_rules("MID", 5)

                        # only proceed if the given shift line can also be filled with missing shifts
                        if given_shift_line_can_be_filled:
                            # swap the lines by assigning shift_dicts
                            self.shifts_dict = missing_shift_line_copy.shifts_dict
                            self.push_shift_line_to_df()
                            # update schedule lists
                            for a in range(len(list_of_days_with_missing_shifts)):
                                day = list_of_days_with_missing_shifts[a]
                                shift = missing_shift_combo[a]
                                self.schedule.update_shifts_assigned_and_missing_shifts_with_assigned_shift(day, shift)

                            # push changes to df
                            given_shift_line.shifts_dict = given_shift_line_copy.shifts_dict
                            given_shift_line.push_shift_line_to_df()
                            print('swapped with row', row)
                            return True

        # if entire loop ends without return, swap failed
        return False





