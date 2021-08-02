from Data import *
from Schedule import *
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import cProfile
import pstats

app = Flask(__name__)
CORS(app)
app.config['JSON_SORT_KEYS'] = False

pd.set_option("display.max_rows", None, "display.max_columns", None)


# This allows angular to check a user created/edited shift line
@app.route('/check_shift_line', methods=['GET', 'POST'])
@cross_origin()
def check_shift_line():
    data = request.get_json()
    shift_length = data['shift_length']
    shift_line_mt = data['shift_line']

    # convert from mt to st and assign to ShiftLine object
    shift_line = ShiftLine('row', shift_length)
    for i in range(len(shift_line_mt)):
        if shift_line_mt[i] == "X":
            shift_line.insert_shift_into_shifts_dict(days[i], 'X')
        else:
            shift_line.insert_shift_into_shifts_dict(days[i], mt_to_int(shift_line_mt[i]))

    # determine if any shifts violate business rules
    passes_business_rules = shift_line.check_all_business_rules('MID', ignore_desirable_moves=True)

    if passes_business_rules:
        return jsonify({"business_rules": True})
    else:
        return jsonify({"business_rules": False})


@app.route('/schedule/<int:employees_number>', methods=['GET', 'POST'])
@cross_origin()
def main(employees_number):

    schedule_response_complete = False
    max_number_of_attempts = 4
    max_number_of_schedules = 1
    number_of_attempts = 0
    number_of_rdo_failures = 0

    while not schedule_response_complete:
        # load JSON into input data object
        # data is automatically converted from military time to integer/float values
        # key values are automatically calculated and stored as attributes
        data = Data(request.get_json(), business_rules, False)

        # test the PSO for errors, if there is, return an error message
        if data.errors_in_preferred_shift_order():
            pso_error_string = 'Error: The selected work pattern violate business rules; please select valid shifts'
            print(pso_error_string)
            return jsonify([{"generated_schedule_1": {"schedule": {}, "shift totals": {}, "outliers": {}, "pwp_error": pso_error_string}}])

        # # check for outlier in data set
        # outliers = data.check_for_large_outliers()
        # if outliers:
        #     for shift in outliers.keys():
        #         for day, quantity in outliers[shift].items():
        #             print('Outlier of {} found on {} for shift {}'.format(quantity, day, shift))
        #     return jsonify([{"generated_schedule_1": {"schedule": {}, "shift totals": {}, "outliers": outliers, "pwp_error": {}}}])
        # else:
        #     print('No outliers detected')

        # Assign random shifts to weekdays until total shifts is evenly divisible by shifts per week
        if data.number_of_shifts_to_assign > 0:
            max_number_of_schedules = 3
            data.assign_random_shifts(number_of_attempts)

        # Calculate number of rdo needed
        try:
            data.calc_num_of_each_rdo_sequence(number_of_rdo_failures)
        except ImpossibleRdoError:
            print('impossible RDO pair/triple value encountered')
            number_of_attempts += 1
            number_of_rdo_failures += 1

        # create a blank schedule
        schedule = Schedule(data)
        # allow each shift line to reference the data and schedule
        ShiftLine.data = data
        ShiftLine.schedule = schedule

        # assign RDO to schedule
        schedule.assign_rdo()

        # assign PSO to schedule
        schedule.assign_preferred_shift_order(number_of_attempts)

        # set and update potential shifts for each cell
        schedule.set_potential_shifts()
        schedule.update_potential_shifts()

        # assign shifts before RDO (MID for 8 hour schedule)
        if data.shift_length == 8:
            schedule.assign_desired_shift_before_rdo('MID')
        else:
            schedule.assign_desired_shift_after_rdo('MID')

        # fill remaining schedule with shifts
        schedule.fill_remaining_schedule()

        # identify which cells are filled and which ones have missing shifts
        schedule.determine_if_shift_lines_are_filled()
        # clean up missing shifts dict
        schedule.clean_up_missing_shifts_dict()

        # try to fill missing shifts on shift-lines by swapping
        schedule.fill_empty_cells_by_swapping()

        # determine number of cells without shifts assigned - before ignoring desirable moves
        missing_shifts_before_ignoring_desirable_moves = schedule.get_number_of_missing_shifts()
        print('missing before ignoring undesirable moves:', missing_shifts_before_ignoring_desirable_moves)

        # try to fill cells with required shifts, but ignore desirable moves
        schedule.fill_missing_shifts_ignore_desirable_moves()

        # try to fill cells by swapping - still ignore desirable moves
        schedule.fill_empty_cells_by_swapping(ignore_desirable_moves=True)

        # clean up missing shifts dict
        schedule.clean_up_missing_shifts_dict()
        # determine number of cells without shifts assigned - after ignoring desirable moves
        missing_shifts_after_ignoring_desirable_moves = schedule.get_number_of_missing_shifts()
        print('missing after ignoring undesirable moves:', missing_shifts_after_ignoring_desirable_moves)
        print('df after ignoring desirable moves')
        print(schedule.df)

        shifts_with_undesirable_moves = missing_shifts_before_ignoring_desirable_moves - missing_shifts_after_ignoring_desirable_moves

        # try to fill cells with shifts with shifts that follow business rules, but ignore daily shift requirements
        shifts_ignoring_daily_shift_requirements = schedule.fill_missing_shifts_ignore_daily_shift_requirements()

        # use number of cells without shifts assigned (before and after final fill attempt) to calculate grade
        schedule.calculate_grade(shifts_with_undesirable_moves, shifts_ignoring_daily_shift_requirements)

        # store schedule if grade is high enough (return true or false indicating if schedule was stored)
        schedule_stored = schedule.store_if_high_grade(max_number_of_schedules)

        # if schedule is stored (don't bother to find all this info otherwise!)
        if schedule_stored:
            schedule.create_pattern_column()

            schedule.create_shift_totals_df()
            print(schedule.shift_totals_df)

            schedule.convert_df_from_int_to_st()
            print(schedule.df)

        # increase number of attempts no matter what
        number_of_attempts += 1
        print('attempt {}: grade = {}'.format(number_of_attempts, schedule.grade))

        # determine if schedule response is complete (is another attempt needed?)
        schedule_response_complete = schedule.determine_if_response_is_complete(number_of_attempts, max_number_of_attempts, max_number_of_schedules)

    # Below will only execute when the above loop is terminated (schedule response is complete)
    # generate response
    json_to_return = []
    n = 1
    for schedule in Schedule.top_generated_schedules:
        json_to_return.append({"generated_schedule_" + str(n):
                                   {"schedule": schedule.df.to_json(),
                                    "shift totals": schedule.shift_totals_df.to_json(),
                                    "outliers": {},
                                    "pwp_error": {}}
                               })
        n += 1

    return jsonify(json_to_return)

    # profile = cProfile.Profile()
    # profile.runcall(main(employees_number))
    # ps = pstats.Stats(profile)
    # ps.print_stats()


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 5000, app)