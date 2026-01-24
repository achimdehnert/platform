"""
Pipeline Orchestrator

Orchestrates the complete INPUT → PROCESSING → OUTPUT pipeline
by coordinating handlers from all three stages.
"""

from typing import Any, Dict, List
from .handlers.registries import (
    InputHandlerRegistry,
    ProcessingHandlerRegistry,
    OutputHandlerRegistry,
)


class PipelineOrchestrator:
    """
    Orchestrates the complete handler pipeline.
    
    Executes a configured pipeline:
    1. INPUT Stage: Collect data from multiple sources
    2. PROCESSING Stage: Transform data through processing chain
    3. OUTPUT Stage: Store/export results
    
    Example:
        >>> orchestrator = PipelineOrchestrator(action_template)
        >>> context = {"project": project, "agent": agent}
        >>> results = orchestrator.execute(context)
    """
    
    def __init__(self, pipeline_config: Dict[str, Any]):
        """
        Initialize orchestrator with pipeline configuration.
        
        Args:
            pipeline_config: Pipeline configuration dict with:
                - input: List of input handler configs
                - processing: List of processing handler configs
                - output: Output handler config
        """
        self.pipeline_config = pipeline_config
        self.validate_config()
    
    def validate_config(self) -> None:
        """Validate pipeline configuration."""
        required_keys = ["input", "processing", "output"]
        for key in required_keys:
            if key not in self.pipeline_config:
                raise ValueError(f"Missing required pipeline stage: '{key}'")
        
        if not isinstance(self.pipeline_config["input"], list):
            raise ValueError("'input' must be a list of handler configs")
        
        if not isinstance(self.pipeline_config["processing"], list):
            raise ValueError("'processing' must be a list of handler configs")
        
        if not isinstance(self.pipeline_config["output"], dict):
            raise ValueError("'output' must be a dict with handler config")
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete pipeline.
        
        Args:
            context: Runtime context containing:
                - project: BookProjects instance
                - agent: Agents instance
                - user_context: Optional user input
                - user_requirements: Optional requirements
                
        Returns:
            Dictionary with results from all stages:
            {
                "input": {...collected data...},
                "processed": {...transformed data...},
                "output": {...output results...},
                "metadata": {...execution info...}
            }
        """
        results = {
            "input": None,
            "processed": None,
            "output": None,
            "metadata": {
                "stages_completed": [],
                "handlers_executed": [],
                "errors": []
            }
        }
        
        try:
            # STAGE 1: INPUT
            input_data = self._execute_input_stage(context)
            results["input"] = input_data
            results["metadata"]["stages_completed"].append("input")
            
            # STAGE 2: PROCESSING
            processed_data = self._execute_processing_stage(input_data, context)
            results["processed"] = processed_data
            results["metadata"]["stages_completed"].append("processing")
            
            # STAGE 3: OUTPUT
            output_result = self._execute_output_stage(processed_data, context)
            results["output"] = output_result
            results["metadata"]["stages_completed"].append("output")
            
        except Exception as e:
            results["metadata"]["errors"].append({
                "stage": results["metadata"]["stages_completed"][-1] if results["metadata"]["stages_completed"] else "unknown",
                "error": str(e),
                "type": type(e).__name__
            })
            raise
        
        return results
    
    def _execute_input_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute input stage - collect data from all input handlers.
        
        Args:
            context: Runtime context
            
        Returns:
            Merged dictionary with all collected data
        """
        input_configs = self.pipeline_config["input"]
        collected_data = {}
        
        for handler_config in input_configs:
            handler_name = handler_config.get("handler")
            handler_params = handler_config.get("config", {})
            
            if not handler_name:
                raise ValueError("Input handler config missing 'handler' key")
            
            # Get handler class from registry
            try:
                HandlerClass = InputHandlerRegistry.get(handler_name)
            except ValueError as e:
                raise ValueError(f"Input handler '{handler_name}' not found: {e}")
            
            # Initialize handler
            handler = HandlerClass(handler_params)
            
            # Collect data
            data = handler.collect(context)
            
            # Merge into collected_data
            collected_data.update(data)
            
            # Track execution
            self.pipeline_config.setdefault("_metadata", {}).setdefault("handlers_executed", []).append({
                "stage": "input",
                "handler": handler_name,
                "data_keys": list(data.keys())
            })
        
        return collected_data
    
    def _execute_processing_stage(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """
        Execute processing stage - transform data through processing chain.
        
        Args:
            input_data: Data from input stage
            context: Runtime context
            
        Returns:
            Processed data (type depends on handlers)
        """
        processing_configs = self.pipeline_config["processing"]
        current_data = input_data
        
        for handler_config in processing_configs:
            handler_name = handler_config.get("handler")
            handler_params = handler_config.get("config", {})
            
            if not handler_name:
                raise ValueError("Processing handler config missing 'handler' key")
            
            # Get handler class from registry
            try:
                HandlerClass = ProcessingHandlerRegistry.get(handler_name)
            except ValueError as e:
                raise ValueError(f"Processing handler '{handler_name}' not found: {e}")
            
            # Initialize handler
            handler = HandlerClass(handler_params)
            
            # Process data
            current_data = handler.process(current_data, context)
            
            # Track execution
            self.pipeline_config.setdefault("_metadata", {}).setdefault("handlers_executed", []).append({
                "stage": "processing",
                "handler": handler_name,
                "output_type": type(current_data).__name__
            })
        
        return current_data
    
    def _execute_output_stage(
        self,
        processed_data: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute output stage - store/export results.
        
        Args:
            processed_data: Data from processing stage
            context: Runtime context
            
        Returns:
            Dictionary with output results:
            {
                "handler": handler_name,
                "responses": [EnrichmentResponse, ...],
                "validation": {...}
            }
        """
        output_config = self.pipeline_config["output"]
        
        handler_name = output_config.get("handler")
        handler_params = output_config.get("config", {})
        
        if not handler_name:
            raise ValueError("Output handler config missing 'handler' key")
        
        # Get handler class from registry
        try:
            HandlerClass = OutputHandlerRegistry.get(handler_name)
        except ValueError as e:
            raise ValueError(f"Output handler '{handler_name}' not found: {e}")
        
        # Initialize handler
        handler = HandlerClass(handler_params)
        
        # Parse processed data
        parsed_data = handler.parse(processed_data)
        
        # Validate
        validation = handler.validate(parsed_data)
        
        if not validation["valid"]:
            raise ValueError(f"Output validation failed: {validation['errors']}")
        
        # Create enrichment responses for approval
        project = context.get("project")
        agent = context.get("agent")
        
        if not project or not agent:
            raise ValueError("Context missing 'project' or 'agent'")
        
        responses = handler.create_enrichment_responses(
            parsed_data,
            project,
            agent
        )
        
        # Track execution
        self.pipeline_config.setdefault("_metadata", {}).setdefault("handlers_executed", []).append({
            "stage": "output",
            "handler": handler_name,
            "responses_created": len(responses)
        })
        
        return {
            "handler": handler_name,
            "responses": responses,
            "validation": validation,
            "parsed_data": parsed_data
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary of last execution.
        
        Returns:
            Dictionary with execution statistics
        """
        metadata = self.pipeline_config.get("_metadata", {})
        handlers_executed = metadata.get("handlers_executed", [])
        
        return {
            "total_handlers": len(handlers_executed),
            "input_handlers": len([h for h in handlers_executed if h["stage"] == "input"]),
            "processing_handlers": len([h for h in handlers_executed if h["stage"] == "processing"]),
            "output_handlers": len([h for h in handlers_executed if h["stage"] == "output"]),
            "handlers": handlers_executed
        }
