import React from 'react';
import './Dashboard.css';
import Sidebar from '../Sidebar/Sidebar';
import MapView from '../Map/MapView';
import RightPanel from '../RightPanel/RightPanel';

const Dashboard: React.FC = () => {
  return (
    <div className="dashboard">
      <Sidebar />
      <div className="main-content">
        <MapView />
      </div>
      <RightPanel />
    </div>
  );
};

export default Dashboard;
