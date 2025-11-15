"""
Gerenciador de Chaves API do Google Gemini
Rotaciona automaticamente entre múltiplas chaves quando uma atinge o limite
"""
import google.generativeai as genai
from datetime import datetime, timedelta
import json
import os

class APIKeyManager:
    def __init__(self, keys_file='api_keys.json'):
        """
        Inicializa o gerenciador de chaves
        
        Args:
            keys_file: Caminho para o arquivo JSON com as chaves
        """
        self.keys_file = keys_file
        self.keys_data = self._load_keys()
        self.current_key_index = 0
        # Só configura se houver chaves
        if self.keys_data.get('keys'):
            self.configure_current_key()
    
    def _load_keys(self):
        """Carrega as chaves do arquivo JSON"""
        if os.path.exists(self.keys_file):
            with open(self.keys_file, 'r') as f:
                return json.load(f)
        else:
            # Cria estrutura inicial se o arquivo não existir
            default_structure = {
                "keys": [],
                "last_rotation": None
            }
            self._save_keys(default_structure)
            return default_structure
    
    def _save_keys(self, data):
        """Salva o estado das chaves no arquivo JSON"""
        with open(self.keys_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    def add_key(self, api_key, name=None):
        """
        Adiciona uma nova chave ao pool
        
        Args:
            api_key: A chave API
            name: Nome identificador para a chave (opcional)
        """
        if name is None:
            name = f"key_{len(self.keys_data['keys']) + 1}"
        
        key_entry = {
            "name": name,
            "key": api_key,
            "active": True,
            "error_count": 0,
            "last_error": None,
            "blocked_until": None
        }
        
        self.keys_data['keys'].append(key_entry)
        self._save_keys(self.keys_data)
        print(f"✅ Chave '{name}' adicionada com sucesso!")
    
    def get_current_key(self):
        """Retorna a chave atual"""
        if not self.keys_data['keys']:
            raise ValueError("Nenhuma chave API configurada!")
        
        return self.keys_data['keys'][self.current_key_index]
    
    def configure_current_key(self):
        """Configura o Gemini com a chave atual"""
        current = self.get_current_key()
        genai.configure(api_key=current['key'])
        print(f"🔑 Usando chave: {current['name']}")
    
    def rotate_key(self, reason="manual"):
        """
        Rotaciona para a próxima chave disponível
        
        Args:
            reason: Motivo da rotação (para log)
        """
        if len(self.keys_data['keys']) <= 1:
            print("⚠️ Apenas uma chave disponível, não é possível rotacionar!")
            return False
        
        # Marca a chave atual como com erro
        current = self.keys_data['keys'][self.current_key_index]
        current['error_count'] += 1
        current['last_error'] = datetime.now().isoformat()
        
        # Se atingiu muitos erros, bloqueia temporariamente (24h)
        if current['error_count'] >= 3:
            current['blocked_until'] = (datetime.now() + timedelta(hours=24)).isoformat()
            current['active'] = False
            print(f"🚫 Chave '{current['name']}' bloqueada até {current['blocked_until']}")
        
        # Procura a próxima chave disponível
        attempts = 0
        original_index = self.current_key_index
        
        while attempts < len(self.keys_data['keys']):
            self.current_key_index = (self.current_key_index + 1) % len(self.keys_data['keys'])
            next_key = self.keys_data['keys'][self.current_key_index]
            
            # Verifica se a chave está disponível
            if self._is_key_available(next_key):
                self.keys_data['last_rotation'] = datetime.now().isoformat()
                self._save_keys(self.keys_data)
                self.configure_current_key()
                print(f"🔄 Rotação realizada: {reason}")
                print(f"   {self.keys_data['keys'][original_index]['name']} → {next_key['name']}")
                return True
            
            attempts += 1
        
        print("❌ Nenhuma chave disponível para rotação!")
        return False
    
    def _is_key_available(self, key_entry):
        """Verifica se uma chave está disponível para uso"""
        if not key_entry['active']:
            # Verifica se o bloqueio expirou
            if key_entry['blocked_until']:
                blocked_until = datetime.fromisoformat(key_entry['blocked_until'])
                if datetime.now() > blocked_until:
                    # Reativa a chave
                    key_entry['active'] = True
                    key_entry['error_count'] = 0
                    key_entry['blocked_until'] = None
                    print(f"✅ Chave '{key_entry['name']}' reativada!")
                    return True
            return False
        return True
    
    def handle_api_error(self, error):
        """
        Trata erros da API e decide se deve rotacionar
        
        Args:
            error: Exceção capturada
            
        Returns:
            bool: True se rotacionou, False caso contrário
        """
        error_str = str(error).lower()
        
        # Erros que indicam limite atingido
        quota_errors = [
            'quota',
            'rate limit',
            'too many requests',
            'resource exhausted',
            '429',
            'daily limit exceeded'
        ]
        
        should_rotate = any(err in error_str for err in quota_errors)
        
        if should_rotate:
            print(f"⚠️ Limite de API detectado: {error}")
            return self.rotate_key(reason="Limite de API atingido")
        else:
            print(f"❌ Erro não relacionado a quota: {error}")
            return False
    
    def get_status(self):
        """Retorna o status de todas as chaves"""
        print("\n" + "="*60)
        print("📊 STATUS DAS CHAVES API")
        print("="*60)
        
        for i, key in enumerate(self.keys_data['keys']):
            status = "🟢 ATIVA" if key['active'] else "🔴 BLOQUEADA"
            current = " ← ATUAL" if i == self.current_key_index else ""
            
            print(f"\n{key['name']}{current}")
            print(f"  Status: {status}")
            print(f"  Erros: {key['error_count']}")
            
            if key['last_error']:
                last_error = datetime.fromisoformat(key['last_error'])
                print(f"  Último erro: {last_error.strftime('%d/%m/%Y %H:%M:%S')}")
            
            if key['blocked_until']:
                blocked_until = datetime.fromisoformat(key['blocked_until'])
                print(f"  Bloqueada até: {blocked_until.strftime('%d/%m/%Y %H:%M:%S')}")
        
        print("\n" + "="*60)
    
    def reset_key_errors(self, key_name):
        """Reseta os erros de uma chave específica"""
        for key in self.keys_data['keys']:
            if key['name'] == key_name:
                key['error_count'] = 0
                key['active'] = True
                key['blocked_until'] = None
                key['last_error'] = None
                self._save_keys(self.keys_data)
                print(f"✅ Erros da chave '{key_name}' resetados!")
                return True
        
        print(f"❌ Chave '{key_name}' não encontrada!")
        return False


# ============================================
# EXEMPLO DE USO
# ============================================

def generate_with_retry(key_manager, prompt, model_name="gemini-2.5-flash", max_retries=3):
    """
    Gera conteúdo com retry automático em caso de erro de quota
    
    Args:
        key_manager: Instância do APIKeyManager
        prompt: Texto do prompt
        model_name: Nome do modelo Gemini
        max_retries: Número máximo de tentativas
        
    Returns:
        str: Resposta gerada ou None em caso de falha total
    """
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        
        except Exception as e:
            print(f"\n🔴 Tentativa {attempt + 1}/{max_retries} falhou")
            
            # Tenta rotacionar a chave
            if key_manager.handle_api_error(e):
                print("🔄 Tentando novamente com nova chave...")
                continue
            else:
                # Erro não relacionado a quota
                if attempt < max_retries - 1:
                    print("⏳ Aguardando antes de tentar novamente...")
                    import time
                    time.sleep(2)
                else:
                    print("❌ Todas as tentativas falharam!")
                    raise
    
    return None


# ============================================
# EXEMPLO DE INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    # Cria o gerenciador
    manager = APIKeyManager()
    
    # Adiciona suas chaves (faça isso uma vez, depois comente)
    # manager.add_key("SUA_CHAVE_API_1", "chave_principal")
    # manager.add_key("SUA_CHAVE_API_2", "chave_backup_1")
    # manager.add_key("SUA_CHAVE_API_3", "chave_backup_2")
    
    # Verifica o status
    manager.get_status()
    
    # Teste de geração com retry automático
    # prompt = "Explique o conceito de filosofia em 2 parágrafos."
    # resultado = generate_with_retry(manager, prompt)
    # if resultado:
    #     print("\n✅ RESPOSTA GERADA:")
    #     print(resultado)