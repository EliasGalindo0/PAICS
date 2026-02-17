"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getExame,
  gerarLaudo,
  atualizarLaudo,
  atualizarRequisicao,
  liberarLaudo,
  regenerarLaudo,
  cancelarLaudo,
  loadImageAsBlobUrl,
} from "@/lib/api";

const btn = {
  padding: "6px 12px",
  border: "none",
  borderRadius: 6,
  cursor: "pointer" as const,
  fontSize: "0.9rem",
  fontWeight: 600,
};

export default function AdminExameDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editando, setEditando] = useState(false);
  const [textoLaudo, setTextoLaudo] = useState("");
  const [correcoesIa, setCorrecoesIa] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [regenerando, setRegenerando] = useState(false);
  const [cancelando, setCancelando] = useState(false);
  const [imgUrls, setImgUrls] = useState<Record<string, string>>({});
  const [imgSelecionadas, setImgSelecionadas] = useState<
    Record<string, boolean>
  >({});
  const [zoomRef, setZoomRef] = useState<string | null>(null);
  const [confirmCancelar, setConfirmCancelar] = useState(false);
  const [editandoRequisicao, setEditandoRequisicao] = useState(false);
  const [formRequisicao, setFormRequisicao] = useState<Record<string, string>>(
    {},
  );
  const [salvandoRequisicao, setSalvandoRequisicao] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getExame(id)
      .then((d) => {
        setData(d);
        setTextoLaudo(d?.laudo?.texto || "");
        setEditando(!!d?.laudo);
        const r = d?.requisicao || {};
        setFormRequisicao({
          paciente: r.paciente || "",
          tutor: r.tutor || "",
          especie: r.especie || "",
          idade: r.idade || "",
          raca: r.raca || "",
          regiao_estudo: r.regiao_estudo || "",
          suspeita_clinica: r.suspeita_clinica || "",
          historico_clinico: r.historico_clinico || "",
        });
        const refs = d?.requisicao?.imagens || [];
        setImgSelecionadas((prev) => {
          const next = { ...prev };
          refs.forEach((r: string) => {
            if (!(r in next)) next[r] = true;
          });
          return next;
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (id) load();
  }, [id, load]);

  useEffect(() => {
    if (!data?.requisicao?.imagens) return;
    const refs = data.requisicao.imagens as string[];
    refs.forEach((ref) => {
      loadImageAsBlobUrl(id, ref)
        .then((url) => setImgUrls((m) => ({ ...m, [ref]: url })))
        .catch(() => {});
    });
  }, [id, data?.requisicao?.imagens]);

  const imagens = (data?.requisicao?.imagens || []) as string[];
  const selecionadas = imagens.filter((r) => imgSelecionadas[r] !== false);

  const handleGerar = async () => {
    if (selecionadas.length === 0) {
      setError("Selecione ao menos 1 imagem para gerar o laudo");
      return;
    }
    setGerando(true);
    setError("");
    try {
      await gerarLaudo(id, selecionadas);
      setEditando(true);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGerando(false);
    }
  };

  const handleSalvarLaudo = async () => {
    setSalvando(true);
    setError("");
    try {
      await atualizarLaudo(id, textoLaudo);
      setEditando(false);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSalvando(false);
    }
  };

  const handleSalvarRequisicao = async () => {
    setSalvandoRequisicao(true);
    setError("");
    try {
      const updates: Record<string, string> = {};
      Object.entries(formRequisicao).forEach(([k, v]) => {
        updates[k] = (v || "").trim();
      });
      await atualizarRequisicao(id, updates);
      setEditandoRequisicao(false);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSalvandoRequisicao(false);
    }
  };

  const handleLiberar = async () => {
    setError("");
    try {
      if (textoLaudo !== (data?.laudo?.texto || "")) {
        await atualizarLaudo(id, textoLaudo);
      }
      await liberarLaudo(id);
      router.push("/admin/exames");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleRegenerar = async () => {
    if (!correcoesIa.trim()) {
      setError("Descreva as correções para a IA");
      return;
    }
    setRegenerando(true);
    setError("");
    try {
      const res = await regenerarLaudo(id, correcoesIa.trim());
      setTextoLaudo(res.texto ?? "");
      setCorrecoesIa("");
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRegenerando(false);
    }
  };

  const handleCancelarLaudo = async () => {
    if (!confirmCancelar) {
      setConfirmCancelar(true);
      return;
    }
    setCancelando(true);
    setError("");
    try {
      await cancelarLaudo(id);
      setEditando(false);
      setConfirmCancelar(false);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCancelando(false);
    }
  };

  const toggleTodas = (sel: boolean) => {
    const next: Record<string, boolean> = {};
    imagens.forEach((r) => {
      next[r] = sel;
    });
    setImgSelecionadas(next);
  };

  if (loading || !data) {
    return <p>Carregando...</p>;
  }

  const req = data.requisicao;
  const laudo = data.laudo;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
      <button
        onClick={() => router.push("/admin/exames")}
        style={{
          ...btn,
          backgroundColor: "#1a2d4a",
          color: "#fff",
          fontSize: "0.8rem",
          marginBottom: 12,
          padding: "6px 12px",
          borderRadius: 6,
        }}
      >
        ← Voltar para lista de exames
      </button>
      <h1 style={{ fontSize: "1.25rem", marginBottom: 16 }}>
        Exame #{id.slice(-8)} · {req.paciente}
      </h1>
      {error && (
        <div
          style={{
            padding: 10,
            background: "#fef2f2",
            color: "#b91c1c",
            borderRadius: 6,
            marginBottom: 12,
          }}
        >
          {error}
          <button
            onClick={() => setError("")}
            style={{
              marginLeft: 8,
              padding: "2px 8px",
              background: "#b91c1c",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Fechar
          </button>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          marginBottom: 24,
        }}
      >
        <div>
          <h3
            style={{
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            Dados do Paciente
            {!editandoRequisicao ? (
              <button
                onClick={() => setEditandoRequisicao(true)}
                style={{ ...btn, background: "#2563eb", color: "#fff", fontSize: "0.8rem" }}
              >
                Editar requisição
              </button>
            ) : null}
          </h3>
          {editandoRequisicao ? (
            <div
              className="paics-card"
              style={{
                background: "#fff",
                padding: 16,
                borderRadius: 8,
                boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
                display: "flex",
                flexDirection: "column",
                gap: 12,
              }}
            >
              {[
                "paciente",
                "tutor",
                "especie",
                "idade",
                "raca",
                "regiao_estudo",
                "suspeita_clinica",
              ].map((f) => (
                <div key={f}>
                  <label
                    style={{
                      display: "block",
                      fontSize: "0.85rem",
                      marginBottom: 4,
                    }}
                  >
                    {f === "paciente"
                      ? "Paciente"
                      : f === "tutor"
                        ? "Tutor"
                        : f === "especie"
                          ? "Espécie"
                          : f === "idade"
                            ? "Idade"
                            : f === "raca"
                              ? "Raça"
                              : f === "regiao_estudo"
                                ? "Região de estudo"
                                : "Suspeita clínica"}
                  </label>
                  <input
                    value={formRequisicao[f] || ""}
                    onChange={(e) =>
                      setFormRequisicao((p) => ({ ...p, [f]: e.target.value }))
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                    }}
                  />
                </div>
              ))}
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.85rem",
                    marginBottom: 4,
                  }}
                >
                  Histórico clínico
                </label>
                <textarea
                  value={formRequisicao.historico_clinico || ""}
                  onChange={(e) =>
                    setFormRequisicao((p) => ({
                      ...p,
                      historico_clinico: e.target.value,
                    }))
                  }
                  rows={4}
                  style={{
                    width: "100%",
                    padding: 8,
                    borderRadius: 6,
                    border: "1px solid #d1d5db",
                  }}
                />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={handleSalvarRequisicao}
                  disabled={salvandoRequisicao}
                  style={{ ...btn, background: "#16a34a", color: "#fff" }}
                >
                  {salvandoRequisicao ? "Salvando..." : "Salvar"}
                </button>
                <button
                  onClick={() => setEditandoRequisicao(false)}
                  style={{ ...btn, background: "#e5e7eb" }}
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <div
              className="paics-card"
              style={{
                background: "#fff",
                padding: 16,
                borderRadius: 8,
                boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              }}
            >
              <p>
                <strong>Paciente:</strong> {req.paciente}
              </p>
              <p>
                <strong>Tutor:</strong> {req.tutor}
              </p>
              <p>
                <strong>Clínica:</strong> {req.clinica}
              </p>
              <p>
                <strong>Veterinário:</strong>{" "}
                {req.medico_veterinario_solicitante}
              </p>
              <p>
                <strong>Espécie:</strong> {req.especie || "—"}
              </p>
              <p>
                <strong>Idade:</strong> {req.idade || "—"}
              </p>
              <p>
                <strong>Raça:</strong> {req.raca || "—"}
              </p>
              <p>
                <strong>Região:</strong> {req.regiao_estudo || "—"}
              </p>
              <p>
                <strong>Suspeita:</strong> {req.suspeita_clinica || "—"}
              </p>
              <p>
                <strong>Histórico:</strong>
              </p>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontSize: "0.9rem",
                  marginTop: 4,
                }}
              >
                {req.historico_clinico || "—"}
              </pre>
            </div>
          )}
          {(req.historico_edicoes || []).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ marginBottom: 8, fontSize: "0.95rem" }}>
                Histórico de edições (auditoria)
              </h4>
              <div
                className="paics-card"
                style={{
                  padding: 12,
                  maxHeight: 200,
                  overflowY: "auto",
                }}
              >
                {(req.historico_edicoes || []).map((h: any, i: number) => (
                  <div
                    key={i}
                    style={{
                      padding: 8,
                      marginBottom:
                        i < (req.historico_edicoes?.length || 0) - 1 ? 8 : 0,
                      borderBottom:
                        i < (req.historico_edicoes?.length || 0) - 1
                          ? "1px solid var(--border)"
                          : "none",
                      fontSize: "0.85rem",
                    }}
                  >
                    <div
                      style={{ color: "var(--text-muted)", marginBottom: 4 }}
                    >
                      {h.created_at
                        ? new Date(h.created_at).toLocaleString("pt-BR")
                        : "—"}
                    </div>
                    {Object.entries(h.alteracoes || {}).map(
                      ([campo, alt]: [string, any]) => (
                        <div
                          key={campo}
                          style={{ marginLeft: 8, marginBottom: 2 }}
                        >
                          <strong>{campo}:</strong> {String(alt?.de ?? "—")} →{" "}
                          {String(alt?.para ?? "—")}
                        </div>
                      ),
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div>
          <h3 style={{ marginBottom: 8 }}>Imagens</h3>
          {!laudo && imagens.length > 0 && (
            <p
              style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: 8 }}
            >
              Desmarque as que NÃO devem ir para análise da IA. Mínimo 1.
            </p>
          )}
          {!laudo && imagens.length > 0 && (
            <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
              <button
                onClick={() => toggleTodas(true)}
                style={{ ...btn, background: "#e5e7eb" }}
              >
                Selecionar todas
              </button>
              <button
                onClick={() => toggleTodas(false)}
                style={{ ...btn, background: "#e5e7eb" }}
              >
                Desmarcar todas
              </button>
              <span style={{ alignSelf: "center", fontSize: "0.9rem" }}>
                {selecionadas.length} de {imagens.length} selecionada(s)
              </span>
            </div>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {imagens.map((ref: string) => (
              <div
                key={ref}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <div
                  onClick={() => setZoomRef(ref)}
                  style={{
                    width: 140,
                    cursor: "pointer",
                    border: laudo
                      ? "2px solid transparent"
                      : imgSelecionadas[ref] !== false
                        ? "2px solid #16a34a"
                        : "2px solid #e5e7eb",
                    borderRadius: 8,
                    overflow: "hidden",
                  }}
                >
                  {imgUrls[ref] ? (
                    <img
                      src={imgUrls[ref]}
                      alt=""
                      style={{
                        width: "100%",
                        height: 120,
                        objectFit: "contain",
                        display: "block",
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: 140,
                        height: 120,
                        background: "#f3f4f6",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "0.8rem",
                      }}
                    >
                      Carregando...
                    </div>
                  )}
                </div>
                {!laudo && (
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      fontSize: "0.8rem",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={imgSelecionadas[ref] !== false}
                      onChange={(e) =>
                        setImgSelecionadas((p) => ({
                          ...p,
                          [ref]: e.target.checked,
                        }))
                      }
                    />
                    Incluir
                  </label>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 24 }}>
        <h3 style={{ marginBottom: 8 }}>Laudo</h3>
        {!laudo && imagens.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <button
              onClick={handleGerar}
              disabled={gerando || selecionadas.length === 0}
              style={{
                ...btn,
                padding: "10px 20px",
                background: "#16a34a",
                color: "#fff",
              }}
            >
              {gerando ? "Gerando..." : "Gerar Laudo com IA"}
            </button>
            {selecionadas.length === 0 && (
              <span
                style={{ marginLeft: 12, color: "#b91c1c", fontSize: "0.9rem" }}
              >
                Selecione ao menos 1 imagem
              </span>
            )}
          </div>
        )}
        {laudo && (
          <div
            className="paics-card"
            style={{
              background: "#fff",
              padding: 20,
              borderRadius: 8,
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
            }}
          >
            {!editando ? (
              <div style={{ marginBottom: 12 }}>
                <button
                  onClick={() => setEditando(true)}
                  style={{ ...btn, background: "#2563eb", color: "#fff" }}
                >
                  Abrir edição
                </button>
              </div>
            ) : (
              <>
                <div
                  className="paics-muted"
                  style={{
                    marginBottom: 16,
                    padding: 12,
                    background: "#f9fafb",
                    borderRadius: 6,
                  }}
                >
                  <h4 style={{ margin: "0 0 12px", fontSize: "0.95rem" }}>
                    Ações
                  </h4>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 8,
                      alignItems: "center",
                    }}
                  >
                    <button
                      onClick={handleSalvarLaudo}
                      disabled={salvando}
                      style={{ ...btn, background: "#16a34a", color: "#fff" }}
                    >
                      {salvando ? "Salvando..." : "Salvar alterações"}
                    </button>
                    {(laudo.status === "pendente" ||
                      laudo.status === "validado") && (
                      <button
                        onClick={handleLiberar}
                        style={{ ...btn, background: "#16a34a", color: "#fff" }}
                      >
                        Liberar exame
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setEditando(false);
                        setTextoLaudo(laudo.texto);
                        setConfirmCancelar(false);
                        router.push("/admin/exames");
                      }}
                      style={{ ...btn, background: "#6b7280", color: "#fff" }}
                    >
                      Fechar edição
                    </button>
                    <button
                      onClick={handleCancelarLaudo}
                      disabled={cancelando}
                      style={{
                        ...btn,
                        background: confirmCancelar ? "#b91c1c" : "#dc2626",
                        color: "#fff",
                      }}
                    >
                      {confirmCancelar
                        ? "Confirmar exclusão?"
                        : cancelando
                          ? "Excluindo..."
                          : "Excluir laudo"}
                    </button>
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label
                    style={{
                      display: "block",
                      marginBottom: 6,
                      fontSize: "0.9rem",
                    }}
                  >
                    Correções para IA (opcional)
                  </label>
                  <textarea
                    value={correcoesIa}
                    onChange={(e) => setCorrecoesIa(e.target.value)}
                    placeholder='Ex: "A lesão está no membro ESQUERDO, não direito"'
                    maxLength={500}
                    rows={3}
                    style={{
                      width: "100%",
                      padding: 10,
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                      fontFamily: "inherit",
                      boxSizing: "border-box",
                    }}
                  />
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      marginTop: 6,
                    }}
                  >
                    <button
                      onClick={handleRegenerar}
                      disabled={regenerando || !correcoesIa.trim()}
                      style={{ ...btn, background: "#7c3aed", color: "#fff" }}
                    >
                      {regenerando
                        ? "Regenerando..."
                        : "Gerar laudo com correções"}
                    </button>
                    <span style={{ fontSize: "0.85rem", color: "#6b7280" }}>
                      {correcoesIa.length}/500
                    </span>
                  </div>
                </div>
                <div>
                  <label
                    style={{
                      display: "block",
                      marginBottom: 6,
                      fontSize: "0.9rem",
                    }}
                  >
                    Conteúdo do laudo
                  </label>
                  <textarea
                    value={textoLaudo}
                    onChange={(e) => setTextoLaudo(e.target.value)}
                    style={{
                      width: "100%",
                      minHeight: 300,
                      padding: 12,
                      borderRadius: 8,
                      border: "1px solid #d1d5db",
                      fontFamily: "inherit",
                      fontSize: "0.95rem",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
              </>
            )}
            {!editando && laudo && (
              <div
                className="paics-card paics-laudo-conteudo"
                style={{
                  minHeight: 200,
                  padding: 16,
                  fontSize: "0.95rem",
                  lineHeight: 1.6,
                }}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {textoLaudo || ""}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>

      {zoomRef && imgUrls[zoomRef] && (
        <div
          onClick={() => setZoomRef(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.85)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 24,
            cursor: "pointer",
          }}
        >
          <img
            src={imgUrls[zoomRef]}
            alt=""
            onClick={(e) => e.stopPropagation()}
            style={{
              maxWidth: "95vw",
              maxHeight: "95vh",
              objectFit: "contain",
              borderRadius: 8,
              boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
            }}
          />
          <button
            onClick={() => setZoomRef(null)}
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              width: 40,
              height: 40,
              background: "#fff",
              border: "none",
              borderRadius: 50,
              fontSize: "1.5rem",
              cursor: "pointer",
              lineHeight: 1,
              fontWeight: 600,
            }}
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
