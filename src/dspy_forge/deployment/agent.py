import json
import mlflow
import os

from uuid import uuid4
from typing import (
    Annotated, Any, Generator, Optional, Sequence, TypedDict, Union
)
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

from databricks.sdk import WorkspaceClient
from databricks_ai_bridge import ModelServingUserCredentials

try:
    from program import CompoundProgram
except ImportError:
    import sys
    import os
    # Add the directory containing this file to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from program import CompoundProgram

mlflow.dspy.autolog()

class DSPyResponseAgent(ResponsesAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO add output field names to program and reference it here

    def load_context(self, context):
        self.program_state_path = None
        if context.artifacts:
            self.program_state_path = context.artifacts.get("program_state_path", None)

    def initialize_agent(self):
        # For OBO Auth
        user_authorized_client = WorkspaceClient(
            credentials_strategy=ModelServingUserCredentials()
        )
        self.program = CompoundProgram(
            user_authorized_client=user_authorized_client,
        )

        # Load optimizations from program.json if available
        if self.program_state_path and os.path.exists(self.program_state_path):
            self.program.load(self.program_state_path)
            print(f"Loaded program state from {self.program_state_path}")

    def _convert_to_dspy_format(self, messages):
        question = messages[-1]['content']

        history = []
        # TODO answer is hardcoded instead of using output fields
        for i in range(0, len(messages) - 1, 2):
            if i + 1 < len(messages):
                history.append({
                    'question': messages[i]['content'],
                    'answer': messages[i + 1]['content']
                })
        return question, history

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)

    def predict_stream(
        self,
        request: ResponsesAgentRequest,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        cc_msgs = self.prep_msgs_for_cc_llm([i.model_dump() for i in request.input])
        self.initialize_agent()

        dspy_msgs = self._convert_to_dspy_format(cc_msgs)
        
        output = self.program(*dspy_msgs)

        # TODO Implement Streaming
        for item in [output.answer]: # TODO use derived output field names
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_text_output_item(
                    text=item,
                    id=str(uuid4())
                )
            )


# Create the agent object, and specify it as the agent object to use when
# loading the agent back for inference via mlflow.models.set_model()
agent = DSPyResponseAgent()

mlflow.models.set_model(agent)