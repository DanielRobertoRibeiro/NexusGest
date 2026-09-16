import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { LayoutDashboard, Users, Package, ChartNoAxesCombined, Settings, LogOut, Search, Plus,
  ArrowUpRight, ArrowRight, RefreshCw, Pencil, Trash2, X, Menu, Download, ShieldCheck,
  ChevronLeft, ChevronRight, Check, AlertCircle, FileText, KeyRound, Box, Layers3 } from 'lucide-react';
import { api, downloadReport, setCsrf } from './api';
import './styles.css';

const money = value => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const number = value => Number(value || 0).toLocaleString('pt-BR');
const roles = { admin: 'Administrador', operador: 'Operador', consulta: 'Consulta' };
const states = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(' ');
const pages = {
  dashboard: { title: 'Visão geral', subtitle: 'Seu negócio, conectado em um só lugar.', icon: LayoutDashboard },
  clientes: { title: 'Clientes', subtitle: 'Relacionamentos que fazem seu negócio crescer.', icon: Users },
  produtos: { title: 'Produtos', subtitle: 'Organize seu catálogo e acompanhe o estoque.', icon: Package },
  relatorios: { title: 'Relatórios', subtitle: 'Transforme seus cadastros em informação.', icon: ChartNoAxesCombined },
  usuarios: { title: 'Equipe e acessos', subtitle: 'As pessoas certas, com as permissões certas.', icon: ShieldCheck },
  conta: { title: 'Minha conta', subtitle: 'Cuide do acesso ao seu espaço de trabalho.', icon: Settings },
};
function Brand({ light = false }) {
  return <div className={`brand ${light ? 'brand-light' : ''}`}><span className="brand-symbol"><Layers3 size={23}/></span>
    <span>Nexus<span className="brand-weight">Gest</span><small>GESTÃO CONECTADA</small></span></div>;
}
function ErrorMessage({ message }) { return message ? <div className="error" role="alert"><AlertCircle size={18}/><span>{message}</span></div> : null; }
function Field({ label, children, full = false }) { return <label className={`field ${full ? 'field-full' : ''}`}><span>{label}</span>{children}</label>; }

function Login({ setup, onLogin }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [token] = useState(() => new URLSearchParams(location.hash.slice(1)).get('setup') || '');
  useEffect(() => { if (token) history.replaceState(null, '', location.pathname); }, [token]);
  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true);
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try { const result = await api(setup ? '/auth/setup' : '/auth/login', {
      method: 'POST', body: data, headers: setup ? { 'X-Setup-Token': data.token || token } : {},
    }); onLogin(result.user); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <main className="login-layout">
    <section className="login-story"><Brand light/><div><span className="eyebrow light">UM NOVO JEITO DE ORGANIZAR</span>
      <h1>Mais clareza.<br/>Mais conexão.<br/><em>Mais possibilidades.</em></h1>
      <p>Clientes, produtos e informações que trabalham juntos. Seu próximo passo começa aqui.</p>
      <div className="login-visual"><div><Users/><span>Relacionamentos</span><Check size={18}/></div><div><Package/><span>Operação organizada</span><Check size={18}/></div><div><ChartNoAxesCombined/><span>Decisões informadas</span><Check size={18}/></div></div>
    </div><small>NexusGest · Um espaço para o seu negócio evoluir.</small></section>
    <section className="login-form-wrap"><form onSubmit={submit} className="login-form">
      <span className="icon-tile"><ShieldCheck size={26}/></span><h2>{setup ? 'Seu espaço começa aqui' : 'Bom ter você de volta.'}</h2>
      <p className="muted">{setup ? 'Crie a primeira conta de administrador do NexusGest.' : 'Entre na sua conta para acompanhar sua operação.'}</p>
      <ErrorMessage message={error}/>
      {setup && <Field label="Seu nome"><input name="name" required minLength={2} maxLength={120} autoComplete="name"/></Field>}
      <Field label="E-mail"><input name="email" type="email" required maxLength={190} autoComplete="username" placeholder="voce@empresa.com"/></Field>
      <Field label="Senha"><input name="password" type="password" required minLength={setup ? 12 : 1} maxLength={128} autoComplete={setup ? 'new-password' : 'current-password'}/></Field>
      {setup && <><small className="muted">Use pelo menos 12 caracteres. Esta senha é independente do MySQL.</small>
        {!token && <Field label="Chave de configuração"><input name="token" required type="password" autoComplete="off"/><small>Use a chave de configuração exibida no servidor.</small></Field>}</>}
      <button className="button primary login-submit" disabled={busy}>{busy ? 'Aguarde…' : setup ? 'Criar meu espaço' : 'Entrar no NexusGest'}<ArrowRight size={18}/></button>
      <p className="login-note"><KeyRound size={14}/> Acesso individual e protegido por perfil.</p>
      {!setup && <small className="muted">Esqueceu sua senha? Peça a redefinição ao administrador da sua equipe.</small>}
    </form></section>
  </main>;
}
function Modal({ title, onClose, children }) {
  const ref = useRef();
  useEffect(() => { ref.current.showModal(); const el = ref.current; return () => el.close(); }, []);
  return <dialog className="modal" ref={ref} onCancel={onClose} onClick={e => { if (e.target === ref.current) onClose(); }} aria-label={title}>
    <div className="modal-head"><div><span className="eyebrow">NEXUSGEST</span><h2>{title}</h2></div><button className="icon-button" onClick={onClose} aria-label="Fechar"><X/></button></div>{children}</dialog>;
}
function EntityForm({ kind, initial, onClose, onSaved }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const client = kind === 'clientes';
  const input = (name, props = {}) => <input name={name} defaultValue={initial?.[name] ?? ''} required {...props}/>;
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); const data = Object.fromEntries(new FormData(event.currentTarget));
    for (const key of client ? ['revenue'] : ['price', 'stock']) data[key] = Number(data[key]);
    try { await api(`/${kind}${initial ? `/${initial.id}` : ''}`, { method: initial ? 'PUT' : 'POST', body: data }); onSaved(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <Modal title={`${initial ? 'Editar' : 'Novo'} ${client ? 'cliente' : 'produto'}`} onClose={onClose}>
    <form onSubmit={submit}><ErrorMessage message={error}/><div className="form-grid">{client ? <>
      <Field label="Razão social" full>{input('company', { maxLength: 150, autoFocus: true })}</Field>
      <Field label="Nome fantasia">{input('name', { maxLength: 150 })}</Field>
      <Field label="CNPJ">{input('cnpj', { maxLength: 18, inputMode: 'numeric', placeholder: '00.000.000/0000-00' })}</Field>
      <Field label="Estado"><select name="state" defaultValue={initial?.state || 'SP'}>{states.map(s => <option key={s}>{s}</option>)}</select></Field>
      <Field label="Status"><select name="status" defaultValue={initial?.status || 'Ativo'}><option>Ativo</option><option>Inativo</option></select></Field>
      <Field label="Faturamento informado (R$)">{input('revenue', { type: 'number', min: 0, max: 99999999.99, step: '.01', defaultValue: initial?.revenue ?? 0 })}</Field>
    </> : <>
      <Field label="Nome do produto" full>{input('name', { maxLength: 150, autoFocus: true })}</Field>
      <Field label="Categoria">{input('category', { maxLength: 100 })}</Field><Field label="Marca">{input('brand', { maxLength: 100 })}</Field>
      <Field label="Estoque (unidades)">{input('stock', { type: 'number', min: 0, max: 2147483647, step: 1, defaultValue: initial?.stock ?? 0 })}</Field>
      <Field label="Preço (R$)">{input('price', { type: 'number', min: 0, max: 99999999.99, step: '.01', defaultValue: initial?.price ?? 0 })}</Field>
    </>}</div><div className="modal-actions"><button type="button" className="button secondary" onClick={onClose}>Cancelar</button><button className="button primary" disabled={busy}>{busy ? 'Salvando…' : 'Salvar cadastro'}</button></div></form></Modal>;
}
function SummaryCard({ label, value, caption, icon: Icon }) {
  return <article className="summary-card"><div><span>{label}</span><Icon size={19}/></div><strong>{value}</strong><small>{caption}</small></article>;
}
function Empty({ text }) { return <div className="empty"><Search size={26}/><p>{text}</p></div>; }
function Dashboard({ clients, products, navigate, user }) {
  const revenue = clients.reduce((sum, c) => sum + c.revenue, 0); const stock = products.reduce((sum, p) => sum + p.stock, 0);
  const lowStock = products.filter(p => p.stock <= 10);
  const categories = Object.entries(products.reduce((all, p) => { all[p.category] = (all[p.category] || 0) + p.stock; return all; }, Object.create(null))).sort((a, b) => b[1] - a[1]).slice(0, 5);
  return <><div className="welcome"><div><span className="eyebrow light">SEU PAINEL DE CONTROLE</span><h2>Olá, {user.name.split(' ')[0]}.<br/>Vamos construir o próximo passo?</h2><p>Uma visão clara de tudo que você está organizando.</p></div><button className="button light-button" onClick={() => navigate('clientes')}>Ver clientes<ArrowUpRight size={18}/></button></div>
    <div className="summary-grid"><SummaryCard label="Clientes" value={number(clients.length)} caption={`${clients.filter(c => c.status === 'Ativo').length} clientes ativos`} icon={Users}/><SummaryCard label="Produtos" value={number(products.length)} caption="Itens no seu catálogo" icon={Package}/><SummaryCard label="Faturamento informado" value={money(revenue)} caption="Soma dos valores cadastrados" icon={ChartNoAxesCombined}/><SummaryCard label="Estoque disponível" value={number(stock)} caption="Unidades no total" icon={Box}/></div>
    <div className="dashboard-grid"><section className="panel"><div className="panel-title"><div><h3>Estoque por categoria</h3><p>Distribuição das unidades cadastradas</p></div><Package size={20}/></div>
      {categories.length ? <div className="bars">{categories.map(([label, value]) => <div key={label}><div><span>{label}</span><strong>{number(value)}</strong></div><progress value={value} max={Math.max(stock, 1)} aria-label={`Estoque ${label}`}/></div>)}</div> : <Empty text="Seu catálogo começa com o primeiro produto."/>}</section>
      <section className="panel"><div className="panel-title"><div><h3>Atenção ao estoque</h3><p>Produtos com até 10 unidades</p></div><span className="badge warning">{lowStock.length} itens</span></div>
      {lowStock.length ? <div className="stock-list">{lowStock.slice(0, 5).map(p => <div key={p.id}><span className="icon-tile small"><Package size={18}/></span><span><strong>{p.name}</strong><small>{p.brand}</small></span><b className={p.stock <= 5 ? 'danger-text' : ''}>{p.stock} un.</b></div>)}</div> : <div className="all-good"><span><Check size={26}/></span><h4>Tudo em dia por aqui</h4><p>Nenhum produto com estoque baixo.</p></div>}</section></div>
    <section className="panel"><div className="panel-title"><div><h3>Clientes recentes</h3><p>Os últimos relacionamentos adicionados à sua base</p></div><button className="text-button" onClick={() => navigate('clientes')}>Ver todos<ArrowRight size={16}/></button></div>
      {clients.length ? <div className="recent-grid">{clients.slice(-3).reverse().map(c => <div key={c.id}><span className="initial-avatar">{c.name.slice(0, 2).toUpperCase()}</span><span><strong>{c.name}</strong><small>{c.state} · {c.status}</small></span></div>)}</div> : <Empty text="Cadastre seu primeiro cliente para começar."/>}</section></>;
}
function DataPage({ kind, data, user, refresh, notify }) {
  const [query, setQuery] = useState(''); const [page, setPage] = useState(1); const [editing, setEditing] = useState(undefined);
  const [deleting, setDeleting] = useState(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const client = kind === 'clientes'; const canEdit = user.role !== 'consulta';
  const filtered = data.filter(row => Object.values(row).join(' ').toLocaleLowerCase('pt-BR').includes(query.toLocaleLowerCase('pt-BR')));
  const totalPages = Math.max(1, Math.ceil(filtered.length / 10)); const currentPage = Math.min(page, totalPages);
  const shown = filtered.slice((currentPage - 1) * 10, currentPage * 10);
  async function remove() {
    setBusy(true); setError('');
    try { await api(`/${kind}/${deleting.id}`, { method: 'DELETE' }); setDeleting(null); await refresh(); notify('Registro excluído.'); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <><div className="section-heading"><span className="eyebrow">{client ? 'BASE DE RELACIONAMENTOS' : 'CATÁLOGO E ESTOQUE'}</span>{canEdit && <button className="button primary" onClick={() => setEditing(null)}><Plus size={18}/>{client ? 'Novo cliente' : 'Novo produto'}</button>}</div>
    <section className="panel data-panel"><div className="table-toolbar"><label className="search"><Search size={18}/><input aria-label={`Pesquisar ${kind}`} placeholder={client ? 'Buscar por nome, CNPJ ou estado…' : 'Buscar por produto, categoria ou marca…'} value={query} onChange={e => { setQuery(e.target.value); setPage(1); }}/></label><span className="badge">{filtered.length} registros</span></div>
      <div className="table-scroll" tabIndex={0} role="region" aria-label={`Tabela de ${kind}`}><table><thead><tr>{(client ? ['Cliente', 'CNPJ', 'Estado', 'Status', 'Faturamento'] : ['Produto', 'Categoria', 'Marca', 'Estoque', 'Preço']).map(h => <th key={h}>{h}</th>)}{canEdit && <th className="actions-cell">Ações</th>}</tr></thead><tbody>{shown.map(row => <tr key={row.id}>
        <td><strong>{client ? row.company : row.name}</strong>{client && <small>{row.name}</small>}</td>
        {client ? <><td className="nowrap">{row.cnpj}</td><td>{row.state}</td><td><span className={`badge ${row.status === 'Ativo' ? 'success' : ''}`}>{row.status}</span></td><td className="numeric">{money(row.revenue)}</td></> : <><td>{row.category}</td><td>{row.brand}</td><td><span className={`badge ${row.stock <= 5 ? 'danger' : row.stock <= 10 ? 'warning' : ''}`}>{number(row.stock)} un.</span></td><td className="numeric">{money(row.price)}</td></>}
        {canEdit && <td><div className="table-actions"><button className="icon-button" aria-label={`Editar ${row.name}`} onClick={() => setEditing(row)}><Pencil size={16}/></button>{user.role === 'admin' && <button className="icon-button destructive" aria-label={`Excluir ${row.name}`} onClick={() => { setDeleting(row); setError(''); }}><Trash2 size={16}/></button>}</div></td>}</tr>)}</tbody></table></div>
      {!shown.length && <Empty text={query ? 'Nenhum registro corresponde à busca.' : `Nenhum ${client ? 'cliente' : 'produto'} cadastrado ainda.`}/>}
      <div className="pagination"><small>{filtered.length ? `${(currentPage - 1) * 10 + 1}–${Math.min(currentPage * 10, filtered.length)} de ${filtered.length}` : '0 registros'}</small><div><button className="icon-button" aria-label="Página anterior" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={18}/></button><span>{currentPage} / {totalPages}</span><button className="icon-button" aria-label="Próxima página" disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}><ChevronRight size={18}/></button></div></div>
    </section>{editing !== undefined && <EntityForm kind={kind} initial={editing} onClose={() => setEditing(undefined)} onSaved={async () => { setEditing(undefined); await refresh(); notify('Cadastro salvo com sucesso.'); }}/>}
    {deleting && <Modal title="Excluir cadastro?" onClose={() => setDeleting(null)}><p>O registro <strong>{deleting.name}</strong> será removido da base. Essa ação não pode ser desfeita.</p><ErrorMessage message={error}/><div className="modal-actions"><button className="button secondary" onClick={() => setDeleting(null)}>Cancelar</button><button className="button danger-button" onClick={remove} disabled={busy}>{busy ? 'Excluindo…' : 'Excluir registro'}</button></div></Modal>}</>;
}
function Reports({ notify }) {
  const [busy, setBusy] = useState(''); const [error, setError] = useState('');
  async function download(kind, format) {
    setBusy(`${kind}.${format}`); setError('');
    try { await downloadReport(kind, format); notify('Relatório pronto. Confira seus downloads.'); }
    catch (err) { setError(err.message); } finally { setBusy(''); }
  }
  return <><ErrorMessage message={error}/><div className="report-grid">{[
    ['clientes', 'Clientes', 'Resumo cadastral, situação e faturamento informado da sua base.', Users],
    ['produtos', 'Produtos', 'Catálogo completo com categorias, marcas, preços e estoque.', Package],
    ['financeiro', 'Financeiro', 'Totais de cadastros, faturamento informado e valor de estoque.', ChartNoAxesCombined],
  ].map(([kind, title, desc, Icon], index) => <article className="panel report-card" key={kind}><div className="report-top"><span className="icon-tile"><Icon size={24}/></span><span className="report-number">0{index + 1}</span></div><h2>{title}</h2><p>{desc}</p><div className="report-formats">{['pdf', 'docx', 'csv'].map(format => <button key={format} className="button secondary" disabled={!!busy} onClick={() => download(kind, format)}><Download size={15}/>{busy === `${kind}.${format}` ? '…' : format.toUpperCase()}</button>)}</div></article>)}</div><div className="report-note"><FileText size={20}/><p>Os relatórios refletem os dados salvos no momento da emissão. PDF para compartilhar, DOCX para editar e CSV para planilhas. Os indicadores financeiros representam valores informados nos cadastros.</p></div></>;
}
function UserForm({ initial, onClose, onSaved }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); const data = Object.fromEntries(new FormData(event.currentTarget)); data.active = data.active === 'on';
    try { await api(`/users${initial ? `/${initial.id}` : ''}`, { method: initial ? 'PUT' : 'POST', body: data }); onSaved(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <Modal title={initial ? 'Editar acesso' : 'Adicionar à equipe'} onClose={onClose}><form onSubmit={submit}><ErrorMessage message={error}/><div className="form-grid">
    <Field label="Nome completo" full><input name="name" required minLength={2} maxLength={120} defaultValue={initial?.name} autoFocus/></Field>
    <Field label="E-mail" full><input name="email" type="email" required maxLength={190} defaultValue={initial?.email}/></Field>
    <Field label="Perfil"><select name="role" defaultValue={initial?.role || 'consulta'}>{Object.entries(roles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
    <Field label={initial ? 'Nova senha (opcional)' : 'Senha inicial'}><input name="password" type="password" autoComplete="new-password" required={!initial} minLength={12} maxLength={128}/></Field>
    <label className="checkbox"><input name="active" type="checkbox" defaultChecked={initial ? !!initial.active : true}/>Acesso ativo</label>
    </div><p className="muted small-text">Consulta: leitura e relatórios. Operador: também cadastra e edita. Administrador: também exclui e gerencia a equipe. Alterações encerram as sessões desse usuário.</p><div className="modal-actions"><button type="button" className="button secondary" onClick={onClose}>Cancelar</button><button disabled={busy} className="button primary">{busy ? 'Salvando…' : 'Salvar acesso'}</button></div></form></Modal>;
}
function Team({ notify, onSelfChange, currentUser }) {
  const [users, setUsers] = useState([]); const [error, setError] = useState(''); const [editing, setEditing] = useState(undefined);
  const load = useCallback(() => api('/users').then(setUsers).catch(err => setError(err.message)), []); useEffect(() => { load(); }, [load]);
  return <><div className="section-heading"><span className="eyebrow">CONTROLE DE ACESSOS</span><button className="button primary" onClick={() => setEditing(null)}><Plus size={18}/>Adicionar pessoa</button></div><ErrorMessage message={error}/><section className="panel data-panel"><div className="table-scroll"><table><thead><tr><th>Pessoa</th><th>Perfil</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{users.map(user => <tr key={user.id}><td><strong>{user.name}</strong><small>{user.email}</small></td><td>{roles[user.role]}</td><td><span className={`badge ${user.active ? 'success' : ''}`}>{user.active ? 'Ativo' : 'Inativo'}</span></td><td><button className="icon-button" aria-label={`Editar ${user.name}`} onClick={() => setEditing(user)}><Pencil size={16}/></button></td></tr>)}</tbody></table></div></section>
    {editing !== undefined && <UserForm initial={editing} onClose={() => setEditing(undefined)} onSaved={() => { const self = editing?.id === currentUser.id; setEditing(undefined); if (self) onSelfChange(); else { load(); notify('Acesso atualizado.'); } }}/>}</>;
}
function Account({ user, notify }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form));
    if (data.password !== data.confirm) { setError('As novas senhas não coincidem.'); return; }
    setBusy(true); setError('');
    try { await api('/auth/password', { method: 'POST', body: data }); form.reset(); notify('Senha alterada. Outras sessões foram encerradas.'); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <section className="panel account-panel"><span className="icon-tile"><KeyRound/></span><h2>{user.name}</h2><p className="muted">{user.email} · {roles[user.role]}</p><hr/><h3>Alterar senha</h3><form onSubmit={submit}><ErrorMessage message={error}/><Field label="Senha atual"><input name="currentPassword" required type="password" autoComplete="current-password" maxLength={128}/></Field><Field label="Nova senha"><input name="password" required type="password" minLength={12} maxLength={128} autoComplete="new-password"/></Field><Field label="Confirme a nova senha"><input name="confirm" required type="password" minLength={12} maxLength={128} autoComplete="new-password"/></Field><small className="muted">No mínimo 12 caracteres. Use uma senha exclusiva para sua conta.</small><button className="button primary" disabled={busy}>{busy ? 'Salvando…' : 'Atualizar senha'}</button></form></section>;
}
function App() {
  const [pendingDatabase, setPendingDatabase] = useState(false);
  const [user, setUser] = useState(null); const [setup, setSetup] = useState(false); const [checking, setChecking] = useState(true);
  const [page, setPage] = useState('dashboard'); const [mobile, setMobile] = useState(false);
  const [clients, setClients] = useState([]); const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false); const [error, setError] = useState(''); const [toast, setToast] = useState('');
  const reset = useCallback(() => { setUser(null); setCsrf(''); setClients([]); setProducts([]); setPage('dashboard'); }, []);
  const initialize = useCallback(async () => {
    setChecking(true); setError('');
    try { const state = await api('/auth/status'); setPendingDatabase(state.databaseConfigured === false); setSetup(state.requiresSetup); if (state.databaseConfigured !== false && !state.requiresSetup) { try { const result = await api('/auth/me'); setUser(result.user); } catch (err) { if (err.status !== 401) throw err; } } }
    catch (err) { setError(err.message); } finally { setChecking(false); }
  }, []);
  useEffect(() => { initialize(); window.addEventListener('session-expired', reset); return () => window.removeEventListener('session-expired', reset); }, [initialize, reset]);
  const refresh = useCallback(async () => {
    setLoading(true); setError('');
    try { const [c, p] = await Promise.all([api('/clientes'), api('/produtos')]); setClients(c); setProducts(p); }
    catch (err) { setError(err.message); } finally { setLoading(false); }
  }, []);
  useEffect(() => { if (user) refresh(); }, [user, refresh]);
  useEffect(() => { if (!toast) return; const timeout = setTimeout(() => setToast(''), 5000); return () => clearTimeout(timeout); }, [toast]);
  function navigate(next) { setPage(next); setMobile(false); document.title = `${pages[next].title} · NexusGest`; }
  async function logout() { try { await api('/auth/logout', { method: 'POST' }); reset(); } catch (err) { setError(err.message); } }
  if (checking) return <div className="loading-screen"><Brand/><span>Preparando seu espaço…</span></div>;
  if (pendingDatabase) return <div className="loading-screen"><Brand/><span className="icon-tile"><Layers3/></span><h1>Seu próximo passo começa aqui.</h1><p className="muted">Clientes, produtos e relatórios em um espaço conectado.</p><p className="muted">Estamos preparando o ambiente online. O acesso será liberado após a configuração do banco de dados.</p><button className="button secondary" onClick={initialize}><RefreshCw size={16}/>Verificar disponibilidade</button></div>;
  if (!user && error) return <div className="loading-screen"><Brand/><ErrorMessage message={error}/><button className="button primary" onClick={initialize}><RefreshCw size={16}/>Tentar novamente</button></div>;
  if (!user) return <Login setup={setup} onLogin={value => { setUser(value); setSetup(false); }}/>;
  return <div className="app-shell">{mobile && <button className="sidebar-backdrop" aria-label="Fechar menu" onClick={() => setMobile(false)}/>}
    <aside className={`sidebar ${mobile ? 'open' : ''}`}><Brand/><span className="nav-label">ESPAÇO DE TRABALHO</span><nav aria-label="Navegação principal">{Object.entries(pages).filter(([key]) => key !== 'conta' && (key !== 'usuarios' || user.role === 'admin')).map(([key, { title, icon: Icon }]) => <button key={key} className={page === key ? 'nav-item active' : 'nav-item'} aria-current={page === key ? 'page' : undefined} onClick={() => navigate(key)}><Icon size={19}/><span>{title}</span>{page === key && <span className="nav-indicator"/>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="workspace-card"><span className="icon-tile small"><Layers3 size={18}/></span><div><strong>Meu espaço</strong><small>NexusGest 1.0</small></div></div><button className={`nav-item ${page === 'conta' ? 'active' : ''}`} onClick={() => navigate('conta')}><Settings size={19}/>Minha conta</button><button className="nav-item" onClick={logout}><LogOut size={19}/>Sair</button></div></aside>
    <div className="main-area"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-toggle" aria-label="Abrir menu" onClick={() => setMobile(true)}><Menu/></button><span>Workspace</span><ChevronRight size={14}/><strong>{pages[page].title}</strong></div><button className="user-menu" onClick={() => navigate('conta')}><span className="user-text"><strong>{user.name}</strong><small>{roles[user.role]}</small></span><span className="initial-avatar">{user.name.slice(0, 2).toUpperCase()}</span></button></header>
      <main className="main-content"><div className="page-heading"><div><h1>{pages[page].title}</h1><p>{pages[page].subtitle}</p></div><button className="button secondary" onClick={refresh} disabled={loading}><RefreshCw size={15} className={loading ? 'spin' : ''}/><span>Atualizar</span></button></div>
      <ErrorMessage message={error}/>{loading && !clients.length && !products.length ? <div className="empty" role="status">Carregando seus dados…</div> : <>
        {page === 'dashboard' && <Dashboard clients={clients} products={products} navigate={navigate} user={user}/>}
        {['clientes', 'produtos'].includes(page) && <DataPage key={page} kind={page} data={page === 'clientes' ? clients : products} user={user} refresh={refresh} notify={setToast}/>}
        {page === 'relatorios' && <Reports notify={setToast}/>}
        {page === 'usuarios' && user.role === 'admin' && <Team notify={setToast} currentUser={user} onSelfChange={reset}/>}
        {page === 'conta' && <Account user={user} notify={setToast}/>}
      </>}<footer className="page-footer"><span>NexusGest <span className="muted">/ Gestão conectada</span></span><span className={error ? 'connection-error' : 'connection-ok'}><i/>{error ? 'Verifique a conexão' : loading ? 'Sincronizando…' : 'Dados sincronizados'}</span></footer></main></div>
    {toast && <div className="toast" role="status"><Check size={18}/>{toast}<button aria-label="Fechar aviso" onClick={() => setToast('')}><X size={16}/></button></div>}
  </div>;
}
createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>);
