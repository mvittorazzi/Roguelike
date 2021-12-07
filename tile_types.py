from typing import Tuple

import numpy as np # Tipo: ignorado.

# Estrutura dos gráficos dos tiles compatível com Console.tiles_rgb.
graphic_dt = np.dtype(
    [
        ("ch", np.int32),   # Codepoint Unicode.
        ("fg", "3B"),       # 3 bytes unsigned para cores RGB.
        ("bg", "3B"),
    ]
)

# Estrutura usada para dados estaticamente definidos dos tiles.
tile_dt = np.dtype(
    [
        ("walkable", np.bool),      # True se este tile pode ser passável.
        ("transparent", np.bool),   # True se este tile bloqueia o campo de visão.
        ("dark", graphic_dt),       # Gráfico para quando este tile não está no campo de visão.
    ]
)

def new_tile(
    *, # Força o uso de keywords, para que a ordem do parâmetro não seja relevante.
    walkable: int,
    transparent: int,
    dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
) -> np.ndarray:
    # Função auxiliar para definir os tipos de tiles individuais.
    return np.array((walkable, transparent, dark), dtype = tile_dt)

floor = new_tile(
    walkable=True, transparent=True, dark=(ord(" "), (255, 255, 255), (50, 50, 150)),
)

wall = new_tile(
    walkable=False, transparent=False, dark=(ord(" "), (255, 255, 255), (0, 0, 150)),
)