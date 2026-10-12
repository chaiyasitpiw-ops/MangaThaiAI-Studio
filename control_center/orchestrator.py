"""
MangaThaiAI-Studio: Control Center Orchestrator
Dispatches manga image pages to Gaming PC Remote Worker over LAN and manages local task pipeline.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Orchestrator")


class MangaOrchestrator:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Paths
        self.base_dir = Path(self.config.get("paths", {}).get("base_dir", "."))
        self.inputs_dir = Path(self.config.get("paths", {}).get("inputs_dir", "./data/inputs"))
        self.outputs_dir = Path(self.config.get("paths", {}).get("outputs_dir", "./data/outputs"))
        self.cache_dir = Path(self.config.get("paths", {}).get("cache_dir", "./data/cache"))
        
        # Worker Config
        worker_cfg = self.config.get("network", {}).get("remote_worker", {})
        self.worker_host = worker_cfg.get("host", "127.0.0.1")
        self.worker_port = worker_cfg.get("port", 8888)
        self.worker_base_url = f"http://{self.worker_host}:{self.worker_port}"
        self.timeout = worker_cfg.get("timeout_seconds", 120)

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}, using defaults.")
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    async def check_worker_health(self) -> Dict[str, Any]:
        """Checks if Gaming PC Remote Worker is online and reachable over LAN."""
        health_url = f"{self.worker_base_url}/api/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(health_url)
                if res.status_code == 200:
                    data = res.json()
                    logger.info(f"Worker connected at {self.worker_base_url}: {data}")
                    return {"status": "online", "worker_url": self.worker_base_url, "details": data}
                else:
                    return {"status": "unhealthy", "code": res.status_code, "worker_url": self.worker_base_url}
        except httpx.ConnectError:
            return {
                "status": "offline",
                "error": f"Cannot connect to Gaming PC Worker at {self.worker_base_url}. Make sure worker service is running and LAN firewall allows port {self.worker_port}.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "worker_url": self.worker_base_url}

    async def submit_page_for_processing(self, image_path: Path) -> Dict[str, Any]:
        """Submits a single manga page image to Gaming PC Worker for OCR, Inpainting, and Translation."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at {image_path}")

        process_url = f"{self.worker_base_url}/api/v1/process-page"
        logger.info(f"Submitting {image_path.name} to Remote Worker ({process_url})...")

        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                with open(image_path, "rb") as f:
                    files = {"file": (image_path.name, f, "image/png")}
                    response = await client.post(process_url, files=files)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Worker returned error: {response.status_code} - {response.text}")
                    return {"error": response.text, "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Failed to submit task to worker: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    import asyncio

    orchestrator = MangaOrchestrator()
    print("Testing Gaming PC Worker Connectivity...")
    result = asyncio.run(orchestrator.check_worker_health())
    print("Health Check Result:", json.dumps(result, indent=2, ensure_ascii=False))
