/**
 * Cliente API para o backend PAICS (FastAPI)
 * No browser: usa origem atual se env não definido (produção).
 * No server (SSR): usa localhost:8000.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined" ? "" : "http://localhost:8000");

export interface User {
  id: string;
  username: string;
  email: string;
  nome: string;
  role: string;
  primeiro_acesso?: boolean;
  clinica_id?: string;
}

export interface Exame {
  id: string;
  paciente: string;
  tutor: string;
  clinica?: string;
  status: string;
  tipo_exame: string;
  created_at: string | null;
  created_at_raw?: string;
  n_imagens: number;
  tem_laudo: boolean;
  liberado_at?: string | null;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  access_token?: string;
  refresh_token?: string;
  user?: User;
}

async function getTokens(): Promise<{ access: string; refresh: string } | null> {
  if (typeof window === "undefined") return null;
  const access = localStorage.getItem("paics_access_token");
  const refresh = localStorage.getItem("paics_refresh_token");
  if (!access || !refresh) return null;
  return { access, refresh };
}

async function setTokens(access: string, refresh: string): Promise<void> {
  if (typeof window === "undefined") return;
  localStorage.setItem("paics_access_token", access);
  localStorage.setItem("paics_refresh_token", refresh);
}

export async function clearTokens(): Promise<void> {
  if (typeof window === "undefined") return;
  localStorage.removeItem("paics_access_token");
  localStorage.removeItem("paics_refresh_token");
}

async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const tokens = await getTokens();
  const headers: HeadersInit = { ...options.headers };
  if (!(options.body instanceof FormData)) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  if (tokens) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${tokens.access}`;
  }

  let res = await fetch(`${API_BASE}${url}`, { ...options, headers });

  if (res.status === 401 && tokens) {
    const refreshRes = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refresh }),
    });
    if (refreshRes.ok) {
      const data = await refreshRes.json();
      await setTokens(data.access_token, data.refresh_token);
      (headers as Record<string, string>)["Authorization"] = `Bearer ${data.access_token}`;
      res = await fetch(`${API_BASE}${url}`, { ...options, headers });
    }
  }
  return res;
}

export async function isAuthenticated(): Promise<boolean> {
  const tokens = await getTokens();
  if (!tokens) return false;
  const res = await fetchWithAuth("/api/auth/me");
  return res.ok;
}

export async function login(
  emailOrUsername: string,
  password: string,
  rememberMe = false
): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email_or_username: emailOrUsername,
      password,
      remember_me: rememberMe,
    }),
  });
  const data = await res.json();
  if (data.success && data.access_token && data.refresh_token) {
    await setTokens(data.access_token, data.refresh_token);
  }
  return data;
}

export async function logout(): Promise<void> {
  await clearTokens();
}

export async function getMe(): Promise<User | null> {
  const res = await fetchWithAuth("/api/auth/me");
  if (!res.ok) return null;
  return res.json();
}

export async function alterarSenha(senhaAtual: string, novaSenha: string): Promise<{ success: boolean; message?: string }> {
  const res = await fetchWithAuth("/api/auth/alterar-senha", {
    method: "POST",
    body: JSON.stringify({ senha_atual: senhaAtual, nova_senha: novaSenha }),
  });
  return res.json();
}

// --- Exames ---
export async function listExames(params?: {
  status?: string;
  tipo_exame?: string;
  search?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<Exame[]> {
  const sp = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
    });
  }
  const res = await fetchWithAuth(`/api/exames?${sp.toString()}`);
  if (!res.ok) throw new Error("Erro ao listar exames");
  return res.json();
}

export async function getExame(id: string): Promise<any> {
  const res = await fetchWithAuth(`/api/exames/${id}`);
  if (!res.ok) throw new Error("Erro ao obter exame");
  return res.json();
}

export async function excluirExame(id: string): Promise<void> {
  const res = await fetchWithAuth(`/api/exames/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = typeof err?.detail === "string" ? err.detail : "Erro ao excluir exame";
    throw new Error(msg);
  }
}

export async function loadImageAsBlobUrl(exameId: string, ref: string): Promise<string> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/imagens/${ref}`);
  if (!res.ok) throw new Error("Erro ao carregar imagem");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function addObservacao(exameId: string, texto: string): Promise<void> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/observacao`, {
    method: "POST",
    body: JSON.stringify({ texto }),
  });
  if (!res.ok) throw new Error("Erro ao adicionar observação");
}

export async function atualizarRequisicao(
  exameId: string,
  updates: {
    paciente?: string;
    tutor?: string;
    especie?: string;
    idade?: string;
    raca?: string;
    regiao_estudo?: string;
    suspeita_clinica?: string;
    historico_clinico?: string;
  }
): Promise<void> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/requisicao`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Erro ao atualizar requisição");
}

export async function gerarLaudo(exameId: string, imagensRefs?: string[]): Promise<{ success: boolean; laudo_id?: string }> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/gerar-laudo`, {
    method: "POST",
    body: JSON.stringify(imagensRefs ? { imagens_refs: imagensRefs } : {}),
  });
  return res.json();
}

export async function atualizarLaudo(exameId: string, texto: string): Promise<void> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/laudo`, {
    method: "PATCH",
    body: JSON.stringify({ texto }),
  });
  if (!res.ok) throw new Error("Erro ao atualizar laudo");
}

export async function validarLaudo(exameId: string): Promise<void> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/laudo/validar`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Erro ao validar laudo");
}

export async function liberarLaudo(exameId: string): Promise<void> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/laudo/liberar`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Erro ao liberar laudo");
}

export async function regenerarLaudo(exameId: string, correcoes: string): Promise<{ success: boolean; texto?: string }> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/laudo/regenerar`, {
    method: "POST",
    body: JSON.stringify({ correcoes }),
  });
  return res.json();
}

export async function cancelarLaudo(exameId: string): Promise<void> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/laudo`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Erro ao cancelar laudo");
}

export async function downloadPdf(exameId: string): Promise<Blob> {
  const res = await fetchWithAuth(`/api/exames/${exameId}/pdf`);
  if (!res.ok) throw new Error("Erro ao baixar PDF");
  return res.blob();
}

/** Abre preview do PDF em nova aba. Admin pode ver antes de liberar (preview=true). */
export async function previewPdf(exameId: string, asAdmin = false): Promise<void> {
  const url = `/api/exames/${exameId}/pdf${asAdmin ? "?preview=1" : ""}`;
  const res = await fetchWithAuth(url);
  if (!res.ok) throw new Error("Erro ao carregar preview do PDF");
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  window.open(objectUrl, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
}

// --- Requisições / Clínicas ---
export async function listClinicas(apenasAtivas = true): Promise<{ id: string; nome: string; cnpj?: string }[]> {
  const res = await fetchWithAuth(`/api/clinicas?apenas_ativas=${apenasAtivas}`);
  if (!res.ok) throw new Error("Erro ao listar clínicas");
  return res.json();
}

export async function listVeterinarios(clinicaId: string, apenasAtivos = true): Promise<{ id: string; nome: string; crmv?: string }[]> {
  const res = await fetchWithAuth(`/api/clinicas/${clinicaId}/veterinarios?apenas_ativos=${apenasAtivos}`);
  if (!res.ok) throw new Error("Erro ao listar veterinários");
  return res.json();
}

export async function criarRequisicao(formData: FormData): Promise<{ success: boolean; id?: string }> {
  const res = await fetchWithAuth("/api/requisicoes", {
    method: "POST",
    headers: {}, // não definir Content-Type - FormData define automaticamente
    body: formData,
  });
  return res.json();
}

export async function salvarRascunho(formData: FormData): Promise<{ success: boolean; id?: string }> {
  const res = await fetchWithAuth("/api/requisicoes/rascunho", {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function listRascunhos(): Promise<any[]> {
  const res = await fetchWithAuth("/api/requisicoes/rascunhos");
  if (!res.ok) throw new Error("Erro ao listar rascunhos");
  return res.json();
}

// --- CEP (público) ---
export async function buscarCep(cep: string): Promise<any> {
  const cepLimpo = cep.replace(/\D/g, "");
  if (cepLimpo.length !== 8) throw new Error("CEP deve ter 8 dígitos");
  const res = await fetch(`${API_BASE}/api/cep/${cepLimpo}`);
  if (!res.ok) throw new Error("CEP não encontrado");
  return res.json();
}

// --- Usuários ---
export async function listUsuarios(): Promise<any[]> {
  const res = await fetchWithAuth("/api/usuarios");
  if (!res.ok) throw new Error("Erro ao listar usuários");
  return res.json();
}

export async function getUsuario(usuarioId: string): Promise<any> {
  const res = await fetchWithAuth(`/api/usuarios/${usuarioId}`);
  if (!res.ok) throw new Error("Usuário não encontrado");
  return res.json();
}

export async function criarUsuario(data: {
  nome: string;
  username: string;
  email: string;
  senha_temporaria: string;
  role?: string;
  clinica_id?: string;
}): Promise<any> {
  const res = await fetchWithAuth("/api/usuarios", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function atualizarUsuario(usuarioId: string, data: Record<string, any>): Promise<void> {
  const res = await fetchWithAuth(`/api/usuarios/${usuarioId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Erro ao atualizar usuário");
}

export async function excluirUsuario(usuarioId: string): Promise<void> {
  const res = await fetchWithAuth(`/api/usuarios/${usuarioId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Erro ao excluir usuário");
}

// --- Clínicas ---
export async function getClinica(clinicaId: string): Promise<any> {
  const res = await fetchWithAuth(`/api/clinicas/${clinicaId}`);
  if (!res.ok) throw new Error("Clínica não encontrada");
  return res.json();
}

export async function criarClinicaCompleta(data: {
  nome: string;
  cnpj?: string;
  endereco?: string;
  numero?: string;
  bairro?: string;
  cidade?: string;
  cep?: string;
  telefone?: string;
  email: string;
  username: string;
  senha_temporaria: string;
}): Promise<any> {
  const res = await fetchWithAuth("/api/clinicas/completo", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function criarVeterinario(clinicaId: string, data: { nome: string; crmv: string; email?: string }): Promise<any> {
  const res = await fetchWithAuth(`/api/clinicas/${clinicaId}/veterinarios`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = typeof err?.detail === "string" ? err.detail : Array.isArray(err?.detail) ? err.detail.map((d: any) => d?.msg ?? d).join(", ") : "Erro ao cadastrar veterinário";
    throw new Error(msg);
  }
  return res.json();
}

export async function atualizarClinica(clinicaId: string, data: Record<string, any>): Promise<any> {
  const res = await fetchWithAuth(`/api/clinicas/${clinicaId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function excluirClinica(clinicaId: string): Promise<void> {
  const res = await fetchWithAuth(`/api/clinicas/${clinicaId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = typeof err?.detail === "string" ? err.detail : "Erro ao excluir clínica";
    throw new Error(msg);
  }
}

// --- Financeiro ---
export async function listFaturas(status?: string, userId?: string): Promise<any[]> {
  const sp = new URLSearchParams();
  if (status) sp.set("status", status);
  if (userId) sp.set("user_id", userId);
  const qs = sp.toString() ? `?${sp}` : "";
  const res = await fetchWithAuth(`/api/faturas${qs}`);
  if (!res.ok) throw new Error("Erro ao listar faturas");
  return res.json();
}

export async function fechamentoTodos(
  dataInicio: string,
  dataFim: string,
  valorPorExame?: number,
  valorPlantao?: number
): Promise<any> {
  const sp = new URLSearchParams({
    data_inicio: dataInicio,
    data_fim: dataFim,
    ...(valorPorExame != null && { valor_por_exame: String(valorPorExame) }),
    ...(valorPlantao != null && { valor_plantao: String(valorPlantao) }),
  });
  const res = await fetchWithAuth(`/api/financeiro/fechamento-todos?${sp}`);
  return res.json();
}

export async function gerarFechamento(params: {
  user_id: string;
  data_inicio: string;
  data_fim: string;
  valor_por_exame?: number;
  valor_plantao?: number;
}): Promise<any> {
  const res = await fetchWithAuth("/api/financeiro/fechamento", {
    method: "POST",
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function criarFatura(params: {
  user_id: string;
  periodo: string;
  exames: any[];
  valor_total: number;
}): Promise<{ success: boolean; id?: string }> {
  const res = await fetchWithAuth("/api/financeiro/faturas", {
    method: "POST",
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function atualizarStatusFatura(faturaId: string, status: "paga" | "cancelada"): Promise<void> {
  const res = await fetchWithAuth(`/api/faturas/${faturaId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error("Erro ao atualizar fatura");
}

// --- Knowledge Base ---
export async function listarKnowledgeBase(tipo?: string): Promise<any[]> {
  const sp = tipo ? `?tipo=${tipo}` : "";
  const res = await fetchWithAuth(`/api/knowledge-base${sp}`);
  if (!res.ok) throw new Error("Erro ao listar knowledge base");
  return res.json();
}

export async function adicionarKbPdf(file: File, titulo: string, tags?: string[]): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("titulo", titulo);
  if (tags?.length) formData.append("tags", tags.join(","));
  const res = await fetchWithAuth("/api/knowledge-base/pdf", {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function adicionarKbPrompt(titulo: string, conteudo: string, tags?: string[]): Promise<any> {
  const res = await fetchWithAuth("/api/knowledge-base/prompt", {
    method: "POST",
    body: JSON.stringify({ titulo, conteudo, tags }),
  });
  return res.json();
}

export async function adicionarKbOrientacao(titulo: string, conteudo: string, tags?: string[]): Promise<any> {
  const res = await fetchWithAuth("/api/knowledge-base/orientacao", {
    method: "POST",
    body: JSON.stringify({ titulo, conteudo, tags }),
  });
  return res.json();
}

export async function excluirKnowledgeBaseItem(kbId: string): Promise<void> {
  const res = await fetchWithAuth(`/api/knowledge-base/${kbId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Erro ao excluir item");
}

export async function getLearningStats(): Promise<any> {
  const res = await fetchWithAuth("/api/knowledge-base/learning/stats");
  return res.json();
}

export async function buscarKnowledgeBase(q: string, n = 5): Promise<any[]> {
  const res = await fetchWithAuth(`/api/knowledge-base/search?q=${encodeURIComponent(q)}&n=${n}`);
  if (!res.ok) return [];
  return res.json();
}
