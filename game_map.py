import numpy as np
from tcod.console import Console

import tile_types

class GameMap:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.tiles = np.full((width, height), fill_value = tile_types.wall, order = "F")

        self.visible = np.full((width, height), fill_value = False, order = "F") # Tiles que o jogador pode ver.
        self.explored = np.full((width, height), fill_value = False, order = "F") # Tiles que o jogador já viu.
    def in_bounds(self, x: int, y: int) -> bool:
        # Retorna True se x e y estão dentro dos limites do mapa.
        return 0 <= x < self.width and 0 <= y < self.height
    
    def render(self, console: Console) -> None:
        # Renderiza a mapa.
        # Se um tile está no array "visível", então desenha ele com as cores "light".
        # Se não estiver, mas for um tile "explorado", desenha ele com as cores "dark".
        # Senão, o padrão é "SHROUD".
        console.tiles_rgb[0:self.width, 0:self.height] = np.select(
            condlist = [self.visible, self.explored],
            choicelist = [self.tiles["light"], self.tiles["dark"]],
            default = tile_types.SHROUD
        )