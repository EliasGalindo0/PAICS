"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getMe } from "@/lib/api";
import DashboardLayout from "../components/DashboardLayout";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<{ nome: string; username: string; role: string } | null>(null);

  useEffect(() => {
    getMe().then((u) => {
      if (!u) {
        router.replace("/login");
        return;
      }
      if (u.primeiro_acesso) {
        router.replace("/alterar-senha");
        return;
      }
      if (u.role !== "admin") {
        router.replace("/user/exames");
        return;
      }
      setUser(u);
    });
  }, [router]);

  if (!user) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        Carregando...
      </div>
    );
  }

  return <DashboardLayout user={user}>{children}</DashboardLayout>;
}
