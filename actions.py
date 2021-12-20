from __future__ import annotations
from random import expovariate

from typing import Optional, Tuple, TYPE_CHECKING

import color
import exceptions

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Entity, Item

class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity
    
    @property
    def engine(self) -> Engine:
        # Retorna a engine a que essa ação pertence.
        return self.entity.gamemap.engine

    def perform(self) -> None:
        """
        Executa a ação com os objetos necessários para determinar seu escopo.
        'self.engine' é o escopo onde esta ação está sendo executada.
        'self.entity' é o objeto executando a ação.
        Este método precisa ser sobrescrito pela subclasse 'Action'.
        """
        raise NotImplementedError()

class PickupAction(Action):
    # Pega um item e adiciona ao inventário, se houver espaço para ele.

    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> None:
        actor_location_x = self.entity.x
        actor_location_y = self.entity.y
        inventory = self.entity.inventory

        for item in self.engine.game_map.items:
            if len(inventory.items) >= inventory.capacity:
                raise exceptions.Impossible("Your inventory is full.")

            self.engine.game_map.entities.remove(item)
            item.parent = self.entity.inventory
            inventory.items.append(item)

            self.engine.message_log.add_message(f"You picked up the {item.name}!")
            return
        
        raise exceptions.Impossible("There is nothing here to pick up.")

class ItemAction(Action):
    def __init__(
        self, entity: Actor, item: Item, target_xy: Optional[Tuple[int, int]] = None
    ):
        super().__init__(entity)
        self.item = item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy

    @property
    def target_actor(self) -> Optional[Actor]:
        # Retorna o actor no destino desta ação.
        return self.engine.game_map.get_actor_at_location(*self.target_xy)

    def perform(self) -> None:
        # Invoca a abilidade do item, esta ação será informada para fornecer contexto.
        self.item.consumable.activate(self)

class DropItem(ItemAction):
    def perform(self) -> None:
        self.entity.inventory.drop(self.item)

class WaitAction(Action):
    def perform(self) -> None:
        pass

class ActionWithDirection(Action):
    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)

        self.dx = dx
        self.dy = dy

    @property
    def dest_xy(self) -> Tuple[int, int]:
        # Retorna o destino desta ação.
        return self.entity.x + self.dx, self.entity.y + self.dy
    
    @property
    def blocking_entity(self) -> Optional[Entity]:
        # Retorna a entidade bloqueando no destino desta ação.
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)
    
    @property
    def target_actor(self) -> Optional[Actor]:
        # Retorna o ator no destino desta ação.
        return self.engine.game_map.get_actor_at_location(*self.dest_xy)

    def perform(self) -> None:
        raise NotImplementedError()
    
class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.target_actor
        if not target:
            raise exceptions.Impossible("Nothing to attack.")
        
        damage = self.entity.fighter.power - target.fighter.defense

        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        if self.entity is self.engine.player:
            attack_color = color.player_atk
        else:
            attack_color = color.enemy_atk
            
        if damage > 0:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage} hit points.", attack_color
            )
            target.fighter.hp -= damage
        else:
            self.engine.message_log.add_message(
                f"{attack_desc} but does no damage.", attack_color
            )

class MovementAction(ActionWithDirection):    
    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy

        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            # Destino está fora do escopo.
            raise exceptions.Impossible("That way is blocked.")
        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            # Destino está bloqueado por um tile.
            raise exceptions.Impossible("That way is blocked.")
        if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
            # Destino está bloqueado por uma entidade.
            raise exceptions.Impossible("That way is blocked.")
        
        self.entity.move(self.dx, self.dy)

class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.target_actor:
            return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()