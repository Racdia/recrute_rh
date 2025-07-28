import os

import requests

from database import engine
from models import Base
import openai


def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
 init_db()