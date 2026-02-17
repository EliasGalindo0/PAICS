"use client";

import React, { useEffect, useState } from "react";
import {
  listarKnowledgeBase,
  buscarKnowledgeBase,
  adicionarKbPdf,
  adicionarKbPrompt,
  adicionarKbOrientacao,
  excluirKnowledgeBaseItem,
  getLearningStats,
} from "@/lib/api";

type TabId = "adicionar" | "buscar" | "listar" | "aprendizado";

export default function AdminKnowledgeBasePage() {
  const [tab, setTab] = useState<TabId>("adicionar");
  const [items, setItems] = useState<any[]>([]);
  const [tipoFiltro, setTipoFiltro] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Adicionar
  const [tipoConteudo, setTipoConteudo] = useState<"pdf" | "prompt" | "orientacao">("pdf");
  const [titulo, setTitulo] = useState("");
  const [conteudo, setConteudo] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [salvando, setSalvando] = useState(false);

  // Buscar
  const [query, setQuery] = useState("");
  const [nResultados, setNResultados] = useState(5);
  const [resultados, setResultados] = useState<any[]>([]);
  const [buscando, setBuscando] = useState(false);

  // Aprendizado
  const [stats, setStats] = useState<any>(null);

  const styleBtn = { padding: "8px 16px", background: "#1a2d4a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" as const };
  const styleInput = { width: "100%", padding: 10, borderRadius: 6, border: "1px solid #d1d5db", boxSizing: "border-box" as const };

  const loadItems = () => {
    setLoading(true);
    listarKnowledgeBase(tipoFiltro || undefined)
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const loadStats = () => {
    getLearningStats()
      .then(setStats)
      .catch(() => setStats(null));
  };

  useEffect(() => {
    if (tab === "listar") loadItems();
    if (tab === "aprendizado") loadStats();
  }, [tab, tipoFiltro]);

  const handleAdicionar = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSalvando(true);
    try {
      const tags = tagsInput ? tagsInput.split(",").map((t) => t.trim()).filter(Boolean) : [];
      if (tipoConteudo === "pdf") {
        if (!pdfFile || !titulo.trim()) {
          throw new Error("Selecione um PDF e informe o título");
        }
        await adicionarKbPdf(pdfFile, titulo.trim(), tags);
        setSuccess("PDF adicionado com sucesso!");
      } else if (tipoConteudo === "prompt") {
        if (!titulo.trim() || !conteudo.trim()) throw new Error("Título e conteúdo são obrigatórios");
        await adicionarKbPrompt(titulo.trim(), conteudo.trim(), tags);
        setSuccess("Prompt adicionado com sucesso!");
      } else {
        if (!titulo.trim() || !conteudo.trim()) throw new Error("Título e conteúdo são obrigatórios");
        await adicionarKbOrientacao(titulo.trim(), conteudo.trim(), tags);
        setSuccess("Orientação adicionada com sucesso!");
      }
      setTitulo("");
      setConteudo("");
      setTagsInput("");
      setPdfFile(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSalvando(false);
    }
  };

  const handleBuscar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setBuscando(true);
    setError("");
    try {
      const r = await buscarKnowledgeBase(query.trim(), nResultados);
      setResultados(r);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBuscando(false);
    }
  };

  const handleExcluir = async (id: string) => {
    if (!confirm("Excluir este item?")) return;
    setError("");
    try {
      await excluirKnowledgeBaseItem(id);
      loadItems();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const tabs = [
    { id: "adicionar" as TabId, label: "Adicionar Conteúdo" },
    { id: "buscar" as TabId, label: "Buscar" },
    { id: "listar" as TabId, label: "Listar Tudo" },
    { id: "aprendizado" as TabId, label: "Sistema de Aprendizado" },
  ];

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 24px" }}>
      <h1 style={{ fontSize: "1.25rem", marginBottom: 20 }}>Knowledge Base e Aprendizado</h1>
      {error && (
        <div className="paics-error" style={{ padding: 12, background: "#fef2f2", color: "#b91c1c", borderRadius: 6, marginBottom: 16 }}>
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: 12, padding: "2px 8px", background: "#b91c1c", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>Fechar</button>
        </div>
      )}
      {success && (
        <div className="paics-success" style={{ padding: 12, background: "#dcfce7", color: "#166534", borderRadius: 6, marginBottom: 16 }}>
          {success}
          <button onClick={() => setSuccess("")} style={{ marginLeft: 12, padding: "2px 8px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>Fechar</button>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              ...styleBtn,
              background: tab === t.id ? "#1a2d4a" : "#6b7280",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "adicionar" && (
        <form onSubmit={handleAdicionar} className="paics-card" style={{ background: "#fff", padding: 24, borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>Adicionar Novo Conteúdo</h3>
          <div style={{ marginBottom: 12 }}>
            <label>Tipo de Conteúdo</label>
            <select value={tipoConteudo} onChange={(e) => setTipoConteudo(e.target.value as any)} style={styleInput}>
              <option value="pdf">PDF</option>
              <option value="prompt">Prompt</option>
              <option value="orientacao">Orientação</option>
            </select>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label>Título *</label>
            <input value={titulo} onChange={(e) => setTitulo(e.target.value)} required style={styleInput} />
          </div>
          {tipoConteudo === "pdf" && (
            <div style={{ marginBottom: 12 }}>
              <label>Arquivo PDF *</label>
              <input type="file" accept=".pdf" onChange={(e) => setPdfFile(e.target.files?.[0] || null)} style={styleInput} />
            </div>
          )}
          {(tipoConteudo === "prompt" || tipoConteudo === "orientacao") && (
            <div style={{ marginBottom: 12 }}>
              <label>Conteúdo *</label>
              <textarea value={conteudo} onChange={(e) => setConteudo(e.target.value)} required rows={8} style={styleInput} />
            </div>
          )}
          <div style={{ marginBottom: 16 }}>
            <label>Tags (separadas por vírgula)</label>
            <input value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} placeholder="ex: radiologia, ortopedia" style={styleInput} />
          </div>
          <button type="submit" disabled={salvando} style={{ ...styleBtn, background: "#16a34a" }}>{salvando ? "Salvando..." : "Adicionar"}</button>
        </form>
      )}

      {tab === "buscar" && (
        <div className="paics-card" style={{ background: "#fff", padding: 24, borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>Buscar na Knowledge Base</h3>
          <form onSubmit={handleBuscar} style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 12 }}>
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Digite sua busca" style={styleInput} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label>Número de resultados</label>
              <input type="number" min={1} max={20} value={nResultados} onChange={(e) => setNResultados(parseInt(e.target.value) || 5)} style={{ ...styleInput, maxWidth: 80 }} />
            </div>
            <button type="submit" disabled={buscando} style={styleBtn}>{buscando ? "Buscando..." : "Buscar"}</button>
          </form>
          {resultados.length > 0 && (
            <div>
              <p style={{ color: "#166534", marginBottom: 12 }}>Encontrados {resultados.length} resultado(s)</p>
              {resultados.map((r, idx) => (
                <details key={idx} style={{ marginBottom: 12, padding: 12, background: "#f9fafb", borderRadius: 6 }}>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>#{idx + 1} - {r.kb_item?.titulo} (Relevância: {((r.relevancia || 0) * 100).toFixed(0)}%)</summary>
                  <div style={{ marginTop: 8, fontSize: "0.9rem" }}>
                    <p><strong>Tipo:</strong> {r.kb_item?.tipo}</p>
                    <p><strong>Tags:</strong> {(r.kb_item?.tags || []).join(", ") || "—"}</p>
                    <pre style={{ background: "#fff", padding: 8, borderRadius: 4, overflow: "auto", maxHeight: 150 }}>{(r.kb_item?.conteudo || "").slice(0, 500)}...</pre>
                  </div>
                </details>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "listar" && (
        <div className="paics-card" style={{ background: "#fff", padding: 24, borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>Todos os Itens</h3>
          <div style={{ marginBottom: 12 }}>
            <label>Filtrar por tipo</label>
            <select value={tipoFiltro} onChange={(e) => setTipoFiltro(e.target.value)} style={{ ...styleInput, maxWidth: 200 }}>
              <option value="">Todos</option>
              <option value="pdf">pdf</option>
              <option value="prompt">prompt</option>
              <option value="orientacao">orientacao</option>
            </select>
          </div>
          <p style={{ marginBottom: 16, fontWeight: 600 }}>Total: {items.length} itens</p>
          {loading ? (
            <p>Carregando...</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {items.map((it) => (
                <details key={it.id} style={{ padding: 12, background: "#f9fafb", borderRadius: 6, border: "1px solid #e5e7eb" }}>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>{it.titulo} — {it.tipo}</summary>
                  <div style={{ marginTop: 8, fontSize: "0.9rem" }}>
                    <p><strong>Tags:</strong> {(it.tags || []).join(", ") || "—"}</p>
                    <p><strong>Criado em:</strong> {it.created_at}</p>
                    <pre style={{ background: "#fff", padding: 8, borderRadius: 4, overflow: "auto", maxHeight: 100, fontSize: "0.85rem" }}>{(it.conteudo_preview || "")}...</pre>
                    <button onClick={() => handleExcluir(it.id)} style={{ marginTop: 8, padding: "4px 12px", background: "#b91c1c", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: "0.85rem" }}>Excluir</button>
                  </div>
                </details>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "aprendizado" && (
        <div className="paics-card" style={{ background: "#fff", padding: 24, borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}>
          <h3 style={{ marginTop: 0, marginBottom: 16 }}>Sistema de Aprendizado Contínuo</h3>
          <div style={{ padding: 12, background: "#eff6ff", borderRadius: 6, marginBottom: 20, fontSize: "0.9rem" }}>
            <strong>Sistema de Aprendizado Contínuo</strong>
            <p style={{ margin: "8px 0 0" }}>
              O sistema aprende com cada laudo processado: <strong>Rating 5/5</strong> = aprovado sem edições; <strong>Rating 3/5</strong> = editado parcialmente; <strong>Rating 1/5</strong> = muito editado (API externa).
            </p>
          </div>
          {stats && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 16 }}>
              <div className="paics-stats" style={{ padding: 16, background: "#f3f4f6", borderRadius: 8, textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{stats.total_casos ?? 0}</div>
                <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>Total de Casos</div>
              </div>
              <div className="paics-stats" style={{ padding: 16, background: "#f3f4f6", borderRadius: 8, textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{(stats.taxa_aprovacao ?? 0).toFixed(1)}%</div>
                <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>Taxa de Aprovação</div>
              </div>
              <div className="paics-stats" style={{ padding: 16, background: "#f3f4f6", borderRadius: 8, textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{(stats.economia_api ?? 0).toFixed(1)}%</div>
                <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>Economia API</div>
              </div>
              <div className="paics-stats" style={{ padding: 16, background: "#f3f4f6", borderRadius: 8, textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{stats.rating_5 ?? 0}</div>
                <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>Rating 5</div>
              </div>
              <div className="paics-stats" style={{ padding: 16, background: "#f3f4f6", borderRadius: 8, textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{stats.rating_3 ?? 0}</div>
                <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>Rating 3</div>
              </div>
              <div className="paics-stats" style={{ padding: 16, background: "#f3f4f6", borderRadius: 8, textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{stats.rating_1 ?? 0}</div>
                <div style={{ fontSize: "0.85rem", color: "#6b7280" }}>Rating 1</div>
              </div>
            </div>
          )}
          {stats?.erro && <p style={{ color: "#b91c1c", marginTop: 12 }}>{stats.erro}</p>}
        </div>
      )}
    </div>
  );
}
