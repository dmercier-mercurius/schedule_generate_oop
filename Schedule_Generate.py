from Data import Data, ImpossibleRdoError
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


@app.route('/schedule/<int:employees_number>', methods=['GET', 'POST'])
@cross_origin()
def main(employees_number):

    number_of_attempts = 0
    number_of_RDO_failures = 0

    while number_of_attempts < 1:
        # load JSON into input data object
        # data is automatically converted from military time to integer/float values
        # key values are automatically calculated and stored as attributes
        data = Data(request.get_json(), True)

        # Assign random shifts to weekdays until total shifts is evenly divisible by shifts per week
        data.assign_random_shifts(number_of_attempts)

        # Calculate number of rdo needed
        try:
            data.calc_num_of_each_rdo_sequence(number_of_RDO_failures)
        except ImpossibleRdoError:
            print('impossible RDO pair/triple value encountered')
            number_of_attempts += 1
            number_of_RDO_failures += 1

        # create a blank schedule
        schedule = Schedule(data)
        # allow each shift line to reference the schedule
        ShiftLine.data = data
        ShiftLine.schedule = schedule

        # assign RDO to schedule
        schedule.assign_rdo()

        # assign PSO to schedule
        schedule.assign_preferred_shift_order()

        # set potential shifts for each cell
        schedule.set_potential_shifts()

        # I still need to update potential shifts for the pso shifts already assigned
        # these changes will only affect the shift_line_dict, not the dataframe
        # this will allow me to reference potential shifts even if a shift has been assigned in a cell

        # assign shift before RDO
        schedule.assign_shift_before_rdo('MID')

        # profile = cProfile.Profile()
        # profile.runcall(main(employees_number))
        # ps = pstats.Stats(profile)
        # ps.print_stats()

        number_of_attempts += 1

    return ('successfully ran')

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 5000, app)