/**
 * Utilitários de data para o sistema PAICS
 * Configurado para GMT-3 (Horário de Brasília)
 */

const TZ_BRASILIA = "America/Sao_Paulo";

/**
 * Retorna a data de hoje no formato YYYY-MM-DD no horário de Brasília (GMT-3).
 * Evita o problema de toISOString() que usa UTC e adianta o dia após 21h no Brasil.
 */
export function hojeISO(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: TZ_BRASILIA });
}

/**
 * Retorna a data de N dias atrás no formato YYYY-MM-DD no horário de Brasília.
 */
export function diasAtrasISO(dias: number): string {
  const d = new Date();
  d.setDate(d.getDate() - dias);
  return d.toLocaleDateString("en-CA", { timeZone: TZ_BRASILIA });
}

/**
 * Converte um Date ou string ISO para YYYY-MM-DD no horário de Brasília.
 * Útil ao exibir datas vindas da API (que podem estar em UTC).
 */
export function dateToISOLocal(dt: Date | string): string {
  const d = typeof dt === "string" ? new Date(dt) : dt;
  return d.toLocaleDateString("en-CA", { timeZone: TZ_BRASILIA });
}
