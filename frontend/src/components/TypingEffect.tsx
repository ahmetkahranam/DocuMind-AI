import { Box, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';

interface TypingEffectProps {
  text: string;
  speed?: number;
  onComplete?: () => void;
}

const TypingEffect: React.FC<TypingEffectProps> = ({
  text,
  speed = 10,
  onComplete
}) => {
  const [displayText, setDisplayText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        // Uzun metinler için kelime bazlı yazım (200+ karakter)
        if (text.length > 200 && text[currentIndex] === ' ') {
          // Bir sonraki kelimeyi bulup tümünü ekle
          let nextSpaceIndex = text.indexOf(' ', currentIndex + 1);
          if (nextSpaceIndex === -1) nextSpaceIndex = text.length;
          
          setDisplayText(prev => prev + text.slice(currentIndex, nextSpaceIndex));
          setCurrentIndex(nextSpaceIndex);
        } else {
          // Normal karakter bazlı yazım
          setDisplayText(prev => prev + text[currentIndex]);
          setCurrentIndex(prev => prev + 1);
        }
      }, speed);

      return () => clearTimeout(timeout);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, text, speed, onComplete]);

  // Link dönüştürme fonksiyonu
  const renderTextWithLinks = (text: string) => {
    // https ile başlayan linkleri bul ve tıklanabilir hale getir
    const linkRegex = /(https:\/\/[^\s]+)/g;
    const parts = text.split(linkRegex);
    
    return (
      <>
        {parts.map((part, index) => {
          if (part.match(linkRegex)) {
            return (
              <a 
                key={index}
                href={part}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#3b82f6',
                  textDecoration: 'none',
                  fontWeight: 600,
                  borderRadius: '4px',
                  padding: '2px 4px',
                  backgroundColor: 'rgba(59, 130, 246, 0.1)',
                  border: '1px solid rgba(59, 130, 246, 0.2)',
                  transition: 'all 0.2s ease',
                  display: 'inline-block',
                  margin: '0 2px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                  e.currentTarget.style.boxShadow = '0 2px 4px rgba(59, 130, 246, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {part}
              </a>
            );
          }
          return part;
        })}
      </>
    );
  };

  return (
    <Box sx={{ position: 'relative' }}>
      <Typography
        component="span"
        sx={{
          whiteSpace: 'pre-wrap',
          lineHeight: 1.7,
          fontSize: '0.95rem',
          color: '#1e3a8a',
          fontFamily: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
          fontWeight: 500,
        }}
      >
        {renderTextWithLinks(displayText)}
        {currentIndex < text.length && (
          <Box
            component="span"
            sx={{
              display: 'inline-block',
              width: '2px',
              height: '1.2em',
              backgroundColor: '#1e3a8a',
              marginLeft: '2px',
              animation: 'blink 1s infinite',
              '@keyframes blink': {
                '0%, 50%': { opacity: 1 },
                '51%, 100%': { opacity: 0 },
              },
            }}
          />
        )}
      </Typography>
    </Box>
  );
};

export default TypingEffect;
