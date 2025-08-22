import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from portiautil import *
from bodyquery import *
import asyncio
import json
import threading
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

# main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from portiautil import createplan, runplan, queue, WebClarificationHandler
from bodyquery import BodyQuery
import json
from uuid import uuid4
from typing import Dict
from portia import PlanRunState, Clarification
from threading import Lock

app = FastAPI()

# Global dict for pending plan_runs and clarifications, with lock for thread safety
pending_plan_runs: Dict[str, 'PlanRun'] = {}
pending_clarifications: Dict[str, Dict] = {}
lock = Lock()


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
Clarifications will be cased in a while loop? but hoe will i get the client to interact with it.
So when clairfication occurs we can return a particular function for the client body to use.

"""

@app.post("/postquery/")
async def postquery(request: Request, body: BodyQuery):
    print(body)
    """Stream the steps to the users"""
    plan = createplan(str(body.query))
    plan_run = runplan(plan, body.username)
    return plan_run.outputs.final_output.value

@app.post("/create-task/")
def createTask(request: Request, body: TaskBody):
    print(body)
    plan = createplan(str(body.prompt))
    plan_run = runplan(plan, body.username)
    
    return { "message": plan_run.outputs.final_output.value } #type: ignore

# if __name__ == "__main__":
#     main()
