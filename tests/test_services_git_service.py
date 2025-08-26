"""Unit tests for GitService."""

import pytest
from unittest.mock import Mock, MagicMock
from src.claude_tasker.services.git_service import GitService
from src.claude_tasker.services.command_executor import CommandExecutor, CommandResult, CommandErrorType


class TestGitService:
    """Test cases for GitService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_executor = Mock(spec=CommandExecutor)
        self.git_service = GitService(self.mock_executor)
    
    def _create_command_result(self, success=True, stdout="", stderr="", returncode=0):
        """Helper to create CommandResult objects."""
        return CommandResult(
            returncode=returncode if not success else 0,
            stdout=stdout,
            stderr=stderr,
            command="git test",
            execution_time=0.1,
            error_type=CommandErrorType.SUCCESS if success else CommandErrorType.GENERAL_ERROR,
            attempts=1,
            success=success
        )
    
    def test_init(self):
        """Test GitService initialization."""
        executor = Mock()
        logger = Mock()
        service = GitService(executor, logger)
        
        assert service.executor == executor
        assert service.logger == logger
    
    def test_status(self):
        """Test git status command."""
        expected_result = self._create_command_result(stdout="M file.py")
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.status()
        
        self.mock_executor.execute.assert_called_once_with(['git', 'status'], cwd=None)
        assert result == expected_result
    
    def test_status_porcelain(self):
        """Test git status with porcelain format."""
        expected_result = self._create_command_result(stdout="M  file.py")
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.status(porcelain=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'status', '--porcelain'], cwd=None)
        assert result == expected_result
    
    def test_add(self):
        """Test git add command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.add(['file1.py', 'file2.py'])
        
        self.mock_executor.execute.assert_called_once_with(['git', 'add', 'file1.py', 'file2.py'], cwd=None)
        assert result == expected_result
    
    def test_commit(self):
        """Test git commit command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.commit("Test commit message")
        
        self.mock_executor.execute.assert_called_once_with(
            ['git', 'commit', '-m', 'Test commit message'], cwd=None
        )
        assert result == expected_result
    
    def test_commit_allow_empty(self):
        """Test git commit with allow empty flag."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.commit("Empty commit", allow_empty=True)
        
        self.mock_executor.execute.assert_called_once_with(
            ['git', 'commit', '-m', 'Empty commit', '--allow-empty'], cwd=None
        )
        assert result == expected_result
    
    def test_push_basic(self):
        """Test basic git push command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.push()
        
        self.mock_executor.execute.assert_called_once_with(['git', 'push', 'origin'], cwd=None)
        assert result == expected_result
    
    def test_push_with_branch(self):
        """Test git push with specific branch."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.push(branch="feature-branch")
        
        self.mock_executor.execute.assert_called_once_with(['git', 'push', 'origin', 'feature-branch'], cwd=None)
        assert result == expected_result
    
    def test_push_set_upstream(self):
        """Test git push with upstream flag."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.push(branch="feature-branch", set_upstream=True)
        
        self.mock_executor.execute.assert_called_once_with(
            ['git', 'push', '-u', 'origin', 'feature-branch'], cwd=None
        )
        assert result == expected_result
    
    def test_push_force(self):
        """Test git push with force flag."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.push(force=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'push', 'origin', '--force'], cwd=None)
        assert result == expected_result
    
    def test_pull(self):
        """Test git pull command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.pull()
        
        self.mock_executor.execute.assert_called_once_with(['git', 'pull', 'origin'], cwd=None)
        assert result == expected_result
    
    def test_pull_with_branch(self):
        """Test git pull with specific branch."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.pull(branch="main")
        
        self.mock_executor.execute.assert_called_once_with(['git', 'pull', 'origin', 'main'], cwd=None)
        assert result == expected_result
    
    def test_checkout(self):
        """Test git checkout command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.checkout("feature-branch")
        
        self.mock_executor.execute.assert_called_once_with(['git', 'checkout', 'feature-branch'], cwd=None)
        assert result == expected_result
    
    def test_checkout_create(self):
        """Test git checkout with create flag."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.checkout("new-branch", create=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'checkout', '-b', 'new-branch'], cwd=None)
        assert result == expected_result
    
    def test_branch_list(self):
        """Test git branch list command."""
        expected_result = self._create_command_result(stdout="* main\n  feature-branch")
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.branch()
        
        self.mock_executor.execute.assert_called_once_with(['git', 'branch'], cwd=None)
        assert result == expected_result
    
    def test_branch_list_all(self):
        """Test git branch list all command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.branch(list_all=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'branch', '-a'], cwd=None)
        assert result == expected_result
    
    def test_branch_delete(self):
        """Test git branch delete command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.branch(name="old-branch", delete=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'branch', '-d', 'old-branch'], cwd=None)
        assert result == expected_result
    
    def test_branch_force_delete(self):
        """Test git branch force delete command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.branch(name="old-branch", delete=True, force_delete=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'branch', '-D', 'old-branch'], cwd=None)
        assert result == expected_result
    
    def test_merge(self):
        """Test git merge command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.merge("feature-branch")
        
        self.mock_executor.execute.assert_called_once_with(['git', 'merge', 'feature-branch'], cwd=None)
        assert result == expected_result
    
    def test_merge_no_ff(self):
        """Test git merge with no-ff flag."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.merge("feature-branch", no_ff=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'merge', '--no-ff', 'feature-branch'], cwd=None)
        assert result == expected_result
    
    def test_fetch(self):
        """Test git fetch command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.fetch()
        
        self.mock_executor.execute.assert_called_once_with(['git', 'fetch', 'origin'], cwd=None)
        assert result == expected_result
    
    def test_fetch_prune(self):
        """Test git fetch with prune flag."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.fetch(prune=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'fetch', 'origin', '--prune'], cwd=None)
        assert result == expected_result
    
    def test_log(self):
        """Test git log command."""
        expected_result = self._create_command_result(stdout="commit abc123...")
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.log()
        
        self.mock_executor.execute.assert_called_once_with(['git', 'log'], cwd=None)
        assert result == expected_result
    
    def test_log_with_options(self):
        """Test git log with options."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.log(max_count=10, oneline=True, since="2023-01-01")
        
        self.mock_executor.execute.assert_called_once_with(
            ['git', 'log', '-n', '10', '--oneline', '--since', '2023-01-01'], cwd=None
        )
        assert result == expected_result
    
    def test_diff(self):
        """Test git diff command."""
        expected_result = self._create_command_result(stdout="diff --git a/file.py...")
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.diff()
        
        self.mock_executor.execute.assert_called_once_with(['git', 'diff'], cwd=None)
        assert result == expected_result
    
    def test_diff_cached(self):
        """Test git diff cached command."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        result = self.git_service.diff(cached=True)
        
        self.mock_executor.execute.assert_called_once_with(['git', 'diff', '--cached'], cwd=None)
        assert result == expected_result
    
    def test_current_branch(self):
        """Test current_branch helper method."""
        expected_result = self._create_command_result(stdout="feature-branch\n")
        self.mock_executor.execute.return_value = expected_result
        
        branch = self.git_service.current_branch()
        
        # Should call rev_parse with --abbrev-ref HEAD
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert args[0][1] == 'rev-parse'  # git rev-parse
        assert '--abbrev-ref' in args[0]
        assert 'HEAD' in args[0]
        
        assert branch == "feature-branch"
    
    def test_current_branch_failure(self):
        """Test current_branch when command fails."""
        expected_result = self._create_command_result(success=False)
        self.mock_executor.execute.return_value = expected_result
        
        branch = self.git_service.current_branch()
        
        assert branch is None
    
    def test_is_clean_true(self):
        """Test is_clean when repository is clean."""
        expected_result = self._create_command_result(stdout="")  # Empty output means clean
        self.mock_executor.execute.return_value = expected_result
        
        is_clean = self.git_service.is_clean()
        
        # Should call status --porcelain
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert 'status' in args[0]
        assert '--porcelain' in args[0]
        
        assert is_clean is True
    
    def test_is_clean_false(self):
        """Test is_clean when repository has changes."""
        expected_result = self._create_command_result(stdout="M file.py\n")
        self.mock_executor.execute.return_value = expected_result
        
        is_clean = self.git_service.is_clean()
        
        assert is_clean is False
    
    def test_has_changes_true(self):
        """Test has_changes when there are changes."""
        expected_result = self._create_command_result(stdout="diff --git a/file.py...")
        self.mock_executor.execute.return_value = expected_result
        
        has_changes = self.git_service.has_changes()
        
        # Should call diff
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert 'diff' in args[0]
        
        assert has_changes is True
    
    def test_has_changes_false(self):
        """Test has_changes when there are no changes."""
        expected_result = self._create_command_result(stdout="")
        self.mock_executor.execute.return_value = expected_result
        
        has_changes = self.git_service.has_changes()
        
        assert has_changes is False
    
    def test_branch_exists_true(self):
        """Test branch_exists when branch exists."""
        expected_result = self._create_command_result(stdout="refs/heads/feature-branch abc123")
        self.mock_executor.execute.return_value = expected_result
        
        exists = self.git_service.branch_exists("feature-branch")
        
        # Should call show-ref
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert 'show-ref' in args[0]
        assert 'refs/heads/feature-branch' in args[0]
        
        assert exists is True
    
    def test_branch_exists_false(self):
        """Test branch_exists when branch doesn't exist."""
        expected_result = self._create_command_result(stdout="")
        self.mock_executor.execute.return_value = expected_result
        
        exists = self.git_service.branch_exists("nonexistent-branch")
        
        assert exists is False
    
    def test_branch_exists_remote(self):
        """Test branch_exists for remote branch."""
        expected_result = self._create_command_result(stdout="refs/remotes/origin/feature abc123")
        self.mock_executor.execute.return_value = expected_result
        
        exists = self.git_service.branch_exists("feature", remote=True)
        
        # Should check refs/remotes/origin/feature
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert 'refs/remotes/origin/feature' in args[0]
        
        assert exists is True
    
    def test_get_remote_url(self):
        """Test get_remote_url method."""
        expected_result = self._create_command_result(stdout="git@github.com:user/repo.git\n")
        self.mock_executor.execute.return_value = expected_result
        
        url = self.git_service.get_remote_url()
        
        # Should call remote get-url origin
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert 'remote' in args[0]
        assert 'get-url' in args[0]
        assert 'origin' in args[0]
        
        assert url == "git@github.com:user/repo.git"
    
    def test_get_remote_url_failure(self):
        """Test get_remote_url when command fails."""
        expected_result = self._create_command_result(success=False)
        self.mock_executor.execute.return_value = expected_result
        
        url = self.git_service.get_remote_url()
        
        assert url is None
    
    def test_get_commit_hash(self):
        """Test get_commit_hash method."""
        expected_result = self._create_command_result(stdout="abc123f\n")
        self.mock_executor.execute.return_value = expected_result
        
        commit_hash = self.git_service.get_commit_hash()
        
        # Should call rev-parse HEAD --short
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert 'rev-parse' in args[0]
        assert 'HEAD' in args[0]
        assert '--short' in args[0]
        
        assert commit_hash == "abc123f"
    
    def test_get_commit_hash_full(self):
        """Test get_commit_hash with full hash."""
        expected_result = self._create_command_result(stdout="abc123f456def...\n")
        self.mock_executor.execute.return_value = expected_result
        
        commit_hash = self.git_service.get_commit_hash(short=False)
        
        # Should call rev-parse without --short
        self.mock_executor.execute.assert_called_once()
        args, kwargs = self.mock_executor.execute.call_args
        assert 'rev-parse' in args[0]
        assert '--short' not in args[0]
        
        assert commit_hash.startswith("abc123f456def")
    
    def test_cwd_parameter_propagation(self):
        """Test that cwd parameter is properly passed through."""
        expected_result = self._create_command_result()
        self.mock_executor.execute.return_value = expected_result
        
        self.git_service.status(cwd="/tmp")
        
        self.mock_executor.execute.assert_called_once_with(['git', 'status'], cwd="/tmp")
    
    def test_with_custom_logger(self):
        """Test GitService with custom logger."""
        mock_logger = Mock()
        mock_executor = Mock()
        
        service = GitService(mock_executor, mock_logger)
        
        assert service.logger == mock_logger