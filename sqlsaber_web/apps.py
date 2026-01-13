from django.apps import AppConfig


class SqlsaberWebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sqlsaber_web"
    # Keep legacy app label so existing migrations and DB tables stay stable.
    label = "sqlsaber"
