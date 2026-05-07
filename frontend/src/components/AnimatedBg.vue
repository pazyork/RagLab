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

  // Grid density — larger gap = sparser, more minimal
  const gap = 60

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

  function onMove(e) {
    targetX = e.clientX
    targetY = e.clientY
  }

  // Gentle 2D wave offset at a grid point
  function waveOffset(x, y, t) {
    const f1 = Math.sin(x * 0.008 + t * 0.003) * Math.cos(y * 0.008 - t * 0.002)
    const f2 = Math.sin(x * 0.015 + y * 0.012 + t * 0.004) * 0.5
    return (f1 + f2) * 2 // amplitude in px
  }

  function animate() {
    // Smooth mouse follow
    mouseX += (targetX - mouseX) * 0.03
    mouseY += (targetY - mouseY) * 0.03
    time++
    const t = time

    ctx.clearRect(0, 0, w, h)

    // Draw vertical lines
    const cols = Math.ceil(w / gap) + 1
    const rows = Math.ceil(h / gap) + 1

    ctx.lineWidth = 0.4
    ctx.strokeStyle = 'rgba(57, 217, 138, 0.025)'

    for (let i = 0; i < cols; i++) {
      const baseX = i * gap
      ctx.beginPath()
      for (let j = 0; j <= rows; j++) {
        const baseY = j * gap
        let dx = waveOffset(baseX, baseY, t)
        let dy = waveOffset(baseY, baseX, t + 200)

        // Mouse ripple influence — very gentle
        const mdx = baseX - mouseX
        const mdy = baseY - mouseY
        const mdist = Math.sqrt(mdx * mdx + mdy * mdy)
        if (mdist < 300) {
          const ripple = Math.sin(mdist * 0.03 - t * 0.08) * (1 - mdist / 300) * 3
          dx += ripple * (mdx / (mdist + 1))
          dy += ripple * (mdy / (mdist + 1))
        }

        if (j === 0) ctx.moveTo(baseX + dx, baseY + dy)
        else ctx.lineTo(baseX + dx, baseY + dy)
      }
      ctx.stroke()
    }

    // Draw horizontal lines
    for (let j = 0; j < rows; j++) {
      const baseY = j * gap
      ctx.beginPath()
      for (let i = 0; i <= cols; i++) {
        const baseX = i * gap
        let dx = waveOffset(baseX, baseY, t)
        let dy = waveOffset(baseY, baseX, t + 200)

        const mdx = baseX - mouseX
        const mdy = baseY - mouseY
        const mdist = Math.sqrt(mdx * mdx + mdy * mdy)
        if (mdist < 300) {
          const ripple = Math.sin(mdist * 0.03 - t * 0.08) * (1 - mdist / 300) * 3
          dx += ripple * (mdx / (mdist + 1))
          dy += ripple * (mdy / (mdist + 1))
        }

        if (i === 0) ctx.moveTo(baseX + dx, baseY + dy)
        else ctx.lineTo(baseX + dx, baseY + dy)
      }
      ctx.stroke()
    }

    // Subtle accent dots at intersections — extremely faint
    for (let i = 0; i < cols; i += 2) {
      for (let j = 0; j < rows; j += 2) {
        const baseX = i * gap
        const baseY = j * gap
        let dx = waveOffset(baseX, baseY, t)
        let dy = waveOffset(baseY, baseX, t + 200)

        const mdx = baseX - mouseX
        const mdy = baseY - mouseY
        const mdist = Math.sqrt(mdx * mdx + mdy * mdy)
        if (mdist < 300) {
          const ripple = Math.sin(mdist * 0.03 - t * 0.08) * (1 - mdist / 300) * 3
          dx += ripple * (mdx / (mdist + 1))
          dy += ripple * (mdy / (mdist + 1))
        }

        const alpha = 0.015 + Math.sin(t * 0.01 + i * 0.5 + j * 0.3) * 0.008
        ctx.fillStyle = `rgba(57, 217, 138, ${alpha})`
        ctx.beginPath()
        ctx.arc(baseX + dx, baseY + dy, 1, 0, Math.PI * 2)
        ctx.fill()
      }
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
