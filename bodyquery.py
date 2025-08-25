import os
from typing import TypedDict, List, Dict, Any, NotRequired
from dotenv import load_dotenv
from pydantic import BaseModel
from uuid import uuid4
from bson import ObjectId


class BodyQuery(BaseModel):
  query: str
  username: str


class TaskBody(BaseModel):
  title: str
  username: str
  prompt: str
  time: str
  weekday: str
  
class TaskBodyDict(TypedDict):
  _id: NotRequired[ObjectId]
  title: str
  task_uuid: str
  username: str
  prompt: str
  time: str
  weekday: str
  actions_taken: list
  
class ClassificationAnswer(BaseModel):
  id: str
  category: str
  answer: str