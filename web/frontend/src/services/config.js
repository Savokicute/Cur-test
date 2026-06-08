import api from './api';

export async function getConfig() {
  return api.get('/config');
}

export async function getConfigModule(module) {
  return api.get('/config/module', { params: { module } });
}

export async function updateConfigModule(module, value) {
  return api.put('/config/module', { value }, { params: { module } });
}

export async function saveConfig(content, createBackup = true) {
  return api.put('/config', null, {
    params: { create_backup: createBackup },
    data: content ? { content } : null,
  });
}

export async function saveConfigParsed(parsed, createBackup = true) {
  return api.put('/config', null, {
    params: { create_backup: createBackup },
    data: parsed ? { parsed } : null,
  });
}

export async function getConfigSchema() {
  return api.get('/config/schema');
}

export async function listBackups() {
  return api.get('/config/backups');
}

export async function restoreBackup(filename) {
  return api.post('/config/restore', null, { params: { filename } });
}
