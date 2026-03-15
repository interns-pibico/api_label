import * as THREE from 'three';

// ── Shape definitions ─────────────────────────────────────────
// Coordenadas normalizadas [-1,1], escaladas por `scale` en createCluster()
const SHAPES = {
  cart: {
    // Derivado del SVG shopping-cart-thin (viewBox 256×256)
    // nx=(x-128)/128  ny=-(y-128)/128  (Y invertido: SVG↓ → Three.js↑)
    points: [
      // Handle (barra horizontal, top-left) — 3 pts
      [-0.875, 0.844, 0.00], [-0.805, 0.844, 0.00], [-0.734, 0.844, 0.00],
      // Polo diagonal (handle → cuerpo cesto) — 6 pts
      [-0.641, 0.766, 0.00], [-0.609, 0.523, 0.00], [-0.578, 0.281, 0.00],
      [-0.555, 0.039, 0.00], [-0.523, -0.203, 0.00], [-0.484, -0.445, 0.00],
      // Rim superior del cesto (izq → der) — 6 pts
      [-0.602, 0.531, 0.00], [-0.352, 0.531, 0.00], [-0.109, 0.531, 0.00],
      [ 0.141, 0.531, 0.00], [ 0.391, 0.531, 0.00], [ 0.688, 0.531, 0.00],
      // Lado derecho del cesto (top → base) — 4 pts
      [ 0.648, 0.320, 0.00], [ 0.602, 0.109, 0.00],
      [ 0.547, -0.094, 0.00], [ 0.469, -0.156, 0.00],
      // Base del cesto (der → izq) — 4 pts
      [ 0.211, -0.156, 0.00], [-0.047, -0.156, 0.00],
      [-0.305, -0.156, 0.00], [-0.477, -0.156, 0.00],
      // Rueda izquierda (centro 80,204 → -0.375,-0.594) — 4 pts
      [-0.375, -0.469, 0.00], [-0.250, -0.594, 0.00],
      [-0.375, -0.719, 0.00], [-0.500, -0.594, 0.00],
      // Rueda derecha (centro 184,204 → 0.438,-0.594) — 4 pts
      [ 0.438, -0.469, 0.00], [ 0.563, -0.594, 0.00],
      [ 0.438, -0.719, 0.00], [ 0.313, -0.594, 0.00],
    ],
    color: 0x4682B4, opacity: 0.72,
  },
  offer: {
    // Badge de oferta — starburst exterior + símbolo %
    // ViewBox 472.674×472.674, centro 236.337. nx=(x-236.337)/236.337, ny=-(y-236.337)/236.337
    points: [
      // Starburst outer: 8 tips (r=0.88) intercalados con 8 valles (r=0.72) — 16 pts
      [ 0.000,  0.880, 0.00], [ 0.275,  0.665, 0.00],  // tip 0° / valle 22.5°
      [ 0.622,  0.622, 0.00], [ 0.665,  0.275, 0.00],  // tip 45° / valle 67.5°
      [ 0.880,  0.000, 0.00], [ 0.665, -0.275, 0.00],  // tip 90° / valle 112.5°
      [ 0.622, -0.622, 0.00], [ 0.275, -0.665, 0.00],  // tip 135° / valle 157.5°
      [ 0.000, -0.880, 0.00], [-0.275, -0.665, 0.00],  // tip 180° / valle 202.5°
      [-0.622, -0.622, 0.00], [-0.665, -0.275, 0.00],  // tip 225° / valle 247.5°
      [-0.880,  0.000, 0.00], [-0.665,  0.275, 0.00],  // tip 270° / valle 292.5°
      [-0.622,  0.622, 0.00], [-0.275,  0.665, 0.00],  // tip 315° / valle 337.5°
      // % diagonal (upper-right → lower-left) — 5 pts
      [ 0.180,  0.360, 0.00], [ 0.090,  0.180, 0.00], [ 0.000,  0.000, 0.00],
      [-0.090, -0.180, 0.00], [-0.180, -0.360, 0.00],
      // Círculo superior-izq (centro -0.25, +0.25, r=0.12) — 4 pts
      [-0.250,  0.370, 0.00], [-0.130,  0.250, 0.00],
      [-0.250,  0.130, 0.00], [-0.370,  0.250, 0.00],
      // Círculo inferior-der (centro +0.25, -0.25, r=0.12) — 4 pts
      [ 0.250, -0.130, 0.00], [ 0.370, -0.250, 0.00],
      [ 0.250, -0.370, 0.00], [ 0.130, -0.250, 0.00],
    ],
    color: 0xCB4154, opacity: 0.70,
  },
  lipstick: {
    // Labial en vertical: cuerpo rectangular + collar + bullet con corte diagonal
    points: [
      // Base plana (3 pts)
      [-0.12, -0.82, 0.00], [ 0.00, -0.82, 0.00], [ 0.12, -0.82, 0.00],
      // Borde izquierdo del tubo (4 pts subiendo)
      [-0.12, -0.62, 0.00], [-0.12, -0.35, 0.00], [-0.12, -0.08, 0.00], [-0.12,  0.12, 0.00],
      // Borde derecho del tubo (4 pts subiendo)
      [ 0.12, -0.62, 0.00], [ 0.12, -0.35, 0.00], [ 0.12, -0.08, 0.00], [ 0.12,  0.12, 0.00],
      // Collar ring (3 pts, ligeramente más ancho)
      [-0.17,  0.20, 0.00], [ 0.00,  0.20, 0.00], [ 0.17,  0.20, 0.00],
      // Borde izquierdo del bullet (sube hasta el apex) — 3 pts
      [-0.10,  0.30, 0.00], [-0.10,  0.50, 0.00], [-0.10,  0.70, 0.00],
      // Cara angular (apex izq → bajo der, conectada al borde der) — 1 pt intermedio
      [ 0.00,  0.62, 0.00],
      // Borde derecho del bullet (desde la base hasta el fin del corte) — 3 pts
      [ 0.10,  0.54, 0.00], [ 0.10,  0.40, 0.00], [ 0.10,  0.30, 0.00],
    ],
    color: 0xCB4154, opacity: 0.70,
  },
  tomato: {
    // Tomate — viewBox 32×32, centro (16,16). nx=(x-16)/16, ny=-(y-16)/16
    points: [
      // Cuerpo circular (11 pts, sentido horario desde top-left)
      [-0.338,  0.394, 0.00], [-0.563,  0.188, 0.00], [-0.750, -0.088, 0.00],
      [-0.656, -0.375, 0.00], [-0.375, -0.688, 0.00], [ 0.000, -0.813, 0.00],
      [ 0.375, -0.688, 0.00], [ 0.656, -0.375, 0.00], [ 0.750, -0.088, 0.00],
      [ 0.563,  0.188, 0.00], [ 0.338,  0.394, 0.00],
      // Corona de sépalos (6 pts): left outer, left inner, stem top, right inner, right outer, base
      [-0.419,  0.531, 0.00], [-0.156,  0.569, 0.00], [ 0.000,  0.813, 0.00],
      [ 0.163,  0.563, 0.00], [ 0.431,  0.531, 0.00], [ 0.000,  0.250, 0.00],
    ],
    color: 0xa8c8e8, opacity: 0.68,
  },
};

// Posición fija: shapes en los márgenes exteriores del section-inner (fuera del contenido)
// section-inner 1100px en viewport 1280px → borde world ≈ ±7.9 → shapes a ±8.6/±9.0
const CLUSTER_DEFS = [
  { shape: 'cart',     pos: [-9.0,  1.2, 0], scale: 0.75 },
  { shape: 'tomato',   pos: [-8.7, -1.6, 0], scale: 0.75 },
  { shape: 'offer',    pos: [ 8.7,  1.6, 0], scale: 0.80 },
  { shape: 'lipstick', pos: [ 9.0, -0.8, 0], scale: 0.70 },
];

// ── Geometría compartida ──────────────────────────────────────
const icoGeo = new THREE.SphereGeometry(0.05, 10, 8);

function createCluster({ shape, pos, scale }) {
  const { points, color, opacity } = SHAPES[shape];
  const mat = new THREE.MeshPhongMaterial({
    color, transparent: true, opacity,
    shininess: 90, specular: 0xffffff,
  });
  const mesh = new THREE.InstancedMesh(icoGeo, mat, points.length);
  const dummy = new THREE.Object3D();
  points.forEach(([x, y, z], i) => {
    dummy.position.set(x * scale, y * scale, z * scale);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
  });
  mesh.instanceMatrix.needsUpdate = true;

  const group = new THREE.Group();
  group.position.set(...pos);
  group.userData = {
    baseY: pos[1],
    phase: Math.random() * Math.PI * 2,
    speed: 0.35 + Math.random() * 0.20,
  };
  group.add(mesh);
  return group;
}

// ── Canvas & renderer ─────────────────────────────────────────
const canvas = document.getElementById('particles-canvas');
if (!canvas) throw new Error('particles-canvas not found');

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
camera.position.z = 10;

const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);

// ── Lights ────────────────────────────────────────────────────
scene.add(new THREE.AmbientLight(0xffffff, 0.9));
const pointLight = new THREE.PointLight(0xffffff, 1.2, 30);
pointLight.position.set(3, 4, 7);
scene.add(pointLight);

// ── Clusters ─────────────────────────────────────────────────
const clusters = CLUSTER_DEFS.map(createCluster);
clusters.forEach(c => scene.add(c));

// ── Resize ────────────────────────────────────────────────────
function onResize() {
  const w = canvas.parentElement.clientWidth;
  const h = canvas.parentElement.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', onResize);
onResize();

// ── Mobile (<768px): solo 2 clusters, reposicionados ──
if (window.innerWidth < 768) {
  clusters[1].visible = false;
  clusters[3].visible = false;
  clusters[0].position.set(-2.5,  1.2, 0); clusters[0].userData.baseY =  1.2;
  clusters[2].position.set( 2.5, -1.0, 0); clusters[2].userData.baseY = -1.0;
  clusters.forEach(c => {
    const mesh = c.children[0];
    if (mesh && mesh.material) mesh.material.opacity *= 0.45;
  });
}

// ── Parallax ─────────────────────────────────────────────────
let mouseX = 0, mouseY = 0, targetX = 0, targetY = 0;
window.addEventListener('mousemove', e => {
  mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
  mouseY = -(e.clientY / window.innerHeight - 0.5) * 2;
});

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ── 30fps cap ─────────────────────────────────────────────────
const FRAME_MS = 1000 / 30;
let lastTime = 0, isVisible = true, animId = null;

const observer = new IntersectionObserver(entries => {
  isVisible = entries[0].isIntersecting;
  if (isVisible && !animId) animId = requestAnimationFrame(loop);
}, { threshold: 0.01 });
observer.observe(canvas.parentElement);

// ── Loop ──────────────────────────────────────────────────────
function loop(ts) {
  animId = null;
  if (!isVisible) return;

  const delta = ts - lastTime;
  if (delta < FRAME_MS) { animId = requestAnimationFrame(loop); return; }
  lastTime = ts - (delta % FRAME_MS);

  if (!reducedMotion) {
    const t = ts * 0.001;
    clusters.forEach(c => {
      if (!c.visible) return;
      const { baseY, phase, speed } = c.userData;
      c.position.y = baseY + Math.sin(t * speed + phase) * 0.15;
    });
    targetX += (mouseX * 0.02 - targetX) * 0.05;
    targetY += (mouseY * 0.02 - targetY) * 0.05;
    scene.position.x = targetX;
    scene.position.y = targetY;
  }

  renderer.render(scene, camera);
  animId = requestAnimationFrame(loop);
}

animId = requestAnimationFrame(loop);
