"""
Use this script for single simulations of SENSIBLE storage
"""

import os
import sqlite3
import numpy as np
import pandas as pd
import cobmo.building
import cobmo.controller_sensible
import cobmo.utils
import cobmo.config
import datetime as dt


def connect_database(
        data_path=cobmo.config.data_path,
        overwrite_database=True
):
    # Create database, if none
    if overwrite_database or not os.path.isfile(os.path.join(data_path, 'data.sqlite')):
        cobmo.utils.create_database(
            sqlite_path=os.path.join(data_path, 'data.sqlite'),
            sql_path=os.path.join(cobmo.config.cobmo_path, 'cobmo', 'database_schema.sql'),
            csv_path=data_path
        )

    conn = sqlite3.connect(os.path.join(data_path, 'data.sqlite'))
    return conn


scenario = 'scenario_default'
pricing_method = 'wholesale_market'  # Options: 'wholesale_market' or 'retailer_peak_offpeak'


def get_building_model(
        scenario_name=scenario,
        conn=connect_database()
):
    building = cobmo.building.Building(conn, scenario_name, pricing_method=pricing_method)
    return building


def example():
    """
    Example script
    """

    conn = connect_database()

    # Extracting tables from the sql
    # CAREFUL!
    # Indexing to allow precise modification of the dataframe.
    # If this is used you need to reindex as pandas when using to_sql (meaning NOT using "index=False")
    building_scenarios_csv = pd.read_sql(
        """
        select * from building_scenarios
        """,
        conn,
        index_col='scenario_name'
    )
    buildings_csv = pd.read_sql(
        """
        select * from buildings
        """,
        conn,
        index_col='building_name'
    )
    building_storage_types = pd.read_sql(
        """
        select * from building_storage_types
        """,
        conn,
        index_col='building_storage_type'
    )

    # Importing the parameter_sets to change the storage lifetime
    building_parameter_sets = pd.read_sql(  # TODO: do this without using the parameters table.
        """
        select * from building_parameter_sets
        """,
        conn
    )
    position_lifetime = building_parameter_sets.index[
        building_parameter_sets['parameter_name'] == 'storage_lifetime'
        ].tolist()
    building_parameter_sets.loc[position_lifetime, 'parameter_value'] = (
        float(building_storage_types.at['sensible_thermal_storage_default', 'storage_lifetime'])
    )

    building_parameter_sets.to_sql(
        'building_parameter_sets',
        con=conn,
        if_exists='replace',
        index=False
    )

    building_name = building_scenarios_csv.at[scenario, 'building_name']

    # ____________________________________________ Running the scenarios ______________________________________________

    # Baseline scenario
    buildings_csv.at[building_name, 'building_storage_type'] = ''
    buildings_csv.to_sql(
        'buildings',
        con=conn,
        if_exists='replace'
        # index=False
    )

    building_baseline = get_building_model(conn=conn)
    building_baseline.define_augmented_model()

    controller_sensible = cobmo.controller_sensible.Controller_sensible(
        conn=conn,
        building=building_baseline
    )
    (
        control_timeseries_controller_baseline,
        state_timeseries_controller_baseline,
        output_timeseries_controller_baseline,
        _,
        optimum_obj_baseline
    ) = controller_sensible.solve()

    # Storage scenario
    # Setting storage option for the building + getting another building + running controller again
    buildings_csv.at[building_name, 'building_storage_type'] = 'sensible_thermal_storage_default'
    buildings_csv.to_sql(
        'buildings',
        con=conn,
        if_exists='replace'
        # index=False
    )
    building_sensible = get_building_model(conn=conn)
    building_sensible.define_augmented_model()

    controller_sensible = cobmo.controller_sensible.Controller_sensible(
        conn=conn,
        building=building_sensible
    )
    (
        control_timeseries_controller_storage,
        state_timeseries_controller_storage,
        output_timeseries_controller_storage,
        storage_size,
        optimum_obj_storage
    ) = controller_sensible.solve()

    # ____________________________________________ Payback & Plotting ______________________________________________

    # Set options here
    print_on_csv = 0
    plotting = 1
    save_plot = 0

    print('\n----------------------------------------------')
    print('\n>> Total opex (storage)= {}'.format(float(optimum_obj_storage)))

    # Calculating the savings and the payback time
    savings_day = (optimum_obj_baseline - optimum_obj_storage)

    if building_sensible.building_scenarios['investment_sgd_per_X'][0] == 'kwh':
        storage_size = storage_size * 1000.0 * 4186.0 * 8.0 * 2.77778e-7  # TODO: take value from building_sensible
        print('\n>> Storage size = %.2f kWh' % storage_size)
    elif building_sensible.building_scenarios['investment_sgd_per_X'][0] == 'm3':
        print('\n>> Storage size = %.2f m3' % storage_size)
    else:
        print('\n Please define a specific unit of the storage investment')

    (simple_payback, discounted_payback) = cobmo.utils.discounted_payback_time(
        building_sensible,
        storage_size,
        savings_day,
        save_plot,
        plotting
    )

    print('\n>> Storage type = %s'
          '  |  Optimal storage size = %.2f'
          '  | savings year 〜= %.2f'
          '  | Discounted payback = %i\n'
          % (
            building_sensible.building_scenarios['building_storage_type'][0],
            storage_size,
            savings_day * 260.0,
            discounted_payback
          )
          )

    # Printing the outputs to dedicated csv files. These are IGNORED by the git
    if print_on_csv == 1:

        # Storage scenario
        building_sensible.state_matrix.to_csv('delete_me_storage/sensible/state_matrix_SENSIBLE.csv')
        building_sensible.control_matrix.to_csv('delete_me_storage/sensible/control_matrix_SENSIBLE.csv')
        building_sensible.disturbance_matrix.to_csv('delete_me_storage/sensible/disturbance_matrix_SENSIBLE.csv')

        building_sensible.state_output_matrix.to_csv('delete_me_storage/sensible/state_output_matrix_SENSIBLE.csv')
        building_sensible.control_output_matrix.to_csv('delete_me_storage/sensible/control_output_matrix_SENSIBLE.csv')
        building_sensible.disturbance_output_matrix.to_csv('delete_me_storage/sensible/disturbance_output_matrix_SENSIBLE.csv')

        # state_timeseries_simulation_storage.to_csv('delete_me_storage/sensible/state_timeseries_simulation_SENSIBLE.csv')

        state_timeseries_controller_storage.to_csv('delete_me_storage/sensible/state_timeseries_controller_SENSIBLE.csv')
        date_main = dt.datetime.now()
        filename_out_controller = (
                'output_timeseries_controller_SENSIBLE' + '_{:04d}-{:02d}-{:02d}_{:02d}-{:02d}-{:02d}'.format(
                    date_main.year, date_main.month, date_main.day, date_main.hour, date_main.minute,
                    date_main.second)
                + '.csv'
        )
        output_timeseries_controller_storage.to_csv('delete_me_storage/sensible/' + filename_out_controller)

        control_timeseries_controller_storage.to_csv('delete_me_storage/sensible/control_timeseries_controller_SENSIBLE.csv')

        # Baseline scenario
        building_baseline.state_matrix.to_csv('delete_me/state_matrix.csv')
        building_baseline.control_matrix.to_csv('delete_me/control_matrix.csv')
        building_baseline.disturbance_matrix.to_csv('delete_me/disturbance_matrix.csv')

        building_baseline.state_output_matrix.to_csv('delete_me/state_output_matrix.csv')
        building_baseline.control_output_matrix.to_csv('delete_me/control_output_matrix.csv')
        building_baseline.disturbance_output_matrix.to_csv('delete_me/disturbance_output_matrix.csv')

        # np.savetxt(r'my_file_output_state_matrix.txt', building.state_matrix.values) # , fmt='%d'
        # state_timeseries_simulation_baseline.to_csv('delete_me/state_timeseries_simulation.csv')

        state_timeseries_controller_baseline.to_csv('delete_me/state_timeseries_controller.csv')

        date_main = dt.datetime.now()
        filename_out_controller = (
                'output_timeseries_controller' + '_{:04d}-{:02d}-{:02d}_{:02d}-{:02d}-{:02d}'.format(
                    date_main.year, date_main.month, date_main.day, date_main.hour, date_main.minute,
                    date_main.second)
                + '.csv'
        )
        output_timeseries_controller_baseline.to_csv('delete_me/' + filename_out_controller)
        control_timeseries_controller_baseline.to_csv('delete_me/control_timeseries_controller.csv')


if __name__ == "__main__":
    example()


