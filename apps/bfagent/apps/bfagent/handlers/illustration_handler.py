"""
AI-Powered Image Generation Handler
Supports DALL-E 3 (OpenAI) and Stable Diffusion (Replicate)
"""
import os
import asyncio
import time
import re
import structlog
from typing import Dict, Any, Optional, List
from decimal import Decimal

logger = structlog.get_logger(__name__)


class ImageGenerationHandler:
    """
    Handler for AI Image Generation
    Supports multiple providers: DALL-E 3, Stable Diffusion
    """

    # Provider Pricing (per image in USD)
    PRICING = {
        'dalle3': {
            'standard': {'1024x1024': 0.040, '1024x1792': 0.080, '1792x1024': 0.080},
            'hd': {'1024x1024': 0.080, '1024x1792': 0.120, '1792x1024': 0.120},
        },
        'stable_diffusion': {
            'any': 0.020,  # via Replicate
        },
        'stability': {
            'sd3': 0.035,  # Direct Stability AI
            'sd3-turbo': 0.020,  # Faster & cheaper
        }
    }

    def __init__(self, mock_mode: bool = False):
        """Initialize handler with API keys
        
        Args:
            mock_mode: If True, return mock images instantly without API calls
        """
        self.mock_mode = mock_mode or os.getenv('ILLUSTRATION_MOCK_MODE', 'false').lower() == 'true'
        # API Keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY') or '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'
        self.replicate_api_token = os.getenv('REPLICATE_API_TOKEN')
        self.stability_api_key = os.getenv('STABILITY_API_KEY') or 'sk-BoG5vu1NUHCIwvBrCBu8IFHyvxigQvJgkRzZ9Jsck0dS9Nm2'
        self.log = logger.bind(handler="ImageGenerationHandler", mock_mode=self.mock_mode)

        if not self.mock_mode and not any([self.openai_api_key, self.stability_api_key, self.replicate_api_token]):
            raise ValueError("No API keys found. Set OPENAI_API_KEY, STABILITY_API_KEY, or REPLICATE_API_TOKEN")

    @staticmethod
    def sanitize_prompt(prompt: str, max_length: int = 4000) -> str:
        """Sanitize user input prompt before sending to LLM/Image API
        
        Args:
            prompt: Raw user input prompt
            max_length: Maximum allowed prompt length
            
        Returns:
            Sanitized prompt safe for API calls
        """
        if not prompt or not isinstance(prompt, str):
            return ""
        
        # Remove code blocks that could be injection attempts
        prompt = re.sub(r'```[\s\S]*?```', '', prompt)
        
        # Remove potential command injections
        prompt = prompt.replace('$(', '').replace('`', '')
        
        # Remove excessive whitespace
        prompt = ' '.join(prompt.split())
        
        # Enforce max length
        if len(prompt) > max_length:
            prompt = prompt[:max_length]
            logger.warning("prompt_truncated", original_length=len(prompt), max_length=max_length)
        
        return prompt.strip()

    def calculate_cost(self, provider: str, quality: str, resolution: str) -> Decimal:
        """Calculate cost for image generation"""
        if provider == 'dalle3':
            pricing = self.PRICING['dalle3'].get(quality, {})
            cost = pricing.get(resolution, 0.040)
        else:
            cost = self.PRICING['stable_diffusion']['any']

        return Decimal(str(cost))

    async def generate_with_dalle3(
        self,
        prompt: str,
        quality: str = 'standard',
        size: str = '1024x1024',
        num_images: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate images using OpenAI gpt-image-1 (DALL·E 3 successor) - Correct Async API
        """
        try:
            from openai import AsyncOpenAI
            import time
            import base64
            import tempfile
            import os

            sanitized_prompt = self.sanitize_prompt(prompt)
            client = AsyncOpenAI(api_key=self.openai_api_key)

            start_time = time.time()
            self.log.info("dalle3_generation_start", prompt_length=len(sanitized_prompt), quality=quality, size=size)

            # Map your app's "hd"/"standard" to new required values
            quality_mapped = "high" if quality in ("hd", "high") else "medium"
            
            # Correct: use gpt-image-1 model with await
            resp = await client.images.generate(
                model="gpt-image-1",
                prompt=sanitized_prompt,
                size=size,
                quality=quality_mapped,  # Use correct mapping
                n=1
            )

            generation_time = time.time() - start_time
            cost = float(self.calculate_cost('dalle3', quality, size))

            results = []
            # resp.data is a list; each item has b64_json (Base64)
            for i, d in enumerate(resp.data):
                b64 = d.b64_json
                img_bytes = base64.b64decode(b64)
                
                # Save to media directory with unique filename
                import uuid
                from django.conf import settings
                
                filename = f"illustrations/{uuid.uuid4().hex}.png"
                media_path = settings.MEDIA_ROOT / filename
                media_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(media_path, "wb") as f:
                    f.write(img_bytes)
                
                # Create proper URL for display
                image_url = f"{settings.MEDIA_URL}{filename}"

                results.append({
                    'image_url': image_url,       # Proper URL for display
                    'image_path': str(media_path), # Local file path
                    'image_bytes': img_bytes,     # Raw bytes
                    'revised_prompt': getattr(d, 'revised_prompt', sanitized_prompt),
                    'generation_time_seconds': generation_time,
                    'cost_usd': cost,
                    'provider': 'gpt-image-1',
                    'quality': quality,
                    'size': size,
                })

            self.log.info("dalle3_generation_success", images_count=len(results), duration=generation_time, cost=cost)
            return results

        except Exception as e:
            self.log.error("dalle3_generation_error", error=str(e), error_type=type(e).__name__)
            raise Exception(f"DALL-E 3 generation failed: {str(e)}")

    async def generate_with_stable_diffusion(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_outputs: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate images with Stable Diffusion via Replicate
        """
        if not self.replicate_api_token:
            raise ValueError("REPLICATE_API_TOKEN not found in environment")

        # Sanitize prompts
        sanitized_prompt = self.sanitize_prompt(prompt)
        sanitized_negative = self.sanitize_prompt(negative_prompt) if negative_prompt else ""

        if not sanitized_prompt:
            raise ValueError("Prompt cannot be empty after sanitization")

        try:
            import replicate
            from replicate.exceptions import ReplicateError

            start_time = time.time()
            self.log.info("stable_diffusion_start", prompt_length=len(sanitized_prompt), size=f"{width}x{height}")

            output = await asyncio.to_thread(
                replicate.run,
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": sanitized_prompt,
                    "negative_prompt": sanitized_negative,
                    "width": width,
                    "height": height,
                    "num_outputs": num_outputs,
                }
            )

            generation_time = time.time() - start_time
            cost = self.calculate_cost('stable_diffusion', 'standard', f"{width}x{height}")

            results = []
            for image_url in output:
                results.append({
                    'image_url': str(image_url),
                    'revised_prompt': sanitized_prompt,
                    'generation_time_seconds': generation_time / num_outputs,
                    'cost_usd': float(cost),
                    'provider': 'stable_diffusion',
                    'quality': 'standard',
                    'size': f"{width}x{height}",
                })

            self.log.info("stable_diffusion_success", images_count=len(results), duration=generation_time)
            return results

        except ReplicateError as e:
            self.log.error("stable_diffusion_api_error", error=str(e))
            raise Exception(f"Stable Diffusion API error: {str(e)}")
        except Exception as e:
            self.log.error("stable_diffusion_failed", error=str(e), error_type=type(e).__name__)
            raise Exception(f"Stable Diffusion generation failed: {str(e)}")

    async def generate_with_stability(
        self,
        prompt: str,
        aspect_ratio: str = '1:1',
        negative_prompt: Optional[str] = None,
        model: str = 'sd3-turbo',
        style_preset: Optional[str] = None,
        num_images: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate images with Stability AI (direct API)
        """
        if not self.stability_api_key:
            raise ValueError("STABILITY_API_KEY not found in environment")

        sanitized_prompt = self.sanitize_prompt(prompt)
        sanitized_negative = self.sanitize_prompt(negative_prompt) if negative_prompt else None

        if not sanitized_prompt:
            raise ValueError("Prompt cannot be empty after sanitization")

        try:
            import requests
            import base64
            import tempfile

            start_time = time.time()
            self.log.info("stability_generation_start", 
                         prompt_length=len(sanitized_prompt), 
                         aspect_ratio=aspect_ratio,
                         model=model)

            # Prepare request
            url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
            headers = {
                "Authorization": f"Bearer {self.stability_api_key}",
                "Accept": "image/*"
            }
            
            data = {
                "prompt": sanitized_prompt,
                "aspect_ratio": aspect_ratio,
                "model": model,
                "output_format": "png"
            }
            
            if sanitized_negative:
                data["negative_prompt"] = sanitized_negative
            
            if style_preset:
                data["style_preset"] = style_preset

            # Make request in thread pool
            response = await asyncio.to_thread(
                requests.post,
                url,
                headers=headers,
                files={"none": ''},
                data=data,
                timeout=60
            )

            if response.status_code != 200:
                raise Exception(f"Stability API error: {response.status_code} - {response.text}")

            generation_time = time.time() - start_time
            cost = float(self.PRICING['stability'].get(model, 0.035))

            # Save image to media directory
            img_bytes = response.content
            import uuid
            from django.conf import settings
            
            filename = f"illustrations/{uuid.uuid4().hex}.png"
            media_path = settings.MEDIA_ROOT / filename
            media_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(media_path, "wb") as f:
                f.write(img_bytes)
            
            # Create proper URL for display
            image_url = f"{settings.MEDIA_URL}{filename}"

            results = [{
                'image_url': image_url,
                'image_path': str(media_path),
                'image_bytes': img_bytes,
                'revised_prompt': sanitized_prompt,
                'generation_time_seconds': generation_time,
                'cost_usd': cost,
                'provider': f'stability-{model}',
                'quality': 'standard',
                'size': aspect_ratio,
            }]

            self.log.info("stability_generation_success", 
                         images_count=len(results), 
                         duration=generation_time, 
                         cost=cost)
            return results

        except Exception as e:
            self.log.error("stability_generation_error", error=str(e), error_type=type(e).__name__)
            raise Exception(f"Stability AI generation failed: {str(e)}")

    async def generate_mock_image(
        self,
        prompt: str,
        quality: str = 'standard',
        size: str = '1024x1024',
        provider: str = 'dalle3'
    ) -> List[Dict[str, Any]]:
        """
        Generate mock image for testing (instant, no API call)
        Uses random placeholder images
        """
        import random
        
        # Simulate small delay (0.5s)
        await asyncio.sleep(0.5)
        
        cost = self.calculate_cost(provider, quality, size)
        
        # Random placeholder image
        random_id = random.randint(1, 1000)
        
        return [{
            'image_url': f'https://picsum.photos/{size.replace("x", "/")}?random={random_id}',
            'revised_prompt': f"[MOCK] {prompt}",
            'generation_time_seconds': 0.5,
            'cost_usd': float(cost),
            'provider': provider,
            'quality': quality,
            'size': size,
        }]

    async def generate_image(
        self,
        prompt: str,
        provider: str = 'dalle3',
        quality: str = 'standard',
        size: str = '1024x1024',
        negative_prompt: Optional[str] = None,
        num_images: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for image generation
        Routes to appropriate provider or mock
        """
        try:
            # Validate inputs
            if not prompt:
                raise ValueError("Prompt cannot be empty")
            
            if provider not in ['dalle3', 'stable_diffusion', 'stability']:
                raise ValueError(f"Unsupported provider: {provider}. Use 'dalle3', 'stable_diffusion', or 'stability'")
            
            # Use mock mode if enabled
            if self.mock_mode:
                self.log.info("using_mock_mode", provider=provider)
                return await self.generate_mock_image(
                    prompt=prompt,
                    quality=quality,
                    size=size,
                    provider=provider
                )
            
            if provider == 'dalle3':
                return await self.generate_with_dalle3(
                    prompt=prompt,
                    quality=quality,
                    size=size,
                    num_images=min(num_images, 1)
                )
            elif provider == 'stable_diffusion':
                # Use Stability AI directly (faster, has API key)
                # Falls back from Replicate to direct Stability API
                size_to_aspect = {
                    '1024x1024': '1:1',
                    '1792x1024': '16:9',
                    '1024x1792': '9:16',
                    '1536x1024': '3:2',
                    '1024x1536': '2:3',
                }
                aspect_ratio = size_to_aspect.get(size, '1:1')
                
                return await self.generate_with_stability(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    negative_prompt=negative_prompt,
                    model='sd3-turbo',
                    num_images=min(num_images, 1)
                )
            elif provider == 'stability':
                # Map size to aspect ratio for Stability AI
                size_to_aspect = {
                    '1024x1024': '1:1',
                    '1792x1024': '16:9',
                    '1024x1792': '9:16',
                    '1536x1024': '3:2',
                    '1024x1536': '2:3',
                }
                aspect_ratio = size_to_aspect.get(size, '1:1')
                
                return await self.generate_with_stability(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    negative_prompt=negative_prompt,
                    model='sd3-turbo',  # Faster & cheaper
                    num_images=min(num_images, 1)
                )
        except Exception as e:
            self.log.error("image_generation_failed", provider=provider, error=str(e))
            raise


class PromptEnhancer:
    """
    Enhances prompts for better image generation
    Combines style profile + content context
    """

    @staticmethod
    def enhance_prompt(
        base_prompt: str,
        style_profile_prompt: Optional[str] = None,
        image_type: str = 'scene_illustration',
        enhance: bool = True
    ) -> str:
        """
        Enhance prompt with style and best practices
        """
        parts = []

        # Add base prompt
        if base_prompt:
            parts.append(base_prompt)

        # Add style profile
        if style_profile_prompt:
            parts.append(style_profile_prompt)

        # Add image type specific enhancements
        if enhance:
            enhancements = {
                'scene_illustration': 'highly detailed, professional illustration',
                'character_portrait': 'portrait, centered, detailed face, character design',
                'location': 'establishing shot, wide angle, environmental design',
                'cover': 'book cover art, dramatic composition, eye-catching',
            }
            if image_type in enhancements:
                parts.append(enhancements[image_type])

        return ', '.join(parts)

    @staticmethod
    def build_negative_prompt(
        base_negative: Optional[str] = None,
        image_type: str = 'scene_illustration'
    ) -> str:
        """
        Build comprehensive negative prompt
        """
        defaults = [
            "low quality",
            "blurry",
            "distorted",
            "deformed",
            "watermark",
            "text"
        ]

        if base_negative:
            defaults.append(base_negative)

        return ', '.join(defaults)
