import React, { useState, useRef, useCallback } from 'react';
import './Dashboard.css';
import Sidebar from '../Sidebar/Sidebar';
import MapView from '../Map/MapView';
import RightPanel from '../RightPanel/RightPanel';

const Dashboard: React.FC = () => {
  const [leftWidth, setLeftWidth] = useState(350);
  const [rightWidth, setRightWidth] = useState(320);
  const isDragging = useRef<'left' | 'right' | null>(null);
  const startX = useRef(0);
  const startWidth = useRef(0);

  const handleMouseDown = useCallback((side: 'left' | 'right') => (e: React.MouseEvent) => {
    console.log('Mouse down on', side); // Debug log
    e.preventDefault();
    e.stopPropagation();
    isDragging.current = side;
    startX.current = e.clientX;
    startWidth.current = side === 'left' ? leftWidth : rightWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [leftWidth, rightWidth]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging.current) return;

    console.log('Mouse move, dragging:', isDragging.current); // Debug log
    const deltaX = e.clientX - startX.current;

    if (isDragging.current === 'left') {
      const newWidth = Math.max(250, Math.min(600, startWidth.current + deltaX));
      console.log('Setting left width to:', newWidth); // Debug log
      setLeftWidth(newWidth);
    } else if (isDragging.current === 'right') {
      const newWidth = Math.max(250, Math.min(600, startWidth.current - deltaX));
      console.log('Setting right width to:', newWidth); // Debug log
      setRightWidth(newWidth);
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    if (isDragging.current) {
      isDragging.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  }, []);

  React.useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  return (
    <div className="dashboard">
      <div 
        className="sidebar-container" 
        style={{ width: `${leftWidth}px` }}
      >
        <Sidebar />
      </div>
      
      <div 
        className="resize-handle left-handle"
        onMouseDown={handleMouseDown('left')}
      />
      
      <div className="main-content">
        <MapView />
      </div>
      
      <div 
        className="resize-handle right-handle"
        onMouseDown={handleMouseDown('right')}
      />
      
      <div 
        className="right-panel-container" 
        style={{ width: `${rightWidth}px` }}
      >
        <RightPanel />
      </div>
    </div>
  );
};

export default Dashboard;
