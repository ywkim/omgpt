import argparse
import configparser

from langchain.agents import AgentType, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from langchain.schema import SystemMessage
from prompt_toolkit import prompt

from shtool import make_shell_tool

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


def load_tools():
    return [
        make_shell_tool(),
    ]


def init_agent_with_tools(config, verbose):
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
    )
    tools = load_tools()
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
    while True:
        user_input = prompt("> ")
        response_message = agent.run(user_input)
        print(response_message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help='Increase output verbosity')
    args = parser.parse_args()

    config = load_config()
    agent = init_agent_with_tools(config, verbose=args.verbose)

    run(agent)


if __name__ == "__main__":
    main()
