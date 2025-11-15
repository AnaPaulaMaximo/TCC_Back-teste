"""
Script de Configuração Inicial das Chaves API
Execute este arquivo para configurar suas chaves pela primeira vez
"""
from api_key_manager import APIKeyManager

def setup_keys():
    print("\n" + "="*60)
    print("🔐 CONFIGURAÇÃO DE CHAVES API DO GOOGLE GEMINI")
    print("="*60)
    
    manager = APIKeyManager()
    
    print("\n📋 Instruções:")
    print("1. Obtenha suas chaves em: https://aistudio.google.com/app/apikey")
    print("2. Você pode adicionar quantas chaves quiser")
    print("3. O sistema rotacionará automaticamente quando atingir limites")
    print("4. Digite 'sair' para finalizar\n")
    
    key_count = 0
    
    while True:
        print(f"\n➕ Adicionando Chave #{key_count + 1}")
        print("-" * 40)
        
        # Nome da chave
        default_name = f"chave_{key_count + 1}"
        name = input(f"Nome da chave [{default_name}]: ").strip()
        if not name:
            name = default_name
        
        if name.lower() == 'sair':
            break
        
        # API Key
        api_key = input("Cole a chave API: ").strip()
        
        if api_key.lower() == 'sair':
            break
        
        if not api_key:
            print("❌ Chave não pode ser vazia!")
            continue
        
        # Adiciona a chave
        try:
            manager.add_key(api_key, name)
            key_count += 1
            
            # Pergunta se quer adicionar mais
            continuar = input("\n➕ Adicionar outra chave? (s/N): ").strip().lower()
            if continuar not in ['s', 'sim', 'y', 'yes']:
                break
        
        except Exception as e:
            print(f"❌ Erro ao adicionar chave: {e}")
            continue
    
    # Mostra resumo
    print("\n" + "="*60)
    print("✅ CONFIGURAÇÃO CONCLUÍDA")
    print("="*60)
    
    if key_count > 0:
        manager.get_status()
        print(f"\n✅ {key_count} chave(s) configurada(s) com sucesso!")
        print("\n🚀 Agora você pode iniciar o servidor:")
        print("   python app.py")
    else:
        print("\n⚠️ Nenhuma chave foi adicionada.")
        print("Execute este script novamente para configurar.")
    
    print("\n" + "="*60)


def list_keys():
    """Lista as chaves configuradas"""
    manager = APIKeyManager()
    manager.get_status()


def add_single_key():
    """Adiciona uma única chave"""
    manager = APIKeyManager()
    
    print("\n➕ Adicionar Nova Chave")
    print("-" * 40)
    
    name = input("Nome da chave: ").strip()
    if not name:
        print("❌ Nome é obrigatório!")
        return
    
    api_key = input("Cole a chave API: ").strip()
    if not api_key:
        print("❌ Chave é obrigatória!")
        return
    
    try:
        manager.add_key(api_key, name)
        manager.get_status()
    except Exception as e:
        print(f"❌ Erro: {e}")


def remove_key():
    """Remove uma chave"""
    manager = APIKeyManager()
    manager.get_status()
    
    print("\n🗑️ Remover Chave")
    print("-" * 40)
    
    name = input("Nome da chave para remover: ").strip()
    if not name:
        print("❌ Nome é obrigatório!")
        return
    
    # Remove a chave da lista
    original_count = len(manager.keys_data['keys'])
    manager.keys_data['keys'] = [k for k in manager.keys_data['keys'] if k['name'] != name]
    
    if len(manager.keys_data['keys']) < original_count:
        manager._save_keys(manager.keys_data)
        print(f"✅ Chave '{name}' removida com sucesso!")
        manager.get_status()
    else:
        print(f"❌ Chave '{name}' não encontrada!")


def reset_key():
    """Reseta os erros de uma chave"""
    manager = APIKeyManager()
    manager.get_status()
    
    print("\n🔄 Resetar Chave")
    print("-" * 40)
    
    name = input("Nome da chave para resetar: ").strip()
    if not name:
        print("❌ Nome é obrigatório!")
        return
    
    manager.reset_key_errors(name)
    manager.get_status()


def interactive_menu():
    """Menu interativo"""
    while True:
        print("\n" + "="*60)
        print("🔐 GERENCIADOR DE CHAVES API - MENU PRINCIPAL")
        print("="*60)
        print("\n1. Configuração Inicial (múltiplas chaves)")
        print("2. Adicionar uma chave")
        print("3. Listar chaves")
        print("4. Remover uma chave")
        print("5. Resetar erros de uma chave")
        print("0. Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == '1':
            setup_keys()
        elif opcao == '2':
            add_single_key()
        elif opcao == '3':
            list_keys()
        elif opcao == '4':
            remove_key()
        elif opcao == '5':
            reset_key()
        elif opcao == '0':
            print("\n👋 Até logo!")
            break
        else:
            print("❌ Opção inválida!")


if __name__ == "__main__":
    interactive_menu()