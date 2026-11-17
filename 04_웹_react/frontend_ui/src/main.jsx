import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles/tokens.css';
import './page.css';
import App from './App.jsx';
import './responsive.css'; // 화면 폭에 따라 3칸 → 2칸 → 1칸 (컴포넌트 CSS 뒤에 둬야 덮어씀)

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
