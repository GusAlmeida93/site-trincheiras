/** The compose invocation for the e2e stack; E2E_PROJECT keeps parallel checkouts apart. */
export function composeCommand(): string {
  const project = process.env.E2E_PROJECT;
  return `docker compose${project ? ` -p ${project}` : ''} -f ../docker-compose.test.yml`;
}
