class Impossible(Exception):
    """Exceção emitida quando uma ação impossível é executada. A razão é dada como a mensagem da exceção."""

class QuitWithoutSaving(SystemExit):
    """Pode ser chamada para fechar o jogo sem salvar."""