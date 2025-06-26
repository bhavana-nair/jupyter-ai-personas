import os
from agno.agent import Agent
from agno.tools.github import GithubTools
from agno.tools.reasoning import ReasoningTools
from agno.models.google import Gemini
from pr_comment_tool import create_pr_comment_with_head_sha

def main():

    github_token = os.getenv('GITHUB_ACCESS_TOKEN')
    if github_token:
        os.environ['GITHUB_ACCESS_TOKEN'] = github_token

    agent = Agent(
        instructions=[
            "You are PR commenter, given a PR, You would comment on the PR what the user would like to say",
            "Use create_pr_comment_with_head_sha to create PR comments - it handles everything automatically"
        ],
        tools=[GithubTools(get_pull_requests=True, get_pull_request_changes=True, 
                           get_file_content = True, get_directory_content= True)
           , ReasoningTools(add_instructions=True, think=True, analyze=True), 
           create_pr_comment_with_head_sha],
        show_tool_calls=True,
        model=Gemini(
            id="gemini-1.5-flash",
            api_key="AIzaSyCkD-2rU7O2Ubsf_iXV9rOZ2fmatZ5IxSA"
        )
    )

    result = agent.run("Comment 'Test' on PR #5 from bhavana-nair/jupyter-ai-personas on file"
    " .github/workflows/run-tests.yml line number 29")

if __name__ == "__main__":
    main()