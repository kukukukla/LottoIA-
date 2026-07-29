# 📦 Guia de Instalação Rápida

## Opção 1: Instalação Direta (recomendado para uso local)

```bash
# 1. Entre na pasta do projeto
cd loterias_inteligencia

# 2. Crie ambiente virtual
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instale dependências
pip install -r requirements.txt

# 4. Execute a demonstração
python scripts/demo.py

# Ou use o run.py:
python run.py demo
```

## Opção 2: Instalação como Pacote Python

```bash
# Instale o pacote
pip install -e .

# Execute via console
loterias-demo
```

## Opção 3: Docker (recomendado para produção)

```bash
# Construa a imagem
docker build -t loterias-inteligencia .

# Execute
docker run -v $(pwd)/data:/app/data loterias-inteligencia python scripts/demo.py
```

## Verificação

Após instalação, execute os testes:

```bash
pytest tests/ -v
```

## Uso Básico

```python
from core import MotorPrincipal, Concurso, LoteriaTipo

# Carregar seus dados
concursos = [...]  # lista de Concurso
motor = MotorPrincipal(concursos)

# Gerar jogos
jogos = motor.gerar_jogos("score", 15, 5)

# Analisar
analise = motor.analise_completa()
```
