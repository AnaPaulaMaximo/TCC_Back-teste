Aqui está o seu texto transformado em Markdown profissional, pronto para ser usado como um arquivo `README.md` no GitHub ou GitLab.

Organizei os comandos em blocos de código, criei uma tabela para os usuários de teste e formatei a estrutura de arquivos para melhor visualização.

-----

# Repensei - Backend API (TCC)

Este repositório contém o código-fonte do Backend da aplicação **Repensei**, um projeto de TCC focado no ensino de Filosofia e Sociologia. A aplicação utiliza inteligência artificial para gerar conteúdo personalizado e opera sob um modelo de negócios Freemium.

O sistema é construído em Python com Flask e integra-se à API do Google Gemini para geração de conteúdo dinâmico.

## 📋 Funcionalidades

O sistema divide-se em três níveis de acesso principais:

### 1\. Aluno Freemium (Gratuito)

  * **Acesso a conteúdo estático:** Banco de questões e flashcards pré-definidos (curadoria).
  * **Foco:** Conteúdo para revisão geral de Filosofia e Sociologia.

### 2\. Aluno Premium (Pago)

  * **Geração de Conteúdo via IA:** Criação de Quizzes, Flashcards e Resumos inéditos sobre qualquer tema solicitado.
  * **Correção de Redação:** Envio de textos para análise e feedback detalhado da IA.
  * **Histórico de Atividades:** Salvamento automático de todo conteúdo gerado e resultados de quizzes.
  * **Chatbot Tutor:** Assistente virtual em tempo real para debates filosóficos.

### 3\. Administrador

  * **Dashboard:** Visualização de estatísticas (total de alunos, distribuição por plano, médias de acertos).
  * **Gestão de Usuários:** CRUD completo de alunos.
  * **Monitoramento:** Acompanhamento do uso da plataforma.

-----

## 🛠️ Tecnologias Utilizadas

  * **Linguagem:** Python 3.x
  * **Framework Web:** Flask
  * **Banco de Dados:** SQLite (`repensei.db`)
  * **IA Generativa:** Google Gemini (Modelo `gemini-2.5-flash`)
  * **Real-time:** Flask-SocketIO (para o Chatbot)
  * **Gerenciamento de Chaves:** Sistema proprietário de rotação de chaves API (`api_key_manager.py`) para contornar limites de quota.

-----

## 🚀 Instalação e Configuração

Siga os passos abaixo para rodar o projeto localmente.

### 1\. Pré-requisitos

  * Python 3.8 ou superior instalado.
  * Git instalado.

### 2\. Clonar o Repositório

```bash
git clone <url-do-seu-repositorio>
cd TCC_Backend
```

### 3\. Criar e Ativar Ambiente Virtual

Recomendado para isolar as dependências do projeto.

  * **Windows:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
  * **Linux/Mac:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

### 4\. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 5\. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto e defina uma chave secreta para as sessões do Flask:

```env
SECRET_KEY=sua_chave_secreta_super_segura
```

### 6\. Inicializar o Banco de Dados

O projeto inclui um script para criar as tabelas e popular com dados de teste.

```bash
python init_db.py
```

*Isso criará o arquivo `repensei.db` com usuários padrão (veja a seção abaixo).*

### 7\. Configurar Chaves da API Google Gemini

O projeto possui um gerenciador inteligente de chaves. Para configurá-lo:

1.  Obtenha suas chaves em [Google AI Studio](https://aistudio.google.com/).
2.  Execute o script de configuração interativo:
    ```bash
    python setup_keys.py
    ```
3.  Siga as instruções no terminal para colar suas chaves. Elas serão salvas em `api_keys.json`.

### 8\. Executar o Servidor

```bash
python app.py
```

O servidor estará rodando em: `http://localhost:5000`

-----

## 🔑 Usuários de Teste

*(Gerados pelo `init_db.py`)*

| Perfil | Email | Senha |
| :--- | :--- | :--- |
| **Admin** | admin@email.com | 123 |
| **Premium** | premium@email.com | 123 |
| **Freemium** | freemium@email.com | 123 |

-----

## 📚 Documentação da API

### 🔐 Autenticação (`/auth`)

  * `POST /auth/login`: Login unificado para Alunos e Admins.
  * `POST /auth/cadastrar_usuario`: Cadastro de novos alunos (padrão Freemium).
  * `PUT /auth/editar_usuario/<id>`: Atualiza dados do perfil.
  * `DELETE /auth/excluir_usuario/<id>`: Remove conta.

### 💎 Rotas Premium (`/premium`)

*Requer plano Premium e utiliza IA.*

  * `POST /premium/quiz`: Gera quiz sobre tema específico.
  * `POST /premium/flashcard`: Gera flashcards sobre tema específico.
  * `POST /premium/resumo`: Gera resumo de estudo.
  * `POST /premium/correcao`: Corrige texto enviado pelo aluno.
  * `POST /premium/quiz/salvar_completo`: Salva quiz gerado e respostas.
  * `GET /premium/historico/<id_aluno>`: Lista histórico de atividades.

### 🆓 Rotas Freemium (`/freemium`)

*Acessa conteúdo estático dos arquivos JSON.*

  * `POST /freemium/quiz`: Retorna perguntas aleatórias do banco fixo.
  * `POST /freemium/flashcard`: Retorna flashcards aleatórios do banco fixo.

### ⚙️ Admin (`/admin`)

  * `GET /admin/stats`: Estatísticas gerais para dashboard.
  * `GET /admin/alunos`: Lista todos os alunos.
  * `POST /admin/alunos`: Cria aluno manualmente.

-----

## 🧠 Gerenciador de Chaves (API Key Manager)

Um dos diferenciais deste backend é o `api_key_manager.py`. Ele implementa um sistema de **Rotação de Chaves (Round-Robin)** com tratamento de erros.

**Como funciona:** Se uma chave da API do Google atingir o limite de requisições (*Rate Limit 429*), o sistema automaticamente captura o erro, bloqueia a chave temporariamente e tenta a requisição novamente com a próxima chave disponível na lista, garantindo alta disponibilidade para os usuários Premium.

-----

## 📄 Estrutura do Projeto

```text
TCC_Backend/
├── app.py              # Ponto de entrada da aplicação (SocketIO + Flask)
├── config.py           # Configuração de conexão com banco de dados
├── init_db.py          # Script de inicialização do SQLite
├── setup_keys.py       # Script CLI para adicionar chaves API
├── api_key_manager.py  # Lógica de rotação de chaves Gemini
├── utils.py            # Funções auxiliares
├── requirements.txt    # Dependências
├── banco.sql           # Referência SQL
├── flashcards.json     # Dados estáticos para Freemium
├── questions.json      # Dados estáticos para Freemium
└── *_routes.py         # Blueprints das rotas (Controllers)
```

-----

