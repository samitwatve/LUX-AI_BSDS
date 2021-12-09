#!/usr/bin/env python
# coding: utf-8

# In[ ]:





# In[ ]:





# #### Import packages

# In[1]:


import numpy as np
import pandas as pd
from kaggle_environments import make

from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math
import sys


# #### Functions to find things on the map such as resources, enemy units and cities etc

# In[2]:


# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def find_resources(game_state):
    resource_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles

# the next snippet finds the closest resources that we can mine given position on a map
def find_closest_resources(pos, player, resource_tiles):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        # we skip over resources that we can't mine due to not having researched them
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile

def find_closest_city_tile(pos, player):
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile

def find_city_adjacent_empty_tiles(player):
    width, height = game_state.map_width, game_state.map_height
    adjacent_empty_tiles = []
    city_tiles_positions = []
    if len(player.cities) > 0:
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                city_tiles_positions.append(city_tile.pos)
                for y in range(height):
                    for x in range(width):
                        cell = game_state.map.get_cell(x, y)
                        if cell.pos.is_adjacent(city_tile.pos):
                            for ctp in city_tiles_positions:
                                if cell.pos.equals(ctp):
                                    continue
                                else:
                                    if not cell.has_resource():
                                        adjacent_empty_tiles.append(cell.pos)
    return adjacent_empty_tiles
        
    


# #### Functions to keep track of metrics

# In[3]:


def total_fuel_available(player):
    total_fuel_available = 0
    for k, city in player.cities.items():
        total_fuel_available += city.fuel
    return total_fuel_available


# #### Functions to take actions based on specified policies

# In[4]:


def worker_actions_policy(player, actions):
    resource_tiles = find_resources(game_state)
    actions = []
    
    # if resources are low, prioritize resource collection
    if total_fuel_available(player) < 500: 
        for unit in player.units:
            # if the unit is a worker (can mine resources) and can perform an action this turn
            if unit.is_worker() and unit.can_act():
                # we want to mine only if there is space left in the worker's cargo
                if unit.get_cargo_space_left() > 0:
                    # find the closest resource if it exists to this unit
                    closest_resource_tile = find_closest_resources(unit.pos, player, resource_tiles)
                    if closest_resource_tile is not None:
                        # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                        action = unit.move(unit.pos.direction_to(closest_resource_tile.pos))
                        actions.append(action)
                else:
                    #find the closest city tile and drop off resources there
                    closest_city_tile = find_closest_city_tile(unit.pos, player)
                    action = unit.move(unit.pos.direction_to(closest_city_tile.pos))
                    actions.append(action)
                    
    elif total_fuel_available(player) > 500: 
        for unit in player.units:
            # if the unit is a worker (can mine resources) and can perform an action this turn
            if unit.is_worker() and unit.can_act():
                 # we want to mine only if there is space left in the worker's cargo
                if unit.get_cargo_space_left() > 0:
                    # find the closest resource if it exists to this unit
                    closest_resource_tile = find_closest_resources(unit.pos, player, resource_tiles)
                    if closest_resource_tile is not None:
                        # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                        action = unit.move(unit.pos.direction_to(closest_resource_tile.pos))
                        actions.append(action)
                else:                                     
                    for empty_tile in find_city_adjacent_empty_tiles(player):
                        if unit.pos.equals(empty_tile):
                            annotate.sidetext(unit.pos)
                            annotate.sidetext("Unit at valid build city location")
                            action = unit.build_city()
                            actions.append(action)
                        else:
                            annotate.sidetext("Trying to move to empty_tile")
                            action = unit.move(unit.pos.direction_to(empty_tile))
                            actions.append(action)
                            break
    return actions


def city_actions_policy(player, actions):
    resource_tiles = find_resources(game_state)
    actions = []
    
    if len(player.cities) > 0:
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                if city_tile.can_act():
                    if player.city_tile_count > len(player.units):
                        action = city_tile.build_worker()
                        actions.append(action)
                    else:
                        action = city_tile.research()
                        actions.append(action)
                else:
                    continue        
    return actions
    


# #### Agent Code

# In[5]:


game_state = None
def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height
    
    # add debug statements like so!
    if game_state.turn == 0:
        print("Agent is running!", file=sys.stderr)
    
    actions = worker_actions_policy(player, actions)
    #actions = city_actions_policy(player, actions)
    
    return actions


# #### Run the game

# In[6]:


env = make("lux_ai_2021", configuration={"seed": 562124210, "loglevel": 2, "annotations": True}, debug=True)
steps = env.run([agent, "simple_agent"])
env.render(mode="ipython", width=720, height=480)

