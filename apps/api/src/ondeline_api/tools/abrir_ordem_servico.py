"""Tool: abre OS, roteia tecnico por cidade/rua do cadastro SGP, notifica via WhatsApp.

O LLM NAO precisa (e nao deve) inventar endereco — a tool resolve a partir do
cliente vinculado a conversa, lendo o cadastro fresco no SGP. O parametro
`endereco` so deve ser passado quando o cliente *especificar* um endereco
diferente do cadastro (ex: 'a OS e pro outro imovel meu').
"""
from __future__ import annotations

from typing import Any

import structlog

from ondeline_api.adapters.genieacs.client import GenieAcsClient
from ondeline_api.adapters.sgp.base import EnderecoSgp
from ondeline_api.config import get_settings
from ondeline_api.db.crypto import decrypt_pii
from ondeline_api.domain.os_sequence import next_codigo
from ondeline_api.repositories.ordem_servico import OrdemServicoRepo
from ondeline_api.repositories.tecnico import TecnicoRepo
from ondeline_api.services.rede_service import RedeService, qualidade_sinal, snapshot_sinal
from ondeline_api.tools.context import ToolContext
from ondeline_api.tools.registry import tool

log = structlog.get_logger(__name__)

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "problema": {
            "type": "string",
            "description": "Descricao curta do problema reportado pelo cliente.",
        },
        "endereco": {
            "type": "string",
            "description": (
                "Opcional. Endereco completo (rua, numero, bairro, cidade). "
                "Omita para usar o endereco do cadastro do cliente — que e o "
                "default. So passe se o cliente especificar outro endereco."
            ),
        },
    },
    "required": ["problema"],
}


def _fmt_endereco(e: EnderecoSgp | dict[str, Any]) -> str:
    """Tolerante a dict (caso o cache devolva nao-tipado)."""
    if isinstance(e, dict):
        logradouro = e.get("logradouro", "") or ""
        numero = e.get("numero", "") or ""
        bairro = e.get("bairro", "") or ""
        cidade = e.get("cidade", "") or ""
        uf = e.get("uf", "") or ""
    else:
        logradouro = e.logradouro
        numero = e.numero
        bairro = e.bairro
        cidade = e.cidade
        uf = e.uf
    parts = [
        f"{logradouro}, {numero}".strip(", ") if logradouro else "",
        bairro,
        cidade + ("/" + uf if uf else ""),
    ]
    return " — ".join(p for p in parts if p)


def _endereco_attrs(e: EnderecoSgp | dict[str, Any] | None) -> tuple[str, str]:
    """Returns (logradouro, cidade) tolerando dict/EnderecoSgp/None."""
    if e is None:
        return "", ""
    if isinstance(e, dict):
        return (e.get("logradouro", "") or "", e.get("cidade", "") or "")
    return (e.logradouro or "", e.cidade or "")


def _split_endereco(endereco: str) -> tuple[str, str]:
    """Best-effort: extrai (rua, cidade) do texto livre."""
    parts = [p.strip() for p in (endereco or "").replace("—", ",").split(",") if p.strip()]
    rua = parts[0] if parts else ""
    cidade = parts[-2] if len(parts) >= 2 else (parts[-1] if parts else "")
    return rua, cidade


async def _resolve_endereco_do_cadastro(ctx: ToolContext) -> tuple[str, str, str]:
    """Returns (endereco_str, rua, cidade) lendo o SGP via cache.

    Fallback para Cliente.cidade do DB quando SGP indisponivel.
    """
    if ctx.cliente is None:
        return "", "", ""
    cidade_db = ctx.cliente.cidade or ""
    if ctx.sgp_cache is None:
        return cidade_db, "", cidade_db
    try:
        cpf = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
        cli_sgp = await ctx.sgp_cache.get_cliente(cpf)
    except Exception:
        return cidade_db, "", cidade_db
    if cli_sgp is None:
        return cidade_db, "", cidade_db
    end = (
        (cli_sgp.contratos[0].endereco if cli_sgp.contratos else None)
        or cli_sgp.endereco
    )
    endereco_str = _fmt_endereco(end) if end else cidade_db
    rua, cidade = _endereco_attrs(end)
    if not cidade:
        cidade = cidade_db
    return endereco_str, rua, cidade


async def _capturar_sinal(ctx: ToolContext) -> dict[str, Any] | None:
    """Snapshot best-effort do sinal pra gravar na OS. Nunca propaga erro."""
    if ctx.cliente is None:
        return None
    try:
        cpf_cli = decrypt_pii(ctx.cliente.cpf_cnpj_encrypted)
        genie = GenieAcsClient(base_url=get_settings().genieacs_url)
        try:
            rede = RedeService(session=ctx.session, genieacs=genie, sgp_cache=ctx.sgp_cache)
            return await snapshot_sinal(rede, cpf_cli)
        finally:
            await genie.aclose()
    except Exception as e:  # nunca bloqueia a criacao da OS
        log.warning("abrir_os.sinal_snapshot_falhou", error=str(e))
        return None


@tool(
    name="abrir_ordem_servico",
    description=(
        "Cria uma Ordem de Servico (OS) tecnica para o cliente vinculado a esta conversa. "
        "Por padrao usa o endereco do cadastro do cliente para rotear o tecnico mais "
        "adequado por cidade/rua. Use quando o problema tecnico nao puder ser resolvido "
        "por orientacao."
    ),
    parameters=SCHEMA,
)
async def abrir_ordem_servico(
    ctx: ToolContext, *, problema: str, endereco: str | None = None
) -> dict[str, Any]:
    if ctx.cliente is None:
        return {"ok": False, "motivo": "cliente nao vinculado"}

    # Cooldown 12h: evita abrir OS duplicada quando bot oscila / cliente insiste.
    # Se ja existe OS aberta ou criada nas ultimas 12h pra esse cliente,
    # devolve a existente em vez de criar nova. Tecnico ja vai resolver tudo
    # na mesma visita; multiplas OS confundem o roteiro.
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from ondeline_api.db.models.business import OrdemServico, OsStatus

    cutoff = datetime.now(tz=UTC) - timedelta(hours=12)
    stmt = (
        select(OrdemServico)
        .where(
            OrdemServico.cliente_id == ctx.cliente.id,
            OrdemServico.criada_em >= cutoff,
            OrdemServico.status.in_(
                [OsStatus.PENDENTE, OsStatus.EM_ANDAMENTO]
            ),
        )
        .order_by(OrdemServico.criada_em.desc())
        .limit(1)
    )
    os_recente = (await ctx.session.execute(stmt)).scalar_one_or_none()
    if os_recente is not None:
        log.info(
            "abrir_os.cooldown_hit",
            cliente_id=str(ctx.cliente.id),
            os_existente=os_recente.codigo,
        )
        return {
            "ok": True,
            "ja_existe": True,
            "codigo": os_recente.codigo,
            "problema_anterior": os_recente.problema,
            "motivo": (
                f"Ja existe OS aberta nas ultimas 12h ({os_recente.codigo}). "
                "O tecnico vai resolver tudo na mesma visita. "
                "Avise o cliente e atualize o problema se necessario."
            ),
        }

    if endereco:
        endereco_final = endereco
        rua, cidade = _split_endereco(endereco)
    else:
        endereco_final, rua, cidade = await _resolve_endereco_do_cadastro(ctx)
        if not endereco_final:
            return {
                "ok": False,
                "motivo": "endereco do cliente nao localizado no cadastro",
            }

    codigo = await next_codigo(ctx.session)
    tecnico = await TecnicoRepo(ctx.session).find_by_area(cidade=cidade, rua=rua)
    sinal_snap = await _capturar_sinal(ctx)
    os_ = await OrdemServicoRepo(ctx.session).create(
        codigo=codigo,
        cliente_id=ctx.cliente.id,
        tecnico_id=tecnico.id if tecnico else None,
        problema=problema,
        endereco=endereco_final,
        sinal=sinal_snap,
    )

    tecnico_notificado = False
    if tecnico is not None and tecnico.whatsapp:
        nome_cliente = (
            decrypt_pii(ctx.cliente.nome_encrypted)
            if ctx.cliente.nome_encrypted
            else "Cliente"
        )
        # Mensagem rica pro tecnico — com emoji + bold WhatsApp + lembrete do
        # comando CONCLUIR. Ajuda o tecnico a localizar/identificar a OS no
        # campo e saber como fechar quando terminar.
        wpp_cliente = ctx.conversa.whatsapp.split("@")[0] if ctx.conversa.whatsapp else ""
        # Formata em '(DD) X XXXX-XXXX' se conseguir.
        only_d = "".join(c for c in wpp_cliente if c.isdigit())
        if only_d.startswith("55") and len(only_d) >= 12:
            only_d = only_d[2:]
        if len(only_d) == 11:
            wpp_fmt = f"({only_d[:2]}) {only_d[2:3]} {only_d[3:7]}-{only_d[7:]}"
        elif len(only_d) == 10:
            wpp_fmt = f"({only_d[:2]}) {only_d[2:6]}-{only_d[6:]}"
        else:
            wpp_fmt = ctx.conversa.whatsapp or ""

        linha_sinal = ""
        if sinal_snap and sinal_snap.get("rx_power") is not None:
            _, emoji = qualidade_sinal(sinal_snap["rx_power"])
            linha_sinal = f"*Sinal:* {emoji} {sinal_snap['rx_power']} dBm\n"
        msg = (
            f"🔧 *Nova OS atribuída a você*\n\n"
            f"*Código:* {codigo}\n"
            f"*Cliente:* {nome_cliente}\n"
            f"*WhatsApp:* {wpp_fmt}\n"
            f"*Endereço:* {endereco_final}\n"
            f"*Problema:* {problema}\n"
            f"{linha_sinal}\n"
            f"Quando concluir, mande no chat:\n"
            f"_CONCLUIR {codigo}_"
        )
        # Notificacao do tecnico e best-effort: a OS ja esta persistida.
        # Se o numero nao existe no WhatsApp / Evolution falha, nao quebrar a tool.
        try:
            await ctx.evolution.send_text(tecnico.whatsapp, msg)
            tecnico_notificado = True
        except Exception as e:
            log.warning(
                "abrir_os.tecnico_send_failed",
                tecnico_id=str(tecnico.id),
                error=str(e),
                exc_info=True,
            )

    return {
        "ok": True,
        "codigo": codigo,
        "tecnico_nome": tecnico.nome if tecnico else None,
        "tecnico_atribuido": tecnico is not None,
        "tecnico_notificado": tecnico_notificado,
        "endereco_usado": endereco_final,
        "os_id": str(os_.id),
    }
