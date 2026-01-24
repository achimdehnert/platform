"""
Handler Generator Agent - AI-Powered Handler Creation
Complete orchestration of handler generation from description to deployment
"""

from typing import Dict, Any, Optional
import logging

from apps.bfagent.services.handlers.config_models import (
    HandlerRequirements,
    GeneratedHandler,
    HandlerValidation
)
from apps.bfagent.models_handlers import Handler

from .llm_client import StructuredLLMClient
from .deployment import HandlerDeploymentManager
from .prompts import PromptBuilder


logger = logging.getLogger(__name__)


class HandlerGeneratorAgent:
    """
    AI Agent that generates complete handlers from natural language descriptions
    
    Workflow:
    1. Analyze user requirements → HandlerRequirements
    2. Generate handler code → GeneratedHandler
    3. Validate generated code → HandlerValidation
    4. Deploy with transaction safety → Handler (DB)
    
    Features:
    - Type-safe with Pydantic
    - Structured LLM outputs (no parsing errors)
    - Transaction-safe deployment
    - Automatic validation and testing
    - Rollback on failure
    """
    
    def __init__(self, llm_provider: str = "anthropic"):
        """
        Initialize Handler Generator Agent
        
        Args:
            llm_provider: 'anthropic' or 'openai'
        """
        self.llm = StructuredLLMClient(provider=llm_provider)
        self.deployment_manager = HandlerDeploymentManager()
        self.prompt_builder = PromptBuilder()
    
    def generate_handler(
        self,
        description: str,
        user=None,
        auto_deploy: bool = False
    ) -> Dict[str, Any]:
        """
        Generate handler from natural language description
        
        Args:
            description: Natural language description of handler
            user: User creating the handler
            auto_deploy: If True, automatically deploy after validation
            
        Returns:
            Dictionary with:
            - requirements: HandlerRequirements
            - generated: GeneratedHandler
            - validation: HandlerValidation
            - handler: Handler (if deployed)
            - deployed: bool
            
        Example:
            agent = HandlerGeneratorAgent()
            
            result = agent.generate_handler(
                description="I need a handler that extracts text from PDF files",
                user=request.user,
                auto_deploy=True
            )
            
            if result['deployed']:
                print(f"Handler deployed: {result['handler'].handler_id}")
        """
        logger.info(f"Starting handler generation for: {description[:100]}...")
        
        # Step 1: Analyze requirements
        logger.info("Step 1: Analyzing requirements...")
        requirements = self._analyze_requirements(description)
        logger.info(f"Requirements analyzed: {requirements.handler_id}")
        
        # Step 2: Generate code
        logger.info("Step 2: Generating handler code...")
        generated = self._generate_code(requirements)
        logger.info("Code generation complete")
        
        # Step 3: Validate (pre-deployment check)
        logger.info("Step 3: Validating generated code...")
        validation = self._quick_validate(generated)
        logger.info(f"Validation result: {validation.is_valid}")
        
        result = {
            'requirements': requirements,
            'generated': generated,
            'validation': validation,
            'handler': None,
            'deployed': False
        }
        
        # Step 4: Deploy if requested and valid
        if auto_deploy and validation.is_valid:
            logger.info("Step 4: Deploying handler...")
            try:
                handler = self.deployment_manager.deploy_handler(
                    requirements=requirements,
                    generated=generated,
                    created_by=user
                )
                result['handler'] = handler
                result['deployed'] = True
                logger.info(f"Handler deployed successfully: {handler.handler_id}")
            except Exception as e:
                logger.error(f"Deployment failed: {e}")
                result['deployment_error'] = str(e)
        
        return result
    
    def _analyze_requirements(self, description: str) -> HandlerRequirements:
        """
        Analyze user description and extract structured requirements
        
        Args:
            description: Natural language description
            
        Returns:
            Structured HandlerRequirements
        """
        prompt = self.prompt_builder.build_requirements_prompt(description)
        
        # Use structured LLM to guarantee valid output
        requirements = self.llm.generate_with_fallback(
            prompt=prompt,
            response_model=HandlerRequirements,
            system_prompt=self.prompt_builder.REQUIREMENTS_SYSTEM_PROMPT,
            max_retries=3
        )
        
        return requirements
    
    def _generate_code(self, requirements: HandlerRequirements) -> GeneratedHandler:
        """
        Generate complete handler code from requirements
        
        Args:
            requirements: Structured requirements
            
        Returns:
            Generated handler code, tests, docs
        """
        prompt = self.prompt_builder.build_generation_prompt(requirements)
        
        # Use structured LLM to guarantee valid output
        generated = self.llm.generate_with_fallback(
            prompt=prompt,
            response_model=GeneratedHandler,
            system_prompt=self.prompt_builder.CODE_GENERATION_SYSTEM_PROMPT,
            max_retries=3
        )
        
        return generated
    
    def _quick_validate(self, generated: GeneratedHandler) -> HandlerValidation:
        """
        Quick validation before deployment
        
        Args:
            generated: Generated handler code
            
        Returns:
            Validation results
        """
        import ast
        
        syntax_errors = []
        
        # Validate handler code syntax
        try:
            ast.parse(generated.handler_code)
        except SyntaxError as e:
            syntax_errors.append(f"Handler code syntax error: {e}")
        
        # Validate config model syntax
        try:
            ast.parse(generated.config_model_code)
        except SyntaxError as e:
            syntax_errors.append(f"Config model syntax error: {e}")
        
        # Validate test code syntax
        try:
            ast.parse(generated.test_code)
        except SyntaxError as e:
            syntax_errors.append(f"Test code syntax error: {e}")
        
        is_valid = len(syntax_errors) == 0
        
        return HandlerValidation(
            is_valid=is_valid,
            syntax_valid=is_valid,
            tests_pass=False,  # Not run yet
            syntax_errors=syntax_errors,
            schema_errors=[],
            test_failures=[],
            warnings=[],
            suggestions=[]
        )
    
    def deploy_handler(
        self,
        requirements: HandlerRequirements,
        generated: GeneratedHandler,
        user=None
    ) -> Handler:
        """
        Deploy a generated handler
        
        Args:
            requirements: Handler requirements
            generated: Generated code
            user: User deploying
            
        Returns:
            Deployed Handler instance
        """
        return self.deployment_manager.deploy_handler(
            requirements=requirements,
            generated=generated,
            created_by=user
        )
    
    def regenerate_handler(
        self,
        requirements: HandlerRequirements,
        feedback: str
    ) -> GeneratedHandler:
        """
        Regenerate handler with user feedback
        
        Args:
            requirements: Original requirements
            feedback: User feedback on what to improve
            
        Returns:
            Regenerated handler code
        """
        prompt = self.prompt_builder.build_regeneration_prompt(
            requirements, feedback
        )
        
        generated = self.llm.generate_with_fallback(
            prompt=prompt,
            response_model=GeneratedHandler,
            system_prompt=self.prompt_builder.CODE_GENERATION_SYSTEM_PROMPT,
            max_retries=3
        )
        
        return generated


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def generate_handler_from_description(
    description: str,
    user=None,
    auto_deploy: bool = False,
    llm_provider: str = "anthropic"
) -> Dict[str, Any]:
    """
    Convenience function for quick handler generation
    
    Example:
        result = generate_handler_from_description(
            description="Extract text from PDF files",
            user=request.user,
            auto_deploy=True
        )
        
        if result['deployed']:
            handler = result['handler']
            print(f"Ready to use: {handler.handler_id}")
    """
    agent = HandlerGeneratorAgent(llm_provider=llm_provider)
    return agent.generate_handler(
        description=description,
        user=user,
        auto_deploy=auto_deploy
    )
