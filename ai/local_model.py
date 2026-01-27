"""
Interface para modelos locais (Ollama, LlamaCPP, etc.)
"""
import os
from typing import List, Optional, Dict
from PIL import Image
import requests
import json


class LocalModelInterface:
    """Interface abstrata para modelos locais"""
    
    def __init__(self, model_name: str = "llama3.2", base_url: str = "http://localhost:11434"):
        """
        Inicializa interface para modelo local
        
        Args:
            model_name: Nome do modelo (ex: "llama3.2", "mistral", etc.)
            base_url: URL base do servidor local (Ollama padrão: http://localhost:11434)
        """
        self.model_name = model_name
        self.base_url = base_url
        self.enabled = os.getenv("USE_LOCAL_MODEL", "false").lower() == "true"
    
    def is_available(self) -> bool:
        """Verifica se o modelo local está disponível"""
        if not self.enabled:
            return False
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_text(self, prompt: str, images: Optional[List[Image.Image]] = None) -> str:
        """
        Gera texto usando modelo local
        
        Args:
            prompt: Prompt de texto
            images: Lista opcional de imagens PIL
        
        Returns:
            Texto gerado pelo modelo
        """
        if not self.is_available():
            raise RuntimeError("Modelo local não está disponível")
        
        # Ollama API
        if images:
            # Para imagens, precisamos converter para base64
            import base64
            from io import BytesIO
            
            image_data = []
            for img in images:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                image_data.append(img_str)
            
            # Ollama suporta imagens via API específica
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "images": image_data,
                "stream": False
            }
        else:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120  # Timeout maior para geração
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            raise RuntimeError(f"Erro ao gerar texto com modelo local: {str(e)}")


class OllamaModel(LocalModelInterface):
    """Implementação específica para Ollama"""
    
    def __init__(self, model_name: str = None):
        model_name = model_name or os.getenv("OLLAMA_MODEL_NAME", "llama3.2")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        super().__init__(model_name, base_url)


class LlamaCPPModel(LocalModelInterface):
    """Implementação para LlamaCPP (via servidor HTTP)"""
    
    def __init__(self, model_name: str = None):
        model_name = model_name or os.getenv("LLAMACPP_MODEL_NAME", "llama")
        base_url = os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080")
        super().__init__(model_name, base_url)
    
    def generate_text(self, prompt: str, images: Optional[List[Image.Image]] = None) -> str:
        """Gera texto usando LlamaCPP (pode ter API diferente)"""
        # Implementação específica para LlamaCPP se necessário
        # Por enquanto, usa a implementação base
        return super().generate_text(prompt, images)


def get_local_model() -> Optional[LocalModelInterface]:
    """
    Factory function para obter modelo local configurado
    
    Returns:
        Instância do modelo local ou None se não disponível
    """
    model_type = os.getenv("LOCAL_MODEL_TYPE", "ollama").lower()
    
    if model_type == "ollama":
        model = OllamaModel()
    elif model_type == "llamacpp":
        model = LlamaCPPModel()
    else:
        return None
    
    if model.is_available():
        return model
    
    return None
