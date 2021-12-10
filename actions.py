from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

class Action:
    def __init__(self, entity: Entity) -> None:
        super().__init__()
        self.entity = entity
    
    @property
    def engine(self) -> Engine:
        # Retorna a engine a que essa ação pertence.
        return self.entity.gamemap.engine

    def perform(self) -> None:
        # Executa a ação com os objetos necessários para determinar seu escopo.
        # "self.engine" é o escopo onde esta ação está sendo executada.
        # "self.entity" é o objeto executando a ação.
        # Este método precisa ser sobrescrito pela subclasse "Action".
        raise NotImplementedError()

class EscapeAction(Action):
    def perform(self) -> None:
        raise SystemExit()

class ActionWithDirection(Action):
    def __init__(self, entity: Entity, dx: int, dy: int):
        super().__init__(entity)

        self.dx = dx
        self.dy = dy

    @property
    def dest_xy(self) -> Tuple[int, int]:
        # Retorna o destino desta ação.
        return self.entity.x + self.dx, self.entity.y + self.dy
    
    @property
    def blocking_entity(self) -> Option[Entity]:
        # Retorna a entidade bloqueando no destino desta ação.
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)
    
    def perform(self) -> None:
        raise NotImplementedError()
    
class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.blocking_entity
        if not target:
            return # Nenhuma entidade para atacar.
        
        print(f"Você chuta o {target.name}, para seu aborrecimento!")

class MovementAction(ActionWithDirection):    
    def perform(self) -> None:
        dest_x, dest_y = self.dest_xy

        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            return # Destino está fora do escopo.
        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            return # Destino está bloqueado por um tile.
        if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
            return # Destino está bloqueado por uma entidade.
        
        self.entity.move(self.dx, self.dy)

class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.blocking_entity:
            return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()