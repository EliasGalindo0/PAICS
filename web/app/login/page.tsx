"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(email.trim(), password, rememberMe);
      if (res.success && res.user) {
        router.replace(res.user.primeiro_acesso ? "/alterar-senha" : res.user.role === "admin" ? "/admin/exames" : "/user/exames");
      } else {
        setError(res.message || "Erro ao fazer login");
      }
    } catch (err) {
      setError("Erro de conexão. Verifique se a API está rodando em http://localhost:8000");
    } finally {
      setLoading(false);
    }
  };

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
        <h1
          style={{
            fontSize: "1.5rem",
            marginBottom: "0.5rem",
            color: "#1a2d4a",
          }}
        >
          PAICS
        </h1>
        <p style={{ color: "#6b7280", marginBottom: "1.5rem", fontSize: "0.95rem" }}>
          Entre com seu e-mail ou usuário
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label
              htmlFor="email"
              style={{
                display: "block",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "#374151",
                marginBottom: "0.35rem",
              }}
            >
              E-mail ou usuário
            </label>
            <input
              id="email"
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              autoComplete="username"
              style={{
                width: "100%",
                padding: "0.6rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: 6,
                fontSize: "1rem",
              }}
            />
          </div>

          <div style={{ marginBottom: "1rem" }}>
            <label
              htmlFor="password"
              style={{
                display: "block",
                fontSize: "0.875rem",
                fontWeight: 500,
                color: "#374151",
                marginBottom: "0.35rem",
              }}
            >
              Senha
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={{
                width: "100%",
                padding: "0.6rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: 6,
                fontSize: "1rem",
              }}
            />
          </div>

          <div style={{ marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: 8 }}>
            <input
              id="remember"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
            />
            <label htmlFor="remember" style={{ fontSize: "0.875rem", color: "#6b7280" }}>
              Lembrar-me
            </label>
          </div>

          {error && (
            <div
              className="paics-error"
              style={{
                padding: "0.6rem",
                marginBottom: "1rem",
                background: "#fef2f2",
                color: "#b91c1c",
                borderRadius: 6,
                fontSize: "0.875rem",
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.75rem",
              background: loading ? "#94a3b8" : "#1a2d4a",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: "1rem",
              fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
