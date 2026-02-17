"""
Rotas de exames (requisições + laudos) para admin e user
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response
from pydantic import BaseModel
import io
import base64
from database.connection import get_db
from database.models import Requisicao, Laudo, User, Clinica, Veterinario
from database.image_storage import get_image, get_filename, get_image_bytes_and_filename
from utils.timezone import now, combine_date_local, get_date_start, get_date_end, local_to_utc

from api.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/exames", tags=["exames"])


def _date_to_ymd(val) -> str:
    """Converte para YYYY-MM-DD usando atributos (evita comparação naive/aware)."""
    if val is None:
        return ""
    if isinstance(val, str) and len(val) >= 10:
        return val[:10]
    if hasattr(val, "year") and hasattr(val, "month") and hasattr(val, "day"):
        try:
            return f"{val.year:04d}-{val.month:02d}-{val.day:02d}"
        except (TypeError, ValueError):
            pass
    try:
        return str(val)[:10] if val else ""
    except Exception:
        return ""


def _fmt_dt(x):
    if x is None:
        return None
    if hasattr(x, "strftime"):
        try:
            return x.strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            if hasattr(x, "year") and hasattr(x, "month") and hasattr(x, "day"):
                try:
                    return f"{x.day:02d}/{x.month:02d}/{x.year:04d} {x.hour:02d}:{x.minute:02d}" if hasattr(x, "hour") else f"{x.day:02d}/{x.month:02d}/{x.year:04d}"
                except (TypeError, ValueError):
                    pass
            return str(x)[:16]
    s = str(x)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            dt = datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
    return s[:16]


def _upper(s):
    return (s or "").strip().upper() if isinstance(s, str) else s


def _req_clinica_vet(req, user_model, clinica_model, veterinario_model):
    user = user_model.find_by_id(req.get("user_id")) if req.get("user_id") else None
    clinica_nome = None
    if req.get("clinica_id"):
        c = clinica_model.find_by_id(req["clinica_id"])
        clinica_nome = (c or {}).get("nome") if c else None
    if not clinica_nome and (req.get("clinica") or "").strip():
        clinica_nome = req.get("clinica")
    if not clinica_nome and user and user.get("clinica_id"):
        c = clinica_model.find_by_id(user["clinica_id"])
        clinica_nome = (c or {}).get("nome") if c else None

    vet_nome = None
    if req.get("veterinario_id"):
        v = veterinario_model.find_by_id(req["veterinario_id"])
        vet_nome = (v or {}).get("nome") if v else None
    if not vet_nome and (req.get("medico_veterinario_solicitante") or "").strip():
        vet_nome = req.get("medico_veterinario_solicitante")
    if not vet_nome and user and user.get("clinica_id"):
        vets = veterinario_model.find_by_clinica(user["clinica_id"], apenas_ativos=True)
        vet_nome = (vets[0].get("nome") if vets else None) or ""
    return (clinica_nome or "—", vet_nome or "—")


class ObservacaoRequest(BaseModel):
    texto: str


class LaudoUpdateRequest(BaseModel):
    texto: str


class GerarLaudoRequest(BaseModel):
    imagens_refs: Optional[list[str]] = None


class RegenerarLaudoRequest(BaseModel):
    correcoes: str


class RequisicaoUpdateRequest(BaseModel):
    """Campos editáveis da requisição (com histórico para auditoria)"""
    paciente: Optional[str] = None
    tutor: Optional[str] = None
    especie: Optional[str] = None
    idade: Optional[str] = None
    raca: Optional[str] = None
    regiao_estudo: Optional[str] = None
    suspeita_clinica: Optional[str] = None
    historico_clinico: Optional[str] = None


@router.get("")
def listar_exames(
    status: Optional[str] = None,
    tipo_exame: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """Lista exames com filtros. Admin vê todos; user vê só os seus."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)

    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None
    if start_date and len(start_date) >= 10:
        try:
            d = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
            sd = local_to_utc(get_date_start(combine_date_local(d)))
            start_dt = sd.replace(tzinfo=None) if sd.tzinfo else sd
        except Exception:
            pass
    if end_date and len(end_date) >= 10:
        try:
            d = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
            ed = local_to_utc(get_date_end(combine_date_local(d)))
            end_dt = ed.replace(tzinfo=None) if ed.tzinfo else ed
        except Exception:
            pass

    if user["role"] == "admin":
        exames = req_model.find_all(status=status, start_date=start_dt, end_date=end_dt)
    else:
        exames = req_model.find_by_user(
            user["id"], status=status,
            start_date=start_dt if start_date else None,
            end_date=end_dt if end_date else None,
        )
        exames = [e for e in exames if e.get("status") != "rascunho"]

    if tipo_exame:
        exames = [e for e in exames if e.get("tipo_exame") == tipo_exame]

    if search:
        s = search.lower().strip()

        def _searchable(r):
            parts = [
                r.get("paciente", ""), r.get("tutor", ""), r.get("clinica", ""),
                r.get("especie", ""), r.get("raca", ""), r.get("medico_veterinario_solicitante", ""),
                r.get("regiao_estudo", ""), r.get("suspeita_clinica", ""),
                (r.get("historico_clinico") or r.get("observacoes", "")),
            ]
            return " ".join(str(p or "") for p in parts).lower()
        exames = [e for e in exames if s in _searchable(e)]

    exames = exames[:limit]
    laudos_map = laudo_model.find_by_requisicao_ids([e["id"] for e in exames]) if exames else {}

    result = []
    for req in exames:
        created = req.get("created_at") or req.get("data_exame")
        laudo = laudos_map.get(req["id"])
        liberado_at = None
        if laudo and laudo.get("status") == "liberado":
            la = laudo.get("liberado_at")
            if la:
                liberado_at = la if isinstance(la, str) else (
                    f"{_date_to_ymd(la)}T{la.hour:02d}:{la.minute:02d}:{la.second:02d}" if hasattr(la, "hour") else str(la)
                )
        created_raw = ""
        if created:
            if isinstance(created, str):
                created_raw = created
            elif hasattr(created, "year") and hasattr(created, "hour"):
                created_raw = f"{_date_to_ymd(created)}T{created.hour:02d}:{created.minute:02d}:{created.second:02d}"
            elif hasattr(created, "year"):
                created_raw = _date_to_ymd(created) + "T00:00:00"
            else:
                created_raw = str(created)
        result.append({
            "id": req["id"],
            "paciente": req.get("paciente", "N/A"),
            "tutor": req.get("tutor", "N/A"),
            "clinica": req.get("clinica", "N/A"),
            "status": req.get("status", "N/A"),
            "tipo_exame": req.get("tipo_exame", "N/A"),
            "created_at": _fmt_dt(created),
            "created_at_raw": created_raw,
            "n_imagens": len(req.get("imagens") or []),
            "tem_laudo": req["id"] in laudos_map,
            "liberado_at": liberado_at,
        })
    return result


@router.get("/{exame_id}")
def obter_exame(exame_id: str, user: dict = Depends(get_current_user)):
    """Detalhes completos de um exame (requisição + laudo)."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)
    user_model = User(db.users)
    clinica_model = Clinica(db.clinicas)
    veterinario_model = Veterinario(db.veterinarios)

    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    if user["role"] != "admin" and req.get("user_id") != user["id"]:
        raise HTTPException(403, "Sem permissão para este exame")

    laudo = laudo_model.find_by_requisicao(exame_id)
    clinica_display, vet_display = _req_clinica_vet(req, user_model, clinica_model, veterinario_model)
    user_req = user_model.find_by_id(req.get("user_id")) if req.get("user_id") else None

    return {
        "requisicao": {
            "id": req["id"],
            "paciente": req.get("paciente", "N/A"),
            "tutor": req.get("tutor", "N/A"),
            "clinica": clinica_display,
            "medico_veterinario_solicitante": vet_display,
            "especie": req.get("especie", ""),
            "idade": req.get("idade", ""),
            "raca": req.get("raca", ""),
            "sexo": req.get("sexo", ""),
            "regiao_estudo": req.get("regiao_estudo", ""),
            "suspeita_clinica": req.get("suspeita_clinica", ""),
            "plantao": req.get("plantao", ""),
            "tipo_exame": req.get("tipo_exame", "N/A"),
            "historico_clinico": req.get("historico_clinico") or req.get("observacoes", ""),
            "status": req.get("status", "N/A"),
            "imagens": req.get("imagens") or [],
            "created_at": _fmt_dt(req.get("created_at") or req.get("data_exame")),
            "observacoes_usuario": req.get("observacoes_usuario") or [],
            "historico_edicoes": req.get("historico_edicoes") or [],
            "user": {"nome": user_req.get("nome", user_req.get("username")) if user_req else "—"} if user_req else None,
        },
        "laudo": {
            "id": laudo["id"],
            "texto": laudo.get("texto", ""),
            "status": laudo.get("status", "pendente"),
            "created_at": _fmt_dt(laudo.get("created_at")),
            "validado_at": _fmt_dt(laudo.get("validado_at")),
            "liberado_at": _fmt_dt(laudo.get("liberado_at")),
            "imagens_usadas": laudo.get("imagens_usadas") or [],
        } if laudo else None,
    }


@router.get("/{exame_id}/imagens/{ref}")
def obter_imagem(exame_id: str, ref: str, user: dict = Depends(get_current_user)):
    """Retorna imagem como PNG. Ref = ID GridFS da imagem."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    if user["role"] != "admin" and req.get("user_id") != user["id"]:
        raise HTTPException(403, "Sem permissão")
    refs = [str(r) for r in (req.get("imagens") or [])]
    # Aceitar ref exato ou como sufixo (para IDs longos)
    img_ref = None
    for r in refs:
        if r == ref or r.endswith(ref) or ref in r:
            img_ref = r
            break
    if not img_ref:
        raise HTTPException(404, "Imagem não encontrada nesta requisição")

    result = get_image_bytes_and_filename(img_ref)
    if result:
        data, fn = result
        try:
            from ai.analyzer import _load_image_from_bytes
            img = _load_image_from_bytes(data, fn)
            if img:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                return Response(content=buf.read(), media_type="image/png")
        except Exception:
            pass
        return Response(content=data, media_type="application/octet-stream")
    raw = get_image(img_ref)
    if not raw:
        raise HTTPException(404, "Imagem não encontrada")
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception:
        return Response(content=raw, media_type="application/octet-stream")


@router.post("/{exame_id}/observacao")
def adicionar_observacao(exame_id: str, body: ObservacaoRequest, user: dict = Depends(get_current_user)):
    """Adiciona observação do usuário ao exame."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    if req.get("user_id") != user["id"]:
        raise HTTPException(403, "Sem permissão")
    if not body.texto or not body.texto.strip():
        raise HTTPException(400, "Texto da observação é obrigatório")
    req_model.add_observacao_usuario(exame_id, body.texto.strip(), user["id"])
    return {"success": True}


@router.patch("/{exame_id}/requisicao")
def atualizar_requisicao(
    exame_id: str,
    body: RequisicaoUpdateRequest,
    user: dict = Depends(require_admin),
):
    """Atualiza dados da requisição com histórico para auditoria."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"success": True}
    if "paciente" in updates:
        updates["paciente"] = _upper(updates["paciente"])
    if "tutor" in updates:
        updates["tutor"] = _upper(updates["tutor"])
    if "raca" in updates:
        updates["raca"] = _upper(updates["raca"])
    if "regiao_estudo" in updates:
        updates["regiao_estudo"] = _upper(updates["regiao_estudo"])
    if "suspeita_clinica" in updates:
        updates["suspeita_clinica"] = _upper(updates["suspeita_clinica"])
    if "historico_clinico" in updates:
        updates["historico_clinico"] = _upper(updates["historico_clinico"])
        updates["observacoes"] = _upper(updates["historico_clinico"])
    if not req_model.update_with_history(exame_id, updates, user["id"]):
        raise HTTPException(500, "Erro ao atualizar requisição")
    return {"success": True}


@router.post("/{exame_id}/gerar-laudo")
def gerar_laudo(
    exame_id: str,
    body: Optional[GerarLaudoRequest] = Body(None),
    user: dict = Depends(require_admin),
):
    """Gera laudo com IA (admin). Aceita imagens_refs opcional para selecionar imagens."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)
    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    if laudo_model.find_by_requisicao(exame_id):
        raise HTTPException(400, "Exame já possui laudo")
    todas_refs = req.get("imagens") or []
    imagens_refs = (body.imagens_refs if body and body.imagens_refs else todas_refs)
    if not imagens_refs:
        raise HTTPException(400, "Exame sem imagens ou nenhuma imagem selecionada")
    try:
        from ai.analyzer import load_images_for_analysis
        from ai.learning_system import LearningSystem
        images = load_images_for_analysis(imagens_refs)
        _obs = "\n".join(o.get("texto", "").strip() for o in (req.get("observacoes_usuario") or []) if o.get("texto", "").strip())
        paciente_info = {
            "especie": req.get("especie", ""),
            "raca": req.get("raca", ""),
            "idade": req.get("idade", ""),
            "sexo": req.get("sexo", ""),
            "historico_clinico": (req.get("historico_clinico") or req.get("observacoes", "")),
            "suspeita_clinica": req.get("suspeita_clinica", ""),
            "regiao_estudo": req.get("regiao_estudo", ""),
            "observacoes_adicionais_usuario": _obs,
        }
        ls = LearningSystem()
        texto_gerado, metadata = ls.generate_laudo(images, paciente_info, exame_id)
        laudo_id = laudo_model.create(
            requisicao_id=exame_id,
            texto=texto_gerado,
            texto_original=texto_gerado,
            status="pendente",
            modelo_usado=metadata.get("modelo_usado", "api_externa"),
            usado_api_externa=metadata.get("usado_api_externa", True),
            imagens_usadas=imagens_refs,
            similaridade_casos=metadata.get("similaridade_casos"),
        )
        return {"success": True, "laudo_id": laudo_id}
    except Exception as e:
        laudo_model.create(requisicao_id=exame_id, texto="", texto_original="", status="pendente")
        raise HTTPException(500, f"Erro ao gerar laudo: {str(e)}")


@router.patch("/{exame_id}/laudo")
def atualizar_laudo(exame_id: str, body: LaudoUpdateRequest, user: dict = Depends(require_admin)):
    """Atualiza texto do laudo (admin)."""
    db = get_db()
    laudo_model = Laudo(db.laudos)
    laudo = laudo_model.find_by_requisicao(exame_id)
    if not laudo:
        raise HTTPException(404, "Laudo não encontrado")
    laudo_model.update(laudo["id"], {"texto": body.texto})
    return {"success": True}


@router.post("/{exame_id}/laudo/validar")
def validar_laudo(exame_id: str, user: dict = Depends(require_admin)):
    """Valida laudo (admin)."""
    db = get_db()
    laudo_model = Laudo(db.laudos)
    laudo = laudo_model.find_by_requisicao(exame_id)
    if not laudo:
        raise HTTPException(404, "Laudo não encontrado")
    laudo_model.validate(laudo["id"], user["id"])
    return {"success": True}


@router.post("/{exame_id}/laudo/regenerar")
def regenerar_laudo(exame_id: str, body: RegenerarLaudoRequest, user: dict = Depends(require_admin)):
    """Regenera laudo com correções para a IA (admin)."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)
    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    laudo = laudo_model.find_by_requisicao(exame_id)
    if not laudo:
        raise HTTPException(404, "Laudo não encontrado")
    if not body.correcoes or not body.correcoes.strip():
        raise HTTPException(400, "Descreva as correções para a IA")
    try:
        from ai.learning_system import LearningSystem
        ls = LearningSystem()
        imagens_usadas = laudo.get("imagens_usadas") or req.get("imagens") or []
        novo_texto, _ = ls.regenerate_with_corrections(
            laudo["id"], exame_id, body.correcoes.strip(), imagens_usadas
        )
        laudo_model.update(laudo["id"], {
            "texto": novo_texto,
            "regenerado_com_correcoes": True,
            "rating": 2,
        })
        return {"success": True, "texto": novo_texto}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/{exame_id}/laudo")
def cancelar_laudo(exame_id: str, user: dict = Depends(require_admin)):
    """Cancela/exclui o laudo para permitir nova geração (admin)."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)
    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    if not laudo_model.find_by_requisicao(exame_id):
        raise HTTPException(404, "Laudo não encontrado")
    laudo_model.delete_by_requisicao(exame_id)
    req_model.update_status(exame_id, "pendente")
    return {"success": True}


@router.post("/{exame_id}/laudo/liberar")
def liberar_laudo(exame_id: str, user: dict = Depends(require_admin)):
    """Libera laudo para o usuário (admin)."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)
    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    laudo = laudo_model.find_by_requisicao(exame_id)
    if not laudo:
        raise HTTPException(404, "Laudo não encontrado")
    laudo_model.release(laudo["id"])
    req_model.update_status(exame_id, "liberado")
    return {"success": True}


@router.get("/{exame_id}/pdf")
def baixar_pdf(exame_id: str, user: dict = Depends(get_current_user)):
    """Gera e retorna PDF do laudo (apenas se liberado)."""
    db = get_db()
    req_model = Requisicao(db.requisicoes)
    laudo_model = Laudo(db.laudos)
    clinica_model = Clinica(db.clinicas)
    veterinario_model = Veterinario(db.veterinarios)
    user_model = User(db.users)

    req = req_model.find_by_id(exame_id)
    if not req:
        raise HTTPException(404, "Exame não encontrado")
    if user["role"] != "admin" and req.get("user_id") != user["id"]:
        raise HTTPException(403, "Sem permissão")
    laudo = laudo_model.find_by_requisicao(exame_id)
    if not laudo or laudo.get("status") != "liberado":
        raise HTTPException(403, "Laudo ainda não liberado")

    try:
        from ai.analyzer import load_images_for_analysis
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos

        imagens_paths = req.get("imagens", [])
        images = load_images_for_analysis(imagens_paths) if imagens_paths else []
        _clinica_pdf = req.get("clinica") or ""
        if req.get("clinica_id"):
            c_obj = clinica_model.find_by_id(req["clinica_id"])
            if c_obj:
                _clinica_pdf = c_obj.get("nome", "") or _clinica_pdf
        if not (_clinica_pdf or "").strip() and req.get("user_id"):
            _user_req = user_model.find_by_id(req["user_id"])
            if _user_req and _user_req.get("clinica_id"):
                c_obj = clinica_model.find_by_id(_user_req["clinica_id"])
                _clinica_pdf = (c_obj or {}).get("nome", "") or _clinica_pdf
        _vet_pdf = req.get("medico_veterinario_solicitante") or ""
        if req.get("veterinario_id"):
            v_obj = veterinario_model.find_by_id(req["veterinario_id"])
            if v_obj:
                _vet_pdf = v_obj.get("nome", "") or _vet_pdf
        if not (_vet_pdf or "").strip() and req.get("user_id"):
            _user_req = user_model.find_by_id(req["user_id"])
            if _user_req and _user_req.get("clinica_id"):
                vets = veterinario_model.find_by_clinica(_user_req["clinica_id"], apenas_ativos=True)
                _vet_pdf = (vets[0].get("nome") if vets else None) or _vet_pdf

        def _clean(t):
            t = str(t) if t is not None else ""
            for a, b in [("'", "'"), ("'", "'"), (""", '"'), (""", '"'), ("—", "-"), ("–", "-"), ("…", "..."), ("°", " graus")]:
                t = t.replace(a, b)
            t = t.replace("**", "")
            try:
                t.encode("latin-1")
            except UnicodeEncodeError:
                import unicodedata
                t = unicodedata.normalize("NFKD", t).encode("latin-1", "ignore").decode("latin-1")
            return t

        pdf = FPDF("P", "mm", "A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Paciente: {_clean(req.get('paciente', 'N/A'))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Tutor: {_clean(req.get('tutor', 'N/A'))}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Clinica Solicitante: {_clean(_clinica_pdf or 'N/A')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Medico(a) Veterinario(a): {_clean(_vet_pdf or 'N/A')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Data: {now().strftime('%d/%m/%Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.ln(2)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 5, _clean(laudo.get("texto", "")))
        if images:
            pdf.add_page()
            for i, img in enumerate(images):
                w_px, h_px = img.size
                ar = h_px / w_px
                h_mm = 180 * ar
                if pdf.get_y() + h_mm > 267:
                    pdf.add_page()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                pdf.image(buf, w=180, h=h_mm)
                pdf.set_font("Arial", "I", 9)
                pdf.cell(0, 6, f"Imagem {i + 1}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
                pdf.ln(4)
        pdf.set_y(-35)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, "_" * 60, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "Dra. Lais Costa Muchiutti", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        pdf.ln(2)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 5, "Medica Veterinaria-CRMV SP32247", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        out = pdf.output(dest="S")
        pdf_bytes = bytes(out) if isinstance(out, bytearray) else out
        fn = f"laudo_{req.get('paciente', 'exame').replace(' ', '_')}.pdf"
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fn}"'})
    except Exception as e:
        raise HTTPException(500, f"Erro ao gerar PDF: {str(e)}")
