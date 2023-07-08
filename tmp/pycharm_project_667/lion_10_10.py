import sys
import math
from main_helper import MainHelper

# WGS72 value; taken from https://geographiclib.sourceforge.io/html/NET/NETGeographicLib_8h_source.html
EARTH_RADIUS = 6378135.0

# GENERATION CONSTANTS   Iridium

BASE_NAME = "Lion"
NICE_NAME = "Lion"

# Lion 630

ECCENTRICITY = 0.0000001  # Circular orbits are zero, but pyephem does not permit 0, so lowest possible value
ARG_OF_PERIGEE_DEGREE = 0.0
PHASE_DIFF = True

################################################################
# The below constants are taken from Kuiper's FCC filing as below:
# [1]: https://www.itu.int/ITU-R/space/asreceived/Publication/DisplayPublication/8716
################################################################

MEAN_MOTION_REV_PER_DAY = 14.80  # Altitude ~630 km
ALTITUDE_M = 630000  # Altitude ~630 km

# Considering an elevation angle of 30 degrees; possible values [1]: 20(min)/30/35/45
SATELLITE_CONE_RADIUS_M = ALTITUDE_M / math.tan(math.radians(20.0))

MAX_GSL_LENGTH_M = math.sqrt(math.pow(SATELLITE_CONE_RADIUS_M, 2) + math.pow(ALTITUDE_M, 2))

# ISLs are not allowed to dip below 80 km altitude in order to avoid weather conditions
# MAX_ISL_LENGTH_M = 2 * math.sqrt(math.pow(EARTH_RADIUS + ALTITUDE_M, 2) - math.pow(EARTH_RADIUS + 80000, 2))
MAX_ISL_LENGTH_M = 8000000
NUM_ORBS = 10
NUM_SATS_PER_ORB = 10
INCLINATION_DEGREE = 51.9


################################################################Iridium

main_helper = MainHelper(
        BASE_NAME,
        NICE_NAME,
        ECCENTRICITY,
        ARG_OF_PERIGEE_DEGREE,
        PHASE_DIFF,
        MEAN_MOTION_REV_PER_DAY,
        ALTITUDE_M,
        MAX_GSL_LENGTH_M,
        MAX_ISL_LENGTH_M,
        NUM_ORBS,
        NUM_SATS_PER_ORB,
        INCLINATION_DEGREE,
)


#  python lion_10_10.py 600 100000 isls_plus_grid twostation algorithm_free_one_only_over_isls 4

def testmain():
    main_helper.calculate(
        'genn_data',
        600,100000,
        'isls_plus_grid',
        'twostation',
        'algorithm_free_one_only_over_isls',
        4,
    )


def main():
    args = sys.argv[1:]
    if len(args) != 6:
        print("Must supply exactly six arguments")
        print("Usage: python main_kuiper_630.py [duration (s)] [time step (ms)] "
              "[isls_plus_grid / isls_none] "
              "[ground_stations_{top_100, paris_moscow_grid}] "
              "[algorithm_{free_one_only_over_isls, free_one_only_gs_relays, paired_many_only_over_isls}] "
              "[num threads]")
        exit(1)
    else:
        main_helper.calculate(
            "gen_data",
            int(args[0]),
            int(args[1]),
            args[2],
            args[3],
            args[4],
            int(args[5]),
        )


if __name__ == "__main__":
    testmain()

# python main_Lion_630.py 600 100000 isls_plus_grid twostation algorithm_free_one_only_over_isls 20
