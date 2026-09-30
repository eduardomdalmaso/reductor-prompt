const path = require('path');
const os = require('os');
const isWin = process.platform === 'win32';
const homeDir = os.homedir();
const docsDir = path.resolve(__dirname, '..');

const pythonPath = isWin
  ? path.join(homeDir, 'miniconda3', 'envs', 'reductor-prompt', 'python.exe')
  : path.join(homeDir, 'miniconda3', 'bin', 'python');

const ollamaPath = isWin
  ? path.join(homeDir, 'AppData', 'Local', 'Programs', 'Ollama', 'ollama.exe')
  : path.join(homeDir, '.local', 'bin', 'ollama');

// 1. Ollama
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
    OLLAMA_HOST: '127.0.0.1:11434',
    OLLAMA_ORIGINS: '*',
  },
};

// 2. ReductorPrompt Apps
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
    args: '--port 5174 --host',
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

// 3. HydraForge Apps (FastAPI Backend + Web SPA)
const hydraForgeDir = path.join(docsDir, 'HydraForge');
const hydraForgeWebDir = path.join(hydraForgeDir, 'web');

const hydraApps = [
  {
    name: 'hydra-forge-api',
    script: 'api/main.py',
    cwd: hydraForgeDir,
    instances: 1,
    autorestart: true,
    watch: false,
    interpreter: pythonPath,
    max_memory_restart: '2G',
    env: {
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8',
      API_PORT: '8088',
    },
  },
  {
    name: 'hydra-forge-web',
    script: path.join(hydraForgeWebDir, 'node_modules', 'vite', 'bin', 'vite.js'),
    args: '--port 8081 --host',
    cwd: hydraForgeWebDir,
    instances: 1,
    autorestart: true,
    watch: false,
    interpreter: 'node',
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'development',
    },
  },
];

// 4. Seleção de Perfil via PM2_TARGET: 'reductor', 'hydra', 'suite' (padrão) ou 'all'
const target = (process.env.PM2_TARGET || 'suite').toLowerCase();

let selectedApps = [ollamaApp, ...reductorApps, ...hydraApps];
if (target === 'reductor') {
  selectedApps = [ollamaApp, ...reductorApps];
} else if (target === 'hydra') {
  selectedApps = hydraApps;
} else if (target === 'all' || target === 'suite') {
  selectedApps = [ollamaApp, ...reductorApps, ...hydraApps];
}

module.exports = {
  apps: selectedApps,
};
