"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  listClinicas,
  listVeterinarios,
  criarRequisicao,
  listRegioesEstudo,
  parseRequisicaoTemplate,
} from "@/lib/api";
import { hojeISO } from "@/lib/dateUtils";
import { InputRacaAutocomplete } from "@/app/components/InputRacaAutocomplete";

function normNome(s: string) {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function matchVeterinarioId(
  nome: string,
  vets: { id: string; nome: string }[]
): string {
  const n = normNome(nome);
  if (!n || !vets.length) return "";
  const exact = vets.find((v) => normNome(v.nome) === n);
  if (exact) return exact.id;
  const partial = vets.find(
    (v) => normNome(v.nome).includes(n) || n.includes(normNome(v.nome))
  );
  return partial?.id || "";
}

function setFormField(form: HTMLFormElement, name: string, value: string) {
  const el = form.elements.namedItem(name);
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
    el.value = value || "";
  }
}

export default function AdminNovaRequisicaoPage() {
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const [clinicas, setClinicas] = useState<any[]>([]);
  const [veterinarios, setVeterinarios] = useState<any[]>([]);
  const [regioesEstudo, setRegioesEstudo] = useState<
    { value: string; label: string }[]
  >([]);
  const [regioesEstudoSelecionadas, setRegioesEstudoSelecionadas] = useState<
    string[]
  >([]);
  const [regiaoEstudoOutra, setRegiaoEstudoOutra] = useState("");
  const [clinicaId, setClinicaId] = useState("");
  const [vetPreSelecionado, setVetPreSelecionado] = useState("");
  const [especie, setEspecie] = useState("");
  const [raca, setRaca] = useState("");
  const [plantao, setPlantao] = useState("Não");
  const [sedacao, setSedacao] = useState("Não");
  const [templateTexto, setTemplateTexto] = useState("");
  const [parseMsg, setParseMsg] = useState("");
  const [parsing, setParsing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [vetPendente, setVetPendente] = useState("");
  const vetPendenteRef = useRef("");

  useEffect(() => {
    listClinicas(false).then(setClinicas);
    listRegioesEstudo()
      .then(setRegioesEstudo)
      .catch(() => setRegioesEstudo([]));
  }, []);

  useEffect(() => {
    if (clinicaId) {
      listVeterinarios(clinicaId).then((vets) => {
        setVeterinarios(vets);
        const pendente = vetPendenteRef.current;
        if (pendente) {
          setVetPreSelecionado(matchVeterinarioId(pendente, vets) || "");
          vetPendenteRef.current = "";
          setVetPendente("");
        } else if (vets.length === 1) {
          setVetPreSelecionado(vets[0].id);
        } else if (!vetPreSelecionado) {
          setVetPreSelecionado("");
        }
      });
    } else {
      setVeterinarios([]);
      setVetPreSelecionado("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clinicaId]);

  const handleExtrairTemplate = async () => {
    setParseMsg("");
    setError("");
    if (!templateTexto.trim()) {
      setParseMsg("Cole o texto do template antes de extrair.");
      return;
    }
    setParsing(true);
    try {
      const dados = await parseRequisicaoTemplate(templateTexto);
      const form = formRef.current;
      if (!form) return;

      setFormField(form, "paciente", dados.paciente);
      setFormField(form, "tutor", dados.tutor);
      setFormField(form, "idade", dados.idade);
      setFormField(form, "suspeita_clinica", dados.suspeita_clinica);
      if (dados.historico_clinico) {
        setFormField(form, "historico_clinico", dados.historico_clinico);
      }
      if (dados.data_exame) {
        setFormField(form, "data_exame", dados.data_exame);
      }

      if (dados.especie) setEspecie(dados.especie);
      if (dados.raca) setRaca(dados.raca);
      if (dados.plantao) setPlantao(dados.plantao);
      if (dados.sedacao) setSedacao(dados.sedacao);
      setRegioesEstudoSelecionadas(dados.regioes_estudo || []);
      setRegiaoEstudoOutra(dados.regiao_estudo_outra || "");

      if (dados.medico_veterinario_solicitante) {
        if (clinicaId && veterinarios.length) {
          setVetPreSelecionado(
            matchVeterinarioId(
              dados.medico_veterinario_solicitante,
              veterinarios
            )
          );
        } else {
          vetPendenteRef.current = dados.medico_veterinario_solicitante;
          setVetPendente(dados.medico_veterinario_solicitante);
          if (clinicaId) {
            listVeterinarios(clinicaId).then((vets) => {
              setVeterinarios(vets);
              setVetPreSelecionado(
                matchVeterinarioId(
                  dados.medico_veterinario_solicitante,
                  vets
                )
              );
              vetPendenteRef.current = "";
              setVetPendente("");
            });
          }
        }
      }

      const n = dados.campos_encontrados?.length || 0;
      const avisoVet =
        dados.medico_veterinario_solicitante && !clinicaId
          ? " Selecione a clínica para vincular o M.V. solicitante."
          : "";
      setParseMsg(
        n > 0
          ? `${n} campo(s) preenchido(s). Revise os dados antes de enviar.${avisoVet}`
          : "Nenhum campo reconhecido. Verifique o formato do template."
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setParsing(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    const form = e.currentTarget;
    const fd = new FormData(form);
    const regiaoFinal = [
      ...regioesEstudoSelecionadas,
      ...(regiaoEstudoOutra.trim() ? [regiaoEstudoOutra.trim()] : []),
    ].join(", ");
    fd.set("regiao_estudo", regiaoFinal);
    fd.set("plantao", plantao);
    fd.set("sedacao", sedacao);
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
      setPlantao("Não");
      setSedacao("Não");
      setRegioesEstudoSelecionadas([]);
      setRegiaoEstudoOutra("");
      setTemplateTexto("");
      setParseMsg("");
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

      <div
        className="paics-template-paste"
        style={{
          width: "100%",
          maxWidth: 900,
          margin: "0 auto 20px",
          padding: 16,
        }}
      >
        <h2 style={{ fontSize: "1rem", margin: "0 0 8px" }}>
          Colar template da clínica
        </h2>
        <p
          className="paics-template-desc"
          style={{ fontSize: "0.875rem", margin: "0 0 10px" }}
        >
          Cole abaixo a mensagem que a clínica envia (WhatsApp, e-mail etc.) e
          clique em extrair para preencher o formulário automaticamente.
        </p>
        <textarea
          value={templateTexto}
          onChange={(e) => setTemplateTexto(e.target.value)}
          rows={10}
          placeholder={`Exemplo:\nDados para laudo\n\nData: 10/06/2026\n🔹 Nome do paciente: ...\n🔹 Espécie: Canino\n...`}
          style={{
            width: "100%",
            padding: 10,
            borderRadius: 6,
            fontFamily: "inherit",
            fontSize: "0.875rem",
            boxSizing: "border-box",
            resize: "vertical",
          }}
        />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginTop: 10,
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            onClick={handleExtrairTemplate}
            disabled={parsing}
            style={{
              padding: "8px 16px",
              background: "#0f766e",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: parsing ? "wait" : "pointer",
              fontSize: "0.9rem",
            }}
          >
            {parsing ? "Extraindo..." : "Extrair e preencher"}
          </button>
          {parseMsg && (
            <span className="paics-template-msg" style={{ fontSize: "0.875rem" }}>
              {parseMsg}
            </span>
          )}
        </div>
      </div>

      <form
        ref={formRef}
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
          <label>
            Regiões de estudo (máscara para o laudo) – selecione uma ou mais
          </label>
          <div className="paics-regioes-grid" style={{ marginTop: 8 }}>
            {regioesEstudo
              .filter((r) => r.value && r.value !== "__outra__")
              .map((r) => (
                <label key={r.value}>
                  <input
                    type="checkbox"
                    checked={regioesEstudoSelecionadas.includes(r.value)}
                    onChange={(e) => {
                      setRegioesEstudoSelecionadas((prev) =>
                        e.target.checked
                          ? [...prev, r.value]
                          : prev.filter((v) => v !== r.value)
                      );
                    }}
                  />
                  {r.label}
                </label>
              ))}
          </div>
          <input
            type="text"
            value={regiaoEstudoOutra}
            onChange={(e) => setRegiaoEstudoOutra(e.target.value)}
            placeholder="Outra região (opcional – digite para adicionar)"
            className="paics-input"
            style={{
              width: "100%",
              marginTop: 10,
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
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 140px" }}>
            <label>Plantão</label>
            <select
              value={plantao}
              onChange={(e) => setPlantao(e.target.value)}
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 6,
                border: "1px solid #d1d5db",
              }}
            >
              <option value="Não">Não</option>
              <option value="Sim">Sim</option>
            </select>
          </div>
          <div style={{ flex: "1 1 140px" }}>
            <label>Sedação</label>
            <select
              value={sedacao}
              onChange={(e) => setSedacao(e.target.value)}
              style={{
                width: "100%",
                padding: 8,
                borderRadius: 6,
                border: "1px solid #d1d5db",
              }}
            >
              <option value="Não">Não</option>
              <option value="Sim">Sim</option>
            </select>
          </div>
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
