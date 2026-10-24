# Operação local, segurança e fluxo de jogos

## Preparar o Docker no computador local

O sandbox usado na revisão não tem Docker instalado. O Dockerfile e o Compose do projeto foram preparados para a instalação local descrita abaixo, mas o build precisa ser executado no computador em que Docker está disponível.

No Windows, instale o [Docker Desktop para Windows][1] e escolha o backend WSL 2 recomendado. O guia oficial lista os requisitos atuais de Windows, WSL 2 e virtualização. No macOS, instale o [Docker Desktop para Mac][2], escolhendo o pacote para Apple silicon ou Intel conforme o processador. Docker Desktop já inclui Docker Engine, CLI e Compose; no Linux, use o [Docker Engine e o plugin Compose][3] correspondentes à distribuição. A documentação oficial recomenda Docker Desktop para obter Compose nos sistemas compatíveis [4].

Depois de instalar, inicie Docker Desktop (Windows/macOS) ou confirme que o serviço está rodando (Linux). Abra Terminal, PowerShell ou o terminal WSL e verifique:

```bash
docker version
docker compose version
docker run --rm hello-world
```

Se os três comandos terminarem sem erro, clone o repositório e vá para a pasta do projeto:

```bash
git clone https://github.com/kukukukla/LottoIA-.git
cd LottoIA-
```

Crie o arquivo local de configuração. Ele está ignorado pelo Git e não deve ser enviado ao repositório:

```bash
# macOS/Linux/WSL
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'

# Windows PowerShell
Copy-Item .env.example .env
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie o segredo aleatório exibido para `SESSION_SECRET` no `.env`. Preencha também `ADMIN_USERNAME` e uma senha forte em `ADMIN_PASSWORD`. Mantenha `APP_PORT=5000` e `SESSION_HTTPS_ONLY=false` para uso somente local. Não reutilize o segredo mostrado em exemplos nem deixe os valores vazios. Se a senha contiver `$`, use aspas simples no arquivo `.env` para evitar expansão de variáveis pelo Compose.

Valide a configuração e construa/inicie o serviço:

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f app
```

Acesse `http://localhost:5000`, autentique-se com as credenciais definidas e use o painel. A porta está vinculada a `127.0.0.1` por padrão para não expor acidentalmente a aplicação à rede. Para parar sem apagar jogos/cache, use `docker compose down`; **não** use `docker compose down -v` salvo se quiser apagar o volume persistente. Para atualizar a imagem mantendo os dados, execute `git pull` e depois `docker compose up --build -d`.

O Dockerfile instala apenas as dependências necessárias ao serviço web (`requirements-docker.txt`). O `.dockerignore` exclui `.env`, banco, cache, Git e arquivos de teste do contexto de build. O diretório de dados do contêiner fica no volume Docker nomeado `lottoia_data`. Ele contém o banco SQLite dos lotes e a cache CAIXA. O serviço roda com usuário Linux sem privilégios administrativos. Para backup, pare o serviço e copie o banco para um local protegido:

```bash
docker compose stop app
docker cp lottoia-app:/app/data/lottoia.sqlite3 ./lottoia-backup.sqlite3
docker compose start app
```

Esse arquivo contém o histórico pessoal de combinações geradas; proteja o backup. O volume continua no computador após `docker compose down`, mas não acompanha o projeto caso você troque de máquina. Copie o backup e restaure-o em volume configurado antes de iniciar uma instalação nova.

## Login e segurança da aplicação

O login atual usa um único administrador configurado no `.env`; não há cadastro público, recuperação automática de senha, perfis múltiplos ou identidade por jogador. O backend compara credenciais sem comparação textual ingênua. Depois do login, cria uma sessão assinada com duração de 12 horas, cookie `HttpOnly`, `SameSite=Lax` e opção `Secure`. Cinco tentativas inválidas por IP bloqueiam novos logins por cinco minutos. A proteção de tentativas é mantida em memória, portanto reinicia com o processo e não coordena múltiplos contêineres.

A gravação de lotes exige sessão e token CSRF. Consultas, exports e comparações verificam que o lote pertence ao usuário autenticado; a API responde como não encontrado para lotes alheios. Não exponha o container diretamente na Internet. Se publicar remotamente, coloque um proxy TLS à frente, restrinja a porta com firewall, defina `SESSION_HTTPS_ONLY=true`, mantenha os segredos fora do Git e planeje backup/atualização. Ativar o cookie `Secure` sem HTTPS impedirá o login de funcionar corretamente por HTTP.

O banco local é SQLite, adequado para uma instância pequena. Para várias réplicas/usuários concorrentes, mova persistência, sessões e limitação de tentativas para serviços compartilhados e valide a arquitetura de migração antes de escalar.

## Gerar, salvar, consultar e comparar jogos

Na seção **Gerar jogos**, escolha modalidade, método, quantidade de dezenas, quantidade de combinações e um nome para o lote. O botão gera e salva até 50 jogos por lote. Cada registro conserva nome, modalidade, método, números, quantidade, fonte, data/hora e número do concurso CAIXA usado como referência. Os registros são guardados em SQLite e reaparecem no **Histórico de jogos salvos** após reiniciar o container.

Use **Baixar TXT** para baixar um arquivo de texto com os dados do lote. A tela **Comparar** consulta a CAIXA e cruza cada jogo com até 100 concursos recentes (30 por padrão). O relatório mostra o número/data de cada concurso, marca o mais recente disponível e informa quantidade e valores das dezenas coincidentes por jogo. A métrica é apenas retrospectiva, como um espelho de coincidências; não representa prêmio, retorno financeiro ou probabilidade futura. Se a CAIXA estiver fora do ar, o sistema indica cache válido/desatualizado quando existir e não inventa um resultado. Sem cache, a comparação falha de modo explícito.

A geração por `score`, frequência ou atraso usa métricas históricas. O método aleatório é aleatório; carregar histórico para uma chamada não faz esse método prever sorteios. Sorteios são independentes, e nenhum resultado do histórico aumenta a chance matemática do próximo concurso.

## Aplicação web ou app

Este repositório entrega uma aplicação web FastAPI com HTML, CSS e JavaScript, acessível pelo navegador e pronta para rodar localmente no Docker. O dashboard pode ser aberto no navegador de computador ou telefone quando servido por uma origem acessível. Não há aplicativo Android/iOS nativo, manifesto PWA ou modo offline implementados aqui. Para disponibilizar a outra máquina/dispositivo, use hospedagem com HTTPS e autenticação adequadas, não uma porta pública HTTP improvisada. Um aplicativo nativo exigiria uma camada cliente própria e estratégia de autenticação/API apropriada; não é produzido automaticamente pelo Docker deste projeto.

## Verificação de lógica e execução

A suíte atual cobre motores, regressões, validação de respostas CAIXA simuladas, cache/fallback, autenticação, token CSRF, persistência SQLite entre inicializações, isolamento do proprietário, TXT e comparação com concursos de teste. Os testes não fazem chamadas de rede à CAIXA. Execute localmente:

```bash
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
node --check static/js/dashboard.js
```

O teste `docker run hello-world` verifica a instalação do Docker; `docker compose config --quiet` valida a sintaxe e variáveis do Compose. Só `docker compose up --build` valida o build real deste projeto na máquina local.

## Referências oficiais

[1]: https://docs.docker.com/desktop/setup/install/windows-install/ "Instalação Docker Desktop no Windows"
[2]: https://docs.docker.com/desktop/setup/install/mac-install/ "Instalação Docker Desktop no macOS"
[3]: https://docs.docker.com/engine/install/ubuntu/ "Instalação Docker Engine e Compose em Ubuntu"
[4]: https://docs.docker.com/compose/install/ "Visão geral da instalação Docker Compose"
