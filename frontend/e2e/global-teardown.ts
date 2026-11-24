import { execSync } from 'node:child_process';

export default function globalTeardown(): void {
  if (process.env.PW_BASE_URL) {
    return;
  }
  execSync('docker compose -f ../docker-compose.test.yml down -v', {
    stdio: 'inherit',
  });
}
