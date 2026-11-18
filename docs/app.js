"use strict";
(function () {
  document.documentElement.classList.add("js");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- Nav background once the page scrolls ----
  const nav = document.getElementById("nav");
  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 40);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // ---- Reveal on scroll ----
  const reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduced) {
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("in"));
  }

  // ---- Hero video: still frame for reduced motion ----
  const hero = document.querySelector(".hero-video");
  if (hero && reduced) { hero.removeAttribute("autoplay"); hero.pause(); }

  // ---- Clip reel: plays what is on screen, muted; one clip at a time has sound ----
  const clips = Array.from(document.querySelectorAll(".clip"));
  let voiced = null;
  function setSound(clip, on) {
    const video = clip.querySelector("video");
    const button = clip.querySelector(".sound");
    video.muted = !on;
    button.setAttribute("aria-pressed", on ? "true" : "false");
    if (on) { voiced = clip; video.play().catch(() => {}); } else if (voiced === clip) voiced = null;
  }
  for (const clip of clips) {
    const video = clip.querySelector("video");
    const toggle = () => {
      const on = voiced !== clip;
      if (voiced && voiced !== clip) setSound(voiced, false);
      setSound(clip, on);
    };
    clip.querySelector(".sound").addEventListener("click", toggle);
    video.addEventListener("click", toggle);
  }
  if ("IntersectionObserver" in window && !reduced) {
    const vio = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const clip = e.target;
        const video = clip.querySelector("video");
        if (e.isIntersecting) video.play().catch(() => {});
        else { video.pause(); if (voiced === clip) setSound(clip, false); }
      }
    }, { threshold: 0.6 });
    clips.forEach((c) => vio.observe(c));
  }

  // ---- Slot Theory lightbox ----
  const box = document.getElementById("lightbox");
  const boxImg = document.getElementById("lightbox-img");
  const boxCap = document.getElementById("lightbox-caption");
  document.querySelectorAll(".shot").forEach((shot) => {
    shot.addEventListener("click", () => {
      boxImg.src = shot.dataset.full;
      boxImg.alt = shot.querySelector("img").alt;
      boxCap.textContent = shot.dataset.caption;
      if (box.showModal) box.showModal(); else window.open(shot.dataset.full, "_blank");
    });
  });
  document.getElementById("lightbox-close").addEventListener("click", () => box.close());
  box.addEventListener("click", (e) => { if (e.target === box) box.close(); });

  // ---- Slot Theory trailer: nothing loads from YouTube until someone presses play ----
  const trailer = document.getElementById("trailer");
  if (trailer) {
    trailer.addEventListener("click", (e) => {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;  // a new tab, as the link asks
      e.preventDefault();
      const player = document.createElement("iframe");
      player.src = "https://www.youtube-nocookie.com/embed/" + trailer.dataset.video + "?autoplay=1&rel=0&playsinline=1";
      player.title = "Slot Theory trailer";
      player.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      player.allowFullscreen = true;
      player.referrerPolicy = "strict-origin-when-cross-origin";
      const frame = document.createElement("div");
      frame.className = "trailer";
      frame.append(player);
      trailer.replaceWith(frame);
      player.focus();
    });
  }

  // ---- Mo' Mentum toy: a Kestrel chases the pointer, with no brakes ----
  const canvas = document.getElementById("toy");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height, TILE = 16;
  const speedOut = document.getElementById("toy-speed");
  const sprite = new Image();
  sprite.src = "assets/fuck-off/ships/kestrel.png";

  const TURN = 0.75 * Math.PI * 2;  // the Kestrel turns 0.75 times a second
  const THRUST = 320, MAX_SPEED = 430, BOUNCE = 0.6;
  const ship = { x: W * 0.3, y: H * 0.6, vx: 60, vy: -40, a: 0.6, thrust: false };
  const target = { x: W * 0.7, y: H * 0.4 };
  let pointerAt = -1e9, last = 0, t = 0, visible = true, running = false;
  const sparks = [];
  const stars = Array.from({ length: 90 }, () => ({ x: Math.random() * W, y: Math.random() * H, r: Math.random() < 0.15 ? 2 : 1, p: Math.random() * 6 }));

  function pointer(e) {
    const r = canvas.getBoundingClientRect();
    target.x = (e.clientX - r.left) * (W / r.width);
    target.y = (e.clientY - r.top) * (H / r.height);
    pointerAt = t;
    run();
  }
  canvas.addEventListener("pointermove", pointer);
  canvas.addEventListener("pointerdown", pointer);

  function step(dt) {
    t += dt;
    if (!reduced && t - pointerAt > 2.5) {  // nobody steering: the autopilot picks spots to overshoot
      target.x = W / 2 + Math.cos(t * 0.45) * W * 0.34;
      target.y = H / 2 + Math.sin(t * 0.8) * H * 0.3;
    }
    const dx = target.x - ship.x, dy = target.y - ship.y;
    const want = Math.atan2(dx, -dy);
    let err = want - ship.a;
    err = Math.atan2(Math.sin(err), Math.cos(err));
    const turn = Math.max(-TURN * dt, Math.min(TURN * dt, err));
    ship.a += turn;
    ship.thrust = Math.abs(err) < 0.4 && Math.hypot(dx, dy) > 36;
    if (ship.thrust) {
      ship.vx += Math.sin(ship.a) * THRUST * dt;
      ship.vy -= Math.cos(ship.a) * THRUST * dt;
      const s = Math.hypot(ship.vx, ship.vy);
      if (s > MAX_SPEED) { ship.vx *= MAX_SPEED / s; ship.vy *= MAX_SPEED / s; }
      if (Math.random() < 0.9) sparks.push({ x: ship.x - Math.sin(ship.a) * 12, y: ship.y + Math.cos(ship.a) * 12, vx: ship.vx * 0.4 - Math.sin(ship.a) * 60 + (Math.random() - 0.5) * 40, vy: ship.vy * 0.4 + Math.cos(ship.a) * 60 + (Math.random() - 0.5) * 40, life: 0.5 });
    }
    ship.x += ship.vx * dt;
    ship.y += ship.vy * dt;
    const lo = TILE + 12, hiX = W - TILE - 12, hiY = H - TILE - 12;
    if (ship.x < lo) { ship.x = lo; ship.vx = Math.abs(ship.vx) * BOUNCE; }
    if (ship.x > hiX) { ship.x = hiX; ship.vx = -Math.abs(ship.vx) * BOUNCE; }
    if (ship.y < lo) { ship.y = lo; ship.vy = Math.abs(ship.vy) * BOUNCE; }
    if (ship.y > hiY) { ship.y = hiY; ship.vy = -Math.abs(ship.vy) * BOUNCE; }
    for (let i = sparks.length - 1; i >= 0; i--) {
      const s = sparks[i];
      s.x += s.vx * dt; s.y += s.vy * dt; s.life -= dt;
      if (s.life <= 0) sparks.splice(i, 1);
    }
  }

  function draw() {
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, W, H);
    for (const s of stars) {
      ctx.globalAlpha = 0.35 + 0.35 * Math.sin(t * 1.3 + s.p);
      ctx.fillStyle = "#9fb0d0";
      ctx.fillRect(Math.round(s.x), Math.round(s.y), s.r, s.r);
    }
    ctx.globalAlpha = 1;
    // Walls, tiled like the game's
    ctx.fillStyle = "#5b6478";
    for (let x = 0; x < W; x += TILE) { ctx.fillRect(x + 1, 1, TILE - 2, TILE - 2); ctx.fillRect(x + 1, H - TILE + 1, TILE - 2, TILE - 2); }
    for (let y = TILE; y < H - TILE; y += TILE) { ctx.fillRect(1, y + 1, TILE - 2, TILE - 2); ctx.fillRect(W - TILE + 1, y + 1, TILE - 2, TILE - 2); }
    // Target ring
    ctx.strokeStyle = "rgba(242, 201, 76, .55)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(target.x, target.y, 18 + Math.sin(t * 4) * 2, 0, Math.PI * 2);
    ctx.stroke();
    // Exhaust
    for (const s of sparks) {
      ctx.globalAlpha = Math.max(0, s.life * 2);
      ctx.fillStyle = s.life > 0.3 ? "#ffe08a" : "#e07a3a";
      ctx.fillRect(Math.round(s.x) - 2, Math.round(s.y) - 2, 4, 4);
    }
    ctx.globalAlpha = 1;
    // Ship
    ctx.save();
    ctx.translate(Math.round(ship.x), Math.round(ship.y));
    ctx.rotate(ship.a);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    if (sprite.complete && sprite.naturalWidth) ctx.drawImage(sprite, -24, -24, 48, 48);
    ctx.restore();
    // Velocity vector
    ctx.strokeStyle = "rgba(127, 216, 255, .7)";
    ctx.beginPath();
    ctx.moveTo(ship.x, ship.y);
    ctx.lineTo(ship.x + ship.vx * 0.18, ship.y + ship.vy * 0.18);
    ctx.stroke();
    speedOut.textContent = Math.round(Math.hypot(ship.vx, ship.vy)) + " px/s" + (ship.thrust ? " · thrust" : " · drifting");
  }

  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000 || 0);
    last = now;
    step(dt);
    draw();
    // With reduced motion the ship only flies while someone is steering it.
    running = visible && !(reduced && t - pointerAt > 2.5);
    if (running) requestAnimationFrame(frame);
  }

  function run() {
    if (running || !visible) return;
    running = true;
    last = performance.now();
    requestAnimationFrame(frame);
  }

  sprite.onload = draw;
  draw();
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
      if (!reduced) run();
    }).observe(canvas);
  }
  if (!reduced) run();
})();
