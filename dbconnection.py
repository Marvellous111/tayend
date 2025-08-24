import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


load_dotenv()
uri = os.getenv('CONNECTION_STRING')

# Create a new client and connect to the server
client = AsyncMongoClient(uri, server_api=ServerApi('1'))

# # Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)

def task_helper(tasks) -> dict:
  return {
    "title": tasks["title"],
    "task_id": tasks["task_id"],
    "username": tasks["username"],
    "prompt": tasks["prompt"],
    "time":tasks["time"],
    "weekday": tasks["weekday"],
    "actions_taken": tasks["actions_taken"]
  }