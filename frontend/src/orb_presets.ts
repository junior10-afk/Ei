export interface ThemePalette {
  idle: number;
  listening: number;
  thinking: number;
  speaking: number;
  core: number;
  line: number;
  electron: number;
}

export type OrbCategory =
  | 'Classique'
  | 'Sci-Fi & IA'
  | 'Cosmique & Espace'
  | 'Énergie & Éléments'
  | 'Cyber & Géométrie';

export type OrbAnimationStyle =
  | 'plasma'
  | 'vortex'
  | 'quantum'
  | 'equalizer'
  | 'rings'
  | 'helix'
  | 'tesseract'
  | 'tesla'
  | 'crystal'
  | 'cascade';

export type VertexColorMode =
  | 'gradient'
  | 'accretion'
  | 'eye'
  | 'reactor'
  | 'matrix'
  | 'tesla'
  | 'saturn'
  | 'solar'
  | 'helix'
  | 'tesseract'
  | 'synthwave'
  | 'pulsar'
  | 'aurora'
  | 'crystal';

export interface OrbPreset {
  id: string;
  name: string;
  category: OrbCategory;
  icon: string;
  description: string;
  palette: ThemePalette;
  animation: OrbAnimationStyle;
  colorMode: VertexColorMode;
  hasLines: boolean;
  lineOpacity?: number;
  glowColor: string;
  particleSize?: number;
  coreSize?: number;
  speedMultiplier?: number;
}

export const ORB_PRESETS: Record<string, OrbPreset> = {
  // ── 1. CLASSIQUES ──────────────────────────────────────────────────────────
  cyber_blue: {
    id: 'cyber_blue',
    name: 'Cyan Cyber',
    category: 'Classique',
    icon: '🔷',
    description: "L'orbe holographique original d'EI avec réseau synaptique.",
    palette: {
      idle: 0x00d9ff,
      listening: 0x2979ff,
      thinking: 0xb300ff,
      speaking: 0x00ffff,
      core: 0x80f7ff,
      line: 0x00b0ff,
      electron: 0xffffff
    },
    animation: 'plasma',
    colorMode: 'gradient',
    hasLines: true,
    lineOpacity: 0.25,
    glowColor: 'rgba(0, 217, 255, 0.35)',
    particleSize: 0.95
  },
  iron_man: {
    id: 'iron_man',
    name: 'Mark VII (Stark)',
    category: 'Classique',
    icon: '🔴',
    description: "Nuance or et carmin inspirée de l'armure de Tony Stark.",
    palette: {
      idle: 0xffa000,
      listening: 0xff3d00,
      thinking: 0xff0055,
      speaking: 0xffd700,
      core: 0xffe082,
      line: 0xff5500,
      electron: 0xffffff
    },
    animation: 'plasma',
    colorMode: 'solar',
    hasLines: true,
    lineOpacity: 0.25,
    glowColor: 'rgba(255, 160, 0, 0.4)',
    particleSize: 1.0
  },

  // ── 2. SCI-FI & INTELLIGENCES ARTIFICIELLES ─────────────────────────────────
  arc_reactor: {
    id: 'arc_reactor',
    name: 'Arc Reactor MK-85',
    category: 'Sci-Fi & IA',
    icon: '⚡',
    description: "Cœur de réacteur Stark, anneaux concentriques à 10 bobines et plasma cyan-or.",
    palette: {
      idle: 0x00f0ff,
      listening: 0x0088ff,
      thinking: 0xffd700,
      speaking: 0xffffff,
      core: 0xffffff,
      line: 0x00e5ff,
      electron: 0xfff0b0
    },
    animation: 'quantum',
    colorMode: 'reactor',
    hasLines: true,
    lineOpacity: 0.35,
    glowColor: 'rgba(0, 240, 255, 0.45)',
    particleSize: 1.05,
    speedMultiplier: 1.25
  },
  hal_9000: {
    id: 'hal_9000',
    name: 'HAL-9000 Sovereign',
    category: 'Sci-Fi & IA',
    icon: '👁️',
    description: "L'œil optique rouge incandescent et implacable de 2001, l'Odyssée de l'espace.",
    palette: {
      idle: 0xd50000,
      listening: 0xff1744,
      thinking: 0xff5252,
      speaking: 0xff8a80,
      core: 0xffffff,
      line: 0xb71c1c,
      electron: 0xff1744
    },
    animation: 'quantum',
    colorMode: 'eye',
    hasLines: false,
    glowColor: 'rgba(255, 23, 68, 0.55)',
    particleSize: 1.0,
    speedMultiplier: 0.9
  },
  cortana: {
    id: 'cortana',
    name: 'Cortana Hologram',
    category: 'Sci-Fi & IA',
    icon: '💜',
    description: 'Avatar holographique IA de Halo, résonance lilas, magenta et cyan céleste.',
    palette: {
      idle: 0xb388ff,
      listening: 0x7c4dff,
      thinking: 0x00e5ff,
      speaking: 0xe040fb,
      core: 0xff80ab,
      line: 0x651fff,
      electron: 0xffffff
    },
    animation: 'plasma',
    colorMode: 'gradient',
    hasLines: true,
    lineOpacity: 0.22,
    glowColor: 'rgba(224, 64, 251, 0.4)',
    particleSize: 0.85
  },
  aperture: {
    id: 'aperture',
    name: 'Aperture Optical Core',
    category: 'Sci-Fi & IA',
    icon: '🔬',
    description: "Noyau optique d'Aperture Science, ambre chaud et arcs bleus de portail.",
    palette: {
      idle: 0xffab00,
      listening: 0xff6d00,
      thinking: 0x00b0ff,
      speaking: 0xffd54f,
      core: 0xffffff,
      line: 0x0091ea,
      electron: 0xffffff
    },
    animation: 'equalizer',
    colorMode: 'gradient',
    hasLines: true,
    lineOpacity: 0.2,
    glowColor: 'rgba(255, 171, 0, 0.4)',
    particleSize: 0.9
  },
  tachikoma: {
    id: 'tachikoma',
    name: 'Tachikoma Cyber-Net',
    category: 'Sci-Fi & IA',
    icon: '🕸️',
    description: 'Réseau de données tactique Ghost in the Shell, vert émeraude et sarcelle.',
    palette: {
      idle: 0x00e676,
      listening: 0x00b0ff,
      thinking: 0x1de9b6,
      speaking: 0x76ff03,
      core: 0xb9f6ca,
      line: 0x00b4d8,
      electron: 0xffffff
    },
    animation: 'equalizer',
    colorMode: 'gradient',
    hasLines: true,
    lineOpacity: 0.3,
    glowColor: 'rgba(0, 230, 118, 0.4)',
    particleSize: 0.9
  },

  // ── 3. COSMIQUE & ASTROPHYSIQUE ─────────────────────────────────────────────
  gargantua: {
    id: 'gargantua',
    name: 'Gargantua (Singularité)',
    category: 'Cosmique & Espace',
    icon: '🕳️',
    description: 'Disque d’accrétion relativiste ultra-lumineux autour d’un trou noir absolu.',
    palette: {
      idle: 0xff6d00,
      listening: 0xff9100,
      thinking: 0xdd2c00,
      speaking: 0xffd180,
      core: 0xffffff,
      line: 0xff3d00,
      electron: 0xffffff
    },
    animation: 'vortex',
    colorMode: 'accretion',
    hasLines: false,
    glowColor: 'rgba(255, 109, 0, 0.55)',
    particleSize: 1.15,
    speedMultiplier: 1.6
  },
  pulsar: {
    id: 'pulsar',
    name: 'Neutron Pulsar',
    category: 'Cosmique & Espace',
    icon: '✨',
    description: 'Étoile à neutrons à rotation relativiste projetant deux faisceaux polaires intenses.',
    palette: {
      idle: 0x80d8ff,
      listening: 0x00b0ff,
      thinking: 0x7c4dff,
      speaking: 0xffffff,
      core: 0xffffff,
      line: 0x40c4ff,
      electron: 0x00e5ff
    },
    animation: 'quantum',
    colorMode: 'pulsar',
    hasLines: false,
    glowColor: 'rgba(128, 216, 255, 0.5)',
    particleSize: 0.95,
    speedMultiplier: 1.7
  },
  saturn_rings: {
    id: 'saturn_rings',
    name: 'Saturn Rings',
    category: 'Cosmique & Espace',
    icon: '🪐',
    description: 'Globe planétaire ocre ceinturé d’anneaux de poussière dorée avec division de Cassini.',
    palette: {
      idle: 0xffe082,
      listening: 0xffd54f,
      thinking: 0x80cbc4,
      speaking: 0xfff9c4,
      core: 0xfff8e1,
      line: 0xffca28,
      electron: 0xffffff
    },
    animation: 'rings',
    colorMode: 'saturn',
    hasLines: false,
    glowColor: 'rgba(255, 224, 130, 0.4)',
    particleSize: 1.0,
    speedMultiplier: 1.1
  },
  aurora: {
    id: 'aurora',
    name: 'Aurora Borealis',
    category: 'Cosmique & Espace',
    icon: '🌌',
    description: 'Voiles de plasma géomagnétique émeraude et turquoise ondulant dans la nuit polaire.',
    palette: {
      idle: 0x69f0ae,
      listening: 0x00e5ff,
      thinking: 0xe040fb,
      speaking: 0xb9f6ca,
      core: 0x84ffff,
      line: 0x00e676,
      electron: 0xffffff
    },
    animation: 'plasma',
    colorMode: 'aurora',
    hasLines: false,
    glowColor: 'rgba(105, 240, 174, 0.45)',
    particleSize: 1.05,
    speedMultiplier: 1.15
  },
  dark_matter: {
    id: 'dark_matter',
    name: 'Dark Matter',
    category: 'Cosmique & Espace',
    icon: '🌑',
    description: 'Énergie du vide quantique, violet abyssal et flashs d’arcs krypton.',
    palette: {
      idle: 0x4a148c,
      listening: 0x7b1fa2,
      thinking: 0x00e5ff,
      speaking: 0xaa00ff,
      core: 0xba68c8,
      line: 0x311b92,
      electron: 0x00e5ff
    },
    animation: 'quantum',
    colorMode: 'gradient',
    hasLines: true,
    lineOpacity: 0.18,
    glowColor: 'rgba(123, 31, 162, 0.45)',
    particleSize: 0.9
  },

  // ── 4. ÉNERGIE, HAUTE TENSION & ÉLÉMENTS ────────────────────────────────────
  solar_flare: {
    id: 'solar_flare',
    name: 'Solar Flare',
    category: 'Énergie & Éléments',
    icon: '☀️',
    description: 'Ébullition de plasma stellaire à 6000K avec boucles coronales magnétiques en fusion.',
    palette: {
      idle: 0xffd600,
      listening: 0xff6d00,
      thinking: 0xff3d00,
      speaking: 0xffeb3b,
      core: 0xffffff,
      line: 0xffab00,
      electron: 0xffffff
    },
    animation: 'plasma',
    colorMode: 'solar',
    hasLines: false,
    glowColor: 'rgba(255, 214, 0, 0.55)',
    particleSize: 1.25,
    speedMultiplier: 1.3
  },
  tesla_coil: {
    id: 'tesla_coil',
    name: 'Tesla 100kV',
    category: 'Énergie & Éléments',
    icon: '⚡',
    description: 'Arcs électriques haute tension et éclairs fractals saccadés bleu néon et violet.',
    palette: {
      idle: 0x651fff,
      listening: 0x2979ff,
      thinking: 0x00e5ff,
      speaking: 0xffffff,
      core: 0xffffff,
      line: 0x3d5afe,
      electron: 0x80d8ff
    },
    animation: 'tesla',
    colorMode: 'tesla',
    hasLines: true,
    lineOpacity: 0.45,
    glowColor: 'rgba(101, 31, 255, 0.55)',
    particleSize: 0.9,
    speedMultiplier: 1.4
  },
  abyssal: {
    id: 'abyssal',
    name: 'Abyssal Biolum',
    category: 'Énergie & Éléments',
    icon: '🌊',
    description: 'Pulsation biomimétique fluide des abysses océaniques en turquoise et cyan lagon.',
    palette: {
      idle: 0x1de9b6,
      listening: 0x00b4d8,
      thinking: 0x0077b6,
      speaking: 0x64ffda,
      core: 0xa7ffeb,
      line: 0x0096c7,
      electron: 0xffffff
    },
    animation: 'plasma',
    colorMode: 'gradient',
    hasLines: false,
    glowColor: 'rgba(29, 233, 182, 0.45)',
    particleSize: 0.95,
    speedMultiplier: 0.8
  },
  crystal: {
    id: 'crystal',
    name: 'Crystal Chronos',
    category: 'Énergie & Éléments',
    icon: '💎',
    description: 'Prisme géométrique cristallin réfractant cyan quartz, améthyste et lumière pure.',
    palette: {
      idle: 0x84ffff,
      listening: 0xb388ff,
      thinking: 0xf48fb1,
      speaking: 0xffffff,
      core: 0xe1bee7,
      line: 0x80deea,
      electron: 0xffffff
    },
    animation: 'crystal',
    colorMode: 'crystal',
    hasLines: true,
    lineOpacity: 0.28,
    glowColor: 'rgba(132, 255, 255, 0.45)',
    particleSize: 1.05
  },
  radioactive: {
    id: 'radioactive',
    name: 'Rad-226 Isotope',
    category: 'Énergie & Éléments',
    icon: '☢️',
    description: 'Lueur Tcherenkov intense et nuage d’isotopes verts instables sous radiation gamma.',
    palette: {
      idle: 0x76ff03,
      listening: 0x00e676,
      thinking: 0xffea00,
      speaking: 0xccff90,
      core: 0xf4ff81,
      line: 0x64dd17,
      electron: 0xffffff
    },
    animation: 'quantum',
    colorMode: 'gradient',
    hasLines: false,
    glowColor: 'rgba(118, 255, 3, 0.55)',
    particleSize: 1.0,
    speedMultiplier: 1.3
  },

  // ── 5. CYBER, GÉOMÉTRIE & EXPÉRIMENTAL ──────────────────────────────────────
  tesseract: {
    id: 'tesseract',
    name: 'Tesseract 4D',
    category: 'Cyber & Géométrie',
    icon: '🧊',
    description: 'Véritable hypercube 4D en rotation géométrique quadridimensionnelle avec arêtes néon.',
    palette: {
      idle: 0x00e5ff,
      listening: 0x3d5afe,
      thinking: 0xd500f9,
      speaking: 0xffffff,
      core: 0x80d8ff,
      line: 0x00b0ff,
      electron: 0xffffff
    },
    animation: 'tesseract',
    colorMode: 'tesseract',
    hasLines: true,
    lineOpacity: 0.35,
    glowColor: 'rgba(0, 229, 255, 0.5)',
    particleSize: 1.15,
    speedMultiplier: 1.2
  },
  dna_helix: {
    id: 'dna_helix',
    name: 'Double Helix DNA',
    category: 'Cyber & Géométrie',
    icon: '🧬',
    description: 'Double hélice moléculaire en rotation continue avec barreaux de liaisons hydrogène.',
    palette: {
      idle: 0x00c853,
      listening: 0x00b0ff,
      thinking: 0xaa00ff,
      speaking: 0x69f0ae,
      core: 0xb9f6ca,
      line: 0x00e676,
      electron: 0xffffff
    },
    animation: 'helix',
    colorMode: 'helix',
    hasLines: false,
    glowColor: 'rgba(0, 200, 83, 0.45)',
    particleSize: 1.05,
    speedMultiplier: 1.25
  },
  neural_synapse: {
    id: 'neural_synapse',
    name: 'Neural Synapse',
    category: 'Cyber & Géométrie',
    icon: '🧠',
    description: 'Réseau synaptique ultra-dense où circulent des influx lumineux à chaque calcul IA.',
    palette: {
      idle: 0xff4081,
      listening: 0xffab40,
      thinking: 0x7c4dff,
      speaking: 0xff80ab,
      core: 0xffd180,
      line: 0xf50057,
      electron: 0xffffff
    },
    animation: 'quantum',
    colorMode: 'gradient',
    hasLines: true,
    lineOpacity: 0.38,
    glowColor: 'rgba(255, 64, 129, 0.5)',
    particleSize: 0.95
  },
  synthwave: {
    id: 'synthwave',
    name: 'Synthwave 84',
    category: 'Cyber & Géométrie',
    icon: '🕶️',
    description: 'Coucher de soleil Outrun rétro-futuriste, néon fuchsia, ambre crépusculaire et grille laser.',
    palette: {
      idle: 0xff007f,
      listening: 0xff7700,
      thinking: 0x7928ca,
      speaking: 0xffbe0b,
      core: 0xffa07a,
      line: 0xff0055,
      electron: 0x00f0ff
    },
    animation: 'equalizer',
    colorMode: 'synthwave',
    hasLines: true,
    lineOpacity: 0.25,
    glowColor: 'rgba(255, 0, 127, 0.5)',
    particleSize: 1.05
  },
  matrix_code: {
    id: 'matrix_code',
    name: 'Matrix Code Cascade',
    category: 'Cyber & Géométrie',
    icon: '💾',
    description: 'Pluie de code numérique en colonnes verticales descendantes avec têtes blanches et traînées vertes.',
    palette: {
      idle: 0x00e676,
      listening: 0x76ff03,
      thinking: 0x00b0ff,
      speaking: 0xb9f6ca,
      core: 0xe8f5e9,
      line: 0x00c853,
      electron: 0xffffff
    },
    animation: 'cascade',
    colorMode: 'matrix',
    hasLines: false,
    glowColor: 'rgba(0, 230, 118, 0.55)',
    particleSize: 1.0,
    speedMultiplier: 1.35
  }
};

export function getOrbPreset(id: string): OrbPreset {
  return ORB_PRESETS[id] || ORB_PRESETS.cyber_blue;
}

export function getAllOrbPresets(): OrbPreset[] {
  return Object.values(ORB_PRESETS);
}

export function getPresetsByCategory(): Record<OrbCategory, OrbPreset[]> {
  const grouped: Record<OrbCategory, OrbPreset[]> = {
    'Classique': [],
    'Sci-Fi & IA': [],
    'Cosmique & Espace': [],
    'Énergie & Éléments': [],
    'Cyber & Géométrie': []
  };

  for (const preset of Object.values(ORB_PRESETS)) {
    if (grouped[preset.category]) {
      grouped[preset.category].push(preset);
    }
  }

  return grouped;
}
