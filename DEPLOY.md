# Publicação do NexusGest

Frontend e API publicados em **https://nexusgest-two.vercel.app**.
Repositório conectado: `DanielRobertoRibeiro/NexusGest`, branch `main`.
Alterações nessa branch disparam um novo deploy automaticamente.
O endpoint `/api/health` deve responder HTTP 200 com o banco conectado.

## Vercel: interface e API no mesmo endereço

Importe o repositório com raiz `./` e preset **Other**. `vercel.json` instala
e compila React; `api/index.py` expõe Flask em funções Python 3.12.
Não selecione apenas Frontend, pois isso deixaria a API fora da publicação.

Sem `DB_PASSWORD`, a página informa que aguarda banco. Isso **não é operação
full stack concluída**. `/api/auth/status` retorna `databaseConfigured: false`.

## Banco online: TiDB Cloud Starter (compatível com MySQL)

1. Crie uma instância TiDB Cloud Starter em modo **MySQL Compatible**, com
   limite mensal de gastos de US$ 0. Use a região mais próxima da função da
   Vercel. O banco local não é acessível pela Vercel; não exponha a porta 3306
   doméstica.
2. Crie um database vazio para o NexusGest. No painel **Connect**, escolha
   **Public Endpoint** e anote host, porta, nome de usuário e database.
   Gere a senha e guarde-a em um gerenciador de senhas. Baixe o certificado
   público ISRG Root X1 indicado pelo TiDB para verificar a conexão TLS.
3. Para uma implantação com permissões mínimas, crie credenciais separadas
   para migração e execução. Migração exige `CREATE`, `ALTER`, `INDEX`,
   `REFERENCES` e operações de dados; execução exige `SELECT`, `INSERT`,
   `UPDATE`, `DELETE` nas tabelas do ERP.
4. Num terminal seguro, defina variáveis do banco remoto e execute:

```powershell
$env:APP_ENV='production'
# Defina DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME e DB_SSL_CA.
# DB_SSL_CA deve apontar para o certificado público ISRG Root X1 baixado.
.\.runtime\Scripts\python.exe Backend/manage.py migrate
```

Variáveis do terminal prevalecem sobre `.env`; feche o terminal ao terminar. A migração cria
esquema vazio, sem copiar os cadastros locais. Transferir dados exige backup,
exportação e importação planejados separadamente.

5. Em Vercel → Settings → Environment Variables configure:

| Variável | Valor |
| --- | --- |
| APP_ENV | production |
| DB_HOST / DB_PORT | Endpoint e porta do provedor |
| DB_NAME | Banco criado |
| DB_USER / DB_PASSWORD | Credencial do banco; prefira um usuário com permissões mínimas |
| DB_SSL_CA_PEM | Conteúdo do certificado público ISRG Root X1 indicado pelo TiDB |
| SETUP_TOKEN | Segredo temporário aleatório de pelo menos 32 caracteres para o primeiro administrador |
| ALLOWED_ORIGINS | URL HTTPS pública exata do NexusGest |

O certificado CA é público; nunca inclua sua chave privada. Com DB_SSL_CA_PEM,
o conector verifica certificado e identidade do host. Remova variáveis antigas
que apontem para a Aiven. Funções abrem conexões curtas e precisam de
concorrência suficiente.

6. Faça **Redeploy** para aplicar variáveis. Confira `/api/health` online.
7. Abra `https://SEU-DOMINIO/#setup=SEU_TOKEN` privadamente e cadastre o
   administrador. A interface remove o fragmento após lê-lo. Não compartilhe
   esse link. Remova SETUP_TOKEN da Vercel depois e faça outro redeploy.
8. Teste login, perfis, CRUD e nove downloads. Configure backups, monitoramento
   e limites de uso. Só então declare a operação online concluída.

Não use banco de produção em Preview; use credenciais separadas. Nunca use
prefixo `VITE_` em segredos: esses valores seriam enviados ao navegador.

## Docker alternativo

O Dockerfile compila React e executa Flask com Gunicorn, aplicando migrações
aditivas na inicialização. Forneça variáveis fora da imagem. Precisa de teste
no host escolhido; não foi executado neste Windows por ausência do Docker.
