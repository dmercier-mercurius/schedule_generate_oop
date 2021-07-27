import pymysql


class Database:
    # create database with name specifying the specific database to connect with
    def __init__(self, database_name):
        self.database_name = database_name

    # create ane return a mysql connection object
    def create_db_connection(self):
        try:
            conn = pymysql.connect(host="stlines.citzqhoya3lb.us-east-2.rds.amazonaws.com",
                                   user="stlines_admin", password="LNTnjFxYvBjDkPw5", database=self.database_name)
            print('Successfully connected to database')
            return conn
        except Exception as error:
            print('connection failed!', error)
            exit()

    # retrieve all business rules and return as a python dictionary
    def get_all_business_rules(self):

        conn = self.create_db_connection()

        try:
            with conn.cursor() as cursor:
                sql_statement = "SELECT Parameter, Value, Shift_Length FROM ztest_faa_business_rules"
                cursor.execute(sql_statement)
                business_rules = cursor.fetchall()

                business_rules_dict = {}
                for rule in business_rules:
                    try:
                        business_rules_dict[rule[2]][rule[0]] = rule[1]
                    except KeyError:
                        business_rules_dict[rule[2]] = {}
                        business_rules_dict[rule[2]][rule[0]] = rule[1]

                return business_rules_dict

        except Exception as error:
            print(error)
        finally:
            conn.close()
