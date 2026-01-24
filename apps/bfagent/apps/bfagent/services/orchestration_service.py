# -*- coding: utf-8 -*-
"""
Orchestration Service für Cascade Router Architecture.

Handhabt:
- Parallele Reasoning-Pfade (Cascade vs Thinking Model)
- Code-Delegation an Worker-LLMs
- Tracking aller Operationen
"""
import os
import json
import time
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Singleton
_orchestration_service = None


def get_orchestration_service() -> 'OrchestrationService':
    """Gibt Singleton-Instanz zurück."""
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = OrchestrationService()
    return _orchestration_service


class WorkerLLMClient:
    """Client für Worker-LLM APIs (Grok, Codestral, DeepSeek)."""
    
    # Provider mapping for logging
    PROVIDER_MAP = {
        'groq-llama': 'groq', 'groq-mixtral': 'groq',
        'grok': 'xai', 'codestral': 'mistral',
        'deepseek-coder': 'deepseek', 'deepseek-v3': 'deepseek',
        'gpt4o-mini': 'openai', 'gemini-flash': 'google',
        'openrouter-deepseek-v3': 'openrouter', 'openrouter-codestral': 'openrouter',
        'openrouter-llama-70b': 'openrouter',
    }
    
    DEFAULT_CONFIGS = {
        # GROQ = Groq Inc. (schnelle Inference für Llama/Mixtral)
        'groq-llama': {
            'api_url': 'https://api.groq.com/openai/v1/chat/completions',
            'model': 'llama-3.3-70b-versatile',
            'api_key_env': 'GROQ_API_KEY',
            'cost_per_1k_input': Decimal('0.00059'),
            'cost_per_1k_output': Decimal('0.00079'),
        },
        'groq-mixtral': {
            'api_url': 'https://api.groq.com/openai/v1/chat/completions',
            'model': 'mixtral-8x7b-32768',
            'api_key_env': 'GROQ_API_KEY',
            'cost_per_1k_input': Decimal('0.00024'),
            'cost_per_1k_output': Decimal('0.00024'),
        },
        # GROK = X.AI (Elon Musk) - separater Key!
        'grok': {
            'api_url': 'https://api.x.ai/v1/chat/completions',
            'model': 'grok-beta',
            'api_key_env': 'GROK_API_KEY',
            'cost_per_1k_input': Decimal('0.005'),
            'cost_per_1k_output': Decimal('0.015'),
        },
        'codestral': {
            'api_url': 'https://api.mistral.ai/v1/chat/completions',
            'model': 'codestral-latest',
            'api_key_env': 'MISTRAL_API_KEY',
            'cost_per_1k_input': Decimal('0.001'),
            'cost_per_1k_output': Decimal('0.003'),
        },
        'deepseek-coder': {
            'api_url': 'https://api.deepseek.com/v1/chat/completions',
            'model': 'deepseek-coder',
            'api_key_env': 'DEEPSEEK_API_KEY',
            'cost_per_1k_input': Decimal('0.00014'),
            'cost_per_1k_output': Decimal('0.00028'),
        },
        # DeepSeek V3 - Bestes Preis-Leistungs-Verhältnis für Coding (Jan 2025)
        # OpenAI-kompatible API: https://api.deepseek.com
        'deepseek-v3': {
            'api_url': 'https://api.deepseek.com/v1/chat/completions',
            'model': 'deepseek-chat',  # = DeepSeek V3
            'api_key_env': 'DEEPSEEK_API_KEY',
            'cost_per_1k_input': Decimal('0.00028'),   # $0.28/1M
            'cost_per_1k_output': Decimal('0.00110'),  # $1.10/1M
        },
        # GPT-4o mini - Sehr günstig für einfache Tasks
        'gpt4o-mini': {
            'api_url': 'https://api.openai.com/v1/chat/completions',
            'model': 'gpt-4o-mini',
            'api_key_env': 'OPENAI_API_KEY',
            'cost_per_1k_input': Decimal('0.00015'),   # $0.15/1M
            'cost_per_1k_output': Decimal('0.00060'),  # $0.60/1M
        },
        # Gemini 2.0 Flash - Schnell & günstig
        'gemini-flash': {
            'api_url': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent',
            'model': 'gemini-2.0-flash',
            'api_key_env': 'GEMINI_API_KEY',
            'cost_per_1k_input': Decimal('0.00015'),
            'cost_per_1k_output': Decimal('0.00060'),
        },
        # ═══════════════════════════════════════════════════════════════
        # OpenRouter - Universal Gateway zu allen Modellen
        # ═══════════════════════════════════════════════════════════════
        'openrouter-deepseek-v3': {
            'api_url': 'https://openrouter.ai/api/v1/chat/completions',
            'model': 'deepseek/deepseek-chat',
            'api_key_env': 'OPENROUTER_API_KEY',
            'cost_per_1k_input': Decimal('0.00014'),   # Via OpenRouter
            'cost_per_1k_output': Decimal('0.00028'),
        },
        'openrouter-codestral': {
            'api_url': 'https://openrouter.ai/api/v1/chat/completions',
            'model': 'mistralai/codestral-latest',
            'api_key_env': 'OPENROUTER_API_KEY',
            'cost_per_1k_input': Decimal('0.00030'),
            'cost_per_1k_output': Decimal('0.00090'),
        },
        'openrouter-llama-70b': {
            'api_url': 'https://openrouter.ai/api/v1/chat/completions',
            'model': 'meta-llama/llama-3.3-70b-instruct',
            'api_key_env': 'OPENROUTER_API_KEY',
            'cost_per_1k_input': Decimal('0.00035'),
            'cost_per_1k_output': Decimal('0.00040'),
        },
    }
    
    def __init__(self, model_name: str = 'auto', task: str = None):
        self.model_name = model_name
        self._current_task = task
        self.config = self._get_config(model_name)
    
    async def _log_usage(
        self,
        task: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: Decimal,
        latency_ms: float,
        success: bool,
        error_message: str = None,
        prompt_text: str = None,
        response_text: str = None,
        context_metadata: dict = None
    ):
        """Log LLM usage to database with content."""
        try:
            from apps.bfagent.models_controlling import LLMUsageLog
            await asyncio.to_thread(
                LLMUsageLog.objects.create,
                agent='WorkerLLMClient',
                task=task,
                model=self.config.get('model', self.model_name),
                provider=self.PROVIDER_MAP.get(self.model_name, 'unknown'),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                prompt_text=prompt_text[:2000] if prompt_text else None,
                response_text=response_text[:4000] if response_text else None,
                context_metadata=context_metadata or {}
            )
        except Exception as e:
            logger.warning(f"Failed to log LLM usage: {e}")
    
    def _get_config(self, model_name: str) -> Dict:
        """Holt Config für Model, mit DB-Override wenn vorhanden."""
        if model_name == 'auto':
            # Wähle bestes Preis-Leistungs-Model für Coding
            # Priorität: DeepSeek V3 direkt > OpenRouter > gpt4o-mini > gemini-flash > groq
            for name in ['deepseek-v3', 'openrouter-deepseek-v3', 'gpt4o-mini', 'gemini-flash', 'groq-mixtral']:
                config = self.DEFAULT_CONFIGS.get(name, {})
                if os.environ.get(config.get('api_key_env', '')):
                    self.model_name = name
                    return config
            # Fallback zu GPT-4o mini (OPENAI_API_KEY meist vorhanden)
            self.model_name = 'gpt4o-mini'
            return self.DEFAULT_CONFIGS['gpt4o-mini']
        
        return self.DEFAULT_CONFIGS.get(model_name, self.DEFAULT_CONFIGS['gpt4o-mini'])
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Generiert Code via Worker-LLM."""
        api_key = os.environ.get(self.config.get('api_key_env', ''))
        
        if not api_key:
            return {
                'success': False,
                'error': f"API Key nicht gesetzt: {self.config.get('api_key_env')}",
                'model': self.model_name,
            }
        
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        payload = {
            'model': self.config.get('model'),
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.get('api_url'),
                    headers={
                        'Authorization': f"Bearer {api_key}",
                        'Content-Type': 'application/json',
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': result.get('error', {}).get('message', str(result)),
                            'model': self.model_name,
                            'duration_ms': int((time.time() - start_time) * 1000),
                        }
                    
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    usage = result.get('usage', {})
                    
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    
                    cost = (
                        Decimal(input_tokens) / 1000 * self.config.get('cost_per_1k_input', Decimal('0')) +
                        Decimal(output_tokens) / 1000 * self.config.get('cost_per_1k_output', Decimal('0'))
                    )
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Log to database with content
                    await self._log_usage(
                        task=self._current_task or 'code_delegation',
                        tokens_in=input_tokens,
                        tokens_out=output_tokens,
                        cost_usd=cost,
                        latency_ms=duration_ms,
                        success=True,
                        prompt_text=prompt,
                        response_text=content,
                        context_metadata=getattr(self, '_context_metadata', {})
                    )
                    
                    return {
                        'success': True,
                        'content': content,
                        'model': self.model_name,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'total_tokens': input_tokens + output_tokens,
                        'estimated_cost': float(cost),
                        'duration_ms': duration_ms,
                    }
                    
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            await self._log_usage(
                task=self._current_task or 'code_delegation',
                tokens_in=0, tokens_out=0, cost_usd=Decimal('0'),
                latency_ms=duration_ms, success=False, error_message='Request timeout'
            )
            return {
                'success': False,
                'error': 'Request timeout',
                'model': self.model_name,
                'duration_ms': duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Worker LLM error: {e}")
            await self._log_usage(
                task=self._current_task or 'code_delegation',
                tokens_in=0, tokens_out=0, cost_usd=Decimal('0'),
                latency_ms=duration_ms, success=False, error_message=str(e)
            )
            return {
                'success': False,
                'error': str(e),
                'model': self.model_name,
                'duration_ms': duration_ms,
            }


class ThinkingModelClient:
    """Client für Thinking Models (o1, Gemini Thinking, etc.)."""
    
    DEFAULT_CONFIGS = {
        'o1': {
            'api_url': 'https://api.openai.com/v1/chat/completions',
            'model': 'o1-preview',
            'api_key_env': 'OPENAI_API_KEY',
            'cost_per_1k_input': Decimal('0.015'),
            'cost_per_1k_output': Decimal('0.060'),
        },
        'o1-mini': {
            'api_url': 'https://api.openai.com/v1/chat/completions',
            'model': 'o1-mini',
            'api_key_env': 'OPENAI_API_KEY',
            'cost_per_1k_input': Decimal('0.003'),
            'cost_per_1k_output': Decimal('0.012'),
        },
        'gemini-thinking': {
            'api_url': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-thinking-exp:generateContent',
            'model': 'gemini-2.0-flash-thinking-exp',
            'api_key_env': 'GOOGLE_API_KEY',
            'cost_per_1k_input': Decimal('0.001'),
            'cost_per_1k_output': Decimal('0.004'),
        },
        'deepseek-r1': {
            'api_url': 'https://api.deepseek.com/v1/chat/completions',
            'model': 'deepseek-reasoner',
            'api_key_env': 'DEEPSEEK_API_KEY',
            'cost_per_1k_input': Decimal('0.00055'),
            'cost_per_1k_output': Decimal('0.00219'),
        },
    }
    
    def __init__(self, model_name: str = 'auto'):
        self.model_name = model_name
        self.config = self._get_config(model_name)
    
    def _get_config(self, model_name: str) -> Dict:
        """Holt Config für Thinking Model."""
        if model_name == 'auto':
            # Wähle günstigstes verfügbares
            for name in ['deepseek-r1', 'gemini-thinking', 'o1-mini', 'o1']:
                config = self.DEFAULT_CONFIGS.get(name, {})
                if os.environ.get(config.get('api_key_env', '')):
                    self.model_name = name
                    return config
            self.model_name = 'o1-mini'
            return self.DEFAULT_CONFIGS['o1-mini']
        
        return self.DEFAULT_CONFIGS.get(model_name, self.DEFAULT_CONFIGS['o1-mini'])
    
    async def reason(
        self,
        task: str,
        context: str = None,
        max_tokens: int = 8000,
    ) -> Dict[str, Any]:
        """Führt Reasoning durch via Thinking Model."""
        api_key = os.environ.get(self.config.get('api_key_env', ''))
        
        if not api_key:
            return {
                'success': False,
                'error': f"API Key nicht gesetzt: {self.config.get('api_key_env')}",
                'model': self.model_name,
            }
        
        prompt = f"""Analysiere diese Aufgabe und erstelle einen strukturierten Plan:

AUFGABE:
{task}

{f"KONTEXT:{chr(10)}{context}" if context else ""}

Gib einen JSON-Plan zurück mit:
{{
    "analysis": "Kurze Analyse der Aufgabe",
    "complexity": "simple|medium|complex",
    "steps": [
        {{"step": 1, "action": "Beschreibung", "type": "code|config|test|etc"}},
        ...
    ],
    "risks": ["Potentielle Risiken"],
    "estimated_effort": "Minuten"
}}"""
        
        start_time = time.time()
        
        try:
            # Für Gemini ist das API anders
            if 'gemini' in self.model_name:
                return await self._call_gemini(prompt, api_key, start_time)
            else:
                return await self._call_openai_style(prompt, api_key, max_tokens, start_time)
                
        except Exception as e:
            logger.error(f"Thinking Model error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': self.model_name,
                'duration_ms': int((time.time() - start_time) * 1000),
            }
    
    async def _call_openai_style(
        self, 
        prompt: str, 
        api_key: str, 
        max_tokens: int,
        start_time: float
    ) -> Dict[str, Any]:
        """Ruft OpenAI-style API auf (o1, DeepSeek)."""
        messages = [{'role': 'user', 'content': prompt}]
        
        payload = {
            'model': self.config.get('model'),
            'messages': messages,
        }
        
        # o1 models don't support max_tokens in the same way
        if 'o1' not in self.model_name:
            payload['max_tokens'] = max_tokens
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.config.get('api_url'),
                headers={
                    'Authorization': f"Bearer {api_key}",
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # Thinking takes longer
            ) as response:
                result = await response.json()
                
                if response.status != 200:
                    return {
                        'success': False,
                        'error': result.get('error', {}).get('message', str(result)),
                        'model': self.model_name,
                        'duration_ms': int((time.time() - start_time) * 1000),
                    }
                
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                usage = result.get('usage', {})
                
                # Parse JSON from response
                plan = self._extract_json(content)
                
                return {
                    'success': True,
                    'content': content,
                    'plan': plan,
                    'model': self.model_name,
                    'input_tokens': usage.get('prompt_tokens', 0),
                    'output_tokens': usage.get('completion_tokens', 0),
                    'duration_ms': int((time.time() - start_time) * 1000),
                }
    
    async def _call_gemini(
        self, 
        prompt: str, 
        api_key: str,
        start_time: float
    ) -> Dict[str, Any]:
        """Ruft Gemini API auf."""
        payload = {
            'contents': [{'parts': [{'text': prompt}]}]
        }
        
        url = f"{self.config.get('api_url')}?key={api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                result = await response.json()
                
                if response.status != 200:
                    return {
                        'success': False,
                        'error': str(result),
                        'model': self.model_name,
                        'duration_ms': int((time.time() - start_time) * 1000),
                    }
                
                content = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                plan = self._extract_json(content)
                
                return {
                    'success': True,
                    'content': content,
                    'plan': plan,
                    'model': self.model_name,
                    'duration_ms': int((time.time() - start_time) * 1000),
                }
    
    def _extract_json(self, text: str) -> Dict:
        """Extrahiert JSON aus Text."""
        import re
        try:
            # Suche nach JSON-Block
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        return {}


class OrchestrationService:
    """Hauptservice für Cascade Router Architecture."""
    
    def __init__(self):
        self.worker_client = WorkerLLMClient('auto')
        self.thinking_client = ThinkingModelClient('auto')
    
    async def parallel_reason(
        self,
        user_input: str,
        task_category: str = 'coding',
        include_thinking: bool = True,
    ) -> Dict[str, Any]:
        """
        Führt paralleles Reasoning durch.
        
        Path A: Cascade analysiert direkt (simuliert hier)
        Path B: Thinking Model analysiert parallel
        """
        from ..models_orchestration import ReasoningComparison
        
        # Comparison-Record erstellen
        comparison = ReasoningComparison.objects.create(
            user_input=user_input,
            task_category=task_category,
        )
        
        start_time = time.time()
        
        # Path A: Cascade Reasoning (hier simuliert mit einfacher Analyse)
        cascade_plan = self._cascade_analyze(user_input)
        comparison.cascade_plan = cascade_plan
        comparison.cascade_duration_ms = int((time.time() - start_time) * 1000)
        
        # Path B: Thinking Model (parallel wenn aktiviert)
        thinking_result = None
        if include_thinking:
            thinking_result = await self.thinking_client.reason(
                task=user_input,
                context=None
            )
            
            if thinking_result.get('success'):
                comparison.thinking_model = self.thinking_client.model_name
                comparison.thinking_response = thinking_result.get('content')
                comparison.thinking_plan = thinking_result.get('plan', {})
                comparison.thinking_duration_ms = thinking_result.get('duration_ms')
                comparison.thinking_tokens = (
                    thinking_result.get('input_tokens', 0) + 
                    thinking_result.get('output_tokens', 0)
                )
        
        # Vergleich
        comparison.similarity_score = self._compare_plans(
            cascade_plan,
            comparison.thinking_plan
        )
        comparison.plans_identical = comparison.similarity_score > 0.9
        
        # Speichern
        comparison.save()
        
        return {
            'comparison_id': str(comparison.id),
            'cascade_plan': cascade_plan,
            'thinking_plan': comparison.thinking_plan if thinking_result else None,
            'thinking_model': self.thinking_client.model_name if thinking_result else None,
            'similarity_score': comparison.similarity_score,
            'recommended_path': 'A' if comparison.similarity_score > 0.7 else 'B',
        }
    
    def _cascade_analyze(self, user_input: str) -> Dict:
        """Cascade's eigene Analyse (Placeholder - in Realität bin ich das)."""
        # Dies wird in der Praxis von Cascade selbst gemacht
        # Hier nur als Struktur für den Vergleich
        return {
            'analysis': 'Cascade direct analysis',
            'steps': [],
            'complexity': 'medium',
        }
    
    def _compare_plans(self, plan_a: Dict, plan_b: Dict) -> float:
        """Vergleicht zwei Pläne und gibt Ähnlichkeit zurück."""
        if not plan_a or not plan_b:
            return 0.0
        
        # Einfacher Vergleich basierend auf Anzahl Steps
        steps_a = len(plan_a.get('steps', []))
        steps_b = len(plan_b.get('steps', []))
        
        if steps_a == 0 and steps_b == 0:
            return 1.0
        
        if steps_a == 0 or steps_b == 0:
            return 0.0
        
        # Ähnlichkeit basierend auf Step-Anzahl
        return 1.0 - abs(steps_a - steps_b) / max(steps_a, steps_b)
    
    async def delegate_code_generation(
        self,
        task_type: str,
        component_name: str,
        specification: Dict[str, Any],
        context: Dict[str, Any] = None,
        output_path: str = None,
        worker_model: str = 'auto',
    ) -> Dict[str, Any]:
        """
        Delegiert Code-Generierung an Worker-LLM.
        """
        from ..models_orchestration import CodeGenerationLog
        
        # Log erstellen
        log = CodeGenerationLog.objects.create(
            task_type=task_type,
            component_name=component_name,
            output_path=output_path or '',
            specification=specification,
            context_provided=context or {},
            method_used='llm',
        )
        
        # Prompt bauen
        prompt = self._build_code_prompt(task_type, component_name, specification, context)
        system_prompt = self._get_system_prompt(task_type)
        
        # Worker aufrufen
        client = WorkerLLMClient(worker_model)
        result = await client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=4000,
            temperature=0.1,
        )
        
        # Log aktualisieren
        log.worker_model = client.model_name
        log.completed_at = timezone.now()
        log.duration_ms = result.get('duration_ms')
        log.success = result.get('success', False)
        log.tokens_used = result.get('total_tokens', 0)
        log.estimated_cost = Decimal(str(result.get('estimated_cost', 0)))
        
        if result.get('success'):
            log.generated_code = result.get('content')
            # Basis-Validierung
            log.syntax_valid = self._validate_syntax(result.get('content', ''), task_type)
        else:
            log.error_message = result.get('error')
        
        log.save()
        
        return {
            'success': result.get('success', False),
            'log_id': str(log.id),
            'generated_code': result.get('content') if result.get('success') else None,
            'worker_model': client.model_name,
            'duration_ms': result.get('duration_ms'),
            'tokens_used': result.get('total_tokens', 0),
            'estimated_cost': result.get('estimated_cost', 0),
            'syntax_valid': log.syntax_valid,
            'error': result.get('error'),
        }
    
    def _build_code_prompt(
        self,
        task_type: str,
        component_name: str,
        specification: Dict,
        context: Dict = None,
    ) -> str:
        """Baut Prompt für Code-Generierung."""
        prompt = f"""Generiere einen Django {task_type}: {component_name}

SPEZIFIKATION:
{json.dumps(specification, indent=2)}
"""
        
        if context:
            prompt += f"\nKONTEXT:\n{json.dumps(context, indent=2)}"
        
        prompt += """

ANFORDERUNGEN:
- Sauberer, produktionsreifer Code
- Django Best Practices
- Alle nötigen Imports
- Keine Kommentare außer Docstrings
- Nur der Code, keine Erklärungen

Gib NUR den Code zurück, ohne Markdown-Blöcke."""
        
        return prompt
    
    def _get_system_prompt(self, task_type: str) -> str:
        """System-Prompt basierend auf Task-Type."""
        base = "Du bist ein erfahrener Django-Entwickler. Generiere sauberen, produktionsreifen Code."
        
        specifics = {
            'template': "Fokus auf Bootstrap 5, HTMX, saubere Jinja2-Syntax.",
            'view': "Class-based Views bevorzugen, Login-Required wo nötig.",
            'model': "Klare Feldnamen, Meta-Klasse, __str__ Methode.",
            'urls': "RESTful URL-Patterns, app_name setzen.",
            'form': "ModelForm wo möglich, Widgets optimieren.",
        }
        
        return f"{base} {specifics.get(task_type, '')}"
    
    def _validate_syntax(self, code: str, task_type: str) -> bool:
        """Basis-Syntax-Validierung."""
        if not code or not code.strip():
            return False
        
        if task_type in ['view', 'model', 'form', 'urls', 'service']:
            # Python Syntax Check
            try:
                compile(code, '<string>', 'exec')
                return True
            except SyntaxError:
                return False
        
        if task_type == 'template':
            # Basis HTML/Template Check
            return '{{' not in code or '}}' in code  # Ausgeglichene Django-Tags
        
        return True
