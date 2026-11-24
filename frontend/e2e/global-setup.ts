import { execSync } from 'node:child_process';

export default function globalSetup(): void {
  if (process.env.PW_BASE_URL) {
    return; // caller manages their own stack
  }
  execSync('docker compose -f ../docker-compose.test.yml up -d --build --wait', {
    stdio: 'inherit',
  });
}
