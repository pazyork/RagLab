<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref(null)
let animId = null
let mouseX = -1000
let mouseY = -1000
let targetX = -1000
let targetY = -1000

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  let w, h
  let time = 0

  // 3 very subtle orbs — low saturation, barely visible
  const orbs = [
    { baseX: 0.25, baseY: 0.3, r: 20, g: 45, b: 60, size: 350, phase: 0, speed: 0.001 },
    { baseX: 0.75, baseY: 0.6, r: 35, g: 28, b: 50, size: 400, phase: 2, speed: 0.0012 },
    { baseX: 0.5,  baseY: 0.8, r: 25, g: 50, b: 40, size: 300, phase: 4, speed: 0.0008 },
  ]

  function resize() {
    w = window.innerWidth
    h = window.innerHeight
    canvas.width = w
    canvas.height = h
  }

  function onMove(e) {
    targetX = e.clientX
    targetY = e.clientY
  }

  function animate() {
    mouseX += (targetX - mouseX) * 0.02
    mouseY += (targetY - mouseY) * 0.02
    time++

    ctx.clearRect(0, 0, w, h)

    for (const o of orbs) {
      // Slow orbit around base position
      o.phase += o.speed
      const orbitR = 40
      const ox = o.baseX * w + Math.cos(o.phase) * orbitR
      const oy = o.baseY * h + Math.sin(o.phase * 0.7) * orbitR

      // Very slight mouse influence (pull toward cursor gently)
      const dx = mouseX - ox
      const dy = mouseY - oy
      const dist = Math.sqrt(dx * dx + dy * dy)
      const pull = Math.min(dist * 0.015, 30)
      const angle = Math.atan2(dy, dx)
      const x = ox + Math.cos(angle) * pull
      const y = oy + Math.sin(angle) * pull

      // Draw subtle radial glow
      const alpha = 0.035 + Math.sin(time * 0.008 + o.phase) * 0.01
      const grad = ctx.createRadialGradient(x, y, 0, x, y, o.size)
      grad.addColorStop(0, `rgba(${o.r},${o.g},${o.b},${alpha})`)
      grad.addColorStop(1, `rgba(${o.r},${o.g},${o.b},0)`)
      ctx.fillStyle = grad
      ctx.beginPath()
      ctx.arc(x, y, o.size, 0, Math.PI * 2)
      ctx.fill()
    }

    animId = requestAnimationFrame(animate)
  }

  resize()
  window.addEventListener('resize', resize)
  window.addEventListener('mousemove', onMove)
  animate()

  onUnmounted(() => {
    cancelAnimationFrame(animId)
    window.removeEventListener('resize', resize)
    window.removeEventListener('mousemove', onMove)
  })
})
</script>

<template>
  <canvas
    ref="canvasRef"
    style="position:fixed;inset:0;z-index:0;pointer-events:none;opacity:1;"
  />
</template>
