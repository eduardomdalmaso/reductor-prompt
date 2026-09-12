export interface UserPreferences {
  selectedBook?: string;
  maxTokens?: number;
  queryMode?: 'standard' | 'fast' | 'only_context';
  logLevel?: string;
  autoScrollLogs?: boolean;
}

const STORAGE_KEY = 'reductor_user_preferences_v1';

export class StorageClient {
  static getPreferences(): UserPreferences {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : {};
    } catch {
      return {};
    }
  }

  static savePreferences(prefs: Partial<UserPreferences>) {
    try {
      const current = this.getPreferences();
      const updated = { ...current, ...prefs };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch (e) {
      console.warn('Failed to save preferences to localStorage', e);
    }
  }
}
