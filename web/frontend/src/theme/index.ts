import { extendTheme, type ThemeConfig } from '@chakra-ui/react'

const config: ThemeConfig = {
  initialColorMode: 'dark',
  useSystemColorMode: false,
}

const theme = extendTheme({
  config,
  colors: {
    brand: {
      50: '#ffe9e0',
      100: '#ffcab8',
      200: '#ffaa8e',
      300: '#ff8b63',
      400: '#ff6b35',  // Primary color
      500: '#e65a28',
      600: '#b4451c',
      700: '#823111',
      800: '#501c05',
      900: '#200700',
    },
  },
  styles: {
    global: {
      body: {
        bg: '#121212',
        color: '#F5F5F5',
      },
    },
  },
  components: {
    Button: {
      defaultProps: {
        colorScheme: 'brand',
      },
    },
    Card: {
      baseStyle: {
        container: {
          bg: '#1E1E1E',
          borderColor: '#1E1E1E',
        },
      },
    },
  },
})

export default theme
