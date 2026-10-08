// Ferramentas de diagnóstico são habilitadas somente por opção explícita.
export const developmentTools = import.meta.env.PAP_ENVIRONMENT === 'development';
