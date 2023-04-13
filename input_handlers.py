from __future__ import annotations

import os

from typing import Callable, Optional, Tuple, TYPE_CHECKING, Union

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

CONFIRM_KEYS = {
    tcod.event.K_RETURN,
    tcod.event.K_KP_ENTER,
}

ActionOrHandler = Union[Action, "BaseEventHandler"]
    # Um controlador de eventos que retorna um valor que pode ativar uma ação ou trocar controladores ativos.
    # Se um controlador é retornado então ele se torna o controlador ativo em eventos futuros.
    # Se uma ação é retornada então ela tentará ser executada e se for válida o MainGameEventHandler será o controlador ativo.

class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        # Controla o evento e retorna o próximo controlador de evento ativo.
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):
            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, console: tcod.Console) -> None:
        raise NotImplementedError()
    
    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()

class PopupMessage(BaseEventHandler):
    """Exibe uma janela de texto."""

    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text
    
    def on_render(self, console: tcod.console) -> None:
        """Renderiza o objeto parente e obscurece o resultado, então imprime a mensagem em cima de tudo."""
        self.parent.on_render(console)
        console.tiles_rgb["fg"] //=8
        console.tiles_rgb["bg"] //=8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=tcod.CENTER,
        )

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[BaseEventHandler]:
        """Qualquer tecla retorna ao controlador parente."""
        return self.parent

class EventHandler(BaseEventHandler):
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        # Controla eventos para os controladores de entrada da engine.
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            # Uma ação válida foi executada
            if not self.engine.player.is_alive:
                # O jogador foi morto em algum momento durante ou após a execução da ação.
                return GameOverEventHandler(self.engine)
            return MainGameEventHandler(self.engine)  # Retorna ao controlador principal.
        return self

    def handle_action(self, action: Optional[Action]) -> bool:
        # Controla ações retornadas por métodos de evento.
        # Retorna True se a ação avança um turno.

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

    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)

class AskUserEventHandler(EventHandler):
    # Controla a entrada do usuário para ações que requerem entradas especiais.

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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
    
    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        # Por padrão qualquer clique do mouse sai do input handler.
        return self.on_exit()
    
    def on_exit(self) -> Optional[ActionOrHandler]:
        # Chamado quando o usuário está tentando sair ou cancelar uma ação.
        # Por padrão retorna ao main event handler.

        return MainGameEventHandler(self.engine)

class InventoryEventHandler(AskUserEventHandler):
    # Este handler permite o usuário escolher um item.
    # O que acontece depois depende da subclasse.

    TITLE = "<missing title>"

    def on_render(self, console: tcod.Console) -> None:
        # Renderiza um menu de inventário, que exibe os itens dentro dele e a letra para seleciona-los.
        # Será movido para uma posição diferente baseada na posição do jogador, para que ele sempre veja onde está.

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

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        # Chamado quando o usuário seleciona um item válido.
        raise NotImplementedError()

class InventoryActivateHandler(InventoryEventHandler):
    # Controla o uso de um item do inventário.

    TITLE = "Select an item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        # Retorna a ação para o  item selecionado.
        return item.consumable.get_action(self.engine.player)

class InventoryDropHandler(InventoryEventHandler):
    # Controla a ação de largar um item do inventário.

    TITLE = "Select an item to drop"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        # Larga este item.
        return actions.DropItem(self.engine.player, item)

class SelectIndexHandler(AskUserEventHandler):
    # Lida com a solicitação ao usuário de um índice no mapa

    def __init__(self, engine: Engine):
        # Seta o cursor no jogador quando esse handler é construído.
        super().__init__(engine)
        player = self.engine.player
        engine.mouse_location = player.x, player.y
    
    def on_render(self, console: tcod.Console) -> None:
        # Destaca o tile na posição do cursor.
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.tiles_rgb["bg"][x, y] = color.white
        console.tiles_rgb["fg"][x, y] = color.black
    
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        # Verifica por teclas de movimentação ou confirmação.
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1 # Segurando uma tecla de movimentação aumenta a velocidade de movimento.
            if event.mod & (tcod.event.KMOD_LSHIFT | tcod.event.KMOD_RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KMOD_LCTRL | tcod.event.KMOD_RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KMOD_LALT | tcod.event.KMOD_RALT):
                modifier *= 20
            
            x, y = self.engine.mouse_location
            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            # Limita a posição do mouse ao tamanho do mapa.
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)
        return super().ev_keydown(event)
    
    def ev_mousebuttondown(self, event: tcod.event.MouseButtonDown) -> Optional[ActionOrHandler]:
        # Clique esquerdo confirma a seleção.
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
        return super().ev_mousebuttondown(event)
    
    def on_index_selected(self, x: int, y: int) -> Optional[ActActionOrHandlerion]:
        # Chamado quando um índice é selecionado.
        raise NotImplementedError()

class LookHandler(SelectIndexHandler):
    # Permite ao jogador observar o cenário usando o teclado.
    def on_index_selected(self, x: int, y: int) -> MainGameEventHandler:
        # Retorna ao controlador principal.
        return MainGameEventHandler(self.engine)

class SingleRangedAttackHandler(SelectIndexHandler):
    # Controla a seleção de um inimigo como alvo. Somente o inimigo selecionado é afetado.
    def __init__(
        self, engine: Engine, callback: Callable[[Tuple[int, int]], Optional[Action]]
    ):
        super().__init__(engine)

        self.callback = callback
    
    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

class AreaRangedAttackHandler(SelectIndexHandler):
    # Lida com alvos em um raio de determinada área. Uma entidade dentro da área será afetada.

    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[Action]],
    ):

        super().__init__(engine)

        self.radius = radius
        self.callback = callback

    def on_render(self, console: tcod.Console) -> None:
        # Realça um tile no cursor.
        super().on_render(console)

        x, y = self.engine.mouse_location

        # Desenha um retângulo envolta da área alvo, para que o jogador saiva quais tiles serão afetados.
        console.draw_frame(
            x=x - self.radius - 1,
            y=y - self.radius - 1,
            width=self.radius ** 2,
            height=self.radius ** 2,
            fg=color.red,
            clear=False,
        )
    
    def on_index_selected(self, x: int, y: int) -> Optional[Action]:
        return self.callback((x, y))

class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
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
            return HistoryViewer(self.engine)

        elif key == tcod.event.K_g:
            action = PickupAction(player)

        elif key == tcod.event.K_i:
            return InventoryActivateHandler(self.engine)

        elif key == tcod.event.K_d:
            return InventoryDropHandler(self.engine)

        elif key == tcod.event.K_SLASH:
            return LookHandler(self.engine)

        # Nenhuma tecla válida foi pressionada.
        return action

class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        """Controla a saida do jogo em uma sessão finalizada."""
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav") # Apaga o jogo salvo ativo.
        raise exceptions.QuitWithoutSaving() # Evita salvar um jogo finalizado.

    def ev_quit(self, event: tcod.event.Quit) -> None:
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.K_ESCAPE:
            self.on_quit()

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

    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[MainGameEventHandler]:
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
            return MainGameEventHandler(self.engine)
        return None