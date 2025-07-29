import numpy as np
import PARAMETER_CONFIG

def make_parameter_ranges(
    nominals: dict,
    n_values: int,
    lower_factor: float,
    upper_factor: float
) -> dict:
    return {
        name: list(np.linspace(
            nominal * lower_factor,
            nominal * upper_factor,
            num=n_values
        ))
        for name, nominal in nominals.items()
    }


parameters = make_parameter_ranges(
    PARAMETER_CONFIG.NOMINALS,
    n_values=PARAMETER_CONFIG.NUMBER_OF_VALUES,
    lower_factor=PARAMETER_CONFIG.LOWER_BOUND,
    upper_factor=PARAMETER_CONFIG.UPPER_BOUND
)