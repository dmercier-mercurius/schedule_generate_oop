from Data import Data, ImpossibleRdoError
from Cell import *
from Schedule import *
from Shift_Functions import *
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app)
app.config['JSON_SORT_KEYS'] = False

pd.set_option("display.max_rows", None, "display.max_columns", None)


@app.route('/schedule/<int:employees_number>', methods=['GET', 'POST'])
@cross_origin()
def main(employees_number):

    # list of days to aid in looping through various tasks
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

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
        # allow each cell to reference the dataframe
        Cell.df = schedule.df

        # assign RDO to schedule
        schedule.assign_rdo()
        schedule.display()

        number_of_attempts += 1

    return vars(data)

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 5000, app)