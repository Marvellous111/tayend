import os
from dotenv import load_dotenv
from typing import Callable, Dict
import asyncio
from queue import Queue
from uuid import uuid4
from portia import (
  Config,LLMProvider,Plan,PlanRun,PortiaToolRegistry,Step, Output,
  InMemoryToolRegistry,DefaultToolRegistry,LLMTool,Portia,StorageClass,LogLevel,
  open_source_tool_registry,example_tool_registry,MultipleChoiceClarification,ActionClarification,InputClarification,
  ValueConfirmationClarification,PlanRunState,ClarificationHandler, ExecutionHooks,Clarification,
)
from portia.cli import CLIExecutionHooks
import json
import threading

#In-memory store for the clarifications to save to the classifications handler
clarifications_list = []
queue = Queue()
def on_step_start(plan: Plan, plan_run: PlanRun, step: Step) -> None:  # noqa: ARG001
  try:
    queue.put(f"data: STEP_START::{step.task}")
  except Exception as e:
    queue.put(f"data: Error::An error occurred before step start")
    queue.put(None)

def on_step_end(plan: Plan, plan_run: PlanRun, step: Step, output) -> None:
  try:
    queue.put(f"data: STEP_RESULT::{step.output if step.output else 'No output'}")
  except Exception as e:
    queue.put(f"data: Error::An error occurred after step end")
    queue.put(None)

def on_plan_end(plan: Plan, plan_run: PlanRun, output) -> None:
  
  try:
    if plan_run.outputs:
      final_output = plan_run.outputs
      queue.put(f"data: ANSWER::{final_output.model_dump_json()}")
      
    queue.put(None)  # signal completion
  except Exception as e:
    queue.put(f"data: Error::An error occurred after plan end")
    queue.put(None)

class WebClarificationHandler(ClarificationHandler):
  """Handles clarification by getting user actions from the web"""
  def handle_input_clarification(
    self,
    clarification: InputClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None],  # noqa: ARG002
  ) -> None:
    """Handle a user input clarifications by asking the user for input from the CLI."""
    user_input = input(f"{clarification.user_guidance}\nPlease enter a value:\n")
    
    # clarification_obj = {
    #   "type": "INPUT",
    #   "clarification_uuid": clarification.uuid,
    #   "plan_id": clarification.plan_run_id,
    #   "response": "",
    # }
    clarifications_list.append(clarification)
    on_resolution(clarification, user_input)
    
  def handle_action_clarification(
    self,
    clarification: ActionClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None]
    ) -> None:
    return super().handle_action_clarification(clarification, on_resolution, on_error)
  
  def handle_value_confirmation_clarification(
    self,
    clarification: ValueConfirmationClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None]
  ) -> None:
    return super().handle_value_confirmation_clarification(clarification, on_resolution, on_error)
  
  def handle_multiple_choice_clarification(
    self,
    clarification: MultipleChoiceClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None]
  ) -> None:
    return super().handle_multiple_choice_clarification(clarification, on_resolution, on_error)


load_dotenv()
GOOGLE_API_KEY=os.getenv('GOOGLE_API_KEY')
#Create the config for the portia instance
my_config = Config.from_default(
  storage_class=StorageClass.CLOUD,
  #default_log_level=LogLevel.DEBUG,
  llm_provider=LLMProvider.GOOGLE,
  default_model="google/gemini-2.5-flash",
  google_api_key=GOOGLE_API_KEY
)
#Instantiate portia here
portia = Portia(
  config=my_config,
  tools=PortiaToolRegistry(my_config) + open_source_tool_registry,
  execution_hooks=ExecutionHooks(
    before_step_execution=on_step_start, # type: ignore
    after_step_execution=on_step_end, # type: ignore
    after_plan_run=on_plan_end, # type: ignore
    clarification_handler=WebClarificationHandler()
  )
)

task_portia = Portia(
  config=my_config,
  tools=PortiaToolRegistry(my_config) + open_source_tool_registry,
  # execution_hooks=ExecutionHooks(
  #   before_step_execution=on_step_start, # type: ignore
  #   after_step_execution=on_step_end, # type: ignore
  #   after_plan_run=on_plan_end, # type: ignore
  #   clarification_handler=WebClarificationHandler()
  # )
)

def createplan(task: str) -> Plan:
  plan = portia.plan(str(task))
  return plan

def runplan(plan: Plan, username: str) -> PlanRun:
  plan_run = portia.run_plan(plan, end_user=f"{username}")
  return plan_run


def taskcreateplan(task: str) -> Plan:
  plan = task_portia.plan(str(task))
  return plan

def taskrunplan(plan: Plan, username: str) -> PlanRun:
  plan_run = task_portia.run_plan(plan, end_user=f"{username}")
  return plan_run