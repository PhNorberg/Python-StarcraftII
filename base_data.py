from typing import TYPE_CHECKING, Any, Type, Union, Optional
import copy
import math
import time
if TYPE_CHECKING:
    from tasks.task import Task
    from modules.py_unit import PyUnit
    from agents.basic_agent import BasicAgent


from library import UnitType, Unit, UNIT_TYPEID, Point2D, Point2DI, BaseLocation, BaseLocationManager
from modules.map_decomposer import MapDecomposer

class BaseData:
    """ BaseData keeps track of necessary data related to a base to help BuildingPlacerEvaluator determine a coordinate."""
    def __init__(self, mapdecomposor : MapDecomposer, coordinate : Point2DI):
        self.mapdecomposor = mapdecomposor
        self.coordinate = coordinate
        self.last_suggested_def = []
        self.last_suggested_off = []
        self.choke_points = self.mapdecomposor.choke_point_coords[self.coordinate]
        self.mid_points = {self.get_midpoint(self.coordinate.x, self.coordinate.y, chokepoint.x, chokepoint.y) : "Free" for chokepoint in self.choke_points}
        self.midpoint_list = [self.get_midpoint(self.coordinate.x, self.coordinate.y, chokepoint.x, chokepoint.y) for
                              chokepoint in self.choke_points]
        self.addonable_units = {}


    """ Fetches midpoint between base coordinate and choke point. Used to divide zone into
        two sub-zones, one of each preferred to have defensive or offensive buildings built within
        them. """
    def get_midpoint(self, x_base: int, y_base: int, x_choke: int, y_choke: int):
        return (x_base +  math.floor(int((x_choke - x_base) / 2)) if x_base > x_choke else x_base + \
            abs(math.floor(int(((x_choke - x_base) / 2)))),
                y_base + math.floor(int((y_choke - y_base) / 2)) if y_base > y_choke else y_base + \
                 abs(math.floor(int(((y_choke - y_base) / 2)))))