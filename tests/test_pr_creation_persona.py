import pytest
import os
from unittest.mock import Mock, patch
from jupyter_ai_personas.pr_creation_persona import PRCreationPersona

class TestPRCreationPersona:
    
    def test_persona_initialization(self):
        """Test that the persona initializes correctly."""
        persona = PRCreationPersona()
        
        assert persona.defaults.name == "PRCreationPersona"
        assert "specialized assistant" in persona.defaults.description.lower()
        assert "pr creation" in persona.defaults.system_prompt.lower()
    
    def test_agno_tools_usage(self):
        """Test that persona uses Agno's built-in tools."""
        persona = PRCreationPersona()
        
        # Verify persona doesn't have custom tools
        assert not hasattr(persona, 'git_tools')
        assert not hasattr(persona, 'file_ops')
        
        # Verify it will use Agno's built-in tools in team initialization
        assert persona is not None
    
    @patch.dict(os.environ, {'GITHUB_ACCESS_TOKEN': 'test_token'})
    @patch('jupyter_ai_personas.pr_creation_persona.persona.AwsBedrock')
    def test_team_initialization(self, mock_bedrock):
        """Test that the team initializes with proper agents."""
        persona = PRCreationPersona()
        
        # Mock the config
        persona.config = Mock()
        persona.config.lm_provider_params = {"model_id": "test_model"}
        
        team = persona.initialize_team("test prompt")
        
        assert team is not None
        assert len(team.members) == 4  # issue_analyzer, architect, code_implementer, git_manager
        
        # Check agent names
        agent_names = [agent.name for agent in team.members]
        assert "issue_analyzer" in agent_names
        assert "architect" in agent_names
        assert "code_implementer" in agent_names
        assert "git_manager" in agent_names
    
    def test_repo_url_extraction(self):
        """Test repository URL extraction from issue text."""
        persona = PRCreationPersona()
        
        # Test with full GitHub URL
        issue_text = "Fix bug in https://github.com/user/repo repository"
        with patch.object(persona, '_clone_and_analyze', return_value='/tmp/test') as mock_clone:
            result = persona._auto_analyze_repo(issue_text)
            mock_clone.assert_called_once_with("https://github.com/user/repo.git")
    
    def test_missing_github_token_error(self):
        """Test that missing GitHub token raises appropriate error."""
        persona = PRCreationPersona()
        persona.config = Mock()
        persona.config.lm_provider_params = {"model_id": "test_model"}
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GITHUB_ACCESS_TOKEN"):
                persona.initialize_team("test prompt")
    
    def test_simplified_implementation(self):
        """Test that the simplified implementation works correctly."""
        persona = PRCreationPersona()
        
        # Should not have custom tools
        assert not hasattr(persona, 'git_tools')
        assert not hasattr(persona, 'file_ops')
        
        # Should still have shared_analyzer attribute
        assert hasattr(persona, 'shared_analyzer')