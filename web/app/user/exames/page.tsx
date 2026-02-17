"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listExames, type Exame } from "@/lib/api";
import { hojeISO, diasAtrasISO } from "@/lib/dateUtils";

const STORAGE_KEY = "paics_last_meus_exames_visit";

export default function UserExamesPage() {
  const [exames, setExames] = useState<Exame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [startDate, setStartDate] = useState(() => diasAtrasISO(30));
  const [endDate, setEndDate] = useState(() => hojeISO());
  const [showAllDates, setShowAllDates] = useState(false);
  const [newlyLiberados, setNewlyLiberados] = useState(0);

  useEffect(() => {
    const params: Parameters<typeof listExames>[0] = {
      status: statusFilter || undefined,
      limit: 100,
    };
    if (!showAllDates && startDate && endDate) {
      params.start_date = startDate;
      params.end_date = endDate;
    }
    const nowIso = new Date().toISOString();
    const lastVisit = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;

    listExames(params)
      .then((data) => {
        setExames(data);
        if (lastVisit && data.length > 0) {
          const lastTs = new Date(lastVisit).getTime();
          const count = data.filter((ex) => {
            if (ex.status !== "liberado" || !ex.liberado_at) return false;
            const libTs = new Date(ex.liberado_at).getTime();
            return libTs >= lastTs;
          }).length;
          setNewlyLiberados(count);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => {
        setLoading(false);
        if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, nowIso);
      });
  }, [statusFilter, startDate, endDate, showAllDates]);

  const statusBadge = (s: string) => {
    const map: Record<string, { bg: string; color: string }> = {
      liberado: { bg: "#dcfce7", color: "#166534" },
      validado: { bg: "#dbeafe", color: "#1e40af" },
      pendente: { bg: "#e5e7eb", color: "#374151" },
    };
    const st = map[s] || { bg: "#f3f4f6", color: "#6b7280" };
    return <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: "0.8rem", background: st.bg, color: st.color }}>{s}</span>;
  };

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", marginBottom: 16 }}>Meus Exames</h1>
      <div className="paics-filters" style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}
        >
          <option value="">Todos</option>
          <option value="pendente">Pendente</option>
          <option value="validado">Validado</option>
          <option value="liberado">Liberados</option>
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
          <input
            type="checkbox"
            checked={showAllDates}
            onChange={(e) => setShowAllDates(e.target.checked)}
          />
          Mostrar todas as datas
        </label>
      </div>
      {newlyLiberados > 0 && (
        <div
          className="paics-success"
          style={{
            padding: 12,
            background: "#dcfce7",
            color: "#166534",
            borderRadius: 6,
            marginBottom: 12,
          }}
        >
          🎉 {newlyLiberados} laudo(s) liberado(s)! Disponível(is) para download abaixo.
        </div>
      )}
      {!showAllDates && (
        <p style={{ fontSize: "0.85rem", color: "#6b7280", marginTop: -8, marginBottom: 12 }}>
          Exibindo requisições de {new Date(startDate + "T12:00:00").toLocaleDateString("pt-BR")} até{" "}
          {new Date(endDate + "T12:00:00").toLocaleDateString("pt-BR")}. Marque «Mostrar todas as datas» para ver o histórico.
        </p>
      )}
      {error && <div className="paics-error" style={{ padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 6, marginBottom: 12 }}>{error}</div>}
      {loading ? (
        <p>Carregando...</p>
      ) : (
        <div className="paics-card" style={{ background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", overflow: "hidden" }}>
          <div className="paics-table-wrap">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Paciente</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Tutor</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Status</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Data</th>
                <th style={{ padding: "10px 12px", textAlign: "left", fontSize: "0.8rem" }}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {exames.map((ex) => (
                <tr key={ex.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "10px 12px" }}>{ex.paciente}</td>
                  <td style={{ padding: "10px 12px" }}>{ex.tutor}</td>
                  <td style={{ padding: "10px 12px" }}>{statusBadge(ex.status)}</td>
                  <td style={{ padding: "10px 12px" }}>{ex.created_at || "—"}</td>
                  <td style={{ padding: "10px 12px" }}>
                    <Link href={`/user/exames/${ex.id}`} style={{ color: "#1a2d4a", textDecoration: "none" }}>Ver / Baixar PDF</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          {exames.length === 0 && <p style={{ padding: 24, color: "#6b7280", textAlign: "center" }}>Nenhum exame encontrado.</p>}
        </div>
      )}
    </div>
  );
}
