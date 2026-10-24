# Fontes de resultados oficiais

Consulta direta realizada em 23 de outubro de 2026 por `CaixaLoteriasClient`, via HTTPS ao endpoint no domínio `servicebus2.caixa.gov.br` da CAIXA. A busca de concurso mais recente retornou os seguintes resultados:

| Modalidade | Concurso | Data de apuração | Dezenas consultadas |
|---|---:|---|---|
| Lotofácil | 3811 | 22/10/2026 | 01, 03, 05, 07, 08, 09, 10, 11, 12, 15, 16, 18, 19, 23, 25 |
| Mega-Sena | 3073 | 22/10/2026 | 04, 13, 23, 28, 41, 58 |
| Lotomania | 2990 | 21/10/2026 | 04, 06, 11, 19, 25, 27, 29, 32, 35, 37, 42, 52, 63, 66, 67, 70, 76, 80, 81, 99 |

Os resultados podem ser conferidos nos recursos específicos [Lotofácil 3811][1], [Mega-Sena 3073][2] e [Lotomania 2990][3], no endpoint oficial de resultados CAIXA. O teste de geração de jogos também foi executado com os últimos cinco concursos reais da Lotofácil e o método `score`; o comando terminou com dois jogos válidos. Os valores acima são um snapshot da consulta e não substituem a consulta atualizada no uso futuro.

Em uma nova verificação em 24/10/2026, o mesmo cliente consultou os dois últimos concursos Lotofácil diretamente na CAIXA e recebeu o #3812, apurado em 23/10/2026, com dezenas 03, 04, 05, 07, 08, 11, 13, 16, 17, 19, 20, 21, 23, 24 e 25 [6]. Os resultados de Mega-Sena e Lotomania acima permanecem snapshots de 23/10; não foram reconsultados nesta verificação.

## Como o cliente encontra o resultado mais recente

O serviço de resultados não publica um contrato de API versionado, e seu índice simples pode ficar atrás de um concurso já publicado. O cliente consulta o índice por modalidade e confirma números consecutivos seguintes, até encontrar o primeiro concurso ainda indisponível. Em uma verificação anterior, o índice da Lotofácil estava no concurso 3807 enquanto o concurso 3808 já podia ser obtido por URL específica. A resposta HTTP 500 vista ao consultar um concurso futuro foi uma observação daquele momento — não é garantia de que todo erro 500 indique concurso não publicado. Esse comportamento pode mudar; o cliente valida o número retornado e mantém fallback explícito.

O JSON é validado antes de criar um objeto `Concurso`: número positivo e esperado, data reconhecida, quantidade de dezenas correta para a modalidade, sem duplicatas e dentro do universo permitido. Se a rede falhar, um cache anterior pode ser usado com metadados sobre idade e desatualização. Sem cache válido, a aplicação informa indisponibilidade e não substitui os resultados por dados sintéticos.

Os slugs da API são `lotofacil`, `megasena` e `lotomania`; o enum interno da Mega-Sena é `mega_sena` e o mapeamento fica centralizado no cliente. O cliente não depende do serviço Heroku de terceiros referido abaixo; essa referência serviu apenas como fonte secundária para estrutura comum de respostas.

## Referências

[1]: https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/3811 "Resultado CAIXA da Lotofácil 3811"
[2]: https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/3073 "Resultado CAIXA da Mega-Sena 3073"
[3]: https://servicebus2.caixa.gov.br/portaldeloterias/api/lotomania/2990 "Resultado CAIXA da Lotomania 2990"
[4]: https://loterias.caixa.gov.br/ "Portal oficial de Loterias CAIXA"
[5]: https://github.com/isaccanedo/loterias-api "Cliente de terceiros para consulta de resultados das Loterias CAIXA"
[6]: https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/3812 "Resultado CAIXA da Lotofácil 3812"
