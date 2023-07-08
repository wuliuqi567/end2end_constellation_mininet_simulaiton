import os
import time
import math
import ephem
from astropy.time import Time
from astropy import units as u
import numpy as np
import networkx as nx

from gen_satellites_info import gen_info
# from add_flow import add_flow
from add_gs_host_link import *

# import pexpect
from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.link import TCLink, Link, Intf
from mininet.topo import Topo
from mininet.util import quietRun
import threading

# gen_data = 'gen_data/'
# gen_data = 'starlink/'
# gen_data2 = 'gen_data2/'
# WGS72 value; taken from https://geographiclib.sourceforge.io/html/NET/NETGeographicLib_8h_source.html
EARTH_RADIUS = 6378135.0

ECCENTRICITY = 0.0000001  # Circular orbits are zero, but pyephem does not permit 0, so lowest possible value
ARG_OF_PERIGEE_DEGREE = 0.0

PHASE_DIFF = True

light_speed = 3e8
REMOTE_CONTROLLER_IP = '127.0.0.1'

################################################################
# The below constants are taken from Kuiper's FCC filing as below:
# [1]: https://www.itu.int/ITU-R/space/asreceived/Publication/DisplayPublication/8716
################################################################

# read configure file
configure_dict = {}
# {'satellite_network_dir_and_name': 'starlink',
# 'ALTITUDE_M': '550000',
# 'Elevation_angle': '20',
# 'NUM_ORBS': '72',
# 'NUM_SATS_PER_ORB': '22',
# 'INCLINATION_DEGREE': '53',
# 'simulation_end_time_s': '600',
# 'Time_step_ms': '100',
# 'isl_data_rate_megabit_per_s': '10.0',
# 'gsl_data_rate_megabit_per_s': '10.0',
# 'isl_max_queue_size_pkts': '100',
# 'gsl_max_queue_size_pkts': '100',
# }
with open('config_mininet.csv', 'r') as config_file:
    lines = config_file.readlines()
    for line in lines:
        line = line.strip().split('=')
        configure_dict.setdefault(line[0], line[1])
    # print(configure_dict)xc

if not os.path.exists(configure_dict['satellite_network_dir_and_name']):
    # gen_info(output_generated_data_dir, simulation_end_time_s, time_step_ms,
    #             BASE_NAME, ALTITUDE_M, Elevation_angle, NUM_ORBS, NUM_SATS_PER_ORB, INCLINATION_DEGREE):
    gen_info(configure_dict['satellite_network_dir_and_name'], int(configure_dict['simulation_end_time_s']),
             int(configure_dict['Time_step_ms']), configure_dict['satellite_network_dir_and_name'],
             int(configure_dict['ALTITUDE_M']), int(configure_dict['Elevation_angle']), int(configure_dict['NUM_ORBS']),
             int(configure_dict['NUM_SATS_PER_ORB']), int(configure_dict['INCLINATION_DEGREE']))
else:

    print('constellation {} has already'.format(configure_dict['satellite_network_dir_and_name']))

ALTITUDE_M = int(configure_dict['ALTITUDE_M'])
NUM_ORBS = int(configure_dict['NUM_ORBS'])
NUM_SATS_PER_ORB = int(configure_dict['NUM_SATS_PER_ORB'])
elevation_angle = int(configure_dict['Elevation_angle'])
simulation_end_time_s = int(configure_dict['simulation_end_time_s'])
time_step_ms = int(configure_dict['Time_step_ms'])
gen_data = configure_dict['satellite_network_dir_and_name']

isl_data_rate_megabit_per_s = float(configure_dict['isl_data_rate_megabit_per_s'])
gsl_data_rate_megabit_per_s = float(configure_dict['gsl_data_rate_megabit_per_s'])
isl_max_queue_size_pkts = int(configure_dict['isl_max_queue_size_pkts'])
gsl_max_queue_size_pkts = int(configure_dict['gsl_max_queue_size_pkts'])

satellite_network_dir = configure_dict['satellite_network_dir_and_name']
satellite_network_routes_dir = os.path.join(satellite_network_dir, satellite_network_dir, ) \
                               + '_isls_plus_grid_twostation_algorithm_free_one_only_over_isls/dynamic_state_{}ms_for_{}s'.format(
    time_step_ms, simulation_end_time_s)

# Considering an elevation angle of 30 degrees; possible values [1]: 20(min)/30/35/45
SATELLITE_CONE_RADIUS_M = ALTITUDE_M / math.tan(math.radians(elevation_angle))

MAX_GSL_LENGTH_M = math.sqrt(math.pow(SATELLITE_CONE_RADIUS_M, 2) + math.pow(ALTITUDE_M, 2))

# ISLs are not allowed to dip below 80 km altitude in order to avoid weather conditions
# MAX_ISL_LENGTH_M = 2 * math.sqrt(math.pow(EARTH_RADIUS + ALTITUDE_M, 2) - math.pow(EARTH_RADIUS + 80000, 2))
# MAX_ISL_LENGTH_M = 8000000

# def add_flow_table_from_fstate(satellite_network_routes_dir):
#     route_dir =

ground_dpid_list = [NUM_ORBS * NUM_SATS_PER_ORB + 1, NUM_ORBS * NUM_SATS_PER_ORB + 2]


class Mytopo(Topo):
    def __init__(self, enable_verbose_logs=False, **opts):
        super(Mytopo, self).__init__(self, **opts)

        self.enable_verbose_logs = enable_verbose_logs

        # Graphs
        self.graphs_sat_net_graph_only_satellites_with_isls = nx.Graph()
        self.graphs_sat_net_graph_all_with_only_gsls = nx.Graph()
        #####################################################################
        # mininet switches and host dict
        sat_net_switches_all_with_only_gsls = {}
        Hosts_On_Ground = {}
        # interfaces info
        self.total_num_isls = 0
        self.num_isls_per_sat = []
        self.sat_neighbor_to_if = {}

        sat_info = read_tles(gen_data)
        # Dictionary:{
        # "n_orbits": n_orbits,
        # "n_sats_per_orbit": n_sats_per_orbit,
        # "num_of_all_satellite": n_orbits * n_sats_per_orbit,
        # "epoch": epoch,
        # "satellites":satellites
        # }
        ground_stations = read_ground_stations_extended(gen_data)
        satellites = sat_info['satellites']
        epoch = sat_info['epoch']
        time = epoch + 0 * u.day

        # graph Information
        for i in range(len(satellites)):
            self.graphs_sat_net_graph_only_satellites_with_isls.add_node(i)
        for i in range(len(satellites) + len(ground_stations)):
            self.graphs_sat_net_graph_all_with_only_gsls.add_node(i)

        isl_list = read_isls(gen_data, sat_info['num_of_all_satellite'])

        self.num_isls_per_sat = [0] * len(satellites)
        for (a, b) in isl_list:
            sat_distance_m = distance_m_between_satellites(satellites[a], satellites[b], str(epoch), str(time))
            # if sat_distance_m > MAX_ISL_LENGTH_M:
            #     raise ValueError(
            #         "The distance between two satellites (%d and %d) "
            #         "with an ISL exceeded the maximum ISL length (%.2fm > %.2fm at t=%dns)"
            #         % (a, b, sat_distance_m, MAX_ISL_LENGTH_M, time)
            #     )

            delay = round(sat_distance_m / light_speed, 4) * 1000
            # print("\n-->delay--->", delay)

            self.graphs_sat_net_graph_only_satellites_with_isls.add_edge(a, b, weight=delay)
            self.graphs_sat_net_graph_all_with_only_gsls.add_edge(a, b, weight=delay)

            # Interface mapping of ISLs
            self.sat_neighbor_to_if[(a, b)] = self.num_isls_per_sat[a]
            self.sat_neighbor_to_if[(b, a)] = self.num_isls_per_sat[b]
            self.num_isls_per_sat[a] += 1
            self.num_isls_per_sat[b] += 1
            self.total_num_isls += 1

        if self.enable_verbose_logs:
            print("  > Total ISLs............. " + str(len(isl_list)))
            print("  > Min. ISLs/satellite.... " + str(np.min(self.num_isls_per_sat)))
            print("  > Max. ISLs/satellite.... " + str(np.max(self.num_isls_per_sat)))

        #################################

        # Calculate shortest path distances
        if self.enable_verbose_logs:
            print("  > Calculating Floyd-Warshall for graph without ground-station relays")
        # (Note: Numpy has a deprecation warning here because of how networkx uses matrices)
        dist_sat_net_without_gs = nx.floyd_warshall_numpy(self.graphs_sat_net_graph_only_satellites_with_isls)

        adj_sats_list = {}

        # for time_since_epoch_ms in range(0, simulation_end_time_s, time_step_ms):
        for time_since_epoch_ms in [0]:

            time = epoch + time_since_epoch_ms * u.ms
            if self.enable_verbose_logs:
                print('\n\n')
                print("  > Epoch.................. " + str(epoch))
                print("  > Time since epoch....... " + str(time_since_epoch_ms) + " ms")
                print("  > Absolute time.......... " + str(time))

            ground_station_satellites_in_range = []
            for ground_station in ground_stations:
                # Find satellites in range
                satellites_in_range = []
                for sid in range(len(satellites)):
                    distance_m = distance_m_ground_station_to_satellite(
                        ground_station,
                        satellites[sid],
                        str(epoch),
                        str(time)
                    )
                    if distance_m <= MAX_GSL_LENGTH_M:
                        satellites_in_range.append((distance_m, sid))
                        # graph info
                        delay = round(distance_m / light_speed, 4) * 1000
                        # print("\ngs2sat---->  ", delay)
                        self.graphs_sat_net_graph_all_with_only_gsls.add_edge(sid,
                                                                              len(satellites) + ground_station["gid"],
                                                                              weight=delay)

                satellites_in_range = sorted(satellites_in_range)

                ground_station_satellites_in_range.append(satellites_in_range)

            if self.enable_verbose_logs:
                print('-------------------------------------')
                print(" ----> ground_station_satellites_in_range ")
                print(ground_station_satellites_in_range)

            ground_fstate_dict = calculate_fstate_shortest_path_without_gs_relaying(
                satellites,
                ground_stations,
                dist_sat_net_without_gs,
                ground_station_satellites_in_range,
                enable_verbose_logs=False)



            for src_ground_id, des_ground_id in ground_fstate_dict:

                adj_satellite_id = ground_fstate_dict.get((src_ground_id, des_ground_id))
                adj_sats_list.setdefault((src_ground_id, des_ground_id), [])
                if adj_satellite_id not in adj_sats_list[(src_ground_id, des_ground_id)]:
                    adj_sats_list[(src_ground_id, des_ground_id)].append(adj_satellite_id)
                    gsl_distance_m = distance_m_ground_station_to_satellite(
                        ground_stations[src_ground_id - len(satellites)],
                        satellites[adj_satellite_id],
                        str(epoch),
                        str(time)
                    )
                    gsl_delay = round(gsl_distance_m / light_speed, 4) * 1000

                    info('add ground-sate links')
                    # print(sat_net_switches_all_with_only_gsls[src_ground_id + 1], sat_net_switches_all_with_only_gsls[adj_satellite_id + 1])
                    # add gsl link
                    self.addLink(sat_net_switches_all_with_only_gsls[src_ground_id + 1],
                                 sat_net_switches_all_with_only_gsls[adj_satellite_id + 1],
                                 bw=gsl_data_rate_megabit_per_s, delay=str(gsl_delay) + 'ms',
                                 max_queue_size=gsl_max_queue_size_pkts)

        # add ground host

        for i in range(1, len(ground_stations) + 1):
            gs_switch_name = 'g{}'.format(i)
            Hosts_On_Ground[i] = self.addHost(gs_switch_name, ip='10.0.{}.{}'.format((len(satellites) + i) // 255,
                                                                                     (i + len(satellites)) % 255))
            ground_id = len(satellites) + i
            self.addLink(Hosts_On_Ground[i], sat_net_switches_all_with_only_gsls[ground_id])


def read_tles(gen_data):
    """
    Read a constellation of satellites from the TLES file.

    :param filename_tles:                    Filename of the TLES (typically /path/to/tles.txt)

    :return: Dictionary:{
        "n_orbits": n_orbits,
        "n_sats_per_orbit": n_sats_per_orbit,
        "num_of_all_satellite": n_orbits * n_sats_per_orbit,
        "epoch": epoch,
        "satellites":satellites
        }
    """

    sat_data = os.listdir(gen_data)
    satellites = []
    with open(os.path.join(gen_data, sat_data[0]) + '/tles.txt', 'r') as f:
        n_orbits, n_sats_per_orbit = [int(n) for n in f.readline().split()]
        universal_epoch = None

        i = 0
        for tles_line_1 in f:
            tles_line_2 = f.readline()
            tles_line_3 = f.readline()

            # Retrieve name and identifier
            name = tles_line_1
            sid = int(name.split()[1])
            if sid != i:
                raise ValueError("Satellite identifier is not increasing by one each line")
            i += 1

            # Fetch and check the epoch from the TLES data
            # In the TLE, the epoch is given with a Julian data of yyddd.fraction
            # ddd is actually one-based, meaning e.g. 18001 is 1st of January, or 2018-01-01 00:00.
            # As such, to convert it to Astropy Time, we add (ddd - 1) days to it
            # See also: https://www.celestrak.com/columns/v04n03/#FAQ04
            epoch_year = tles_line_2[18:20]
            epoch_day = float(tles_line_2[20:32])
            epoch = Time("20" + epoch_year + "-01-01 00:00:00", scale="tdb") + (epoch_day - 1) * u.day
            if universal_epoch is None:
                universal_epoch = epoch
            if epoch != universal_epoch:
                raise ValueError("The epoch of all TLES must be the same")

            # Finally, store the satellite information
            satellites.append(ephem.readtle(tles_line_1, tles_line_2, tles_line_3))

    return {
        "n_orbits": n_orbits,
        "n_sats_per_orbit": n_sats_per_orbit,
        "num_of_all_satellite": n_orbits * n_sats_per_orbit,
        "epoch": epoch,
        "satellites": satellites
    }


def read_isls(gen_filename, num_satellites):
    """
    Read ISLs file into a list of undirected edges

    :param filename_isls:  Filename of ISLs (typically /path/to/isls.txt)
    :param num_satellites: Number of satellites (to verify indices)

    :return: List of all undirected ISL edges
    """
    isls_list = []

    info = os.listdir(gen_filename)

    with open(os.path.join(gen_filename, info[0]) + '/isls.txt', 'r') as f:
        isls_set = set()
        for line in f:
            line_spl = line.split()
            a = int(line_spl[0])
            b = int(line_spl[1])

            # Verify the input
            if a >= num_satellites:
                raise ValueError("Satellite does not exist: %d" % a)
            if b >= num_satellites:
                raise ValueError("Satellite does not exist: %d" % b)
            if b <= a:
                raise ValueError("The second satellite index must be strictly larger than the first")
            if (a, b) in isls_set:
                raise ValueError("Duplicate ISL: (%d, %d)" % (a, b))
            isls_set.add((a, b))

            # Finally add it to the list
            isls_list.append((a, b))

    return isls_list


def distance_m_between_satellites(sat1, sat2, epoch_str, date_str):
    """
    Computes the straight distance between two satellites in meters.

    :param sat1:       The first satellite
    :param sat2:       The other satellite
    :param epoch_str:  Epoch time of the observer (string)
    :param date_str:   The time instant when the distance should be measured (string)

    :return: The distance between the satellites in meters
    """

    # Create an observer somewhere on the planet
    observer = ephem.Observer()
    observer.epoch = epoch_str
    observer.date = date_str
    observer.lat = 0
    observer.lon = 0
    observer.elevation = 0

    # Calculate the relative location of the satellites to this observer
    sat1.compute(observer)
    sat2.compute(observer)

    # Calculate the angle observed by the observer to the satellites (this is done because the .compute() calls earlier)
    angle_radians = float(repr(ephem.separation(sat1, sat2)))

    # Now we have a triangle with three knows:
    # (1) a = sat1.range (distance observer to satellite 1)
    # (2) b = sat2.range (distance observer to satellite 2)
    # (3) C = angle (the angle at the observer point within the triangle)
    #
    # Using the formula:
    # c^2 = a^2 + b^2 - 2 * a * b * cos(C)
    #
    # This gives us side c, the distance between the two satellites
    return math.sqrt(sat1.range ** 2 + sat2.range ** 2 - (2 * sat1.range * sat2.range * math.cos(angle_radians)))


def distance_m_ground_station_to_satellite(ground_station, satellite, epoch_str, date_str):
    """
    Computes the straight distance between a ground station and a satellite in meters

    :param ground_station:  The ground station
    :param satellite:       The satellite
    :param epoch_str:       Epoch time of the observer (ground station) (string)
    :param date_str:        The time instant when the distance should be measured (string)

    :return: The distance between the ground station and the satellite in meters
    """

    # Create an observer on the planet where the ground station is
    observer = ephem.Observer()
    observer.epoch = epoch_str
    observer.date = date_str
    observer.lat = str(ground_station["latitude_degrees_str"])  # Very important: string argument is in degrees.
    observer.lon = str(ground_station["longitude_degrees_str"])  # DO NOT pass a float as it is interpreted as radians
    observer.elevation = ground_station["elevation_m_float"]

    # Compute distance from satellite to observer
    satellite.compute(observer)

    # Return distance
    return satellite.range


def read_ground_stations_extended(gen_data):
    """
    Reads ground stations from the input file.

    :param filename_ground_stations_basic: Filename of ground stations basic (typically /path/to/ground_stations.txt)

    :return: List of ground stations
    """

    constellation_info_list = os.listdir(gen_data)

    ground_stations_extended = []
    gid = 0

    for i in constellation_info_list:
        with open(os.path.join(gen_data, i) + '/ground_stations.txt', 'r') as f:
            for line in f:
                split = line.split(',')
                if len(split) != 8:
                    raise ValueError("Extended ground station file has 8 columns: " + line)
                if int(split[0]) != gid:
                    raise ValueError("Ground station id must increment each line")
                ground_station_basic = {
                    "gid": gid,
                    "name": split[1],
                    "latitude_degrees_str": split[2],
                    "longitude_degrees_str": split[3],
                    "elevation_m_float": float(split[4]),
                    "cartesian_x": float(split[5]),
                    "cartesian_y": float(split[6]),
                    "cartesian_z": float(split[7]),
                }
                ground_stations_extended.append(ground_station_basic)
                gid += 1
    return ground_stations_extended


def calculate_fstate_shortest_path_without_gs_relaying(
        satellites,
        ground_stations,
        dist_sat_net_without_gs,
        ground_station_satellites_in_range,
        enable_verbose_logs=False
):
    # Forwarding state
    fstate = {}
    # Satellites to ground stations
    # From the satellites attached to the destination ground station,
    # select the one which promises the shortest path to the destination ground station (getting there + last hop)
    dist_satellite_to_ground_station = {}
    for curr in range(len(satellites)):
        for dst_gid in range(len(ground_stations)):
            dst_gs_node_id = len(satellites) + dst_gid

            # Among the satellites in range of the destination ground station,
            # find the one which promises the shortest distance
            possible_dst_sats = ground_station_satellites_in_range[dst_gid]
            possibilities = []
            for b in possible_dst_sats:
                if not math.isinf(dist_sat_net_without_gs[(curr, b[1])]):  # Must be reachable
                    possibilities.append(
                        (
                            dist_sat_net_without_gs[(curr, b[1])] + b[0],
                            b[1]
                        )
                    )
            possibilities = list(sorted(possibilities))

            # By default, if there is no satellite in range for the

            distance_to_ground_station_m = float("inf")
            if len(possibilities) > 0:
                dst_sat = possibilities[0][1]
                distance_to_ground_station_m = possibilities[0][0]
            # In any case, save the distance of the satellite to the ground station to re-use
            # when we calculate ground station to ground station forwarding
            dist_satellite_to_ground_station[(curr, dst_gs_node_id)] = distance_to_ground_station_m

        # Ground stations to ground stations
        # Choose the source satellite which promises the shortest path
    for src_gid in range(len(ground_stations)):
        for dst_gid in range(len(ground_stations)):
            if src_gid != dst_gid:
                src_gs_node_id = len(satellites) + src_gid
                dst_gs_node_id = len(satellites) + dst_gid

                # Among the satellites in range of the source ground station,
                # find the one which promises the shortest distance
                possible_src_sats = ground_station_satellites_in_range[src_gid]

                if enable_verbose_logs:
                    print('-----------------------')
                    print('----possible_src_sats----')
                    print(possible_src_sats)

                possibilities = []
                for a in possible_src_sats:
                    best_distance_offered_m = dist_satellite_to_ground_station[(a[1], dst_gs_node_id)]
                    if not math.isinf(best_distance_offered_m):
                        possibilities.append(
                            (
                                a[0] + best_distance_offered_m,
                                # distance between two stations #(51, 100): 725104.4375, (51, 101): 15010708.41926724, the two value is addde
                                a[1]
                            )
                        )
                possibilities = sorted(possibilities)

                if enable_verbose_logs:
                    print('-------------------------------')
                    print("dist_satellite_to_ground_station")
                    print(possibilities)

                # By default, if there is no satellite in range for one of the
                # ground stations, it will be dropped (indicated by -1)
                # next_hop_decision = (-1, -1, -1)
                if len(possibilities) > 0:
                    src_sat_id = possibilities[0][1]
                else:
                    print('current snapshots no gsl')
                    src_sat_id = -1

                fstate[(src_gs_node_id, dst_gs_node_id)] = src_sat_id

    return fstate


def cal_access_sats_each_time_step(ground_station_satellites_in_range) -> list:
    postions_sat_parsed = []
    for ground_station in ground_station_satellites_in_range:
        # parse num_plan and num_sat_in_plane
        # mini_dist = ground_station[0][0]
        temp = []
        for dist, id in ground_station:
            temp.append((id // NUM_SATS_PER_ORB, id % NUM_SATS_PER_ORB, dist))
        postions_sat_parsed.append(temp)

    # # def select_minimal_hop(postions_sat_parsed):
    sat_two_final_selected = []

    # minimum distance two satellites
    # sat0_orbit = 0
    # sat0_num_of_plane = 0
    # sat1_orbit = 0
    # sat1_num_of_plane = 0

    minimal_mesh_grid = 65535
    for a, b, dist0 in postions_sat_parsed[0]:
        for c, d, dist1 in postions_sat_parsed[1]:
            rows_nums = min(get_positive_int((a - c)), NUM_ORBS - get_positive_int((a - c)))
            column = min(get_positive_int((b - d)), NUM_SATS_PER_ORB - get_positive_int((b - d)))
            num_grid = rows_nums + column
            if get_positive_int(num_grid) < minimal_mesh_grid:
                sat0_orbit = a
                sat0_num_of_plane = b
                final_row = rows_nums
                sat0_to_gs_dist = dist0

                sat1_orbit = c
                sat1_num_of_plane = d
                sat1_to_gs_dist = dist1
                minimal_mesh_grid = get_positive_int(num_grid)
            elif num_grid == minimal_mesh_grid:
                if rows_nums > final_row:
                    # if dist0 + dist1 < sat0_to_gs_dist + sat1_to_gs_dist:
                    sat0_orbit = a
                    sat0_num_of_plane = b
                    final_row = rows_nums
                    sat0_to_gs_dist = dist0

                    sat1_orbit = c
                    sat1_num_of_plane = d
                    sat1_to_gs_dist = dist1

    sat_two_final_selected.append((sat0_orbit * NUM_SATS_PER_ORB + sat0_num_of_plane))
    sat_two_final_selected.append((sat1_orbit * NUM_SATS_PER_ORB + sat1_num_of_plane))
    return sat_two_final_selected


def get_positive_int(ne_or_po_num: int):
    if ne_or_po_num < 0:
        ne_or_po_num = - ne_or_po_num
    return ne_or_po_num


class Change_delay_for_link(threading.Thread):
    def __init__(self, gen_data, net, simulation_end_time_s, time_step_ms):
        super(Change_delay_for_link, self).__init__()
        sats_info = read_tles(gen_data)
        ground_stations = read_ground_stations_extended(gen_data)

        self.net = net
        self.simulation_end_time_s = simulation_end_time_s
        self.time_step_ms = time_step_ms
        # self.sat_neighbor_to_if = sat_neighbor_to_if
        self.sat_info = sats_info
        self.ground_stations = ground_stations

    def run(self):

        satellites = self.sat_info['satellites']
        epoch = self.sat_info['epoch']

        current_time = 0

        print(threading.currentThread().name, 'already')
        print('gs to host flow table')
        add_gs2host_link(ground_dpid_list, add_flowentry_url, post_data_ip, post_data_arp)
        while current_time < self.simulation_end_time_s * 1000:

            fstate_file_name = 'fstate_{}.txt'.format(current_time * 1000000)
            print('fstate file name ', fstate_file_name)
            add_flow(satellite_network_routes_dir, fstate_file_name, time_step_ms)
            current_time += self.time_step_ms
            simulation_time = epoch + current_time * u.ms

            time.sleep(self.time_step_ms / 1000)
            print('\n change delay')
            print("  > Epoch.................. " + str(epoch))
            print("  > Time since epoch....... " + str(current_time) + " s")
            print("  > Absolute time.......... " + str(simulation_time))

            switch2satellites = self.net.switches
            links_sat = []
            for sat in switch2satellites:
                for intf in sat.intfList():
                    if intf.link and type(intf.link.intf1.node) == type(
                            intf.link.intf2.node):  # the link is between switch and switch

                        src_2_dst_node_ids = (int(intf.link.intf1.node.dpid, 16) - 1,
                                              int(intf.link.intf2.node.dpid, 16) - 1)  # 卫星编号从0开始， 交换机编号从1开始
                        src_2_dst_node_ids_reverse = (int(intf.link.intf2.node.dpid, 16) - 1,
                                                      int(intf.link.intf1.node.dpid, 16) - 1)  # 卫星编号从0开始， 交换机编号从1开始
                        # print('src_2_dst_node_ids----------->', src_2_dst_node_ids)
                        if src_2_dst_node_ids not in links_sat:
                            links_sat.append(src_2_dst_node_ids)
                            links_sat.append(src_2_dst_node_ids_reverse)

                            if src_2_dst_node_ids[0] < len(satellites) and src_2_dst_node_ids[1] < len(satellites):
                                distance_m = distance_m_between_satellites(satellites[src_2_dst_node_ids[0]],
                                                                           satellites[src_2_dst_node_ids[1]],
                                                                           str(epoch), str(simulation_time))

                            else:
                                gs_id = 0
                                sat_id = 0
                                if src_2_dst_node_ids[0] >= len(satellites):
                                    gs_id = src_2_dst_node_ids[0] - len(satellites)
                                    sat_id = src_2_dst_node_ids[1]
                                elif src_2_dst_node_ids[1] >= len(satellites):
                                    gs_id = src_2_dst_node_ids[1] - len(satellites)
                                    sat_id = src_2_dst_node_ids[0]

                                distance_m = distance_m_ground_station_to_satellite(
                                    self.ground_stations[gs_id],
                                    satellites[sat_id],
                                    str(epoch),
                                    str(simulation_time)
                                )

                            delay = round(distance_m / light_speed, 4) * 1000
                            intfs = [intf.link.intf1,
                                     intf.link.intf2]  # intfs[0] is source of link and intfs[1] is dst of link
                            intfs[0].config(delay=str(delay) + 'ms')
                            intfs[1].config(delay=str(delay) + 'ms')
                    # else:
                    #     print('\n <------>intf link ', intf.link)


# def manageLinks():
#     nodes = net.switches + net.hosts
#     print("nodes", nodes)
#     print("type node", type(nodes))
#     for node in nodes:
#         changeBandwith(node)
#
# def changeBandwith( node ):
#
#     print("node.intfList--->", node.intfList())
#     for intf in node.intfList(): # loop on interfaces of node
#         print('intf', intf)
#         if intf.link: # get link that connects to interface(if any)
#             newBW = 5
#             intfs = [ intf.link.intf1, intf.link.intf2 ] #intfs[0] is source of link and intfs[1] is dst of link
#             print('intfs', intfs)
#             intfs[0].config(bw=newBW, delay='10ms')
#             intfs[1].config(bw=newBW, delay='10ms')
#         else:
#             info( ' \n' )


def main():
    print('init customized topology')
    lion_topo = Mytopo(enable_verbose_logs=False)
    print('init net')
    net = Mininet(topo=lion_topo, controller=None, link=TCLink, switch=OVSKernelSwitch)
    print('add controller')
    net.addController("c0",
                      controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP,
                      port=6653)
    print('dynamic network')
    dynamic_topology = Change_delay_for_link(gen_data, net, simulation_end_time_s, time_step_ms)
    dynamic_topology.setDaemon(True)
    net.start()
    print('--------- net start ----------')
    dynamic_topology.start()
    # #VideoStreamingService(net)
    CLI(net)
    net.stop()


if __name__ == "__main__":
    main()


