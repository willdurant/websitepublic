from django.apps import AppConfig


class EnergyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "energy"

    def ready(self):
        from energy.usageUpdater import updater

        updater.start()
