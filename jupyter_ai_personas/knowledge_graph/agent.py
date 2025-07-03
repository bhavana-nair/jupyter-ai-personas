
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools
from agno.models.google import Gemini
from code_analysis_tool import CodeAnalysisTool
from bulk_analyzer import BulkCodeAnalyzer

def main():

    analyzer = BulkCodeAnalyzer("neo4j://127.0.0.1:7687", ("neo4j", "Bhavana@97"))
    analyzer.analyze_folder("source_code", clear_existing=True)


    agent = Agent(
        instructions=[
             ],
        tools=[ 
            ReasoningTools(add_instructions=True, think=True, analyze=True),
            CodeAnalysisTool()
        ],
        show_tool_calls=True,
        model=Gemini(
            id="gemini-2.5-pro",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
        )
    )
    result = agent.run("Get the source code of process_message function in SoftwareTeamPersona class")
    print(result)

if __name__ == "__main__":
    main()