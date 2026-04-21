export const WIKI_FOLDER_CONFIG = {
  allowedFolders: ['concepts', 'entities', 'summaries'] as const,
};

export type WikiFolder = typeof WIKI_FOLDER_CONFIG.allowedFolders[number];