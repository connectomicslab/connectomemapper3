# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Module that defines CMTK functions for converting C02 emissions estimated with `codecarbon`."""


def get_emission_car_miles_equivalent(emissions):
    """Return the equivalent of CO2 emissions [Kg] in terms of kms traveled by an average car.

    References
    ----------
    https://github.com/mlco2/codecarbon/blob/c6aebb9681186a71573748e381b6a3c9731de2d3/codecarbon/viz/data.py#L53

    """
    return "{:.0f}".format((emissions / 0.409) * 1.60934)


def get_emission_tv_time_equivalent(emissions):
    """Return the equivalent of CO2 emissions [Kg] in terms of kms traveled by an average car.

    References
    ----------
    https://github.com/mlco2/codecarbon/blob/c6aebb9681186a71573748e381b6a3c9731de2d3/codecarbon/viz/data.py#L66

    """
    tv_time_in_minutes = emissions * (1 / 0.097) * 60
    tv_time = "{:.0f} minutes".format(tv_time_in_minutes)
    if tv_time_in_minutes >= 60:
        time_in_hours = tv_time_in_minutes / 60
        tv_time = "{:.0f} hours".format(time_in_hours)
        if time_in_hours >= 24:
            time_in_days = time_in_hours / 24
            tv_time = "{:.0f} days".format(time_in_days)
    return tv_time
