const path = require('path');
const os = require('os');
const isWin = process.platform === 'win32';
const homeDir = os.homedir();
const docsDir = path.resolve(__dirname, '..');

const pythonPath = isWin
  ? path.join(homeDir, 'miniconda3', 'envs', 'reductor-prompt', 'python.exe')
  : path.join(homeDir, 'miniconda3', 'bin', 'python');

const ollamaPath = isWin ? 'ollama' : path.join(homeDir, '.local', 'bin', 'ollama');

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
    OLLAMA_HOST: '0.0.0.0:11434',
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

// 3. HydraForge & HydraVault Apps
const hydraForgeDir = path.join(docsDir, 'HydraForge');
const hydraVaultDir = path.join(docsDir, 'HydraVault');

const hydraApps = [
  {
    name: 'hydra-forge',
    script: isWin ? 'hydraforge.exe' : './hydraforge',
    cwd: hydraForgeDir,
    instances: 1,
    autorestart: true,
    watch: false,
    interpreter: 'none',
    env: {
      PORT: '8081',
    },
  },
  {
    name: 'hydra-vault',
    script: isWin ? 'hydravault.exe' : './hydravault',
    cwd: hydraVaultDir,
    instances: 1,
    autorestart: true,
    watch: false,
    interpreter: 'none',
    env: {
      PORT: '8082',
    },
  },
];

// 4. Seleção de Perfil via PM2_TARGET
// Opções: 'reductor' (padrão), 'hydra', 'suite' ou 'all'
const target = (process.env.PM2_TARGET || 'reductor').toLowerCase();

let selectedApps = reductorApps;
if (target === 'hydra') {
  selectedApps = hydraApps;
} else if (target === 'suite' || target === 'all') {
  selectedApps = [...reductorApps, ...hydraApps, ...(target === 'all' ? [ollamaApp] : [])];
}

module.exports = {
  apps: selectedApps,
};
