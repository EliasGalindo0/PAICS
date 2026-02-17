"use client";

import React, { useEffect, useState } from "react";
import {
  listClinicas,
  listUsuarios,
  criarUsuario,
  atualizarUsuario,
  excluirUsuario,
  getUsuario,
  getMe,
  buscarCep,
  criarClinicaCompleta,
  getClinica,
  listVeterinarios,
  criarVeterinario,
  atualizarClinica,
  excluirClinica,
} from "@/lib/api";

function gerarSenhaTemporaria(): string {
  const chars = "abcdefghjkmnpqrstuvwxyz23456789";
  let s = "";
  for (let i = 0; i < 10; i++)
    s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}

export default function AdminClinicasPage() {
  const [clinicas, setClinicas] = useState<any[]>([]);
  const [usuarios, setUsuarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    nome: "",
    username: "",
    email: "",
    senha_temporaria: "",
    role: "user",
    clinica_id: "",
  });
  const [criando, setCriando] = useState(false);
  const [novoUserCreds, setNovoUserCreds] = useState<{
    username: string;
    email: string;
    senha_temporaria: string;
  } | null>(null);

  // Nova clínica (completa: clínica + usuário)
  const [showClinicaForm, setShowClinicaForm] = useState(false);
  const [clinicaForm, setClinicaForm] = useState({
    nome: "",
    cnpj: "",
    cep: "",
    logradouro: "",
    numero: "",
    bairro: "",
    cidade: "",
    uf: "",
    telefone: "",
    email: "",
    username: "",
    senha_temporaria: "",
  });
  const [buscandoCep, setBuscandoCep] = useState(false);
  const [criandoClinica, setCriandoClinica] = useState(false);
  const [novaClinicaCreds, setNovaClinicaCreds] = useState<{
    nome_clinica: string;
    username: string;
    senha_temporaria: string;
  } | null>(null);

  // Edição de clínica
  const [editClinicaId, setEditClinicaId] = useState<string | null>(null);
  const [editClinicaForm, setEditClinicaForm] = useState<Record<
    string,
    string
  > | null>(null);
  const [salvandoClinica, setSalvandoClinica] = useState(false);
  const [editCepBusca, setEditCepBusca] = useState("");

  // Veterinários por clínica
  const [vetAddClinicaId, setVetAddClinicaId] = useState<string | null>(null);
  const [vetForm, setVetForm] = useState({ nome: "", crmv: "", email: "" });
  const [criandoVet, setCriandoVet] = useState(false);
  const [veterinariosCache, setVeterinariosCache] = useState<
    Record<string, any[]>
  >({});

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{
    nome: string;
    username: string;
    email: string;
    role: string;
    ativo: boolean;
    clinica_id: string;
  } | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [deletandoId, setDeletandoId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletandoClinicaId, setDeletandoClinicaId] = useState<string | null>(null);
  const [confirmDeleteClinicaId, setConfirmDeleteClinicaId] = useState<string | null>(null);

  const [filtros, setFiltros] = useState({
    nome: "",
    usuario: "",
    email: "",
    tipo: "",
    clinica: "",
    status: "",
  });

  const [viewingUserId, setViewingUserId] = useState<string | null>(null);
  const [detailUsuario, setDetailUsuario] = useState<any | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([listClinicas(false), listUsuarios()])
      .then(([c, u]) => {
        setClinicas(c);
        setUsuarios(u);
        c.forEach((clinica) => loadVets(clinica.id));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const loadVets = (clinicaId: string) => {
    listVeterinarios(clinicaId, false).then((vets) => {
      setVeterinariosCache((prev) => ({ ...prev, [clinicaId]: vets }));
    });
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    getMe()
      .then((u) => setCurrentUserId(u?.id ?? null))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!viewingUserId) {
      setDetailUsuario(null);
      return;
    }
    setLoadingDetail(true);
    getUsuario(viewingUserId)
      .then(setDetailUsuario)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingDetail(false));
  }, [viewingUserId]);

  useEffect(() => {
    if (detailUsuario?.clinica_id && !veterinariosCache[detailUsuario.clinica_id]) {
      loadVets(detailUsuario.clinica_id);
    }
  }, [detailUsuario?.clinica_id]);

  const handleBuscarCep = async () => {
    const cep = clinicaForm.cep.replace(/\D/g, "");
    if (cep.length !== 8) {
      setError("CEP deve ter 8 dígitos");
      return;
    }
    setBuscandoCep(true);
    setError("");
    try {
      const data = await buscarCep(cep);
      setClinicaForm((f) => ({
        ...f,
        logradouro: data.logradouro || f.logradouro,
        bairro: data.bairro || f.bairro,
        cidade: data.cidade || f.cidade,
        uf: data.uf || f.uf,
        cep: data.cep || f.cep,
      }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBuscandoCep(false);
    }
  };

  const handleCriarClinicaCompleta = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !clinicaForm.nome ||
      !clinicaForm.email ||
      !clinicaForm.username ||
      !clinicaForm.senha_temporaria
    ) {
      setError("Preencha nome, e-mail, usuário e senha temporária");
      return;
    }
    if (clinicaForm.senha_temporaria.length < 6) {
      setError("Senha temporária deve ter pelo menos 6 caracteres");
      return;
    }
    setCriandoClinica(true);
    setError("");
    try {
      const res = await criarClinicaCompleta({
        nome: clinicaForm.nome,
        cnpj: clinicaForm.cnpj,
        endereco: clinicaForm.logradouro,
        numero: clinicaForm.numero,
        bairro: clinicaForm.bairro,
        cidade: clinicaForm.cidade,
        cep: clinicaForm.cep,
        telefone: clinicaForm.telefone,
        email: clinicaForm.email,
        username: clinicaForm.username,
        senha_temporaria: clinicaForm.senha_temporaria,
      });
      setNovaClinicaCreds({
        nome_clinica: res.clinica.nome,
        username: res.username,
        senha_temporaria: res.senha_temporaria,
      });
      setClinicaForm({
        nome: "",
        cnpj: "",
        cep: "",
        logradouro: "",
        numero: "",
        bairro: "",
        cidade: "",
        uf: "",
        telefone: "",
        email: "",
        username: "",
        senha_temporaria: "",
      });
      setShowClinicaForm(false);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCriandoClinica(false);
    }
  };

  const handleEditarClinica = async (c: any) => {
    setEditClinicaId(c.id);
    try {
      const full = await getClinica(c.id);
      setEditClinicaForm({
        nome: full.nome || "",
        cnpj: full.cnpj || "",
        endereco: full.endereco || "",
        numero: full.numero || "",
        bairro: full.bairro || "",
        cidade: full.cidade || "",
        cep: full.cep || "",
        telefone: full.telefone || "",
        email: full.email || "",
      });
    } catch {
      setEditClinicaForm({
        nome: c.nome || "",
        cnpj: c.cnpj || "",
        endereco: c.endereco || "",
        numero: "",
        bairro: "",
        cidade: "",
        cep: "",
        telefone: c.telefone || "",
        email: c.email || "",
      });
    }
    setEditCepBusca("");
    loadVets(c.id);
  };

  const handleBuscarCepEdit = async () => {
    if (!editClinicaId || !editClinicaForm) return;
    const cep = editCepBusca.replace(/\D/g, "");
    if (cep.length !== 8) {
      setError("CEP deve ter 8 dígitos");
      return;
    }
    try {
      const data = await buscarCep(cep);
      setEditClinicaForm((f) =>
        f
          ? {
              ...f,
              endereco: data.logradouro || f.endereco,
              bairro: data.bairro || f.bairro,
              cidade: data.cidade || f.cidade,
              cep: data.cep || f.cep,
            }
          : null,
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleSalvarClinica = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editClinicaId || !editClinicaForm) return;
    setSalvandoClinica(true);
    setError("");
    try {
      await atualizarClinica(editClinicaId, {
        nome: editClinicaForm.nome,
        cnpj: editClinicaForm.cnpj,
        endereco: editClinicaForm.endereco,
        numero: editClinicaForm.numero,
        bairro: editClinicaForm.bairro,
        cidade: editClinicaForm.cidade,
        cep: editClinicaForm.cep,
        telefone: editClinicaForm.telefone,
        email: editClinicaForm.email,
      });
      setEditClinicaId(null);
      setEditClinicaForm(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSalvandoClinica(false);
    }
  };

  const handleAddVet = (clinicaId: string) => {
    setVetAddClinicaId(clinicaId);
    setVetForm({ nome: "", crmv: "", email: "" });
    if (!veterinariosCache[clinicaId]) loadVets(clinicaId);
  };

  const handleCriarVet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vetAddClinicaId || !vetForm.nome || !vetForm.crmv) {
      setError("Preencha nome e CRMV");
      return;
    }
    const clinicaId = vetAddClinicaId;
    setCriandoVet(true);
    setError("");
    try {
      await criarVeterinario(clinicaId, {
        nome: vetForm.nome,
        crmv: vetForm.crmv,
        email: vetForm.email,
      });
      setVetAddClinicaId(null);
      setVetForm({ nome: "", crmv: "", email: "" });
      loadVets(clinicaId);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCriandoVet(false);
    }
  };

  const handleGerarSenha = () => {
    setForm((f) => ({ ...f, senha_temporaria: gerarSenhaTemporaria() }));
  };
  const handleGerarSenhaClinica = () => {
    setClinicaForm((f) => ({ ...f, senha_temporaria: gerarSenhaTemporaria() }));
  };

  const handleCriarUsuario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.nome || !form.username || !form.email || !form.senha_temporaria) {
      setError("Preencha todos os campos");
      return;
    }
    if (form.senha_temporaria.length < 6) {
      setError("Senha temporária deve ter pelo menos 6 caracteres");
      return;
    }
    setCriando(true);
    setError("");
    try {
      const res = await criarUsuario({
        nome: form.nome,
        username: form.username,
        email: form.email,
        senha_temporaria: form.senha_temporaria,
        role: form.role,
        clinica_id: form.clinica_id || undefined,
      });
      setNovoUserCreds({
        username: form.username,
        email: form.email,
        senha_temporaria: res.senha_temporaria,
      });
      setForm({
        nome: "",
        username: "",
        email: "",
        senha_temporaria: "",
        role: "user",
        clinica_id: "",
      });
      setShowForm(false);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCriando(false);
    }
  };

  const handleEditar = (u: any) => {
    setEditingId(u.id);
    setEditForm({
      nome: u.nome || "",
      username: u.username || "",
      email: u.email || "",
      role: u.role || "user",
      ativo: u.ativo !== false,
      clinica_id: u.clinica_id || "",
    });
  };

  const handleSalvarEdicao = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingId || !editForm) return;
    setSalvando(true);
    setError("");
    try {
      await atualizarUsuario(editingId, {
        nome: editForm.nome,
        username: editForm.username,
        email: editForm.email,
        role: editForm.role,
        ativo: editForm.ativo,
        clinica_id:
          editForm.role === "user" ? editForm.clinica_id || null : null,
      });
      setEditingId(null);
      setEditForm(null);
      load();
      if (viewingUserId === editingId) {
        const updated = await getUsuario(editingId);
        setDetailUsuario(updated);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSalvando(false);
    }
  };

  const handleExcluir = async (id: string) => {
    if (confirmDeleteId !== id) {
      setConfirmDeleteId(id);
      return;
    }
    setDeletandoId(id);
    setError("");
    try {
      await excluirUsuario(id);
      setConfirmDeleteId(null);
      setViewingUserId(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDeletandoId(null);
    }
  };

  const handleExcluirClinica = async (clinicaId: string) => {
    if (confirmDeleteClinicaId !== clinicaId) {
      setConfirmDeleteClinicaId(clinicaId);
      return;
    }
    setDeletandoClinicaId(clinicaId);
    setError("");
    try {
      await excluirClinica(clinicaId);
      setConfirmDeleteClinicaId(null);
      setEditClinicaId(null);
      setEditClinicaForm(null);
      setVetAddClinicaId(null);
      load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDeletandoClinicaId(null);
    }
  };

  const handleToggleAtivo = async (id: string, ativoAtual: boolean) => {
    setError("");
    try {
      await atualizarUsuario(id, { ativo: !ativoAtual });
      if (detailUsuario?.id === id) {
        setDetailUsuario((prev: any) =>
          prev ? { ...prev, ativo: !ativoAtual } : null,
        );
      }
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const getUsuarioByClinica = (clinicaId: string) =>
    usuarios.find((u) => u.clinica_id === clinicaId);
  const getVets = (clinicaId: string) => veterinariosCache[clinicaId] ?? [];

  const usuariosFiltrados = usuarios.filter((u) => {
    if (
      filtros.nome &&
      !(u.nome || "").toLowerCase().includes(filtros.nome.toLowerCase())
    )
      return false;
    if (
      filtros.usuario &&
      !(u.username || "").toLowerCase().includes(filtros.usuario.toLowerCase())
    )
      return false;
    if (
      filtros.email &&
      !(u.email || "").toLowerCase().includes(filtros.email.toLowerCase())
    )
      return false;
    if (
      filtros.tipo &&
      (u.role || "").toLowerCase() !== filtros.tipo.toLowerCase()
    )
      return false;
    const clinicaNome = u.clinica_id
      ? clinicas.find((c) => c.id === u.clinica_id)?.nome || ""
      : "";
    if (
      filtros.clinica &&
      !clinicaNome.toLowerCase().includes(filtros.clinica.toLowerCase())
    )
      return false;
    if (filtros.status) {
      const ativo = u.ativo !== false;
      const buscaStatus = filtros.status.toLowerCase();
      if (buscaStatus === "ativo" && !ativo) return false;
      if (buscaStatus === "inativo" && ativo) return false;
    }
    return true;
  });

  const usuariosAdmin = usuariosFiltrados.filter((u) => u.role === "admin");
  const clinicasFiltradas = clinicas.filter((c) => {
    if (filtros.tipo && filtros.tipo.toLowerCase() !== "user") return false; // tipo "user" = clínica
    if (
      filtros.nome &&
      !(c.nome || "").toLowerCase().includes(filtros.nome.toLowerCase())
    )
      return false;
    const u = getUsuarioByClinica(c.id);
    if (
      filtros.usuario &&
      (!u ||
        !(u.username || "")
          .toLowerCase()
          .includes(filtros.usuario.toLowerCase()))
    )
      return false;
    if (
      filtros.email &&
      (!u ||
        !(u.email || "").toLowerCase().includes(filtros.email.toLowerCase()))
    )
      return false;
    if (filtros.status && u) {
      const ativo = u.ativo !== false;
      const buscaStatus = filtros.status.toLowerCase();
      if (buscaStatus === "ativo" && !ativo) return false;
      if (buscaStatus === "inativo" && ativo) return false;
    }
    if (
      filtros.clinica &&
      !(c.nome || "").toLowerCase().includes(filtros.clinica.toLowerCase())
    )
      return false;
    return true;
  });

  const styleBtn = {
    padding: "8px 16px",
    background: "#1a2d4a",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer" as const,
  };
  const styleInput = {
    width: "100%",
    padding: 10,
    borderRadius: 6,
    border: "1px solid #d1d5db",
    boxSizing: "border-box" as const,
  };
  const containerStyle = {
    width: "100%",
    padding: "0 16px",
    boxSizing: "border-box" as const,
  };

  return (
    <div style={containerStyle}>
      <h1 style={{ fontSize: "1.25rem", marginBottom: 16 }}>
        Clínicas e Usuários
      </h1>
      {error && (
        <div
          className="paics-error"
          style={{ padding: 12, borderRadius: 6, marginBottom: 16 }}
        >
          {error}
          <button
            onClick={() => setError("")}
            style={{
              marginLeft: 12,
              padding: "2px 8px",
              background: "#b91c1c",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
        </div>
      )}
      {novaClinicaCreds && (
        <div
          className="paics-success"
          style={{ padding: 14, borderRadius: 6, marginBottom: 20 }}
        >
          <strong>Clínica e conta criadas!</strong> Compartilhe as credenciais
          de acesso:
          <pre
            className="paics-card"
            style={{ marginTop: 8, padding: 8, borderRadius: 4 }}
          >{`Clínica: ${novaClinicaCreds.nome_clinica}\nUsuário: ${novaClinicaCreds.username}\nSenha temporária: ${novaClinicaCreds.senha_temporaria}`}</pre>
          <button
            onClick={() => setNovaClinicaCreds(null)}
            style={{
              marginTop: 8,
              padding: "4px 12px",
              background: "#6b7280",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
        </div>
      )}
      {novoUserCreds && (
        <div
          className="paics-success"
          style={{ padding: 14, borderRadius: 6, marginBottom: 20 }}
        >
          <strong>Usuário criado!</strong> Compartilhe as credenciais:
          <pre
            className="paics-card"
            style={{ marginTop: 8, padding: 8, borderRadius: 4 }}
          >{`Usuário: ${novoUserCreds.username}\nE-mail: ${novoUserCreds.email}\nSenha temporária: ${novoUserCreds.senha_temporaria}`}</pre>
          <button
            onClick={() => setNovoUserCreds(null)}
            style={{
              marginTop: 8,
              padding: "4px 12px",
              background: "#6b7280",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <h3 style={{ marginBottom: 12 }}>Clínicas e Usuários</h3>
        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            marginBottom: 16,
          }}
        >
          <button
            onClick={() => {
              setShowClinicaForm(true);
              setShowForm(false);
            }}
            style={{ ...styleBtn, background: "#16a34a" }}
          >
            + Nova clínica (com conta de acesso)
          </button>
          <button
            onClick={() => {
              setShowForm(true);
              setShowClinicaForm(false);
            }}
            style={{ ...styleBtn, background: "#16a34a" }}
          >
            + Novo usuário
          </button>
        </div>
        {showClinicaForm && (
          <div
            style={{ width: "100%", marginBottom: 24, boxSizing: "border-box" }}
          >
            <form
              onSubmit={handleCriarClinicaCompleta}
              className="paics-card"
              style={{ width: "100%", padding: 24, borderRadius: 8 }}
            >
              <h4 style={{ marginTop: 0 }}>
                Cadastrar clínica e conta de acesso
              </h4>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <div>
                  <label>Nome da clínica *</label>
                  <input
                    value={clinicaForm.nome}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, nome: e.target.value })
                    }
                    required
                    style={styleInput}
                  />
                </div>
                <div>
                  <label>CNPJ</label>
                  <input
                    value={clinicaForm.cnpj}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, cnpj: e.target.value })
                    }
                    style={styleInput}
                  />
                </div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label>Endereço (busca por CEP)</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    value={clinicaForm.cep}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, cep: e.target.value })
                    }
                    placeholder="00000-000"
                    style={{ flex: 1, ...styleInput }}
                  />
                  <button
                    type="button"
                    onClick={handleBuscarCep}
                    disabled={buscandoCep}
                    style={{
                      padding: "8px 16px",
                      background: "#6b7280",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {buscandoCep ? "Buscando..." : "Buscar CEP"}
                  </button>
                </div>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(0, 2fr) minmax(80px, 0.5fr)",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <div>
                  <label>Logradouro</label>
                  <input
                    value={clinicaForm.logradouro}
                    onChange={(e) =>
                      setClinicaForm({
                        ...clinicaForm,
                        logradouro: e.target.value,
                      })
                    }
                    placeholder="Rua, Av."
                    style={styleInput}
                  />
                </div>
                <div>
                  <label>Número</label>
                  <input
                    value={clinicaForm.numero}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, numero: e.target.value })
                    }
                    style={styleInput}
                  />
                </div>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <div>
                  <label>Bairro</label>
                  <input
                    value={clinicaForm.bairro}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, bairro: e.target.value })
                    }
                    style={styleInput}
                  />
                </div>
                <div>
                  <label>Cidade</label>
                  <input
                    value={clinicaForm.cidade}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, cidade: e.target.value })
                    }
                    style={styleInput}
                  />
                </div>
                <div>
                  <label>UF</label>
                  <input
                    value={clinicaForm.uf}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, uf: e.target.value })
                    }
                    style={styleInput}
                  />
                </div>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <div>
                  <label>Telefone</label>
                  <input
                    value={clinicaForm.telefone}
                    onChange={(e) =>
                      setClinicaForm({
                        ...clinicaForm,
                        telefone: e.target.value,
                      })
                    }
                    style={styleInput}
                  />
                </div>
                <div>
                  <label>E-mail *</label>
                  <input
                    type="email"
                    value={clinicaForm.email}
                    onChange={(e) =>
                      setClinicaForm({ ...clinicaForm, email: e.target.value })
                    }
                    required
                    style={styleInput}
                  />
                </div>
              </div>
              <div
                style={{
                  borderTop: "1px solid #e5e7eb",
                  paddingTop: 16,
                  marginTop: 16,
                }}
              >
                <h5 style={{ marginBottom: 12 }}>
                  Conta de acesso (login da clínica)
                </h5>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 12,
                    marginBottom: 12,
                  }}
                >
                  <div>
                    <label>Usuário para login *</label>
                    <input
                      value={clinicaForm.username}
                      onChange={(e) =>
                        setClinicaForm({
                          ...clinicaForm,
                          username: e.target.value,
                        })
                      }
                      required
                      style={styleInput}
                    />
                  </div>
                  <div>
                    <label>Senha temporária *</label>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        type="text"
                        value={clinicaForm.senha_temporaria}
                        onChange={(e) =>
                          setClinicaForm({
                            ...clinicaForm,
                            senha_temporaria: e.target.value,
                          })
                        }
                        required
                        minLength={6}
                        placeholder="Digite ou clique em Gerar"
                        style={{ flex: 1, ...styleInput }}
                      />
                      <button
                        type="button"
                        onClick={handleGerarSenhaClinica}
                        style={{
                          padding: "8px 12px",
                          background: "#6b7280",
                          color: "#fff",
                          border: "none",
                          borderRadius: 6,
                          cursor: "pointer",
                          whiteSpace: "nowrap",
                        }}
                      >
                        Gerar
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="submit"
                  disabled={criandoClinica}
                  style={{ ...styleBtn, background: "#16a34a" }}
                >
                  {criandoClinica ? "Criando..." : "Criar clínica e conta"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowClinicaForm(false)}
                  style={{
                    padding: "8px 16px",
                    background: "#6b7280",
                    color: "#fff",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}
        {showForm && (
          <div
            style={{ width: "100%", marginBottom: 24, boxSizing: "border-box" }}
          >
            <form
              onSubmit={handleCriarUsuario}
              className="paics-card"
              style={{ width: "100%", padding: 24, borderRadius: 8 }}
            >
              <h4 style={{ marginTop: 0 }}>
                Cadastrar usuário (senha temporária)
              </h4>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <div>
                  <label>Nome *</label>
                  <input
                    value={form.nome}
                    onChange={(e) => setForm({ ...form, nome: e.target.value })}
                    required
                    style={styleInput}
                  />
                </div>
                <div>
                  <label>Usuário (login) *</label>
                  <input
                    value={form.username}
                    onChange={(e) =>
                      setForm({ ...form, username: e.target.value })
                    }
                    required
                    style={styleInput}
                  />
                </div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label>E-mail *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                  style={styleInput}
                />
              </div>
              <div style={{ marginBottom: 12 }}>
                <label>Senha temporária * (mín. 6 caracteres)</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="text"
                    value={form.senha_temporaria}
                    onChange={(e) =>
                      setForm({ ...form, senha_temporaria: e.target.value })
                    }
                    required
                    minLength={6}
                    placeholder="Digite ou clique em Gerar"
                    style={{ flex: 1, ...styleInput }}
                  />
                  <button
                    type="button"
                    onClick={handleGerarSenha}
                    style={{
                      padding: "8px 12px",
                      background: "#6b7280",
                      color: "#fff",
                      border: "none",
                      borderRadius: 6,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Gerar
                  </button>
                </div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <label>Tipo</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  style={styleInput}
                >
                  <option value="user">Cliente</option>
                  <option value="admin">Administrador</option>
                </select>
              </div>
              {form.role === "user" && (
                <div style={{ marginBottom: 12 }}>
                  <label>Clínica</label>
                  <select
                    value={form.clinica_id}
                    onChange={(e) =>
                      setForm({ ...form, clinica_id: e.target.value })
                    }
                    style={styleInput}
                  >
                    <option value="">Nenhuma</option>
                    {clinicas.map((clin) => (
                      <option key={clin.id} value={clin.id}>
                        {clin.nome}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="submit"
                  disabled={criando}
                  style={{
                    padding: "8px 16px",
                    background: "#16a34a",
                    color: "#fff",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                >
                  {criando ? "Criando..." : "Criar"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  style={{
                    padding: "8px 16px",
                    background: "#6b7280",
                    color: "#fff",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}
        {loading ? (
          <p>Carregando...</p>
        ) : (
          <div
            className="paics-card"
            style={{ borderRadius: 8, overflow: "hidden", marginTop: 20 }}
          >
            <div className="paics-table-wrap">
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 900 }}>
              <thead>
                <tr
                  className="paics-stats"
                  style={{ borderBottom: "1px solid var(--border)" }}
                >
                  <th style={{ padding: 10, textAlign: "left" }}>Tipo</th>
                  <th style={{ padding: 10, textAlign: "left" }}>Nome</th>
                  <th style={{ padding: 10, textAlign: "left" }}>Usuário</th>
                  <th style={{ padding: 10, textAlign: "left" }}>E-mail</th>
                  <th style={{ padding: 10, textAlign: "left" }}>CNPJ</th>
                  <th style={{ padding: 10, textAlign: "left" }}>Endereço</th>
                  <th style={{ padding: 10, textAlign: "left" }}>
                    Veterinários
                  </th>
                  <th style={{ padding: 10, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 10, textAlign: "left" }}>Ações</th>
                </tr>
                <tr
                  className="paics-stats"
                  style={{ borderBottom: "1px solid var(--border)" }}
                >
                  <th style={{ padding: 6 }}>
                    <select
                      value={filtros.tipo}
                      onChange={(e) =>
                        setFiltros((f) => ({ ...f, tipo: e.target.value }))
                      }
                      style={{
                        width: "100%",
                        padding: 6,
                        fontSize: "0.85rem",
                        border: "1px solid #d1d5db",
                        borderRadius: 4,
                      }}
                    >
                      <option value="">Todos</option>
                      <option value="admin">Admin</option>
                      <option value="user">Clínica</option>
                    </select>
                  </th>
                  <th style={{ padding: 6 }}>
                    <input
                      type="text"
                      placeholder="Filtrar..."
                      value={filtros.nome}
                      onChange={(e) =>
                        setFiltros((f) => ({ ...f, nome: e.target.value }))
                      }
                      style={{
                        width: "100%",
                        padding: 6,
                        fontSize: "0.85rem",
                        border: "1px solid #d1d5db",
                        borderRadius: 4,
                      }}
                    />
                  </th>
                  <th style={{ padding: 6 }}>
                    <input
                      type="text"
                      placeholder="Filtrar..."
                      value={filtros.usuario}
                      onChange={(e) =>
                        setFiltros((f) => ({ ...f, usuario: e.target.value }))
                      }
                      style={{
                        width: "100%",
                        padding: 6,
                        fontSize: "0.85rem",
                        border: "1px solid #d1d5db",
                        borderRadius: 4,
                      }}
                    />
                  </th>
                  <th style={{ padding: 6 }}>
                    <input
                      type="text"
                      placeholder="Filtrar..."
                      value={filtros.email}
                      onChange={(e) =>
                        setFiltros((f) => ({ ...f, email: e.target.value }))
                      }
                      style={{
                        width: "100%",
                        padding: 6,
                        fontSize: "0.85rem",
                        border: "1px solid #d1d5db",
                        borderRadius: 4,
                      }}
                    />
                  </th>
                  <th style={{ padding: 6 }} />
                  <th style={{ padding: 6 }}>
                    <input
                      type="text"
                      placeholder="Filtrar..."
                      value={filtros.clinica}
                      onChange={(e) =>
                        setFiltros((f) => ({ ...f, clinica: e.target.value }))
                      }
                      style={{
                        width: "100%",
                        padding: 6,
                        fontSize: "0.85rem",
                        border: "1px solid #d1d5db",
                        borderRadius: 4,
                      }}
                    />
                  </th>
                  <th style={{ padding: 6 }} />
                  <th style={{ padding: 6 }}>
                    <select
                      value={filtros.status}
                      onChange={(e) =>
                        setFiltros((f) => ({ ...f, status: e.target.value }))
                      }
                      style={{
                        width: "100%",
                        padding: 6,
                        fontSize: "0.85rem",
                        border: "1px solid #d1d5db",
                        borderRadius: 4,
                      }}
                    >
                      <option value="">Todos</option>
                      <option value="ativo">Ativo</option>
                      <option value="inativo">Inativo</option>
                    </select>
                  </th>
                  <th style={{ padding: 6 }} />
                </tr>
              </thead>
              <tbody>
                {(!filtros.tipo || filtros.tipo.toLowerCase() === "admin") &&
                  usuariosAdmin.length > 0 && (
                    <tr
                      className="paics-stats"
                      style={{
                        borderTop: "2px solid var(--border)",
                        borderBottom: "2px solid var(--border)",
                        background: "rgba(37, 99, 235, 0.08)",
                      }}
                    >
                      <td
                        colSpan={9}
                        style={{
                          padding: "12px 16px",
                          fontWeight: 700,
                          color: "var(--text)",
                          fontSize: "0.95rem",
                          letterSpacing: "0.02em",
                        }}
                      >
                        Administradores
                      </td>
                    </tr>
                  )}
                {(!filtros.tipo || filtros.tipo.toLowerCase() === "admin") &&
                  usuariosAdmin.map((u) => (
                    <React.Fragment key={u.id}>
                      <tr style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: 10 }}>Admin</td>
                        <td style={{ padding: 10 }}>{u.nome}</td>
                        <td style={{ padding: 10 }}>{u.username}</td>
                        <td style={{ padding: 10 }}>{u.email}</td>
                        <td style={{ padding: 10 }}>—</td>
                        <td style={{ padding: 10 }}>—</td>
                        <td style={{ padding: 10 }}>—</td>
                        <td style={{ padding: 10 }}>
                          {u.ativo ? "Ativo" : "Inativo"}
                        </td>
                        <td
                          style={{
                            padding: 10,
                            display: "flex",
                            gap: 8,
                            flexWrap: "wrap",
                          }}
                        >
                          <button
                            onClick={() => setViewingUserId(u.id)}
                            style={{
                              padding: "4px 10px",
                              background: "#4b5563",
                              color: "#fff",
                              border: "none",
                              borderRadius: 4,
                              cursor: "pointer",
                              fontSize: "0.85rem",
                            }}
                          >
                            Ver detalhes
                          </button>
                          <button
                            onClick={() => handleEditar(u)}
                            style={{
                              padding: "4px 10px",
                              background: "#2563eb",
                              color: "#fff",
                              border: "none",
                              borderRadius: 4,
                              cursor: "pointer",
                              fontSize: "0.85rem",
                            }}
                          >
                            Editar
                          </button>
                          <button
                            onClick={() => handleExcluir(u.id)}
                            disabled={
                              deletandoId === u.id || u.id === currentUserId
                            }
                            style={{
                              padding: "4px 10px",
                              background: "#dc2626",
                              color: "#fff",
                              border: "none",
                              borderRadius: 4,
                              cursor: "pointer",
                              fontSize: "0.85rem",
                            }}
                          >
                            {confirmDeleteId === u.id
                              ? "Confirma?"
                              : deletandoId === u.id
                                ? "Excluindo..."
                                : "Excluir"}
                          </button>
                        </td>
                      </tr>
                      {editingId === u.id && editForm && (
                        <tr style={{ background: "var(--bg-muted)" }}>
                          <td colSpan={9} style={{ padding: 16 }}>
                            <form
                              onSubmit={handleSalvarEdicao}
                              style={{
                                display: "grid",
                                gridTemplateColumns:
                                  "repeat(auto-fill, minmax(180px, 1fr))",
                                gap: 12,
                                alignItems: "end",
                              }}
                            >
                              <div>
                                <label>Nome</label>
                                <input
                                  value={editForm.nome}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      nome: e.target.value,
                                    })
                                  }
                                  required
                                  style={styleInput}
                                />
                              </div>
                              <div>
                                <label>Usuário</label>
                                <input
                                  value={editForm.username}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      username: e.target.value,
                                    })
                                  }
                                  required
                                  style={styleInput}
                                />
                              </div>
                              <div>
                                <label>E-mail</label>
                                <input
                                  type="email"
                                  value={editForm.email}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      email: e.target.value,
                                    })
                                  }
                                  required
                                  style={styleInput}
                                />
                              </div>
                              <div>
                                <label>Tipo</label>
                                <select
                                  value={editForm.role}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      role: e.target.value,
                                    })
                                  }
                                  style={styleInput}
                                >
                                  <option value="user">Cliente</option>
                                  <option value="admin">Admin</option>
                                </select>
                              </div>
                              <div>
                                <label>Ativo</label>
                                <label
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 8,
                                  }}
                                >
                                  <input
                                    type="checkbox"
                                    checked={editForm.ativo}
                                    onChange={(e) =>
                                      setEditForm({
                                        ...editForm,
                                        ativo: e.target.checked,
                                      })
                                    }
                                  />
                                  Ativo
                                </label>
                              </div>
                              {editForm.role === "user" && (
                                <div>
                                  <label>Clínica</label>
                                  <select
                                    value={editForm.clinica_id}
                                    onChange={(e) =>
                                      setEditForm({
                                        ...editForm,
                                        clinica_id: e.target.value,
                                      })
                                    }
                                    style={styleInput}
                                  >
                                    <option value="">Nenhuma</option>
                                    {clinicas.map((clin) => (
                                      <option key={clin.id} value={clin.id}>
                                        {clin.nome}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                              )}
                              <div style={{ display: "flex", gap: 8 }}>
                                <button
                                  type="submit"
                                  disabled={salvando}
                                  style={{
                                    padding: "8px 16px",
                                    background: "#16a34a",
                                    color: "#fff",
                                    border: "none",
                                    borderRadius: 6,
                                    cursor: "pointer",
                                  }}
                                >
                                  {salvando ? "Salvando..." : "Salvar"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingId(null);
                                    setEditForm(null);
                                  }}
                                  style={{
                                    padding: "8px 16px",
                                    background: "#6b7280",
                                    color: "#fff",
                                    border: "none",
                                    borderRadius: 6,
                                    cursor: "pointer",
                                  }}
                                >
                                  Cancelar
                                </button>
                              </div>
                            </form>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                {(!filtros.tipo || filtros.tipo.toLowerCase() === "user") &&
                  clinicasFiltradas.length > 0 && (
                    <tr
                      className="paics-stats"
                      style={{
                        borderTop: "2px solid var(--border)",
                        borderBottom: "2px solid var(--border)",
                        background: "rgba(22, 163, 74, 0.08)",
                      }}
                    >
                      <td
                        colSpan={9}
                        style={{
                          padding: "12px 16px",
                          fontWeight: 700,
                          color: "var(--text)",
                          fontSize: "0.95rem",
                          letterSpacing: "0.02em",
                        }}
                      >
                        Clínicas e Veterinários
                      </td>
                    </tr>
                  )}
                {(!filtros.tipo || filtros.tipo.toLowerCase() === "user") &&
                  clinicasFiltradas.map((c) => {
                    const u = getUsuarioByClinica(c.id);
                    const vets = getVets(c.id);
                    return (
                      <React.Fragment key={c.id}>
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: 10 }}>Clínica</td>
                          <td style={{ padding: 10 }}>
                            {c.nome}
                            {!c.ativa && " (inativa)"}
                          </td>
                          <td style={{ padding: 10 }}>{u?.username ?? "—"}</td>
                          <td style={{ padding: 10 }}>
                            {u?.email ?? c.email ?? "—"}
                          </td>
                          <td style={{ padding: 10 }}>{c.cnpj || "—"}</td>
                          <td
                            style={{
                              padding: 10,
                              maxWidth: 180,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                            title={
                              [c.endereco, c.numero, c.bairro, c.cidade, c.cep]
                                .filter(Boolean)
                                .join(", ") || undefined
                            }
                          >
                            {[c.endereco, c.numero, c.bairro, c.cidade]
                              .filter(Boolean)
                              .join(", ") || "—"}
                          </td>
                          <td style={{ padding: 10 }}>
                            {veterinariosCache[c.id] ? (
                              `${vets.length} vet(s)`
                            ) : (
                              <button
                                type="button"
                                onClick={() => loadVets(c.id)}
                                style={{
                                  padding: "2px 6px",
                                  fontSize: "0.8rem",
                                  background: "var(--bg-muted)",
                                  border: "none",
                                  borderRadius: 4,
                                  cursor: "pointer",
                                  color: "var(--text)",
                                }}
                              >
                                Carregar
                              </button>
                            )}
                          </td>
                          <td style={{ padding: 10 }}>
                            {u ? (u.ativo ? "Ativo" : "Inativo") : "—"}
                          </td>
                          <td
                            style={{
                              padding: 10,
                              display: "flex",
                              gap: 8,
                              flexWrap: "wrap",
                            }}
                          >
                            {u && (
                              <button
                                onClick={() => setViewingUserId(u.id)}
                                style={{
                                  padding: "4px 10px",
                                  background: "#4b5563",
                                  color: "#fff",
                                  border: "none",
                                  borderRadius: 4,
                                  cursor: "pointer",
                                  fontSize: "0.85rem",
                                }}
                              >
                                Ver detalhes
                              </button>
                            )}
                            <button
                              onClick={() => handleEditarClinica(c)}
                              style={{
                                padding: "4px 10px",
                                background: "#2563eb",
                                color: "#fff",
                                border: "none",
                                borderRadius: 4,
                                cursor: "pointer",
                                fontSize: "0.85rem",
                              }}
                            >
                              Editar clínica
                            </button>
                            <button
                              onClick={() => handleExcluirClinica(c.id)}
                              disabled={
                                deletandoClinicaId === c.id ||
                                (u?.id === currentUserId)
                              }
                              style={{
                                padding: "4px 10px",
                                background: "#dc2626",
                                color: "#fff",
                                border: "none",
                                borderRadius: 4,
                                cursor: "pointer",
                                fontSize: "0.85rem",
                              }}
                            >
                              {confirmDeleteClinicaId === c.id
                                ? "Confirma?"
                                : deletandoClinicaId === c.id
                                  ? "Excluindo..."
                                  : "Excluir"}
                            </button>
                          </td>
                        </tr>
                        {editClinicaId === c.id && editClinicaForm && (
                          <tr style={{ background: "var(--bg-muted)" }}>
                            <td colSpan={9} style={{ padding: 16 }}>
                              <form onSubmit={handleSalvarClinica}>
                                <h4 style={{ marginTop: 0, marginBottom: 12 }}>
                                  Editar clínica: {c.nome}
                                </h4>
                                <div
                                  style={{
                                    display: "grid",
                                    gridTemplateColumns:
                                      "repeat(auto-fill, minmax(180px, 1fr))",
                                    gap: 12,
                                    marginBottom: 12,
                                  }}
                                >
                                  <div>
                                    <label>CEP</label>
                                    <div style={{ display: "flex", gap: 8 }}>
                                      <input
                                        value={
                                          editCepBusca || editClinicaForm.cep
                                        }
                                        onChange={(e) =>
                                          setEditCepBusca(e.target.value)
                                        }
                                        placeholder="00000-000"
                                        style={{ flex: 1, ...styleInput }}
                                      />
                                      <button
                                        type="button"
                                        onClick={handleBuscarCepEdit}
                                        style={{
                                          padding: "8px 12px",
                                          background: "#6b7280",
                                          color: "#fff",
                                          border: "none",
                                          borderRadius: 6,
                                          cursor: "pointer",
                                        }}
                                      >
                                        Buscar CEP
                                      </button>
                                    </div>
                                  </div>
                                  <div>
                                    <label>Nome *</label>
                                    <input
                                      value={editClinicaForm.nome}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          nome: e.target.value,
                                        })
                                      }
                                      required
                                      style={styleInput}
                                    />
                                  </div>
                                  <div>
                                    <label>CNPJ</label>
                                    <input
                                      value={editClinicaForm.cnpj}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          cnpj: e.target.value,
                                        })
                                      }
                                      style={styleInput}
                                    />
                                  </div>
                                  <div>
                                    <label>Logradouro</label>
                                    <input
                                      value={editClinicaForm.endereco}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          endereco: e.target.value,
                                        })
                                      }
                                      style={styleInput}
                                    />
                                  </div>
                                  <div>
                                    <label>Número</label>
                                    <input
                                      value={editClinicaForm.numero}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          numero: e.target.value,
                                        })
                                      }
                                      style={styleInput}
                                    />
                                  </div>
                                  <div>
                                    <label>Bairro</label>
                                    <input
                                      value={editClinicaForm.bairro}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          bairro: e.target.value,
                                        })
                                      }
                                      style={styleInput}
                                    />
                                  </div>
                                  <div>
                                    <label>Cidade</label>
                                    <input
                                      value={editClinicaForm.cidade}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          cidade: e.target.value,
                                        })
                                      }
                                      style={styleInput}
                                    />
                                  </div>
                                  <div>
                                    <label>Telefone</label>
                                    <input
                                      value={editClinicaForm.telefone}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          telefone: e.target.value,
                                        })
                                      }
                                      style={styleInput}
                                    />
                                  </div>
                                  <div>
                                    <label>E-mail</label>
                                    <input
                                      type="email"
                                      value={editClinicaForm.email}
                                      onChange={(e) =>
                                        setEditClinicaForm({
                                          ...editClinicaForm,
                                          email: e.target.value,
                                        })
                                      }
                                      style={styleInput}
                                    />
                                  </div>
                                </div>
                                <div
                                  style={{
                                    marginBottom: 12,
                                    marginTop: 16,
                                    paddingTop: 16,
                                    borderTop: "1px solid var(--border)",
                                  }}
                                >
                                  <strong
                                    style={{
                                      display: "block",
                                      marginBottom: 8,
                                      color: "var(--text)",
                                      fontSize: "0.95rem",
                                    }}
                                  >
                                    Veterinários
                                  </strong>
                                  {vetAddClinicaId === c.id ? (
                                    <div
                                      style={{
                                        display: "flex",
                                        flexWrap: "wrap",
                                        gap: 8,
                                        alignItems: "flex-end",
                                        marginTop: 8,
                                      }}
                                    >
                                      <div>
                                        <label
                                          style={{
                                            display: "block",
                                            fontSize: "0.85rem",
                                          }}
                                        >
                                          Nome *
                                        </label>
                                        <input
                                          value={vetForm.nome}
                                          onChange={(e) =>
                                            setVetForm({
                                              ...vetForm,
                                              nome: e.target.value,
                                            })
                                          }
                                          required
                                          placeholder="Nome"
                                          style={{ ...styleInput, width: 140 }}
                                        />
                                      </div>
                                      <div>
                                        <label
                                          style={{
                                            display: "block",
                                            fontSize: "0.85rem",
                                          }}
                                        >
                                          CRMV *
                                        </label>
                                        <input
                                          value={vetForm.crmv}
                                          onChange={(e) =>
                                            setVetForm({
                                              ...vetForm,
                                              crmv: e.target.value,
                                            })
                                          }
                                          required
                                          placeholder="CRMV"
                                          style={{ ...styleInput, width: 100 }}
                                        />
                                      </div>
                                      <div>
                                        <label
                                          style={{
                                            display: "block",
                                            fontSize: "0.85rem",
                                          }}
                                        >
                                          E-mail
                                        </label>
                                        <input
                                          value={vetForm.email}
                                          onChange={(e) =>
                                            setVetForm({
                                              ...vetForm,
                                              email: e.target.value,
                                            })
                                          }
                                          placeholder="E-mail"
                                          style={{ ...styleInput, width: 180 }}
                                        />
                                      </div>
                                      <button
                                        type="button"
                                        disabled={criandoVet}
                                        onClick={(e) => {
                                          e.preventDefault();
                                          handleCriarVet(e as unknown as React.FormEvent);
                                        }}
                                        style={{
                                          padding: "8px 12px",
                                          background: "#16a34a",
                                          color: "#fff",
                                          border: "none",
                                          borderRadius: 6,
                                          cursor: "pointer",
                                        }}
                                      >
                                        {criandoVet
                                          ? "Salvando..."
                                          : "Adicionar"}
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => setVetAddClinicaId(null)}
                                        style={{
                                          padding: "8px 12px",
                                          background: "#6b7280",
                                          color: "#fff",
                                          border: "none",
                                          borderRadius: 6,
                                          cursor: "pointer",
                                        }}
                                      >
                                        Cancelar
                                      </button>
                                    </div>
                                  ) : (
                                    <>
                                      {vets.length > 0 && (
                                        <ul
                                          style={{
                                            margin: "8px 0",
                                            paddingLeft: 20,
                                          }}
                                        >
                                          {vets.map((v) => (
                                            <li
                                              key={v.id}
                                              style={{ marginBottom: 4 }}
                                            >
                                              {v.nome} — CRMV: {v.crmv}{" "}
                                              {v.email && `(${v.email})`}
                                            </li>
                                          ))}
                                        </ul>
                                      )}
                                      <button
                                        type="button"
                                        onClick={() => handleAddVet(c.id)}
                                        style={{
                                          padding: "6px 12px",
                                          background: "#16a34a",
                                          color: "#fff",
                                          border: "none",
                                          borderRadius: 6,
                                          cursor: "pointer",
                                          fontSize: "0.85rem",
                                        }}
                                      >
                                        + Adicionar veterinário
                                      </button>
                                    </>
                                  )}
                                </div>
                                <div style={{ display: "flex", gap: 8 }}>
                                  <button
                                    type="submit"
                                    disabled={salvandoClinica}
                                    style={{
                                      ...styleBtn,
                                      background: "#16a34a",
                                    }}
                                  >
                                    {salvandoClinica ? "Salvando..." : "Salvar"}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setEditClinicaId(null);
                                      setEditClinicaForm(null);
                                      setVetAddClinicaId(null);
                                    }}
                                    style={{
                                      padding: "8px 16px",
                                      background: "#6b7280",
                                      color: "#fff",
                                      border: "none",
                                      borderRadius: 6,
                                      cursor: "pointer",
                                    }}
                                  >
                                    Cancelar
                                  </button>
                                </div>
                              </form>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                {(!filtros.tipo || filtros.tipo.toLowerCase() === "admin"
                  ? usuariosAdmin.length
                  : 0) +
                  (!filtros.tipo || filtros.tipo.toLowerCase() === "user"
                    ? clinicasFiltradas.length
                    : 0) ===
                  0 && (
                  <tr>
                    <td
                      colSpan={9}
                      style={{
                        padding: 24,
                        textAlign: "center",
                        color: "var(--text-muted)",
                      }}
                    >
                      Nenhum resultado encontrado com os filtros aplicados.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            </div>
          </div>
        )}
      </div>

      {/* Painel de detalhes do usuário */}
      {viewingUserId && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 24,
          }}
          onClick={() => setViewingUserId(null)}
        >
          <div
            className="paics-card paics-modal"
            style={{
              borderRadius: 12,
              maxWidth: 560,
              width: "100%",
              maxHeight: "90vh",
              overflow: "auto",
              boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                padding: 24,
                borderBottom: "1px solid var(--border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <h3 style={{ margin: 0, fontSize: "1.25rem" }}>
                Detalhes do usuário
              </h3>
              <button
                onClick={() => setViewingUserId(null)}
                style={{
                  padding: "6px 12px",
                  background: "#6b7280",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                }}
              >
                Fechar
              </button>
            </div>
            <div style={{ padding: 24 }}>
              {loadingDetail ? (
                <p style={{ color: "var(--text-muted)" }}>Carregando...</p>
              ) : detailUsuario ? (
                <>
                  {editingId === viewingUserId && editForm ? (
                    <form
                      onSubmit={handleSalvarEdicao}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 12,
                      }}
                    >
                      <div>
                        <label>Nome</label>
                        <input
                          value={editForm.nome}
                          onChange={(e) =>
                            setEditForm({ ...editForm, nome: e.target.value })
                          }
                          required
                          style={styleInput}
                        />
                      </div>
                      <div>
                        <label>Usuário</label>
                        <input
                          value={editForm.username}
                          onChange={(e) =>
                            setEditForm({
                              ...editForm,
                              username: e.target.value,
                            })
                          }
                          required
                          style={styleInput}
                        />
                      </div>
                      <div>
                        <label>E-mail</label>
                        <input
                          type="email"
                          value={editForm.email}
                          onChange={(e) =>
                            setEditForm({ ...editForm, email: e.target.value })
                          }
                          required
                          style={styleInput}
                        />
                      </div>
                      <div>
                        <label>Tipo</label>
                        <select
                          value={editForm.role}
                          onChange={(e) =>
                            setEditForm({ ...editForm, role: e.target.value })
                          }
                          style={styleInput}
                        >
                          <option value="user">Cliente</option>
                          <option value="admin">Admin</option>
                        </select>
                      </div>
                      <div>
                        <label>Ativo</label>
                        <label
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={editForm.ativo}
                            onChange={(e) =>
                              setEditForm({
                                ...editForm,
                                ativo: e.target.checked,
                              })
                            }
                          />
                          Ativo
                        </label>
                      </div>
                      {editForm.role === "user" && (
                        <div>
                          <label>Clínica</label>
                          <select
                            value={editForm.clinica_id}
                            onChange={(e) =>
                              setEditForm({
                                ...editForm,
                                clinica_id: e.target.value,
                              })
                            }
                            style={styleInput}
                          >
                            <option value="">Nenhuma</option>
                            {clinicas.map((clin) => (
                              <option key={clin.id} value={clin.id}>
                                {clin.nome}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      <div
                        style={{
                          gridColumn: "1 / -1",
                          display: "flex",
                          gap: 8,
                        }}
                      >
                        <button
                          type="submit"
                          disabled={salvando}
                          style={{
                            padding: "8px 16px",
                            background: "#16a34a",
                            color: "#fff",
                            border: "none",
                            borderRadius: 6,
                            cursor: "pointer",
                          }}
                        >
                          {salvando ? "Salvando..." : "Salvar"}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingId(null);
                            setEditForm(null);
                          }}
                          style={{
                            padding: "8px 16px",
                            background: "#6b7280",
                            color: "#fff",
                            border: "none",
                            borderRadius: 6,
                            cursor: "pointer",
                          }}
                        >
                          Cancelar
                        </button>
                      </div>
                    </form>
                  ) : (
                    <>
                      <dl
                        style={{ margin: "0 0 20px", display: "grid", gap: 8 }}
                      >
                        <div>
                          <dt
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--text-muted)",
                            }}
                          >
                            Nome
                          </dt>
                          <dd style={{ margin: 0 }}>{detailUsuario.nome}</dd>
                        </div>
                        <div>
                          <dt
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--text-muted)",
                            }}
                          >
                            Usuário
                          </dt>
                          <dd style={{ margin: 0 }}>
                            {detailUsuario.username}
                          </dd>
                        </div>
                        <div>
                          <dt
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--text-muted)",
                            }}
                          >
                            E-mail
                          </dt>
                          <dd style={{ margin: 0 }}>{detailUsuario.email}</dd>
                        </div>
                        <div>
                          <dt
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--text-muted)",
                            }}
                          >
                            Tipo
                          </dt>
                          <dd style={{ margin: 0 }}>{detailUsuario.role}</dd>
                        </div>
                        <div>
                          <dt
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--text-muted)",
                            }}
                          >
                            Clínica
                          </dt>
                          <dd style={{ margin: 0 }}>
                            {detailUsuario.clinica_nome || "—"}
                          </dd>
                        </div>
                        {detailUsuario.clinica_id && (
                          <div
                            style={{
                              gridColumn: "1 / -1",
                              marginTop: 12,
                              paddingTop: 12,
                              borderTop: "1px solid var(--border)",
                            }}
                          >
                            <dt
                              style={{
                                fontSize: "0.8rem",
                                color: "var(--text-muted)",
                                marginBottom: 8,
                              }}
                            >
                              Veterinários cadastrados na clínica
                            </dt>
                            <dd style={{ margin: 0 }}>
                              {veterinariosCache[detailUsuario.clinica_id] ? (
                                veterinariosCache[detailUsuario.clinica_id]
                                  .length > 0 ? (
                                  <ul
                                    style={{
                                      margin: 0,
                                      paddingLeft: 20,
                                      listStyle: "disc",
                                    }}
                                  >
                                    {veterinariosCache[
                                      detailUsuario.clinica_id
                                    ].map((v) => (
                                      <li
                                        key={v.id}
                                        style={{ marginBottom: 4 }}
                                      >
                                        {v.nome}
                                        {v.crmv && ` — CRMV: ${v.crmv}`}
                                        {v.email && ` (${v.email})`}
                                      </li>
                                    ))}
                                  </ul>
                                ) : (
                                  <span
                                    style={{
                                      color: "var(--text-muted)",
                                      fontSize: "0.9rem",
                                    }}
                                  >
                                    Nenhum veterinário cadastrado
                                  </span>
                                )
                              ) : (
                                <span
                                  style={{
                                    color: "var(--text-muted)",
                                    fontSize: "0.9rem",
                                  }}
                                >
                                  Carregando...
                                </span>
                              )}
                            </dd>
                          </div>
                        )}
                        <div>
                          <dt
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--text-muted)",
                            }}
                          >
                            Status
                          </dt>
                          <dd style={{ margin: 0 }}>
                            {detailUsuario.ativo !== false
                              ? "Ativo"
                              : "Inativo"}
                          </dd>
                        </div>
                      </dl>
                      <div
                        className="paics-muted"
                        style={{
                          marginBottom: 20,
                          padding: 12,
                          borderRadius: 8,
                        }}
                      >
                        <strong style={{ fontSize: "0.9rem" }}>
                          Estatísticas
                        </strong>
                        <div style={{ marginTop: 8, display: "flex", gap: 16 }}>
                          <span>
                            Requisições: {detailUsuario.total_requisicoes ?? 0}
                          </span>
                          <span>Laudos: {detailUsuario.total_laudos ?? 0}</span>
                          <span>
                            Liberados: {detailUsuario.laudos_liberados ?? 0}
                          </span>
                        </div>
                      </div>
                      {detailUsuario.primeiro_acesso &&
                        detailUsuario.senha_temporaria && (
                          <div
                            className="paics-muted"
                            style={{
                              marginBottom: 20,
                              padding: 12,
                              borderRadius: 8,
                            }}
                          >
                            <strong style={{ fontSize: "0.9rem" }}>
                              Senha temporária (primeiro acesso pendente)
                            </strong>
                            <pre
                              className="paics-card"
                              style={{
                                marginTop: 8,
                                padding: 8,
                                borderRadius: 4,
                                overflow: "auto",
                              }}
                            >
                              {detailUsuario.senha_temporaria}
                            </pre>
                          </div>
                        )}
                      <div
                        style={{ display: "flex", gap: 8, flexWrap: "wrap" }}
                      >
                        <button
                          onClick={() => handleEditar(detailUsuario)}
                          style={{
                            padding: "8px 16px",
                            background: "#2563eb",
                            color: "#fff",
                            border: "none",
                            borderRadius: 6,
                            cursor: "pointer",
                          }}
                        >
                          Editar
                        </button>
                        <button
                          onClick={() =>
                            handleToggleAtivo(
                              detailUsuario.id,
                              detailUsuario.ativo !== false,
                            )
                          }
                          style={{
                            padding: "8px 16px",
                            background:
                              detailUsuario.ativo !== false
                                ? "#d97706"
                                : "#16a34a",
                            color: "#fff",
                            border: "none",
                            borderRadius: 6,
                            cursor: "pointer",
                          }}
                        >
                          {detailUsuario.ativo !== false
                            ? "Desativar"
                            : "Ativar"}
                        </button>
                        <button
                          onClick={() => handleExcluir(detailUsuario.id)}
                          disabled={
                            detailUsuario.id === currentUserId ||
                            deletandoId === detailUsuario.id
                          }
                          title={
                            detailUsuario.id === currentUserId
                              ? "Não é possível excluir o próprio usuário"
                              : undefined
                          }
                          style={{
                            padding: "8px 16px",
                            background: "#dc2626",
                            color: "#fff",
                            border: "none",
                            borderRadius: 6,
                            cursor: "pointer",
                          }}
                        >
                          {confirmDeleteId === detailUsuario.id
                            ? "Confirma excluir?"
                            : deletandoId === detailUsuario.id
                              ? "Excluindo..."
                              : "Excluir"}
                        </button>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <p style={{ color: "var(--text-muted)" }}>
                  Usuário não encontrado.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
