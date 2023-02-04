from __future__ import annotations
from typing import TYPE_CHECKING, Any, Type, Union, Optional
import copy
import math
import time
if TYPE_CHECKING:
    from tasks.task import Task
    from modules.py_unit import PyUnit
    from agents.basic_agent import BasicAgent


from library import MapTools, Point2DI, Point2D, Color, BaseLocation

class MapDecomposer:

    def __init__(self, agent: BasicAgent):
        self.k = 0
        self.agent = agent
        self.depth_map = [ [-1]*self.agent.map_tools.width for i in range(self.agent.map_tools.height)]
        self.zone_map = copy.deepcopy(self.depth_map)
        self.gate_cluster_map = []
        self.depth_tile_list = []
        self.not_walkable_tiles = set()
        self.base_coordinates = [base_coord.depot_position for base_coord in self.agent.base_location_manager.base_locations]
        self.chokepoints = []
        self.mineral_locations = [(base_coord.minerals) for base_coord in
                                  self.agent.base_location_manager.base_locations]
        self.mineral_coord = [mineral.tile_position for mineral_list in self.mineral_locations for mineral in mineral_list]
        self.algo_1_and_5()
        self.algo_2()
        self.chokepoints.append(Point2DI(116, 43))
        self.choke_point_coords = self.map_zone_to_chokepoints()


    '''Get neighbors of coordinate. Choose whichever distance you want.'''
    def get_octile_coordinates(self, distance: int, x: int, y: int) -> list:
        tile = (x,y)
        octile_coordinates = []
        for x in range(-distance, distance+1):
             for y in range(-distance, distance+1):
                 if -distance in (x,y) or distance in (x,y):
                      octile_coordinates.append((tile[0]+x, tile[1]+y))
        return octile_coordinates

    '''Uses another depth mapping calculation than algo_1_and_4, which was my first try. This sets depth value as a floored log value.
       The depths will range from 1-3, where 1 being un-walkable tile. This is what ultimately was used.'''

    def algo_1_and_5(self):
        # Loop over real map coords and put proper depth_value to the depth_map coord that corresponds to maps
        # spot of that coord.
        for x in range(0, self.agent.map_tools.width):
            for y in range(0, self.agent.map_tools.height):

                curr_depth = 0
                wall_found = False
                found_first_wall = False
                wall_tile_found_times = 0
                wall_threshhold = 0
                while not wall_found:
                    octile_coords = self.get_octile_coordinates(curr_depth, x, y)
                    for coord in octile_coords:
                        if not self.agent.map_tools.is_walkable(coord[0], coord[1]):
                            self.not_walkable_tiles.add(Point2DI(coord[0], coord[1]))
                            wall_tile_found_times += 1
                            if found_first_wall == False:
                                wall_threshhold = (50 - curr_depth) / 28 + 1
                                found_first_wall = True

                            elif wall_tile_found_times >= wall_threshhold:

                                self.depth_map[self.agent.map_tools.height - 1 - y][x] = math.floor(
                                    math.log2(curr_depth + 1))
                                ## Also add to depth_tile_list
                                if len(self.depth_tile_list) >= (math.floor(math.log2(curr_depth + 1)) + 1):
                                    if (x, y) not in self.depth_tile_list[math.floor(math.log2(curr_depth + 1))]:
                                        self.depth_tile_list[math.floor(math.log2(curr_depth + 1))].append((x, y))
                                else:
                                    if (x, y) not in self.depth_tile_list:
                                        self.depth_tile_list.append([(x, y)])
                                wall_found = True

                    curr_depth += 1

        ## This part kills alot of efficiency.
        for i in range(len(self.depth_tile_list) - 2, 1, -1):
            self.sort_depth_tile_list_3(i)



    ''' Flood fill algo. Gives zone numbers to coordinates depending on how many neighboring coordinates
    have or havent different zone numbers. If no neighbor has zone number, mark coordinate as new zone. If theres only one
    zone number neighboring, inherit that zone number. If theres more than one zone number neighboring, we are between
    two zones and gets marked as gate tile.'''
    def algo_2(self):
        curr_water_lvl = len(self.depth_tile_list)  -1
        k = 0
        while curr_water_lvl > 1:
            for x,y in self.depth_tile_list[curr_water_lvl]:
                neighbors = self.get_octile_coordinates(1, x, y)
                labels = set()
                amount_labeled = 0
                for i,j in neighbors:
                    grid_coord = (self.agent.map_tools.height - 1 - j, i)
                    # -1 in grid means no label on tile yet
                    if self.zone_map[grid_coord[0]][grid_coord[1]] == -1:
                        continue
                    labels.add(self.zone_map[grid_coord[0]][grid_coord[1]])
                    amount_labeled += 1

                if amount_labeled > 1:
                    if len(labels) > 1:
                        self.gate_cluster_map.append((x,y))
                    self.zone_map[self.agent.map_tools.height - 1 - y][x] = next(iter(labels))
                elif amount_labeled == 1:
                    self.zone_map[self.agent.map_tools.height - 1 - y][x] = next(iter(labels))
                else:
                    k += 1
                    self.zone_map[self.agent.map_tools.height - 1 - y][x] = k

            curr_water_lvl -= 1


        ''' Turn gate tiles into proper chokepoints by constraining them to be adjacent to wall, have no coordinate
        adjacent to it already been set as a proper chokepoint, and be in a set distance away from closest mineral
        (could do this against base position aswell if wanted to). Simplified version of algo 3.'''
        for gate_tile in self.gate_cluster_map:
            neighbors = self.get_octile_coordinates(1, gate_tile[0], gate_tile[1])
            for x,y in neighbors:
                if self.zone_map[self.agent.map_tools.height - 1 - y][x] == -1 and self.lowest_distance_to_mineral(gate_tile[0], gate_tile[1]) > 10\
                        and not self.is_neighbor_gate(neighbors):
                    self.zone_map[self.agent.map_tools.height - 1 - gate_tile[1]][gate_tile[0]] = -2
                    self.chokepoints.append(Point2DI(gate_tile[0], gate_tile[1]))


    ''' Sorts the depth tile lists so that the coordinates in the parent depth tile list (i.e lower
       depth value) are in the order like a ring around a child depth tile. Use several rings for more coverage.
       This is needed when flood-filling so it correctly inherits zone numbers.
       I.e if (10,10) had depth 3 and next depth to examine is 2. We want to go (9,9), (9, 10), (9, 11), (10,9).. as
       ring 1, then (8,8), (8,9)... as ring 2, etc. This ensures proper inheritance of zone values. Best detailed
       when using 6 rings, 3 brings some noise but does the job nonetheless (and is quicker).'''
    def sort_depth_tile_list_3(self, sort_number):
        adjacent = sort_number + 1
        result = []
        left_over = self.depth_tile_list[sort_number]
        first_ring = []
        second_ring = []
        third_ring = []

        for x, y in self.depth_tile_list[adjacent]:
            first_ring_neighbor = self.get_octile_coordinates(1, x, y)
            second_ring_neighbor = self.get_octile_coordinates(2, x, y)
            third_ring_neighbor = self.get_octile_coordinates(3, x, y)

            for neighbor1 in first_ring_neighbor:
                if neighbor1 in self.depth_tile_list[sort_number]:
                    first_ring.append(neighbor1)
                    left_over.remove(neighbor1)
                    continue
            for neighbor2 in second_ring_neighbor:
                if neighbor2 in self.depth_tile_list[sort_number]:
                    second_ring.append(neighbor2)
                    left_over.remove(neighbor2)
                    continue

            for neighbor3 in third_ring_neighbor:
                if neighbor3 in self.depth_tile_list[sort_number]:
                    third_ring.append(neighbor3)
                    left_over.remove(neighbor3)
                    continue

            result += first_ring + second_ring + third_ring

            first_ring = []
            second_ring = []
            third_ring = []

        rest = self.sort_left_over(left_over)
        result += rest
        self.depth_tile_list[sort_number] = result


    ''' Sort left over tiles (those that arent in the "rings" around a coordinate. Sorting them
    so instead of being random coordinates, they are (trying) to be in a neighboring order.'''

    def sort_left_over(self, left_over_list):

        result = []
        while left_over_list:
            x, y = left_over_list[0]
            result.append((x, y))
            left_over_list.remove((x, y))

            neighbors = self.get_octile_coordinates(1, x, y)

            for neighbor in neighbors:
                if neighbor in left_over_list:
                    result.append(neighbor)
                    left_over_list.remove(neighbor)

        result += left_over_list

        return result

    """ Get distance between two coordinates """
    def get_distance_between(self, this, other):
        return math.sqrt((this.x - other.x)**2 + (this.y - other.y)**2)

    """ Returns lowest distance from coordinate to mineral """
    def lowest_distance_to_mineral(self, x, y):
        this = Point2DI(x,y)
        result = math.inf
        for mineral in self.mineral_coord:
            if self.get_distance_between(this, mineral) < result:
                result = self.get_distance_between(this, mineral)
        return result

    """ Checks if neighbor is gate tile """
    def is_neighbor_gate(self, neighbors):
        zone_numbers = [self.zone_map[self.agent.map_tools.height - 1 - y][x] for x,y in neighbors]
        return -2 in zone_numbers


    """ Maps base coordinates to choke points as a dict """
    def map_zone_to_chokepoints(self):
        result = {}
        temp_choke = [] #holder of chokepoints
        for base in self.base_coordinates:
            for chokepoint in self.chokepoints:
                # Somehow I have dupliacte chokepoitns in self.chokepoints??
                if chokepoint not in temp_choke and self.can_reach(base, chokepoint):
                    temp_choke.append(chokepoint)
            # Done for one base, add to dict
            result[base] = temp_choke
            temp_choke = []
        return result

    ''' Checks whether you can reach from a base coordinate to a choke coordinate without hitting a wall.
    If so, it means that this chokepoint is related to this zone. Do this by trying to walk dx then dy and vice versa.'''
    def can_reach(self, base: Point2DI, chokepoint : Point2DI) -> bool:
        delta_x = chokepoint.x - base.x
        delta_y = chokepoint.y - base.y
        if abs(delta_x) >25 or abs(delta_y) > 25:
            return False
        succeeded_through_first = True
        # Path 1. dx then dy
        dx = [(base.x + i, base.y) for i in range(0, delta_x+1 if delta_x >= 0 else delta_x-1, 1 if delta_x >= 0
                                                        else -1)]
        dy = [(base.x + delta_x, base.y + i) for i in range(0, delta_y+1 if delta_y >= 0 else delta_y-1, 1 if delta_y >=
                                                            0 else -1)]

        dxdy = dx + dy
        for coord in dxdy:
            if not type(coord) == Point2DI:
                coord = Point2DI(coord[0], coord[1])
            if coord in self.not_walkable_tiles:
                succeeded_through_first = False
                break
        if succeeded_through_first:
            return True

        # Path 1 didnt work, try Path 2. dy then dx

        dy2 = [(base.x, base.y+i) for i in range(0, delta_y+1 if delta_y >=0 else delta_y - 1, 1 if delta_y >=0 else -1)]
        dx2 = [(base.x + i, base.y + delta_y) for i in range(0, delta_x+1 if delta_x >= 0 else delta_x - 1, 1 if delta_x >= 0
                                                             else -1)]

        dydx = dy2 + dx2
        for coord in dydx:
            if not type(coord) == Point2DI:
                coord = Point2DI(coord[0], coord[1])
            if coord in self.not_walkable_tiles:
                # No luck here either, return False
                return False

        # You got through path 2
        return True
