type AudioContextConstructor = typeof AudioContext;

let blastAudioContext: AudioContext | null = null;
let blastNoiseBuffer: AudioBuffer | null = null;

function getBlastAudioContext(): AudioContext | null {
  const ContextClass: AudioContextConstructor | undefined =
    window.AudioContext ??
    (window as Window & { webkitAudioContext?: AudioContextConstructor })
      .webkitAudioContext;
  if (!ContextClass) return null;

  if (!blastAudioContext) {
    blastAudioContext = new ContextClass();
  }
  return blastAudioContext;
}

function getBlastNoiseBuffer(context: AudioContext): AudioBuffer {
  if (blastNoiseBuffer && blastNoiseBuffer.sampleRate === context.sampleRate) {
    return blastNoiseBuffer;
  }

  const length = Math.floor(context.sampleRate * 1.8);
  const buffer = context.createBuffer(1, length, context.sampleRate);
  const channel = buffer.getChannelData(0);

  for (let i = 0; i < length; i += 1) {
    const decay = 1 - i / length;
    channel[i] = (Math.random() * 2 - 1) * Math.pow(decay, 1.35);
  }

  blastNoiseBuffer = buffer;
  return blastNoiseBuffer;
}

/**
 * Creates and resumes the audio context. Browsers only allow that inside a
 * user gesture, and the explosion now plays after a network round trip, so
 * the games call this from the click or drop handler itself.
 */
export function primeExplosionAudio(): void {
  const context = getBlastAudioContext();
  if (context?.state === 'suspended') {
    context.resume().catch(() => {});
  }
}

export function playExplosionSound(): void {
  const context = getBlastAudioContext();
  if (!context) return;

  if (context.state === 'suspended') {
    context.resume().catch(() => {});
  }

  const now = context.currentTime;
  const compressor = context.createDynamicsCompressor();
  compressor.threshold.setValueAtTime(-18, now);
  compressor.knee.setValueAtTime(14, now);
  compressor.ratio.setValueAtTime(6, now);
  compressor.attack.setValueAtTime(0.002, now);
  compressor.release.setValueAtTime(0.42, now);
  compressor.connect(context.destination);

  const master = context.createGain();
  master.gain.setValueAtTime(0.0001, now);
  master.gain.exponentialRampToValueAtTime(0.68, now + 0.01);
  master.gain.exponentialRampToValueAtTime(0.36, now + 0.48);
  master.gain.exponentialRampToValueAtTime(0.0001, now + 1.9);
  master.connect(compressor);

  const noiseSource = context.createBufferSource();
  noiseSource.buffer = getBlastNoiseBuffer(context);
  const noiseFilter = context.createBiquadFilter();
  noiseFilter.type = 'lowpass';
  noiseFilter.frequency.setValueAtTime(820, now);
  noiseFilter.frequency.exponentialRampToValueAtTime(62, now + 1.35);
  const noiseGain = context.createGain();
  noiseGain.gain.setValueAtTime(0.0001, now);
  noiseGain.gain.exponentialRampToValueAtTime(1.42, now + 0.012);
  noiseGain.gain.exponentialRampToValueAtTime(0.58, now + 0.46);
  noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.52);

  noiseSource.connect(noiseFilter);
  noiseFilter.connect(noiseGain);
  noiseGain.connect(master);
  noiseSource.start(now);
  noiseSource.stop(now + 1.62);

  const thump = context.createOscillator();
  thump.type = 'triangle';
  thump.frequency.setValueAtTime(178, now);
  thump.frequency.exponentialRampToValueAtTime(28, now + 0.98);
  const thumpGain = context.createGain();
  thumpGain.gain.setValueAtTime(0.0001, now);
  thumpGain.gain.exponentialRampToValueAtTime(1.28, now + 0.025);
  thumpGain.gain.exponentialRampToValueAtTime(0.18, now + 0.55);
  thumpGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.15);
  thump.connect(thumpGain);
  thumpGain.connect(master);
  thump.start(now);
  thump.stop(now + 1.2);

  const rumble = context.createOscillator();
  rumble.type = 'sine';
  rumble.frequency.setValueAtTime(56, now + 0.08);
  rumble.frequency.exponentialRampToValueAtTime(22, now + 1.55);
  const rumbleGain = context.createGain();
  rumbleGain.gain.setValueAtTime(0.0001, now);
  rumbleGain.gain.exponentialRampToValueAtTime(0.34, now + 0.12);
  rumbleGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.62);
  rumble.connect(rumbleGain);
  rumbleGain.connect(master);
  rumble.start(now + 0.05);
  rumble.stop(now + 1.64);

  const crack = context.createOscillator();
  crack.type = 'square';
  crack.frequency.setValueAtTime(980, now);
  crack.frequency.exponentialRampToValueAtTime(220, now + 0.16);
  const crackGain = context.createGain();
  crackGain.gain.setValueAtTime(0.0001, now);
  crackGain.gain.exponentialRampToValueAtTime(0.24, now + 0.003);
  crackGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.18);
  crack.connect(crackGain);
  crackGain.connect(master);
  crack.start(now);
  crack.stop(now + 0.2);
}
