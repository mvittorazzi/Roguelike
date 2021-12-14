from typing import Iterable, List, Reversible, Tuple
import textwrap

import tcod

import color

class Message:
    def __init__(self, text: str, fg: Tuple[int, int, int]):
        self.plain_text = text
        self.fg = fg
        self.count = 1

    @property
    def full_text(self) -> str:
        # O texto completo da mensagem, incluindo um contador se necessário.
        if self.count > 1:
            return f"{self.plain_text} (x{self.count})"
        return self.plain_text

class MessageLog:
    def __init__(self) -> None:
        self.messages: List[Message] = []
    
    def add_message(
        self, text: str, fg: Tuple[int, int, int] = color.white, *, stack: bool = True,
    ) -> None:
        # Adiciona uma mensagem ao log.
        # "Text" é a mensagem de texto, "fg" é a cor.
        # Se "stack" for True então a mensagem acumula com a anterior com texto igual.
        if stack and self.messages and text == self.messages[-1].plain_text:
            self.messages[-1].count += 1
        else:
            self.messages.append(Message(text, fg))
    
    def render(
        self, console: tcod.Console, x: int, y: int, width: int, height: int,
    ) -> None:
        # Renderiza o log de mensagem em uma área determinada.
        # "x, "y", "width", "height" são a área retangular onde será renderizado no "console".
        self.render_messages(console, x, y, width, height, self.messages)

    @staticmethod
    def wrap(string: str, width: int) -> Iterable[str]:
        # Retorna uma mensagem com quebra de linha.
        for line in string.splitlines(): # Controla novas linhas em mensagens.
            yield from textwrap.wrap(
                line, width, expand_tabs=True,
            )

    @classmethod
    def render_messages(
        cls,
        console: tcod.console,
        x: int,
        y: int,
        width: int,
        height: int,
        messages: Reversible[Message],
    ) -> None:
        # Renderiza as mensagens recebidas.
        # A variável "messages" é renderizada começando pela última mensagem.
        y_offset = height - 1

        for message in reversed(messages):
            for line in reversed(list(cls.wrap(message.full_text, width))):
                console.print(x=x, y=y + y_offset, string=line, fg=message.fg)
                y_offset -= 1
                if y_offset < 0:
                    return # Sem espaço para eixibir mais mensagens.