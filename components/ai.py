from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING
from entity import Entity

import numpy as np # type: ignore
import tcod

from actions import Action, MeleeAction, MovementAction, WaitAction

if TYPE_CHECKING:
    from entity import Actor

class BaseAI(Action):
    entity: Actor

    def perform(self) -> None:
        raise NotImplementedError()

    def get_path_to(self, dest_x: int, dest_y: int) -> List[Tuple[int, int]]:
        """
        Computa e retorna o caminho até a posição alvo.
        Se não há caminho válido então retorna uma lista vazia.

        Copia o array 'caminhável'.
        """
        cost = np.array(self.entity.gamemap.tiles["walkable"], dtype = np.int8)

        for entity in self.entity.gamemap.entities:
            # Verifica se há uma entidade bloqueando o movimento e se o custo não é zero (bloqueando).
            if entity.blocks_movement and cost[entity.x, entity.y]:
                """
                Adiciona ao custo de uma posição bloqueada.
                Um número menor significa que mais inimigos se acumularão em corredores.
                Um número maior significa que inimigos tomarão caminhos mais longos para encontrar o jogador.
                """
                cost[entity.x, entity.y] += 10

        graph = tcod.path.SimpleGraph(cost = cost, cardinal = 2, diagonal = 3)
        pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.entity.x, self.entity.y)) # Posição inicial

        # Calcula o caminho até o destino e remove o ponto inicial.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()

        # Converte de uma List[List[int]] para uma List[Tuple[int, int]].
        return [(index[0], index[1]) for index in path]

class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
    
    def perform(self) -> None:
        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy)) # Distancia Chebyshev.

        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()

            self.path = self.get_path_to(target.x, target.y)
        
        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()