"use client";

import { useEffect, useState } from "react";
import { listFaturas } from "@/lib/api";

export default function UserFaturasPage() {
  const [faturas, setFaturas] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    listFaturas(statusFilter || undefined)
      .then(setFaturas)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  const totalPendente = faturas.filter((f) => f.status === "pendente").reduce((s, f) => s + (f.valor_total || 0), 0);
  const totalPago = faturas.filter((f) => f.status === "paga").reduce((s, f) => s + (f.valor_total || 0), 0);

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", marginBottom: 16 }}>Minhas Faturas</h1>
      <div style={{ display: "flex", gap: 24, marginBottom: 24 }}>
        <div className="paics-card" style={{ padding: 16, background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", minWidth: 140 }}>
          <p style={{ margin: 0, fontSize: "0.9rem", color: "#6b7280" }}>Total</p>
          <p style={{ margin: "4px 0 0", fontSize: "1.25rem", fontWeight: 600 }}>{faturas.length} fatura(s)</p>
        </div>
        <div className="paics-card" style={{ padding: 16, background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", minWidth: 140 }}>
          <p style={{ margin: 0, fontSize: "0.9rem", color: "#6b7280" }}>Pendentes</p>
          <p style={{ margin: "4px 0 0", fontSize: "1.25rem", fontWeight: 600 }}>R$ {totalPendente.toFixed(2)}</p>
        </div>
        <div className="paics-card" style={{ padding: 16, background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", minWidth: 140 }}>
          <p style={{ margin: 0, fontSize: "0.9rem", color: "#6b7280" }}>Pagas</p>
          <p style={{ margin: "4px 0 0", fontSize: "1.25rem", fontWeight: 600 }}>R$ {totalPago.toFixed(2)}</p>
        </div>
      </div>
      <div style={{ marginBottom: 12 }}>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db" }}>
          <option value="">Todos</option>
          <option value="pendente">Pendente</option>
          <option value="paga">Paga</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </div>
      {error && <div style={{ padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 6, marginBottom: 12 }}>{error}</div>}
      {loading ? (
        <p>Carregando...</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {faturas.map((f) => (
            <div key={f.id} className="paics-card" style={{ padding: 16, background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
              <div
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
                onClick={() => setExpandedId(expandedId === f.id ? null : f.id)}
              >
                <div>
                  <strong>{f.periodo}</strong>
                  <p style={{ margin: "4px 0 0", color: "#6b7280", fontSize: "0.9rem" }}>R$ {f.valor_total?.toFixed(2)} · {f.quantidade_exames} exame(s)</p>
                </div>
                <span style={{ padding: "4px 10px", borderRadius: 6, fontSize: "0.85rem", background: f.status === "paga" ? "#dcfce7" : f.status === "cancelada" ? "#fee2e2" : "#fef3c7", color: f.status === "paga" ? "#166534" : f.status === "cancelada" ? "#991b1b" : "#92400e" }}>{f.status}</span>
                <span style={{ fontSize: "1.2rem" }}>{expandedId === f.id ? "−" : "+"}</span>
              </div>
              {expandedId === f.id && (f.exames || []).length > 0 && (
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid #e5e7eb" }}>
                  <p style={{ margin: "0 0 8px", fontWeight: 600, fontSize: "0.9rem" }}>Exames incluídos</p>
                  {f.exames.map((ex: any, i: number) => {
                    const totalEx = ex.valor ?? (ex.valor_base ?? 0) + (ex.acrescimo_plantao ?? 0);
                    return (
                      <div key={i} style={{ padding: "8px 0", fontSize: "0.9rem", color: "#374151" }}>
                        {i + 1}. {ex.paciente}
                        {ex.valor_base != null && <span> · Base: R$ {Number(ex.valor_base).toFixed(2)}</span>}
                        {ex.plantao && ex.acrescimo_plantao ? <span> · Plantão: +R$ {Number(ex.acrescimo_plantao).toFixed(2)}</span> : null}
                        <span> · Total: R$ {Number(totalEx).toFixed(2)}</span>
                        {ex.observacao ? <span> · Obs: {ex.observacao}</span> : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
          {faturas.length === 0 && <p style={{ padding: 24, color: "#6b7280", textAlign: "center" }}>Nenhuma fatura.</p>}
        </div>
      )}
    </div>
  );
}
