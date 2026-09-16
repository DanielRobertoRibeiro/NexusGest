# NexusGest — guia rápido

## Usar novamente neste computador

1. Abra **`iniciar.cmd`** na raiz do projeto.
2. O navegador abrirá em **http://127.0.0.1:5000**. Entre com sua conta NexusGest.
3. Mantenha a janela aberta. Ao terminar, pressione `Ctrl+C` nela.

**Sem Live Server, Workbench, ativação de ambiente ou dois terminais.** O
iniciador serve frontend e API juntos. Não recrie banco, usuários SQL ou `.env`.
Na primeira abertura desta versão, use o link privado de setup exibido pelo
iniciador para escolher nome, e-mail e senha do primeiro administrador.

Se MySQL estiver parado, execute no PowerShell como administrador:

```powershell
Start-Service MySQL80
```

## Instalar em outro computador — apenas uma vez

1. Instale **Python 3.12+**, **Node.js 22.12+** e **MySQL Server 8**.
   Eles executam a API, compilam React e armazenam dados, respectivamente.
2. No cliente MySQL, autenticado como administrador, crie banco e usuário:

```sql
CREATE DATABASE IF NOT EXISTS erp_pai CHARACTER SET utf8mb4;
CREATE USER 'erpweb_app'@'localhost' IDENTIFIED BY 'SUBSTITUA_POR_SUA_SENHA_SQL';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON erp_pai.* TO 'erpweb_app'@'localhost';
```

Escolha uma senha real no lugar do exemplo. Não execute `CREATE USER` se já
existir. As permissões de esquema permitem migrações locais. Não importe
novamente os exemplos de `banco.sql`.

3. Copie `Backend/.env.example` para `Backend/.env` **somente se ainda não
   existir**. Edite apenas `.env`, com a mesma senha configurada no MySQL:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=erpweb_app
DB_PASSWORD="SUBSTITUA_PELA_MESMA_SENHA_SQL"
DB_NAME=erp_pai
APP_ENV=development
ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

4. Abra **`preparar.cmd`**. Instala dependências em `.runtime`, compila React e
   cria somente tabelas/migrações faltantes, preservando os cadastros.
5. Abra **`iniciar.cmd`** e crie seu administrador. A senha NexusGest tem de
   12 a 128 caracteres; **não é a senha do usuário MySQL**.

## Usar e administrar

- **Clientes / Produtos:** pesquisar, cadastrar e editar; só administrador exclui.
- **Relatórios:** baixar PDF, DOCX ou CSV do banco atual.
- **Equipe e acessos:** administrador cria usuários de operação ou consulta.
- **Minha conta:** trocar senha NexusGest; sessões antigas são revogadas.

Esqueceu a senha NexusGest? Na raiz, um administrador local pode redefini-la:

```powershell
.\.runtime\Scripts\python.exe Backend/manage.py reset-password --email seu@email.com
```

## Problemas comuns

| Mensagem | Ação |
| --- | --- |
| Porta 5000 ocupada | Encerre a API antiga com Ctrl+C; use só um iniciador. |
| Access denied / 1045 | Confira a senha SQL no `.env`; mudar o arquivo não altera o MySQL. |
| Banco indisponível | Confira serviço MySQL80, DB_HOST, DB_PORT e DB_NAME. |
| Falta biblioteca ou build | Rode `preparar.cmd` novamente. |
| Sem permissão para criar tabelas | Conceda as permissões de migração do passo 2. |

Após alterar `.env`, reinicie o iniciador. Publicação sem depender do PC:
**[DEPLOY.md](./DEPLOY.md)**. Nunca envie `.env` ao GitHub.
