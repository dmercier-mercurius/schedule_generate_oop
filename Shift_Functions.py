from Database import Database
from Day_Functions import *
import random

database = Database('ST-AWS')
business_rules = database.get_all_business_rules()


# receives starting time of a shift in the range 0 - 23 and returns type of shift
def determine_type_of_shift(shift_start, shift_length):
    if shift_start == "X":
        return 'RDO'

    if shift_start == "-":
        return 'unassigned'

    if (7 - shift_length / 2) < shift_start <= (7 + shift_length / 2):
        return "DAY"
    elif (15 - shift_length / 2) < shift_start <= (15 + shift_length / 2):
        return "EVE"
    else:
        return "MID"


# determine if the amount of time between two shifts is sufficient
# references business rules
def sufficient_rest_between_shifts(prev_shift, next_shift, shift_length):

    global business_rules
    business_rules_for_given_shift_length = business_rules[shift_length]

    if prev_shift == 'X' or next_shift == 'X':
        return True

    if prev_shift == '-' or next_shift == '-':
        return True

    # Case 1: prev_shift starts on given day
    if 0 <= prev_shift <= (23 - shift_length / 2):
        # Sub-Case 1: next_shift starts on given day
        if 0 <= next_shift <= (23 - shift_length / 2):
            if prev_shift < next_shift:
                return True
            else:
                time_between_shift_starts = (24 - prev_shift) + next_shift

        # Sub-Case 2: next_shift starts on previous day
        elif (23 - shift_length / 2) < next_shift < 24:
            time_between_shift_starts = next_shift - prev_shift

    # Case 2: prev_shift starts on previous day
    elif (23 - shift_length / 2) < prev_shift < 24:
        # Sub-Case 1: next_shift starts on given day
        if 0 <= next_shift <= (23 - shift_length / 2):
            return True

        # Sub-Case 2: next_shift starts on previous day
        elif (23 - shift_length / 2) < next_shift < 24:
            time_between_shift_starts = (24 - prev_shift) + next_shift

    rest = round(time_between_shift_starts - shift_length, 2)

    prev_shift_type = determine_type_of_shift(prev_shift, shift_length)
    next_shift_type = determine_type_of_shift(next_shift, shift_length)

    sufficient_rest = True

    # check if rest is sufficient for varying cases
    if prev_shift_type == "DAY" and next_shift_type == "MID":
        if shift_length == 8 and prev_shift <= 5.5:
            sufficient_rest = False
        else:
            if rest < business_rules_for_given_shift_length['time_between_day_shift_to_mid_shift']:
                sufficient_rest = False
    elif prev_shift_type == "EVE" and next_shift_type == "DAY":
        if rest < business_rules_for_given_shift_length['time_between_eve_shift_to_day_shift']:
            sufficient_rest = False
    elif prev_shift_type == "MID" and next_shift_type == "MID":
        if rest < business_rules_for_given_shift_length['time_between_mid_shift_to_any_shift']:
            sufficient_rest = False
    else:
        if rest < 8:
            sufficient_rest = False

    return sufficient_rest


# Check if transition between two shifts is "desirable"
def desirable_move_between_shifts(prev_shift, next_shift, shift_length):

    if prev_shift == "-" or next_shift == '-':
        return True

    if prev_shift == "X" or next_shift == 'X':
        return True

    prev_shift_type = determine_type_of_shift(prev_shift, shift_length)

    next_shift_type = determine_type_of_shift(next_shift, shift_length)

    if next_shift == "X":
        return True

    if prev_shift == "X":
        return True

    if prev_shift_type == "EVE":
        if next_shift_type == "EVE" or next_shift_type == "DAY":
            return True
        else:
            return False
    elif prev_shift_type == "DAY":
        if next_shift_type == "DAY" or next_shift_type == "MID":
            return True
        else:
            return False
    else:
        if shift_length == 10:
            return True
        else:
            if next_shift_type == "MID":
                return True
            else:
                return False


# Identify the sets of shifts that can follow a given shift
# by default it takes desirable moves into account, but this can be set to False
def identify_set_of_possible_shifts_before(shift, day, daily_shifts, shift_length, check_for_desirable=True):
    potential_shifts_before = set()

    # look at all shifts on the previous day
    for prev_shift in daily_shifts[previous(day)].keys():

        # check rest requirements
        if sufficient_rest_between_shifts(prev_shift, shift, shift_length):
            satisfy_rest_requirements = True
        else:
            satisfy_rest_requirements = False

        # check desirable move requirements (unless function call specifies not to)
        if check_for_desirable:
            if desirable_move_between_shifts(prev_shift, shift, shift_length):
                satisfy_desirable_move_requirements = True
            else:
                satisfy_desirable_move_requirements = False
        else:
            satisfy_desirable_move_requirements = True

        if satisfy_rest_requirements and satisfy_desirable_move_requirements:
            potential_shifts_before.add(prev_shift)

    return potential_shifts_before


# Identify the sets of shifts that can follow a given shift
# by default it takes desirable moves into account, but this can be set to False
def identify_set_of_possible_shifts_after(shift, day, daily_shifts, shift_length, check_for_desirable=True):
    potential_shifts_after = set()

    # look at all shifts on the next day
    for next_shift in daily_shifts[next(day)].keys():

        # check rest requirements
        if sufficient_rest_between_shifts(shift, next_shift, shift_length):
            satisfy_rest_requirements = True
        else:
            satisfy_rest_requirements = False

        # check desirable move requirements (unless function call specifies not to)
        if check_for_desirable:
            if desirable_move_between_shifts(shift, next_shift, shift_length):
                satisfy_desirable_move_requirements = True
            else:
                satisfy_desirable_move_requirements = False
        else:
            satisfy_desirable_move_requirements = True

        if satisfy_rest_requirements and satisfy_desirable_move_requirements:
            potential_shifts_after.add(next_shift)

    return potential_shifts_after


# Identifies the shift on a given day with the highest quantity
# This is part of the function that assigns extra shifts randomly
def identify_busiest_shift_on_day(daily_shifts, day, potential_shifts):
    max_num_of_shifts = 0
    busiest_shift = None

    for shift, quantity in daily_shifts[day].items():
        if shift in potential_shifts:
            if quantity > max_num_of_shifts:
                potential_shifts.remove(shift)
                max_num_of_shifts = quantity
                busiest_shift = shift

    return busiest_shift, potential_shifts


def add_to_busiest_shifts_on_random_days(shifts_to_add, daily_shifts, shift_length):
    # only add random shifts to weekdays
    days = ["MON", "TUE", "WED", "THU", "FRI"]

    # select all week day shifts as possible shifts to add
    potential_shifts_to_add = {}
    for day in days:
        potential_shifts_to_add[day] = []
        for shift in daily_shifts[day].keys():
            if determine_type_of_shift(shift, shift_length) == "MID":
                continue
            elif daily_shifts[day][shift] == 0:
                continue
            else:
                potential_shifts_to_add[day].append(shift)

    while shifts_to_add > 0:
        # if every day has been selected, reset the days list
        if len(days) == 0:
            days = ["MON", "TUE", "WED", "THU", "FRI"]

        # select day / remove from days list
        random_day = days.pop(random.randint(0, len(days)-1))

        # refill a day with potential shifts if every potential shift for a day has already been assigned
        if len(potential_shifts_to_add[random_day]) == 0:
            for shift in daily_shifts[random_day].keys():
                if 22 <= shift < 24 or 0 <= shift < 6:
                    continue
                elif daily_shifts[random_day][shift] == 0:
                    continue
                else:
                    potential_shifts_to_add[random_day].append(shift)

        # pick a random shift and remove from list for the random day
        random_shift, potential_shifts_to_add[random_day] = identify_busiest_shift_on_day(daily_shifts, random_day, potential_shifts_to_add[random_day])
        daily_shifts[random_day][random_shift] += 1

        shifts_to_add -= 1

    return daily_shifts


# Identify day with least shifts
# Used to identify day that should be assigned extra shifts
def identify_day_with_least_shifts(total_shifts_per_day):
    min_daily_shifts = 999999999

    for day, num_of_shifts in total_shifts_per_day.items():
        if num_of_shifts < min_daily_shifts:
            min_daily_shifts = num_of_shifts
            day_with_least_shifts = day

    return day_with_least_shifts


# new random shift generator
# Identify day with least number of shifts
# Assign shifts to that day
def generate_targeted_random_shifts_to_add(shifts_to_add, total_shifts_per_day, daily_shifts):

    # Track the number of potential shifts added on each day
    potential_shifts_added = {}

    # Select existing shifts that are not mid-shifts as potential
    for day, shifts in daily_shifts.items():
        potential_shifts_added[day] = {}
        for shift, quantity in shifts.items():
            if quantity == 0 or 22 <= shift < 24 or 0 <= shift < 6:
                continue
            else:
                potential_shifts_added[day][shift] = 0

    while shifts_to_add > 0:
        # identify day with least total shifts
        day_to_add_shift = identify_day_with_least_shifts(total_shifts_per_day)

        # Identify shift on day with fewest number of shifts added
        min_number_of_shifts = 9999999999
        for shift, quantity in potential_shifts_added[day_to_add_shift].items():
            if quantity < min_number_of_shifts:
                min_number_of_shifts = quantity
                shift_to_add = shift

        # Add shift to daily shifts
        daily_shifts[day_to_add_shift][shift_to_add] += 1
        # Record that shift has been added
        potential_shifts_added[day_to_add_shift][shift_to_add] += 1
        # decrement number of shifts to add
        shifts_to_add -= 1

    return daily_shifts
