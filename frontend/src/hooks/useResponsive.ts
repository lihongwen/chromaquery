import { useState, useEffect } from 'react';

export interface BreakpointConfig {
  xs: boolean;
  sm: boolean;
  md: boolean;
  lg: boolean;
  xl: boolean;
  xxl: boolean;
}

export interface ResponsiveConfig {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  screenWidth: number;
  breakpoints: BreakpointConfig;
}

export const useResponsive = (): ResponsiveConfig => {
  const [screenData, setScreenData] = useState<ResponsiveConfig>(() => {
    const width = typeof window !== 'undefined' ? window.innerWidth : 1200;
    return {
      isMobile: width < 768,
      isTablet: width >= 768 && width < 1200,
      isDesktop: width >= 1200,
      screenWidth: width,
      breakpoints: {
        xs: width >= 0,
        sm: width >= 576,
        md: width >= 768,
        lg: width >= 992,
        xl: width >= 1200,
        xxl: width >= 1600,
      },
    };
  });

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      setScreenData({
        isMobile: width < 768,
        isTablet: width >= 768 && width < 1200,
        isDesktop: width >= 1200,
        screenWidth: width,
        breakpoints: {
          xs: width >= 0,
          sm: width >= 576,
          md: width >= 768,
          lg: width >= 992,
          xl: width >= 1200,
          xxl: width >= 1600,
        },
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return screenData;
};