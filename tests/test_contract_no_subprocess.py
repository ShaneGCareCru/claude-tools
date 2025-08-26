"""Contract tests to verify no direct subprocess calls in refactored modules."""

import ast
import os
from pathlib import Path
import pytest


class SubprocessCallVisitor(ast.NodeVisitor):
    """AST visitor to find subprocess calls."""
    
    def __init__(self):
        self.subprocess_calls = []
        self.subprocess_imports = []
    
    def visit_Import(self, node):
        """Check for subprocess imports."""
        for alias in node.names:
            if alias.name == 'subprocess':
                self.subprocess_imports.append({
                    'type': 'import',
                    'line': node.lineno,
                    'name': alias.name,
                    'asname': alias.asname
                })
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Check for subprocess imports."""
        if node.module == 'subprocess':
            for alias in node.names:
                self.subprocess_imports.append({
                    'type': 'from_import',
                    'line': node.lineno,
                    'module': node.module,
                    'name': alias.name,
                    'asname': alias.asname
                })
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check for subprocess.* calls."""
        if (isinstance(node.value, ast.Name) and 
            node.value.id == 'subprocess' and 
            node.attr in ['run', 'call', 'Popen', 'check_output']):
            self.subprocess_calls.append({
                'type': 'attribute',
                'line': node.lineno,
                'call': f'subprocess.{node.attr}'
            })
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check for direct subprocess function calls."""
        if (isinstance(node.func, ast.Name) and 
            node.func.id in ['run', 'call', 'Popen', 'check_output']):
            self.subprocess_calls.append({
                'type': 'direct_call',
                'line': node.lineno,
                'call': node.func.id
            })
        self.generic_visit(node)


def analyze_file_for_subprocess_calls(file_path: Path):
    """Analyze a Python file for subprocess calls."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        visitor = SubprocessCallVisitor()
        visitor.visit(tree)
        
        return {
            'file': str(file_path),
            'subprocess_imports': visitor.subprocess_imports,
            'subprocess_calls': visitor.subprocess_calls
        }
    except Exception as e:
        return {
            'file': str(file_path),
            'error': str(e),
            'subprocess_imports': [],
            'subprocess_calls': []
        }


class TestSubprocessContractViolations:
    """Test that refactored modules don't use subprocess directly."""
    
    @pytest.fixture
    def refactored_modules(self):
        """List of modules that should not have direct subprocess calls."""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src" / "claude_tasker"
        
        # These modules have been refactored to use services
        refactored_files = [
            src_dir / "branch_manager.py",
            src_dir / "pr_body_generator.py", 
            src_dir / "prompt_builder.py",
            src_dir / "environment_validator.py",
            src_dir / "workspace_manager.py"
        ]
        
        # Filter to only existing files
        return [f for f in refactored_files if f.exists()]
    
    @pytest.fixture
    def allowed_subprocess_modules(self):
        """List of modules that are still allowed to use subprocess."""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src" / "claude_tasker"
        
        # These modules are legacy or have specific reasons to use subprocess
        allowed_files = [
            src_dir / "base.py",  # Legacy module with old CommandExecutor
            src_dir / "github_client.py",  # Will be deprecated in favor of gh_service
        ]
        
        return [f for f in allowed_files if f.exists()]
    
    @pytest.fixture
    def service_modules(self):
        """List of service modules - these contain controlled subprocess usage."""
        project_root = Path(__file__).parent.parent
        services_dir = project_root / "src" / "claude_tasker" / "services"
        
        service_files = []
        if services_dir.exists():
            service_files = list(services_dir.glob("*.py"))
            # Exclude __init__.py
            service_files = [f for f in service_files if f.name != "__init__.py"]
        
        return service_files
    
    def test_refactored_modules_no_subprocess_calls(self, refactored_modules):
        """Test that refactored modules don't have direct subprocess calls."""
        violations = []
        
        for module_path in refactored_modules:
            analysis = analyze_file_for_subprocess_calls(module_path)
            
            if analysis.get('error'):
                pytest.fail(f"Error analyzing {module_path}: {analysis['error']}")
            
            # Check for subprocess imports (should not have any)
            if analysis['subprocess_imports']:
                for imp in analysis['subprocess_imports']:
                    violations.append(
                        f"{module_path.name}:{imp['line']} - "
                        f"subprocess import: {imp}"
                    )
            
            # Check for subprocess calls (should not have any)
            if analysis['subprocess_calls']:
                for call in analysis['subprocess_calls']:
                    violations.append(
                        f"{module_path.name}:{call['line']} - "
                        f"subprocess call: {call['call']}"
                    )
        
        if violations:
            violation_msg = "\\n".join(violations)
            pytest.fail(
                f"Found subprocess usage in refactored modules:\\n{violation_msg}\\n\\n"
                f"These modules should use dependency-injected services instead of "
                f"direct subprocess calls."
            )
    
    def test_service_modules_controlled_subprocess_usage(self, service_modules):
        """Test that service modules have controlled subprocess usage."""
        for module_path in service_modules:
            analysis = analyze_file_for_subprocess_calls(module_path)
            
            if analysis.get('error'):
                pytest.fail(f"Error analyzing {module_path}: {analysis['error']}")
            
            # Services can import subprocess
            subprocess_imports = analysis['subprocess_imports']
            
            # Services can use subprocess, but let's verify they're using it appropriately
            subprocess_calls = analysis['subprocess_calls']
            
            # CommandExecutor service should have subprocess calls (it's the centralized place)
            if module_path.name == "command_executor.py":
                assert len(subprocess_calls) > 0, (
                    f"CommandExecutor service should contain subprocess calls, "
                    f"but found none in {module_path}"
                )
                
                # Should have subprocess.run calls
                run_calls = [call for call in subprocess_calls 
                           if call['call'] in ['subprocess.run', 'run']]
                assert len(run_calls) > 0, (
                    f"CommandExecutor should use subprocess.run, "
                    f"but found no run calls in {module_path}"
                )
            
            # Other services should not have subprocess calls (they should use CommandExecutor)
            elif module_path.name in ["git_service.py", "gh_service.py"]:
                if subprocess_calls:
                    violations = []
                    for call in subprocess_calls:
                        violations.append(f"{module_path.name}:{call['line']} - {call['call']}")
                    
                    pytest.fail(
                        f"Service modules should delegate to CommandExecutor, not use "
                        f"subprocess directly:\\n" + "\\n".join(violations)
                    )
    
    def test_services_directory_exists(self):
        """Test that services directory was created."""
        project_root = Path(__file__).parent.parent
        services_dir = project_root / "src" / "claude_tasker" / "services"
        
        assert services_dir.exists(), "Services directory should exist"
        assert services_dir.is_dir(), "Services path should be a directory"
    
    def test_required_service_files_exist(self):
        """Test that required service files were created."""
        project_root = Path(__file__).parent.parent
        services_dir = project_root / "src" / "claude_tasker" / "services"
        
        required_files = [
            "__init__.py",
            "command_executor.py", 
            "git_service.py",
            "gh_service.py"
        ]
        
        for filename in required_files:
            file_path = services_dir / filename
            assert file_path.exists(), f"Required service file {filename} should exist"
    
    def test_services_have_expected_classes(self):
        """Test that service files contain expected classes."""
        project_root = Path(__file__).parent.parent
        services_dir = project_root / "src" / "claude_tasker" / "services"
        
        expected_classes = {
            "command_executor.py": ["CommandExecutor", "CommandResult", "CommandErrorType"],
            "git_service.py": ["GitService"],
            "gh_service.py": ["GhService", "IssueData", "PRData", "GitHubError"]
        }
        
        for filename, classes in expected_classes.items():
            file_path = services_dir / filename
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content, filename=str(file_path))
                
                # Find class definitions
                class_names = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_names.append(node.name)
                
                for expected_class in classes:
                    assert expected_class in class_names, (
                        f"Expected class {expected_class} not found in {filename}. "
                        f"Found classes: {class_names}"
                    )
                        
            except Exception as e:
                pytest.fail(f"Error analyzing {file_path}: {e}")
    
    def test_no_subprocess_in_main_package_init(self):
        """Test that main package __init__.py doesn't import subprocess."""
        project_root = Path(__file__).parent.parent
        init_file = project_root / "src" / "claude_tasker" / "__init__.py"
        
        if init_file.exists():
            analysis = analyze_file_for_subprocess_calls(init_file)
            
            assert not analysis['subprocess_imports'], (
                f"Main package __init__.py should not import subprocess: "
                f"{analysis['subprocess_imports']}"
            )
            
            assert not analysis['subprocess_calls'], (
                f"Main package __init__.py should not call subprocess: "
                f"{analysis['subprocess_calls']}"
            )


class TestServiceDependencyInjection:
    """Test that modules properly use dependency injection."""
    
    def test_branch_manager_uses_services(self):
        """Test that BranchManager uses injected services."""
        project_root = Path(__file__).parent.parent
        file_path = project_root / "src" / "claude_tasker" / "branch_manager.py"
        
        if not file_path.exists():
            pytest.skip("BranchManager file not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should import services
        assert "from src.claude_tasker.services.git_service import GitService" in content
        assert "from src.claude_tasker.services.gh_service import GhService" in content
        
        # Should accept services in constructor
        assert "git_service: GitService" in content
        assert "gh_service: GhService" in content
    
    def test_pr_body_generator_uses_command_executor(self):
        """Test that PRBodyGenerator uses CommandExecutor."""
        project_root = Path(__file__).parent.parent
        file_path = project_root / "src" / "claude_tasker" / "pr_body_generator.py"
        
        if not file_path.exists():
            pytest.skip("PRBodyGenerator file not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should import CommandExecutor
        assert "from .services.command_executor import CommandExecutor" in content
        
        # Should accept CommandExecutor in constructor
        assert "command_executor: CommandExecutor" in content
    
    def test_environment_validator_uses_services(self):
        """Test that EnvironmentValidator uses services and shutil.which."""
        project_root = Path(__file__).parent.parent
        file_path = project_root / "src" / "claude_tasker" / "environment_validator.py"
        
        if not file_path.exists():
            pytest.skip("EnvironmentValidator file not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Should import shutil instead of subprocess
        assert "import shutil" in content
        assert "import subprocess" not in content
        
        # Should use shutil.which
        assert "shutil.which" in content
        
        # Should import GitService
        assert "from .services.git_service import GitService" in content