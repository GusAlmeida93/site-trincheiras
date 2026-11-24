import { execSync } from 'node:child_process';

import { composeCommand } from './compose';

export default function globalTeardown(): void {
  if (process.env.PW_BASE_URL) {
    return;
  }
  execSync(`${composeCommand()} down -v`, {
    stdio: 'inherit',
  });
}
