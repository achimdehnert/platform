"""
ComfyUI Local Image Generation Handler
Provides fast, free, local image generation using Stable Diffusion XL
"""
import os
import json
import time
import uuid
import base64
import asyncio
import aiohttp
import structlog
from typing import Dict, Any, Optional, List
from decimal import Decimal
from pathlib import Path

logger = structlog.get_logger(__name__)


class ComfyUIHandler:
    """
    Handler for local ComfyUI image generation
    Supports SDXL, custom models, LoRAs, and batch generation
    
    Configuration:
        Set COMFYUI_URL environment variable or Django setting COMFYUI_URL
        Default: http://localhost:8181
    """
    
    # Default ComfyUI settings - Port 8181 ist der lokale Standard
    DEFAULT_URL = "http://localhost:8181"
    MODELS_PATH = Path.home() / "ai-tools" / "ComfyUI" / "models"
    
    # Available models and their download URLs
    AVAILABLE_MODELS = {
        'sdxl_base': {
            'filename': 'sd_xl_base_1.0.safetensors',
            'url': 'https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors',
            'size_gb': 6.5,
            'type': 'checkpoint'
        },
        'sdxl_refiner': {
            'filename': 'sd_xl_refiner_1.0.safetensors',
            'url': 'https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors',
            'size_gb': 6.1,
            'type': 'checkpoint'
        },
        'sdxl_vae': {
            'filename': 'sdxl_vae.safetensors',
            'url': 'https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors',
            'size_gb': 0.3,
            'type': 'vae'
        }
    }
    
    # Style presets for book illustration
    STYLE_PRESETS = {
        'fantasy_watercolor': {
            'positive_suffix': ', watercolor painting, fantasy illustration, soft edges, vibrant colors, magical atmosphere, professional illustration',
            'negative': 'photo, realistic, 3d render, blurry, modern, urban, text, watermark, signature',
            'cfg': 7.5,
            'steps': 25
        },
        'fantasy_digital': {
            'positive_suffix': ', digital art, fantasy illustration, highly detailed, dramatic lighting, epic scene, professional artwork',
            'negative': 'photo, realistic, blurry, low quality, text, watermark',
            'cfg': 8.0,
            'steps': 30
        },
        'childrens_book': {
            'positive_suffix': ', children book illustration, whimsical, colorful, friendly, storybook style, hand-drawn feel',
            'negative': 'scary, dark, realistic, photo, violent, adult content',
            'cfg': 7.0,
            'steps': 25
        },
        'noir': {
            'positive_suffix': ', film noir style, black and white, high contrast, dramatic shadows, cinematic, moody atmosphere',
            'negative': 'colorful, bright, cheerful, cartoon, anime',
            'cfg': 8.0,
            'steps': 30
        },
        'manga': {
            'positive_suffix': ', manga style, anime illustration, clean lines, expressive, dynamic composition, Japanese art style',
            'negative': 'photo, realistic, western cartoon, 3d render',
            'cfg': 7.5,
            'steps': 25
        },
        'realistic': {
            'positive_suffix': ', photorealistic, highly detailed, professional photography, cinematic lighting, 8k resolution',
            'negative': 'cartoon, anime, drawing, painting, illustration, low quality',
            'cfg': 7.0,
            'steps': 30
        }
    }

    def __init__(self, base_url: Optional[str] = None):
        """Initialize ComfyUI handler
        
        Args:
            base_url: ComfyUI server URL (default: http://localhost:8188)
        """
        self.base_url = base_url or os.getenv('COMFYUI_URL', self.DEFAULT_URL)
        self.log = logger.bind(handler="ComfyUIHandler", url=self.base_url)
        self.client_id = str(uuid.uuid4())
        
    async def check_connection(self) -> bool:
        """Check if ComfyUI server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/system_stats", timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            self.log.warning("comfyui_connection_failed", error=str(e))
            return False
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get ComfyUI system information"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/system_stats") as resp:
                return await resp.json()
    
    def get_installed_models(self) -> List[str]:
        """List installed checkpoint models"""
        checkpoints_path = self.MODELS_PATH / "checkpoints"
        if not checkpoints_path.exists():
            return []
        return [f.name for f in checkpoints_path.glob("*.safetensors")]
    
    def check_model_installed(self, model_key: str) -> bool:
        """Check if a specific model is installed"""
        if model_key not in self.AVAILABLE_MODELS:
            return False
        model_info = self.AVAILABLE_MODELS[model_key]
        model_path = self.MODELS_PATH / f"{model_info['type']}s" / model_info['filename']
        return model_path.exists()
    
    async def download_model(self, model_key: str, progress_callback=None) -> bool:
        """Download a model from HuggingFace
        
        Args:
            model_key: Key from AVAILABLE_MODELS
            progress_callback: Optional callback(downloaded_mb, total_mb)
        """
        if model_key not in self.AVAILABLE_MODELS:
            raise ValueError(f"Unknown model: {model_key}")
        
        model_info = self.AVAILABLE_MODELS[model_key]
        target_dir = self.MODELS_PATH / f"{model_info['type']}s"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / model_info['filename']
        
        if target_path.exists():
            self.log.info("model_already_exists", model=model_key)
            return True
        
        self.log.info("downloading_model", model=model_key, size_gb=model_info['size_gb'])
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(model_info['url']) as resp:
                    if resp.status != 200:
                        raise Exception(f"Download failed: HTTP {resp.status}")
                    
                    total_size = int(resp.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(target_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):  # 1MB chunks
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded / 1024 / 1024, total_size / 1024 / 1024)
            
            self.log.info("model_downloaded", model=model_key)
            return True
            
        except Exception as e:
            self.log.error("model_download_failed", model=model_key, error=str(e))
            if target_path.exists():
                target_path.unlink()  # Remove partial download
            raise
    
    def build_sdxl_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        cfg: float = 7.5,
        seed: int = -1,
        model: str = "sd_xl_base_1.0.safetensors"
    ) -> Dict[str, Any]:
        """Build a ComfyUI workflow for SDXL image generation
        
        Returns a workflow dict that can be sent to ComfyUI's /prompt endpoint
        """
        # Generate random seed if -1 or None
        if seed is None or seed == -1:
            import random
            seed = random.randint(0, 2**32 - 1)
        
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": cfg,
                    "denoise": 1,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "seed": seed,
                    "steps": steps
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": model
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": negative_prompt
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "comfyui_bfagent",
                    "images": ["8", 0]
                }
            }
        }
        
        return workflow
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        cfg: float = 7.5,
        seed: int = -1,
        style_preset: Optional[str] = None,
        model: str = "sd_xl_base_1.0.safetensors"
    ) -> Dict[str, Any]:
        """Generate an image using ComfyUI
        
        Args:
            prompt: The image description
            negative_prompt: What to avoid in the image
            width: Image width (default 1024)
            height: Image height (default 1024)
            steps: Number of diffusion steps (default 25)
            cfg: Classifier-free guidance scale (default 7.5)
            seed: Random seed (-1 for random)
            style_preset: Optional style preset from STYLE_PRESETS
            model: Checkpoint model filename
            
        Returns:
            Dict with image_url (base64), generation_time, seed_used
        """
        start_time = time.time()
        
        # Apply style preset if specified
        if style_preset and style_preset in self.STYLE_PRESETS:
            preset = self.STYLE_PRESETS[style_preset]
            prompt = prompt + preset['positive_suffix']
            negative_prompt = negative_prompt or preset['negative']
            cfg = preset.get('cfg', cfg)
            steps = preset.get('steps', steps)
        
        # Build workflow
        workflow = self.build_sdxl_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            seed=seed,
            model=model
        )
        
        self.log.info("generating_image", prompt_length=len(prompt), steps=steps, size=f"{width}x{height}")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Queue the prompt
                async with session.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow, "client_id": self.client_id}
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"Failed to queue prompt: {error_text}")
                    result = await resp.json()
                    prompt_id = result['prompt_id']
                
                # Wait for completion via WebSocket or polling
                image_result = await self._wait_for_image(session, prompt_id)
                
                generation_time = time.time() - start_time
                
                self.log.info("image_generated", duration=generation_time, prompt_id=prompt_id)
                
                return {
                    'success': True,
                    'image_url': image_result['file_url'],  # Proper file URL
                    'image_base64': image_result['base64'],
                    'generation_time_seconds': generation_time,
                    'seed_used': seed if seed != -1 else 'random',
                    'prompt_id': prompt_id,
                    'cost_usd': Decimal('0'),  # Free!
                    'provider': 'comfyui_local'
                }
                
        except Exception as e:
            self.log.error("generation_failed", error=str(e))
            raise
    
    async def _wait_for_image(self, session: aiohttp.ClientSession, prompt_id: str, timeout: int = 120) -> dict:
        """Wait for image generation to complete and return image data dict"""
        start = time.time()
        
        while time.time() - start < timeout:
            # Check history for completed prompt
            async with session.get(f"{self.base_url}/history/{prompt_id}") as resp:
                if resp.status == 200:
                    history = await resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get('outputs', {})
                        # Find the SaveImage node output
                        for node_id, node_output in outputs.items():
                            if 'images' in node_output:
                                image_info = node_output['images'][0]
                                # Get the actual image and save to file
                                return await self._get_image(session, image_info['filename'], image_info.get('subfolder', ''))
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError(f"Image generation timed out after {timeout}s")
    
    async def _get_image(self, session: aiohttp.ClientSession, filename: str, subfolder: str) -> dict:
        """Get image from ComfyUI and save to media folder, return URL and base64"""
        import os
        import uuid
        from django.conf import settings
        
        params = {'filename': filename}
        if subfolder:
            params['subfolder'] = subfolder
        params['type'] = 'output'
        
        async with session.get(f"{self.base_url}/view", params=params) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to get image: {resp.status}")
            image_bytes = await resp.read()
            
            # Save to media folder
            media_root = getattr(settings, 'MEDIA_ROOT', 'media')
            illustrations_dir = os.path.join(media_root, 'illustrations')
            os.makedirs(illustrations_dir, exist_ok=True)
            
            # Generate unique filename
            unique_name = f"scene_{uuid.uuid4().hex[:12]}.png"
            file_path = os.path.join(illustrations_dir, unique_name)
            
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            
            # Return both file URL and base64
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            file_url = f"{media_url}illustrations/{unique_name}"
            
            return {
                'file_url': file_url,
                'base64': base64.b64encode(image_bytes).decode('utf-8')
            }
    
    async def generate_batch(
        self,
        prompts: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Generate multiple images in sequence
        
        Args:
            prompts: List of prompts to generate
            **kwargs: Additional arguments passed to generate_image
            
        Returns:
            List of generation results
        """
        results = []
        for i, prompt in enumerate(prompts):
            self.log.info("batch_progress", current=i+1, total=len(prompts))
            result = await self.generate_image(prompt, **kwargs)
            results.append(result)
        return results


# Synchronous wrapper for Django views
def generate_image_sync(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    cfg: float = 7.5,
    seed: int = -1,
    style_preset: Optional[str] = None,
    model: str = "sd_xl_base_1.0.safetensors",
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """Synchronous wrapper for generate_image"""
    handler = ComfyUIHandler(base_url)
    return asyncio.run(handler.generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        steps=steps,
        cfg=cfg,
        seed=seed,
        style_preset=style_preset,
        model=model
    ))
