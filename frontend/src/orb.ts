import * as THREE from 'three';
import { AssistantStateType } from './protocol';
import {
  ORB_PRESETS,
  OrbPreset,
  OrbAnimationStyle,
  ThemePalette,
  getOrbPreset
} from './orb_presets';

export type OrbTheme = string;
export type { OrbAnimationStyle, OrbPreset };

export interface OrbOptions {
  container: HTMLElement;
  particleCount?: number;
  initialStyle?: OrbAnimationStyle;
}

const THEMES: Record<string, ThemePalette> = {};
for (const [key, preset] of Object.entries(ORB_PRESETS)) {
  THEMES[key] = preset.palette;
}

interface Electron {
  sx: number; sy: number; sz: number;
  ex: number; ey: number; ez: number;
  t: number;
  speed: number;
}

export class JarvisOrb {
  private container: HTMLElement;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;

  // 1. Nuage de particules principal (Volumétrique + Couleurs par vertex)
  private N: number;
  private particleGeo: THREE.BufferGeometry;
  private particleMat: THREE.PointsMaterial;
  private particles: THREE.Points;
  private pos: Float32Array;
  private vel: Float32Array;
  private phase: Float32Array;
  private colors: Float32Array;
  private targetColors: Float32Array;

  // 2. Cœur d'énergie (Nucleus / Photon Ring / Eye Core)
  private coreN: number = 420;
  private coreGeo: THREE.BufferGeometry;
  private coreMat: THREE.PointsMaterial;
  private coreParticles: THREE.Points;
  private corePos: Float32Array;

  // 3. Réseau Synaptique (Lignes Plexus)
  private MAX_LINES: number = 4000;
  private lineGeo: THREE.BufferGeometry;
  private lineMat: THREE.LineBasicMaterial;
  private lineSegments: THREE.LineSegments;
  private linePos: Float32Array;
  private activeConnections: { x1: number; y1: number; z1: number; x2: number; y2: number; z2: number }[] = [];

  // 4. Électrons circulants
  private MAX_ELECTRONS: number = 100;
  private electronGeo: THREE.BufferGeometry;
  private electronMat: THREE.PointsMaterial;
  private electronPoints: THREE.Points;
  private electronPos: Float32Array;
  private activeElectrons: Electron[] = [];
  private lastElectronSpawn: number = 0;

  // Configuration active
  private currentPreset: OrbPreset;
  private animationStyle: OrbAnimationStyle = 'plasma';
  private state: AssistantStateType = 'idle';
  private quality: 'low' | 'medium' | 'high' = 'high';

  // Paramètres physiques
  private targetRadius: number = 15;
  private currentRadius: number = 15;
  private targetSpeed: number = 0.25;
  private currentSpeed: number = 0.25;
  private targetLineAmount: number = 0.25;
  private lineAmount: number = 0.25;
  private targetElectronRate: number = 0.01;
  private electronRate: number = 0.01;
  private vortexStrength: number = 0.0;
  private breathAmp: number = 0.0;
  private shockwave: number = 0.0;

  // Couleurs globales
  private currentColor: THREE.Color = new THREE.Color(0x00d9ff);
  private targetColor: THREE.Color = new THREE.Color(0x00d9ff);
  private coreColor: THREE.Color = new THREE.Color(0x80f7ff);
  private targetCoreColor: THREE.Color = new THREE.Color(0x80f7ff);
  private lineColor: THREE.Color = new THREE.Color(0x00b0ff);
  private electronColor: THREE.Color = new THREE.Color(0xffffff);

  // Audio réactif
  private volume: number = 0.0;
  private targetVolume: number = 0.0;
  private prevBass: number = 0.0;

  // Rotation & boucle
  private spinX: number = 0;
  private spinY: number = 0;
  private clock: THREE.Clock = new THREE.Clock();
  private animFrameId: number | null = null;
  private isDestroyed: boolean = false;

  constructor(options: OrbOptions) {
    this.container = options.container;
    this.currentPreset = ORB_PRESETS.cyber_blue;
    this.animationStyle = this.currentPreset.animation;
    this.N = options.particleCount || 2200;

    // 1. Initialisation Three.js
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      1,
      1000
    );
    this.camera.position.z = 105;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setClearColor(0x000000, 0);
    this.container.appendChild(this.renderer.domElement);

    // 2. Texture de particule optique haute définition
    const particleTexture = this.createParticleGlowTexture();

    // 3. Nuage de particules principal avec Vertex Colors
    this.particleGeo = new THREE.BufferGeometry();
    this.pos = new Float32Array(this.N * 3);
    this.vel = new Float32Array(this.N * 3);
    this.phase = new Float32Array(this.N);
    this.colors = new Float32Array(this.N * 3);
    this.targetColors = new Float32Array(this.N * 3);

    this.initDefaultSpherePositions();

    this.particleGeo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    this.particleGeo.setAttribute('color', new THREE.BufferAttribute(this.colors, 3));

    this.particleMat = new THREE.PointsMaterial({
      size: 0.95,
      map: particleTexture,
      transparent: true,
      opacity: 0.92,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexColors: true
    });
    this.particles = new THREE.Points(this.particleGeo, this.particleMat);
    this.scene.add(this.particles);

    // 4. Cœur d'énergie dense (Nucleus)
    this.coreGeo = new THREE.BufferGeometry();
    this.corePos = new Float32Array(this.coreN * 3);
    this.initDefaultCorePositions();

    this.coreGeo.setAttribute('position', new THREE.BufferAttribute(this.corePos, 3));
    this.coreMat = new THREE.PointsMaterial({
      color: this.coreColor,
      size: 1.25,
      map: particleTexture,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    this.coreParticles = new THREE.Points(this.coreGeo, this.coreMat);
    this.scene.add(this.coreParticles);

    // 5. Réseau Synaptique (Lignes Plexus)
    this.lineGeo = new THREE.BufferGeometry();
    this.linePos = new Float32Array(this.MAX_LINES * 6);
    this.lineGeo.setAttribute('position', new THREE.BufferAttribute(this.linePos, 3));
    this.lineGeo.setDrawRange(0, 0);

    this.lineMat = new THREE.LineBasicMaterial({
      color: this.lineColor,
      transparent: true,
      opacity: 0.25,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    this.lineSegments = new THREE.LineSegments(this.lineGeo, this.lineMat);
    this.scene.add(this.lineSegments);

    // 6. Électrons circulants
    this.electronGeo = new THREE.BufferGeometry();
    this.electronPos = new Float32Array(this.MAX_ELECTRONS * 3);
    this.electronGeo.setAttribute('position', new THREE.BufferAttribute(this.electronPos, 3));
    this.electronGeo.setDrawRange(0, 0);

    this.electronMat = new THREE.PointsMaterial({
      color: this.electronColor,
      size: 1.5,
      map: particleTexture,
      transparent: true,
      opacity: 1.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    this.electronPoints = new THREE.Points(this.electronGeo, this.electronMat);
    this.scene.add(this.electronPoints);

    // Initialiser le preset par défaut
    this.setPreset('cyber_blue');

    // Redimensionnement
    window.addEventListener('resize', this.onResize.bind(this));

    // Démarrer la boucle de rendu
    this.animate();
  }

  /**
   * Crée une texture circulaire de lueur avec halo doux et cœur haute énergie
   */
  private createParticleGlowTexture(): THREE.Texture {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext('2d')!;

    const grad = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.18, 'rgba(255, 255, 255, 0.95)');
    grad.addColorStop(0.42, 'rgba(255, 255, 255, 0.55)');
    grad.addColorStop(0.72, 'rgba(255, 255, 255, 0.18)');
    grad.addColorStop(1, 'rgba(255, 255, 255, 0)');

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 128, 128);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
  }

  private initDefaultSpherePositions() {
    for (let i = 0; i < this.N; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = Math.pow(Math.random(), 0.65) * this.currentRadius;

      this.pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      this.pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      this.pos[i * 3 + 2] = r * Math.cos(phi);
      this.phase[i] = Math.random() * 1000;

      this.colors[i * 3] = 0.0;
      this.colors[i * 3 + 1] = 0.85;
      this.colors[i * 3 + 2] = 1.0;
      this.targetColors[i * 3] = 0.0;
      this.targetColors[i * 3 + 1] = 0.85;
      this.targetColors[i * 3 + 2] = 1.0;
    }
  }

  private initDefaultCorePositions() {
    for (let i = 0; i < this.coreN; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = Math.pow(Math.random(), 0.8) * (this.currentRadius * 0.45);
      this.corePos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      this.corePos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      this.corePos[i * 3 + 2] = r * Math.cos(phi);
    }
  }

  /**
   * Reconfiguration topologique instantanée et fluide lors du changement d'orbe
   */
  private reconfigureTopology(preset: OrbPreset) {
    const style = preset.animation;
    const r = this.currentRadius;

    for (let i = 0; i < this.N; i++) {
      const i3 = i * 3;
      const ph = this.phase[i];

      if (style === 'vortex' || preset.id === 'gargantua') {
        // Disque d'accrétion incliné + jets polaires
        if (i < this.N * 0.82) {
          const angle = Math.random() * Math.PI * 2;
          const rad = 6.0 + Math.pow(Math.random(), 0.5) * (r * 1.55);
          const x0 = Math.cos(angle) * rad;
          const z0 = Math.sin(angle) * rad;
          // Inclinaison de 24 degrés autour de l'axe X
          const tilt = 0.42;
          this.pos[i3] = x0;
          this.pos[i3 + 1] = z0 * Math.sin(tilt);
          this.pos[i3 + 2] = z0 * Math.cos(tilt);
          this.vel[i3] = -Math.sin(angle) * 0.2;
          this.vel[i3 + 1] = 0;
          this.vel[i3 + 2] = Math.cos(angle) * 0.2;
        } else {
          // Jets polaires verticaux
          const sign = i % 2 === 0 ? 1 : -1;
          const h = (Math.random() * r * 1.4 + 4) * sign;
          const beamR = Math.random() * 2.5;
          const angle = Math.random() * Math.PI * 2;
          this.pos[i3] = Math.cos(angle) * beamR;
          this.pos[i3 + 1] = h;
          this.pos[i3 + 2] = Math.sin(angle) * beamR;
          this.vel[i3] = 0;
          this.vel[i3 + 1] = sign * 0.15;
          this.vel[i3 + 2] = 0;
        }
      } else if (style === 'rings' || preset.id === 'saturn_rings') {
        // Corps planétaire + anneaux découpés avec division de Cassini
        if (i < this.N * 0.38) {
          // Planète sphérique centrale
          const theta = Math.random() * Math.PI * 2;
          const phi = Math.acos(2 * Math.random() - 1);
          const pr = Math.pow(Math.random(), 0.7) * 8.2;
          this.pos[i3] = pr * Math.sin(phi) * Math.cos(theta);
          this.pos[i3 + 1] = pr * Math.sin(phi) * Math.sin(theta) * 0.9;
          this.pos[i3 + 2] = pr * Math.cos(phi);
        } else {
          // Anneaux plats inclinés (Ring B: 12-16, Cassini: 16-17.5, Ring A: 17.5-24)
          const angle = Math.random() * Math.PI * 2;
          const inRingA = (i % 3 === 0);
          const rad = inRingA ? (17.5 + Math.random() * 6.5) : (11.5 + Math.random() * 4.5);
          const x0 = Math.cos(angle) * rad;
          const z0 = Math.sin(angle) * rad;
          const tilt = 0.46; // ~27 degrés
          this.pos[i3] = x0;
          this.pos[i3 + 1] = z0 * Math.sin(tilt) + (Math.random() - 0.5) * 0.4;
          this.pos[i3 + 2] = z0 * Math.cos(tilt);
          this.vel[i3] = -Math.sin(angle) * 0.1;
          this.vel[i3 + 1] = 0;
          this.vel[i3 + 2] = Math.cos(angle) * 0.1;
        }
      } else if (style === 'cascade' || preset.id === 'matrix_code') {
        // Colonnes verticales de données descendantes
        const colCount = 48;
        const col = i % colCount;
        const colAngle = (col / colCount) * Math.PI * 2;
        const colRadius = 6.0 + ((col * 7) % 16);
        this.pos[i3] = Math.cos(colAngle) * colRadius + (Math.random() - 0.5) * 0.8;
        this.pos[i3 + 1] = (Math.random() * 2 - 1) * (r * 1.3);
        this.pos[i3 + 2] = Math.sin(colAngle) * colRadius + (Math.random() - 0.5) * 0.8;
        this.vel[i3] = 0;
        this.vel[i3 + 1] = -(0.08 + Math.random() * 0.08);
        this.vel[i3 + 2] = 0;
      } else if (style === 'helix' || preset.id === 'dna_helix') {
        // Double hélice moléculaire ADN
        const isStrandA = (i % 2 === 0);
        const isStrandB = (i % 2 === 1);
        const isRung = (i % 7 === 0);
        const yNorm = (i / this.N) * 2 - 1;
        const h = yNorm * (r * 1.3);
        const theta = yNorm * Math.PI * 4.0;
        const strandR = 8.5;

        if (isRung) {
          // Barreau de liaison entre les 2 brins
          const frac = Math.random() * 2 - 1;
          this.pos[i3] = Math.cos(theta) * (strandR * frac);
          this.pos[i3 + 1] = h;
          this.pos[i3 + 2] = Math.sin(theta) * (strandR * frac);
        } else {
          const shift = isStrandA ? 0 : Math.PI;
          this.pos[i3] = Math.cos(theta + shift) * strandR;
          this.pos[i3 + 1] = h;
          this.pos[i3 + 2] = Math.sin(theta + shift) * strandR;
        }
        this.vel[i3] = 0; this.vel[i3 + 1] = 0; this.vel[i3 + 2] = 0;
      } else if (style === 'tesseract' || preset.id === 'tesseract') {
        // Hypercube 4D: 16 sommets reliés
        const vIdx = i % 16;
        const sx = (vIdx & 1) ? 1 : -1;
        const sy = (vIdx & 2) ? 1 : -1;
        const sz = (vIdx & 4) ? 1 : -1;
        const sw = (vIdx & 8) ? 1 : -1;
        const scale = 8.5;
        // Projection 4D -> 3D
        const wFactor = 1.0 / (2.0 - sw * 0.35);
        this.pos[i3] = sx * scale * wFactor + (Math.random() - 0.5) * 1.5;
        this.pos[i3 + 1] = sy * scale * wFactor + (Math.random() - 0.5) * 1.5;
        this.pos[i3 + 2] = sz * scale * wFactor + (Math.random() - 0.5) * 1.5;
        this.vel[i3] = 0; this.vel[i3 + 1] = 0; this.vel[i3 + 2] = 0;
      } else {
        // Sphère volumétrique harmonique standard
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        const rad = Math.pow(Math.random(), 0.65) * r;
        this.pos[i3] = rad * Math.sin(phi) * Math.cos(theta);
        this.pos[i3 + 1] = rad * Math.sin(phi) * Math.sin(theta);
        this.pos[i3 + 2] = rad * Math.cos(phi);
        this.vel[i3] = (Math.random() - 0.5) * 0.02;
        this.vel[i3 + 1] = (Math.random() - 0.5) * 0.02;
        this.vel[i3 + 2] = (Math.random() - 0.5) * 0.02;
      }
    }

    // Mise à jour immédiate du buffer de géométrie
    this.particleGeo.getAttribute('position').needsUpdate = true;

    // Mise à jour de la lueur d'ambiance dynamique du HUD
    const container = document.getElementById('orb-container');
    if (container && preset.glowColor) {
      container.style.filter = `drop-shadow(0 0 45px ${preset.glowColor})`;
    }
  }

  /**
   * Met à jour les couleurs par vertex selon le mode d'affichage du preset
   */
  private updateVertexColors(theme: ThemePalette) {
    const baseColor = new THREE.Color(theme[this.state] || theme.idle);
    const coreColor = new THREE.Color(theme.core);
    const mode = this.currentPreset.colorMode;

    const cAttr = this.particleGeo.getAttribute('color') as THREE.BufferAttribute;
    if (!cAttr) return;

    for (let i = 0; i < this.N; i++) {
      const i3 = i * 3;
      const x = this.pos[i3], y = this.pos[i3 + 1], z = this.pos[i3 + 2];
      const dist = Math.sqrt(x * x + y * y + z * z) || 0.01;

      let r = baseColor.r;
      let g = baseColor.g;
      let b = baseColor.b;

      if (mode === 'accretion') {
        // Gargantua: Cœur blanc incandescent -> Or chaud -> Écarlate gravitationnel
        const normDist = Math.min(1.0, Math.max(0.0, (dist - 6) / 18));
        if (normDist < 0.25) {
          // Anneau de photons blanc-or
          r = 1.0; g = 0.95; b = 0.8;
        } else if (normDist < 0.65) {
          // Disque chaud orange-ambre
          r = 1.0; g = 0.45 + (1 - normDist) * 0.4; b = 0.05;
        } else {
          // Bord externe rouge magma sombre
          r = 0.85; g = 0.08; b = 0.02;
        }
      } else if (mode === 'eye') {
        // HAL-9000: Pupille centrale blanche -> Iris laser rouge sang -> Coque sombre
        if (dist < 2.0) {
          r = 1.0; g = 1.0; b = 0.9;
        } else if (dist < 7.5) {
          r = 1.0; g = 0.08; b = 0.12;
        } else {
          r = 0.25; g = 0.02; b = 0.04;
        }
      } else if (mode === 'reactor') {
        // Arc Reactor: Noyau palladium blanc pur -> Bobines cyan néon -> Accents or
        if (dist < 5.0) {
          r = 1.0; g = 1.0; b = 1.0;
        } else if (i % 5 === 0) {
          r = 1.0; g = 0.84; b = 0.0;
        } else {
          r = 0.0; g = 0.92; b = 1.0;
        }
      } else if (mode === 'matrix') {
        // Matrix: Tête de colonne blanche -> Vert phosphore intense -> Vert sombre
        const headProgress = (y + this.currentRadius) / (this.currentRadius * 2);
        if (headProgress > 0.88) {
          r = 0.95; g = 1.0; b = 0.95;
        } else {
          r = 0.05; g = 0.95 * headProgress + 0.15; b = 0.15;
        }
      } else if (mode === 'solar') {
        // Solar Flare: Fusion blanc-jaune au cœur -> Orange éruption en surface
        const norm = Math.min(1.0, dist / this.currentRadius);
        r = 1.0;
        g = Math.max(0.1, 0.9 - norm * 0.7);
        b = Math.max(0.0, 0.4 - norm * 0.4);
      } else if (mode === 'saturn') {
        // Saturn: Globe planétaire ocre -> Anneaux platine / or clair
        if (dist < 9.5) {
          r = 0.95; g = 0.82; b = 0.52;
        } else {
          r = 1.0; g = 0.92; b = 0.75;
        }
      } else if (mode === 'helix') {
        // ADN: Brin A cyan, Brin B violet/magenta, barreaux blanc-ambre
        if (i % 7 === 0) {
          r = 1.0; g = 0.95; b = 0.7;
        } else if (i % 2 === 0) {
          r = 0.0; g = 0.95; b = 0.55;
        } else {
          r = 0.85; g = 0.2; b = 1.0;
        }
      } else if (mode === 'synthwave') {
        // Dégradé vertical Outrun: Fuchsia néon en haut -> Cyan nuit en bas
        const normY = (y / this.currentRadius + 1) * 0.5;
        r = normY;
        g = normY * 0.2 + (1 - normY) * 0.6;
        b = (1 - normY);
      } else {
        // Mode 'gradient' standard: Lerp radial Cœur -> Surface
        const norm = Math.min(1.0, dist / this.currentRadius);
        r = coreColor.r * (1 - norm) + baseColor.r * norm;
        g = coreColor.g * (1 - norm) + baseColor.g * norm;
        b = coreColor.b * (1 - norm) + baseColor.b * norm;
      }

      this.targetColors[i3] = r;
      this.targetColors[i3 + 1] = g;
      this.targetColors[i3 + 2] = b;
    }
  }

  /**
   * Application d'un Preset Unifié complet (Physique + Couleurs + Particules + Topologie)
   */
  public setPreset(presetId: string): OrbPreset {
    const preset = getOrbPreset(presetId);
    this.currentPreset = preset;
    this.animationStyle = preset.animation;

    // Lignes synaptiques selon le type d'orbe
    this.lineSegments.visible = preset.hasLines;
    this.lineMat.opacity = preset.lineOpacity || 0.25;

    // Tailles et vitesses
    if (preset.particleSize) {
      this.particleMat.size = preset.particleSize;
    } else {
      this.particleMat.size = 0.95;
    }

    // Couleurs du thème
    const theme = preset.palette;
    this.lineColor.setHex(theme.line);
    this.electronColor.setHex(theme.electron);
    this.lineMat.color.copy(this.lineColor);
    this.electronMat.color.copy(this.electronColor);

    // Réinitialiser la topologie des particules
    this.reconfigureTopology(preset);

    // Mettre à jour l'état et les couleurs
    this.setState(this.state);

    return preset;
  }

  public getCurrentPreset(): OrbPreset {
    return this.currentPreset;
  }

  public getCurrentPresetId(): string {
    return this.currentPreset.id;
  }

  public setAnimationStyle(style: OrbAnimationStyle) {
    this.animationStyle = style;
  }

  public setTheme(themeName: OrbTheme) {
    if (ORB_PRESETS[themeName]) {
      this.setPreset(themeName);
    }
  }

  /**
   * Changement de l'état fonctionnel de l'assistant
   */
  public setState(state: AssistantStateType) {
    this.state = state;
    const theme = this.currentPreset.palette;

    switch (state) {
      case 'idle':
        this.targetRadius = 15;
        this.targetSpeed = 0.25;
        this.targetLineAmount = this.currentPreset.hasLines ? 0.22 : 0.0;
        this.targetElectronRate = 0.005;
        this.vortexStrength = 0.0;
        this.breathAmp = 0.0;
        this.targetColor.setHex(theme.idle);
        this.targetCoreColor.setHex(theme.core);
        break;

      case 'listening':
        this.targetRadius = 13.5;
        this.targetSpeed = 0.35;
        this.targetLineAmount = this.currentPreset.hasLines ? 0.45 : 0.0;
        this.targetElectronRate = 0.012;
        this.vortexStrength = 0.0;
        this.breathAmp = 0.3;
        this.targetColor.setHex(theme.listening);
        this.targetCoreColor.setHex(0xffffff);
        break;

      case 'thinking':
        this.targetRadius = 9.5;
        this.targetSpeed = 0.6;
        this.targetLineAmount = this.currentPreset.hasLines ? 0.9 : 0.0;
        this.targetElectronRate = 0.04;
        this.vortexStrength = 0.25;
        this.breathAmp = 0.45;
        this.targetColor.setHex(theme.thinking);
        this.targetCoreColor.setHex(0xffffff);
        break;

      case 'speaking':
        this.targetRadius = 14.5;
        this.targetSpeed = 0.48;
        this.targetLineAmount = this.currentPreset.hasLines ? 0.7 : 0.0;
        this.targetElectronRate = 0.028;
        this.vortexStrength = 0.4;
        this.breathAmp = 1.0;
        this.targetColor.setHex(theme.speaking);
        this.targetCoreColor.setHex(theme.core);
        break;
    }

    this.updateVertexColors(theme);
  }

  public setVolume(vol: number) {
    this.targetVolume = Math.min(1.0, Math.max(0.0, vol));
  }

  public setQuality(quality: 'low' | 'medium' | 'high') {
    this.quality = quality;
    if (quality === 'low') {
      this.MAX_LINES = 1200;
      this.MAX_ELECTRONS = 35;
    } else if (quality === 'medium') {
      this.MAX_LINES = 2400;
      this.MAX_ELECTRONS = 65;
    } else {
      this.MAX_LINES = 4000;
      this.MAX_ELECTRONS = 100;
    }
  }

  /**
   * Boucle d'animation principale 60 FPS
   */
  private animate() {
    if (this.isDestroyed) return;
    this.animFrameId = requestAnimationFrame(this.animate.bind(this));

    const t = this.clock.getElapsedTime();

    // 1. Interpolation dynamique des paramètres
    const lerpSpeed = 0.05;
    this.currentRadius += (this.targetRadius - this.currentRadius) * lerpSpeed;
    this.currentSpeed += (this.targetSpeed - this.currentSpeed) * lerpSpeed;
    this.lineAmount += (this.targetLineAmount - this.lineAmount) * lerpSpeed;
    this.electronRate += (this.targetElectronRate - this.electronRate) * lerpSpeed;
    this.volume += (this.targetVolume - this.volume) * 0.18;

    // Onde de choc lors d'un pic de volume vocal
    const bassJump = Math.max(0, this.volume - this.prevBass - 0.04) * 4.0;
    this.shockwave = Math.max(this.shockwave * 0.82, bassJump);
    this.prevBass = this.volume;

    // Interpolation des couleurs globales et vertex
    this.currentColor.lerp(this.targetColor, 0.06);
    this.coreColor.lerp(this.targetCoreColor, 0.06);
    this.coreMat.color.copy(this.coreColor);

    const cArr = this.colors;
    const tcArr = this.targetColors;
    const colorCount = this.N * 3;
    for (let c = 0; c < colorCount; c++) {
      cArr[c] += (tcArr[c] - cArr[c]) * 0.08;
    }
    this.particleGeo.getAttribute('color').needsUpdate = true;

    // 2. Rotation globale
    const effectiveSpeed = this.currentSpeed * (this.currentPreset.speedMultiplier || 1.0);
    const style = this.animationStyle;

    let rotY = 0.003 * effectiveSpeed;
    if (style === 'vortex') rotY *= 3.8;
    else if (style === 'helix') rotY *= 2.2;
    else if (style === 'crystal') rotY *= 1.8;
    else if (style === 'rings') rotY *= 1.2;

    this.spinY += rotY;
    this.spinX += Math.sin(t * 0.2) * 0.0008;

    this.particles.rotation.y = this.spinY;
    this.particles.rotation.x = this.spinX;
    this.coreParticles.rotation.y = -this.spinY * 1.3;
    this.coreParticles.rotation.x = this.spinX * 0.8;
    this.lineSegments.rotation.y = this.spinY;
    this.lineSegments.rotation.x = this.spinX;
    this.electronPoints.rotation.y = this.spinY;
    this.electronPoints.rotation.x = this.spinX;

    // 3. Physique cinématique des particules
    const pAttr = this.particleGeo.getAttribute('position') as THREE.BufferAttribute;
    const a = pAttr.array as Float32Array;

    const isSpeaking = this.state === 'speaking';
    const isListening = this.state === 'listening';
    const audioExpansion = (isSpeaking ? this.volume * 4.5 + Math.sin(t * 4.0) * (1.2 * this.breathAmp) : (isListening ? this.volume * 3.0 : 0.0));
    const rTarget = this.currentRadius + audioExpansion;

    for (let i = 0; i < this.N; i++) {
      const i3 = i * 3;
      let x = a[i3], y = a[i3 + 1], z = a[i3 + 2];
      const ph = this.phase[i];
      const dist = Math.sqrt(x * x + y * y + z * z) || 0.01;

      // ── Comportements par style d'orbe ──
      if (style === 'vortex' || this.currentPreset.id === 'gargantua') {
        // Gargantua: Accretion disk avec shear Keplerien & horizon des événements impénétrable
        if (i < this.N * 0.82) {
          const xzDist = Math.sqrt(x * x + z * z) || 0.01;
          const targetDiskR = Math.max(6.2, Math.min(rTarget * 1.5, xzDist));
          // Répulsion de l'horizon absolu
          if (dist < 5.2) {
            const push = (5.2 - dist) * 0.12;
            this.vel[i3] += (x / dist) * push;
            this.vel[i3 + 1] += (y / dist) * push;
            this.vel[i3 + 2] += (z / dist) * push;
          }
          // Aplatir vers le plan du disque incliné
          const tilt = 0.42;
          const idealY = z * Math.sin(tilt);
          this.vel[i3 + 1] += (idealY - y) * 0.06;

          // Vitesse orbitale accrue près de l'horizon (Shear relativiste)
          const orbSpeed = (0.045 / Math.sqrt(Math.max(1.0, xzDist / 10))) * effectiveSpeed;
          this.vel[i3] += (-z / xzDist) * orbSpeed;
          this.vel[i3 + 2] += (x / xzDist) * orbSpeed;
        } else {
          // Jets polaires
          const sign = i % 2 === 0 ? 1 : -1;
          this.vel[i3 + 1] += sign * (0.02 + this.volume * 0.06);
          this.vel[i3] += Math.sin(t * 3.0 + ph) * 0.005;
          this.vel[i3 + 2] += Math.cos(t * 3.0 + ph) * 0.005;
          if (Math.abs(y) > rTarget * 1.5) {
            a[i3 + 1] = 0;
            this.vel[i3 + 1] = 0;
          }
        }
      } else if (style === 'rings' || this.currentPreset.id === 'saturn_rings') {
        // Saturn Rings: Corps sphérique central + anneaux plats extérieurs
        if (i < this.N * 0.38) {
          const pR = 8.2 + this.volume * 1.2;
          const pullP = (dist - pR) * 0.035;
          this.vel[i3] -= (x / dist) * pullP;
          this.vel[i3 + 1] -= (y / dist) * pullP;
          this.vel[i3 + 2] -= (z / dist) * pullP;
        } else {
          const tilt = 0.46;
          const idealY = z * Math.sin(tilt);
          this.vel[i3 + 1] += (idealY - y) * 0.08;
          const xzDist = Math.sqrt(x * x + z * z) || 0.01;
          const orbSpeed = 0.026 * effectiveSpeed;
          this.vel[i3] += (-z / xzDist) * orbSpeed;
          this.vel[i3 + 2] += (x / xzDist) * orbSpeed;
          // Ondulation de l'anneau avec les basses audio
          this.vel[i3 + 1] += Math.sin(xzDist * 0.5 - t * 4.0) * (0.004 + this.volume * 0.03);
        }
      } else if (style === 'cascade' || this.currentPreset.id === 'matrix_code') {
        // Matrix Code Cascade: Pluie numérique en colonnes
        this.vel[i3 + 1] -= (0.065 + (i % 5) * 0.015) * effectiveSpeed * (1.0 + this.volume * 2.0);
        if (a[i3 + 1] < -rTarget * 1.25) {
          a[i3 + 1] = rTarget * 1.25;
          this.vel[i3 + 1] = 0;
        }
      } else if (style === 'helix' || this.currentPreset.id === 'dna_helix') {
        // Double Hélice ADN
        const isStrandA = (i % 2 === 0);
        const yNorm = (y / (rTarget * 1.2));
        const theta = yNorm * Math.PI * 4.0 + t * 2.0 * effectiveSpeed;
        const strandR = 8.5 + this.volume * 1.5;
        const shift = isStrandA ? 0 : Math.PI;

        const targetX = Math.cos(theta + shift) * strandR;
        const targetZ = Math.sin(theta + shift) * strandR;
        this.vel[i3] += (targetX - x) * 0.04;
        this.vel[i3 + 2] += (targetZ - z) * 0.04;
        this.vel[i3 + 1] += Math.sin(ph + t * 2.0) * (0.003 + this.volume * 0.02);
      } else if (style === 'tesseract' || this.currentPreset.id === 'tesseract') {
        // Tesseract 4D: Rotation et pulsation géométrique
        const vIdx = i % 16;
        const sx = (vIdx & 1) ? 1 : -1;
        const sy = (vIdx & 2) ? 1 : -1;
        const sz = (vIdx & 4) ? 1 : -1;
        const sw = (vIdx & 8) ? 1 : -1;

        const rot4D = t * 1.2 * effectiveSpeed;
        const rotX = sx * Math.cos(rot4D) - sw * Math.sin(rot4D);
        const rotW = sx * Math.sin(rot4D) + sw * Math.cos(rot4D);
        const wFactor = 1.0 / (2.2 - rotW * 0.35);

        const targetX = rotX * 8.5 * wFactor;
        const targetY = sy * 8.5 * wFactor;
        const targetZ = sz * 8.5 * wFactor;

        this.vel[i3] += (targetX - x) * 0.04;
        this.vel[i3 + 1] += (targetY - y) * 0.04;
        this.vel[i3 + 2] += (targetZ - z) * 0.04;
      } else if (style === 'tesla' || this.currentPreset.id === 'tesla_coil') {
        // Arcs Tesla haute tension
        const pull = (dist - rTarget) * 0.04;
        this.vel[i3] -= (x / dist) * pull;
        this.vel[i3 + 1] -= (y / dist) * pull;
        this.vel[i3 + 2] -= (z / dist) * pull;

        if (Math.random() < 0.06 + this.volume * 0.15) {
          const arcForce = 0.45 + this.volume * 0.6;
          this.vel[i3] += (Math.random() - 0.5) * arcForce;
          this.vel[i3 + 1] += (Math.random() - 0.5) * arcForce;
          this.vel[i3 + 2] += (Math.random() - 0.5) * arcForce;
        }
      } else if (style === 'crystal') {
        // Prisme polyédrique facetté
        const facet = Math.floor(ph % 12);
        const angle = (facet / 12) * Math.PI * 2 + t * 0.4 * effectiveSpeed;
        const targetX = Math.cos(angle) * rTarget;
        const targetZ = Math.sin(angle) * rTarget;
        this.vel[i3] += (targetX - x) * 0.035;
        this.vel[i3 + 2] += (targetZ - z) * 0.035;
        this.vel[i3 + 1] += (Math.sin(ph + t * 1.5) * (rTarget * 0.5) - y) * 0.025;
      } else if (style === 'quantum') {
        // Ondes quantiques harmoniques
        const wave = Math.sin(dist * 0.75 - t * 5.5 + ph * 0.4) * (0.012 + this.volume * 0.03) * effectiveSpeed;
        this.vel[i3] += (x / dist) * wave;
        this.vel[i3 + 1] += (y / dist) * wave;
        this.vel[i3 + 2] += (z / dist) * wave;
        const pull = (dist - rTarget) * 0.035;
        this.vel[i3] -= (x / dist) * pull;
        this.vel[i3 + 1] -= (y / dist) * pull;
        this.vel[i3 + 2] -= (z / dist) * pull;
      } else if (style === 'equalizer') {
        // Égaliseur de fréquences par latitude
        const lat = Math.abs(y) / (rTarget || 1);
        const eq = Math.sin(lat * Math.PI * 5 + t * 4.0) * (this.volume * 0.06 + 0.005);
        this.vel[i3] += (x / dist) * eq;
        this.vel[i3 + 1] += (y / dist) * eq;
        this.vel[i3 + 2] += (z / dist) * eq;
        const pull = (dist - rTarget) * 0.035;
        this.vel[i3] -= (x / dist) * pull;
        this.vel[i3 + 1] -= (y / dist) * pull;
        this.vel[i3 + 2] -= (z / dist) * pull;
      } else {
        // Plasma multi-octave organique fluide (Défaut)
        const pull = Math.max(0, dist - rTarget) * 0.035 + (dist < rTarget * 0.65 ? -0.025 : 0.001);
        this.vel[i3] -= (x / dist) * pull;
        this.vel[i3 + 1] -= (y / dist) * pull;
        this.vel[i3 + 2] -= (z / dist) * pull;

        const f1 = Math.sin(t * 1.3 + ph) * 0.004 * effectiveSpeed;
        const f2 = Math.cos(t * 1.5 + ph * 1.2) * 0.004 * effectiveSpeed;
        const f3 = Math.sin(t * 1.1 + ph * 0.7) * 0.004 * effectiveSpeed;
        this.vel[i3] += f1;
        this.vel[i3 + 1] += f2;
        this.vel[i3 + 2] += f3;
      }

      // Onde de choc lors d'un pic audio
      if (this.shockwave > 0.01) {
        this.vel[i3] += (x / dist) * this.shockwave * 0.07;
        this.vel[i3 + 1] += (y / dist) * this.shockwave * 0.07;
        this.vel[i3 + 2] += (z / dist) * this.shockwave * 0.07;
      }

      // Amortissement de vélocité
      this.vel[i3] *= 0.95;
      this.vel[i3 + 1] *= 0.95;
      this.vel[i3 + 2] *= 0.95;

      // Déplacement
      a[i3] += this.vel[i3];
      a[i3 + 1] += this.vel[i3 + 1];
      a[i3 + 2] += this.vel[i3 + 2];
    }
    pAttr.needsUpdate = true;

    // 4. Animation du Cœur dense (Nucleus / Photon Ring / HAL Eye)
    const cpAttr = this.coreGeo.getAttribute('position') as THREE.BufferAttribute;
    const ca = cpAttr.array as Float32Array;
    const coreMode = this.currentPreset.colorMode;

    if (coreMode === 'accretion') {
      // Photon ring ultra-dense entourant le trou noir
      const photonR = 5.5 + Math.sin(t * 6.0) * 0.15;
      const tilt = 0.42;
      for (let i = 0; i < this.coreN; i++) {
        const i3 = i * 3;
        const angle = (i / this.coreN) * Math.PI * 2 + t * 4.0;
        const x0 = Math.cos(angle) * photonR;
        const z0 = Math.sin(angle) * photonR;
        ca[i3] = x0;
        ca[i3 + 1] = z0 * Math.sin(tilt);
        ca[i3 + 2] = z0 * Math.cos(tilt);
      }
    } else if (coreMode === 'eye') {
      // HAL-9000: Pupille pulsante
      const pupilR = (isSpeaking ? 2.5 + this.volume * 2.0 : 1.5 + Math.sin(t * 2.0) * 0.2);
      for (let i = 0; i < this.coreN; i++) {
        const i3 = i * 3;
        const angle = (i / this.coreN) * Math.PI * 2;
        const rad = Math.sqrt(Math.random()) * pupilR;
        ca[i3] = Math.cos(angle) * rad;
        ca[i3 + 1] = Math.sin(angle) * rad;
        ca[i3 + 2] = (Math.random() - 0.5) * 0.5;
      }
    } else {
      // Cœur d'énergie sphérique pulsant
      const coreScale = 1.0 + Math.sin(t * 3.0) * 0.08 + this.volume * 0.28;
      for (let i = 0; i < this.coreN; i++) {
        const i3 = i * 3;
        const baseR = Math.pow((i / this.coreN), 0.65) * (this.currentRadius * 0.42) * coreScale;
        const ph = i * 1.5;
        ca[i3] = baseR * Math.sin(ph + t * 0.5);
        ca[i3 + 1] = baseR * Math.cos(ph * 1.2 + t * 0.4);
        ca[i3 + 2] = baseR * Math.sin(ph * 0.7 - t * 0.3);
      }
    }
    cpAttr.needsUpdate = true;

    // 5. Réseau Synaptique (Lignes Plexus)
    if (this.currentPreset.hasLines && this.lineAmount > 0.02) {
      const lpAttr = this.lineGeo.getAttribute('position') as THREE.BufferAttribute;
      const la = lpAttr.array as Float32Array;
      let lineCount = 0;

      const thresholdDist = (3.6 + this.volume * 2.0) * (this.currentRadius / 15);
      const thresholdDistSq = thresholdDist * thresholdDist;
      const step = Math.max(1, Math.floor(this.N / 520));

      this.activeConnections = [];

      for (let i = 0; i < this.N && lineCount < this.MAX_LINES; i += step) {
        const i3 = i * 3;
        const x1 = a[i3], y1 = a[i3 + 1], z1 = a[i3 + 2];

        for (let j = i + step; j < this.N && lineCount < this.MAX_LINES; j += step) {
          const j3 = j * 3;
          const dx = a[j3] - x1, dy = a[j3 + 1] - y1, dz = a[j3 + 2] - z1;
          const distSq = dx * dx + dy * dy + dz * dz;

          if (distSq < thresholdDistSq) {
            const idx = lineCount * 6;
            la[idx] = x1; la[idx + 1] = y1; la[idx + 2] = z1;
            la[idx + 3] = a[j3]; la[idx + 4] = a[j3 + 1]; la[idx + 5] = a[j3 + 2];
            lineCount++;

            if (this.activeConnections.length < 400) {
              this.activeConnections.push({
                x1, y1, z1,
                x2: a[j3], y2: a[j3 + 1], z2: a[j3 + 2]
              });
            }
          }
        }
      }

      this.lineGeo.setDrawRange(0, lineCount * 2);
      lpAttr.needsUpdate = true;
      this.lineMat.opacity = (this.currentPreset.lineOpacity || 0.25) * (this.lineAmount + this.shockwave * 0.4);
    } else {
      this.lineGeo.setDrawRange(0, 0);
      this.activeConnections = [];
    }

    // 6. Électrons lumineux
    if (this.activeConnections.length > 0 && this.electronRate > 0.005) {
      const maxElec = isSpeaking ? 32 : this.state === 'thinking' ? 55 : 12;
      const spawnInterval = isSpeaking ? 0.08 : this.state === 'thinking' ? 0.04 : 0.35;

      if (this.activeElectrons.length < maxElec && (t - this.lastElectronSpawn) > spawnInterval) {
        const conn = this.activeConnections[Math.floor(Math.random() * this.activeConnections.length)];
        this.activeElectrons.push({
          sx: conn.x1, sy: conn.y1, sz: conn.z1,
          ex: conn.x2, ey: conn.y2, ez: conn.z2,
          t: 0,
          speed: 0.025 + Math.random() * 0.035
        });
        this.lastElectronSpawn = t;
      }
    }

    const epAttr = this.electronGeo.getAttribute('position') as THREE.BufferAttribute;
    const ea = epAttr.array as Float32Array;
    let aliveCount = 0;

    for (let e = this.activeElectrons.length - 1; e >= 0; e--) {
      const el = this.activeElectrons[e];
      el.t += el.speed;
      if (el.t >= 1.0) {
        this.activeElectrons.splice(e, 1);
        continue;
      }
      const ei = aliveCount * 3;
      ea[ei] = el.sx + (el.ex - el.sx) * el.t;
      ea[ei + 1] = el.sy + (el.ey - el.sy) * el.t;
      ea[ei + 2] = el.sz + (el.ez - el.sz) * el.t;
      aliveCount++;
    }

    this.electronGeo.setDrawRange(0, aliveCount);
    epAttr.needsUpdate = true;

    // Rendu Three.js
    this.renderer.render(this.scene, this.camera);
  }

  private onResize() {
    if (this.isDestroyed) return;
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  public destroy() {
    this.isDestroyed = true;
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
    }
    this.renderer.dispose();
    if (this.container.contains(this.renderer.domElement)) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}
