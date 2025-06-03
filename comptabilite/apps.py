# comptabilite/apps.py
from django.apps import AppConfig

class ComptabiliteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comptabilite'
    verbose_name = "Comptabilité Générale" # Optionnel pour l'admin

    def ready(self):
        import comptabilite.signals # Importer et connecter les signaux