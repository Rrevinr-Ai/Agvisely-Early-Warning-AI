/**
 * PM2 process file — backend :9603, frontend :9604
 * Usage on VPS:
 *   pm2 start ecosystem.config.cjs
 *   pm2 save && pm2 startup
 */
module.exports = {
  apps: [
    {
      name: "agvisely-backend",
      cwd: __dirname,
      script: "venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 9603",
      interpreter: "none",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "agvisely-frontend",
      cwd: `${__dirname}/frontend`,
      script: "node_modules/.bin/serve",
      args: "-s dist -l 9604",
      interpreter: "none",
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      watch: false,
    },
  ],
};
