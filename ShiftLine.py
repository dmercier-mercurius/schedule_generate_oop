from Shift_Functions import *
import pandas as pd

day_to_index = {'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6}
index_to_day = {0: 'SUN', 1: 'MON', 2: 'TUE', 3: 'WED', 4: 'THU', 5: 'FRI', 6: 'SAT'}

# list of days to aid in looping through various tasks
days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


class ShiftLine:
    data = None
    schedule = None

    def __init__(self, row, shift_length):
        self.row = row
        self.shift_length = shift_length
        self.shifts_dict = {'SUN': '-', 'MON': '-', 'TUE': '-', 'WED': '-', 'THU': '-', 'FRI': '-', 'SAT': '-'}
        self.potential_shifts_dict = {'SUN': [], 'MON': [], 'TUE': [], 'WED': [], 'THU': [], 'FRI': [], 'SAT': []}
        self.rdo_pair_triple = None

    @property
    def shifts_list(self):
        return list(self.shifts_dict.values())

    def assign_shift(self, day, shift):
        self.shifts_dict[day] = shift

    def remove_shift(self, day):
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
        series_to_push = pd.Series(self.shifts_dict)
        self.schedule.df.iloc[self.row] = series_to_push

    def fill_with_pso(self):
        # track if you could fill this shift line with a PSO
        shift_line_filled = False

        # find first day after consecutive RDO
        for i in range(len(self.shifts_list)):
            if self.shifts_list[i] != "X" and self.shifts_list[i-1] == "X" and self.shifts_list[i-2] == "X":
                day_to_fill = index_to_day[i]
                break

        # look at every shift in PSO
        for preferred_shift in self.data.preferred_shift_order:
            shift_assigned = False
            # check if shift for day is under daily requirements
            try:
                if self.schedule.missing_shifts[day_to_fill][preferred_shift] > 0:
                    # if so, assign shift...
                    self.assign_shift(day_to_fill, preferred_shift)
                    shift_assigned = True
            except KeyError:
                shift_assigned = False

            if shift_assigned == False:
                # if not, look at alternative shifts of same type
                type_of_pso_shift = determine_type_of_shift(preferred_shift, self.shift_length)
                for alt_shift in self.data.shifts_on_day_of_type[day_to_fill][type_of_pso_shift]:
                    try:
                        # check if alt shift is under daily requirements
                        if self.schedule.missing_shifts[day_to_fill][alt_shift] > 0:
                            # assign the shift
                            self.assign_shift(day_to_fill, alt_shift)
                            shift_assigned = True
                            # check if this alt shift meets business rules
                            if self.check_all_business_rules('MID', 5, day_to_fill, day_to_fill):
                                # if all rules met, break from alt shift loop
                                break
                            else:
                                # if rules not met, remove shift and continue alt shift loop
                                self.remove_shift(day_to_fill)
                                continue
                    except KeyError:
                        # if shift is not in missing days it cannot be assiend; proceed to next alt shift
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
                        self.remove_shift(day)
                return False

        # if you make it though all preferred shifts without error, shift line is filled
        # update assigned shifts
        # push shift line to df
        # return True
        for day, shift in self.shifts_dict.items():
            if self.shifts_dict[day] != "X":
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
            existing_potential_shifts_list = self.potential_shifts

            # Compare to previous cell
            possible_shifts_after_previous = set()

            # Determine case (assigned shift or list of potential_shifts)
            prev_day = previous(day)
            prev_shift = self.shifts_dict[prev_day]

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

            # determine if the potential shifts list for this cell changed
            if existing_potential_shifts_list == potential_shifts_list:
                potential_shifts_list_changed = False
            else:
                potential_shifts_list_changed = True

            self.potential_shifts_dict[day] = potential_shifts_list
            return potential_shifts_list_changed

    def update_potential_shifts_for_entire_shift_line(self, start_day):

        prior_day = previous(start_day)
        while self.update_potential_shifts_on_day(prior_day):
            prior_day = previous(prior_day)

        next_day = next(start_day)
        while self.update_potential_shifts_on_day(next_day):
            next_day = next(next_day)

