import { createTheme } from '@mui/material/styles'

/**
 * Diet Plan Studio — Organic Light Theme
 * ───────────────────────────────
 * Design tokens:
 *   Spacing unit  : 8 px
 *   Border radius : 12 px (card), 8 px (button/input)
 *   Palette       : Forest Green primary, Appetizing Orange accent, Clean Off‑white background
 */
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2E7D32',       // Forest Green – healthy/fresh
      light: '#4CAF50',
      dark: '#1B5E20',
      contrastText: '#fff',
    },
    secondary: {
      main: '#F57C00',       // Appetizing Orange
      light: '#FFB74D',
      dark: '#E65100',
      contrastText: '#fff',
    },
    background: {
      default: '#FCFCFB',    // Subtle warm off‑white
      paper: '#FFFFFF',      // Pure white cards
    },
    text: {
      primary: '#1A1C1E',    // Deep slate for readability
      secondary: '#5C6166',  // Muted gray
    },
    error: { main: '#D32F2F' },
    success: { main: '#388E3C' },
    divider: 'rgba(0, 0, 0, 0.08)',
  },

  spacing: 8,

  shape: {
    borderRadius: 12,
  },

  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica Neue", Arial, sans-serif',
    h1: { fontSize: '2.2rem', fontWeight: 800, color: '#1A1C1E' },
    h2: { fontSize: '1.45rem', fontWeight: 700, color: '#1A1C1E' },
    h3: { fontSize: '1.1rem', fontWeight: 700, color: '#1A1C1E' },
    h4: { fontSize: '0.9rem', fontWeight: 700 },
    body1: { fontSize: '0.95rem', lineHeight: 1.6 },
    body2: { fontSize: '0.85rem', lineHeight: 1.5 },
    caption: { fontSize: '0.75rem', fontWeight: 500 },
  },

  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#FCFCFB',
          scrollbarColor: '#2E7D32 transparent',
          '&::-webkit-scrollbar': { width: '8px' },
          '&::-webkit-scrollbar-thumb': { backgroundColor: '#2E7D32', borderRadius: '10px' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: '1px solid rgba(0, 0, 0, 0.06)',
          boxShadow: '0 2px 12px rgba(0, 0, 0, 0.03)',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            borderColor: 'rgba(46, 125, 50, 0.3)',
            boxShadow: '0 8px 32px rgba(46, 125, 50, 0.08)',
          },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 700,
          padding: '8px 20px',
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #388E3C 0%, #2E7D32 100%)',
          },
        },
      },
    },
    MuiTextField: {
      defaultProps: { variant: 'outlined', size: 'small', fullWidth: true },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
            backgroundColor: '#fff',
            '&:hover fieldset': { borderColor: '#2E7D32' },
            '&.Mui-focused fieldset': { borderColor: '#2E7D32' },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 600 },
        outlined: { backgroundColor: '#fff' },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          height: 8,
          backgroundColor: '#E8F5E9',
        },
        bar: { borderRadius: 4 },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 20,
          boxShadow: '0 12px 48px rgba(0, 0, 0, 0.12)',
        },
      },
    },
  },
})

export default theme
