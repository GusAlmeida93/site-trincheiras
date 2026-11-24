import { execSync } from 'node:child_process';

import { composeCommand } from './compose';

export default function globalSetup(): void {
  if (process.env.PW_BASE_URL) {
    return; // caller manages their own stack
  }
  execSync(`${composeCommand()} up -d --build --wait`, {
    stdio: 'inherit',
  });
}
