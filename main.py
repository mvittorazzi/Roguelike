import traceback

import tcod

import color
import exceptions
import input_handlers
import setup_game

def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    """Se o controlador de eventos atual tem uma Engine ativa então ele salva-a."""
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("Game saved.")

def main() -> None:
    screen_width = 80
    screen_height = 50

    tileset = tcod.tileset.load_tilesheet("Anikki_square_10x10.png", 16, 16, tcod.tileset.CHARMAP_CP437)

    handler: input_handlers.BaseEventHandler = setup_game.MainMenu()

    with tcod.context.new_terminal(
        screen_width,
        screen_height,
        tileset=tileset,
        title="PyRogue",
        vsync=True,
    ) as context:
        root_console = tcod.Console(screen_width, screen_height, order = "F")
        try:
            while True:
                root_console.clear()
                handler.on_render(console=root_console)
                context.present(root_console)

                try:
                    for event in tcod.event.wait():
                        context.convert_event(event)
                        handler = handler.handle_events(event)
                except Exception: # Controla exceções no jogo.
                    traceback.print_exc() # Imprime o erro para stderr.
                    # Então imprime o erro no log de mensagens.
                    if isinstance(handler, input_handlers.EventHandler):
                        handler.engine.message_log.add_message(
                            traceback.format_exc(), color.error
                        )
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit: # Salva e sai do jogo.
            save_game(handler, "savegame.sav")
            raise
        except BaseException: # Salva em qualquer exceção não esperada.
            save_game(handler, "savegame.sav")
            raise

if __name__ == "__main__":
    main()