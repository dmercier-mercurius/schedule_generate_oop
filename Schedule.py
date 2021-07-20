from Cell import *
import pandas as pd

# list of days to aid in looping through various tasks
days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]


def create_empty_dataframe(number_of_workers):
    blank_schedule = {}
    for day in days:
        blank_schedule[day] = [None] * number_of_workers
        df_to_return = pd.DataFrame(blank_schedule)
    for day in days:
        for i in range(number_of_workers):
            cell = Cell(i, day)
            df_to_return.at[i, day] = cell
    return df_to_return


class Schedule:
    list_of_top_3 = []

    def __init__(self, data):
        self.data = data
        self.df = create_empty_dataframe(data.number_of_workers)

    @property
    def shifts_assigned_on(self):
        shifts_assigned_on = {}
        for day in days:
            shifts_assigned_on[day] = {}
            for i in range(self.data.number_of_workers):
                current_cell = self.df.at[i, day]
                if current_cell.assigned_shift != None:
                    try:
                        shifts_assigned_on[day][current_cell.assigned_shift] += 1
                    except KeyError:
                        shifts_assigned_on[day][current_cell.assigned_shift] = 1
        return shifts_assigned_on

    @property
    def missing_shifts(self):
        shifts_assigned_on = self.shifts_assigned_on
        missing_shifts = {}
        for day in days:
            missing_shifts[day] = {}
            for shift in self.data.daily_shifts[day].keys():
                try:
                    if shifts_assigned_on[day][shift] < self.data.daily_shifts[day][shift]:
                        missing_shifts[day][shift] = self.data.daily_shifts[day][shift] - shifts_assigned_on[day][shift]
                except KeyError:
                    missing_shifts[day][shift] = self.data.daily_shifts[day][shift]
        return missing_shifts

    def display(self):
        display_df = self.df.copy()
        for day in days:
            for i in range(self.data.number_of_workers):
                display_df.at[i, day] = self.df.at[i, day].assigned_shift
        print(display_df)

    def assign_rdo(self):
        first_row_to_fill = 0
        pair_triple_lists = []
        for pair_triple, quantity in self.data.rdo_dict.items():
            pair_triple_days = pair_triple.split("_")
            pair_triple_lists.append(pair_triple_days)
            for row in range(first_row_to_fill, first_row_to_fill + quantity):
                for day in pair_triple_days:
                    self.df.at[row, day].assign_shift("X")
            first_row_to_fill += quantity
