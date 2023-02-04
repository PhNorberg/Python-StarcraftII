from __future__ import annotations
from typing import TYPE_CHECKING, Any, Type, Union, Optional
import copy
import math
import random
import time
if TYPE_CHECKING:
    from tasks.task import Task
    from modules.py_unit import PyUnit
    from agents.basic_agent import BasicAgent

from modules.py_unit import PyUnit
from typing import Optional
from tasks import build
from library import UnitType, Unit, UNIT_TYPEID, Point2D, Point2DI, BaseLocation, BaseLocationManager, BuildingPlacer,PLAYER_SELF
from modules.py_building_placer import PyBuildingPlacer
from modules.base_data import BaseData
class BuildingPlacerEvaluator(PyBuildingPlacer):
    """ Building placemenent evaluator determines where to place next building that is going to be built. """
    def __init__(self, agent, mapdecomposor):
        self.agent = agent
        self.map_decomposer = mapdecomposor
        self.last_suggested_def = []
        self.last_suggested_off = []
        self.occupied_mid_points = []
        self.upgrades = self.init_upgrades_dict()
        self.defensive = self.init_defensive_dict()
        self.offensive = self.init_offensive_dict()
        self.addons = self.init_addons_dict()
        self.addonable_buildings = self.init_addonable_list()
        self.locations = self.agent.base_location_manager.base_locations
        ## These are meant to be reserved when creating factory/barrack/starport to make room for addon.
        ## Use this list to quickly find where to put it when asked to build addon.
        self.reserved_tiles = []
        # BaseData objects hold information about each base, create a list of these objects in this guy, with the
        # help of data gained by map decomposor.
        self.base_data_objects = [BaseData(self.map_decomposer, Point2DI(59, 28)), BaseData(self.map_decomposer, Point2DI(125, 137)),
                                  BaseData(self.map_decomposer, Point2DI(60, 96)), BaseData(self.map_decomposer, Point2DI(93, 39)),
                                  BaseData(self.map_decomposer, Point2DI(126, 56)),
                                  BaseData(self.map_decomposer, Point2DI(58, 128)),
                                  BaseData(self.map_decomposer, Point2DI(86, 114)),
                                  BaseData(self.map_decomposer, Point2DI(92, 139)),
                                  BaseData(self.map_decomposer, Point2DI(125, 30)),
                                  BaseData(self.map_decomposer, Point2DI(26, 137)),
                                  BaseData(self.map_decomposer, Point2DI(25, 111)),
                                  BaseData(self.map_decomposer, Point2DI(26, 81)),
                                  BaseData(self.map_decomposer, Point2DI(125, 86)),
                                  BaseData(self.map_decomposer, Point2DI(91, 71)),
                                  BaseData(self.map_decomposer, Point2DI(65, 53)),
                                  BaseData(self.map_decomposer, Point2DI(26, 30)),
                                  ]
        self.addon_tiles_placed = []

    def init_upgrades_dict(self):
        return { UnitType(UNIT_TYPEID.TERRAN_ORBITALCOMMAND, self.agent) : UnitType(UNIT_TYPEID.TERRAN_ORBITALCOMMAND, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_PLANETARYFORTRESS, self.agent) : UnitType(UNIT_TYPEID.TERRAN_PLANETARYFORTRESS, self.agent).tile_height ,

                 }

    def init_addons_dict(self):
       return { UnitType(UNIT_TYPEID.TERRAN_TECHLAB, self.agent) : UnitType(UNIT_TYPEID.TERRAN_TECHLAB, self.agent).tile_height,
                UnitType(UNIT_TYPEID.TERRAN_REACTOR, self.agent) : UnitType(UNIT_TYPEID.TERRAN_REACTOR, self.agent).tile_height
                }

    def init_defensive_dict(self):
        return { UnitType(UNIT_TYPEID.TERRAN_COMMANDCENTER, self.agent) : UnitType(UNIT_TYPEID.TERRAN_COMMANDCENTER, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_SUPPLYDEPOT, self.agent) : UnitType(UNIT_TYPEID.TERRAN_SUPPLYDEPOT, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_REFINERY, self.agent) : UnitType(UNIT_TYPEID.TERRAN_REFINERY, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_ENGINEERINGBAY, self.agent) :  UnitType(UNIT_TYPEID.TERRAN_ENGINEERINGBAY, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_MISSILETURRET, self.agent) : UnitType(UNIT_TYPEID.TERRAN_MISSILETURRET, self.agent).tile_height ,
                 }

    def init_offensive_dict(self):
        return { UnitType(UNIT_TYPEID.TERRAN_BARRACKS, self.agent) : UnitType(UNIT_TYPEID.TERRAN_BARRACKS, self.agent).tile_height,
                 UnitType(UNIT_TYPEID.TERRAN_BUNKER, self.agent) : UnitType(UNIT_TYPEID.TERRAN_BUNKER, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_SENSORTOWER, self.agent) : UnitType(UNIT_TYPEID.TERRAN_SENSORTOWER, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_FACTORY, self.agent) : UnitType(UNIT_TYPEID.TERRAN_FACTORY, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_ARMORY, self.agent) : UnitType(UNIT_TYPEID.TERRAN_ARMORY, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_STARPORT, self.agent) : UnitType(UNIT_TYPEID.TERRAN_STARPORT, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_FUSIONCORE, self.agent) : UnitType(UNIT_TYPEID.TERRAN_FUSIONCORE, self.agent).tile_height ,
                 UnitType(UNIT_TYPEID.TERRAN_GHOSTACADEMY, self.agent) : UnitType(UNIT_TYPEID.TERRAN_GHOSTACADEMY, self.agent).tile_height
                 }

    def init_addonable_list(self):
        return [UnitType(UNIT_TYPEID.TERRAN_BARRACKS, self.agent),
                 UnitType(UNIT_TYPEID.TERRAN_FACTORY, self.agent),
                 UnitType(UNIT_TYPEID.TERRAN_STARPORT, self.agent)
                ]

    def get_octile_dist_revamped(self, distance: int, x: int, y:int) -> list:

        # Add all perpendicular coordinates to desired tile.
        octile_coordinates = [(x-distance, y), (x, y+distance), (x, y-distance), (x+distance, y)]

        return octile_coordinates

    def find_position(self, unittype : UnitType, base : Point2DI=None) -> Point2DI:
        if base is None:
            return super().find_position(unittype)

        bd_object = self.get_bd_object(base)
        # ## If build order person wishes to build command center, return the base coordinate it gave us
        if unittype == UnitType(UNIT_TYPEID.TERRAN_COMMANDCENTER, self.agent):
            self.map_color = 3 # Color Green for defensif
            return base

        # ## If refinery is next to build, use parent to find since you first have to find
        # vespengeyser ID and then a new call for the refinery comes etc. Messy.
        if unittype == UnitType(UNIT_TYPEID.TERRAN_REFINERY, self.agent):
            return super().find_position(unittype)

        # ## If upgrade, just return base since upgrade is built upon Command Center.
        if unittype in self.upgrades.keys():
            return base
        #
        # If addon, look through addonable buildings, find the ones that can build addon at +3,0 offset
        # If do-able, remove from reserved tiles and return this coordinate.
        # Optimization should be to not remove build_coord from reserved tile until we know its properly built,
        # dunno how tho, yet.

        if unittype in self.addons:
            keys = bd_object.addonable_units.keys()
            for key in keys:
                possible_coords = bd_object.addonable_units[key]
                for coord in possible_coords:
                    build_coord = Point2DI(coord.x + 3, coord.y)
                    if self.agent.building_placer.can_build_here_with_size(build_coord.x, build_coord.y, 1, 1) and \
                            build_coord not in self.addon_tiles_placed:
                        self.reserved_tiles.remove(build_coord)
                        ## Add this data structure for in-a-vaccuum testing purposes, else will the addon just try to
                        ## build itself in first possible spot all the iterations (which we removed in first iteration).
                        self.addon_tiles_placed.append(build_coord)
                        self.map_color = 4
                        return build_coord
                # No place to put addon
                return


        ## Strategy is to occupy mid-points first, for spread purposes.
        ## When that is done, piggyback on prior suggested coordinates to recommend coordinates adjacent to these.
        # If that doesnt work, look at prior firsts. And if that doesnt work, last_resort for defensive units
        # goes through _all_ placed defensive units and look to their neighboring spots if theres somewhere to build.
        # For offensive units, last_resort is to find new places to build at other choke points.

        if unittype in self.defensive:
            self.map_color = 3
            last_suggested = bd_object.last_suggested_def
            build_distance = 3
            addonable = False
        elif unittype in self.offensive:
            self.map_color = 2
            last_suggested = bd_object.last_suggested_off
            build_distance = random.randint(4,5)
            if unittype in self.addonable_buildings:
                addonable = True

        if "Free" in bd_object.mid_points.values():
            keys = [k for k, v in bd_object.mid_points.items() if v == "Free"]
            for key in keys:
                if self.agent.building_placer.can_build_here(key[0], key[1], unittype):
                    bd_object.mid_points[key] = "Occupied"
                    if not type(key) == Point2DI:
                        key = Point2DI(key[0], key[1])
                    # To try this without using the bot, reserve tiles (this doesnt make
                    # can-build_here false tho. Add to reserve tiles instead and check if its in it
                    self.agent.building_placer.reserve_tiles(key.x, key.y, 2, 2)
                    self.reserved_tiles.append(key)
                    self.occupied_mid_points.append(key)

                    last_suggested.append([key])
                    if addonable:
                        self.update_and_reserve(bd_object, key, unittype)
                    return key
                # Even tho midpoint is free, need to check if we can build here
                elif not self.agent.building_placer.can_build_here(key[0], key[1], unittype):
                    continue


        ## All mid points are occupied, start piggy-backing.
        if len(last_suggested) == 0:
            for midpoint in self.occupied_mid_points:
                possible_coords = self.get_octile_dist_revamped(build_distance, midpoint.x, midpoint.y)
                recommendation = self.find_around_piggyback(possible_coords, bd_object, base, unittype)
                if recommendation:
                    if addonable:
                        self.update_and_reserve(bd_object,recommendation, unittype)

                    return recommendation

        piggyback = last_suggested[-1][-1]
        if self.agent.building_placer.can_build_here(piggyback.x, piggyback.y, unittype) and piggyback not in \
            self.reserved_tiles:
            if addonable:
                self.update_and_reserve(bd_object, piggyback, unittype)
            return piggyback

        possible_coords = self.get_octile_dist_revamped(build_distance, piggyback.x, piggyback.y)
        recommendation = self.find_around_piggyback(possible_coords, bd_object, base, unittype)
        if recommendation:
            if addonable:
                self.update_and_reserve(bd_object, recommendation, unittype)
            return recommendation

        prior_firsts_suggestions = [last_suggested[i][0] for i in range(len(last_suggested)-1, -1, -1)]
        possible_coords_prior_firsts_suggestions = []
        for suggestion in prior_firsts_suggestions:
            possible_coords_prior_firsts_suggestions.append(self.get_octile_dist_revamped(build_distance, suggestion.x, \
                                                                                          suggestion.y))
        possible_coords_prior_firsts_suggestions = [item for sublist in possible_coords_prior_firsts_suggestions \
                                                    for item in sublist]

        recommendation = self.find_around_piggyback(possible_coords_prior_firsts_suggestions, bd_object, base, unittype)
        if recommendation:
            last_suggested.append([recommendation])
            if addonable:
                self.update_and_reserve(bd_object, recommendation, unittype)
            return recommendation

        self.last_resort(last_suggested, build_distance, bd_object, base, unittype, addonable)


    """ Used to match a geyser to a base"""
    def match_geyser_to_base(self, geyser_2DI, base_2DI) -> int:
        return abs(geyser_2DI.tile_position.x - base_2DI.x) + abs(geyser_2DI.tile_position.y - base_2DI.y)


    """ used to determine whether a coord is closer to base coord or choke coord"""
    def is_closer_to_base(self, coord: Point2DI, base: Point2DI, choke_point: Point2DI) -> bool:
        dist_to_base = self.map_decomposer.get_distance_between(coord, base)
        dist_to_choke = self.map_decomposer.get_distance_between(coord, choke_point)
        return dist_to_base < dist_to_choke


    """ Borrowed from lab series to determine if a geyser is occupied by a refinery or not """
    def get_refinery(self, geyser: Unit) -> Optional[Unit]:
        """
        Returns: A refinery which is on top of unit `geyser` if any, None otherwise
        """

        def squared_distance(p1: Point2D, p2: Point2D) -> float:
            return (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2

        for unit in self.agent.get_my_units():
            if unit.unit_type.is_refinery and squared_distance(unit.position, geyser.position) < 1:
                return unit

        return None

    def find_around_piggyback(self, possible_coords : list , bd_object : BaseData, base : Point2DI, unittype : UnitType)\
            -> Point2DI:
        # Look around piggyback to determine next spot. Make sure to go in
        # right direction (closer/further from base whether defensive/offensive). When find good
        # enough spot, check if its possible to build here.

        for coord in possible_coords:

            if not type(coord) == Point2DI:
                coord = Point2DI(coord[0], coord[1])

            choke_point = self.get_nearest_chokepoint(coord, bd_object)
            if not type(choke_point) == Point2DI:
                choke_point = Point2DI(choke_point[0], choke_point[1])

            beyond_chokepoints = self.get_beyond_chokepoints(choke_point, base)

            if self.is_out_of_bounds(beyond_chokepoints, coord, choke_point):
                continue

            if self.is_closer_to_base(coord, base, choke_point) and unittype in self.defensive:
                if self.agent.building_placer.can_build_here(coord.x, coord.y, unittype) and coord not in \
                        self.reserved_tiles:

                    # To try this without using the bot, reserve tiles (this doesnt make
                    # can-build_here false tho. Add to reserve tiles instead and check if its in it
                    # innit
                    self.agent.building_placer.reserve_tiles(coord.x, coord.y, 2, 2)
                    self.reserved_tiles.append(coord)
                    if len(bd_object.last_suggested_def) == 0:
                        bd_object.last_suggested_def.append([coord])
                        return coord
                    bd_object.last_suggested_def[-1].append(coord)
                    return coord

            elif not self.is_closer_to_base(coord, base, choke_point) and unittype in self.offensive:
                if self.agent.building_placer.can_build_here(coord.x, coord.y, unittype) and coord not in \
                        self.reserved_tiles:

                    self.agent.building_placer.reserve_tiles(coord.x, coord.y, 2, 2)
                    self.reserved_tiles.append(coord)
                    if len(bd_object.last_suggested_off) == 0:
                        bd_object.last_suggested_off.append([coord])
                        return coord

                    bd_object.last_suggested_off[-1].append(coord)
                    return coord

        print("SADLY, NO PLACEMENT FOUND")

    """ Creates a fictive chokepoint beyond actual. Used as a limit to not go further than actual chokepoint."""
    def get_beyond_chokepoints(self, choke_point : Point2DI, base: Point2DI) -> list:

        result = []
        candidates = self.get_octile_dist_revamped(15, choke_point.x, choke_point.y)
        for candidate in candidates:
            candidate = Point2DI(candidate[0], candidate[1])
            if self.map_decomposer.get_distance_between(candidate, base) > self.map_decomposer.get_distance_between(\
                    choke_point,base):
                result.append(candidate)

        return result

    """ Finds nearest chokepoint to coordinate. Used to map a coordinate to a chokepoint. """
    def get_nearest_chokepoint(self, coord: Point2DI, bd_object : BaseData) -> Point2DI:
        result = Point2DI()
        temp = math.inf
        for choke_point in bd_object.choke_points:
            if not type(choke_point) == Point2DI:
                choke_point = Point2DI(choke_point[0], choke_point[1])
            if self.map_decomposer.get_distance_between(coord, choke_point) < temp:
                temp = self.map_decomposer.get_distance_between(coord, choke_point)
                result.x = choke_point.x
                result.y = choke_point.y

        return result

    """ Checks if a coordinate is out of bounds. I.e closer to the beyond chokepoint than the actual chokepoint. """
    def is_out_of_bounds(self, beyond_chokepoint : list, coord : Point2DI, chokepoint : Point2DI):
        truth_table = []
        for beyond in beyond_chokepoint:
            if self.map_decomposer.get_distance_between(coord, beyond) < self.map_decomposer.get_distance_between(coord, chokepoint):
                truth_table.append(True)
        if True in truth_table:
            return True
        return False


    """ Get corresponding BaseData object for this particular base. """
    def get_bd_object(self, base: Point2DI):
        for bd_object in self.base_data_objects:
            if bd_object.coordinate == base:
                return bd_object


    """ Updates data structure which keeps track of addon-able buildings (Barracks, Factory, Starport) built. 
     It then reserves tiles adjacent to this addon-able building so addon can be built here later, if wanted to. """

    def update_and_reserve(self, bd_object : BaseData, coord : Point2DI, unittype : UnitType):

        # Reserve tile meant for addon
        self.reserved_tiles.append(Point2DI(coord.x + 3 , coord.y))

        # If first time this addonable unit is built
        if not bd_object.addonable_units.get(unittype):
            bd_object.addonable_units[unittype] = coord
            return
        # If not, update value
        modify = bd_object.addonable_units.get(unittype)
        # If only 1 tuple innit, turn into list
        if type(modify) == Point2DI:
            modify = [modify]
            modify.append(coord)
            bd_object.addonable_units[unittype] = modify
            return
        # Else its already a list of values, update it
        modify.append(coord)
        bd_object.addonable_units[unittype] = modify
        return

    """ Last way of finding coordinate to build unittype at. Defensive looks through all prior coordinates neighbors.
        Offensive looks through all chokepoints and seeks positions there. """
    def last_resort(self, last_suggested : list, build_distance: int, bd_object: BaseData, base : Point2DI, unittype \
                              : UnitType, addonable : bool) -> Point2DI:

        if unittype in self.defensive:
            all_prior = [y for x in last_suggested for y in x]
            all_prior.append(Point2DI(base.x +5, base.y+5))
            neighbor_all_prior = []
            for prior in all_prior:
                if not type(prior) == Point2DI:
                    prior = Point2DI(prior[0], prior[1])
                neighbor_all_prior.append(self.get_octile_dist_revamped(build_distance, prior.x, prior.y))
            # Flatten it
            neighbor_all_prior = [item for sublist in neighbor_all_prior for item in sublist]
            recommendation = self.find_around_piggyback(neighbor_all_prior, bd_object, base, unittype)
            if recommendation:
                return recommendation

        elif unittype in self.offensive:
            chokepoints = bd_object.choke_points
            for chokepoint in chokepoints:
                if not type(chokepoint) == Point2DI:
                    chokepoint = Point2DI(chokepoint[0], chokepoint[1])

                possible_coords = self.get_octile_dist_revamped(2, chokepoint.x, chokepoint.y)
                recommendation = self.find_around_piggyback(possible_coords, bd_object, base, unittype)
                if recommendation:
                    last_suggested.append([recommendation])
                    if addonable:
                        self.update_and_reserve(bd_object, recommendation, unittype)
                    return recommendation


    """ Overriden function from py_building_placer that just calls parent function."""
    def find_refinery_position(self) -> Optional[PyUnit]:
        return super().find_refinery_position()

    """ Overriden function from py_building_placer that just calls parent function."""
    def can_build_addon(self, candidate: PyUnit) -> bool:
        return super().can_build_addon(candidate)

    """ Overriden function from py_building_placer that just calls parent function."""
    def check_and_fix_building_place(self,
                                     pos: Union[Point2DI, PyUnit],
                                     building_type: UnitType
                                     ) -> tuple[bool, Union[Point2DI, PyUnit]]:
        return super().check_and_fix_building_place(pos,building_type)

    """ Overriden function from py_building_placer that just calls parent function."""
    def get_new_addon_pos(self, unit_type: UnitType, py_unit: PyUnit) -> Optional[Point2D]:
        return super().get_new_addon_pos(unit_type,py_unit)