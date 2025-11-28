Este repositório contém o código-fonte do Backend da aplicação **Repensei**, um projeto de TCC focado no ensino de Filosofia e Sociologia. A aplicação utiliza inteligência artificial para gerar conteúdo personalizado e opera sob um modelo de negócios Freemium.

O sistema é construído em Python com Flask e integra-se à API do Google Gemini para geração de conteúdo dinâmico.

## 📋 Funcionalidades

O sistema divide-se em três níveis de acesso principais:

### 1. Aluno Freemium (Gratuito)

* **Acesso a conteúdo estático:** Banco de questões e flashcards pré-definidos (curadoria).
* **Foco:** Conteúdo para revisão geral de Filosofia e Sociologia.

### 2. Aluno Premium (Pago)

* **Geração de Conteúdo via IA:** Criação de Quizzes, Flashcards e Resumos inéditos sobre qualquer tema solicitado.
* **Correção de Redação:** Envio de textos para análise e feedback detalhado da IA.
* **Histórico de Atividades:** Salvamento automático de todo conteúdo gerado e resultados de quizzes.
* **Chatbot Tutor:** Assistente virtual em tempo real para debates filosóficos.

### 3. Administrador

* **Dashboard:** Visualização de estatísticas (total de alunos, distribuição por plano, médias de acertos).
* **Gestão de Usuários:** CRUD completo de alunos.
* **Monitoramento:** Acompanhamento do uso da plataforma.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.x
* **Framework Web:** Flask
* **Banco de Dados:** SQLite (repensei.db)
* **IA Generativa:** Google Gemini (Modelo `gemini-2.5-flash`)
* **Real-time:** Flask-SocketIO (para o Chatbot)
* **Gerenciamento de Chaves:** Sistema proprietário de rotação de chaves API (api_key_manager.py) para contornar limites de quota.

---

## 🚀 Instalação e Configuração

Siga os passos abaixo para rodar o projeto localmente.

### 1. Pré-requisitos

* Python 3.8 ou superior instalado.
* Git instalado.
* Chaves da API Google Gemini.

### 2. Clonar o Repositório

````bash
git clone <url-do-seu-repositorio>
cd TCC_Backend
````

### 3. Criar e Ativar Ambiente Virtual

Recomendado para isolar as dependências do projeto.

**Windows:**
````bash
python -m venv venv
.\venv\Scripts\activate
````

**Linux/Mac:**
````bash
python3 -m venv venv
source venv/bin/activate
````

### 4. Instalar Dependências

````bash
pip install -r requirements.txt
````

### 5. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

````env
SECRET_KEY=sua_chave_secreta_super_segura
GEMINI_API_KEY=sua_chave_do_google_gemini
````

### 6. Inicializar o Banco de Dados

````bash
python init_db.py
````

*Isso criará o arquivo repensei.db com usuários padrão.*

### 7. Configurar Chaves da API Google Gemini

1. Obtenha suas chaves em [Google AI Studio](https://aistudio.google.com/).
2. Execute o script de configuração:
   ````bash
   python setup_keys.py
   ````
3. Siga as instruções para salvar as chaves em `api_keys.json`.

### 8. Executar o Servidor

````bash
python app.py
````

O servidor estará rodando em: `http://localhost:5000`

---

## 🔑 Usuários de Teste

| Perfil | Email | Senha |
| :--- | :--- | :--- |
| **Admin** | admin@email.com | 123 |
| **Premium** | premium@email.com | 123 |
| **Freemium** | freemium@email.com | 123 |

---

## 📚 Documentação da API

### 🔐 Autenticação (`/auth`)

* `POST /auth/login` - Login unificado para Alunos e Admins.
* `POST /auth/cadastrar_usuario` - Cadastro de novos alunos.
* `PUT /auth/editar_usuario/<id>` - Atualiza dados do perfil.
* `DELETE /auth/excluir_usuario/<id>` - Remove conta.

### 💎 Rotas Premium (`/premium`)

* `POST /premium/quiz` - Gera quiz via IA.
* `POST /premium/flashcard` - Gera flashcards via IA.
* `POST /premium/resumo` - Gera resumo de estudo.
* `POST /premium/correcao` - Corrige texto enviado.
* `POST /premium/quiz/salvar_completo` - Salva quiz e respostas.
* `GET /premium/historico/<id_aluno>` - Lista histórico de atividades.

### 🆓 Rotas Freemium (`/freemium`)

* `POST /freemium/quiz` - Retorna perguntas aleatórias.
* `POST /freemium/flashcard` - Retorna flashcards aleatórios.

### ⚙️ Admin (`/admin`)

* `GET /admin/stats` - Estatísticas do dashboard.
* `GET /admin/alunos` - Lista todos os alunos.
* `POST /admin/alunos` - Cria aluno manualmente.

---

## 🧠 Gerenciador de Chaves (API Key Manager)

O api_key_manager.py implementa um sistema de **Rotação de Chaves (Round-Robin)**. Se uma chave atingir o limite de requisições (429 Rate Limit), o sistema automaticamente bloqueia a chave e tenta novamente com a próxima chave disponível, garantindo alta disponibilidade.

---

## 📁 Estrutura do Projeto

````text
TCC_Backend/
├── app.py                   # Ponto de entrada da aplicação
├── config.py                # Configuração do banco de dados
├── init_db.py               # Script de inicialização
├── setup_keys.py            # Script para configurar chaves API
├── api_key_manager.py       # Lógica de rotação de chaves
├── utils.py                 # Funções auxiliares
├── requirements.txt         # Dependências do projeto
├── banco.sql                # Referência SQL
├── flashcards.json          # Dados estáticos (Freemium)
├── questions.json           # Dados estáticos (Freemium)
├── auth_routes.py           # Rotas de autenticação
├── premium_routes.py        # Rotas Premium
├── freemium_routes.py       # Rotas Freemium
├── admin_routes.py          # Rotas Administrativas
├── .env.example             # Exemplo de variáveis de ambiente
└── README.md                # Este arquivo
````

---

## 🔗 Projeto Frontend

O frontend desta aplicação pode ser encontrado em:

**[🌐 Link do Repositório Frontend](https://github.com/AnaPaulaMaximo/TCC_frontend.git)**

*Substitua o link acima pelo endereço do repositório do frontend do Repensei.*

---

## 📝 Licença

Este projeto está sob a licença **MIT**. Consulte o arquivo [LICENSE](./LICENSE) para mais detalhes.

---

## 👥 Contribuidores

* **Desenvolvedores:** 
  - [Ana Paula Máximo](https://github.com/AnaPaulaMaximo)
  - [Luis Gustavo](https://github.com/Luisglm7)
  - [Pedro Henrique](https://github.com/Pedrao345)
  - [Thimótio Araujo](https://github.com/Thimo08)
* **Orientadores:** João Paulo e Rafael Ribas

