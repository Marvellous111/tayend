import os
from dotenv import load_dotenv
from typing import Callable, Dict, Any
import asyncio
from queue import Queue
from bodyquery import *
from uuid import uuid4
from portia import (
  Config,LLMProvider,Plan,PlanRun,PortiaToolRegistry,Step, Output, Tool, ToolHardError,
  InMemoryToolRegistry,DefaultToolRegistry,LLMTool,Portia,StorageClass,LogLevel,
  open_source_tool_registry,example_tool_registry,MultipleChoiceClarification,ActionClarification,InputClarification,
  ValueConfirmationClarification,PlanRunState,ClarificationHandler, ExecutionHooks,Clarification, UserVerificationClarification
)
from portia.cli import CLIExecutionHooks
import json
import threading

#In-memory store for the clarifications to save to the classifications handler
#clarifications_list = [] ## This will store the classification we will use for verification
# new_plan_run: PlanRun | None = None
#paused_plan_run_list = []
queue = Queue()
def on_step_start(plan: Plan, plan_run: PlanRun, step: Step) -> None:  # noqa: ARG001
  try:
    previous_clarification = plan_run.get_clarifications_for_step()
    for previous in previous_clarification:
      if not previous or not previous.resolved:
        print("STEP START WITH UNRESOLVED CLARIFICATION, SKIPPING STEP START EVENT")
        # print("ADDED A CLARIFICATION TO QUEUE AND PAUSING TO RERUN LATER")
        # paused_run = portia.wait_for_ready(plan_run)
        # queue.put(None) # We want to stop sending server events here right??
        # fillpausedplanrunlist(paused_run)
    queue.put(f"data: STEP_START::{step.task}\n\n")
  except Exception as e:
    queue.put(f"data: Error::An error occurred before step start\n\n")
    queue.put(None)

def on_step_end(plan: Plan, plan_run: PlanRun, step: Step, output) -> None:
  try:
    queue.put(f"data: STEP_RESULT::{step.output if step.output else 'No output'}\n\n")
  except Exception as e:
    queue.put(f"data: Error::An error occurred after step end\n\n")
    queue.put(None)

def on_plan_end(plan: Plan, plan_run: PlanRun, output) -> None:
  try:
    final_output = plan_run.outputs
    print(final_output)
    queue.put(f"data: ANSWER::{final_output.model_dump_json()}\n\n")
    queue.put(None)  # signal completion
  except Exception as e:
    queue.put(f"data: Error::An error occurred after plan end\n\n")
    queue.put(None)
    
###Clarification | InputClarification | ActionClarification | MultipleChoiceClarification | ValueConfirmationClarification | UserVerificationClarification
   
def before_plan(plan: Plan, plan_run: PlanRun) -> None:
  try:
    print("BEFORE THE PLAN IS RUN THERE MAY BE A CLARIFICATION HERE TO RESOLVE")
    if plan_run.state == PlanRunState.NEED_CLARIFICATION:
      for clarification in plan_run.get_outstanding_clarifications():
        print("Plan run needs clarification:", clarification)
        clarification_dict = {
          "uuid": clarification.id,
          "plan_run_id":plan_run.id,
          "category": clarification.category,
          "step": clarification.step,
          "user_guidance": clarification.user_guidance,
          "resolved": clarification.resolved,
          "response": clarification.response,
        }
        if isinstance(clarification, ActionClarification):
          clarification_dict["action_url"] = clarification.action_url
        if isinstance(clarification, InputClarification):
          clarification_dict["argument"] = clarification.argument_name
        if isinstance(clarification, MultipleChoiceClarification):
          clarification_dict["argument"] = clarification.argument_name
          clarification_dict["response"] = clarification.response
          clarification_dict["options"] = clarification.options
        if isinstance(clarification, ValueConfirmationClarification):
          clarification_dict["argument"] = clarification.argument_name
          clarification_dict["response"] = clarification.response
        if isinstance(clarification, UserVerificationClarification):
          clarification_dict["response"] = clarification.response
          clarification_dict["question"] = ["yes", "no"]
          
        queue.put(f"data: CLARIFICATION::{json.dumps(clarification_dict)}\n\n")
        print("ADDED A CLARIFICATION TO QUEUE AND PAUSING TO RERUN LATER")
      # paused_run = portia.wait_for_ready(plan_run)
      # queue.put(None)
      # fillpausedplanrunlist(paused_run)
  except Exception as e:
    queue.put(f"data: Error::An error occurred before plan start\n\n")
    queue.put(None)
    
    
    
def before_clarify_tools(
  tool: Tool,
  args: dict[str, Any],
  plan_run: PlanRun,
  step: Step
  ) -> Clarification | None:
  try:
    print("TRY TOOL CALL")
    previous_clarification = plan_run.get_clarifications_for_step()
    
    print(previous_clarification)
    
    if len(previous_clarification) > 0:
      for clarification in previous_clarification:
        if not clarification or not clarification.resolved:
          if isinstance(clarification, ActionClarification):
            clarification_dict = {
              "uuid": clarification.id,
              "plan_run_id":plan_run.id,
              "category": clarification.category,
              "step": clarification.step,
              "user_guidance": clarification.user_guidance,
              "resolved": clarification.resolved,
              "action_url": clarification.action_url,
            }
            # clarifications_list.append(clarification)
            queue.put(f"data: CLARIFICATION::{json.dumps(clarification_dict)}\n\n")
          elif isinstance(clarification, InputClarification):
            clarification_dict = {
              "uuid": clarification.id,
              "plan_run_id":plan_run.id,
              "category": clarification.category,
              "step": clarification.step,
              "user_guidance": clarification.user_guidance,
              "resolved": clarification.resolved,
              "argument": clarification.argument_name,
            }
            # clarifications_list.append(clarification)
            queue.put(f"data: CLARIFICATION::{json.dumps(clarification_dict)}\n\n")
          elif isinstance(clarification, MultipleChoiceClarification):
            clarification_dict = {
              "uuid": clarification.id,
              "plan_run_id":plan_run.id,
              "category": clarification.category,
              "step": clarification.step,
              "user_guidance": clarification.user_guidance,
              "resolved": clarification.resolved,
              "argument": clarification.argument_name,
              "response": clarification.response,
              "options": clarification.options
            }
            # clarifications_list.append(clarification)
            queue.put(f"data: CLARIFICATION::{json.dumps(clarification_dict)}\n\n")
          elif isinstance(clarification, ValueConfirmationClarification):
            clarification_dict = {
              "uuid": clarification.id,
              "plan_run_id":plan_run.id,
              "category": clarification.category,
              "step": clarification.step,
              "user_guidance": clarification.user_guidance,
              "resolved": clarification.resolved,
              "argument": clarification.argument_name,
              "response": clarification.response,
            }
            # clarifications_list.append(clarification)
            queue.put(f"data: CLARIFICATION::{json.dumps(clarification_dict)}\n\n")
          elif isinstance(clarification, UserVerificationClarification):
            clarification_dict = {
              "uuid": clarification.id,
              "plan_run_id":plan_run.id,
              "category": clarification.category,
              "step": clarification.step,
              "user_guidance": clarification.user_guidance,
              "resolved": clarification.resolved,
              "response": clarification.response,
              "question": ["yes", "no"]
            }
            # clarifications_list.append(clarification)
            queue.put(f"data: CLARIFICATION::{json.dumps(clarification_dict)}\n\n")
            
            
          print("ADDED A CLARIFICATION TO QUEUE AND PAUSING TO RERUN LATER")
          # paused_run = portia.wait_for_ready(plan_run)
          # queue.put(None) # We want to stop sending server events here right??
          # fillpausedplanrunlist(paused_run)
          #paused_plan_run_list = [new_plan_run]
            
          return clarification
        
        if clarification.response == None:
          raise ToolHardError(f"User rejected tool call to {tool.name} with args {args}")
    else:
      return None
  except Exception as e:
    queue.put(f"data: Error::An error occurred after plan end\n\n")
    queue.put(None)


def after_clarify_tool(
  tool: Tool,
  args: dict[str, Any],
  plan_run: PlanRun,
  step: Step,
  ) -> Clarification | None:
  try:
    plan_run_clarifications = plan_run.get_clarifications_for_step()
    for resolved_clarifications in plan_run_clarifications:
      if resolved_clarifications or resolved_clarifications.resolved: 
        queue.put(f"data: CLARIFICATION_END::Resolved clarification")
  except Exception as e:
    queue.put(f"data: Error::An error occurred after plan end\n\n")
    queue.put(None)

class WebClarificationHandler(ClarificationHandler):
  """Handles clarification by getting user actions from the web"""
  def handle_input_clarification(
    self,
    clarification: InputClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None],
  ) -> None:
    """Get the input from the web and process it here"""
    
    get_resolved = getresolutionlist()
    
    on_resolution(clarification, get_resolved[0])    
    queue.put(f"data: STEP_RESULT::Input clarification resolved\n\n")
    emptyresolutionlist()
    
  def handle_action_clarification(
    self,
    clarification: ActionClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None]
    ) -> None:
    print("ACTION CLARIFICATION CALLED")
    get_resolved = getresolutionlist()
    on_resolution(clarification, get_resolved[0])
    queue.put(f"data: STEP_RESULT::Action clarification resolved\n\n") 
    emptyresolutionlist()
  
  def handle_value_confirmation_clarification(
    self,
    clarification: ValueConfirmationClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None]
  ) -> None:
    get_resolved = getresolutionlist()
    on_resolution(clarification, get_resolved[0])
    queue.put(f"data: STEP_RESULT::Action clarification resolved\n\n") 
    emptyresolutionlist()
  
  def handle_multiple_choice_clarification(
    self,
    clarification: MultipleChoiceClarification,
    on_resolution: Callable[[Clarification, object], None],
    on_error: Callable[[Clarification, object], None]
  ) -> None:
    get_resolved = getresolutionlist()
    on_resolution(clarification, get_resolved[0])
    queue.put(f"data: STEP_RESULT::Action clarification resolved\n\n") 
    emptyresolutionlist()


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
    before_plan_run=before_plan,
    after_plan_run=on_plan_end, # type: ignore
    before_tool_call=before_clarify_tools,
    after_tool_call=after_clarify_tool,
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