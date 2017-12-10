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
    )

settings = Settings()
