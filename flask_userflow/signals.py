import blinker

signals = blinker.Namespace()

register_finish = signals.signal("user-register-finish")
