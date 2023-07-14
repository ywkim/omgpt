"""Tool that run shell commands."""
import logging
import subprocess
import sys
from typing import Any, Optional, Type

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.chains.question_answering import load_qa_chain
from langchain.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.llms import OpenAI
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from langchain.tools.base import BaseTool, ToolException
from openai.error import OpenAIError
from pydantic import BaseModel, Field


class ShellToolSchema(BaseModel):
    command: str = Field(description="should be a command to run with bash")


class ShellTool:
    def __init__(self):
        self.process = subprocess.Popen(
            "/bin/bash",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.eof_marker = "<EOF_MARKER>"

    def __call__(self, command: str) -> str:
        print(f"$ {command}")
        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.write('echo "{}"\n'.format(self.eof_marker))
            self.process.stdin.flush()
            output = ""
            for line in iter(self.process.stdout.readline, ""):
                if line.strip() == self.eof_marker:
                    break
                output += line
            return output.strip()
        except (OpenAIError, IOError) as e:
            self.process.stdin.close()
            self.process.terminate()
            self.process.wait(timeout=0.2)
            raise ToolException(str(e)) from e


def make_shell_tool():
    shell_tool = ShellTool()
    return Tool.from_function(
        func=shell_tool,
        name="sh",
        description="Useful when you need to run a shell command and get standard output and errors.",
        args_schema=ShellToolSchema,
        handle_tool_error=True,
    )
