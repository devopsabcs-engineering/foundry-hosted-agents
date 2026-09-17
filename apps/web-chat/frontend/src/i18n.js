export const DEFAULT_LANGUAGE = 'en-CA';
export const LANGUAGES = ['en-CA', 'fr-CA'];
export const STORAGE_KEY = 'fha-ui-language';

export const french = {
  'ASSESSMENT WORKSPACE': "ESPACE D'\u00c9VALUATION",
  'New assessment': 'Nouvelle \u00e9valuation',
  'THIS SESSION': 'CETTE SESSION',
  'Conversations': 'Conversations',
  'Delete conversation': 'Supprimer la conversation',
  'Not signed in': 'Non connect\u00e9',
  'Sign out': 'Se d\u00e9connecter',
  'AIR CANADA / SECURITY OPERATIONS': 'AIR CANADA / OP\u00c9RATIONS DE S\u00c9CURIT\u00c9',
  'Threat assessment': '\u00c9valuation des menaces',
  'Staging pilot': 'Pilote de pr\u00e9production',
  'THREAT ASSESSMENT AGENT': "AGENT D'\u00c9VALUATION DES MENACES",
  'A new assessment.': 'Une nouvelle \u00e9valuation.',
  'Security starts with access.': "La s\u00e9curit\u00e9 commence par l'acc\u00e8s.",
  'Verifying pilot access...': "V\u00e9rification de l'acc\u00e8s au pilote...",
  'Ready': 'Pr\u00eat',
  'Internal pilot / authorized members only': 'Pilote interne / membres autoris\u00e9s seulement',
  'Sign in with Microsoft': 'Se connecter avec Microsoft',
  'Conversation': 'Conversation',
  'YOU': 'VOUS',
  'ASSESSMENT AGENT': "AGENT D'\u00c9VALUATION",
  'Assessment in progress': '\u00c9valuation en cours',
  'Copied': 'Copi\u00e9',
  'Copy answer': 'Copier la r\u00e9ponse',
  'Synthetic demo queries': 'Requ\u00eates de d\u00e9monstration synth\u00e9tiques',
  'Assessment message': "Message d'\u00e9valuation",
  'Describe the incident or ask a follow-up...': "D\u00e9crivez l'incident ou posez une question de suivi...",
  'Stop response': 'Arr\u00eater la r\u00e9ponse',
  'Send message': 'Envoyer le message',
  'Application version': "Version de l'application",
  'Synthetic or approved pilot data only. Verify recommendations before action.': 'Donn\u00e9es synth\u00e9tiques ou approuv\u00e9es pour le pilote seulement. V\u00e9rifiez les recommandations avant toute action.',
  'Your sign-in needs attention. Sign out and sign in again.': 'Votre connexion n\u00e9cessite une intervention. D\u00e9connectez-vous et reconnectez-vous.',
  'Response stopped.': 'R\u00e9ponse arr\u00eat\u00e9e.',
  'The response was interrupted. Try again.': 'La r\u00e9ponse a \u00e9t\u00e9 interrompue. R\u00e9essayez.',
  'Configuration is unavailable.': 'La configuration est indisponible.',
  'The assessment workspace could not load. Refresh to try again.': "L'espace d'\u00e9valuation n'a pas pu \u00eatre charg\u00e9. Actualisez la page pour r\u00e9essayer.",
  'The request could not complete. Try again.': "La requ\u00eate n'a pas pu aboutir. R\u00e9essayez.",
  'The assessment could not complete. Try again.': "L'\u00e9valuation n'a pas pu aboutir. R\u00e9essayez.",
  'The service is temporarily unavailable.': 'Le service est temporairement indisponible.',
  'Sign-in verification is temporarily unavailable.': 'La v\u00e9rification de connexion est temporairement indisponible.',
  'A valid access token is required.': "Un jeton d'acc\u00e8s valide est requis.",
  'This application is not authorized.': "Cette application n'est pas autoris\u00e9e.",
  'Chat permission is required.': "L'autorisation de clavardage est requise.",
  'Pilot membership is required. Contact the pilot administrator.': "Vous devez \u00eatre membre du pilote. Communiquez avec l'administrateur du pilote.",
  'A user identity is required.': 'Une identit\u00e9 utilisateur est requise.',
  'Sign in to continue.': 'Connectez-vous pour continuer.',
  'Pilot capacity reached. Try again later.': 'La capacit\u00e9 du pilote est atteinte. R\u00e9essayez plus tard.',
  'Close an existing conversation before starting another.': "Fermez une conversation existante avant d'en commencer une autre.",
  'Conversation not found. Start a new conversation.': 'Conversation introuvable. Commencez une nouvelle conversation.',
  'Conversation expired. Start a new conversation.': 'Conversation expir\u00e9e. Commencez une nouvelle conversation.',
  'Stop the current response first.': "Arr\u00eatez d'abord la r\u00e9ponse en cours.",
  'This request key was already used for a different message.': 'Cette cl\u00e9 de requ\u00eate a d\u00e9j\u00e0 servi pour un autre message.',
  'A response is already in progress.': 'Une r\u00e9ponse est d\u00e9j\u00e0 en cours.',
  'Conversation limit reached. Start a new conversation.': 'Limite de conversation atteinte. Commencez une nouvelle conversation.',
  'The pilot is busy. Try again shortly.': 'Le pilote est occup\u00e9. R\u00e9essayez sous peu.',
};

export function translate(language, text) {
  return language === 'fr-CA' ? french[text] ?? text : text;
}

export function errorText(language, message) {
  const match = /^(.*) Reference: ([0-9a-f-]{36})$/i.exec(message);
  const text = match ? match[1] : message;
  const known = Object.hasOwn(french, text);
  const localized = translate(language, known ? text : 'The request could not complete. Try again.');
  return match ? `${localized} ${language === 'fr-CA' ? 'R\u00e9f\u00e9rence' : 'Reference'}: ${match[2]}` : localized;
}

export function storedLanguage(storage) {
  try {
    const language = (storage ?? globalThis.localStorage).getItem(STORAGE_KEY);
    return LANGUAGES.includes(language) ? language : DEFAULT_LANGUAGE;
  } catch {
    return DEFAULT_LANGUAGE;
  }
}