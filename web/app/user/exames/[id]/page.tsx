"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getExame,
  downloadPdf,
  addObservacao,
  loadImageAsBlobUrl,
} from "@/lib/api";

export default function UserExameDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [baixando, setBaixando] = useState(false);
  const [obs, setObs] = useState("");
  const [envObs, setEnvObs] = useState(false);
  const [imgUrls, setImgUrls] = useState<Record<string, string>>({});
  const [zoomRef, setZoomRef] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    getExame(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (id) load();
  }, [id]);

  const imagens = (data?.requisicao?.imagens || []) as string[];
  useEffect(() => {
    if (!id || !imagens.length) return;
    imagens.forEach((ref: string) => {
      loadImageAsBlobUrl(id, ref)
        .then((url) => setImgUrls((m) => ({ ...m, [ref]: url })))
        .catch(() => {});
    });
  }, [id, data?.requisicao?.imagens]);

  const handleBaixarPdf = async () => {
    setBaixando(true);
    setError("");
    try {
      const blob = await downloadPdf(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `laudo_${data?.requisicao?.paciente || "exame"}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBaixando(false);
    }
  };

  const handleEnviarObs = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!obs.trim()) return;
    setEnvObs(true);
    setError("");
    try {
      await addObservacao(id, obs.trim());
      setObs("");
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEnvObs(false);
    }
  };

  if (loading || !data) {
    return <p>Carregando...</p>;
  }

  const req = data.requisicao;
  const laudo = data.laudo;

  return (
    <div>
      <Link
        href="/user/exames"
        style={{
          color: "#1a2d4a",
          textDecoration: "none",
          marginBottom: 12,
          display: "inline-block",
        }}
      >
        ← Voltar
      </Link>
      <h1 style={{ fontSize: "1.25rem", marginBottom: 16 }}>
        {req.paciente} · {req.tutor}
      </h1>
      {error && (
        <div
          className="paics-error"
          style={{
            padding: 10,
            background: "#fef2f2",
            color: "#b91c1c",
            borderRadius: 6,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      )}
      {imagens.length > 0 && (
        <div
          className="paics-card"
          style={{
            background: "#fff",
            padding: 20,
            borderRadius: 8,
            boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
            marginBottom: 20,
          }}
        >
          <h3 style={{ marginTop: 0, marginBottom: 12 }}>Imagens do Exame</h3>
          <p
            style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: 12 }}
          >
            Clique em uma imagem para ampliar.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {imagens.map((ref: string) => (
              <div
                key={ref}
                onClick={() => setZoomRef(ref)}
                style={{
                  width: 140,
                  height: 120,
                  cursor: "pointer",
                  borderRadius: 8,
                  overflow: "hidden",
                  border: "2px solid #e5e7eb",
                }}
              >
                {imgUrls[ref] ? (
                  <img
                    src={imgUrls[ref]}
                    alt=""
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "contain",
                      display: "block",
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: "100%",
                      height: "100%",
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
            ))}
          </div>
        </div>
      )}
      <div
        className="paics-card"
        style={{
          background: "#fff",
          padding: 20,
          borderRadius: 8,
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
          marginBottom: 20,
        }}
      >
        <p>
          <strong>Status do laudo:</strong> {laudo?.status || "Aguardando"}
        </p>
        <p>
          <strong>Tipo:</strong> {req.tipo_exame}
        </p>
        <p>
          <strong>Data:</strong> {req.created_at}
        </p>
        {laudo?.status === "liberado" && (
          <>
            <div style={{ marginTop: 16, marginBottom: 16 }}>
              <p>
                <strong>Laudo:</strong>
              </p>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  background: "#f9fafb",
                  padding: 16,
                  borderRadius: 6,
                }}
              >
                {laudo.texto}
              </pre>
            </div>
            <button
              onClick={handleBaixarPdf}
              disabled={baixando}
              style={{
                padding: "10px 20px",
                background: "#16a34a",
                color: "#fff",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
              }}
            >
              {baixando ? "Gerando PDF..." : "Baixar PDF"}
            </button>
          </>
        )}
        {(laudo?.status === "pendente" ||
          laudo?.status === "validado" ||
          !laudo) && (
          <p style={{ color: "#6b7280", marginTop: 12 }}>
            O laudo está em análise. Quando for liberado, você poderá baixar o
            PDF aqui.
          </p>
        )}
      </div>
      <div
        className="paics-card"
        style={{
          background: "#fff",
          padding: 20,
          borderRadius: 8,
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}
      >
        <h3 style={{ marginTop: 0 }}>Adicionar observação</h3>
        <p style={{ fontSize: "0.9rem", color: "#6b7280", marginBottom: 12 }}>
          Enviou algo errado ou quer acrescentar um detalhe? O administrador
          verá.
        </p>
        <form onSubmit={handleEnviarObs}>
          <textarea
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            placeholder="Sua observação..."
            rows={3}
            style={{
              width: "100%",
              padding: 10,
              borderRadius: 6,
              border: "1px solid #d1d5db",
              marginBottom: 8,
            }}
          />
          <button
            type="submit"
            disabled={envObs}
            style={{
              padding: "8px 16px",
              background: "#1a2d4a",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            {envObs ? "Enviando..." : "Enviar"}
          </button>
        </form>
        {(req.observacoes_usuario || []).length > 0 && (
          <div style={{ marginTop: 16 }}>
            <p>
              <strong>Suas observações enviadas:</strong>
            </p>
            {req.observacoes_usuario.map((o: any, i: number) => (
              <div
                key={i}
                style={{
                  padding: 10,
                  background: "#f9fafb",
                  borderRadius: 6,
                  marginTop: 8,
                }}
              >
                <p style={{ margin: 0 }}>{o.texto}</p>
                {o.created_at && (
                  <small style={{ color: "#6b7280" }}>{o.created_at}</small>
                )}
              </div>
            ))}
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
            }}
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
