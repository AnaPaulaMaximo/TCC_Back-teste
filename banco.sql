DROP DATABASE IF EXISTS repensei;
CREATE DATABASE repensei;
USE repensei;
CREATE TABLE aluno(
    id_aluno INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    plano  ENUM('freemium', 'premium') NOT NULL,
    url_foto VARCHAR(255)
);

CREATE TABLE quiz_resultado(
    id_resultado INT AUTO_INCREMENT PRIMARY KEY,
    tema VARCHAR(255) NOT NULL,
    acertos INT NOT NULL,
    total_perguntas INT NOT NULL,
    data_criacao DATE NOT NULL
);

INSERT INTO aluno VALUES
(NULL, 'teste', 'teste@email.com', '123', 'premium', NULL),
(NULL, 'teste2', 'teste2@email.com', '123', 'freemium', NULL);