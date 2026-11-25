import os
from dataclasses import dataclass

@dataclass
class Settings:
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:////data/app.db')
    allowed_origins: str = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000')
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '').strip()
    gemini_api_key: str = os.getenv('GEMINI_API_KEY', '').strip()
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    gemini_model: str = os.getenv('GEMINI_MODEL', 'gemini/gemini-3.8-flash')
    enable_failure_simulation: bool = os.getenv('ENABLE_FAILURE_SIMULATION', 'true').lower() == 'true'
    default_system_prompt: str = os.getenv('DEFAULT_SYSTEM_PROMPT', 'You are a helpful, clear and thoughtful AI assistant.')
    cache_dir: str = os.getenv('LITELLM_CACHE_DIR', '/data/litellm_cache')

    @property
    def providers(self):
        providers = []
        if self.openai_api_key:
            providers.append({'key_id':'key_1','provider':'OpenAI','model':self.openai_model,'api_key':self.openai_api_key})
        if self.gemini_api_key:
            providers.append({'key_id':'key_2' if providers else 'key_1','provider':'Gemini','model':self.gemini_model,'api_key':self.gemini_api_key})
        return providers
    @property
    def keys(self):
        return [p['api_key'] for p in self.providers]
    @property
    def model(self):
        return self.providers[0]['model'] if self.providers else self.openai_model
    @property
    def origins(self):
        return [x.strip() for x in self.allowed_origins.split(',') if x.strip()]

settings = Settings()
