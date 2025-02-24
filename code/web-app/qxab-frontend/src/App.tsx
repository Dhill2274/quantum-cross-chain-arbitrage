import './App.css'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomeDashboard from './components/HomeDashboard';
import CustomHistoric from './components/CustomHistoric';
import ArbitrageTable from './components/Arbitarge';
import NavBar from "./components/Navbar";


function App() {

  return (
    <Router>
      <NavBar /> {/* Add the navigation bar at the top */}
      <Routes>
        {/* Exact path for the home page */}
        <Route path="/" element={<HomeDashboard />} />

        {/* CustomHistoric graphs page */}
        <Route path="/custom-historic" element={<CustomHistoric />} />

        {/* ArbitrageTable pages */}
        <Route path="/arbitrage" element={<ArbitrageTable />} />
      </Routes>
    </Router>
  );

}

export default App
