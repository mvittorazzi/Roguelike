from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import tcod

import actions
from actions import (
    Action,
    BumpAction,
    PickupAction,
    WaitAction
)
import color
import exceptions

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item

MOVE_KEYS = {
    # Setas do Teclado.
    tcod.event.K_UP: (0, -1),
    tcod.event.K_DOWN: (0, 1),
    tcod.event.K_LEFT: (-1, 0),
    tcod.event.K_RIGHT: (1, 0),
    tcod.event.K_HOME: (-1, -1),
    tcod.event.K_END: (-1, 1),
    tcod.event.K_PAGEUP: (1, -1),
    tcod.event.K_PAGEDOWN: (1, 1),
    # Teclado Numérico.
    tcod.event.K_KP_1: (-1, 1),
    tcod.event.K_KP_2: (0, 1),
    tcod.event.K_KP_3: (1, 1),
    tcod.event.K_KP_4: (-1, 0),
    tcod.event.K_KP_6: (1, 0),
    tcod.event.K_KP_7: (-1, -1),
    tcod.event.K_KP_8: (0, -1),
    tcod.event.K_KP_9: (1, -1),
    # Teclas Vi.
    tcod.event.K_h: (-1, 0),
    tcod.event.K_j: (0, 1),
    tcod.event.K_k: (0, -1),
    tcod.event.K_l: (1, 0),
    tcod.event.K_y: (-1, -1),
    tcod.event.K_u: (1, -1),
    tcod.event.K_b: (-1, 1),
    tcod.event.K_n: (1, 1),
}

WAIT_KEYS = {
    tcod.event.K_PERIOD,
    tcod.event.K_KP_5,
    tcod.event.K_CLEAR,
}

class EventHandler(tcod.event.EventDispatch[Action]):
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> None:
        self.handle_action(self.dispatch(event))

    def handle_action(self, action: Optional[Action]) -> bool:
        """
        Controle ações retornadas por métodos de evento.
        Retorna True se a ação avança um turno.
        """
        if action is None:
            return False

        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False # Pula o turno do inimigo em exceções.

        self.engine.handle_enemy_turns()

        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.tile.x, event.tile.y):
            self.engine.mouse_location = event.tile.x, event.tile.y

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()

    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)

class AskUserEventHandler(EventHandler):
    # Controla a entrada do usuário para ações que requerem entradas especiais.

    def handle_action(self, action: Optional[Action]) -> bool:
        # Retorna ao event handler principal quando uma ação válida é executada.
        if super().handle_action(action):
            self.engine.event_handler = MainGameEventHandler(self.engine)
            return True
        return False

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        # Por padrão qualquer tecla sai deste input handler.
        if event.sym in { # Ignora teclas de modificação.
            tcod.event.K_LSHIFT,
            tcod.event.K_RSHIFT,
            tcod.event.K_LCTRL,
            tcod.event.K_RCTRL,
            tcod.event.K_LALT,
            tcod.event.K_RALT,
        }:
            return None
        return self.on_exit()
    
    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[Action]:
        # Por padrão qualquer clique do mouse sai do input handler.
        return self.on_exit()
    
    def on_exit(self) -> Optional[Action]:
        """
        Chamado quando o usuário está tentando sair ou cancelar uma ação.

        Por padrão retorna ao main event handler.
        """
        self.engine.event_handler = MainGameEventHandler(self.engine)
        return None

class InventoryEventHandler(AskUserEventHandler):
    """
    Este handler permite o usuário escolher um item.

    O que acontece depois depende da subclasse.
    """

    TITLE = "<missing title>"

    def on_render(self, console: tcod.Console) -> None:
        """
        Renderiza um menu de inventário, que exibe os itens dentro dele e a letra para seleciona-los.
        Será movido para uma posição diferente baseada na posição do jogador, para que ele sempre veja onde está.
        """
        super().on_render(console)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)

        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3
        
        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0
        
        y = 0

        width = len(self.TITLE) + 4

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                console.print(x + 1, y + i + 1, f"({item_key}) {item.name}")
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.K_a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message("Invalid entry.", color.invalid)
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[Action]:
        # Chamado quando o usuário seleciona um item válido.
        raise NotImplementedError()

class InventoryActivateHandler(InventoryEventHandler):
    # Controla o uso de um item do inventário.

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[Action]:
        # Retorna a ação para o  item selecionado.
        return item.consumable.get_action(self.engine.player)

class InventoryDropHandler(InventoryEventHandler):
    # Controla a ação de largar um item do inventário.

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[Action]:
        # Larga este item.
        return actions.DropItem(self.engine.player, item)

class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[Action]:
        action: Optional[Action] = None

        key = event.sym

        player = self.engine.player

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = BumpAction(player, dx, dy)

        elif key in WAIT_KEYS:
            action = WaitAction(player)

        elif key == tcod.event.K_ESCAPE:
            raise SystemExit()

        elif key == tcod.event.K_v:
            self.engine.event_handler = HistoryViewer(self.engine)

        elif key == tcod.event.K_g:
            action = PickupAction(player)

        elif key == tcod.event.K_i:
            self.engine.event_handler = InventoryActivateHandler(self.engine)

        elif key == tcod.event.K_d:
            self.engine.event_handler = InventoryDropHandler(self.engine)

        # Nenhuma tecla válida foi pressionada.
        return action

class GameOverEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.K_ESCAPE:
            raise SystemExit()

CURSOR_Y_KEYS = {
    tcod.event.K_UP: -1,
    tcod.event.K_DOWN: 1,
    tcod.event.K_PAGEUP: -10,
    tcod.event.K_PAGEDOWN: 10,
}

class HistoryViewer(EventHandler):
    # Imprime um histórico em uma janela maior que pode ser navegável.

    def __init__(self, engine: Engine):
        super().__init__(engine)
        self.log_length = len(engine.message_log.messages)
        self.cursor = self.log_length - 1
    
    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console) # Desenha o estado principal como fundo.

        log_console = tcod.Console(console.width - 6, console.height -6)
        
        # Desenha uma borda com uma etiqueta personagelizada.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, " Message history ", alignment=tcod.CENTER
        )

        # Desenha o log de mensagem usando parâmetro de cursor.
        self.engine.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, 3, 3)

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        # Movimento condicional pra ficar bacana. :)
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                # Move a tela do topo para a parte inferior quando está nas bordas.
                self.cursor = self.log_length - 1
            elif adjust > 0 and self.cursor == self.log_length - 1:
                # Idem para o movimento reverso.
                self.cursor = 0
            else:
                # Caso contrário, move a janela enquanto presa aos limites do log de mensagens.
                self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        elif event.sym == tcod.event.K_HOME:
            self.cursor = 0 # Move diretamente para a primeira mensagem.
        elif event.sym == tcod.event.K_END:
            self.cursor = self.log_length - 1 # Move diretamente para a última mensagem.
        else: # Qualquer outra tecla move para o estado inicial.
            self.engine.event_handler = MainGameEventHandler(self.engine)