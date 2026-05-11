<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref(null)
let animId = null

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  let w, h

  const PARTICLE_COUNT = 360
  const CONNECTION_DIST = 100
  const MOUSE_RADIUS = 300
  const MOUSE_FORCE = 0.004      // 降低整体吸引力（原 0.012）
  const BG_COLOR = 'rgba(8, 8, 8, 0.12)'
  const WAVE_SPEED = 2.5
  const WAVE_WIDTH = 40
  const WAVE_LIFE = 400
  const WAVE_FORCE = 0.25        // 降低波浪基础力（原 0.35）
  const WAVE_MAX_RADIUS = 500    // 超过此距离波浪几乎无影响

  // Low-saturation color palette: white, muted blue, muted green
  const PALETTE = [
    { r: 210, g: 212, b: 214 }, // cool white
    { r: 210, g: 212, b: 214 },
    { r: 200, g: 205, b: 210 }, // slightly bluish white
    { r: 140, g: 170, b: 190 }, // muted blue-grey
    { r: 120, g: 185, b: 160 }, // muted green-grey
    { r: 100, g: 195, b: 150 }, // soft green
    { r: 160, g: 180, b: 200 }, // pale steel blue
  ]

  const particles = []
  const waves = []
  const mouse = { x: -1000, y: -1000 }

  function resize() {
    w = window.innerWidth
    h = window.innerHeight
    const dpr = window.devicePixelRatio || 1
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = w + 'px'
    canvas.style.height = h + 'px'
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  function initParticles() {
    particles.length = 0
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const color = PALETTE[Math.floor(Math.random() * PALETTE.length)]
      const radius = 0.5 + Math.random() * 1.8
      const glowRadius = radius * (1.5 + Math.random() * 2.5)
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.10,
        vy: (Math.random() - 0.5) * 0.10,
        radius,
        glowRadius,
        alphaBase: 0.12 + Math.random() * 0.14,
        alphaPhase: Math.random() * Math.PI * 2,
        color,
      })
    }
  }

  function onMove(e) {
    mouse.x = e.clientX
    mouse.y = e.clientY
  }

  function onClick(e) {
    waves.push({ x: e.clientX, y: e.clientY, birthTime: time })
  }

  let time = 0

  function animate() {
    time++
    ctx.fillStyle = BG_COLOR
    ctx.fillRect(0, 0, w, h)

    // Remove old waves
    for (let i = waves.length - 1; i >= 0; i--) {
      if (time - waves[i].birthTime > WAVE_LIFE) {
        waves.splice(i, 1)
      }
    }

    // Update particles
    for (const p of particles) {
      // Mouse attraction — quadratic falloff so near-field is gentler
      const dx = mouse.x - p.x
      const dy = mouse.y - p.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < MOUSE_RADIUS && dist > 1) {
        const t = 1 - dist / MOUSE_RADIUS          // 0 at edge, 1 at center
        const force = t * t * MOUSE_FORCE           // quadratic: near stays gentle
        p.vx += (dx / dist) * force
        p.vy += (dy / dist) * force
      }

      // Wave repulsion — distance-attenuated so far particles barely feel it
      for (const wave of waves) {
        const age = time - wave.birthTime
        const waveRadius = age * WAVE_SPEED
        const wdx = p.x - wave.x
        const wdy = p.y - wave.y
        const wdist = Math.sqrt(wdx * wdx + wdy * wdy)
        // Particle lies within the wave front ring
        if (wdist > waveRadius - WAVE_WIDTH && wdist < waveRadius + WAVE_WIDTH && wdist > 1) {
          const ringPos = Math.abs(wdist - waveRadius) / WAVE_WIDTH  // 0 at ring center, 1 at edge
          const decay = 1 - age / WAVE_LIFE
          // Distance falloff: particles beyond WAVE_MAX_RADIUS get near-zero force
          const distFalloff = Math.max(0, 1 - wdist / WAVE_MAX_RADIUS)
          const strength = (1 - ringPos) * decay * distFalloff * distFalloff * WAVE_FORCE
          p.vx += (wdx / wdist) * strength
          p.vy += (wdy / wdist) * strength
        }
      }

      p.x += p.vx
      p.y += p.vy
      p.vx *= 0.996
      p.vy *= 0.996

      const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy)
      if (speed > 0.15) {
        p.vx = (p.vx / speed) * 0.15
        p.vy = (p.vy / speed) * 0.15
      }

      if (p.x < -20) p.x = w + 20
      if (p.x > w + 20) p.x = -20
      if (p.y < -20) p.y = h + 20
      if (p.y > h + 20) p.y = -20
    }

    // Draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const p1 = particles[i]
        const p2 = particles[j]
        const dx = p1.x - p2.x
        const dy = p1.y - p2.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < CONNECTION_DIST) {
          const alpha = (1 - dist / CONNECTION_DIST) * 0.045
          ctx.strokeStyle = `rgba(130, 145, 140, ${alpha})`
          ctx.lineWidth = 0.35
          ctx.beginPath()
          ctx.moveTo(p1.x, p1.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.stroke()
        }
      }
    }

    // Draw particles with glow
    for (const p of particles) {
      const breathing = Math.sin(time * 0.006 + p.alphaPhase) * 0.05
      const alpha = Math.max(0.04, p.alphaBase + breathing)
      const { r, g, b } = p.color

      // Outer soft glow (fluorescent halo)
      const outerGlow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.glowRadius * 2)
      outerGlow.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha * 0.08})`)
      outerGlow.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, ${alpha * 0.03})`)
      outerGlow.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
      ctx.fillStyle = outerGlow
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.glowRadius * 2, 0, Math.PI * 2)
      ctx.fill()

      // Inner glow
      const innerGlow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.glowRadius)
      innerGlow.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha * 0.35})`)
      innerGlow.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
      ctx.fillStyle = innerGlow
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.glowRadius, 0, Math.PI * 2)
      ctx.fill()

      // Core dot
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
      ctx.fill()
    }

    animId = requestAnimationFrame(animate)
  }

  resize()
  initParticles()
  window.addEventListener('resize', () => { resize(); initParticles() })
  window.addEventListener('mousemove', onMove)
  window.addEventListener('click', onClick)
  animate()

  onUnmounted(() => {
    cancelAnimationFrame(animId)
    window.removeEventListener('resize', resize)
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('click', onClick)
  })
})
</script>

<template>
  <canvas
    ref="canvasRef"
    style="position:fixed;inset:0;z-index:0;pointer-events:none;opacity:1;"
  />
</template>
