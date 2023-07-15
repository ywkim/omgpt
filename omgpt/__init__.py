import argparse
import configparser
import os

from langchain.agents import AgentType, initialize_agent
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.tools import Tool
from prompt_toolkit import PromptSession, prompt
from prompt_toolkit.history import FileHistory

from omgpt.shtool import ShellTool, ShellToolSchema

DEFAULT_CONFIG = {
    "settings": {
        "chat_model": "gpt-3.5-turbo-0613",
        "system_prompt": "You are a shell. Your name is OMGpt.",
        "temperature": "0",
    },
}


def load_config():
    config = configparser.ConfigParser()
    config.read_dict(DEFAULT_CONFIG)
    config.read("config.ini")
    return config


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
        callbacks=[StreamingStdOutCallbackHandler()],
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


def run(agent):
    home = os.path.expanduser("~")
    history = FileHistory(os.path.join(home, ".omgpt_history"))
    session = PromptSession(history=history)

    while True:
        user_input = session.prompt("> ")
        response_message = agent.run(user_input)
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Increase output verbosity"
    )
    args = parser.parse_args()

    config = load_config()
    with ShellTool() as shell_tool:
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
        run(agent)


if __name__ == "__main__":
    main()
