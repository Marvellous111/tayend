import os
from dotenv import load_dotenv
from pydantic import BaseModel



class BodyQuery(BaseModel):
  query: str
  username: str


class TaskBody(BaseModel):
  title: str
  username: str
  prompt: str
  time: str
  weekday: str