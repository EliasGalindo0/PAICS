"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe, alterarSenha } from "@/lib/api";

export default function AlterarSenhaPage() {
  const router = useRouter();
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getMe().then((u) => {
      setLoading(false);
      if (!u) {
        router.replace("/login");
        return;
      }
      if (!u.primeiro_acesso) {
        router.replace(u.role === "admin" ? "/admin/exames" : "/user/exames");
      }
    }).catch(() => {
      setLoading(false);
      router.replace("/login");
    });
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (novaSenha.length < 6) {
      setError("A nova senha deve ter pelo menos 6 caracteres");
      return;
    }
    if (novaSenha !== confirmar) {
      setError("As senhas não coincidem");
      return;
    }
    setSubmitting(true);
    try {
      await alterarSenha(senhaAtual, novaSenha);
      const u = await getMe();
      if (u) {
        router.replace(u.role === "admin" ? "/admin/exames" : "/user/exames");
      } else {
        router.replace("/login");
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        Carregando...
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #0a1628 0%, #1a2d4a 100%)",
      }}
    >
      <div
        className="paics-auth-card"
        style={{
          background: "#fff",
          padding: "2rem 2.5rem",
          borderRadius: 12,
          boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
          width: "100%",
          maxWidth: 480,
          margin: "0 16px",
          boxSizing: "border-box",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", marginBottom: "0.5rem", color: "#1a2d4a" }}>
          Alteração de senha obrigatória
        </h1>
        <p style={{ color: "#6b7280", marginBottom: "1.5rem", fontSize: "0.95rem" }}>
          Este é seu primeiro acesso. Crie uma nova senha para substituir a senha temporária.
        </p>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="senha_atual" style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.35rem" }}>
              Senha temporária atual *
            </label>
            <input
              id="senha_atual"
              type="password"
              value={senhaAtual}
              onChange={(e) => setSenhaAtual(e.target.value)}
              required
              style={{ width: "100%", padding: "0.6rem 0.75rem", border: "1px solid #d1d5db", borderRadius: 6 }}
            />
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="nova_senha" style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.35rem" }}>
              Nova senha * (mín. 6 caracteres)
            </label>
            <input
              id="nova_senha"
              type="password"
              value={novaSenha}
              onChange={(e) => setNovaSenha(e.target.value)}
              required
              minLength={6}
              style={{ width: "100%", padding: "0.6rem 0.75rem", border: "1px solid #d1d5db", borderRadius: 6 }}
            />
          </div>
          <div style={{ marginBottom: "1.25rem" }}>
            <label htmlFor="confirmar" style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.35rem" }}>
              Confirmar nova senha *
            </label>
            <input
              id="confirmar"
              type="password"
              value={confirmar}
              onChange={(e) => setConfirmar(e.target.value)}
              required
              style={{ width: "100%", padding: "0.6rem 0.75rem", border: "1px solid #d1d5db", borderRadius: 6 }}
            />
          </div>
          {error && (
            <div className="paics-error" style={{ padding: "0.6rem", marginBottom: "1rem", background: "#fef2f2", color: "#b91c1c", borderRadius: 6, fontSize: "0.875rem" }}>
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={submitting}
            style={{
              width: "100%",
              padding: "0.75rem",
              background: submitting ? "#94a3b8" : "#1a2d4a",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: "1rem",
              fontWeight: 500,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? "Alterando..." : "Alterar senha"}
          </button>
        </form>
      </div>
    </div>
  );
}
