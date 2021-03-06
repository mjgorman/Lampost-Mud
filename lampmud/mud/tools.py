def combat_log(source, message, target=None):
    if hasattr(source.env, 'combat_log'):
        try:
            message = message.combat_log()
        except AttributeError:
            try:
                message = message()
            except TypeError:
                pass
        source.env.broadcast(s=message, source=source, target=target)
