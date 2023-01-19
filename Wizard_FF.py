import pygame

from random import randint, random
from Graph import *

from Character import *
from State import *

class Wizard_FF(Character):

    def __init__(self, world, image, projectile_image, base, position, explosion_image = None):

        Character.__init__(self, world, "wizard", image)

        self.projectile_image = projectile_image
        self.explosion_image = explosion_image

        self.base = base
        self.position = position
        self.move_target = GameEntity(world, "wizard_move_target", None)
        self.target = None
        self.defenseState = True
        
        self.maxSpeed = 50
        self.min_target_distance = 100
        self.projectile_range = 100
        self.projectile_speed = 100
        self.level = 1
        
        seeking_state = WizardStateSeeking_FF(self)
        attacking_state = WizardStateAttacking_FF(self)
        kiting_state = WizardStateKiting_FF(self)
        waiting_state = WizardStateWaiting_FF(self) #Waiting State
        ko_state = WizardStateKO_FF(self)
        
        self.brain.add_state(seeking_state)
        self.brain.add_state(attacking_state)
        self.brain.add_state(waiting_state)
        self.brain.add_state(kiting_state)
        self.brain.add_state(ko_state)
        
        #State to set at start
        self.brain.set_state("seeking")
        #self.brain.set_state("waiting")

    def render(self, surface):

        Character.render(self, surface)


    def process(self, time_passed):
        
        Character.process(self, time_passed)
        level_up_stats = ["hp", "speed", "ranged damage", "ranged cooldown", "projectile range"]
        if self.can_level_up():
            
            #Level up strategy
            self.level += 1
            print("Level: ", self.level)
            if self.level <= 5 :
                choice = 3
            elif self.level <= 8 :
                choice = 2  
            else:
                choice = 1
                
            self.level_up(level_up_stats[choice])
            
        #If not attack and health not full, do healing
        if self.brain.active_state.name != "attacking" and\
        self.current_hp < self.max_hp:
            self.heal()

#Go thru the selected path
class WizardStateSeeking_FF(State):

    def __init__(self, wizard):

        State.__init__(self, "seeking")
        self.wizard = wizard

        #Spawn bot
        self.wizard.path_graph = self.wizard.world.paths[1]
        #0 - Top Lane, 1 - Bot Lane, 2 - Mid Lane
        

    def do_actions(self):

        self.wizard.velocity = self.wizard.move_target.position - self.wizard.position
        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip();
            self.wizard.velocity *= self.wizard.maxSpeed

    def check_conditions(self):
        
        if self.wizard.defenseState == True:
            return "waiting"
        # check if opponent is in range
        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent != None:
            opponent_distance = (self.wizard.position - nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                    self.wizard.target = nearest_opponent
                    return "attacking"
                
        if (self.wizard.position - self.wizard.move_target.position).length() < 8:
            #continue on path
            if self.current_connection < self.path_length:
                self.wizard.move_target.position = self.path[self.current_connection].toNode.position
                self.current_connection += 1
                      
        return None

    def entry_actions(self):

        nearest_node = self.wizard.path_graph.get_nearest_node(self.wizard.position)

        self.path = pathFindAStar(self.wizard.path_graph, \
                                  nearest_node, \
                                  self.wizard.path_graph.nodes[self.wizard.base.target_node_index])

        
        self.path_length = len(self.path)

        if (self.path_length > 0):
            self.current_connection = 0
            self.wizard.move_target.position = self.path[0].fromNode.position

        else:
            self.wizard.move_target.position = self.wizard.path_graph.nodes[self.wizard.base.target_node_index].position


class WizardStateAttacking_FF(State):

    def __init__(self, wizard):

        State.__init__(self, "attacking")
        self.wizard = wizard

    def do_actions(self):

        opponent_distance = (self.wizard.position - self.wizard.target.position).length()
        
        
        # opponent within range
        if opponent_distance <= self.wizard.min_target_distance:
            self.wizard.velocity = Vector2(0, 0)
            if self.wizard.current_ranged_cooldown <= 0:
                self.wizard.ranged_attack(self.wizard.target.position, self.wizard.explosion_image)

        else:
            self.wizard.velocity = self.wizard.target.position - self.wizard.position
            if self.wizard.velocity.length() > 0:
                self.wizard.velocity.normalize_ip();
                self.wizard.velocity *= self.wizard.maxSpeed


    def check_conditions(self):
        # target is gone
        if self.wizard.world.get(self.wizard.target.id) is None or self.wizard.target.ko:
            self.wizard.target = None
            if self.wizard.defenseState == True:
                return "waiting"
            else:
                return "seeking"
            
        return None
        # when any opponent is near the wizard
        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position - nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                    self.wizard.target = nearest_opponent
            if opponent_distance < 70:
                return "kiting"
        

    def entry_actions(self):

        return None
    

class WizardStateKiting_FF(State):
    def __init__(self, wizard):

        State.__init__(self, "kiting")
        self.wizard = wizard
        
    def do_actions(self):
        target_distance = self.wizard.position - self.wizard.target.position
        self.wizard.velocity = self.wizard.position - self.wizard.target.position

        # when wizard at left side border
        if self.wizard.position.x < 20:
            direction = self.wizard.position + Vector2(0, self.wizard.position.y)
            self.wizard.velocity = Vector2(direction.y, direction.x) + target_distance
        # when wizard at right side border
        if self.wizard.position.x > 1004:
            direction = self.wizard.position + Vector2(1024, self.wizard.position.y)
            self.wizard.velocity = Vector2(direction.y, direction.x) + target_distance
        # when wizard at top side border
        if self.wizard.position.y > 748:
            direction = self.wizard.position + Vector2(self.wizard.position.x, 768)
            self.wizard.velocity = Vector2(direction.y, direction.x) + target_distance
        # when wizard at bottom side border
        if self.wizard.position.y < 20:
            direction = self.wizard.position - Vector2(self.wizard.position.x, 0)
            self.wizard.velocity = Vector2(direction.y, direction.x) + target_distance

        if self.wizard.velocity.length() > 0:
            self.wizard.velocity.normalize_ip();
            self.wizard.velocity *= self.wizard.maxSpeed

        else:
            self.wizard.velocity = self.wizard.target.position - self.wizard.position
            if self.wizard.velocity.length() > 0:
                self.wizard.velocity.normalize_ip();
                self.wizard.velocity *= self.wizard.maxSpeed


    def check_conditions(self):

        # target is gone or wizard died
        if self.wizard.world.get(self.wizard.target.id) is None or self.wizard.target.ko:
            self.wizard.target = None
            return "waiting"

        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent is not None:
            opponent_distance = (self.wizard.position - nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                    self.wizard.target = nearest_opponent
                    target_distance = (self.wizard.position - self.wizard.target.position).length()
                    if  target_distance > 50:
                        return "attacking"
        return None

    def entry_actions(self):

        return None

class WizardStateWaiting_FF(State):

    def __init__(self, wizard):

        State.__init__(self, "waiting")
        self.wizard = wizard

    def do_actions(self):
        tower1 = self.wizard.world.get(1)
        tower2 = self.wizard.world.get(2)
        if(tower1 == None and tower2 == None):
            targetDefense = None
            self.wizard.target = False
            self.wizard.defenseState = False
        else:
            if(tower2 == None):
                targetDefense = tower1
            else:
                targetDefense = tower2

        if targetDefense != None:
            self.wizard.target = targetDefense
            #print (self.wizard.target.position)
            #Add (10,10) to set wizard infront of tower to aggro enemy and prevent tower got targeted
            self.wizard.velocity = (self.wizard.target.position + (20, 20)) - self.wizard.position
            #self.wizard.velocity = (105,190) - self.wizard.position
            tower_distance = (self.wizard.position - self.wizard.target.position).length()
            
            if self.wizard.velocity.length() >= 0:
                self.wizard.velocity.normalize_ip();
                self.wizard.velocity *= self.wizard.maxSpeed
          
    def check_conditions(self):
        if self.wizard.defenseState == False:
            return "seeking"
        # check if opponent is in range
        nearest_opponent = self.wizard.world.get_nearest_opponent(self.wizard)
        if nearest_opponent != None:
            opponent_distance = (self.wizard.position - nearest_opponent.position).length()
            if opponent_distance <= self.wizard.min_target_distance:
                self.wizard.target = nearest_opponent
                return "attacking"

        return None

    def entry_actions(self):

        return None



class WizardStateKO_FF(State):

    def __init__(self, wizard):

        State.__init__(self, "ko")
        self.wizard = wizard

    def do_actions(self):

        return None


    def check_conditions(self):

        # respawned
        if self.wizard.current_respawn_time <= 0:
            self.wizard.current_respawn_time = self.wizard.respawn_time
            self.wizard.ko = False
            self.wizard.path_graph = self.wizard.world.paths[1] #Bot lane
            if self.wizard.defenseState == True:
                return "waiting"
            else:
                return "seeking"
            
        return None

    def entry_actions(self):

        self.wizard.current_hp = self.wizard.max_hp
        self.wizard.position = Vector2(self.wizard.base.spawn_position)
        self.wizard.velocity = Vector2(0, 0)
        self.wizard.target = None

        return None
