from __future__ import annotations

from typing import Iterable, Optional, TYPE_CHECKING

import numpy as np # type: ignore
from tcod.console import Console

import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

class GameMap:
    def __init__(
        self, engine: Engine, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.width, self.height = width, height
        self.entities = set(entities)
        self.tiles = np.full((width, height), fill_value = tile_types.wall, order = "F")

        self.visible = np.full(
            (width, height), fill_value = False, order = "F"
        ) # Tiles que o jogador pode ver.
        self.explored = np.full(
            (width, height), fill_value = False, order = "F"
        ) # Tiles que o jogador já viu.

    def get_blocking_entity_at_location(
        self, location_x: int, location_y: int,
    ) -> Optional[Entity]:
        for entity in self.entities:
            if (
                entity.blocks_movement
                and entity.x == location_x
                and entity.y == location_y
            ):
                return entity

        return None

    def in_bounds(self, x: int, y: int) -> bool:
        # Retorna True se x e y estão dentro dos limites do mapa.
        return 0 <= x < self.width and 0 <= y < self.height
    
    def render(self, console: Console) -> None:
        # Renderiza a mapa.
        # Se um tile está no array "visível", então desenha ele com as cores "light".
        # Se não estiver, mas for um tile "explorado", desenha ele com as cores "dark".
        # Senão, o padrão é "SHROUD".
        console.tiles_rgb[0 : self.width, 0 : self.height] = np.select(
            condlist = [self.visible, self.explored],
            choicelist = [self.tiles["light"], self.tiles["dark"]],
            default = tile_types.SHROUD,
        )

        for entity in self.entities:
            # Desenha apenas entidades que estão no campo de visão.
            if self.visible[entity.x, entity.y]:
                console.print(x = entity.x, y = entity.y, string = entity.char, fg = entity.color)