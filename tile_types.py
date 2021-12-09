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
        ("light", graphic_dt),      # Gráfico para quando o tile está dentro do campo de visão.
    ]
)

def new_tile(
    *, # Força o uso de keywords, para que a ordem do parâmetro não seja relevante.
    walkable: int,
    transparent: int,
    dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
) -> np.ndarray:
    # Função auxiliar para definir os tipos de tiles individuais.
    return np.array((walkable, transparent, dark, light), dtype=tile_dt)

# SHROUD representa tiles não explorados não vistos.
SHROUD = np.array((ord(" "), (255, 255, 255), (0, 0, 0)), dtype=graphic_dt)

floor = new_tile(
    walkable = True,
    transparent = True,
    dark = (ord(" "), (255, 255, 255), (50, 50, 150)),
    light = (ord(" "), (255, 255, 255), (200, 180, 50)),
)

wall = new_tile(
    walkable = False,
    transparent = False,
    dark = (ord(" "), (255, 255, 255), (0, 0, 150)),
    light = (ord(" "), (255, 255, 255), (130, 110, 50)),
)