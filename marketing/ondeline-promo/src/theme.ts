/**
 * Tokens de marca da Ondeline — copiados de
 * apps/cliente-mobile/lib/core/branding/brand_tokens.dart (fonte de verdade).
 * Paleta: ciano Ondeline + azul marinho profundo da logo.
 */
import { loadFont } from '@remotion/google-fonts/PlusJakartaSans'

// Fonte real do app.
export const { fontFamily: JAKARTA } = loadFont()

export const theme = {
  // Principais (derivadas da logo)
  primary: '#14B8B0', // ciano Ondeline
  primaryLight: '#5FE3DC',
  primaryDark: '#0B1F3A', // navy fundo da logo
  navyDeep: '#051329',

  // Neutros light
  bg: '#F4F8FA',
  surface: '#FFFFFF',
  text: '#0B1F3A',
  muted: '#5B6F8A',
  divider: '#E3EBF0',
  white: '#FFFFFF',

  // Status / categóricas (iguais ao app)
  success: '#14B8B0',
  warning: '#E8A33D',
  danger: '#E0455A',
  info: '#3B82F6',
  purple: '#8B5CF6',
  amber: '#E8A33D',
  whatsapp: '#25D366',
  pix: '#14B8B0',
} as const

export const FONT = JAKARTA

// Composicao
export const FPS = 30
export const WIDTH = 1080
export const HEIGHT = 1920
