import pytest
from unittest.mock import Mock, patch, AsyncMock
from jupyter_ai_personas.pr_review_persona.persona import PRReviewPersona
from jupyterlab_chat.models import Message
from agno.team.team import Team

@pytest.fixture
async def pr_persona():
    # Mock required initialization arguments
    mock_ychat = AsyncMock()
    mock_manager = AsyncMock()
    # mock_manager.outdated_timeout = 30000 

    mock_config = Mock()
    mock_config.lm_provider.name = "test_provider"
    mock_config.lm_provider_params = {"model_id": "test_model"}
    mock_log = Mock()

    persona = PRReviewPersona(
        ychat=mock_ychat,
        manager=mock_manager,
        config=mock_config,
        log=mock_log,
        message_interrupted=AsyncMock()
    )
    return persona

@pytest.fixture
def mock_message():
    message = Mock(spec=Message)
    message.body = "Please review PR #123 in repo owner/repo"
    return message

@patch('jupyter_ai_personas.pr_review_persona.persona.Team')
@patch('agno.tools.github.GithubTools.authenticate')
@patch('boto3.Session')

@pytest.mark.asyncio
async def test_initialize_team(mock_boto_session, mock_github_auth, mock_team_class, pr_persona):
    pr_persona = await pr_persona 

    mock_github_auth.return_value = Mock()
    mock_boto_session.return_value = Mock()
    
    mock_team = Mock()
    mock_code_quality = Mock()
    mock_code_quality.name = "code_quality"
    mock_documentation_checker = Mock()
    mock_documentation_checker.name = "documentation_checker"
    mock_security_checker = Mock()
    mock_security_checker.name = "security_checker"
    mock_github = Mock()
    mock_github.name = "github"
    
    mock_team.members = [
        mock_code_quality,
        mock_documentation_checker,
        mock_security_checker,
        mock_github
        ]
    mock_team_class.return_value = mock_team
    
    with patch('os.getenv', return_value='dummy_token'):
        team = pr_persona.initialize_team("test prompt")
        
    # Verify team structure
    assert team is mock_team 
    assert len(team.members) == 4
    assert team.members[0].name == "code_quality"
    assert team.members[1].name == "documentation_checker"
    assert team.members[2].name == "security_checker"
    assert team.members[3].name == "github"
    
    # Verify Team was instantiated with correct parameters
    mock_team_class.assert_called_once()
    
    # Verify GitHub authentication was called
    mock_github_auth.assert_called()

@pytest.mark.asyncio
async def test_process_message_success(pr_persona, mock_message):
    pr_persona = await pr_persona  
    pr_persona.ychat = Mock()
    pr_persona.ychat.get_messages.return_value = []
    pr_persona.stream_message = AsyncMock()
    mock_team = AsyncMock()
    mock_team.run = AsyncMock(return_value="PR review completed successfully")
    with patch.object(pr_persona, 'initialize_team', return_value=mock_team):
        await pr_persona.process_message(mock_message)
        
        # Test team was initialized and run
        assert pr_persona.initialize_team.called
        assert mock_team.run.called
        #  Test stream_message
        assert pr_persona.stream_message.called

@pytest.mark.asyncio
async def test_process_message_value_error(pr_persona, mock_message):
    # Mock dependencies
    pr_persona = await pr_persona  
    pr_persona.ychat = Mock()
    pr_persona.ychat.get_messages.return_value = []
    pr_persona.stream_message = AsyncMock()
    mock_team = AsyncMock()
    mock_team.run = AsyncMock(side_effect=ValueError("Test error"))
    
    with patch.object(pr_persona, 'initialize_team', return_value=mock_team):
        await pr_persona.process_message(mock_message)
        
        # Verify error was handled and error message was streamed
        call_args = pr_persona.stream_message.call_args[0][0]
        async for message in call_args:
            assert "Configuration Error" in message
            assert "Test error" in message

@pytest.mark.asyncio
async def test_process_message_boto_error(pr_persona, mock_message):
    # Mock dependencies
    pr_persona = await pr_persona 
    pr_persona.ychat = Mock()
    pr_persona.ychat.get_messages.return_value = []
    pr_persona.stream_message = AsyncMock()
    mock_team = AsyncMock()
    mock_team.run = AsyncMock(side_effect=Exception("AWS error"))
    
    with patch.object(pr_persona, 'initialize_team', return_value=mock_team):
        await pr_persona.process_message(mock_message)
        
        # Verify error was handled and error message was streamed
        call_args = pr_persona.stream_message.call_args[0][0]
        async for message in call_args:
            assert "PR Review Error" in message
            assert "AWS error" in message
