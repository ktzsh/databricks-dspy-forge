import json
import mlflow

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
    def __init__(self):
        self.program = CompoundProgram()
        # TODO add output field names to program and reference it here

    def _convert_to_dspy_format(self, messages):
        question = messages[-1]['content']

        history = []
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