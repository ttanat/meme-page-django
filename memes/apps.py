from django.apps import AppConfig


class MemesConfig(AppConfig):
    name = 'memes'

    def ready(self):
        import memes.signals
