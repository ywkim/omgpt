import argparse
import configparser
import os
import sys
from typing import Any, Dict, List

from langchain.agents import AgentType, initialize_agent
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from langchain.schema import LLMResult, SystemMessage
from langchain.tools import Tool
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from omgpt.shtool import ShellCommandHistory, ShellTool, ShellToolSchema

DEFAULT_CONFIG = {
    "settings": {
        "chat_model": "gpt-3.5-turbo-0613",
        "system_prompt": "You are a shell. Your name is OMGpt.",
        "temperature": "0",
    },
}


FULL_OUTPUT = "FULL_OUTPUT"


def load_config(config_file: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read_dict(DEFAULT_CONFIG)
    if os.path.exists(config_file):
        config.read(config_file)
    else:
        raise FileNotFoundError(
            f"Configuration file '{config_file}' not found. Please create one."
        )
    if not config.has_section("api") or not config.has_option("api", "openai_api_key"):
        raise ValueError(
            "Missing required 'openai_api_key' in 'api' section in the configuration file."
        )
    return config


class StreamingHandler(BaseCallbackHandler):
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        self.token_count = 0

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""
        self.token_count += len(token)
        sys.stdout.write(token)
        sys.stdout.flush()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        if self.token_count > 0:
            print()


def init_agent_with_tools(tools, config, verbose):
    system_prompt = SystemMessage(content=config.get("settings", "system_prompt"))
    agent_kwargs = {
        "extra_prompt_messages": [MessagesPlaceholder(variable_name="memory")],
        "system_message": system_prompt,
    }
    memory = ConversationBufferMemory(memory_key="memory", return_messages=True)
    chat = ChatOpenAI(
        model=config.get("settings", "chat_model"),
        temperature=float(config.get("settings", "temperature")),
        openai_api_key=config.get("api", "openai_api_key"),
        request_timeout=60,
        streaming=True,
        callbacks=[StreamingHandler()],
    )
    agent = initialize_agent(
        tools,
        chat,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=verbose,
        agent_kwargs=agent_kwargs,
        memory=memory,
    )
    return agent


def run_interactive(agent, command_history):
    """
    Runs the agent in interactive mode.

    In interactive mode, commands are read one by one from the user's input.
    If the user types 'Ctrl + F', the full output of the last commands executed in shell is printed.

    Parameters
    ----------
    agent : Agent
        The agent to run commands.
    command_history : ShellCommandHistory
        The object to keep track of the command history.
    """
    home = os.path.expanduser("~")
    history = FileHistory(os.path.join(home, ".omgpt_history"))

    bindings = KeyBindings()

    @bindings.add(Keys.ControlF)
    def _(event):
        # Check if the user has already entered something
        if event.app.current_buffer.text:
            # If the user has already entered something, do nothing
            return
        # If the user has not entered anything, exit current prompt session with special result
        event.app.exit(result=FULL_OUTPUT)

    session = PromptSession(history=history, key_bindings=bindings)

    while True:
        user_input = session.prompt("> ")
        if user_input == FULL_OUTPUT:
            for command, output in command_history.get_last_commands():
                print()
                print(f"$ {command}")
                print(output)
        elif user_input:
            # Clear command history when a new user command comes in
            command_history.clear()
            response_message = agent.run(user_input)
        print()

def run_noninteractive(agent, command):
    """
    Runs a single command in non-interactive mode.

    Parameters
    ----------
    agent : Agent
        The agent to run the command.
    command : str
        The command to run.
    """
    response_message = agent.run(command)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Increase output verbosity"
    )
    parser.add_argument(
        "-c", "--command", help="Run a single command in non-interactive mode"
    )
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.omgptrc"),
        help="Path to the config file",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    command_history = ShellCommandHistory()
    with ShellTool(command_history) as shell_tool:
        tools = [
            Tool.from_function(
                func=shell_tool,
                name="sh",
                description="Useful when you need to run a shell command and get standard output and errors.",
                args_schema=ShellToolSchema,
                handle_tool_error=True,
            )
        ]
        agent = init_agent_with_tools(tools, config, verbose=args.verbose)

        if args.command:
            run_noninteractive(agent, args.command)
        else:
            run_interactive(agent, command_history)


if __name__ == "__main__":
    main()
