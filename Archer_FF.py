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
        self.proj_dist = None
        self.proj_vect = None
        self.dodged_proj = None
        self.dodged = True
        self.dodge_alt = 1

        self.maxSpeed = 50
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
        
        level_up_stats = ["speed", "ranged cooldown",]
        if self.can_level_up():
            choice = randint(0, len(level_up_stats) - 1)
            self.level_up(level_up_stats[choice])
        
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

        self.archer.path_graph = self.archer.world.paths[0]


    def do_actions(self):
        self.archer.velocity = self.archer.move_target.position - self.archer.position
        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip();
            self.archer.velocity *= self.archer.maxSpeed
        if self.archer.current_hp < 50:
            self.archer.heal()


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
                        projectile_distance = (self.archer.position - self.archer.incoming_proj.position)
                        self.archer.proj_vect = projectile_distance
                        self.archer.proj_dist = projectile_distance_length
                        self.archer.dodged = False
                        return "dodging"
                else:
                        self.archer.incoming_proj = nearest_projectile
                        projectile_distance = (self.archer.position - self.archer.incoming_proj.position)
                        self.archer.proj_vect = projectile_distance
                        self.archer.proj_dist = projectile_distance_length
                        self.archer.dodged = False
                        return "dodging"
        
        if (self.archer.position - self.archer.move_target.position).length() < 8:

            # continue on path
            if self.current_connection < self.path_length:
                self.archer.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
            
        return None

    def entry_actions(self):

        nearest_node = self.archer.path_graph.get_nearest_node(self.archer.position)

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
            if opponent_distance < 50:
                return "kiting"

        # If projectile approaching
        nearest_projectile = self.archer.get_nearest_projectile(self.archer)
        if nearest_projectile is not None:
            projectile_distance_length = (self.archer.position - nearest_projectile.position).length()
            if projectile_distance_length <= self.archer.min_target_distance and self.archer.dodged:
                if self.archer.dodged_proj is not None:
                    if self.archer.dodged_proj.id != nearest_projectile.id:
                        self.archer.incoming_proj = nearest_projectile
                        projectile_distance = (self.archer.position - self.archer.incoming_proj.position)
                        self.archer.proj_vect = projectile_distance
                        self.archer.proj_dist = projectile_distance_length
                        self.archer.dodged = False
                        return "dodging"
                else:
                        self.archer.incoming_proj = nearest_projectile
                        projectile_distance = (self.archer.position - self.archer.incoming_proj.position)
                        self.archer.proj_vect = projectile_distance
                        self.archer.proj_dist = projectile_distance_length
                        self.archer.dodged = False
                        return "dodging"
        return None

    def entry_actions(self):

        return None

class ArcherStateDodge_FF(State):
    def __init__(self, archer):

        State.__init__(self, "dodging")
        self.archer = archer
        
    def do_actions(self):
        projectile_distance = self.archer.proj_vect
        projectile_distance_length = (self.archer.position - self.archer.incoming_proj.position).length()
        if self.archer.dodge_alt == 1:
            #self.archer.velocity = Vector2(projectile_distance.y, projectile_distance.x * -1 )
            self.archer.velocity = Vector2(projectile_distance.y, projectile_distance.x * -1)
        if self.archer.dodge_alt == 2:
            self.archer.velocity = Vector2(projectile_distance.y * -1, projectile_distance.x)

        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip()
            self.archer.velocity *= self.archer.maxSpeed

        # stop dodging after projectile goes past
        if self.archer.proj_dist > projectile_distance_length:
            self.archer.proj_dist = projectile_distance_length
        else:
            self.archer.dodged = True
            self.archer.dodged_proj = self.archer.incoming_proj
        



    def check_conditions(self):
        # target is gone
        if self.archer.world.get(self.archer.incoming_proj.id) is None or self.archer.dodged:
            self.archer.dodged = True
            if self.archer.dodge_alt == 2:
                self.archer.dodge_alt = 1
            if self.archer.dodge_alt == 1:
                self.archer.dodge_alt = 2
            self.archer.incoming_proj = None
            return "seeking"

        return None

    def entry_actions(self):

        return None

class ArcherStateKite_FF(State):
    def __init__(self, archer):

        State.__init__(self, "kiting")
        self.archer = archer
        
    def do_actions(self):
        target_distance = self.archer.position - self.archer.target.position
        self.archer.velocity = self.archer.position - self.archer.target.position

        # when archer at left side border
        if self.archer.position.x < 20:
            direction = self.archer.position + Vector2(SCREEN_WIDTH, self.archer.position.y)
            self.archer.velocity = direction + target_distance
        # when archer at right side border
        if self.archer.position.x > SCREEN_WIDTH - 20:
            direction = self.archer.position + Vector2(0, self.archer.position.y)
            self.archer.velocity = direction + target_distance
        # when archer at top side border
        if self.archer.position.y > SCREEN_HEIGHT - 20:
            direction = self.archer.position + Vector2(self.archer.position.x, 0)
            self.archer.velocity = direction + target_distance
        # when archer at bottom side border
        if self.archer.position.y < 20:
            direction = self.archer.position + Vector2(self.archer.position.x, SCREEN_HEIGHT)
            self.archer.velocity = direction + target_distance

        if self.archer.velocity.length() > 0:
            self.archer.velocity.normalize_ip();
            self.archer.velocity *= self.archer.maxSpeed

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
                        projectile_distance = (self.archer.position - self.archer.incoming_proj.position)
                        self.archer.proj_vect = projectile_distance
                        self.archer.proj_dist = projectile_distance_length
                        self.archer.dodged = False
                        return "dodging"
                else:
                        self.archer.incoming_proj = nearest_projectile
                        projectile_distance = (self.archer.position - self.archer.incoming_proj.position)
                        self.archer.proj_vect = projectile_distance
                        self.archer.proj_dist = projectile_distance_length
                        self.archer.dodged = False
                        return "dodging"
        return None

    def entry_actions(self):

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
            self.archer.path_graph = self.archer.world.paths[0]
            return "seeking"
            
        return None

    def entry_actions(self):

        self.archer.current_hp = self.archer.max_hp
        self.archer.position = Vector2(self.archer.base.spawn_position)
        self.archer.velocity = Vector2(0, 0)
        self.archer.target = None

        return None
