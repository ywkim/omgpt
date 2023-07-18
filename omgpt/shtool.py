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

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ShellCommandHistory:
    """
    A class to keep the history of shell commands and their outputs.

    Attributes
    ----------
    last_commands : List[Tuple[str, str]]
        A list to save command and output pairs.
    """

    def __init__(self):
        """Initializes ShellCommandHistory with an empty command list."""
        self.last_commands = []

    def add_command(self, command, output):
        """
        Adds a command and output pair to the command list.

        Parameters
        ----------
        command : str
            The shell command executed.
        output : str
            The output from the command.
        """
        self.last_commands.append((command, output))

    def get_last_commands(self):
        """
        Returns the last commands and output pairs.

        Returns
        -------
        list
            A list of tuples, where each tuple contains a command and its output.
        """
        return self.last_commands

    def clear(self):
        """Clears the command list."""
        self.last_commands = []


class ShellToolSchema(BaseModel):
    command: str = Field(description="should be a command to run with bash")


class ShellTool:
    def __init__(self, command_history):
        self.process = subprocess.Popen(
            "/bin/bash",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.eof_marker = "<EOF_MARKER>"
        self.command_history = command_history

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
            output = output.strip()
            self.command_history.add_command(command, output)
            return output
        except (OpenAIError, IOError) as e:
            logging.error(str(e), exc_info=True)
            raise ToolException(str(e)) from e

    def close(self):
        self.process.stdin.close()
        self.process.terminate()
        self.process.wait(timeout=0.2)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
