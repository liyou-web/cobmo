"""Example run script to demonstrate the main features of CoBMo."""

import numpy as np
import os
import pandas as pd

import cobmo.building_model
import cobmo.config
import cobmo.optimization_problem
import cobmo.database_interface


def main():

    # Settings.
    scenario_name = 'scenario_default'
    results_path = os.path.join(cobmo.config.results_path, f'run_example_{cobmo.config.timestamp}')

    # Instantiate results directory.
    os.mkdir(results_path)

    # Recreate / overwrite database, to incorporate changes in the CSV files.
    cobmo.database_interface.recreate_database()

    # Obtain building model.
    building = cobmo.building_model.BuildingModel(scenario_name)

    # Print building model matrices and disturbance timeseries.
    print(f"state_matrix = \n{building.state_matrix.to_string()}")
    print(f"control_matrix = \n{building.control_matrix.to_string()}")
    print(f"disturbance_matrix = \n{building.disturbance_matrix.to_string()}")
    print(f"state_output_matrix = \n{building.state_output_matrix.to_string()}")
    print(f"control_output_matrix = \n{building.control_output_matrix.to_string()}")
    print(f"disturbance_output_matrix = \n{building.disturbance_output_matrix.to_string()}")
    print(f"disturbance_timeseries = \n{building.disturbance_timeseries.to_string()}")

    # Store building model matrices and disturbance timeseries as CSV.
    building.state_matrix.to_csv(os.path.join(results_path, 'building_state_matrix.csv'))
    building.control_matrix.to_csv(os.path.join(results_path, 'building_control_matrix.csv'))
    building.disturbance_matrix.to_csv(os.path.join(results_path, 'building_disturbance_matrix.csv'))
    building.state_output_matrix.to_csv(os.path.join(results_path, 'building_state_output_matrix.csv'))
    building.control_output_matrix.to_csv(os.path.join(results_path, 'building_control_output_matrix.csv'))
    building.disturbance_output_matrix.to_csv(os.path.join(results_path, 'building_disturbance_output_matrix.csv'))
    building.disturbance_timeseries.to_csv(os.path.join(results_path, 'building_disturbance_timeseries.csv'))

    # Define exemplary control timeseries and run simulation.
    control_timeseries_simulation = pd.DataFrame(
        np.ones((len(building.timesteps), len(building.controls))),
        index=building.timesteps,
        columns=building.controls
    )
    (
        state_timeseries_simulation,
        output_timeseries_simulation
    ) = building.simulate(
        state_initial=building.state_vector_initial,
        control_timeseries=control_timeseries_simulation
    )

    # Print simulation results.
    print(f"control_timeseries_simulation = \n{control_timeseries_simulation.to_string()}")
    print(f"state_timeseries_simulation = \n{state_timeseries_simulation.to_string()}")
    print(f"output_timeseries_simulation = \n{output_timeseries_simulation.to_string()}")

    # Store simulation results as CSV.
    control_timeseries_simulation.to_csv(os.path.join(results_path, 'control_timeseries_simulation.csv'))
    state_timeseries_simulation.to_csv(os.path.join(results_path, 'state_timeseries_simulation.csv'))
    output_timeseries_simulation.to_csv(os.path.join(results_path, 'output_timeseries_simulation.csv'))

    # Obtain and solve optimization problem.
    optimization_problem = cobmo.optimization_problem.OptimizationProblem(
        building
    )
    (
        control_timeseries_optimization,
        state_timeseries_optimization,
        output_timeseries_optimization,
        operation_cost,
        investment_cost,  # Zero when running (default) operation problem.
        storage_size  # Zero when running (default) operation problem.
    ) = optimization_problem.solve()

    # Print optimization results.
    print(f"operation_cost = {operation_cost}")
    print(f"control_timeseries_optimization = \n{control_timeseries_optimization.to_string()}")
    print(f"state_timeseries_optimization = \n{state_timeseries_optimization.to_string()}")
    print(f"output_timeseries_optimization = \n{output_timeseries_optimization.to_string()}")

    # Store optimization results as CSV.
    control_timeseries_optimization.to_csv(os.path.join(results_path, 'control_timeseries_optimization.csv'))
    state_timeseries_optimization.to_csv(os.path.join(results_path, 'state_timeseries_optimization.csv'))
    output_timeseries_optimization.to_csv(os.path.join(results_path, 'output_timeseries_optimization.csv'))

    # Print results path.
    print(f"Results are stored in: {results_path}")


if __name__ == '__main__':
    main()
