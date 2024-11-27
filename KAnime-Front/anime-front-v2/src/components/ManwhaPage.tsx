import React, { useEffect, useState } from 'react';
import { getManwhasPopulares, Manwha } from '../services/manwhasService'; // Importa el servicio
import { getNuevosCapitulosManwha, NuevoCapitulo } from '../services/manwhasService'; // Importa el servicio para nuevos capítulos
import Carousel from '../components/Carousel'; // Importa el componente Carousel
import '../styles/Manwha.css';

const ManwhasPage: React.FC = () => {
  const [manwhas, setManwhas] = useState<Manwha[]>([]);
  const [nuevosCapitulos, setNuevosCapitulos] = useState<NuevoCapitulo[]>([]); // Estado para los nuevos capítulos

  useEffect(() => {
    const fetchManwhas = async () => {
      try {
        const data = await getManwhasPopulares();
        setManwhas(data);
      } catch (error) {
        console.error('Error al obtener manwhas:', error);
      }
    };

    const fetchNuevosCapitulos = async () => {
      try {
        const data = await getNuevosCapitulosManwha();
        setNuevosCapitulos(data);
      } catch (error) {
        console.error('Error al obtener nuevos capítulos:', error);
      }
    };

    fetchManwhas();
    fetchNuevosCapitulos(); // Llamamos a la función para obtener los nuevos capítulos
  }, []);



  return (
    <div className="manwhas-page">
      <Carousel manwhas={manwhas} title="Recomendado para ti" type={1} />
      <Carousel manwhas={nuevosCapitulos} title="Últimos capítulos" type={2} /> 
      
    </div>
  );
};

export default ManwhasPage;
