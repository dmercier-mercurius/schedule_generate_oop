from ShiftLine import *
from Shift_Functions import *
import numpy as np

database = Database('ST-AWS')
business_rules = database.get_all_business_rules()

days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


class ImpossibleRdoError(Exception):
    pass


# converts a value in military time to an equivalent integer/float
# Used in conversion functions below
def mt_to_int(military_time):
    hours = military_time[0:2]
    minutes = military_time[2:]

    if hours[0] == 0:
        hours = hours[1]
    hours = int(hours)

    minutes = round(int(minutes)/60, 2)

    if minutes == 0:
        time = hours
    else:
        time = hours + minutes
    return time


# convert preferred shift order values from military time to integer/float equivalents
def convert_preferred_shift_order(preferred_shift_order_mt):
    preferred_shift_order = []
    for i in range(0, len(preferred_shift_order_mt)):
        preferred_shift_order.append(mt_to_int(preferred_shift_order_mt[i]))
    return preferred_shift_order


# ensure daily shifts is in the correct order
# removes all shifts with a quantity of 0 (no need to keep them!)
# Used in the function below before daily_shifts is returned
def sort_daily_shifts(daily_shifts):
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

    sorted_daily_shifts = {}
    for day in days:
        sorted_daily_shifts[day] = {}
        for i in np.linspace(23, 47, 2401):
            if i % 1 == 0:
                i = int(i % 24)
            else:
                i = round(round(i, 2) % 24, 2)
            try:
                quantity = daily_shifts[day][i]
                if quantity == 0:
                    continue
                else:
                    sorted_daily_shifts[day][i] = daily_shifts[day][i]
            except KeyError:
                continue
    return sorted_daily_shifts


# convert daily shift data from military time to integer/float equivalents
# sorts daily shifts
def convert_daily_shifts(daily_shifts_mt):
    daily_shifts = {}
    for day in days:
        daily_shifts[day] = {}
        for shift_time, quantity in daily_shifts_mt[day].items():
            daily_shifts[day][mt_to_int(shift_time)] = quantity
    sorted_daily_shifts = sort_daily_shifts(daily_shifts)
    return sorted_daily_shifts


# Helper function for outlier function below
def split_data_set_into_halves(data_set):
    data_set_length = len(data_set)

    # Case 1 - even length data set
    if data_set_length % 2 == 0:
        lower_data_half = data_set[0: int(data_set_length/2)]
        upper_data_half = data_set[int(data_set_length/2):]
    # Case 2 - odd length data set
    else:
        lower_data_half = data_set[0: int(data_set_length / 2)]
        upper_data_half = data_set[int(data_set_length / 2) + 1:]

    return lower_data_half, upper_data_half


# Helper function for outlier function below
def find_median(data_set):
    data_set_length = len(data_set)

    # Case 1 - even length data set
    if data_set_length % 2 == 0:
        median = (data_set[int(data_set_length / 2) - 1] + data_set[int(data_set_length / 2)]) / 2
    # Case 2 - odd length data set
    else:
        median = data_set[int(data_set_length / 2)]

    return median


# sort possible shifts by type
# allows code to search for alternate options if preferred shift is not possible
def sort_shifts_by_type(daily_shifts, shift_length):
    shifts_of_type = {}
    for day in days:
        shifts_of_type[day] = {'EVE': [], 'DAY': [], 'MID': []}
        for shift in daily_shifts[day].keys():
            shift_type = determine_type_of_shift(shift, shift_length)
            if shift_type == "EVE":
                shifts_of_type[day][shift_type].insert(0, shift)
            else:
                shifts_of_type[day][shift_type].append(shift)
    return shifts_of_type


# creates a dictionary of potential shifts before a given shift on a given day (stored as a set)
def get_potential_shifts_dict(daily_shifts, shift_length, check_for_desirable=True):
    potential_shifts = {}

    # look at each day
    for day in days:
        potential_shifts[day] = {}
        potential_shifts[day]['before'] = {}
        potential_shifts[day]['after'] = {}
        # look at each shift one by one
        for shift in daily_shifts[day].keys():
            # get set of possible shifts before
            potential_shifts[day]['before'][shift] = identify_set_of_possible_shifts_before(shift, day, daily_shifts, shift_length, check_for_desirable)
            potential_shifts[day]['after'][shift] = identify_set_of_possible_shifts_after(shift, day, daily_shifts, shift_length, check_for_desirable)

    return potential_shifts


# allows unpacking, storing, converting, and error checking of data received from Angular
# RDO_is_contiguous should be passed from Angular in future
# check for desirable allows later iterations of program to ignore desirable moves check
class Data:
    def __init__(self, input_data, RDO_is_contiguous, check_for_desirable=True):
        self.business_rules = business_rules
        self.shift_length = input_data["shift_length"]
        self.preferred_work_pattern = input_data['PWP']
        self.__preferred_shift_order_mt = input_data['PSO']
        self.preferred_shift_order = convert_preferred_shift_order(self.__preferred_shift_order_mt)
        self.__daily_shifts_mt = input_data["daily_shifts"]
        self.daily_shifts = convert_daily_shifts(self.__daily_shifts_mt)
        self.potential_shifts_dict = get_potential_shifts_dict(self.daily_shifts, self.shift_length, check_for_desirable)
        self.shifts_on_day_of_type = sort_shifts_by_type(self.daily_shifts, self.shift_length)
        self.RDO_is_contiguous = RDO_is_contiguous
        self.number_of_days_in_rdo = 7 - int((40 / self.shift_length))
        self.rdo_dict = None

    # Find the total # shifts per day for SUN - SAT
    @property
    def total_shifts_per_day(self):
        total_shifts_per_day = {}
        for day in days:
            total_shifts_per_day[day] = 0
            for quantity in self.daily_shifts[day].values():
                total_shifts_per_day[day] += quantity
        return total_shifts_per_day

    # Find total number of shifts for the week
    @property
    def total_shifts_in_week(self):
        total_shifts_in_week = 0
        for day, total_shifts in self.total_shifts_per_day.items():
            total_shifts_in_week += total_shifts
        return total_shifts_in_week

    # determine number of extra shifts to assign to make total number of shifts divisible
    @property
    def number_of_shifts_to_assign(self):
        # determine number of shifts worked in a week by a worker
        number_of_weekly_shifts_for_worker = int(40 / self.shift_length)
        # determine number of extra shifts that make total shifts per week NOT divisible by above value
        extra_shifts = self.total_shifts_in_week % number_of_weekly_shifts_for_worker
        # determine number of shifts that must be added
        if extra_shifts == 0:
            number_of_shifts_to_assign = 0
        else:
            number_of_shifts_to_assign = number_of_weekly_shifts_for_worker - extra_shifts
        return number_of_shifts_to_assign

    # determine number of works required based on the total number of shifts for the week
    @property
    def number_of_workers(self):
        # determine number of workers needed based on shift length
        number_of_workers = self.total_shifts_in_week / (40 / self.shift_length)
        # check that number of workers is an integer
        if number_of_workers % 1 == 0:
            return int(number_of_workers)
        else:
            print('Error: The number of workers should be an integer')

    # determine the number of workers who are off / not working on each day
    @property
    def total_workers_off_per_day(self):
        workers_off_per_day = {}
        for day in self.total_shifts_per_day.keys():
            workers_off_per_day[day] = self.number_of_workers - self.total_shifts_per_day[day]
        return workers_off_per_day

    # identify pattern for RDOs to follow
    @property
    def rdo_pattern(self):
        if self.number_of_days_in_rdo == 3:
            if self.RDO_is_contiguous:
                RDO_pattern = [1, 1, 1, 0, 0, 0, 0]
            else:
                RDO_pattern = [1, 1, 0, 0, 1, 0, 0]
        else:
            RDO_pattern = [1, 1, 0, 0, 0, 0, 0]
        return RDO_pattern

    # check if PSO follows business rules
    # if not, return a list of error messages specifying the problem(s)
    def errors_in_preferred_shift_order(self):

        # create blank shift_line
        shift_line = ShiftLine('PSO', 8)

        # insert RDO into the preferred shift order depending on number of RDO and if they are contiguous
        if self.number_of_days_in_rdo == 2:
            list_of_shifts = self.preferred_shift_order + ['X', 'X']
        else:
            if self.RDO_is_contiguous:
                list_of_shifts = self.preferred_shift_order[0:1] + ['X'] + self.preferred_shift_order[2:3] + ['X', 'X']
            else:
                list_of_shifts = self.preferred_shift_order + ['X', 'X', 'X']

        # fill shift line with PSO
        for i in range(len(days)):
            shift_line.shifts_dict[days[i]] = list_of_shifts[i]

        # test all business rules
        passes_business_rules = shift_line.check_all_business_rules('MID', 5)

        if passes_business_rules:
            return False
        else:
            return True

    # Identifies any shifts that have an unusually high quantity using an outlier test
    def check_for_large_outliers(self):

        quantities_data_set = []

        for day in days:
            for quantity in self.__daily_shifts_mt[day].values():
                quantities_data_set.append(quantity)

        quantities_data_set.sort()

        # split data set into upper and lower half
        lower_data_half, upper_data_half = split_data_set_into_halves(quantities_data_set)

        # Find Q1 and Q3
        Q1 = find_median(lower_data_half)
        Q3 = find_median(upper_data_half)

        # Find IQR
        IQR = Q3 - Q1

        # Define upper limit of acceptable data
        upper_bound = Q3 + (1.5 * IQR)

        # check for and store any quantities that are outlier
        outlier_located = False
        outliers = {}
        for day in days:
            for shift, quantity in self.__daily_shifts_mt[day].items():
                if quantity > upper_bound:
                    outlier_located = True
                    if shift[0] == "0":
                        shift = shift[1:]
                    try:
                        outliers[shift][day] = quantity
                    except KeyError:
                        outliers[shift] = {}
                        outliers[shift][day] = quantity

        if outlier_located:
            return outliers
        else:
            return False

    # call appropriate random shift function based on number of attempts
    def assign_random_shifts(self, number_of_attempts):
        if number_of_attempts % 2 == 0:
            self.daily_shifts = add_to_busiest_shifts_on_random_days(self.number_of_shifts_to_assign, self.daily_shifts, self.shift_length)
        else:
            self.daily_shifts = generate_targeted_random_shifts_to_add(self.number_of_shifts_to_assign, self.total_shifts_per_day, self.daily_shifts)

    # calculate how many of each rdo pair/triple is needed based on length of rdo and numbers of total days off each day
    def calc_num_of_each_rdo_sequence(self, num_RDO_failures):

        # create coefficient matrix based on number of days in RDO
        coefficient_matrix = np.zeros((7, 7), dtype=int)

        for i in range(0, 7):
            for j in range(0, 7):
                coefficient_matrix[i, (i + j) % 7] = self.rdo_pattern[j]

        # find inverse of matrix (necessary to solve)
        inverse_coefficient_matrix = np.linalg.inv(coefficient_matrix)

        # Create matrix with total number of RDO for each day
        RDO_totals_matrix = np.zeros((7, 1), dtype=int)
        index = 0
        for day, quantity in self.total_workers_off_per_day.items():
            RDO_totals_matrix[index, 0] = quantity
            index += 1

        # solve for the number of each RDO sequence we need
        RDO_sequence_matrix = np.matmul(inverse_coefficient_matrix, RDO_totals_matrix)

        if num_RDO_failures == 0:
            RDO_minimum = 1
        else:
            RDO_minimum = 0

        if self.number_of_days_in_rdo == 2:
            RDO_pair_triple_name_list = ["SAT_SUN", "SUN_MON", "MON_TUE", "TUE_WED", "WED_THU", "THU_FRI", "FRI_SAT"]
        elif self.number_of_days_in_rdo == 3:
            if self.RDO_is_contiguous:
                RDO_pair_triple_name_list = ["FRI_SAT_SUN", "SAT_SUN_MON", "SUN_MON_TUE", "MON_TUE_WED", "TUE_WED_THU",
                                             "WED_THU_FRI", "THU_FRI_SAT"]
            else:
                RDO_pair_triple_name_list = ["SAT_SUN_WED", "SUN_MON_THU", "MON_TUE_FRI", "TUE_WED_SAT", "WED_THU_SUN",
                                             "THU_FRI_MON", "FRI_SAT_TUE"]

        # create dictionary of the number of each RDO sequence
        rdo_dict = {}
        for i in range(0, 7):
            if int(round(RDO_sequence_matrix[i][0], 0)) >= RDO_minimum:
                rdo_dict[RDO_pair_triple_name_list[i]] = int(round(RDO_sequence_matrix[i][0], 0))
            else:
                raise ImpossibleRdoError

        self.rdo_dict = rdo_dict