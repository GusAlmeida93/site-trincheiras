CREATE TABLE IF NOT EXISTS jogadores (
  id SERIAL PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  turma VARCHAR(50) NOT NULL,
  numero_recruta VARCHAR(50),
  criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS respostas (
  id SERIAL PRIMARY KEY,
  jogador_id INTEGER REFERENCES jogadores(id),
  modulo VARCHAR(50) NOT NULL,
  pergunta_id VARCHAR(100) NOT NULL,
  resposta_escolhida TEXT NOT NULL,
  correto BOOLEAN NOT NULL,
  variacao_pontos INTEGER DEFAULT 0,
  criado_em TIMESTAMP DEFAULT NOW()
);
