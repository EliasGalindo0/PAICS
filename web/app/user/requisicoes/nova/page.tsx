"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  getMe,
  listClinicas,
  listVeterinarios,
  criarRequisicao,
  salvarRascunho,
  listRascunhos,
} from "@/lib/api";
import { hojeISO, dateToISOLocal } from "@/lib/dateUtils";
import { InputRacaAutocomplete } from "@/app/components/InputRacaAutocomplete";

function formatRascunho(r: any): string {
  const dt = r.data_exame || r.created_at;
  const d = dt ? new Date(dt).toLocaleDateString("pt-BR") : "—";
  return `#${r.id?.slice(-8) || "?"} – ${r.paciente || "Sem nome"} – ${d}`;
}

const initialForm = {
  paciente: "",
  tutor: "",
  especie: "",
  raca: "",
  idade: "",
  regiao_estudo: "",
  suspeita_clinica: "",
  historico_clinico: "",
  tipo_exame: "raio-x",
  data_exame: hojeISO(),
  sexo: "Macho",
  plantao: "Não",
};

export default function UserNovaRequisicaoPage() {
  const router = useRouter();
  const [clinicas, setClinicas] = useState<any[]>([]);
  const [veterinarios, setVeterinarios] = useState<any[]>([]);
  const [clinicaId, setClinicaId] = useState("");
  const [vetPreSelecionado, setVetPreSelecionado] = useState("");
  const [form, setForm] = useState(initialForm);
  const [rascunhoId, setRascunhoId] = useState<string | null>(null);
  const [rascunhos, setRascunhos] = useState<any[]>([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [uploadKey, setUploadKey] = useState(0);

  const loadRascunhos = useCallback(() => {
    listRascunhos().then(setRascunhos).catch(() => setRascunhos([]));
  }, []);

  useEffect(() => {
    getMe()
      .then((me) => {
        listClinicas(true).then((c) => {
          setClinicas(c);
          if (me?.clinica_id) {
            setClinicaId(me.clinica_id);
          }
        });
        setPageLoading(false);
      })
      .catch(() => setPageLoading(false));
    loadRascunhos();
  }, [loadRascunhos]);

  useEffect(() => {
    if (clinicaId) {
      listVeterinarios(clinicaId).then((vets) => {
        setVeterinarios(vets);
        if (vets.length === 1) setVetPreSelecionado(vets[0].id);
        else setVetPreSelecionado((prev) => (vets.some((v) => v.id === prev) ? prev : ""));
      });
    } else {
      setVeterinarios([]);
      setVetPreSelecionado("");
    }
  }, [clinicaId]);

  const loadRascunho = (r: any) => {
    setForm({
      paciente: r.paciente || "",
      tutor: r.tutor || "",
      especie: r.especie || "",
      raca: r.raca || "",
      idade: r.idade || "",
      regiao_estudo: r.regiao_estudo || "",
      suspeita_clinica: r.suspeita_clinica || "",
      historico_clinico: r.historico_clinico || r.observacoes || "",
      tipo_exame: r.tipo_exame || "raio-x",
      data_exame: r.data_exame
        ? dateToISOLocal(r.data_exame)
        : hojeISO(),
      sexo: r.sexo || "Macho",
      plantao: r.plantao || "Não",
    });
    if (r.clinica_id) setClinicaId(r.clinica_id);
    if (r.veterinario_id) setVetPreSelecionado(r.veterinario_id);
    setRascunhoId(r.id);
    setUploadKey((k) => k + 1);
  };

  const clearForm = () => {
    setForm(initialForm);
    setRascunhoId(null);
    setClinicaId("");
    setVetPreSelecionado("");
    if (veterinarios.length === 1) setVetPreSelecionado(veterinarios[0].id);
    setUploadKey((k) => k + 1);
    setError("");
  };

  const buildRascunhoFormData = (): FormData => {
    const fd = new FormData();
    fd.set("paciente", form.paciente.trim());
    fd.set("tutor", form.tutor.trim());
    fd.set("tipo_exame", form.tipo_exame);
    fd.set("especie", form.especie);
    fd.set("raca", form.raca);
    fd.set("idade", form.idade);
    fd.set("regiao_estudo", form.regiao_estudo);
    fd.set("suspeita_clinica", form.suspeita_clinica);
    fd.set("sexo", form.sexo);
    fd.set("plantao", form.plantao);
    fd.set("historico_clinico", form.historico_clinico);
    fd.set("data_exame", form.data_exame);
    fd.set("clinica", clinicaAtual?.nome || "");
    if (clinicaId) fd.set("clinica_id", clinicaId);
    if (vetPreSelecionado) fd.set("veterinario_id", vetPreSelecionado);
    if (rascunhoId) fd.set("rascunho_id", rascunhoId);
    return fd;
  };

  const handleSalvarRascunho = async () => {
    if (!form.paciente.trim() || !form.tutor.trim()) {
      setError("Paciente e tutor são obrigatórios para salvar rascunho");
      return;
    }
    setSavingDraft(true);
    setError("");
    try {
      const fd = buildRascunhoFormData();
      const res = await salvarRascunho(fd);
      setRascunhoId(res.id ?? null);
      loadRascunhos();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSavingDraft(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    if (!form.paciente.trim() || !form.tutor.trim()) {
      setError("Paciente e tutor são obrigatórios");
      return;
    }
    const formEl = e.currentTarget;
    const files = (formEl.elements.namedItem("imagens") as HTMLInputElement)
      ?.files;
    if (!files || files.length === 0) {
      setError("Selecione ao menos uma imagem");
      return;
    }
    const fd = buildRascunhoFormData();
    fd.delete("rascunho_id");
    for (let i = 0; i < files.length; i++) fd.append("imagens", files[i]);
    setSubmitting(true);
    try {
      await criarRequisicao(fd);
      setSuccess(true);
      clearForm();
      setTimeout(() => router.push("/user/exames"), 2000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const clinicaAtual =
    clinicas.find((c) => c.id === clinicaId) ||
    (clinicaId && veterinarios.length > 0
      ? { id: clinicaId, nome: "Sua clínica" }
      : null);
  const mostrarClinicSelect = !clinicaId && clinicas.length > 0;

  return (
    <div
      style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "0 24px",
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      <h1 style={{ fontSize: "1.25rem", marginBottom: 16 }}>
        Nova Requisição de Laudo
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
        </div>
      )}
      {success && (
        <div
          style={{
            padding: 10,
            background: "#dcfce7",
            color: "#166534",
            borderRadius: 6,
            marginBottom: 12,
          }}
        >
          Requisição enviada! O laudo será gerado e liberado pelo administrador.
        </div>
      )}
      {pageLoading ? (
        <p>Carregando...</p>
      ) : (
        <>
          {rascunhos.length > 0 && (
            <div
              style={{
                marginBottom: 20,
                padding: 12,
                background: "#f9fafb",
                borderRadius: 8,
                border: "1px solid #e5e7eb",
              }}
            >
              <label style={{ display: "block", marginBottom: 8, fontSize: "0.9rem" }}>
                Carregar rascunho
              </label>
              <select
                onChange={(e) => {
                  const idx = parseInt(e.target.value, 10);
                  if (idx >= 0 && rascunhos[idx]) loadRascunho(rascunhos[idx]);
                  else clearForm();
                }}
                style={{
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                  minWidth: 280,
                }}
              >
                <option value="-1">(nenhum)</option>
                {rascunhos.map((r, i) => (
                  <option key={r.id} value={i}>
                    {formatRascunho(r)}
                  </option>
                ))}
              </select>
            </div>
          )}
          <form
            onSubmit={handleSubmit}
            style={{
              width: "100%",
              maxWidth: 900,
              margin: "0 auto",
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {(clinicaId || mostrarClinicSelect) && (
              <div>
                <label>Clínica</label>
                {clinicaId && clinicaAtual ? (
                  <input
                    type="text"
                    value={clinicaAtual.nome}
                    readOnly
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                      background: "#f9fafb",
                    }}
                  />
                ) : (
                  <select
                    value={clinicaId}
                    onChange={(e) => setClinicaId(e.target.value)}
                    required
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                    }}
                  >
                    <option value="">Selecione</option>
                    {clinicas.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
            {clinicaId && (
              <div>
                <label>Veterinário requisitante</label>
                <select
                  value={vetPreSelecionado}
                  onChange={(e) => setVetPreSelecionado(e.target.value)}
                  style={{
                    width: "100%",
                    padding: 8,
                    borderRadius: 6,
                    border: "1px solid #d1d5db",
                  }}
                >
                  <option value="">Selecione</option>
                  {veterinarios.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.nome}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label>Paciente *</label>
              <input
                name="paciente"
                value={form.paciente}
                onChange={(e) =>
                  setForm((p) => ({ ...p, paciente: e.target.value }))
                }
                required
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              />
            </div>
            <div>
              <label>Tutor *</label>
              <input
                name="tutor"
                value={form.tutor}
                onChange={(e) =>
                  setForm((p) => ({ ...p, tutor: e.target.value }))
                }
                required
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              />
            </div>
            <div>
              <label>Espécie</label>
              <select
                name="especie"
                value={form.especie}
                onChange={(e) =>
                  setForm((p) => ({ ...p, especie: e.target.value }))
                }
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              >
                <option value="">Selecione</option>
                <option value="Canino">Canino</option>
                <option value="Felino">Felino</option>
                <option value="Ave">Ave</option>
                <option value="Silvestre">Silvestre</option>
              </select>
            </div>
            <div>
              <label>Raça</label>
              <InputRacaAutocomplete
                name="raca"
                value={form.raca}
                onChange={(v) => setForm((p) => ({ ...p, raca: v }))}
                especie={form.especie || undefined}
              />
            </div>
            <div>
              <label>Idade</label>
              <input
                name="idade"
                value={form.idade}
                onChange={(e) =>
                  setForm((p) => ({ ...p, idade: e.target.value }))
                }
                placeholder="Ex: 2 anos, 6 meses"
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              />
            </div>
            <div>
              <label>Região de estudo</label>
              <input
                name="regiao_estudo"
                value={form.regiao_estudo}
                onChange={(e) =>
                  setForm((p) => ({ ...p, regiao_estudo: e.target.value }))
                }
                placeholder="Ex: Tórax, Abdômen, Membros"
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              />
            </div>
            <div>
              <label>Suspeita clínica</label>
              <input
                name="suspeita_clinica"
                value={form.suspeita_clinica}
                onChange={(e) =>
                  setForm((p) => ({ ...p, suspeita_clinica: e.target.value }))
                }
                placeholder="Ex: Fratura, corpo estranho"
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              />
            </div>
            <div>
              <label>Histórico clínico</label>
              <textarea
                name="historico_clinico"
                value={form.historico_clinico}
                onChange={(e) =>
                  setForm((p) => ({ ...p, historico_clinico: e.target.value }))
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
            <div>
              <label>Tipo de exame *</label>
              <select
                name="tipo_exame"
                value={form.tipo_exame}
                onChange={(e) =>
                  setForm((p) => ({ ...p, tipo_exame: e.target.value }))
                }
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              >
                <option value="raio-x">Raio-X</option>
                <option value="ultrassom">Ultrassom</option>
              </select>
            </div>
            <div>
              <label>Data do exame</label>
              <input
                name="data_exame"
                type="date"
                value={form.data_exame}
                onChange={(e) =>
                  setForm((p) => ({ ...p, data_exame: e.target.value }))
                }
                style={{
                  width: "100%",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid #d1d5db",
                }}
              />
            </div>
            <div>
              <label>Imagens * (JPG, PNG, DICOM)</label>
              <input
                key={uploadKey}
                name="imagens"
                type="file"
                accept=".jpg,.jpeg,.png,.dcm,.dicom"
                multiple
                required
                style={{ width: "100%", padding: 8 }}
              />
            </div>
            <div
              style={{
                display: "flex",
                gap: 12,
                flexWrap: "wrap",
                marginTop: 8,
              }}
            >
              <button
                type="submit"
                disabled={submitting}
                style={{
                  padding: 12,
                  background: "#1a2d4a",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor: submitting ? "not-allowed" : "pointer",
                  fontSize: "1rem",
                }}
              >
                {submitting ? "Enviando..." : "Enviar Requisição"}
              </button>
              <button
                type="button"
                onClick={handleSalvarRascunho}
                disabled={
                  savingDraft || !form.paciente.trim() || !form.tutor.trim()
                }
                style={{
                  padding: 12,
                  background: "#6b7280",
                  color: "#fff",
                  border: "none",
                  borderRadius: 6,
                  cursor:
                    savingDraft || !form.paciente.trim() || !form.tutor.trim()
                      ? "not-allowed"
                      : "pointer",
                  fontSize: "1rem",
                }}
              >
                {savingDraft ? "Salvando..." : "Salvar rascunho"}
              </button>
              <button
                type="button"
                onClick={clearForm}
                style={{
                  padding: 12,
                  background: "#e5e7eb",
                  color: "#374151",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: "1rem",
                }}
              >
                Limpar formulário
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
