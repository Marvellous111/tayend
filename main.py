import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from portiautil import *
from bodyquery import *
from dbconnection import *
from typing import List
import asyncio
import json
from bson import ObjectId
import threading
from uuid import uuid4
from fastapi_crons import Crons, get_cron_router
from sse_starlette.sse import EventSourceResponse

app = FastAPI()
crons = Crons(app)

app.include_router(get_cron_router())

# Global dict for pending plan_runs and clarifications, with lock for thread safety
pending_plan_runs: Dict[str, 'PlanRun'] = {}
pending_clarifications: Dict[str, Dict] = {}
# lock = Lock()


task = """
Go through my current day emails on my gmail and simply get the ones you deem important to me right now,
no promotional email and all that, just important emails, perhaps about deadlines, hackathons and all that
Ignore the links and just retrieve the texts. At the end of everything i only want to see texts, ignore any characters for now that isnt pure texts, this inlcudes unicode characters, emojis, they arent necessary
Once you are done, make a summarized bullet point list of all the important stuff happening
"""


@app.get("/") # Should main be post or we have a dedicated post query (dedicated seems best)
def main():
    return { "message": f"Portia AI Labs SSE demo running " }

"""
Clarifications will be cased in a while loop? but how will i get the client to interact with it.
So when clairfication occurs we can return a particular function for the client body to use.

"""

@app.post("/postquery/")
async def postquery(request: Request, body: BodyQuery):
    print(body)
    """Stream the steps to the users"""
    plan = createplan(str(body.query))
    plan_run = runplan(plan, body.username)
    
    output = plan_run.outputs
    
    output_str = output.model_dump()
    print(f"Final plan_run output is: {output_str}")
    return {
        "message": output_str
    }


###We want to use this to save the task to a mongodb instance with the username right?
###Hence we can use the username to get the task from the database
###
@app.post("/create-task/")
async def createTask(request: Request, body: TaskBody):
    ### This function is just to add the task to the db for later cron use
    print(body)
    try:
        tasks_db = client["CronTasks"]
        tasks_collection = tasks_db.get_collection("tasks_collection")
        task_uuid = uuid4()
        weekday_dict = {
            "0": "sunday",
            "1": "monday",
            "2": "tuesday",
            "3": "wednesday",
            "4": "thursday",
            "5": "friday",
            "6": "saturday",
            "0": "day"
        }
        task_data = {
          "_id": ObjectId(),
          "title": str(body.title),
          "task_id": str(task_uuid),
          "username": str(body.username),
          "prompt": str(body.prompt),
          "time": str(body.time),
          "weekday": weekday_dict[str(body.weekday)],
          "actions_taken":[]
        }
        sendtask = await tasks_collection.insert_one(task_data)
        temp_task_hour = str(body.time[0:2])
        temp_task_minute = str(body.time[3:])
        task_minute = int(temp_task_minute)
        task_hour = int(temp_task_hour)
        weekday = int(body.weekday)
        if weekday == 7:
            weekday = "*"
        if task_minute > 0:
            task_minute = f"*/{str(task_minute)}"
        print(f"{str(task_minute)} {str(task_hour)} * * {str(weekday)}")
        
        @crons.cron(f"{str(task_minute)} {str(task_hour)} * * {str(weekday)}",name="task_actions", tags=["tasks"])
        async def start_action():
            plan = createplan(str(body.prompt))
            plan_run = runplan(plan, body.username)
            output = plan_run.outputs
            print(output.model_dump_json(indent=2))
            
            
            task_action = await tasks_collection.find_one({ "plan_id": str(task_uuid) })
            if task_action is None:
                raise HTTPException(status_code=500, detail="Task not found") 
            task_action["actions_taken"].push(plan_run.outputs.model_dump())

        get_tasks = tasks_collection.find({"username": str(body.username)})
        gotten_tasks = []
        async for task in get_tasks:
            gotten_tasks.append(task_helper(task))
        # print(f"Task added with id: {sendtask.inserted_id}")
        return { 
            "message": gotten_tasks
        }
    except Exception as e:
        print(f"Error adding task: {e}")
        raise HTTPException(status_code=500, detail="Error adding task") 
    
    # plan = createplan(str(body.prompt))
    # plan_run = runplan(plan, body.username)
    

###This will get the tasks linked to the username
@app.get("/gettasks/{username}")
async def stream_steps(request: Request, username: str):
    try:
        task_db = client["CronTasks"]
        task_collection = task_db.get_collection("tasks_collection")
        # So we are basically going to get the collections based on the user name
        get_tasks = task_collection.find({ "username": username })
        gotten_tasks = []
        async for task in get_tasks:
            gotten_tasks.append(task_helper(task))
            
        return {
            "message": gotten_tasks
        }
    except Exception as e:
        print(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail="Error getting task") 


import uvicorn

if __name__ == "__main__":
    uvicorn.run("server.app:app", host="127.0.0.1", port=8000, reload=True)