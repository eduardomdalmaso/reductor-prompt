module.exports = {
  apps: [
    {
      name: 'ollama',
      script: '/home/hades/.local/bin/ollama',
      args: 'serve',
      cwd: '/home/hades/Documents/reductor-prompt',
      instances: 1,
      autorestart: true,
      watch: false,
      interpreter: 'none',
      env: {
        OLLAMA_HOST: '0.0.0.0:11434',
      },
    },
    {
      name: 'reductor-api',
      script: 'api.py',
      cwd: '/home/hades/Documents/reductor-prompt',
      instances: 1,
      autorestart: true,
      watch: false,
      interpreter: '/home/hades/miniconda3/bin/python',
      max_memory_restart: '2G',
      env: {
        PYTHONUNBUFFERED: '1',
        API_PORT: '8002',
      },
    },
    {
      name: 'reductor-web',
      script: 'node_modules/vite/bin/vite.js',
      args: '--port 5173 --host',
      cwd: '/home/hades/Documents/reductor-prompt/web',
      instances: 1,
      autorestart: true,
      watch: false,
      interpreter: 'node',
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'development',
      },
    },
    {
      name: 'gerar_relatorio',
      script: 'gerar_relatorio.py',
      cwd: '/home/hades/Documents/reductor-prompt',
      instances: 1,
      autorestart: true,
      watch: false,
      interpreter: '/home/hades/miniconda3/bin/python',
      max_memory_restart: '1G',
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
  ],
};
