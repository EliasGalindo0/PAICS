"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  listExames,
  gerarLaudo,
  excluirExame,
  type Exame,
} from "@/lib/api";
import { hojeISO, diasAtrasISO } from "@/lib/dateUtils";

const STATUS_ORDER: Record<string, number> = { pendente: 0, em_analise: 1, validado: 2, liberado: 3, rejeitado: 4 };

export default function AdminExamesPage() {
  const [exames, setExames] = useState<Exame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [tipoFilter, setTipoFilter] = useState("");
  const [search, setSearch] = useState("");
  const [startDate, setStartDate] = useState(() => diasAtrasISO(30));
  const [endDate, setEndDate] = useState(() => hojeISO());
  const [showAllDates, setShowAllDates] = useState(false);
  const [sortBy, setSortBy] = useState("data_desc");
  const [gerandoId, setGerandoId] = useState<string | null>(null);
  const [gerandoMassa, setGerandoMassa] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<{ ok: number; err: number } | null>(null);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);
  const [confirmExcluirId, setConfirmExcluirId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    const params: Parameters<typeof listExames>[0] = {
      status: statusFilter || undefined,
      tipo_exame: tipoFilter || undefined,
      search: search || undefined,
      limit: 100,
    };
    if (!showAllDates && startDate && endDate) {
      params.start_date = startDate;
      params.end_date = endDate;
    }
    listExames(params)
      .then(setExames)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [statusFilter, tipoFilter, search, startDate, endDate, showAllDates]);

  const examesOrdenados = useMemo(() => {
    const list = [...exames];
    if (sortBy === "data_desc") list.sort((a, b) => (b.created_at_raw || "").localeCompare(a.created_at_raw || ""));
    else if (sortBy === "data_asc") list.sort((a, b) => (a.created_at_raw || "").localeCompare(b.created_at_raw || ""));
    else if (sortBy === "status") list.sort((a, b) => (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99));
    else if (sortBy === "clinica") list.sort((a, b) => (a.clinica || "").localeCompare(b.clinica || ""));
    else if (sortBy === "paciente") list.sort((a, b) => (a.paciente || "").localeCompare(b.paciente || ""));
    return list;
  }, [exames, sortBy]);

  const reqsSemLaudo = useMemo(
    () => examesOrdenados.filter((ex) => !ex.tem_laudo && ex.n_imagens > 0),
    [examesOrdenados],
  );

  const handleGerarLaudo = async (id: string) => {
    setGerandoId(id);
    setError("");
    try {
      await gerarLaudo(id);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGerandoId(null);
    }
  };

  const handleExcluir = async (id: string) => {
    if (confirmExcluirId !== id) {
      setConfirmExcluirId(id);
      return;
    }
    setExcluindoId(id);
    setError("");
    try {
      await excluirExame(id);
      setConfirmExcluirId(null);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setExcluindoId(null);
    }
  };

  const handleGerarMassa = async () => {
    setGerandoMassa(true);
    setError("");
    setBulkMsg(null);
    let ok = 0;
    let err = 0;
    for (const ex of reqsSemLaudo) {
      try {
        await gerarLaudo(ex.id);
        ok++;
      } catch {
        err++;
      }
    }
    setBulkMsg({ ok, err });
    setGerandoMassa(false);
    load();
  };

  const statusBadge = (s: string) => {
    const map: Record<string, { bg: string; color: string }> = {
      liberado: { bg: "#dcfce7", color: "#166534" },
      em_analise: { bg: "#fef3c7", color: "#92400e" },
      validado: { bg: "#dbeafe", color: "#1e40af" },
      pendente: { bg: "#e5e7eb", color: "#374151" },
      rejeitado: { bg: "#fee2e2", color: "#991b1b" },
    };
    const st = map[s] || { bg: "#f3f4f6", color: "#6b7280" };
    return <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: "0.8rem", background: st.bg, color: st.color }}>{s}</span>;
  };

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", marginBottom: "1rem" }}>Exames</h1>
      <div className="paics-filters" style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginBottom: "1rem" }}>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
        >
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="em_analise">Em análise</option>
          <option value="validado">Validado</option>
          <option value="liberado">Liberado</option>
        </select>
        <select
          value={tipoFilter}
          onChange={(e) => setTipoFilter(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
        >
          <option value="">Todos os tipos</option>
          <option value="raio-x">Raio-X</option>
          <option value="ultrassom">Ultrassom</option>
        </select>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <label style={{ fontSize: "0.9rem" }}>Período</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={showAllDates}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
            title="Data inicial"
          />
          <span style={{ fontSize: "0.9rem", color: "#6b7280" }}>até</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={showAllDates}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
            title="Data final"
          />
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: "0.9rem" }}>
          <input type="checkbox" checked={showAllDates} onChange={(e) => setShowAllDates(e.target.checked)} />
          Mostrar todas as datas
        </label>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
        >
          <option value="data_desc">Data (mais recente)</option>
          <option value="data_asc">Data (mais antigo)</option>
          <option value="status">Status</option>
          <option value="clinica">Clínica</option>
          <option value="paciente">Paciente</option>
        </select>
        <input
          type="text"
          placeholder="Buscar..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db", minWidth: 200 }}
        />
      </div>
      {!showAllDates && (
        <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: -8, marginBottom: 12 }}>
          Exibindo requisições de {new Date(startDate + "T12:00:00").toLocaleDateString("pt-BR")} até{" "}
          {new Date(endDate + "T12:00:00").toLocaleDateString("pt-BR")}.
        </p>
      )}
      {error && <div className="paics-error" style={{ padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 6, marginBottom: 12 }}>{error}</div>}
      {bulkMsg && (
        <div className="paics-success" style={{ padding: 10, background: "#dcfce7", color: "#166534", borderRadius: 6, marginBottom: 12 }}>
          Geração em massa concluída: {bulkMsg.ok} laudo(s) gerado(s).
          {bulkMsg.err > 0 && ` ${bulkMsg.err} erro(s).`}
        </div>
      )}
      {reqsSemLaudo.length > 0 && !loading && (
        <div style={{ marginBottom: 16 }}>
          <button
            onClick={handleGerarMassa}
            disabled={gerandoMassa}
            style={{
              padding: "10px 20px",
              background: "#16a34a",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: gerandoMassa ? "not-allowed" : "pointer",
              fontSize: "1rem",
            }}
          >
            {gerandoMassa ? `Gerando ${reqsSemLaudo.length} laudo(s)...` : `Gerar laudos em massa (${reqsSemLaudo.length} pendente(s))`}
          </button>
        </div>
      )}
      {loading ? (
        <p>Carregando...</p>
      ) : (
        <div className="paics-card" style={{ background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", overflow: "hidden" }}>
          <div className="paics-table-wrap">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>ID</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Paciente</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Tutor</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Clínica</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Status</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Tipo</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Imagens</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Laudo</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {examesOrdenados.map((ex) => (
                <tr key={ex.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "10px 12px", fontSize: "0.85rem" }}>{ex.id.slice(-8)}</td>
                  <td style={{ padding: "10px 12px" }}>{ex.paciente}</td>
                  <td style={{ padding: "10px 12px" }}>{ex.tutor}</td>
                  <td style={{ padding: "10px 12px", fontSize: "0.85rem" }}>{ex.clinica || "—"}</td>
                  <td style={{ padding: "10px 12px" }}>{statusBadge(ex.status)}</td>
                  <td style={{ padding: "10px 12px" }}>{ex.tipo_exame}</td>
                  <td style={{ padding: "10px 12px" }}>{ex.n_imagens}</td>
                  <td style={{ padding: "10px 12px" }}>{ex.tem_laudo ? "Sim" : "Não"}</td>
                  <td style={{ padding: "10px 12px", display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <Link
                      href={`/admin/exames/${ex.id}`}
                      style={{ padding: "4px 10px", background: "#1a2d4a", color: "#fff", borderRadius: 6, textDecoration: "none", fontSize: "0.85rem" }}
                    >
                      Abrir
                    </Link>
                    {!ex.tem_laudo && ex.n_imagens > 0 && (
                      <button
                        onClick={() => handleGerarLaudo(ex.id)}
                        disabled={gerandoId === ex.id}
                        style={{ padding: "4px 10px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, cursor: gerandoId === ex.id ? "not-allowed" : "pointer", fontSize: "0.85rem" }}
                      >
                        {gerandoId === ex.id ? "Gerando..." : "Gerar Laudo"}
                      </button>
                    )}
                    <button
                      onClick={() => handleExcluir(ex.id)}
                      disabled={excluindoId === ex.id}
                      style={{ padding: "4px 10px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: excluindoId === ex.id ? "not-allowed" : "pointer", fontSize: "0.85rem" }}
                      title="Excluir requisição (exame solicitado por engano ou em duplicidade)"
                    >
                      {confirmExcluirId === ex.id ? "Confirma?" : excluindoId === ex.id ? "Excluindo..." : "Excluir"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          {examesOrdenados.length === 0 && <p style={{ padding: 24, color: "#6b7280", textAlign: "center" }}>Nenhum exame encontrado.</p>}
        </div>
      )}
    </div>
  );
}
