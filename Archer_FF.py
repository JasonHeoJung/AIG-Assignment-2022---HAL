import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

class Archer_FF(Character):

    def __init__(self, world, image, projectile_image, base, position):

        Character.__init__(self, world, "archer", image)

        self.projectile_image = projectile_image

        self.base = base
        self.position = position
        self.move_target = GameEntity(world, "archer_move_target", None)
        self.target = None
        self.incoming_proj = None
        self.dodged_proj = None
        self.dodged = True
        self.dodge_alt = 1

        self.nextNode = None
        self.backNode = None

        self.maxSpeed = 100
        self.min_target_distance = 100
        self.projectile_range = 100
        self.projectile_speed = 100

        seeking_state = ArcherStateSeeking_FF(self)
        attacking_state = ArcherStateAttacking_FF(self)
        dodging_state = ArcherStateDodge_FF(self)
        kiting_state = ArcherStateKite_FF(self)
        ko_state = ArcherStateKO_FF(self)

        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(dodging_state)
        self.brain.add_state(kiting_state)
        self.brain.add_state(ko_state)

        self.brain.set_state("seeking")

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
        
        Character.process(self, time_passed)
        level_up_stats = ["hp", "speed", "ranged damage", "ranged cooldown", "projectile range"]
        if self.can_level_up():
            if self.maxSpeed < 145:
                choice = 1
            else:
                choice = 2

            self.level_up(level_up_stats[choice])

        if self.current_hp < ARCHER_MAX_HP/2:
            self.heal()
        
    def get_nearest_projectile(self, char):

        nearest_projectile = None
        distance = 0.

        for entity in self.world.entities.values():

            # same team
            if entity.team_id == char.team_id:
                continue

            if entity.name != "projectile":
                continue

            if nearest_projectile is None:
                nearest_projectile = entity
                distance = (char.position - entity.position).length()
            else:
                if distance > (char.position - entity.position).length():
                    distance = (char.position - entity.position).length()
                    nearest_projectile = entity
        
        return nearest_projectile

    


class ArcherStateSeeking_FF(State):

    def __init__(self, archer):

        State.__init__(self, "seeking")
        self.archer = archer

        self.archer.path_graph = self.archer.world.paths[1]


    def do_actions(self):
        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip();
            self.archer.velocity *= self.archer.maxSpeed

        collision_list = pygame.sprite.spritecollide(self.archer, self.archer.world.obstacles, False, pygame.sprite.collide_mask)
        for entity in collision_list:
            if entity.team_id == self.archer.team_id:
                continue
            elif entity.name == "obstacle" or entity.name == "base":
                self.archer.velocity = self.archer.position - entity.position
                if self.archer.velocity.length() > 0:
                    self.archer.velocity.normalize_ip();
                    self.archer.velocity *= self.archer.maxSpeed

    def check_conditions(self):

        # check if opponent is in range
        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            opponent_distance = (self.archer.position - nearest_opponent.position).length()
            if opponent_distance <= self.archer.min_target_distance:
                    self.archer.target = nearest_opponent
                    return "attacking"
        
        # If projectile approaching
        nearest_projectile = self.archer.get_nearest_projectile(self.archer)
        if nearest_projectile is not None:
            projectile_distance_length = (self.archer.position - nearest_projectile.position).length()
            if projectile_distance_length <= self.archer.min_target_distance and self.archer.dodged:
                if self.archer.dodged_proj is not None:
                    if self.archer.dodged_proj.id != nearest_projectile.id:
                        self.archer.incoming_proj = nearest_projectile
                        self.archer.dodged = False
                        return "dodging"
                else:
                        self.archer.incoming_proj = nearest_projectile
                        self.archer.dodged = False
                        return "dodging"
                
        if (self.archer.position - self.archer.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.archer.move_target.position = self.path[self.current_connection].toNode.position
                self.archer.backNode = self.path[self.current_connection].fromNode
                self.archer.nextNode = self.path[self.current_connection].toNode
                self.current_connection += 1
            
        return None

    def entry_actions(self):
        

        nearest_node = self.archer.path_graph.get_nearest_node(self.archer.position)
        if self.archer.nextNode is not None:
            nearest_node = self.archer.nextNode

        self.path = pathFindAStar(self.archer.path_graph, \
                                  nearest_node, \
                                  self.archer.path_graph.nodes[self.archer.base.target_node_index])

        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.archer.move_target.position = self.path[0].fromNode.position

        else:
            self.archer.move_target.position = self.archer.path_graph.nodes[self.archer.base.target_node_index].position


class ArcherStateAttacking_FF(State):

    def __init__(self, archer):

        State.__init__(self, "attacking")
        self.archer = archer

    def do_actions(self):

        opponent_distance = (self.archer.position - self.archer.target.position).length()
        # opponent within range
        if opponent_distance <= self.archer.min_target_distance:
            self.archer.velocity = Vector2(0, 0)
            if self.archer.current_ranged_cooldown <= 0:
                self.archer.ranged_attack(self.archer.target.position)

        else:
            self.archer.velocity = self.archer.target.position - self.archer.position
            if self.archer.velocity.length() > 0:
                self.archer.velocity.normalize_ip();
                self.archer.velocity *= self.archer.maxSpeed


    def check_conditions(self):

        # target is gone
        if self.archer.world.get(self.archer.target.id) is None or self.archer.target.ko:
            self.archer.target = None
            return "seeking"

        # when any opponent is near the archer
        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            opponent_distance = (self.archer.position - nearest_opponent.position).length()
            if opponent_distance <= self.archer.min_target_distance:
                    self.archer.target = nearest_opponent
            if opponent_distance < 70:   
                return "kiting"

        # If projectile approaching
        nearest_projectile = self.archer.get_nearest_projectile(self.archer)
        if nearest_projectile is not None:
            projectile_distance_length = (self.archer.position - nearest_projectile.position).length()
            if projectile_distance_length <= self.archer.min_target_distance and self.archer.dodged:
                if self.archer.dodged_proj is not None:
                    if self.archer.dodged_proj.id != nearest_projectile.id:
                        self.archer.incoming_proj = nearest_projectile
                        self.archer.dodged = False
                        return "dodging"
                else:
                        self.archer.incoming_proj = nearest_projectile
                        self.archer.dodged = False
                        return "dodging"
        return None

    def entry_actions(self):

        return None

class ArcherStateDodge_FF(State):
    def __init__(self, archer):

        State.__init__(self, "dodging")
        self.archer = archer
        self.proj_vect = None
        self.proj_dist = None
        
    def do_actions(self):
        projectile_distance_length = (self.archer.position - self.archer.incoming_proj.position).length()
        if self.archer.dodge_alt == 1:
            self.archer.velocity = Vector2(self.proj_vect.y, self.proj_vect.x * -1)
        elif self.archer.dodge_alt == 2:
            self.archer.velocity = Vector2(self.proj_vect.y * -1, self.proj_vect.x)

        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed

        # stop dodging after projectile goes past
        if self.proj_dist > projectile_distance_length:
            self.proj_dist = projectile_distance_length
        else:
            self.archer.dodged = True
            self.archer.dodged_proj = self.archer.incoming_proj
        



    def check_conditions(self):
        # target is gone
        if self.archer.world.get(self.archer.incoming_proj.id) is None or self.archer.dodged:
            self.archer.dodged = True
            if self.archer.dodge_alt == 2:
                self.archer.dodge_alt = 1
            elif self.archer.dodge_alt == 1:
                self.archer.dodge_alt = 2
            self.archer.incoming_proj = None
            return "seeking"

        return None

    def entry_actions(self):
        self.proj_vect = (self.archer.position - self.archer.incoming_proj.position)
        self.proj_dist = (self.archer.position - self.archer.incoming_proj.position).length()
        return None

class ArcherStateKite_FF(State):
    def __init__(self, archer):

        State.__init__(self, "kiting")
        self.archer = archer

        self.archer.path_graph = self.archer.world.paths[1]
        
    def do_actions(self):
        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip();
            self.archer.velocity *= self.archer.maxSpeed

        collision_list = pygame.sprite.spritecollide(self.archer, self.archer.world.obstacles, False, pygame.sprite.collide_mask)
        for entity in collision_list:
            if entity.team_id == self.archer.team_id:
                continue
            elif entity.name == "obstacle" or entity.name == "base":
                self.archer.velocity = self.archer.position - entity.position
                if self.archer.velocity.length() > 0:
                    self.archer.velocity.normalize_ip();
                    self.archer.velocity *= self.archer.maxSpeed

    def check_conditions(self):

        # target is gone
        if self.archer.world.get(self.archer.target.id) is None or self.archer.target.ko:
            self.archer.target = None
            return "seeking"

        nearest_opponent = self.archer.world.get_nearest_opponent(self.archer)
        if nearest_opponent is not None:
            opponent_distance = (self.archer.position - nearest_opponent.position).length()
            if opponent_distance <= self.archer.min_target_distance:
                    self.archer.target = nearest_opponent
                    target_distance = (self.archer.position - self.archer.target.position).length()
                    if  target_distance > 50:
                        return "attacking"

        # If projectile approaching
        nearest_projectile = self.archer.get_nearest_projectile(self.archer)
        if nearest_projectile is not None:
            projectile_distance_length = (self.archer.position - nearest_projectile.position).length()
            if projectile_distance_length <= self.archer.min_target_distance and self.archer.dodged:
                if self.archer.dodged_proj is not None:
                    if self.archer.dodged_proj.id != nearest_projectile.id:
                        self.archer.incoming_proj = nearest_projectile
                        self.archer.dodged = False
                        return "dodging"
                else:
                        self.archer.incoming_proj = nearest_projectile
                        self.archer.dodged = False
                        return "dodging"
                
        if (self.archer.position - self.archer.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.archer.move_target.position = self.path[self.current_connection].toNode.position
                self.archer.backNode = self.path[self.current_connection].toNode
                self.archer.nextNode = self.path[self.current_connection].fromNode
                self.current_connection += 1

        return None

    def entry_actions(self):
        nearest_node = self.archer.path_graph.get_nearest_node(self.archer.position)
        if self.archer.backNode is not None:
            nearest_node = self.archer.backNode

        self.path = pathFindAStar(self.archer.path_graph, \
                                  nearest_node, \
                                  self.archer.path_graph.nodes[self.archer.base.spawn_node_index])

        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.archer.move_target.position = self.path[0].fromNode.position

        else:
            self.archer.move_target.position = self.archer.path_graph.nodes[self.archer.base.spawn_node_index].position
            
        return None

class ArcherStateKO_FF(State):

    def __init__(self, archer):

        State.__init__(self, "ko")
        self.archer = archer

    def do_actions(self):

        return None


    def check_conditions(self):

        # respawned
        if self.archer.current_respawn_time <= 0:
            self.archer.current_respawn_time = self.archer.respawn_time
            self.archer.ko = False
            self.archer.dodged = True
            self.archer.path_graph = self.archer.world.paths[1]
            return "seeking"
            
        return None

    def entry_actions(self):
        self.archer.nextNode = None
        self.archer.current_hp = self.archer.max_hp
        self.archer.position = Vector2(self.archer.base.spawn_position)
        self.archer.velocity = Vector2(0, 0)
        self.archer.target = None

        return None
