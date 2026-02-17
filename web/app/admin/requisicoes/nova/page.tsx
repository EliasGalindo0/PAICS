"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { listClinicas, listVeterinarios, criarRequisicao } from "@/lib/api";
import { hojeISO } from "@/lib/dateUtils";
import { InputRacaAutocomplete } from "@/app/components/InputRacaAutocomplete";

export default function AdminNovaRequisicaoPage() {
  const router = useRouter();
  const [clinicas, setClinicas] = useState<any[]>([]);
  const [veterinarios, setVeterinarios] = useState<any[]>([]);
  const [clinicaId, setClinicaId] = useState("");
  const [vetPreSelecionado, setVetPreSelecionado] = useState("");
  const [especie, setEspecie] = useState("");
  const [raca, setRaca] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    listClinicas(false).then(setClinicas);
  }, []);

  useEffect(() => {
    if (clinicaId) {
      listVeterinarios(clinicaId).then((vets) => {
        setVeterinarios(vets);
        if (vets.length === 1) setVetPreSelecionado(vets[0].id);
        else setVetPreSelecionado("");
      });
    } else {
      setVeterinarios([]);
      setVetPreSelecionado("");
    }
  }, [clinicaId]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    const form = e.currentTarget;
    const fd = new FormData(form);
    if (!fd.get("paciente") || !fd.get("tutor")) {
      setError("Paciente e tutor são obrigatórios");
      return;
    }
    const files = (form.elements.namedItem("imagens") as HTMLInputElement)
      ?.files;
    if (!files || files.length === 0) {
      setError("Selecione ao menos uma imagem");
      return;
    }
    fd.delete("imagens");
    for (let i = 0; i < files.length; i++) fd.append("imagens", files[i]);
    setLoading(true);
    try {
      const res = await criarRequisicao(fd);
      setSuccess(true);
      form.reset();
      setRaca("");
      setEspecie("");
      setTimeout(() => router.push(`/admin/exames/${res.id}`), 1500);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

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
      <h1
        style={{ fontSize: "1.25rem", marginBottom: 16, textAlign: "center" }}
      >
        Nova Requisição (Admin)
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
          Requisição enviada! Redirecionando...
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
        <div>
          <label>Clínica *</label>
          <select
            name="clinica_id"
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
        </div>
        {clinicaId && (
          <div>
            <label>Veterinário responsável</label>
            <select
              name="veterinario_id"
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
            value={especie}
            onChange={(e) => setEspecie(e.target.value)}
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
            value={raca}
            onChange={setRaca}
            especie={especie || undefined}
          />
        </div>
        <div>
          <label>Idade</label>
          <input
            name="idade"
            style={{
              width: "100%",
              padding: 8,
              borderRadius: 6,
              border: "1px solid #d1d5db",
            }}
          />
        </div>
        <div>
          <label>Sexo</label>
          <select
            name="sexo"
            style={{
              width: "100%",
              padding: 8,
              borderRadius: 6,
              border: "1px solid #d1d5db",
            }}
          >
            <option value="Macho">Macho</option>
            <option value="Fêmea">Fêmea</option>
          </select>
        </div>
        <div>
          <label>Tipo de exame *</label>
          <select
            name="tipo_exame"
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
          <label>Região de estudo</label>
          <input
            name="regiao_estudo"
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
          <label>Data do exame</label>
          <input
            name="data_exame"
            type="date"
            defaultValue={hojeISO()}
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
            name="imagens"
            type="file"
            accept=".jpg,.jpeg,.png,.dcm,.dicom"
            multiple
            required
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: 12,
            background: "#1a2d4a",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: "1rem",
          }}
        >
          {loading ? "Enviando..." : "Enviar Requisição"}
        </button>
      </form>
    </div>
  );
}
