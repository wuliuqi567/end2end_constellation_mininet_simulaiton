import math
from secrets import randbits
import networkx as nx

intf1 = 0
intf2 = 0
def my_calculate_fstate_shortest_path_without_gs_relaying(
        output_dynamic_state_dir,
        time_since_epoch_ns,
        num_satellites,
        num_ground_stations,
        sat_net_graph_only_satellites_with_isls,
        num_isls_per_sat,
        gid_to_sat_gsl_if_idx,
        ground_station_satellites_in_range_candidates,
        sat_neighbor_to_if,
        prev_fstate,
        enable_verbose_logs
):
    # Calculate shortest path distances
    # if enable_verbose_logs:
    #     print("  > Calculating Floyd-Warshall for graph without ground-station relays")
    # (Note: Numpy has a deprecation warning here because of how networkx uses matrices)
    # dist_sat_net_without_gs = nx.floyd_warshall_numpy(sat_net_graph_only_satellites_with_isls) #该函数返回一个任意两点间最短距离的矩阵
    global intf1, intf2
    for i in range(num_ground_stations):
        sat_net_graph_only_satellites_with_isls.add_node(num_satellites + i)

    # add edge for net
    for id, candidates_sat in enumerate(ground_station_satellites_in_range_candidates):

        ground_id = num_satellites + id
        # print('\n id = ', id, 'candidate_set', candidates_sat)
        # print('ground_id', ground_id)
        for dist, sat_idx in candidates_sat:
            sat_net_graph_only_satellites_with_isls.add_edge(sat_idx, ground_id, weight=dist)

    # Forwarding state
    fstate = {}

    # Now write state to file for complete graph
    output_filename = output_dynamic_state_dir + "/fstate_" + str(time_since_epoch_ns) + ".txt"
    hop_count_file = output_dynamic_state_dir + "/../hop_count_newd.csv"
    # if enable_verbose_logs:
    #     print("  > Writing forwarding state to: " + output_filename)
    with open(output_filename, "w+") as f_out:

        # minWPath_vs_vt = nx.dijkstra_path(sat_net_graph_only_satellites_with_isls, source=source_id, target=dest_id)

        # Ground stations to ground stations
        # Choose the source satellite which promises the shortest path
        for src_gid in range(num_ground_stations):
            for dst_gid in range(num_ground_stations):
                if src_gid != dst_gid:
                    src_gs_node_id = num_satellites + src_gid
                    dst_gs_node_id = num_satellites + dst_gid

                    minWPath_vs_vt = nx.dijkstra_path(sat_net_graph_only_satellites_with_isls, source=src_gs_node_id,
                                                      target=dst_gs_node_id)
                    # minWPath_vt_vs = nx.dijkstra_path(sat_net_graph_only_satellites_with_isls, source=dst_gs_node_id, target=src_gs_node_id)
                    minWPath_vs_vt_len = nx.dijkstra_path_length(sat_net_graph_only_satellites_with_isls,
                                                                 source=src_gs_node_id, target=dst_gs_node_id)
                    cal_write_hop2file(hop_count_file, len(minWPath_vs_vt) - 1)

                    print('\n >>>>minWPath_vs_vt-----', minWPath_vs_vt)
                    print('\n >>>>minWPath_vs_vt_len-----', round(minWPath_vs_vt_len / 3e8, 4))
                    # print('\n >>>>minWPath_vt_vs-----', minWPath_vt_vs)
                    next_hop_decision = (-1, -1, -1)
                    for curr_node in range(len(minWPath_vs_vt) - 1):
                        next_node = curr_node + 1
                        if minWPath_vs_vt[curr_node] == src_gs_node_id:

                            if prev_fstate and prev_fstate[(src_gs_node_id, dst_gs_node_id)] != minWPath_vs_vt[next_node]:
                                intf1 += 1

                            next_hop_decision = (
                                minWPath_vs_vt[next_node],
                                intf1,
                                num_isls_per_sat[minWPath_vs_vt[next_node]] + gid_to_sat_gsl_if_idx[src_gid]
                            )

                        elif minWPath_vs_vt[next_node] == dst_gs_node_id:

                            if minWPath_vs_vt[curr_node] == dst_gs_node_id:
                                if prev_fstate and prev_fstate[(minWPath_vs_vt[curr_node], dst_gs_node_id)] != minWPath_vs_vt[next_node]:
                                    intf2 += 1

                            next_hop_decision = (
                                dst_gs_node_id,
                                num_isls_per_sat[curr_node] + gid_to_sat_gsl_if_idx[dst_gid],
                                intf2
                            )

                        else:
                            next_hop_decision = (
                                minWPath_vs_vt[next_node],
                                sat_neighbor_to_if[(minWPath_vs_vt[curr_node], minWPath_vs_vt[next_node])],
                                sat_neighbor_to_if[(minWPath_vs_vt[next_node], minWPath_vs_vt[curr_node])]
                            )
                        # if not prev_fstate or prev_fstate[(minWPath_vs_vt[curr_node], dst_gs_node_id)] != next_hop_decision:

                        f_out.write("%d,%d,%d,%d,%d\n" % (
                            minWPath_vs_vt[curr_node],
                            dst_gs_node_id,
                            next_hop_decision[0],
                            next_hop_decision[1],
                            next_hop_decision[2]
                        ))

                        fstate[(minWPath_vs_vt[curr_node], dst_gs_node_id)] = next_hop_decision

    # Finally return result
    return fstate


def cal_write_hop2file(file, hop_count):
    print(' > begin write hop count \n ')
    with open(file, "a") as f:
        f.write(str(hop_count))
        f.write('\n')





