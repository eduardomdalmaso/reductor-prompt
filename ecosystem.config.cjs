const path = require('path');
const os = require('os');
const isWin = process.platform === 'win32';
const homeDir = os.homedir();

const pythonPath = isWin
  ? path.join(homeDir, 'miniconda3', 'envs', 'reductor-prompt', 'python.exe')
  : path.join(homeDir, 'miniconda3', 'bin', 'python');

const ollamaPath = isWin ? 'ollama' : path.join(homeDir, '.local', 'bin', 'ollama');

// 1. Definição dos Apps
const ollamaApp = {
  name: 'ollama',
  script: ollamaPath,
  args: 'serve',
  cwd: __dirname,
  instances: 1,
  autorestart: true,
  watch: false,
  interpreter: 'none',
  env: {
    OLLAMA_HOST: '0.0.0.0:11434',
  },
};

const reductorApps = [
  {
    name: 'reductor-api',
    script: 'api.py',
    cwd: __dirname,
    instances: 1,
    autorestart: true,
    watch: false,
    interpreter: pythonPath,
    max_memory_restart: '2G',
    env: {
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
      API_PORT: '8002',
    },
  },
  {
    name: 'reductor-web',
    script: path.join(__dirname, 'web', 'node_modules', 'vite', 'bin', 'vite.js'),
    args: '--port 5173 --host',
    cwd: path.join(__dirname, 'web'),
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
    cwd: __dirname,
    instances: 1,
    autorestart: true,
    watch: false,
    interpreter: pythonPath,
    max_memory_restart: '1G',
    env: {
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
    },
  },
];

// 2. Chaveamento por PM2_TARGET: 'reductor' (padrão) ou 'all'
const target = (process.env.PM2_TARGET || 'reductor').toLowerCase();

module.exports = {
  apps: target === 'all' ? [ollamaApp, ...reductorApps] : reductorApps,
};
