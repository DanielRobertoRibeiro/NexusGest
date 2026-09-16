# NexusGest

ERP educacional full stack com React/Vite, Flask e MySQL 8. Evolução do projeto
ERP Web / VINILAK para organizar clientes, produtos e indicadores.

**Versão 1.0 implementada e validada localmente.** Autenticação, perfis,
relatórios no backend e migração React entregues. Frontend e API publicados
na Vercel; a operação pública com dados depende de MySQL online, a configurar com o
proprietário. Não é um ERP fiscal/contábil certificado.

**[Acessar NexusGest](https://nexusgest-two.vercel.app)** — enquanto o banco
online não estiver configurado, a página exibe um aviso de preparação.

## Funcionalidades

- Dashboard real, estoque por categoria e alertas de estoque baixo.
- Clientes e produtos: CRUD, pesquisa, paginação e validação.
- Relatórios de clientes, produtos e resumo financeiro em PDF, DOCX e CSV.
- Login, senhas com hash, sessões revogáveis, CSRF e limite de tentativas.
- Administração de usuários com autorização no servidor.
- Interface React responsiva, formulários acessíveis e tratamento de erros.
- Migrações aditivas que preservam registros existentes.
- Iniciador Windows, configuração Vercel e Dockerfile alternativo.

| Perfil | Consultar/exportar | Cadastrar/editar | Excluir | Gerenciar equipe |
| --- | --- | --- | --- | --- |
| Administrador | Sim | Sim | Sim | Sim |
| Operador | Sim | Sim | Não | Não |
| Consulta | Sim | Não | Não | Não |

Faturamento é o valor **informado nos cadastros**, não cálculo de vendas ou lucro.
Compras, pedidos, movimentações de estoque, NF-e, multiempresa e auditoria de
negócio não fazem parte desta versão.

## Executar

No computador configurado, abra **`iniciar.cmd`**. O navegador abre sozinho
em `http://127.0.0.1:5000`. Não use Live Server nem dois servidores.
Na primeira abertura, cadastre seu administrador pelo link local apresentado.

**[Guia curto de execução](./guia.md)** · **[Publicação e banco online](./DEPLOY.md)**

Em outro computador: instale Python 3.12+, Node.js 22.12+ e MySQL 8,
configure `Backend/.env` conforme o guia e execute `preparar.cmd` uma vez.

## Organização

```text
Frontend/src/          React: telas, comunicação com API e estilos
Backend/api.py         CRUD e entrega da interface compilada
Backend/security.py    Autenticação, sessões, CSRF e perfis
Backend/reports.py     Geração de PDF, DOCX e CSV
Backend/manage.py      Migrações e recuperação administrativa
Backend/migrations/   Esquema de usuários e sessões
Backend/test_*.py      Testes unitários e de integração
api/index.py          Entrada WSGI para Vercel
vercel.json           Build, funções Python e rotas
iniciar.cmd           Execução diária no Windows
preparar.cmd          Instalação e build local
```

Fluxo: navegador → API Flask autenticada → MySQL. A senha SQL nunca vai ao
navegador. `Backend/main.py` preserva o programa de terminal original, uma
ferramenta local legada fora da autenticação web.

## Desenvolvimento e testes

Validação da versão: 20 testes passaram localmente e no GitHub Actions, com
MySQL 8 isolado no CI. Build React aprovado; telas de clientes, produtos e
relatórios conferidas no navegador, incluindo layout móvel de relatórios.

```powershell
.\.runtime\Scripts\python.exe -m unittest discover -s Backend -p 'test_*.py' -v
npm.cmd run build --prefix Frontend
```

Integração: prefira um banco de testes separado já migrado. Os testes criam
registros identificados aleatoriamente e removem somente seus próprios IDs:

```powershell
$env:RUN_INTEGRATION='1'
.\.runtime\Scripts\python.exe -m unittest discover -s Backend -p 'test_*.py' -v
Remove-Item Env:RUN_INTEGRATION
```

Para hot reload: `npm.cmd run dev --prefix Frontend` e, em outro terminal,
`.\.runtime\Scripts\python.exe Backend/api.py`. Acesse `http://127.0.0.1:5173`;
configure `ALLOWED_ORIGINS` conforme `.env.example`. No uso diário basta o iniciador.

## API

- Público: `GET /api/health`, `GET /api/auth/status`.
- Autenticação: `POST /api/auth/setup`, `/api/auth/login`, `/api/auth/logout`,
  `/api/auth/password`; `GET /api/auth/me`. Setup exige chave privada.
- Cadastros: `GET/POST /api/clientes`, `/api/produtos`;
  `PUT/DELETE /api/clientes/<id>`, `/api/produtos/<id>`.
- Equipe: `GET/POST /api/users`, `PUT /api/users/<id>` (administrador).
- Relatórios: `GET /api/reports/<clientes|produtos|financeiro>.<pdf|docx|csv>`.

Rotas privadas exigem cookie de sessão; escritas também exigem `X-CSRF-Token`.
Sem credenciais não há acesso aos cadastros ou relatórios.

## Operação e limites

Nunca publique `.env`, `.setup-token`, backups ou senhas. Em produção use HTTPS,
`APP_ENV=production`, banco com TLS, usuário SQL restrito e backups restauráveis.
Migrações exigem criação de tabelas; prefira uma credencial separada para elas.

Testes locais não substituem revisão de segurança, monitoramento, testes de
carga ou validação fiscal. Docker é uma opção de empacotamento ainda não
executada neste computador. Consulte [DEPLOY.md](./DEPLOY.md) para os requisitos.
