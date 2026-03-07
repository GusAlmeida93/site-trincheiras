const { Router } = require('express');
const pool = require('./db');

const router = Router();

// POST /api/jogadores — create a new player
router.post('/jogadores', async (req, res) => {
    const { nome, turma, numero_recruta } = req.body;

    if (!nome || !turma) {
        return res.status(400).json({ error: 'nome and turma are required.' });
    }

    try {
        const { rows } = await pool.query(
            'INSERT INTO jogadores (nome, turma, numero_recruta) VALUES ($1, $2, $3) RETURNING id',
            [nome, turma, numero_recruta || null]
        );
        return res.status(201).json(rows[0]);
    } catch (err) {
        console.error('Error inserting jogador:', err);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

// POST /api/respostas — record an answer
router.post('/respostas', async (req, res) => {
    const { jogador_id, modulo, pergunta_id, resposta_escolhida, correto, variacao_pontos } = req.body;

    if (!modulo || !pergunta_id || resposta_escolhida === undefined || correto === undefined) {
        return res.status(400).json({ error: 'modulo, pergunta_id, resposta_escolhida, and correto are required.' });
    }

    try {
        const { rows } = await pool.query(
            `INSERT INTO respostas (jogador_id, modulo, pergunta_id, resposta_escolhida, correto, variacao_pontos)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING id`,
            [jogador_id || null, modulo, pergunta_id, resposta_escolhida, correto, variacao_pontos || 0]
        );
        return res.status(201).json(rows[0]);
    } catch (err) {
        console.error('Error inserting resposta:', err);
        return res.status(500).json({ error: 'Internal server error.' });
    }
});

module.exports = router;
