import { Box } from '@mui/material';
import React from 'react';

const AnimatedBackground: React.FC = () => {
  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        zIndex: -2,
        background: 'transparent',
      }}
    />
  );
};

export default AnimatedBackground;
