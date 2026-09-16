# Publicação do NexusGest

Frontend e API publicados em **https://nexusgest-two.vercel.app**.
Repositório conectado: `DanielRobertoRibeiro/ERPWEB`, branch `main`.
Alterações nessa branch disparam um novo deploy automaticamente.
Verificado: página e status HTTP 200, cadastros sem login HTTP 401;
health HTTP 503 enquanto o MySQL online estiver ausente (comportamento esperado).

## Vercel: interface e API no mesmo endereço

Importe o repositório com raiz `./` e preset **Other**. `vercel.json` instala
e compila React; `api/index.py` expõe Flask em funções Python 3.12.
Não selecione apenas Frontend, pois isso deixaria a API fora da publicação.

Sem `DB_PASSWORD`, a página informa que aguarda banco. Isso **não é operação
full stack concluída**. `/api/auth/status` retorna `databaseConfigured: false`.

## Conectar MySQL online

1. Escolha um serviço MySQL 8 compatível, com TLS e backups. `localhost` do
   seu PC não é acessível pela Vercel. Não exponha a porta 3306 doméstica.
2. Crie banco e credenciais separadas para migração e execução. Migração
   exige `CREATE`, `ALTER`, `INDEX`, `REFERENCES` e operações de dados;
   execução exige `SELECT`, `INSERT`, `UPDATE`, `DELETE` nas tabelas do ERP.
3. Num terminal seguro, defina variáveis do banco remoto e execute:

```powershell
$env:APP_ENV='production'
# Defina DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_SSL_CA e SETUP_TOKEN
# com os valores do provedor. Não use as credenciais locais.
.\.runtime\Scripts\python.exe Backend/manage.py migrate
```

`SETUP_TOKEN` deve ser aleatório, com pelo menos 32 caracteres. Variáveis do
terminal prevalecem sobre `.env`; feche o terminal ao terminar. A migração cria
esquema vazio, sem copiar os cadastros locais. Transferir dados exige backup,
exportação e importação planejados separadamente.

4. Em Vercel → Settings → Environment Variables configure:

| Variável | Valor |
| --- | --- |
| APP_ENV | production |
| DB_HOST / DB_PORT | Endpoint e porta do provedor |
| DB_NAME | Banco criado |
| DB_USER / DB_PASSWORD | Credencial de execução, não root |
| DB_SSL_CA | Caminho do certificado CA público incluído no pacote |
| SETUP_TOKEN | Mesmo segredo temporário usado na migração |
| ALLOWED_ORIGINS | URL HTTPS pública exata do NexusGest |

O certificado CA é público; nunca inclua sua chave privada. Com DB_SSL_CA, o
conector verifica certificado e identidade do host. Ajuste limites de conexões
ao plano MySQL: funções abrem conexões curtas e precisam de concorrência suficiente.

5. Faça **Redeploy** para aplicar variáveis. Confira `/api/health` online.
6. Abra `https://SEU-DOMINIO/#setup=SEU_TOKEN` privadamente e cadastre o
   administrador. A interface remove o fragmento após lê-lo. Não compartilhe
   esse link. Remova SETUP_TOKEN da Vercel depois e faça outro redeploy.
7. Teste login, perfis, CRUD e nove downloads. Configure backups, monitoramento
   e limites de uso. Só então declare a operação online concluída.

Não use banco de produção em Preview; use credenciais separadas. Nunca use
prefixo `VITE_` em segredos: esses valores seriam enviados ao navegador.

## Docker alternativo

O Dockerfile compila React e executa Flask com Gunicorn, aplicando migrações
aditivas na inicialização. Forneça variáveis fora da imagem. Precisa de teste
no host escolhido; não foi executado neste Windows por ausência do Docker.
