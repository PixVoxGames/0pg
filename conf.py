import os
import re
from envparse import env
from peewee import PostgresqlDatabase

env.read_envfile()


class Settings:
    DB = PostgresqlDatabase(
        database=env("DB_NAME"),
        user=env("DB_USER"),
        password=env("DB_PASSWORD"),
        host=env("DB_HOST"),
        autorollback=True
    )

    SESSION_COOKIE_SECRET_KEY = env("SESSION_COOKIE_SECRET_KEY")
    SECRET_KEY = env("SECRET_KEY")

settings = Settings()
