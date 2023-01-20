import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

class Knight_FF(Character):

    def __init__(self, world, image, base, position):

        Character.__init__(self, world, "knight", image)

        self.base = base
        self.position = position
        self.move_target = GameEntity(world, "knight_move_target", None)
        self.target = None

        self.maxSpeed = 80
        self.min_target_distance = 100
        self.melee_damage = 20
        self.melee_cooldown = 2.
        self.level = 1

        seeking_state = KnightStateSeeking_FF(self)
        attacking_state = KnightStateAttacking_FF(self)
        ko_state = KnightStateKO_FF(self)
        waiting_state = KnightStateWaiting_FF(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(ko_state)
        self.brain.add_state(waiting_state)

        self.brain.set_state("waiting")
        

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
        
        Character.process(self, time_passed)

        level_up_stats = ["hp", "healing"]
        if self.can_level_up():
            #level up
            if self.level <= 5:
                choice = 0
            elif self.level <= 10:
                choice = 1
            else:
                choice = 0
            
            self.level_up(level_up_stats[choice])
            self.level += 1

        if self.brain.active_state.name is not "attacking":
            self.heal()

class KnightStateSeeking_FF(State):

    def __init__(self, knight):

        State.__init__(self, "seeking")
        self.knight = knight

        self.knight.path_graph = self.knight.world.paths[1]
        #0 - Top Lane, 1 - Bot Lane, 2 - Mid Lane


    def do_actions(self):

        self.knight.velocity = self.knight.move_target.position - self.knight.position
        if self.knight.velocity.length() > 0:
            self.knight.velocity.normalize_ip();
            self.knight.velocity *= self.knight.maxSpeed


    def check_conditions(self):

        # check if opponent is in range
        nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
        if nearest_opponent is not None:
            opponent_distance = (self.knight.position - nearest_opponent.position).length()
            if opponent_distance <= self.knight.min_target_distance:
                    self.knight.target = nearest_opponent
                    return "attacking"
        
        if (self.knight.position - self.knight.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.knight.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
            
        return None


    def entry_actions(self):

        nearest_node = self.knight.path_graph.get_nearest_node(self.knight.position)

        self.path = pathFindAStar(self.knight.path_graph, \
                                  nearest_node, \
                                  self.knight.path_graph.nodes[self.knight.base.target_node_index])

        
        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.knight.move_target.position = self.path[0].fromNode.position

        else:
            self.knight.move_target.position = self.knight.path_graph.nodes[self.knight.base.target_node_index].position

class KnightStateAttacking_FF(State):

    def __init__(self, knight):

        State.__init__(self, "attacking")
        self.knight = knight

    def do_actions(self):

        # colliding with target
        if pygame.sprite.collide_rect(self.knight, self.knight.target):
            self.knight.velocity = Vector2(0, 0)
            self.knight.melee_attack(self.knight.target)

        else:
            self.knight.velocity = self.knight.target.position - self.knight.position
            if self.knight.velocity.length() > 0:
                self.knight.velocity.normalize_ip();
                self.knight.velocity *= self.knight.maxSpeed

    def check_conditions(self):

        # target is gone
        if self.knight.world.get(self.knight.target.id) is None or self.knight.target.ko:
            self.knight.target = None
            return "waiting"
            
        return None

    def entry_actions(self):

        return None

class KnightStateWaiting_FF(State):

    def __init__(self, knight):

        State.__init__(self, "waiting")
        self.knight = knight

    def do_actions(self):
        team = self.knight.team_id
        if team == 0:
            tower1 = self.knight.world.get(1)
            tower2 = self.knight.world.get(2)
        elif team == 1:
            tower1 = self.knight.world.get(8)
            tower2 = self.knight.world.get(7)

        if(tower1 == None or tower2 == None):
            self.knight.target = self.knight.base
            #Add (60,60) since I want the knight to be targeted instead of the base
            if team == 0:
                defendPosition = self.knight.target.position+(60,60)
            if team == 1:
                defendPosition = self.knight.target.position-(60,60)
            self.knight.velocity = defendPosition - self.knight.position
            if self.knight.velocity.length() > 0:
                self.knight.velocity.normalize_ip();
                self.knight.velocity *= self.knight.maxSpeed

        else:
            self.knight.target = tower1        
            #Add (10,10) since I want the knight to be targeted instead of the tower
            if team == 0:
                defendPosition = self.knight.target.position+(10,10)
            if team == 1:
                defendPosition = self.knight.target.position-(10,10)
            self.knight.velocity = defendPosition - self.knight.position
            if self.knight.velocity.length() > 0:
                self.knight.velocity.normalize_ip();
                self.knight.velocity *= self.knight.maxSpeed

    def check_conditions(self):

        # check if opponent is in range
        nearest_opponent = self.knight.world.get_nearest_opponent(self.knight)
        if nearest_opponent is not None:
            opponent_distance = (self.knight.position - nearest_opponent.position).length()
            if opponent_distance <= self.knight.min_target_distance:
                    self.knight.target = nearest_opponent
                    return "attacking"
            
        return None

    def entry_actions(self):

        return None

class KnightStateKO_FF(State):

    def __init__(self, knight):

        State.__init__(self, "ko")
        self.knight = knight

    def do_actions(self):

        return None


    def check_conditions(self):

        # respawned
        if self.knight.current_respawn_time <= 0:
            self.knight.current_respawn_time = self.knight.respawn_time
            self.knight.ko = False
            self.knight.path_graph = self.knight.world.paths[randint(0, len(self.knight.world.paths)-1)]
            return "waiting"
            
        return None

    def entry_actions(self):

        self.knight.current_hp = self.knight.max_hp
        self.knight.position = Vector2(self.knight.base.spawn_position)
        self.knight.velocity = Vector2(0, 0)
        self.knight.target = None

        return None
