import React from 'react';

const AnimePage: React.FC = () => {
  return (

    <div className="min-h-screen flex items-center justify-center">
     <h1>Anime</h1>
      <img
        src="https://via.placeholder.com/300x400" // Cambia esta URL por una imagen real
        alt="Portada del Anime"
     
      />
      <p>Descripción del Anime: Una historia emocionante llena de aventuras.</p>
  </div>
    
  );
};

export default AnimePage;
