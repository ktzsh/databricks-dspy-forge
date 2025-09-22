import dspy

from typing import Optional, Any, List, Dict

from databricks_ai_bridge.genie import Genie
from dspy.primitives.prediction import Prediction


class DatabricksGenieRM(dspy.Retrieve):
    def __init__(
        self,
        databricks_genie_space_id: str,
        databricks_genie_space_description: Optional[str] = "",
        databricks_workspace_client: Optional[Any] = None,
        use_with_databricks_agent_framework: bool = False
    ):
        super().__init__()
        self.databricks_genie_space_id = databricks_genie_space_id
        self.use_with_databricks_agent_framework = use_with_databricks_agent_framework
        self.genie = Genie(databricks_genie_space_id, client=databricks_workspace_client)
    
    def forward(
        self,
        query: str,
        history: Optional[list[dict[str, Any]]] = None,
        conversation_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        if history:
            query_with_history = f"I will provide you a chat history. Please help with the provided query based on information described in the chat history.\n\n"
            for i, message in enumerate(history):
                query_with_history += f"Turn {i+1}\n {'\n'.join(f"{key}:{value}" for key, value in message.items())}"
            query_with_history += f"\n\nNow, please help with the following query:\n{query}"
            query = query_with_history
                
        genie_response = self.genie.ask_question(query)

        query_reasoning = genie_response.description or ""
        query_sql = genie_response.query or ""
        query_result = genie_response.result or ""
        conversation_id = conversation_id or genie_response.conversation_id or ""

        if self.use_with_databricks_agent_framework:
            return [
                {
                    "page_content": query_result,
                    "metadata": {
                        "id": conversation_id,
                        "doc_uri": f"genie://{self.databricks_genie_space_id}/{conversation_id}",
                        "query_sql": query_sql,
                        "query_reasoning": query_reasoning,
                    },
                    "type": "Document"
                }
            ]
        else:
            # Returning the prediction
            return Prediction(
                result=[query_result],
                query_sql=query_sql,
                query_reasoning=query_reasoning,
                conversation_id=conversation_id
            )
