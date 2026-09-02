import * as THREE from 'three';
import { AssistantStateType } from './protocol';

export interface OrbOptions {
  container: HTMLElement;
  particleCount?: number;
}

export class JarvisOrb {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private container: HTMLElement;

  private particleCount: number;
  private particles: THREE.Points;
  private geometry: THREE.BufferGeometry;
  private material: THREE.PointsMaterial;

  private originalPositions: Float32Array;
  private currentPositions: Float32Array;
  private velocities: Float32Array;

  // Orbital rings / Electrons
  private ringMesh: THREE.LineLoop;
  private ringMesh2: THREE.LineLoop;

  // Animation & States
  private state: AssistantStateType = 'idle';
  private targetRadius = 2.0;
  private currentRadius = 2.0;
  private baseColor: THREE.Color = new THREE.Color(0x00e5ff);
  private targetColor: THREE.Color = new THREE.Color(0x00e5ff);
  private rotationSpeed = 0.005;
  private targetRotationSpeed = 0.005;
  private turbulence = 0.05;
  private targetTurbulence = 0.05;

  private volume = 0.0;
  private targetVolume = 0.0;
  private time = 0;

  constructor(options: OrbOptions) {
    this.container = options.container;
    this.particleCount = options.particleCount || 1800;

    // 1. Initialisation Three.js
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(
      55,
      this.container.clientWidth / this.container.clientHeight,
      0.1,
      1000
    );
    this.camera.position.z = 6;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.container.appendChild(this.renderer.domElement);

    // 2. Texture de particule lumineuse
    const texture = this.createGlowTexture();

    // 3. Nuage de particules
    this.geometry = new THREE.BufferGeometry();
    this.originalPositions = new Float32Array(this.particleCount * 3);
    this.currentPositions = new Float32Array(this.particleCount * 3);
    this.velocities = new Float32Array(this.particleCount * 3);

    for (let i = 0; i < this.particleCount; i++) {
      // Distribution sphérique de Fibonacci uniforme
      const phi = Math.acos(1 - (2 * (i + 0.5)) / this.particleCount);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;

      const r = 2.0 + (Math.random() - 0.5) * 0.4;
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);

      this.originalPositions[i * 3] = x;
      this.originalPositions[i * 3 + 1] = y;
      this.originalPositions[i * 3 + 2] = z;

      this.currentPositions[i * 3] = x;
      this.currentPositions[i * 3 + 1] = y;
      this.currentPositions[i * 3 + 2] = z;

      this.velocities[i * 3] = (Math.random() - 0.5) * 0.01;
      this.velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.01;
      this.velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.01;
    }

    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.currentPositions, 3));

    this.material = new THREE.PointsMaterial({
      size: 0.08,
      map: texture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      color: this.baseColor
    });

    this.particles = new THREE.Points(this.geometry, this.material);
    this.scene.add(this.particles);

    // 4. Anneaux orbitaux
    const ringGeo = new THREE.BufferGeometry();
    const ringPoints: THREE.Vector3[] = [];
    const segments = 90;
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * Math.PI * 2;
      ringPoints.push(new THREE.Vector3(Math.cos(theta) * 2.5, Math.sin(theta) * 2.5, 0));
    }
    ringGeo.setFromPoints(ringPoints);
    const ringMat = new THREE.LineBasicMaterial({
      color: 0x00e5ff,
      transparent: true,
      opacity: 0.25,
      blending: THREE.AdditiveBlending
    });

    this.ringMesh = new THREE.LineLoop(ringGeo, ringMat);
    this.ringMesh.rotation.x = Math.PI / 3;
    this.scene.add(this.ringMesh);

    this.ringMesh2 = new THREE.LineLoop(ringGeo.clone(), ringMat.clone());
    this.ringMesh2.rotation.y = Math.PI / 4;
    this.ringMesh2.rotation.x = -Math.PI / 4;
    this.scene.add(this.ringMesh2);

    window.addEventListener('resize', this.onResize);
    this.animate();
  }

  private createGlowTexture(): THREE.Texture {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d')!;

    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.3, 'rgba(0, 229, 255, 0.8)');
    grad.addColorStop(0.7, 'rgba(0, 100, 255, 0.2)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);

    return new THREE.CanvasTexture(canvas);
  }

  private onResize = () => {
    if (!this.container) return;
    this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
  };

  public setState(state: AssistantStateType) {
    this.state = state;

    switch (state) {
      case 'idle':
        this.targetRadius = 2.0;
        this.targetColor.setHex(0x00e5ff); // Cyan calme
        this.targetRotationSpeed = 0.004;
        this.targetTurbulence = 0.03;
        break;

      case 'listening':
        this.targetRadius = 2.4;
        this.targetColor.setHex(0x00b0ff); // Bleu vif électrique
        this.targetRotationSpeed = 0.012;
        this.targetTurbulence = 0.08;
        break;

      case 'thinking':
        this.targetRadius = 1.6;
        this.targetColor.setHex(0xb300ff); // Violet / pourpre intense
        this.targetRotationSpeed = 0.035;
        this.targetTurbulence = 0.15;
        break;

      case 'speaking':
        this.targetRadius = 2.1;
        this.targetColor.setHex(0x00ffff); // Cyan pur lumineux
        this.targetRotationSpeed = 0.015;
        this.targetTurbulence = 0.07;
        break;
    }
  }

  public setVolume(vol: number) {
    this.targetVolume = Math.max(0, Math.min(1, vol));
  }

  private animate = () => {
    requestAnimationFrame(this.animate);
    this.time += 0.02;

    // Lerp fluide des propriétés
    this.currentRadius += (this.targetRadius - this.currentRadius) * 0.08;
    this.rotationSpeed += (this.targetRotationSpeed - this.rotationSpeed) * 0.08;
    this.turbulence += (this.targetTurbulence - this.turbulence) * 0.08;
    this.volume += (this.targetVolume - this.volume) * 0.2;
    this.baseColor.lerp(this.targetColor, 0.08);
    this.material.color.copy(this.baseColor);

    // Respiration de base + impulsion volume
    const breath = Math.sin(this.time * 2) * 0.06;
    const dynamicRadius = this.currentRadius + breath + this.volume * 0.8;

    // Déformation des particules
    const positions = this.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < this.particleCount; i++) {
      const idx = i * 3;
      const ox = this.originalPositions[idx];
      const oy = this.originalPositions[idx + 1];
      const oz = this.originalPositions[idx + 2];

      const len = Math.sqrt(ox * ox + oy * oy + oz * oz);
      const nx = ox / len;
      const ny = oy / len;
      const nz = oz / len;

      // Onde turbulente sinusoïdale
      const wave = Math.sin(this.time * 4 + ox * 2 + oy * 2) * this.turbulence;
      const r = dynamicRadius + wave;

      positions[idx] = nx * r;
      positions[idx + 1] = ny * r;
      positions[idx + 2] = nz * r;
    }
    this.geometry.attributes.position.needsUpdate = true;

    // Rotation de l'orbe et des anneaux
    this.particles.rotation.y += this.rotationSpeed;
    this.particles.rotation.x = Math.sin(this.time * 0.5) * 0.1;

    this.ringMesh.rotation.z += this.rotationSpeed * 1.5;
    this.ringMesh.rotation.y += this.rotationSpeed * 0.8;
    this.ringMesh2.rotation.z -= this.rotationSpeed * 1.2;

    // Opacité des anneaux selon le volume
    const ringMat = this.ringMesh.material as THREE.LineBasicMaterial;
    ringMat.opacity = 0.2 + this.volume * 0.6;
    ringMat.color.copy(this.baseColor);

    this.renderer.render(this.scene, this.camera);
  };

  public destroy() {
    window.removeEventListener('resize', this.onResize);
    this.renderer.dispose();
  }
}
