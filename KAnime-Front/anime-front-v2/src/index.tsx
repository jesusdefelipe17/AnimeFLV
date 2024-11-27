import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import 'slick-carousel/slick/slick.css';
import 'slick-carousel/slick/slick-theme.css';



const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement); // Aseguramos que 'root' sea de tipo HTMLElement
root.render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);
