"""Tool that calls SerpAPI and QA."""
import logging
import sys
from typing import Any, Optional, Type

from langchain.callbacks.manager import (AsyncCallbackManagerForToolRun,
                                         CallbackManagerForToolRun)
from langchain.chains.question_answering import load_qa_chain
from langchain.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.llms import OpenAI
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from langchain.tools.base import BaseTool, ToolException
from openai.error import OpenAIError
from pydantic import BaseModel, Field
import subprocess



class ShellToolSchema(BaseModel):
    command: str = Field(description="should be a command to run with subprocess.run(command, shell=True)")


class ShellTool(BaseTool):
    name = "sh"
    description = "useful when you need to run a shell command and get standard output"
    args_schema: Type[ShellToolSchema] = ShellToolSchema

    def _run(
        self,
        command: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        print(f"$ {command}")
        try:
            completed_process = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = completed_process.stdout
            return output
        except OpenAIError as e:
            raise ToolException(str(e)) from e
        except IOError as e:
            raise ToolException(str(e)) from e

    async def _arun(
        self,
        command: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("sh does not support async")
