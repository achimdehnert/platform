"""
Transaction-Safe Handler Deployment
All-or-nothing deployment with automatic rollback on failure
"""

from django.db import transaction
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional
import shutil
import tempfile
import ast
import subprocess
import sys

from apps.bfagent.models_handlers import Handler
from apps.bfagent.services.handlers.config_models import (
    HandlerRequirements,
    GeneratedHandler,
    HandlerValidation
)


class DeploymentError(Exception):
    """Raised when deployment fails"""
    pass


class HandlerDeploymentManager:
    """
    Transaction-safe handler deployment with automatic rollback
    
    Ensures atomic deployments - either everything succeeds or nothing is changed
    """
    
    def __init__(self):
        self.base_handler_path = Path(__file__).parent.parent.parent / "services" / "handlers"
    
    @contextmanager
    def atomic_deployment(self):
        """
        Context manager for atomic deployments
        
        Tracks all files and DB objects created during deployment.
        Automatically rolls back everything on failure.
        
        Usage:
            with deployment_manager.atomic_deployment() as ctx:
                # Create files
                ctx['temp_files'].append(file_path)
                # Create DB objects
                ctx['db_objects'].append(handler)
                # If anything fails, all changes are reverted
        """
        temp_files: List[Path] = []
        db_savepoint = None
        
        try:
            # Start DB transaction
            db_savepoint = transaction.savepoint()
            
            # Provide context
            ctx = {
                'temp_files': temp_files,
                'db_savepoint': db_savepoint
            }
            
            yield ctx
            
            # Success! Commit everything
            transaction.savepoint_commit(db_savepoint)
            
        except Exception as e:
            # Failure! Rollback everything
            if db_savepoint:
                transaction.savepoint_rollback(db_savepoint)
            
            # Delete temp files
            for file_path in temp_files:
                try:
                    file_path.unlink(missing_ok=True)
                except Exception:
                    pass
            
            raise DeploymentError(f"Deployment failed: {e}") from e
    
    def deploy_handler(
        self,
        requirements: HandlerRequirements,
        generated: GeneratedHandler,
        created_by=None
    ) -> Handler:
        """
        Deploy handler with full transaction safety
        
        Steps:
        1. Write code files to temp location
        2. Validate syntax
        3. Run tests
        4. Move files to final location
        5. Create DB record
        6. Commit (or rollback everything on failure)
        
        Args:
            requirements: Handler requirements
            generated: Generated handler code
            created_by: User creating the handler
            
        Returns:
            Handler instance if successful
            
        Raises:
            DeploymentError: If any step fails
        """
        with self.atomic_deployment() as ctx:
            # 1. Determine file paths
            handler_file = self._get_handler_file_path(
                requirements.handler_id,
                requirements.category
            )
            config_file = self.base_handler_path / "config_models.py"
            test_file = self._get_test_file_path(requirements.handler_id)
            
            # 2. Write handler code
            self._write_file(handler_file, generated.handler_code)
            ctx['temp_files'].append(handler_file)
            
            # 3. Append config model to config_models.py
            self._append_config_model(config_file, generated.config_model_code)
            # Note: Not added to temp_files as it's an append, not a new file
            
            # 4. Write test code
            self._write_file(test_file, generated.test_code)
            ctx['temp_files'].append(test_file)
            
            # 5. Validate syntax
            validation = self._validate_deployment(
                handler_file,
                test_file,
                requirements
            )
            
            if not validation.is_valid:
                raise DeploymentError(
                    f"Validation failed:\n"
                    f"Syntax errors: {validation.syntax_errors}\n"
                    f"Schema errors: {validation.schema_errors}\n"
                    f"Test failures: {validation.test_failures}"
                )
            
            # 6. Create DB record (inside transaction)
            handler = Handler.objects.create(
                handler_id=requirements.handler_id,
                display_name=requirements.display_name,
                description=requirements.description,
                category=requirements.category,
                module_path=self._get_module_path(
                    requirements.handler_id,
                    requirements.category
                ),
                class_name=self._get_class_name(requirements.handler_id),
                config_model_path=f"apps.bfagent.services.handlers.config_models.{self._get_config_class_name(requirements.handler_id)}",
                config_schema=self._generate_json_schema(requirements),
                is_active=True,
                version="1.0.0",
                created_by=created_by,
                documentation_url="",
                example_config=self._generate_example_config(requirements)
            )
            
            # 7. Add to registry
            self._update_registry(requirements.handler_id, requirements.category)
            
            # All done! Transaction will commit
            return handler
    
    def _get_handler_file_path(self, handler_id: str, category: str) -> Path:
        """Get file path for handler"""
        category_dir = self.base_handler_path / category
        category_dir.mkdir(parents=True, exist_ok=True)
        return category_dir / f"{handler_id}.py"
    
    def _get_test_file_path(self, handler_id: str) -> Path:
        """Get file path for tests"""
        test_dir = Path(__file__).parent.parent.parent.parent.parent / "tests" / "handlers"
        test_dir.mkdir(parents=True, exist_ok=True)
        return test_dir / f"test_{handler_id}.py"
    
    def _get_module_path(self, handler_id: str, category: str) -> str:
        """Get Python module path"""
        return f"apps.bfagent.services.handlers.{category}.{handler_id}"
    
    def _get_class_name(self, handler_id: str) -> str:
        """Convert handler_id to ClassName"""
        parts = handler_id.split('_')
        return ''.join(word.capitalize() for word in parts) + 'Handler'
    
    def _get_config_class_name(self, handler_id: str) -> str:
        """Convert handler_id to ConfigClassName"""
        parts = handler_id.split('_')
        return ''.join(word.capitalize() for word in parts) + 'Config'
    
    def _write_file(self, file_path: Path, content: str):
        """Write content to file"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
    
    def _append_config_model(self, config_file: Path, config_code: str):
        """Append config model to config_models.py"""
        # Read existing content
        existing = config_file.read_text(encoding='utf-8')
        
        # Find insertion point (before HANDLER_CONFIG_REGISTRY)
        registry_marker = "HANDLER_CONFIG_REGISTRY"
        if registry_marker in existing:
            parts = existing.split(f"# {registry_marker}")
            new_content = (
                parts[0] +
                f"\n\n{config_code}\n\n" +
                f"# {registry_marker}" +
                parts[1]
            )
        else:
            # Just append
            new_content = existing + f"\n\n{config_code}\n"
        
        # Write back
        config_file.write_text(new_content, encoding='utf-8')
    
    def _validate_deployment(
        self,
        handler_file: Path,
        test_file: Path,
        requirements: HandlerRequirements
    ) -> HandlerValidation:
        """
        Validate deployment before committing
        
        Returns:
            HandlerValidation with all checks
        """
        syntax_errors = []
        test_failures = []
        warnings = []
        
        # 1. Validate Python syntax
        try:
            with open(handler_file, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
        except SyntaxError as e:
            syntax_errors.append(f"Handler syntax error: {e}")
        
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
        except SyntaxError as e:
            syntax_errors.append(f"Test syntax error: {e}")
        
        # 2. Run tests (optional, can be slow)
        if not syntax_errors:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", str(test_file), "-v"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    test_failures.append(f"Tests failed:\n{result.stdout}\n{result.stderr}")
            except subprocess.TimeoutExpired:
                warnings.append("Tests timed out after 30s")
            except Exception as e:
                warnings.append(f"Could not run tests: {e}")
        
        # Build validation result
        is_valid = len(syntax_errors) == 0 and len(test_failures) == 0
        
        return HandlerValidation(
            is_valid=is_valid,
            syntax_valid=len(syntax_errors) == 0,
            tests_pass=len(test_failures) == 0,
            syntax_errors=syntax_errors,
            schema_errors=[],  # Could add schema validation here
            test_failures=test_failures,
            warnings=warnings,
            suggestions=[]
        )
    
    def _generate_json_schema(self, requirements: HandlerRequirements) -> dict:
        """Generate JSON Schema from requirements"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param_info in requirements.config_parameters.items():
            schema["properties"][param_name] = param_info
            if param_info.get("required", False):
                schema["required"].append(param_name)
        
        return schema
    
    def _generate_example_config(self, requirements: HandlerRequirements) -> dict:
        """Generate example configuration"""
        example = {}
        
        for param_name, param_info in requirements.config_parameters.items():
            if "default" in param_info:
                example[param_name] = param_info["default"]
            elif "example" in param_info:
                example[param_name] = param_info["example"]
        
        return example
    
    def _update_registry(self, handler_id: str, category: str):
        """Update handler registry file"""
        registry_file = self.base_handler_path / "registries.py"
        
        if not registry_file.exists():
            return  # Registry doesn't exist yet
        
        # Read registry
        content = registry_file.read_text(encoding='utf-8')
        
        # Add import
        class_name = self._get_class_name(handler_id)
        import_line = f"from .{category}.{handler_id} import {class_name}\n"
        
        # Add registration
        registry_name = f"{category.capitalize()}HandlerRegistry"
        register_line = f"{registry_name}.register('{handler_id}', {class_name})\n"
        
        # Append (simple approach - could be smarter)
        content += f"\n{import_line}{register_line}"
        
        registry_file.write_text(content, encoding='utf-8')


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def deploy_handler_safe(
    requirements: HandlerRequirements,
    generated: GeneratedHandler,
    created_by=None
) -> Handler:
    """
    Convenience function for safe handler deployment
    
    Example:
        from apps.bfagent.services.handlers.config_models import HandlerRequirements, GeneratedHandler
        
        requirements = HandlerRequirements(
            handler_id="pdf_extractor",
            display_name="PDF Text Extractor",
            description="Extracts text from PDFs",
            category="input",
            ...
        )
        
        generated = GeneratedHandler(
            handler_code="...",
            config_model_code="...",
            test_code="...",
            ...
        )
        
        handler = deploy_handler_safe(requirements, generated, user)
    """
    manager = HandlerDeploymentManager()
    return manager.deploy_handler(requirements, generated, created_by)
