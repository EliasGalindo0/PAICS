"use client";

import { ReactNode, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/api";
import { useTheme } from "./ThemeProvider";

const SIDEBAR_WIDTH = 220;

const ADMIN_NAV = [
  { href: "/admin/exames", label: "Exames" },
  { href: "/admin/requisicoes/nova", label: "Nova Requisição" },
  { href: "/admin/clinicas", label: "Clínicas e Usuários" },
  { href: "/admin/financeiro", label: "Financeiro" },
  { href: "/admin/knowledge-base", label: "Knowledge Base" },
];

const USER_NAV = [
  { href: "/user/exames", label: "Meus Exames" },
  { href: "/user/requisicoes/nova", label: "Nova Requisição" },
  { href: "/user/faturas", label: "Minhas Faturas" },
];

interface Props {
  user: { nome: string; username: string; role: string };
  children: ReactNode;
}

export default function DashboardLayout({ user, children }: Props) {
  const pathname = usePathname();
  const nav = user.role === "admin" ? ADMIN_NAV : USER_NAV;
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const theme = useTheme();

  const handleLogout = async () => {
    await logout();
    window.location.href = "/login";
  };

  return (
    <div
      className="dashboard-wrapper"
      style={{ minHeight: "100vh", display: "flex" }}
    >
      {/* Botão para abrir sidebar quando oculta */}
      {!sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          aria-label="Mostrar menu"
          style={{
            position: "fixed",
            left: 0,
            top: "50%",
            transform: "translateY(-50%)",
            width: 28,
            height: 48,
            background: "#1a2d4a",
            color: "#fff",
            border: "none",
            borderTopRightRadius: 6,
            borderBottomRightRadius: 6,
            cursor: "pointer",
            zIndex: 1001,
            fontSize: "1.1rem",
            padding: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "2px 0 6px rgba(0,0,0,0.15)",
          }}
        >
          ›
        </button>
      )}

      <aside
        style={{
          position: "fixed",
          top: 0,
          left: sidebarOpen ? 0 : -SIDEBAR_WIDTH,
          width: SIDEBAR_WIDTH,
          height: "100vh",
          background: "#1a2d4a",
          color: "#fff",
          padding: "1rem 0",
          display: "flex",
          flexDirection: "column",
          zIndex: 1000,
          transition: "left 0.25s ease",
          boxShadow: sidebarOpen ? "4px 0 20px rgba(0,0,0,0.12)" : "none",
        }}
      >
        <div
          style={{
            padding: "0 1rem 1rem",
            borderBottom: "1px solid rgba(255,255,255,0.2)",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2 style={{ fontSize: "1rem", margin: 0 }}>
              {user.role === "admin" ? "Admin" : "Meu"} Dashboard
            </h2>
            <p
              style={{
                fontSize: "0.8rem",
                opacity: 0.9,
                margin: "0.25rem 0 0",
              }}
            >
              {user.nome || user.username}
            </p>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            aria-label="Ocultar menu"
            style={{
              flexShrink: 0,
              width: 28,
              height: 28,
              background: "rgba(255,255,255,0.15)",
              border: "none",
              borderRadius: 4,
              color: "#fff",
              cursor: "pointer",
              fontSize: "1.1rem",
              padding: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            ‹
          </button>
        </div>
        {theme && (
          <div style={{ padding: "0 1rem 0.5rem" }}>
            <button
              onClick={theme.toggle}
              aria-label={theme.theme === "dark" ? "Modo claro" : "Modo escuro"}
              style={{
                width: "100%",
                padding: "6px 10px",
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.2)",
                color: "#fff",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: "0.85rem",
                marginTop: "1rem",
              }}
            >
              {theme.theme === "dark" ? "☀️ Modo claro" : "🌙 Modo escuro"}
            </button>
          </div>
        )}
        <nav style={{ flex: 1, padding: "1rem 0" }}>
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "block",
                padding: "0.5rem 1rem",
                margin: "0 0.5rem",
                borderRadius: 6,
                color: pathname.startsWith(item.href)
                  ? "#fff"
                  : "rgba(255,255,255,0.8)",
                background: pathname.startsWith(item.href)
                  ? "rgba(255,255,255,0.15)"
                  : "transparent",
                textDecoration: "none",
                fontSize: "0.95rem",
                transition: "background 0.15s",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div style={{ padding: "1rem" }}>
          <button
            onClick={handleLogout}
            style={{
              width: "100%",
              padding: "0.5rem",
              background: "rgba(255,255,255,0.1)",
              border: "1px solid rgba(255,255,255,0.2)",
              color: "#fff",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: "0.9rem",
            }}
          >
            Sair
          </button>
        </div>
      </aside>
      <main
        className="paics-main"
        style={{
          flex: 1,
          marginLeft: sidebarOpen ? SIDEBAR_WIDTH : 0,
          padding: "1.5rem 2rem",
          overflow: "auto",
          minHeight: "100vh",
          transition: "margin-left 0.25s ease",
        }}
      >
        {children}
      </main>
    </div>
  );
}
