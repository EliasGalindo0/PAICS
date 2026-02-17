"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, getMe } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      setChecking(false);
      return;
    }
    getMe().then((u) => {
      setChecking(false);
      if (u) {
        if (u.primeiro_acesso) router.replace("/alterar-senha");
        else router.replace(u.role === "admin" ? "/admin/exames" : "/user/exames");
      } else router.replace("/login");
    }).catch(() => {
      setChecking(false);
      router.replace("/login");
    });
  }, [router]);

  if (checking) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
          background: "#0a1628",
          color: "#e8edf5",
        }}
      >
        Carregando...
      </div>
    );
  }
  return null;
}
