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
  
clarification_resolution_list = []

def getresolutionlist():
  return clarification_resolution_list

def fillresolutionlist(resolution: Any):
  clarification_resolution_list.append(resolution)

def emptyresolutionlist():
  clarification_resolution_list.clear()
  
  
paused_plan_run = []
def getpausedplanrunlist():
  return paused_plan_run

def fillpausedplanrunlist(resolution: Any):
  paused_plan_run.append(resolution)

def emptypausedplanrunlist():
  paused_plan_run.clear()