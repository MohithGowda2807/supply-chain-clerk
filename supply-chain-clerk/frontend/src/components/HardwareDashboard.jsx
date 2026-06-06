import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Cpu, Power, Settings, ShieldCheck, Usb, Wifi } from 'lucide-react';

export default function HardwareDashboard({ recentEvent, bins, status }) {
  const [conveyorRunning, setConveyorRunning] = useState(false);
  const [activeSensor, setActiveSensor] = useState(null);
  const [openGate, setOpenGate] = useState(null);
  
  // Hardware simulation logic based on events
  useEffect(() => {
    if (recentEvent) {
      if (recentEvent.event_type === 'INTAKE_CREATED') {
        setActiveSensor('IR1');
        setConveyorRunning(true);
        
        setTimeout(() => {
          setActiveSensor('IR2');
          setConveyorRunning(false);
          
          setTimeout(() => {
            setConveyorRunning(true);
            const targetBin = recentEvent.assigned_bin;
            
            const binMap = {
              'A01': { sensor: 'IR3', gate: 'Gate1' },
              'A02': { sensor: 'IR4', gate: 'Gate2' },
              'B01': { sensor: 'IR5', gate: 'Gate3' },
              'B02': { sensor: 'IR6', gate: 'Gate4' },
            };
            
            const mapping = binMap[targetBin] || { sensor: 'IR3', gate: 'Gate1' };
            setActiveSensor(mapping.sensor);
            setOpenGate(mapping.gate);
            
            setTimeout(() => {
              setConveyorRunning(false);
              setOpenGate(null);
              setActiveSensor(null);
            }, 3000);
            
          }, 2000);
        }, 1500);
      }
    }
  }, [recentEvent]);

  const esp32Alive = status?.esp32_alive;
  const esp32Connection = status?.esp32_connection || 'none';

  const esp32BadgeStyle = esp32Alive
    ? { background: 'rgba(22, 163, 74, 0.1)', color: '#16A34A', border: '1px solid rgba(22, 163, 74, 0.25)' }
    : { background: 'rgba(220, 38, 38, 0.08)', color: '#DC2626', border: '1px solid rgba(220, 38, 38, 0.2)' };

  const esp32Label = esp32Alive
    ? (esp32Connection === 'usb' ? '🔌 USB Connected' : '📡 MQTT Online')
    : 'Disconnected';

  return (
    <div className="hardware-panel panel">
      <div className="panel-header">
        <h2 className="panel-title">
          <Cpu className="icon" size={16} /> IoT Diagnostics
        </h2>
        <span className="panel-count" style={esp32BadgeStyle}>
          {esp32Label}
        </span>
      </div>
      
      <div className="hardware-diagram">
        
        {/* ESP32 Connection Info */}
        {esp32Alive && esp32Connection === 'usb' && (
          <div style={{
            background: 'linear-gradient(135deg, #EFF6FF, #DBEAFE)',
            border: '1px solid #BFDBFE',
            borderRadius: 10,
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 11,
            fontWeight: 600,
            color: '#1E40AF'
          }}>
            <Usb size={14} />
            <span>ESP32 detected on USB serial — WiFi/MQTT not configured yet</span>
          </div>
        )}

        {/* Conveyor Visualization */}
        <div className="hw-section">
          <div className="hw-section-title">
            <span>Conveyor Belt & Sensors</span>
            <motion.div animate={{ color: conveyorRunning ? '#16A34A' : '#94A3B8' }}>
              <Power size={12} />
            </motion.div>
          </div>
          
          <div className={`conveyor-belt-visual ${!conveyorRunning ? 'stopped' : ''}`}>
            <div className="conveyor-stripes"></div>
            
            <motion.div 
              className="box-item"
              initial={{ left: '-40px', opacity: 0 }}
              animate={
                activeSensor === 'IR1' ? { left: '10px', opacity: 1 } :
                activeSensor === 'IR2' ? { left: '40%', opacity: 1 } :
                ['IR3', 'IR4', 'IR5', 'IR6'].includes(activeSensor) ? { left: '80%', opacity: 1 } :
                { left: '120%', opacity: 0 }
              }
              transition={{ duration: 1.5, ease: "linear" }}
            />
          </div>
          
          <div className="hw-sensor-list" style={{ marginTop: '10px' }}>
            <div className={`hw-sensor ${activeSensor === 'IR1' ? 'active' : ''}`}>
              <span>IR1 (Entry)</span>
              <span className="hw-status-badge">{activeSensor === 'IR1' ? 'TRIPPED' : 'CLEAR'}</span>
            </div>
            <div className={`hw-sensor ${activeSensor === 'IR2' ? 'active-amber' : ''}`}>
              <span>IR2 (Camera Stop)</span>
              <span className="hw-status-badge">{activeSensor === 'IR2' ? 'SCANNING' : 'CLEAR'}</span>
            </div>
          </div>
        </div>

        {/* Servos & Gates */}
        <div className="hw-section">
          <div className="hw-section-title">
            <span>Diverter Gates (Servos)</span>
            <Settings size={12} color="#475569" />
          </div>
          <div className="hw-sensor-list">
            <div className={`hw-sensor ${openGate === 'Gate1' ? 'active' : ''}`}>
              <span>Servo 1 (Bin A01)</span>
              <span className="hw-status-badge">{openGate === 'Gate1' ? 'OPEN' : 'CLOSED'}</span>
            </div>
            <div className={`hw-sensor ${openGate === 'Gate2' ? 'active' : ''}`}>
              <span>Servo 2 (Bin A02)</span>
              <span className="hw-status-badge">{openGate === 'Gate2' ? 'OPEN' : 'CLOSED'}</span>
            </div>
            <div className={`hw-sensor ${openGate === 'Gate3' ? 'active' : ''}`}>
              <span>Servo 3 (Bin B01)</span>
              <span className="hw-status-badge">{openGate === 'Gate3' ? 'OPEN' : 'CLOSED'}</span>
            </div>
            <div className={`hw-sensor ${openGate === 'Gate4' ? 'active' : ''}`}>
              <span>Servo 4 (Bin B02)</span>
              <span className="hw-status-badge">{openGate === 'Gate4' ? 'OPEN' : 'CLOSED'}</span>
            </div>
          </div>
        </div>

        {/* Load Cells */}
        <div className="hw-section">
          <div className="hw-section-title">
            <span>Weight Sensors (HX711)</span>
            <ShieldCheck size={12} color="#475569" />
          </div>
          <div className="hw-sensor-list">
            <div className={`hw-sensor ${bins.some(b => b.bin_code === 'A01' && b.led_state === 'confirmed') ? 'active' : ''}`}>
              <span>Cell 1 (A01)</span>
              <span className="hw-status-badge">OK</span>
            </div>
            <div className={`hw-sensor ${bins.some(b => b.bin_code === 'A02' && b.led_state === 'confirmed') ? 'active' : ''}`}>
              <span>Cell 2 (A02)</span>
              <span className="hw-status-badge">OK</span>
            </div>
            <div className={`hw-sensor ${bins.some(b => b.bin_code === 'B01' && b.led_state === 'confirmed') ? 'active' : ''}`}>
              <span>Cell 3 (B01)</span>
              <span className="hw-status-badge">OK</span>
            </div>
            <div className={`hw-sensor ${bins.some(b => b.bin_code === 'B02' && b.led_state === 'confirmed') ? 'active' : ''}`}>
              <span>Cell 4 (B02)</span>
              <span className="hw-status-badge">OK</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
