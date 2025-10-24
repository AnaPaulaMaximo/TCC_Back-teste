CREATE DATABASE edutech;

use edutech;
-- Tabela Aluno
CREATE TABLE Aluno (
    id_aluno SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    url_foto VARCHAR(255) -- Adicionado campo para a URL da foto
);

-- Tabela Curso
CREATE TABLE Curso (
    id_curso SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    carga_horaria INT,
    tipo VARCHAR(50) DEFAULT 'regular'
);

-- Tabela Materia
CREATE TABLE Materia (
    id_materia SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL
);

-- Tabela CursoMateria (relacionamento N:N)
CREATE TABLE CursoMateria (
    id_curso INT,
    id_materia INT,
    PRIMARY KEY (id_curso, id_materia),
    FOREIGN KEY (id_curso) REFERENCES Curso(id_curso),
    FOREIGN KEY (id_materia) REFERENCES Materia(id_materia)
);

-- Tabela Conteudo (ligado à Matéria)
CREATE TABLE Conteudo (
    id_conteudo SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, -- Ex: video, texto, quiz
    url_arquivo VARCHAR(255),
    titulo VARCHAR(100),
    id_materia INT,
    FOREIGN KEY (id_materia) REFERENCES Materia(id_materia)
);

-- Tabela Matricula
CREATE TABLE Matricula (
    id_matricula SERIAL PRIMARY KEY,
    id_aluno INT,
    id_curso INT,
    data_matricula DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_curso) REFERENCES Curso(id_curso)
);

-- Tabela Progresso
CREATE TABLE Progresso (
    id_progresso SERIAL PRIMARY KEY,
    id_aluno INT,
    id_curso INT,
    percentual DECIMAL(5,2),
    ultima_data DATE,
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_curso) REFERENCES Curso(id_curso)
);

-- Tabela Certificado
CREATE TABLE Certificado (
    id_certificado SERIAL PRIMARY KEY,
    id_aluno INT,
    id_curso INT,
    data_emissao DATE,
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_curso) REFERENCES Curso(id_curso)
);

-- Tabela Questionario (um por curso)
CREATE TABLE Questionario (
    id_questionario SERIAL PRIMARY KEY,
    titulo VARCHAR(100),
    id_curso INT,
    FOREIGN KEY (id_curso) REFERENCES Curso(id_curso)
);

-- Tabela Pergunta (agora ligada apenas ao questionário)
CREATE TABLE Pergunta (
    id_pergunta SERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- 'objetiva', 'dissertativa'
    id_questionario INT,
    FOREIGN KEY (id_questionario) REFERENCES Questionario(id_questionario)
);

-- Tabela Alternativa
CREATE TABLE Alternativa (
    id_alternativa SERIAL PRIMARY KEY,
    texto VARCHAR(255) NOT NULL,
    correta BOOLEAN DEFAULT FALSE,
    id_pergunta INT,
    FOREIGN KEY (id_pergunta) REFERENCES Pergunta(id_pergunta)
);

-- Tabela RespostaAluno
CREATE TABLE RespostaAluno (
    id_resposta SERIAL PRIMARY KEY,
    id_aluno INT,
    id_pergunta INT,
    resposta_texto TEXT,
    id_alternativa INT, -- se for objetiva
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_pergunta) REFERENCES Pergunta(id_pergunta),
    FOREIGN KEY (id_alternativa) REFERENCES Alternativa(id_alternativa)
);

