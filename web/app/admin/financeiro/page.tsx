"use client";

import { useEffect, useState } from "react";
import { listUsuarios, listFaturas, fechamentoTodos, criarFatura, gerarFechamento, atualizarStatusFatura } from "@/lib/api";

export default function AdminFinanceiroPage() {
  const [usuarios, setUsuarios] = useState<any[]>([]);
  const [faturas, setFaturas] = useState<any[]>([]);
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [valorExame, setValorExame] = useState(35);
  const [valorPlantao, setValorPlantao] = useState(60);
  const [fechamentos, setFechamentos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [gerando, setGerando] = useState(false);
  const [atualizandoId, setAtualizandoId] = useState<string | null>(null);

  const loadFaturas = () => {
    listFaturas(undefined, undefined)
      .then(setFaturas)
      .catch(() => setFaturas([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    listUsuarios()
      .then(setUsuarios)
      .catch(() => setUsuarios([]));
    loadFaturas();
  }, []);

  const handleAtualizarStatus = async (faturaId: string, status: "paga" | "cancelada") => {
    setAtualizandoId(faturaId);
    setError("");
    try {
      await atualizarStatusFatura(faturaId, status);
      loadFaturas();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAtualizandoId(null);
    }
  };

  const handleGerarFechamentos = async () => {
    if (!dataInicio || !dataFim) {
      setError("Informe data inicial e final");
      return;
    }
    setGerando(true);
    setError("");
    try {
      const f = await fechamentoTodos(dataInicio, dataFim, valorExame, valorPlantao);
      setFechamentos(f);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setGerando(false);
    }
  };

  const handleCriarFatura = async (userId: string, periodo: string, exames: any[], valorTotal: number) => {
    setError("");
    try {
      await criarFatura({ user_id: userId, periodo, exames, valor_total: valorTotal });
      setFechamentos((prev) => prev.filter((f) => f.usuario?.id !== userId));
      loadFaturas();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", marginBottom: 16 }}>Financeiro</h1>
      {error && <div className="paics-error" style={{ padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 6, marginBottom: 12 }}>{error}</div>}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 8 }}>Gerar Fechamentos</h3>
        <div className="paics-filters" style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: 4 }}>Data Início</label>
            <input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} style={{ padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: 4 }}>Data Fim</label>
            <input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} style={{ padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: 4 }}>Valor por Exame (R$)</label>
            <input type="number" min={0} step={1} value={valorExame} onChange={(e) => setValorExame(Number(e.target.value) || 0)} style={{ padding: 8, borderRadius: 6, border: "1px solid #d1d5db", width: 100 }} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", marginBottom: 4 }}>Acréscimo Plantão (R$)</label>
            <input type="number" min={0} step={1} value={valorPlantao} onChange={(e) => setValorPlantao(Number(e.target.value) || 0)} style={{ padding: 8, borderRadius: 6, border: "1px solid #d1d5db", width: 100 }} title="Valor adicional para exames em plantão" />
          </div>
          <div style={{ alignSelf: "flex-end" }}>
            <button onClick={handleGerarFechamentos} disabled={gerando} style={{ padding: "8px 16px", background: "#1a2d4a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>{gerando ? "Gerando..." : "Gerar Fechamentos"}</button>
          </div>
        </div>
      </div>
      {fechamentos.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h3>Fechamentos gerados</h3>
          {fechamentos.map((item: any) => (
            <div key={item.usuario?.id} className="paics-card" style={{ padding: 12, background: "#fff", borderRadius: 8, marginBottom: 12, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
              <strong>{item.usuario?.nome || item.usuario?.username}</strong>
              <p>Período: {item.fechamento?.periodo} · {item.fechamento?.quantidade_exames} exame(s) · R$ {item.fechamento?.valor_total?.toFixed(2)}</p>
              <button onClick={() => handleCriarFatura(item.usuario?.id, item.fechamento?.periodo, item.fechamento?.exames || [], item.fechamento?.valor_total || 0)} style={{ padding: "6px 12px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>Criar fatura</button>
            </div>
          ))}
        </div>
      )}
      <div>
        <h3 style={{ marginBottom: 8 }}>Faturas</h3>
        {loading ? <p>Carregando...</p> : (
          <div className="paics-card" style={{ background: "#fff", borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)", overflow: "hidden" }}>
            <div className="paics-table-wrap">
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  <th style={{ padding: 10, textAlign: "left" }}>Período</th>
                  <th style={{ padding: 10, textAlign: "left" }}>Valor</th>
                  <th style={{ padding: 10, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 10, textAlign: "left" }}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {faturas.map((f) => (
                  <tr key={f.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: 10 }}>{f.periodo}</td>
                    <td style={{ padding: 10 }}>R$ {f.valor_total?.toFixed(2)}</td>
                    <td style={{ padding: 10 }}>
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.8rem",
                          background:
                            f.status === "paga"
                              ? "#dcfce7"
                              : f.status === "cancelada"
                                ? "#fee2e2"
                                : "#fef3c7",
                          color:
                            f.status === "paga"
                              ? "#166534"
                              : f.status === "cancelada"
                                ? "#991b1b"
                                : "#92400e",
                        }}
                      >
                        {f.status}
                      </span>
                    </td>
                    <td style={{ padding: 10 }}>
                      {f.status === "pendente" && (
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            onClick={() => handleAtualizarStatus(f.id, "paga")}
                            disabled={atualizandoId === f.id}
                            style={{
                              padding: "4px 10px",
                              background: "#16a34a",
                              color: "#fff",
                              border: "none",
                              borderRadius: 6,
                              cursor: atualizandoId === f.id ? "not-allowed" : "pointer",
                              fontSize: "0.85rem",
                            }}
                          >
                            {atualizandoId === f.id ? "..." : "Marcar paga"}
                          </button>
                          <button
                            onClick={() => handleAtualizarStatus(f.id, "cancelada")}
                            disabled={atualizandoId === f.id}
                            style={{
                              padding: "4px 10px",
                              background: "#dc2626",
                              color: "#fff",
                              border: "none",
                              borderRadius: 6,
                              cursor: atualizandoId === f.id ? "not-allowed" : "pointer",
                              fontSize: "0.85rem",
                            }}
                          >
                            {atualizandoId === f.id ? "..." : "Cancelar"}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            {faturas.length === 0 && <p style={{ padding: 24, color: "#6b7280", textAlign: "center" }}>Nenhuma fatura.</p>}
          </div>
        )}
      </div>
    </div>
  );
}
