from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = "test-secret-key-nao-usar-em-producao"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
