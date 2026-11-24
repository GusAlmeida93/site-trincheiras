import { prefersReducedMotion } from '../../lib/motion';
import { playExplosionSound } from './explosion-audio';

export function pulseHit(element: HTMLElement | null): void {
  if (!element || prefersReducedMotion) return;
  element.classList.remove('is-hit');
  void element.offsetWidth; // restart the CSS animation
  element.classList.add('is-hit');
  setTimeout(() => {
    element.classList.remove('is-hit');
  }, 320);
}

export function triggerBombExplosion(targetElement: HTMLElement | null): void {
  playExplosionSound();
  if (!targetElement || prefersReducedMotion) return;

  const rect = targetElement.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;

  const screenFlash = document.createElement('div');
  screenFlash.className = 'bomb-screen-flash';
  screenFlash.style.setProperty('--flash-x', `${(cx / window.innerWidth) * 100}%`);
  screenFlash.style.setProperty('--flash-y', `${(cy / window.innerHeight) * 100}%`);
  document.body.appendChild(screenFlash);
  setTimeout(() => screenFlash.remove(), 320);

  const blast = document.createElement('span');
  blast.className = 'bomb-blast';
  blast.style.left = `${cx}px`;
  blast.style.top = `${cy}px`;

  const smoke = document.createElement('span');
  smoke.className = 'bomb-smoke';
  blast.appendChild(smoke);

  const afterglow = document.createElement('span');
  afterglow.className = 'bomb-afterglow';
  blast.appendChild(afterglow);

  const ring2 = document.createElement('span');
  ring2.className = 'bomb-ring-secondary';
  blast.appendChild(ring2);

  const smokePuffs = [
    { size: 50, x: -15, y: -35, delay: 60, dur: 1100 },
    { size: 40, x: 18, y: -28, delay: 140, dur: 1300 },
    { size: 55, x: -5, y: -42, delay: 200, dur: 1400 },
  ];
  for (const puff of smokePuffs) {
    const s = document.createElement('span');
    s.className = 'bomb-smoke-large';
    s.style.left = `${-puff.size / 2}px`;
    s.style.top = `${-puff.size / 2}px`;
    s.style.width = `${puff.size}px`;
    s.style.height = `${puff.size}px`;
    s.style.setProperty('--smoke-x', `${puff.x}px`);
    s.style.setProperty('--smoke-y', `${puff.y}px`);
    s.style.setProperty('--smoke-delay', `${puff.delay}ms`);
    s.style.setProperty('--smoke-dur', `${puff.dur}ms`);
    blast.appendChild(s);
  }

  const sparkColors = [
    { color: '#fff8e0', glow: 'rgba(255,248,200,0.9)' },
    { color: '#ffd6a6', glow: 'rgba(255,209,122,0.8)' },
    { color: '#ffb060', glow: 'rgba(255,176,96,0.8)' },
    { color: '#ff8c3a', glow: 'rgba(255,140,58,0.7)' },
    { color: '#ffe8c0', glow: 'rgba(255,232,192,0.85)' },
  ];
  const sparksCount = 20;
  for (let i = 0; i < sparksCount; i += 1) {
    const spark = document.createElement('span');
    spark.className = 'bomb-spark';

    const angle = (Math.PI * 2 * i) / sparksCount + (Math.random() - 0.5) * 0.5;
    const distance = 45 + Math.random() * 75;
    const sc = sparkColors[i % sparkColors.length]!;
    const size = 3 + Math.random() * 5;
    const dur = 450 + Math.random() * 350;

    spark.style.setProperty('--dx', `${Math.cos(angle) * distance}px`);
    spark.style.setProperty('--dy', `${Math.sin(angle) * distance}px`);
    spark.style.setProperty('--spark-color', sc.color);
    spark.style.setProperty('--spark-glow', sc.glow);
    spark.style.setProperty('--spark-size', `${size}px`);
    spark.style.setProperty('--spark-dur', `${dur}ms`);
    spark.style.setProperty('--spark-delay', `${Math.random() * 80}ms`);

    blast.appendChild(spark);
  }

  const debrisColors = ['#8b7355', '#6b5640', '#a39070', '#5c4a35', '#7a6348', '#9c8560'];
  const debrisCount = 10;
  for (let i = 0; i < debrisCount; i += 1) {
    const debris = document.createElement('span');
    debris.className = 'bomb-debris';

    const angle = (Math.PI * 2 * i) / debrisCount + (Math.random() - 0.5) * 0.6;
    const distance = 40 + Math.random() * 80;
    const dx = Math.cos(angle) * distance;
    const dy = Math.sin(angle) * distance + Math.random() * 30;
    const rotation = (Math.random() > 0.5 ? 1 : -1) * (180 + Math.random() * 540);
    const w = 4 + Math.random() * 6;
    const h = 3 + Math.random() * 4;
    const dur = 550 + Math.random() * 350;

    debris.style.setProperty('--debris-dx', `${dx}px`);
    debris.style.setProperty('--debris-dy', `${dy}px`);
    debris.style.setProperty('--debris-rot', `${rotation}deg`);
    debris.style.setProperty('--debris-w', `${w}px`);
    debris.style.setProperty('--debris-h', `${h}px`);
    debris.style.setProperty('--debris-color', debrisColors[i % debrisColors.length]!);
    debris.style.setProperty('--debris-dur', `${dur}ms`);
    debris.style.setProperty('--debris-delay', `${Math.random() * 60}ms`);

    blast.appendChild(debris);
  }

  document.body.appendChild(blast);
  setTimeout(() => {
    blast.remove();
  }, 1600);
}
