import { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

// ─── AI Node Network ──────────────────────────────────────────────────────────

interface NodeData {
  position: THREE.Vector3;
  connections: number[];
  phase: number;
  speed: number;
}

function NetworkNodes({ mouse }: { mouse: React.MutableRefObject<[number, number]> }) {
  const groupRef = useRef<THREE.Group>(null);
  const linesRef = useRef<THREE.LineSegments>(null);

  const { nodes, linePositions } = useMemo(() => {
    const count = 28;
    const nodes: NodeData[] = [];
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 2.5 + Math.random() * 1.8;
      nodes.push({
        position: new THREE.Vector3(
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.sin(phi) * Math.sin(theta) * 0.55,
          r * Math.cos(phi),
        ),
        connections: [],
        phase: Math.random() * Math.PI * 2,
        speed: 0.3 + Math.random() * 0.5,
      });
    }

    // Build connections: each node connects to nearest 2
    const linePositions: number[] = [];
    for (let i = 0; i < count; i++) {
      const distances: [number, number][] = [];
      for (let j = 0; j < count; j++) {
        if (i === j) continue;
        distances.push([j, nodes[i].position.distanceTo(nodes[j].position)]);
      }
      distances.sort((a, b) => a[1] - b[1]);
      const nearestCount = 2 + Math.floor(Math.random() * 2);
      for (let k = 0; k < Math.min(nearestCount, distances.length); k++) {
        const j = distances[k][0];
        if (!nodes[i].connections.includes(j)) {
          nodes[i].connections.push(j);
          linePositions.push(
            ...nodes[i].position.toArray(),
            ...nodes[j].position.toArray(),
          );
        }
      }
    }
    return { nodes, linePositions };
  }, []);

  const sphereGeometries = useMemo(() => {
    return nodes.map(() => new THREE.SphereGeometry(0.045, 8, 8));
  }, [nodes]);

  const lineGeometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(linePositions, 3),
    );
    return geo;
  }, [linePositions]);

  const nodeMaterials = useMemo(() => {
    return nodes.map((_, i) => {
      const t = i / nodes.length;
      const color = new THREE.Color().lerpColors(
        new THREE.Color('#d4d4d8'),
        new THREE.Color('#38bdf8'),
        t,
      );
      return new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9 });
    });
  }, [nodes]);

  const lineMaterial = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: '#a1a1aa',
        transparent: true,
        opacity: 0.12,
      }),
    [],
  );

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;
    const [mx, my] = mouse.current;
    groupRef.current.rotation.y = t * 0.04 + mx * 0.3;
    groupRef.current.rotation.x = my * 0.15;

    // Pulse individual nodes
    sphereGeometries.forEach((_, i) => {
      const mesh = groupRef.current!.children[i] as THREE.Mesh;
      if (mesh) {
        const pulse = Math.sin(t * nodes[i].speed + nodes[i].phase) * 0.5 + 0.5;
        const mat = nodeMaterials[i];
        mat.opacity = 0.5 + pulse * 0.5;
      }
    });
  });

  return (
    <group ref={groupRef}>
      {nodes.map((node, i) => (
        <mesh key={i} position={node.position} geometry={sphereGeometries[i]} material={nodeMaterials[i]} />
      ))}
      <lineSegments ref={linesRef} geometry={lineGeometry} material={lineMaterial} />
    </group>
  );
}

// ─── Ambient Particle Field ────────────────────────────────────────────────────

function ParticleField() {
  const ref = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const count = 900;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 20;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 12;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 15 - 3;
    }
    return positions;
  }, []);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geo;
  }, [positions]);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.y = state.clock.elapsedTime * 0.012;
      ref.current.rotation.x = state.clock.elapsedTime * 0.005;
    }
  });

  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial
        size={0.016}
        color="#4dd9e8"
        transparent
        opacity={0.35}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

// ─── Central Core ─────────────────────────────────────────────────────────────

function CoreGlobe({ mouse }: { mouse: React.MutableRefObject<[number, number]> }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!meshRef.current || !wireRef.current) return;
    const t = state.clock.elapsedTime;
    const [mx, my] = mouse.current;
    meshRef.current.rotation.y = t * 0.15 + mx * 0.2;
    meshRef.current.rotation.x = my * 0.1;
    wireRef.current.rotation.y = -t * 0.08;
    wireRef.current.rotation.z = t * 0.06;
    const pulse = Math.sin(t * 1.5) * 0.05;
    meshRef.current.scale.setScalar(1 + pulse);
  });

  return (
    <group>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.0, 1]} />
        <meshBasicMaterial
          color="#d4d4d8"
          wireframe
          transparent
          opacity={0.18}
        />
      </mesh>
      <mesh ref={wireRef}>
        <icosahedronGeometry args={[1.3, 2]} />
        <meshBasicMaterial
          color="#38bdf8"
          wireframe
          transparent
          opacity={0.07}
        />
      </mesh>
    </group>
  );
}

// ─── Scene ────────────────────────────────────────────────────────────────────

function Scene({ mouse }: { mouse: React.MutableRefObject<[number, number]> }) {
  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(0, 0, 7.5);
  }, [camera]);

  return (
    <>
      <ambientLight intensity={0.15} />
      <pointLight position={[4, 3, 4]} color="#f5f5f5" intensity={1.5} />
      <pointLight position={[-4, -2, -4]} color="#38bdf8" intensity={0.8} />
      <ParticleField />
      <NetworkNodes mouse={mouse} />
      <CoreGlobe mouse={mouse} />
    </>
  );
}

// ─── Export ───────────────────────────────────────────────────────────────────

interface HeroSceneProps {
  mouse: React.MutableRefObject<[number, number]>;
  reducedMotion?: boolean;
}

export default function HeroScene({ mouse, reducedMotion }: HeroSceneProps) {
  if (reducedMotion) {
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse at 50% 60%, rgba(255,255,255,0.04) 0%, transparent 70%)',
        }}
      />
    );
  }

  return (
    <Canvas
      style={{ position: 'absolute', inset: 0 }}
      gl={{
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
        failIfMajorPerformanceCaveat: false,
      }}
      dpr={[1, 1.5]}
      camera={{ fov: 60, near: 0.1, far: 100 }}
    >
      <Scene mouse={mouse} />
    </Canvas>
  );
}
