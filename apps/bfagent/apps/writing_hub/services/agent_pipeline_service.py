"""
Agent Pipeline Service
======================
Orchestrates the execution of agent pipelines for content generation.
Handles LLM selection, prompt building, and execution tracking.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from django.utils import timezone
from django.db import transaction

from apps.writing_hub.models import (
    AgentRole,
    LlmTier,
    AgentPipelineTemplate,
    AgentPipelineExecution,
    AgentPipelineStep,
    ProjectAgentConfig,
)
from apps.bfagent.models import Llms, BookProjects

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result of a single pipeline step"""
    success: bool
    output: str
    tokens_used: int = 0
    cost: float = 0.0
    duration_seconds: float = 0.0
    error_message: str = ""


@dataclass
class PipelineResult:
    """Result of a complete pipeline execution"""
    success: bool
    final_output: str
    steps: List[Dict[str, Any]]
    total_tokens: int = 0
    total_cost: float = 0.0
    total_duration: float = 0.0
    error_message: str = ""


class AgentPipelineService:
    """
    Service for executing agent pipelines.
    
    Usage:
        service = AgentPipelineService(project_id=1)
        result = service.execute_pipeline(
            template_code="write_chapter",
            context={"chapter_title": "Chapter 1", "outline": "..."}
        )
    """
    
    def __init__(self, project_id: int):
        self.project = BookProjects.objects.get(id=project_id)
        self.project_configs = {
            cfg.agent_role.code: cfg 
            for cfg in ProjectAgentConfig.objects.filter(project=self.project).select_related('agent_role', 'llm_override', 'tier_override')
        }
        self._llm_cache = {}
        self._tier_cache = {}
    
    def execute_pipeline(
        self,
        template_code: str,
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> PipelineResult:
        """
        Execute a pipeline template.
        
        Args:
            template_code: Code of the pipeline template
            context: Context data for the pipeline (outline, previous content, etc.)
            dry_run: If True, don't actually call LLMs
            
        Returns:
            PipelineResult with final output and execution details
        """
        try:
            template = AgentPipelineTemplate.objects.get(code=template_code, is_active=True)
        except AgentPipelineTemplate.DoesNotExist:
            return PipelineResult(
                success=False,
                final_output="",
                steps=[],
                error_message=f"Pipeline template '{template_code}' not found"
            )
        
        # Create execution record
        execution = AgentPipelineExecution.objects.create(
            project=self.project,
            pipeline_template=template,
            trigger_type="manual",
            trigger_context=context,
            status="running",
            total_steps=len(template.pipeline_config),
            started_at=timezone.now()
        )
        
        try:
            result = self._run_pipeline(execution, template.pipeline_config, context, dry_run)
            
            # Update execution record
            execution.status = "completed" if result.success else "failed"
            execution.output = {"final_output": result.final_output, "steps": result.steps}
            execution.total_tokens_used = result.total_tokens
            execution.total_cost = result.total_cost
            execution.duration_seconds = result.total_duration
            execution.completed_at = timezone.now()
            execution.save()
            
            return result
            
        except Exception as e:
            logger.exception(f"Pipeline execution failed: {e}")
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            
            return PipelineResult(
                success=False,
                final_output="",
                steps=[],
                error_message=str(e)
            )
    
    def _run_pipeline(
        self,
        execution: AgentPipelineExecution,
        pipeline_config: List[Dict],
        context: Dict[str, Any],
        dry_run: bool
    ) -> PipelineResult:
        """Run all steps in the pipeline"""
        
        steps_results = []
        accumulated_context = dict(context)
        total_tokens = 0
        total_cost = 0.0
        start_time = time.time()
        
        for idx, step_config in enumerate(pipeline_config):
            execution.current_step = idx + 1
            execution.save(update_fields=['current_step'])
            
            # Get agent role
            role_code = step_config.get("agent_role")
            try:
                agent_role = AgentRole.objects.get(code=role_code, is_active=True)
            except AgentRole.DoesNotExist:
                logger.error(f"Agent role '{role_code}' not found")
                continue
            
            # Get tier and LLM
            tier = self._get_tier_for_step(step_config, agent_role)
            llm = self._get_llm_for_step(agent_role, tier)
            
            # Create step record
            step_record = AgentPipelineStep.objects.create(
                execution=execution,
                agent_role=agent_role,
                llm_used=llm,
                tier_used=tier,
                step_order=idx + 1,
                status="running",
                input_data=accumulated_context,
                started_at=timezone.now()
            )
            
            # Build prompts
            system_prompt = self._build_system_prompt(agent_role, accumulated_context)
            user_prompt = self._build_user_prompt(agent_role, step_config, accumulated_context)
            
            step_record.system_prompt_used = system_prompt
            step_record.user_prompt_used = user_prompt
            step_record.save()
            
            # Execute step
            if dry_run:
                step_result = StepResult(
                    success=True,
                    output=f"[DRY RUN] {agent_role.name} would process here",
                    tokens_used=0,
                    cost=0.0,
                    duration_seconds=0.1
                )
            else:
                step_result = self._execute_step(llm, system_prompt, user_prompt, tier)
            
            # Update step record
            step_record.status = "completed" if step_result.success else "failed"
            step_record.output_data = {"output": step_result.output}
            step_record.tokens_used = step_result.tokens_used
            step_record.cost = step_result.cost
            step_record.duration_seconds = step_result.duration_seconds
            step_record.error_message = step_result.error_message
            step_record.completed_at = timezone.now()
            step_record.save()
            
            # Track totals
            total_tokens += step_result.tokens_used
            total_cost += step_result.cost
            
            # Add to accumulated context
            step_label = step_config.get("label", agent_role.code)
            accumulated_context[f"{step_label}_output"] = step_result.output
            accumulated_context["last_output"] = step_result.output
            
            steps_results.append({
                "step": idx + 1,
                "agent": agent_role.name,
                "tier": tier.code if tier else "default",
                "success": step_result.success,
                "tokens": step_result.tokens_used,
                "cost": step_result.cost,
                "duration": step_result.duration_seconds,
            })
            
            # Stop on failure (unless configured to continue)
            if not step_result.success and not step_config.get("continue_on_error"):
                return PipelineResult(
                    success=False,
                    final_output="",
                    steps=steps_results,
                    total_tokens=total_tokens,
                    total_cost=total_cost,
                    total_duration=time.time() - start_time,
                    error_message=f"Step {idx + 1} ({agent_role.name}) failed: {step_result.error_message}"
                )
        
        return PipelineResult(
            success=True,
            final_output=accumulated_context.get("last_output", ""),
            steps=steps_results,
            total_tokens=total_tokens,
            total_cost=total_cost,
            total_duration=time.time() - start_time
        )
    
    def _get_tier_for_step(self, step_config: Dict, agent_role: AgentRole) -> Optional[LlmTier]:
        """Get the LLM tier for a step"""
        tier_code = step_config.get("tier", "standard")
        
        # Check project override
        if agent_role.code in self.project_configs:
            project_cfg = self.project_configs[agent_role.code]
            if project_cfg.tier_override:
                return project_cfg.tier_override
        
        # Get from cache or DB
        if tier_code not in self._tier_cache:
            self._tier_cache[tier_code] = LlmTier.objects.filter(code=tier_code, is_active=True).first()
        
        return self._tier_cache[tier_code]
    
    def _get_llm_for_step(self, agent_role: AgentRole, tier: Optional[LlmTier]) -> Optional[Llms]:
        """Get the LLM to use for a step"""
        # Check project override
        if agent_role.code in self.project_configs:
            project_cfg = self.project_configs[agent_role.code]
            if project_cfg.llm_override:
                return project_cfg.llm_override
        
        # Use tier's default LLM
        if tier and tier.default_llm:
            return tier.default_llm
        
        # Fallback to any active LLM
        cache_key = f"default_{tier.code if tier else 'none'}"
        if cache_key not in self._llm_cache:
            self._llm_cache[cache_key] = Llms.objects.filter(is_active=True).first()
        
        return self._llm_cache[cache_key]
    
    def _build_system_prompt(self, agent_role: AgentRole, context: Dict[str, Any]) -> str:
        """Build the system prompt for an agent"""
        base_prompt = agent_role.base_system_prompt
        
        # Add project-specific instructions
        if agent_role.code in self.project_configs:
            project_cfg = self.project_configs[agent_role.code]
            if project_cfg.custom_instructions:
                base_prompt += f"\n\nPROJEKT-SPEZIFISCHE ANWEISUNGEN:\n{project_cfg.custom_instructions}"
        
        # Add context-specific information
        if context.get("content_type") == "scientific":
            base_prompt += "\n\nKONTEXT: Dies ist eine wissenschaftliche Arbeit. Achte auf formalen Stil und korrekte Zitationen."
        
        return base_prompt
    
    def _build_user_prompt(self, agent_role: AgentRole, step_config: Dict, context: Dict[str, Any]) -> str:
        """Build the user prompt for a step"""
        role_code = agent_role.code
        
        # Base prompt by role
        if role_code == "researcher":
            return self._build_researcher_prompt(context)
        elif role_code.startswith("writer"):
            return self._build_writer_prompt(agent_role, context)
        elif role_code == "reviewer":
            return self._build_reviewer_prompt(context)
        elif role_code == "critic":
            return self._build_critic_prompt(context)
        elif role_code == "quality_manager":
            return self._build_qm_prompt(context)
        else:
            return f"Bearbeite folgende Aufgabe:\n\n{context.get('task', 'Keine Aufgabe definiert')}"
    
    def _build_researcher_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for Researcher agent"""
        return f"""Recherchiere und sammle Kontext für folgende Aufgabe:

PROJEKT: {context.get('project_title', 'Unbekannt')}
KAPITEL/ABSCHNITT: {context.get('chapter_title', context.get('section_title', 'Unbekannt'))}

OUTLINE/GLIEDERUNG:
{context.get('outline', 'Keine Gliederung vorhanden')}

VORHERIGER CONTENT:
{context.get('previous_content', 'Kein vorheriger Content')[:2000]}

CHARAKTERE/ELEMENTE:
{context.get('characters', 'Keine Charaktere definiert')}

Erstelle eine strukturierte Zusammenfassung der relevanten Informationen für den Writer."""
    
    def _build_writer_prompt(self, agent_role: AgentRole, context: Dict[str, Any]) -> str:
        """Build prompt for Writer agents"""
        researcher_output = context.get('researcher_output', context.get('last_output', ''))
        
        prompt = f"""Schreibe folgenden Abschnitt:

TITEL: {context.get('chapter_title', context.get('section_title', 'Unbekannt'))}

OUTLINE:
{context.get('outline', 'Keine Gliederung')}

RECHERCHE-ERGEBNISSE:
{researcher_output[:3000] if researcher_output else 'Keine Recherche'}

VORHERIGER TEXT:
{context.get('previous_content', '')[:2000]}

ZIEL-WORTANZAHL: {context.get('target_words', 1500)}
"""
        
        # Add reviewer/critic feedback if available
        if context.get('reviewer_output'):
            prompt += f"\n\nREVIEWER-FEEDBACK:\n{context['reviewer_output'][:1500]}"
        if context.get('critic_output'):
            prompt += f"\n\nKRITIK:\n{context['critic_output'][:1500]}"
        if context.get('Revision_output'):
            prompt += f"\n\nBASIS FÜR ÜBERARBEITUNG:\n{context.get('writer_output', '')[:2000]}"
        
        return prompt
    
    def _build_reviewer_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for Reviewer agent"""
        writer_output = context.get('writer_output', context.get('last_output', ''))
        
        return f"""Reviewe folgenden Text und gib konstruktives Feedback:

KAPITEL/ABSCHNITT: {context.get('chapter_title', context.get('section_title', 'Unbekannt'))}

TEXT ZUM REVIEW:
{writer_output}

OUTLINE (falls vorhanden):
{context.get('outline', 'Keine Gliederung')}

Gib detailliertes, umsetzbares Feedback zu:
1. Struktur und Aufbau
2. Stil und Ton
3. Inhaltliche Vollständigkeit
4. Konkrete Verbesserungsvorschläge"""
    
    def _build_critic_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for Critic agent"""
        writer_output = context.get('writer_output', context.get('last_output', ''))
        
        return f"""Analysiere kritisch folgenden Text und identifiziere Schwachstellen:

TEXT:
{writer_output}

KONTEXT:
- Projekt: {context.get('project_title', 'Unbekannt')}
- Abschnitt: {context.get('chapter_title', context.get('section_title', 'Unbekannt'))}

Prüfe auf:
1. Logische Fehler und Inkonsistenzen
2. Schwache Argumentation
3. Fehlende Informationen
4. Stilistische Probleme
5. Faktische Unstimmigkeiten

Sei direkt und benenne konkrete Probleme mit Lösungsvorschlägen."""
    
    def _build_qm_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for Quality Manager agent"""
        final_text = context.get('Revision_output', context.get('writer_output', context.get('last_output', '')))
        
        return f"""Führe eine finale Qualitätsprüfung durch:

FINALER TEXT:
{final_text}

PRÜFE:
1. Konsistenz (Namen, Daten, Fakten)
2. Vollständigkeit gemäß Outline
3. Formatierung und Struktur
4. Zitationen (falls wissenschaftlich)
5. Sprachliche Qualität

Erstelle einen kurzen QA-Report mit:
- ✅ Bestanden
- ⚠️ Warnung (nicht kritisch)
- ❌ Problem (muss behoben werden)"""
    
    def _execute_step(
        self,
        llm: Optional[Llms],
        system_prompt: str,
        user_prompt: str,
        tier: Optional[LlmTier]
    ) -> StepResult:
        """Execute a single step by calling the LLM"""
        
        if not llm:
            return StepResult(
                success=False,
                output="",
                error_message="No LLM configured"
            )
        
        start_time = time.time()
        
        try:
            # Get temperature from tier or default
            temperature = tier.default_temperature if tier else 0.7
            max_tokens = tier.default_max_tokens if tier else 2000
            
            # Call LLM service
            from apps.bfagent.domains.book_writing.services.llm_service import LLMService
            
            llm_service = LLMService()
            response = llm_service.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                llm_config={
                    "provider": llm.provider,
                    "model": llm.llm_name,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "api_key": llm.api_key,
                    "api_endpoint": llm.api_endpoint,
                }
            )
            
            duration = time.time() - start_time
            tokens_used = response.get("tokens_used", 0)
            cost = (tokens_used / 1000) * llm.cost_per_1k_tokens
            
            return StepResult(
                success=True,
                output=response.get("content", ""),
                tokens_used=tokens_used,
                cost=cost,
                duration_seconds=duration
            )
            
        except Exception as e:
            logger.exception(f"LLM call failed: {e}")
            return StepResult(
                success=False,
                output="",
                duration_seconds=time.time() - start_time,
                error_message=str(e)
            )


class AgentPipelineManager:
    """
    High-level manager for agent pipelines.
    Provides convenience methods for common operations.
    """
    
    @staticmethod
    def write_chapter(project_id: int, chapter_data: Dict[str, Any], pipeline: str = "write_chapter") -> PipelineResult:
        """
        Write a chapter using the specified pipeline.
        
        Args:
            project_id: Project ID
            chapter_data: Dict with chapter_title, outline, previous_content, etc.
            pipeline: Pipeline template code (default: "write_chapter")
        """
        service = AgentPipelineService(project_id)
        return service.execute_pipeline(pipeline, chapter_data)
    
    @staticmethod
    def review_content(project_id: int, content: str, context: Dict[str, Any] = None) -> PipelineResult:
        """Review and improve existing content"""
        service = AgentPipelineService(project_id)
        ctx = context or {}
        ctx["writer_output"] = content
        return service.execute_pipeline("review_only", ctx)
    
    @staticmethod
    def quality_check(project_id: int, content: str, context: Dict[str, Any] = None) -> PipelineResult:
        """Run quality check on content"""
        service = AgentPipelineService(project_id)
        ctx = context or {}
        ctx["last_output"] = content
        return service.execute_pipeline("quality_check", ctx)
    
    @staticmethod
    def get_available_pipelines(content_type: str = None) -> List[Dict[str, Any]]:
        """Get list of available pipeline templates"""
        queryset = AgentPipelineTemplate.objects.filter(is_active=True)
        
        # Filter by content type if specified
        if content_type:
            queryset = queryset.filter(content_types__code=content_type)
        
        return [
            {
                "code": p.code,
                "name": p.name,
                "name_de": p.name_de,
                "description": p.description,
                "estimated_duration": p.estimated_duration_seconds,
                "estimated_cost": p.estimated_cost_factor,
                "steps": len(p.pipeline_config),
            }
            for p in queryset.order_by('sort_order')
        ]
    
    @staticmethod
    def get_project_agent_config(project_id: int) -> Dict[str, Any]:
        """Get agent configuration for a project"""
        configs = ProjectAgentConfig.objects.filter(
            project_id=project_id
        ).select_related('agent_role', 'llm_override', 'tier_override')
        
        return {
            cfg.agent_role.code: {
                "role": cfg.agent_role.name,
                "enabled": cfg.is_enabled,
                "llm_override": cfg.llm_override.name if cfg.llm_override else None,
                "tier_override": cfg.tier_override.code if cfg.tier_override else None,
                "custom_instructions": cfg.custom_instructions,
                "stats": {
                    "total_calls": cfg.total_calls,
                    "total_tokens": cfg.total_tokens,
                    "total_cost": cfg.total_cost,
                }
            }
            for cfg in configs
        }
