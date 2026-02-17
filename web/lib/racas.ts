/**
 * Lista de raças caninas e felinas comuns no Brasil para autocomplete.
 * Ordenada alfabeticamente para filtro por prefixo.
 */
export const RACAS_CANINAS = [
  "Afegan Hound",
  "Airedale Terrier",
  "Akita",
  "American Pit Bull Terrier",
  "Basset Hound",
  "Beagle",
  "Bernese Mountain Dog",
  "Bichon Frisé",
  "Border Collie",
  "Boxer",
  "Buldogue Francês",
  "Buldogue Inglês",
  "Bull Terrier",
  "Cane Corso",
  "Chihuahua",
  "Chow Chow",
  "Cocker Spaniel",
  "Dachshund",
  "Doberman",
  "Dogue Alemão",
  "Golden Retriever",
  "Husky Siberiano",
  "Jack Russell Terrier",
  "Labrador Retriever",
  "Lhasa Apso",
  "Maltês",
  "Mastiff",
  "Pastor Alemão",
  "Pastor Belga",
  "Pastor Australiano",
  "Pinscher",
  "Pit Bull",
  "Pointer",
  "Poodle",
  "Pug",
  "Rottweiler",
  "São Bernardo",
  "Shar-Pei",
  "Shih Tzu",
  "Spitz Alemão",
  "SRD",
  "Staffordshire Terrier",
  "Vira-lata",
  "Weimaraner",
  "Yorkshire Terrier",
];

export const RACAS_FELINAS = [
  "Abissínio",
  "Angorá Turco",
  "Bengal",
  "Birmanês",
  "Bombaim",
  "Britânico de Pelo Curto",
  "Burmês",
  "Chartreux",
  "Devon Rex",
  "Exótico de Pelo Curto",
  "Himalaio",
  "Maine Coon",
  "Manx",
  "Norueguês da Floresta",
  "Oriental",
  "Persa",
  "Ragdoll",
  "Russian Blue",
  "Scottish Fold",
  "Siamês",
  "Sphynx",
  "SRD",
  "Vira-lata",
];

/** Todas as raças (caninas + felinas) ordenadas alfabeticamente */
export const TODAS_RACAS = [...RACAS_CANINAS, ...RACAS_FELINAS].sort((a, b) =>
  a.localeCompare(b, "pt-BR")
);

/**
 * Filtra raças que começam com o texto digitado (case insensitive).
 */
export function filtrarRacas(entrada: string, especie?: string): string[] {
  const q = entrada.trim().toLowerCase();
  if (!q) return [];

  const lista =
    especie === "Canino"
      ? RACAS_CANINAS
      : especie === "Felino"
        ? RACAS_FELINAS
        : TODAS_RACAS;

  return lista.filter((r) => r.toLowerCase().startsWith(q));
}
