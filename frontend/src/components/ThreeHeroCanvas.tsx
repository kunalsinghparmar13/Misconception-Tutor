import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export const ThreeHeroCanvas: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [webglSupported, setWebglSupported] = useState<boolean>(true);

  useEffect(() => {
    // Check reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const prefersReducedMotion = mediaQuery.matches;

    const container = mountRef.current;
    if (!container) return;

    // WebGL capability check
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) {
        setWebglSupported(false);
        return;
      }
    } catch {
      setWebglSupported(false);
      return;
    }

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 340;

    // Three.js Scene in Charcoal & Muted Sage theme
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x171a18, 0.05);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 7.5);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    // Group for all rotating elements
    const neuralGroup = new THREE.Group();
    scene.add(neuralGroup);

    // 1. Central Core: Mathematical Icosahedron with Muted Sage glow
    const coreGeo = new THREE.IcosahedronGeometry(1.4, 1);
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0xa3b5a0, // Muted Sage
      wireframe: true,
      roughness: 0.3,
      metalness: 0.6,
      emissive: 0x283329, // Soft accent
      emissiveIntensity: 0.35,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    neuralGroup.add(coreMesh);

    // 2. Translucent Inner Sphere
    const innerGeo = new THREE.SphereGeometry(0.9, 24, 24);
    const innerMat = new THREE.MeshPhysicalMaterial({
      color: 0x8fbf9b, // Soft Sage
      transparent: true,
      opacity: 0.22,
      roughness: 0.1,
      metalness: 0.1,
      transmission: 0.85,
    });
    const innerSphere = new THREE.Mesh(innerGeo, innerMat);
    neuralGroup.add(innerSphere);

    // 3. Orbital Synaptic Rings (Gimbal Rotation)
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: 0xa3b5a0,
      transparent: true,
      opacity: 0.45,
    });
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x8fbf9b,
      transparent: true,
      opacity: 0.35,
    });

    const ring1 = new THREE.Mesh(new THREE.TorusGeometry(2.1, 0.02, 16, 100), ringMat1);
    ring1.rotation.x = Math.PI / 3;
    neuralGroup.add(ring1);

    const ring2 = new THREE.Mesh(new THREE.TorusGeometry(2.4, 0.015, 16, 100), ringMat2);
    ring2.rotation.y = Math.PI / 4;
    ring2.rotation.x = -Math.PI / 6;
    neuralGroup.add(ring2);

    // 4. Orbiting Particles / Synaptic Nodes
    const particleCount = 70;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleScales = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      const radius = 2.0 + Math.random() * 1.4;

      particlePositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      particlePositions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      particlePositions[i * 3 + 2] = radius * Math.cos(phi);

      particleScales[i] = Math.random() * 0.08 + 0.02;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0xb7c7b2,
      size: 0.08,
      transparent: true,
      opacity: 0.8,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    neuralGroup.add(particleSystem);

    // 5. Floating Academic Glyphs (Sprites for Math & Science)
    const glyphs = ['π', '∑', '√', '∫', '∞', 'λ', 'Δ', 'Ω'];
    const spriteGroup = new THREE.Group();
    neuralGroup.add(spriteGroup);

    glyphs.forEach((symbol, index) => {
      const textCanvas = document.createElement('canvas');
      textCanvas.width = 128;
      textCanvas.height = 128;
      const ctx = textCanvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0)';
        ctx.fillRect(0, 0, 128, 128);
        ctx.font = 'bold 64px "JetBrains Mono", monospace';
        ctx.fillStyle = index % 2 === 0 ? '#A3B5A0' : '#8FBF9B';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = 'rgba(163, 181, 160, 0.5)';
        ctx.shadowBlur = 10;
        ctx.fillText(symbol, 64, 64);
      }

      const texture = new THREE.CanvasTexture(textCanvas);
      const spriteMat = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        opacity: 0.7,
      });
      const sprite = new THREE.Sprite(spriteMat);

      const angle = (index / glyphs.length) * Math.PI * 2;
      const dist = 2.8 + (index % 2) * 0.4;
      sprite.position.set(Math.cos(angle) * dist, (Math.sin(index * 2) * 0.8), Math.sin(angle) * dist);
      sprite.scale.set(0.65, 0.65, 0.65);
      spriteGroup.add(sprite);
    });

    // 6. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const pointLightSage = new THREE.PointLight(0xa3b5a0, 3, 15);
    pointLightSage.position.set(3, 4, 3);
    scene.add(pointLightSage);

    const pointLightMint = new THREE.PointLight(0x8fbf9b, 2.5, 15);
    pointLightMint.position.set(-3, -2, 2);
    scene.add(pointLightMint);

    // Mouse parallax tracking
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      mouseX = x * 0.5;
      mouseY = y * 0.5;
    };
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Animation Loop
    let animId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);

      if (!prefersReducedMotion) {
        const delta = clock.getDelta();
        const time = clock.getElapsedTime();

        coreMesh.rotation.x += delta * 0.25;
        coreMesh.rotation.y += delta * 0.35;

        innerSphere.rotation.y -= delta * 0.15;

        ring1.rotation.z += delta * 0.4;
        ring2.rotation.z -= delta * 0.3;

        particleSystem.rotation.y += delta * 0.1;
        spriteGroup.rotation.y += delta * 0.08;

        // Subtle breathing scale
        const scaleVal = 1 + Math.sin(time * 1.5) * 0.03;
        coreMesh.scale.set(scaleVal, scaleVal, scaleVal);

        // Smooth mouse parallax interpolation
        neuralGroup.rotation.y += (mouseX - neuralGroup.rotation.y) * 0.05;
        neuralGroup.rotation.x += (-mouseY - neuralGroup.rotation.x) * 0.05;
      }

      renderer.render(scene, camera);
    };

    animate();

    // Resize Observer
    const handleResize = () => {
      if (!container) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      coreGeo.dispose();
      coreMat.dispose();
      innerGeo.dispose();
      innerMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
    };
  }, []);

  if (!webglSupported) {
    return (
      <div className="w-full h-full flex items-center justify-center rounded-2xl bg-[#1D221E] border border-[#353C36] p-6 text-center">
        <div className="space-y-2">
          <div className="w-12 h-12 rounded-xl bg-[#283329] border border-[#A3B5A0]/30 mx-auto flex items-center justify-center text-[#A3B5A0]">
            <span className="font-mono text-xl font-bold">AI</span>
          </div>
          <p className="text-xs text-[#B5B9B0]">Cognitive Multi-Subject Hologram Active</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={mountRef}
      className="w-full h-full relative cursor-grab active:cursor-grabbing select-none"
      title="Interactive 3D Academic Cognitive Core"
    />
  );
};
