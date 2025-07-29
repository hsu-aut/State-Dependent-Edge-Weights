import numpy as np
import PARAMETER_CONFIG

def make_parameter_ranges_gaussian(
    nominals: dict,
    n_values: int,
    lower_factor: float,
    upper_factor: float,
    sigma_coverage_factor: float = 6.0
) -> dict:
    parameter_ranges = {}
    for name, nominal in nominals.items():
        mean = nominal
        std_dev: float

        if nominal == 0:
            std_dev = 0.0
        elif upper_factor == lower_factor:
            std_dev = 0.0
        else:
            # Die Breite des Intervalls ist nominal * (upper_factor - lower_factor)
            # Diese Breite soll sigma_coverage_factor * std_dev entsprechen.
            std_dev = nominal * (upper_factor - lower_factor) / sigma_coverage_factor
            std_dev = max(0.0, std_dev)
        samples = np.random.normal(loc=mean, scale=std_dev, size=n_values)
        parameter_ranges[name] = samples.tolist()
    return parameter_ranges


parameters_gaussian = make_parameter_ranges_gaussian(
    PARAMETER_CONFIG.NOMINALS,
    n_values=PARAMETER_CONFIG.NUMBER_OF_VALUES,
    lower_factor=PARAMETER_CONFIG.LOWER_BOUND,
    upper_factor=PARAMETER_CONFIG.UPPER_BOUND
)