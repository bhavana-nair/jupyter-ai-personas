
import os
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools
from agno.models.google import Gemini
from code_analysis_tool import CodeAnalysisTool

def main():

    agent = Agent(
        instructions=[
             ],
        tools=[ 
            ReasoningTools(add_instructions=True, think=True, analyze=True),
            CodeAnalysisTool()
        ],
        show_tool_calls=True,
        model=Gemini(
            id="gemini-1.5-flash",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
        )
    )
    #result = agent.run("hi")

    # result = agent.run("Analyze zoo.py and tell me what classes inherit from Animal")
    result = agent.run("Get the source code of process_message function in SoftwareTeamPersona class")
    print(result)


if __name__ == "__main__":
    main()